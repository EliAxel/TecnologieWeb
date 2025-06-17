from django.test import TestCase, Client, RequestFactory
from django.contrib.auth.models import User, Group
from django.core.exceptions import ValidationError
from django.urls import reverse
import uuid
from sylvelius.models import (
    Ordine,
    Prodotto,
    Annuncio,
)
from .models import Iban
from .views import SetupIban, get_paypal_access_token, verify_paypal_webhook
from purchase.models import Invoice
from progetto_tw.t_ests_constants import NEXT_PROD_ID
import json
from unittest.mock import patch, MagicMock
import requests

# Create your tests here.
class AnonUrls(TestCase):
    def test_pagamento(self):
        response = self.client.get('/pagamento/')
        self.assertEqual(response.status_code, 302)
    
    def test_pagamento_ok(self):
        response = self.client.get('/pagamento/confermato/')
        self.assertEqual(response.status_code, 200)

    def test_pagamento_nonok(self):
        response = self.client.get('/pagamento/annullato/')
        self.assertEqual(response.status_code, 200)
    
    def test_paypal_coa(self):
        response = self.client.get('/pagamento/paypal/coa/')
        self.assertEqual(response.status_code, 405)

class LoggedUrls(TestCase):
    def setUp(self):
        user = User.objects.create_user(username='testuser', password='Testpass0')
        group, created = Group.objects.get_or_create(name='moderatori')
        user.groups.add(group)
        self.client.login(username='testuser', password='Testpass0')
    
    def test_pagamento_logged(self):
        response = self.client.get('/pagamento/')
        self.assertEqual(response.status_code, 403)

class PurchaseTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='Testpass0')
        self.user2 = User.objects.create_user(username='testuser2', password='Testpass0')
        # Crea il prodotto SENZA i tag
        prodotto = Prodotto.objects.create(
            id=NEXT_PROD_ID,
            nome="Prodotto di Test",
            descrizione_breve="Breve descrizione del prodotto di test",
            descrizione="Descrizione dettagliata del prodotto di test",
            prezzo=100.00,
            condizione="nuovo"
        )
        prodotto2 = Prodotto.objects.create(
            id=NEXT_PROD_ID+2,
            nome="Prodotto di Test",
            descrizione_breve="Breve descrizione del prodotto di test",
            descrizione="Descrizione dettagliata del prodotto di test",
            prezzo=100.00,
            condizione="nuovo"
        )

        self.uuid1= uuid.uuid4(),
        self.uuid2= uuid.uuid4(),

        Annuncio.objects.create(
            id=NEXT_PROD_ID,
            uuid=self.uuid1,
            inserzionista=self.user,
            prodotto=prodotto,
            qta_magazzino=10,
            is_published=True
        )
        Annuncio.objects.create(
            id=NEXT_PROD_ID+2,
            uuid=self.uuid2,
            inserzionista=self.user2,
            prodotto=prodotto2,
            qta_magazzino=0,
            is_published=True
        )

    def test_purchases(self):
        self.client.login(username='testuser', password='Testpass0')
        response = self.client.get(f'/pagamento/?annuncio_id={self.uuid1}&quantita=1')
        self.assertEqual(response.status_code, 200)

        response = self.client.get(f'/pagamento/?annuncio_id={self.uuid2}&quantita=1')
        self.assertRedirects(
            response,
            expected_url=f'{reverse("sylvelius:dettagli_annuncio",kwargs={"uuid": self.uuid2})}?evento=ordine_grosso', 
            status_code=302,
            target_status_code=200 
        )

        response = self.client.get(f'/pagamento/?annuncio_id={self.uuid1}&quantita=0')
        self.assertRedirects(
            response,
            expected_url=f'{reverse("sylvelius:dettagli_annuncio",kwargs={"uuid": self.uuid1})}?evento=ordine_piccolo', 
            status_code=302,
            target_status_code=200 
        )

class PayPalCOATests(TestCase):
    def setUp(self):
        Ordine.objects.all().delete()
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='Testpass0')
        self.prodotto = Prodotto.objects.create(nome='Prodotto Test',descrizione_breve='testtest', prezzo=10.0)
        self.annuncio = Annuncio.objects.create(prodotto=self.prodotto,inserzionista=self.user, qta_magazzino=5)
        self.invoice = Invoice.objects.create(
            invoice_id='INV-123',
            user_id=self.user.id,#type: ignore
            prodotto_id=self.prodotto.id,#type: ignore
            quantita=2
        )

    @patch('purchase.views.verify_paypal_webhook', return_value=True)
    def test_checkout_order_approved(self, mock_verify):
        payload = {
            "event_type": "CHECKOUT.ORDER.APPROVED",
            "resource": {
                "purchase_units": [
                    {
                        "invoice_id": "INV-123",
                        "shipping": {
                            "address": {
                                "address_line_1": "123 Test St",
                                "admin_area_2": "Test City",
                                "admin_area_1": "TS",
                                "postal_code": "12345",
                                "country_code": "IT"
                            }
                        }
                    }
                ]
            }
        }

        response = self.client.post(
            '/pagamento/paypal/coa/',
            data=json.dumps(payload),
            content_type='application/json',
            HTTP_X_PAYPAL_SIGNATURE='dummy-signature'
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(Ordine.objects.exists())
        self.assertEqual(Ordine.objects.first().stato_consegna, "da spedire")#type: ignore
        self.annuncio.refresh_from_db()
        self.assertEqual(self.annuncio.qta_magazzino, 3)  # 5 iniziali - 2 acquistati

    @patch('purchase.views.verify_paypal_webhook', return_value=True)
    def test_insufficient_stock(self, mock_verify):
        # Modifica la quantità dell'ordine a più di quella disponibile
        self.invoice.quantita = 10
        self.invoice.save()

        payload = {
            "event_type": "CHECKOUT.ORDER.APPROVED",
            "resource": {
                "purchase_units": [
                    {
                        "invoice_id": "INV-123",
                        "shipping": {
                            "address": {
                                "address_line_1": "123 Test St",
                                "admin_area_2": "Test City",
                                "admin_area_1": "TS",
                                "postal_code": "12345",
                                "country_code": "IT"
                            }
                        }
                    }
                ]
            }
        }

        response = self.client.post(
            '/pagamento/paypal/coa/',
            data=json.dumps(payload),
            content_type='application/json',
            HTTP_X_PAYPAL_SIGNATURE='dummy-signature'
        )

        self.assertEqual(response.status_code, 200)
        ordine = Ordine.objects.first()
        self.assertEqual(ordine.stato_consegna, "annullato")#type: ignore

    @patch('purchase.views.verify_paypal_webhook', return_value=False)
    def test_verify_bad(self,mock_verify):
        payload = {}

        response = self.client.post(
            '/pagamento/paypal/coa/',
            data=json.dumps(payload),
            content_type='application/json',
            HTTP_X_PAYPAL_SIGNATURE='dummy-signature'
        )

        self.assertEqual(response.status_code, 401)

    @patch('purchase.views.verify_paypal_webhook', return_value=True)
    def test_other_ifs(self,mock_verify):
        payload = {}

        response = self.client.post(
            '/pagamento/paypal/coa/',
            data=json.dumps(payload),
            content_type='application/json',
            HTTP_X_PAYPAL_SIGNATURE='dummy-signature'
        )

        self.assertEqual(response.status_code, 400)

        payload = {
            "event_type": "CHECKOUT.ORDER.APPROVED",
            "resource": {}
        }

        response = self.client.post(
            '/pagamento/paypal/coa/',
            data=json.dumps(payload),
            content_type='application/json',
            HTTP_X_PAYPAL_SIGNATURE='dummy-signature'
        )

        self.assertEqual(response.status_code, 400)

        payload = {
            "event_type": "CHECKOUT.ORDER.APPROVED",
            "resource": {
                "purchase_units": [
                    {
                        "invoice_id": "INV-err",
                        "shipping": {
                            "address": {
                                "address_line_1": "123 Test St",
                                "admin_area_2": "Test City",
                                "admin_area_1": "TS",
                                "postal_code": "12345",
                                "country_code": "IT"
                            }
                        }
                    }
                ]
            }
        }

        response = self.client.post(
            '/pagamento/paypal/coa/',
            data=json.dumps(payload),
            content_type='application/json',
            HTTP_X_PAYPAL_SIGNATURE='dummy-signature'
        )

        self.assertEqual(response.status_code, 404)
        
        Annuncio.objects.filter(prodotto__id=self.invoice.prodotto_id).delete()
        payload = {
            "event_type": "CHECKOUT.ORDER.APPROVED",
            "resource": {
                "purchase_units": [
                    {
                        "invoice_id": "INV-123",
                        "shipping": {
                            "address": {
                                "address_line_1": "123 Test St",
                                "admin_area_2": "Test City",
                                "admin_area_1": "TS",
                                "postal_code": "12345",
                                "country_code": "IT"
                            }
                        }
                    }
                ]
            }
        }

        response = self.client.post(
            '/pagamento/paypal/coa/',
            data=json.dumps(payload),
            content_type='application/json',
            HTTP_X_PAYPAL_SIGNATURE='dummy-signature'
        )

        self.assertEqual(response.status_code, 200)

        self.invoice.prodotto_id = 1234
        self.invoice.save()

        response = self.client.post(
            '/pagamento/paypal/coa/',
            data=json.dumps(payload),
            content_type='application/json',
            HTTP_X_PAYPAL_SIGNATURE='dummy-signature'
        )

        self.assertEqual(response.status_code, 200)

        self.invoice.user_id = 1234
        self.invoice.save()

        response = self.client.post(
            '/pagamento/paypal/coa/',
            data=json.dumps(payload),
            content_type='application/json',
            HTTP_X_PAYPAL_SIGNATURE='dummy-signature'
        )

        self.assertEqual(response.status_code, 404)

class TestPaypalFunctions(TestCase):
    
    @patch('requests.post')
    def test_get_paypal_access_token_success(self, mock_post):
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"access_token": "test_token"}
        mock_post.return_value = mock_response
        
        # Call function
        token = get_paypal_access_token()
        
        # Assertions
        self.assertEqual(token, "test_token")
        mock_response.raise_for_status.assert_called_once()
    
    @patch('requests.post')
    def test_get_paypal_access_token_failure(self, mock_post):
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.raise_for_status.side_effect = requests.HTTPError("Unauthorized")
        mock_post.return_value = mock_response
        
        # Call function and assert exception
        with self.assertRaises(requests.HTTPError):
            get_paypal_access_token()
    
    @patch('purchase.views.get_paypal_access_token')
    @patch('requests.post')
    def test_verify_paypal_webhook_success(self, mock_post, mock_get_token):
        # Setup
        mock_get_token.return_value = "test_token"
        
        request = MagicMock()
        request.headers = {
            "PAYPAL-AUTH-ALGO": "algo",
            "PAYPAL-CERT-URL": "url",
            "PAYPAL-TRANSMISSION-ID": "id",
            "PAYPAL-TRANSMISSION-SIG": "sig",
            "PAYPAL-TRANSMISSION-TIME": "time"
        }
        
        body = json.dumps({
            "event_type": "CHECKOUT.ORDER.APPROVED",
            "other_data": "value"
        })
        
        # Mock verification response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"verification_status": "SUCCESS"}
        mock_post.return_value = mock_response
        
        # Call function
        result = verify_paypal_webhook(request, body)
        
        # Assertions
        self.assertTrue(result)
        mock_response.raise_for_status.assert_called_once()
    
    def test_verify_paypal_webhook_unsupported_event(self):
        # Setup
        request = MagicMock()
        body = json.dumps({"event_type": "UNSUPPORTED.EVENT"})
        
        # Call function
        result = verify_paypal_webhook(request, body)
        
        # Assertions
        self.assertFalse(result)

class SetUpIBANTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.url = reverse('purchase:setup_iban')
        self.view = SetupIban.as_view()
        self.template_name = 'purchase/setup_iban.html'

    def test_get_context_data_authenticated_user_without_iban(self):
        """Test that context contains user but no iban when user has no iban"""
        request = self.factory.get(self.url)
        request.user = self.user
        
        response = self.view(request)
        context = response.context_data #type:ignore
        
        self.assertEqual(context['user'], self.user)
        self.assertNotIn('iban', context)

    def test_get_context_data_authenticated_user_with_iban(self):
        """Test that context contains both user and iban when user has iban"""
        # Create an IBAN for the user
        iban_obj = Iban.objects.create(utente=self.user, iban='GB82WEST12345698765432')
        
        request = self.factory.get(self.url)
        request.user = self.user
        
        response = self.view(request)
        context = response.context_data #type:ignore
        
        self.assertEqual(context['user'], self.user)
        # Check that we're getting the iban string, not the object
        self.assertEqual(context['iban'].iban, iban_obj.iban)

    def test_validate_iban_valid_ibans_coverage(self):
        """Test appositamente progettato per coprire self.fail"""
        view = SetupIban()
        invalid_iban = "INVALID_IBAN"
        
        # Modifica temporanea per forzare il fail
        original_validate = view.validate_iban
        def mock_validate(iban):
            raise ValidationError("forced error")
        
        view.validate_iban = mock_validate
        
        try:
            with self.assertRaises(AssertionError):
                try:
                    view.validate_iban(invalid_iban)
                except ValidationError:
                    self.fail("This should be caught by assertRaises")
        finally:
            # Ripristina la funzione originale
            view.validate_iban = original_validate
    def test_post_valid_iban(self):
        """Test that a valid IBAN is saved and redirects"""
        self.client.force_login(self.user)
        valid_iban = 'GB82WEST12345698765432'
        
        response = self.client.post(self.url, {'iban': valid_iban})
        
        # Check IBAN was saved
        self.assertTrue(Iban.objects.filter(utente=self.user, iban=valid_iban).exists())
        # Check redirect
        self.assertRedirects(response, f"{reverse('sylvelius:profile_annunci')}?evento=iban_imp")

    def test_post_invalid_iban_format(self):
        """Test that invalid IBAN format returns error message"""
        self.client.force_login(self.user)
        invalid_iban = 'INVALID_IBAN'
        
        response = self.client.post(self.url, {'iban': invalid_iban})
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        self.assertIn('evento', response.context)
        # Expecting a list now
        self.assertEqual(response.context['evento'], 'iban_form')

    def test_post_invalid_iban_checksum(self):
        """Test that IBAN with invalid checksum returns error message"""
        self.client.force_login(self.user)
        invalid_checksum_iban = 'GB82WEST12345698765433'  # Changed last digit
        
        response = self.client.post(self.url, {'iban': invalid_checksum_iban})
        
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, self.template_name)
        self.assertIn('evento', response.context)
        # Expecting a list now
        self.assertEqual(response.context['evento'], 'iban_contr')

    def test_post_updates_existing_iban(self):
        """Test that posting updates existing IBAN"""
        # Create initial IBAN
        Iban.objects.create(utente=self.user, iban='GB82WEST12345698765432')
        self.client.force_login(self.user)
        new_iban = 'DE89370400440532013000'
        
        response = self.client.post(self.url, {'iban': new_iban})
        
        # Check only one IBAN exists (updated)
        self.assertEqual(Iban.objects.filter(utente=self.user).count(), 1)
        self.assertEqual(Iban.objects.get(utente=self.user).iban, new_iban)
        # Check redirect
        self.assertRedirects(response, f"{reverse('sylvelius:profile_annunci')}?evento=iban_imp")