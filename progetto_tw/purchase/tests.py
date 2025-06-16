from django.test import TestCase
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

    def test_paypal_pcc(self):
        response = self.client.get('/pagamento/paypal/pcc/')
        self.assertEqual(response.status_code, 405)
    
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
        # Crea i tag
        tag1 = Tag.objects.create(nome='Tag01')
        tag2 = Tag.objects.create(nome='Tag02')
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

        prodotto.immagini.add( # type: ignore
            ImmagineProdotto.objects.create(
                prodotto=prodotto,
                immagine='prodotti/immagini/test_image.jpg'
            )
        )
        # Aggiungi i tag al prodotto
        prodotto.tags.add(tag1, tag2)
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

        CommentoAnnuncio.objects.create(
            id = NEXT_PROD_ID,
            annuncio = Annuncio.objects.get(id=NEXT_PROD_ID),
            utente = self.user,
            testo = "Bello",
            rating = 4
        )

        invoice_uuid = uuid.uuid4()
        invoice=Invoice.objects.create(
            invoice_id=invoice_uuid,
            user_id=self.user.id, #type: ignore
            quantita=3,
            prodotto_id=NEXT_PROD_ID
        )

        mock = {
            'address_line_1': "Via test",
            'admin_area_2': 'Roma',
            'postal_code': '46029',
            'admin_area_1': 'RM',
            'country_code': 'IT'
        }

        self.coa_data = {
  "id": "WH-83F8673080821894D-9N314412BM794700P",
  "create_time": "2025-06-16T14:52:22.795Z",
  "resource_type": "checkout-order",
  "event_type": "CHECKOUT.ORDER.APPROVED",
  "summary": "An order has been approved by buyer",
  "resource": {
    "update_time": "2025-06-16T14:52:16Z",
    "create_time": "2025-06-16T14:52:10Z",
    "purchase_units": [
      {
        "reference_id": "default",
        "amount": {
          "currency_code": "EUR",
          "value": "1.00",
          "breakdown": {}
        },
        "payee": {
          "email_address": "silviaponzati@business.example.com",
          "merchant_id": "4TNWKPWRM83UA"
        },
        "invoice_id": "9765cca4-9e35-4b9e-988a-cf9605c8be02",
        "shipping": {
          "name": {
            "full_name": "Elia Martinelli"
          },
          "address": {
            "address_line_1": "Via del Corso",
            "admin_area_2": "Roma",
            "admin_area_1": "RM",
            "postal_code": "00187",
            "country_code": "IT"
          }
        },
        "payments": {
          "captures": [
            {
              "id": "9CB42170MT121991M",
              "status": "COMPLETED",
              "amount": {
                "currency_code": "EUR",
                "value": "1.00"
              },
              "final_capture": True,
              "seller_protection": {
                "status": "ELIGIBLE",
                "dispute_categories": [
                  "ITEM_NOT_RECEIVED",
                  "UNAUTHORIZED_TRANSACTION"
                ]
              },
              "seller_receivable_breakdown": {
                "gross_amount": {
                  "currency_code": "EUR",
                  "value": "1.00"
                },
                "paypal_fee": {
                  "currency_code": "EUR",
                  "value": "0.38"
                },
                "net_amount": {
                  "currency_code": "EUR",
                  "value": "0.62"
                }
              },
              "invoice_id": "9765cca4-9e35-4b9e-988a-cf9605c8be02",
              "links": [
                {
                  "href": "https://api.sandbox.paypal.com/v2/payments/captures/9CB42170MT121991M",
                  "rel": "self",
                  "method": "GET"
                },
                {
                  "href": "https://api.sandbox.paypal.com/v2/payments/captures/9CB42170MT121991M/refund",
                  "rel": "refund",
                  "method": "POST"
                },
                {
                  "href": "https://api.sandbox.paypal.com/v2/checkout/orders/0CW90826SY068845F",
                  "rel": "up",
                  "method": "GET"
                }
              ],
              "create_time": "2025-06-16T14:52:16Z",
              "update_time": "2025-06-16T14:52:16Z"
            }
          ]
        }
      }
    ],
    "links": [
      {
        "href": "https://api.sandbox.paypal.com/v2/checkout/orders/0CW90826SY068845F",
        "rel": "self",
        "method": "GET"
      }
    ],
    "id": "0CW90826SY068845F",
    "payment_source": {
      "paypal": {
        "email_address": "eliamartinelli@personal.example.com",
        "account_id": "VBJX2RLA87R4C",
        "account_status": "VERIFIED",
        "name": {
          "given_name": "Elia",
          "surname": "Martinelli"
        },
        "address": {
          "country_code": "IT"
        }
      }
    },
    "intent": "CAPTURE",
    "payer": {
      "name": {
        "given_name": "Elia",
        "surname": "Martinelli"
      },
      "email_address": "eliamartinelli@personal.example.com",
      "payer_id": "VBJX2RLA87R4C",
      "address": {
        "country_code": "IT"
      }
    },
    "status": "COMPLETED"
  },
  "status": "PENDING",
  "transmissions": [
    {
      "webhook_url": "https://kite-united-probably.ngrok-free.app/pagamento/paypal/coa/",
      "transmission_id": "8464fdfd-4ac1-11f0-b0d9-47a9f8da8c2d",
      "status": "PENDING"
    }
  ],
  "links": [
    {
      "href": "https://api.sandbox.paypal.com/v1/notifications/webhooks-events/WH-83F8673080821894D-9N314412BM794700P",
      "rel": "self",
      "method": "GET",
      "encType": "application/json"
    },
    {
      "href": "https://api.sandbox.paypal.com/v1/notifications/webhooks-events/WH-83F8673080821894D-9N314412BM794700P/resend",
      "rel": "resend",
      "method": "POST",
      "encType": "application/json"
    }
  ],
  "event_version": "1.0",
  "resource_version": "2.0"
}
        self.pcc_data = {
  "id": "WH-9XD37703VP9425530-31D162954L9840348",
  "create_time": "2025-06-16T14:52:20.284Z",
  "resource_type": "capture",
  "event_type": "PAYMENT.CAPTURE.COMPLETED",
  "summary": "Payment completed for € 1.0 EUR",
  "resource": {
    "payee": {
      "email_address": "silviaponzati@business.example.com",
      "merchant_id": "4TNWKPWRM83UA"
    },
    "amount": {
      "value": "1.00",
      "currency_code": "EUR"
    },
    "seller_protection": {
      "dispute_categories": [
        "ITEM_NOT_RECEIVED",
        "UNAUTHORIZED_TRANSACTION"
      ],
      "status": "ELIGIBLE"
    },
    "supplementary_data": {
      "related_ids": {
        "order_id": "0CW90826SY068845F"
      }
    },
    "update_time": "2025-06-16T14:52:16Z",
    "create_time": "2025-06-16T14:52:16Z",
    "final_capture": True,
    "seller_receivable_breakdown": {
      "paypal_fee": {
        "value": "0.38",
        "currency_code": "EUR"
      },
      "gross_amount": {
        "value": "1.00",
        "currency_code": "EUR"
      },
      "net_amount": {
        "value": "0.62",
        "currency_code": "EUR"
      }
    },
    "invoice_id": f"{invoice_uuid}",
    "links": [
      {
        "method": "GET",
        "rel": "self",
        "href": "https://api.sandbox.paypal.com/v2/payments/captures/9CB42170MT121991M"
      },
      {
        "method": "POST",
        "rel": "refund",
        "href": "https://api.sandbox.paypal.com/v2/payments/captures/9CB42170MT121991M/refund"
      },
      {
        "method": "GET",
        "rel": "up",
        "href": "https://api.sandbox.paypal.com/v2/checkout/orders/0CW90826SY068845F"
      }
    ],
    "id": "9CB42170MT121991M",
    "status": "COMPLETED"
  },
  "status": "PENDING",
  "transmissions": [
    {
      "webhook_url": "https://kite-united-probably.ngrok-free.app/pagamento/paypal/pcc/",
      "transmission_id": "83b9a2cc-4ac1-11f0-b0d9-8b61448ee590",
      "status": "PENDING"
    }
  ],
  "links": [
    {
      "href": "https://api.sandbox.paypal.com/v1/notifications/webhooks-events/WH-9XD37703VP9425530-31D162954L9840348",
      "rel": "self",
      "method": "GET",
      "encType": "application/json"
    },
    {
      "href": "https://api.sandbox.paypal.com/v1/notifications/webhooks-events/WH-9XD37703VP9425530-31D162954L9840348/resend",
      "rel": "resend",
      "method": "POST",
      "encType": "application/json"
    }
  ],
  "event_version": "1.0",
  "resource_version": "2.0"
}

        Ordine.objects.create(
            id=NEXT_PROD_ID,
            invoice = invoice.invoice_id,
            utente = User.objects.get(id=invoice.user_id), 
            prodotto = Prodotto.objects.get(id=invoice.prodotto_id),
            quantita = invoice.quantita,
            stato_consegna = "consegnato",
            luogo_consegna = mock
        )
        invoice=Invoice.objects.create(
            invoice_id=uuid.uuid4(),
            user_id=self.user.id, #type: ignore
            quantita=3,
            prodotto_id=NEXT_PROD_ID
        )
        Ordine.objects.create(
            id=NEXT_PROD_ID+1,
            invoice = invoice.invoice_id,
            utente = User.objects.get(id=invoice.user_id), 
            prodotto = Prodotto.objects.get(id=invoice.prodotto_id),
            quantita = invoice.quantita,
            stato_consegna = "da spedire",
            luogo_consegna = mock
        )
        invoice=Invoice.objects.create(
            invoice_id=uuid.uuid4(),
            user_id=self.user2.id, #type: ignore
            quantita=3,
            prodotto_id=NEXT_PROD_ID+2
        )
        Ordine.objects.create(
            id=NEXT_PROD_ID+2,
            invoice = invoice.invoice_id,
            utente = User.objects.get(id=invoice.user_id), 
            prodotto = Prodotto.objects.get(id=invoice.prodotto_id),
            quantita = invoice.quantita,
            stato_consegna = "da spedire",
            luogo_consegna = mock
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
            expected_url=f'{reverse("sylvelius:dettagli_annuncio",kwargs={"uuid": self.uuid2})}?evento=ordine_piccolo', 
            status_code=302,
            target_status_code=200 
        )

    def test_paypal_pcc(self):
        request = self.client.post('/pagamento/paypal_pcc/',data=self.pcc_data)