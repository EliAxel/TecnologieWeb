from django.test import TestCase, Client
from django.contrib.auth.models import User, Group
from django.urls import reverse
import uuid
from sylvelius.models import (
    Ordine,
    Prodotto,
    Annuncio,
    CommentoAnnuncio,
    Tag,
    ImmagineProdotto
)
from purchase.models import Invoice
from progetto_tw.t_ests_constants import NEXT_PROD_ID
import json
from unittest.mock import patch

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

class PayPalCOATestCase(TestCase):
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
