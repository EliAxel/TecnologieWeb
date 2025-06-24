from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from sylvelius.models import (
    Ordine,
    Prodotto,
    Annuncio,
    CommentoAnnuncio,
    Tag,
    ImmagineProdotto
)
from purchase.models import Invoice
from progetto_tw.constants import _NEXT_PROD_ID
import uuid

# Create your tests here.
class SpedizionePageViewTests(TestCase):
    def setUp(self):
        tag1 = Tag.objects.create(nome='Tag01')
        tag2 = Tag.objects.create(nome='Tag02')
        self.user = User.objects.create_user(username='testuser', password='Testpass0')
        self.user2 = User.objects.create_user(username='testuser2', password='Testpass0')
        prodotto = Prodotto.objects.create(
            id=_NEXT_PROD_ID,
            nome="Prodotto di Test",
            descrizione_breve="Breve descrizione del prodotto di test",
            descrizione="Descrizione dettagliata del prodotto di test",
            prezzo=100.00,
            condizione="nuovo"
        )
        prodotto2 = Prodotto.objects.create(
            id=_NEXT_PROD_ID+2,
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
        prodotto.tags.add(tag1, tag2)

        Annuncio.objects.create(
            id=_NEXT_PROD_ID,
            inserzionista=self.user,
            prodotto=prodotto,
            qta_magazzino=10,
            is_published=True
        )
        Annuncio.objects.create(
            id=_NEXT_PROD_ID+2,
            inserzionista=self.user2,
            prodotto=prodotto2,
            qta_magazzino=10,
            is_published=True
        )

        CommentoAnnuncio.objects.create(
            id = _NEXT_PROD_ID,
            annuncio = Annuncio.objects.get(id=_NEXT_PROD_ID),
            utente = self.user,
            testo = "Bello",
            rating = 4
        )

        invoice=Invoice.objects.create(
            invoice_id=uuid.uuid4(),
            utente=self.user, #type: ignore
            quantita=3,
            prodotto=Prodotto.objects.get(id=_NEXT_PROD_ID)
        )

        mock = {
            'address_line_1': "Via test",
            'admin_area_2': 'Roma',
            'postal_code': '46029',
            'admin_area_1': 'RM',
            'country_code': 'IT'
        }

        Ordine.objects.create(
            id=_NEXT_PROD_ID,
            invoice = invoice.invoice_id,
            utente = invoice.utente, 
            prodotto = invoice.prodotto,
            quantita = invoice.quantita,
            stato_consegna = "consegnato",
            luogo_consegna = mock
        )
        invoice=Invoice.objects.create(
            invoice_id=uuid.uuid4(),
            utente=self.user, #type: ignore
            quantita=3,
            prodotto=Prodotto.objects.get(id=_NEXT_PROD_ID)
        )
        Ordine.objects.create(
            id=_NEXT_PROD_ID+1,
            invoice = invoice.invoice_id,
            utente = invoice.utente, 
            prodotto = invoice.prodotto,
            quantita = invoice.quantita,
            stato_consegna = "da spedire",
            luogo_consegna = mock
        )
        invoice=Invoice.objects.create(
            invoice_id=uuid.uuid4(),
            utente=self.user2, #type: ignore
            quantita=3,
            prodotto=Prodotto.objects.get(id=_NEXT_PROD_ID+2)
        )
        Ordine.objects.create(
            id=_NEXT_PROD_ID+2,
            invoice = invoice.invoice_id,
            utente = invoice.utente, 
            prodotto = invoice.prodotto,
            quantita = invoice.quantita,
            stato_consegna = "da spedire",
            luogo_consegna = mock
        )
            
    def test_unlogged_access(self):
        response = self.client.get('/spedizione/')
        self.assertEqual(response.status_code, 302)
    
    def test_logged_access(self):
        self.client.login(username='testuser', password='Testpass0')
        response = self.client.get('/spedizione/')
        self.assertEqual(response.status_code, 404)

        response = self.client.get(f'/spedizione/?ordine={_NEXT_PROD_ID}')
        self.assertEqual(response.status_code, 404)

        response = self.client.get(f'/spedizione/?ordine={_NEXT_PROD_ID+2}')
        self.assertEqual(response.status_code, 404)

        response = self.client.get(f'/spedizione/?ordine={_NEXT_PROD_ID+1}')
        self.assertEqual(response.status_code, 200)

class ImpostaSpeditoTests(TestCase):

    def setUp(self):
        tag1 = Tag.objects.create(nome='Tag01')
        tag2 = Tag.objects.create(nome='Tag02')
        self.user = User.objects.create_user(username='testuser', password='Testpass0')
        self.user2 = User.objects.create_user(username='testuser2', password='Testpass0')
        prodotto = Prodotto.objects.create(
            id=_NEXT_PROD_ID,
            nome="Prodotto di Test",
            descrizione_breve="Breve descrizione del prodotto di test",
            descrizione="Descrizione dettagliata del prodotto di test",
            prezzo=100.00,
            condizione="nuovo"
        )
        prodotto2 = Prodotto.objects.create(
            id=_NEXT_PROD_ID+2,
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
        prodotto.tags.add(tag1, tag2)

        Annuncio.objects.create(
            id=_NEXT_PROD_ID,
            inserzionista=self.user,
            prodotto=prodotto,
            qta_magazzino=10,
            is_published=True
        )
        Annuncio.objects.create(
            id=_NEXT_PROD_ID+2,
            inserzionista=self.user2,
            prodotto=prodotto2,
            qta_magazzino=10,
            is_published=True
        )

        CommentoAnnuncio.objects.create(
            id = _NEXT_PROD_ID,
            annuncio = Annuncio.objects.get(id=_NEXT_PROD_ID),
            utente = self.user,
            testo = "Bello",
            rating = 4
        )

        invoice=Invoice.objects.create(
            invoice_id=uuid.uuid4(),
            utente=self.user, #type: ignore
            quantita=3,
            prodotto=Prodotto.objects.get(id=_NEXT_PROD_ID)
        )

        mock = {
            'address_line_1': "Via test",
            'admin_area_2': 'Roma',
            'postal_code': '46029',
            'admin_area_1': 'RM',
            'country_code': 'IT'
        }

        Ordine.objects.create(
            id=_NEXT_PROD_ID,
            invoice = invoice.invoice_id,
            utente = invoice.utente, 
            prodotto = invoice.prodotto,
            quantita = invoice.quantita,
            stato_consegna = "consegnato",
            luogo_consegna = mock
        )
        invoice=Invoice.objects.create(
            invoice_id=uuid.uuid4(),
            utente=self.user, #type: ignore
            quantita=3,
            prodotto=Prodotto.objects.get(id=_NEXT_PROD_ID)
        )
        Ordine.objects.create(
            id=_NEXT_PROD_ID+1,
            invoice = invoice.invoice_id,
            utente = invoice.utente, 
            prodotto = invoice.prodotto,
            quantita = invoice.quantita,
            stato_consegna = "da spedire",
            luogo_consegna = mock
        )
        invoice=Invoice.objects.create(
            invoice_id=uuid.uuid4(),
            utente=self.user2, #type: ignore
            quantita=3,
            prodotto=Prodotto.objects.get(id=_NEXT_PROD_ID+2)
        )
        Ordine.objects.create(
            id=_NEXT_PROD_ID+2,
            invoice = invoice.invoice_id,
            utente = invoice.utente, 
            prodotto = invoice.prodotto,
            quantita = invoice.quantita,
            stato_consegna = "da spedire",
            luogo_consegna = mock
        )
    
    def test_unlogged_access(self):
        response = self.client.get(f'/spedizione/spedito/{_NEXT_PROD_ID}/')
        self.assertEqual(response.status_code, 302)

        response = self.client.post(f'/spedizione/spedito/{_NEXT_PROD_ID+1}/')
        response = self.assertEqual(response.status_code, 302)

    def test_logged_access(self):
        self.client.login(username='testuser', password='Testpass0')
        response = self.client.get(f'/spedizione/spedito/{_NEXT_PROD_ID}/')
        self.assertEqual(response.status_code, 405)

        response = self.client.get(f'/spedizione/spedito/{_NEXT_PROD_ID+2}/')
        self.assertEqual(response.status_code, 405)

        response = self.client.get(f'/spedizione/spedito/{_NEXT_PROD_ID+1}/')
        self.assertEqual(response.status_code, 405)
        #post
        response = self.client.post(f'/spedizione/spedito/{_NEXT_PROD_ID}/')
        self.assertEqual(response.status_code, 404)

        response = self.client.post(f'/spedizione/spedito/{_NEXT_PROD_ID+2}/')
        self.assertEqual(response.status_code, 404)

        response = self.client.post(f'/spedizione/spedito/{_NEXT_PROD_ID+1}/?page=1')
        self.assertRedirects(
            response,
            expected_url=f'{reverse("sylvelius:profile_clienti")}?page=1&evento=spedito_ordine', 
            status_code=302,
            target_status_code=200 
        )

class ImpostaCompletatoTests(TestCase):
    
    def setUp(self):
        tag1 = Tag.objects.create(nome='Tag01')
        tag2 = Tag.objects.create(nome='Tag02')
        self.user = User.objects.create_user(username='testuser', password='Testpass0')
        self.user2 = User.objects.create_user(username='testuser2', password='Testpass0')
        prodotto = Prodotto.objects.create(
            id=_NEXT_PROD_ID,
            nome="Prodotto di Test",
            descrizione_breve="Breve descrizione del prodotto di test",
            descrizione="Descrizione dettagliata del prodotto di test",
            prezzo=100.00,
            condizione="nuovo"
        )
        prodotto2 = Prodotto.objects.create(
            id=_NEXT_PROD_ID+2,
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
        prodotto.tags.add(tag1, tag2)

        Annuncio.objects.create(
            id=_NEXT_PROD_ID,
            inserzionista=self.user,
            prodotto=prodotto,
            qta_magazzino=10,
            is_published=True
        )
        Annuncio.objects.create(
            id=_NEXT_PROD_ID+2,
            inserzionista=self.user2,
            prodotto=prodotto2,
            qta_magazzino=10,
            is_published=True
        )

        CommentoAnnuncio.objects.create(
            id = _NEXT_PROD_ID,
            annuncio = Annuncio.objects.get(id=_NEXT_PROD_ID),
            utente = self.user,
            testo = "Bello",
            rating = 4
        )

        invoice=Invoice.objects.create(
            invoice_id=uuid.uuid4(),
            utente=self.user, #type: ignore
            quantita=3,
            prodotto=Prodotto.objects.get(id=_NEXT_PROD_ID)
        )

        mock = {
            'address_line_1': "Via test",
            'admin_area_2': 'Roma',
            'postal_code': '46029',
            'admin_area_1': 'RM',
            'country_code': 'IT'
        }

        Ordine.objects.create(
            id=_NEXT_PROD_ID,
            invoice = invoice.invoice_id,
            utente = invoice.utente, 
            prodotto = invoice.prodotto,
            quantita = invoice.quantita,
            stato_consegna = "consegnato",
            luogo_consegna = mock
        )
        invoice=Invoice.objects.create(
            invoice_id=uuid.uuid4(),
            utente=self.user, #type: ignore
            quantita=3,
            prodotto=Prodotto.objects.get(id=_NEXT_PROD_ID)
        )
        Ordine.objects.create(
            id=_NEXT_PROD_ID+1,
            invoice = invoice.invoice_id,
            utente = invoice.utente, 
            prodotto = invoice.prodotto,
            quantita = invoice.quantita,
            stato_consegna = "da spedire",
            luogo_consegna = mock
        )
        invoice=Invoice.objects.create(
            invoice_id=uuid.uuid4(),
            utente=self.user2, #type: ignore
            quantita=3,
            prodotto=Prodotto.objects.get(id=_NEXT_PROD_ID+2)
        )
        Ordine.objects.create(
            id=_NEXT_PROD_ID+2,
            invoice = invoice.invoice_id,
            utente = invoice.utente, 
            prodotto = invoice.prodotto,
            quantita = invoice.quantita,
            stato_consegna = "da spedire",
            luogo_consegna = mock
        )
    
    def test_unlogged_access(self):
        response = self.client.get(f'/spedizione/completato/{_NEXT_PROD_ID}/')
        self.assertEqual(response.status_code, 302)

        response = self.client.post(f'/spedizione/completato/{_NEXT_PROD_ID+1}/')
        response = self.assertEqual(response.status_code, 302)

    def test_logged_access(self):
        self.client.login(username='testuser', password='Testpass0')
        response = self.client.get(f'/spedizione/completato/{_NEXT_PROD_ID}/')
        self.assertEqual(response.status_code, 405)

        response = self.client.get(f'/spedizione/completato/{_NEXT_PROD_ID+2}/')
        self.assertEqual(response.status_code, 405)

        response = self.client.get(f'/spedizione/completato/{_NEXT_PROD_ID+1}/')
        self.assertEqual(response.status_code, 405)
        #post
        response = self.client.post(f'/spedizione/completato/{_NEXT_PROD_ID}/')
        self.assertEqual(response.status_code, 404)

        response = self.client.post(f'/spedizione/completato/{_NEXT_PROD_ID+2}/')
        self.assertEqual(response.status_code, 404)

        response = self.client.post(f'/spedizione/completato/{_NEXT_PROD_ID+1}/?page=1')
        self.assertRedirects(
            response,
            expected_url=f'{reverse("sylvelius:profile_clienti")}?page=1&evento=completato_ordine', 
            status_code=302,
            target_status_code=200 
        )
