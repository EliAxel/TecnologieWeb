from django.test import TestCase, Client, RequestFactory
from django.contrib.auth.models import User, Group
from django.core.exceptions import ValidationError
from django.urls import reverse
import uuid
from sylvelius.models import (
    Ordine,
    Prodotto,
    Annuncio,
    Tag
)
from .models import Iban, Invoice, Cart
from .views import SetupIban, get_paypal_access_token, verify_paypal_webhook
from progetto_tw.t_ests_constants import NEXT_PROD_ID
from progetto_tw.constants import _MODS_GRP_NAME
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
        group, created = Group.objects.get_or_create(name=_MODS_GRP_NAME)
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

        response = self.client.get(f'/pagamento/?annuncio_id={self.uuid1}&quantita=err')
        self.assertRedirects(
            response,
            expected_url=f'{reverse("sylvelius:dettagli_annuncio",kwargs={"uuid": self.uuid1})}?evento=non_intero', 
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
            utente=self.user,
            prodotto=self.prodotto,
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
    def test_checkout_address_missing(self, mock_verify):
        payload = {
            "event_type": "CHECKOUT.ORDER.APPROVED",
            "resource": {
                "purchase_units": [
                    {
                        "invoice_id": "INV-123",
                        "shipping": {
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

        self.assertEqual(response.status_code, 400)

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
        
        Annuncio.objects.filter(prodotto=self.invoice.prodotto).delete()
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

    @patch('purchase.views.verify_paypal_webhook', return_value=True)
    def test_checkout_order_approved_with_cart(self, mock_verify):
        # Creiamo un carrello con più fatture
        cart = Cart.objects.create(uuid='CART-123', utente=self.user)
        
        # Creiamo 2 fatture associate al carrello
        invoice1 = Invoice.objects.create(
            invoice_id='INV-001',
            utente=self.user,
            prodotto=self.prodotto,
            quantita=1,
            cart=cart
        )
        
        # Creiamo un secondo prodotto e annuncio per la seconda fattura
        prodotto2 = Prodotto.objects.create(nome='Prodotto Test 2', descrizione_breve='testtest2', prezzo=15.0)
        annuncio2 = Annuncio.objects.create(prodotto=prodotto2, inserzionista=self.user, qta_magazzino=10)
        
        invoice2 = Invoice.objects.create(
            invoice_id='INV-002',
            utente=self.user,
            prodotto=prodotto2,
            quantita=3,
            cart=cart
        )

        payload = {
            "event_type": "CHECKOUT.ORDER.APPROVED",
            "resource": {
                "purchase_units": [
                    {
                        "invoice_id": "CART-123",  # ID del carrello
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
        
        # Verifichiamo che siano stati creati 2 ordini
        self.assertEqual(Ordine.objects.count(), 2)
        
        # Verifichiamo l'aggiornamento delle quantità
        self.annuncio.refresh_from_db()
        self.assertEqual(self.annuncio.qta_magazzino, 4)  # 5 - 1
        annuncio2.refresh_from_db()
        self.assertEqual(annuncio2.qta_magazzino, 7)  # 10 - 3

    @patch('purchase.views.verify_paypal_webhook', return_value=True)
    def test_checkout_order_approved_with_cart_insufficient_stock(self, mock_verify):
        # Creiamo un carrello con una fattura che ha quantità insufficiente
        cart = Cart.objects.create(uuid='CART-123', utente=self.user)
        
        # Modifichiamo la quantità disponibile a 1
        self.annuncio.qta_magazzino = 1
        self.annuncio.save()
        
        # Creiamo 2 fatture associate al carrello
        invoice1 = Invoice.objects.create(
            invoice_id='INV-001',
            utente=self.user,
            prodotto=self.prodotto,
            quantita=2,  # Quantità maggiore di quella disponibile
            cart=cart
        )
        
        payload = {
            "event_type": "CHECKOUT.ORDER.APPROVED",
            "resource": {
                "purchase_units": [
                    {
                        "invoice_id": "CART-123",
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
        
        # Verifichiamo che l'ordine sia stato creato ma annullato
        ordine = Ordine.objects.first()
        self.assertEqual(ordine.stato_consegna, "annullato")#type: ignore
        self.assertEqual(ordine.quantita, 2)#type: ignore
        self.annuncio.refresh_from_db()
        self.assertEqual(self.annuncio.qta_magazzino, 1)  # Non deve essere cambiato

    @patch('purchase.views.verify_paypal_webhook', return_value=True)
    def test_checkout_order_approved_with_empty_cart(self, mock_verify):
        # Creiamo un carrello vuoto
        cart = Cart.objects.create(uuid='CART-123', utente=self.user)

        payload = {
            "event_type": "CHECKOUT.ORDER.APPROVED",
            "resource": {
                "purchase_units": [
                    {
                        "invoice_id": "CART-123",
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
        # Nessun ordine dovrebbe essere creato
        self.assertFalse(Ordine.objects.exists())

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

class CartTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        # Login del client
        self.client.force_login(self.user)
        
        # Crea un prodotto e annuncio di test
        self.tag = Tag.objects.create(nome='elettronica')
        self.prodotto = Prodotto.objects.create(
            nome='Smartphone',
            descrizione_breve='Un ottimo smartphone',
            descrizione='Descrizione dettagliata',
            prezzo=599.99,
            iva=22,
            condizione='nuovo'
        )
        self.prodotto.tags.add(self.tag)
        
        self.annuncio = Annuncio.objects.create(
            inserzionista=self.user,
            prodotto=self.prodotto,
            qta_magazzino=10,
            uuid=str(uuid.uuid4()),
            is_published=True
        )
        
        # Crea un carrello per l'utente
        self.cart = Cart.objects.create(
            utente=self.user,
            uuid=str(uuid.uuid4())
        )
        
        # Crea una invoice di test
        self.invoice = Invoice.objects.create(
            invoice_id=str(uuid.uuid4()),
            utente=self.user,
            quantita=2,
            prodotto=self.prodotto,
            cart=self.cart
        )

    def test_add_to_cart_new_item(self):
        """Test aggiunta di un nuovo articolo al carrello"""
        # Cancella il carrello esistente per testare la creazione
        Cart.objects.filter(utente=self.user).delete()
        
        response = self.client.post(
            reverse('purchase:add_to_cart'),
            {'annuncio_id': self.annuncio.uuid, 'quantita': 3}
        )
        # Verifica che sia stato creato un nuovo carrello
        self.assertTrue(Cart.objects.filter(utente=self.user).exists())
        
        # Verifica che sia stata creata una nuova invoice
        cart = Cart.objects.get(utente=self.user)
        self.assertEqual(cart.invoices.count(), 1) #type:ignore
        
        # Verifica il redirect alla pagina dell'annuncio
        self.assertEqual(response.status_code, 302)
        self.assertIn(str(self.annuncio.uuid), response.url) #type:ignore

    def test_add_to_cart_item(self):
        """Test aggiunta di un nuovo articolo al carrello"""
        
        response = self.client.post(
            reverse('purchase:add_to_cart'),
            {'annuncio_id': self.annuncio.uuid, 'quantita': 2}
        )        
        self.assertEqual(self.cart.invoices.count(), 2) #type:ignore
        
        # Verifica il redirect alla pagina dell'annuncio
        self.assertEqual(response.status_code, 302)
        self.assertIn(str(self.annuncio.uuid), response.url) #type:ignore

    def test_add_to_cart_invalid_annuncio(self):
        """Test aggiunta con annuncio non valido"""
        response = self.client.post(
            reverse('purchase:add_to_cart'),
            {'annuncio_id': 'uuid-non-valido', 'quantita': 1}
        )
        
        # Verifica il redirect alla home
        self.assertEqual(response.status_code, 404)
    
    def test_add_to_cart_invalid_quantita(self):
        """Test aggiunta con annuncio non valido"""
        response = self.client.post(
            reverse('purchase:add_to_cart'),
            {'annuncio_id': self.annuncio.uuid, 'quantita': 'err'}
        )
        
        # Verifica il redirect alla home
        self.assertEqual(response.status_code, 302)

    def test_aumenta_carrello(self):
        """Test incremento quantità articolo nel carrello"""
        response = self.client.post(
            reverse('purchase:aumenta_carrello', kwargs={'invoice_id': self.invoice.invoice_id})
        )
        
        # Verifica che la quantità sia aumentata
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.quantita, 3)
        
        # Verifica il redirect al carrello
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('purchase:carrello')) #type:ignore
    
    def test_aumenta_carrello_non_existent_annuncio(self):
        """Test incremento quantità articolo nel carrello"""
        # Crea un oggetto Invoice con dati minimi validi ma prodotto/annuncio non esistente
        inv_err = Invoice.objects.create(
            invoice_id=str(uuid.uuid4()),
            utente=self.user,
            quantita=1,
            prodotto=self.prodotto,  # prodotto esistente, ma puoi anche crearne uno nuovo se vuoi testare annuncio mancante
            cart=self.cart
        )
        # Elimina l'annuncio associato per simulare annuncio non esistente
        inv_err.prodotto.annunci.delete() # type: ignore
        response = self.client.post(
            reverse('purchase:aumenta_carrello', kwargs={'invoice_id': inv_err.invoice_id})
        )
        
        # Verifica il redirect al carrello
        self.assertEqual(response.status_code, 302)

    def test_aumenta_carrello_exceeds_stock(self):
        """Test incremento quantità oltre la disponibilità"""
        # Imposta la quantità vicina al massimo
        self.invoice.quantita = 11
        self.invoice.save()
        
        response = self.client.post(
            reverse('purchase:aumenta_carrello', kwargs={'invoice_id': self.invoice.invoice_id})
        )
        
        # Verifica che la quantità sia stata impostata al massimo
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.quantita, 10)
        
        # Verifica il redirect con messaggio di errore
        self.assertEqual(response.status_code, 302)
        self.assertIn('?evento=troppi_articoli', response.url) #type:ignore

    def test_diminuisci_carrello(self):
        """Test decremento quantità articolo nel carrello"""
        response = self.client.post(
            reverse('purchase:diminuisci_carrello', kwargs={'invoice_id': self.invoice.invoice_id})
        )
        
        # Verifica che la quantità sia diminuita
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.quantita, 1)
        
        # Verifica il redirect al carrello
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('purchase:carrello')) #type:ignore
    
    def test_diminuisci_carrello_non_existent_annuncio(self):
        """Test decremento quantità articolo nel carrello"""
        inv_err = Invoice.objects.create(
            invoice_id=str(uuid.uuid4()),
            utente=self.user,
            quantita=1,
            prodotto=self.prodotto,  # prodotto esistente, ma puoi anche crearne uno nuovo se vuoi testare annuncio mancante
            cart=self.cart
        )
        inv_err.prodotto.annunci.delete() # type: ignore
        response = self.client.post(
            reverse('purchase:diminuisci_carrello', kwargs={'invoice_id': inv_err.invoice_id})
        )
        
        # Verifica il redirect al carrello
        self.assertEqual(response.status_code, 302)

    def test_diminuisci_carrello_to_zero(self):
        """Test decremento quantità fino a zero (cancellazione articolo)"""
        # Imposta la quantità a 1
        self.invoice.quantita = 1
        self.invoice.save()
        
        response = self.client.post(
            reverse('purchase:diminuisci_carrello', kwargs={'invoice_id': self.invoice.invoice_id})
        )
        
        # Verifica che l'invoice sia stata cancellata
        self.assertFalse(Invoice.objects.filter(invoice_id=self.invoice.invoice_id).exists())
        
        # Verifica il redirect al carrello
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('purchase:carrello')) #type:ignore

    def test_rimuovi_da_carrello(self):
        """Test rimozione articolo dal carrello"""
        response = self.client.post(
            reverse('purchase:rimuovi_da_carrello', kwargs={'invoice_id': self.invoice.invoice_id})
        )
        
        # Verifica che l'invoice sia stata cancellata
        self.assertFalse(Invoice.objects.filter(invoice_id=self.invoice.invoice_id).exists())
        
        # Verifica il redirect al carrello con messaggio
        self.assertEqual(response.status_code, 302)
        self.assertIn('?evento=rimosso', response.url) #type:ignore

    def test_carrello_page_view_with_cart(self):
        """Test visualizzazione pagina carrello con carrello esistente"""
        response = self.client.get(reverse('purchase:carrello'))
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('cart', response.context)
        self.assertEqual(response.context['cart'], self.cart)

    def test_carrello_page_view_without_cart(self):
        """Test visualizzazione pagina carrello senza carrello esistente"""
        # Cancella il carrello esistente
        Cart.objects.filter(utente=self.user).delete()
        
        response = self.client.get(reverse('purchase:carrello'))
        
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('cart', response.context)

    def test_checkout_page_view_with_cart(self):
        """Test visualizzazione pagina checkout con carrello esistente"""
        with patch('purchase.views.settings') as mock_settings:
            mock_settings.xxx = 'test_client_id'
            response = self.client.get(reverse('purchase:checkout'))
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('cart', response.context)
        self.assertIn('amount', response.context)
        self.assertIn('paypal_client_id', response.context)
        self.assertIn('invoice_id', response.context)
        self.assertEqual(response.context['cart'], self.cart)
        self.assertEqual(response.context['amount'], self.cart.total)
        self.assertEqual(response.context['paypal_client_id'], 'test_client_id')
        self.assertEqual(response.context['invoice_id'], self.cart.uuid)

    def test_checkout_page_view_removes_invalid_items(self):
        """Test che verifica che gli articoli non più disponibili vengano rimossi"""
        # Crea un prodotto e annuncio che verrà cancellato
        prodotto2 = Prodotto.objects.create(
            nome='Prodotto da cancellare',
            descrizione_breve='Descrizione breve',
            prezzo=19.99,
            iva=22,
            condizione='usato'
        )
        annuncio2 = Annuncio.objects.create(
            inserzionista=self.user,
            prodotto=prodotto2,
            qta_magazzino=5,
            uuid=str(uuid.uuid4())
        )
        invoice2 = Invoice.objects.create(
            invoice_id=str(uuid.uuid4()),
            utente=self.user,
            quantita=1,
            prodotto=prodotto2,
            cart=self.cart
        )
        
        # Cancella l'annuncio (ma non il prodotto)
        annuncio2.delete()
        
        response = self.client.get(reverse('purchase:checkout'))
        
        # Verifica che l'invoice con prodotto non più disponibile sia stata cancellata
        self.assertFalse(Invoice.objects.filter(invoice_id=invoice2.invoice_id).exists())
        
    def test_checkout_page_view_without_cart(self):
        """Test visualizzazione pagina checkout senza carrello esistente"""
        # Cancella il carrello esistente
        Cart.objects.filter(utente=self.user).delete()
        
        response = self.client.get(reverse('purchase:checkout'))
        
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('cart', response.context)
    
    def test_cart_check(self):
        response= self.client.get(reverse('sylvelius:cart_check'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('count', response.json())
        self.assertEqual(response.json()['count'], self.cart.invoices.count()) # type: ignore

        self.cart.delete()
        response= self.client.get(reverse('sylvelius:cart_check'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('count', response.json())
        self.assertEqual(response.json()['count'], 0) # type: ignore