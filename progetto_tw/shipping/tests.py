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
class SpedizionePageViewTests(TestCase):
    def setUp(self):
        # Crea i tag
        tag1 = Tag.objects.create(nome='Tag01')
        tag2 = Tag.objects.create(nome='Tag02')
        self.user = User.objects.create_user(username='testuser', password='Testpass0')
        # Crea il prodotto SENZA i tag
        prodotto = Prodotto.objects.create(
            id=NEXT_PROD_ID,
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

        Annuncio.objects.create(
            id=NEXT_PROD_ID,
            inserzionista=self.user,
            prodotto=prodotto,
            qta_magazzino=10,
            is_published=True
        )

        CommentoAnnuncio.objects.create(
            id = NEXT_PROD_ID,
            annuncio = Annuncio.objects.get(id=NEXT_PROD_ID),
            utente = self.user,
            testo = "Bello",
            rating = 4
        )

        invoice=Invoice.objects.create(
            invoice_id=uuid.uuid4(),
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

        Ordine.objects.create(
            id=NEXT_PROD_ID,
            invoice = invoice.invoice_id,
            utente = User.objects.get(id=invoice.user_id), 
            prodotto = Prodotto.objects.get(id=invoice.prodotto_id),
            quantita = invoice.quantita,
            stato_consegna = "consegnato",
            luogo_consegna = mock
        )
        
    def test_unlogged_access(self):
        response = self.client.get('/spedizione/')
        self.assertEqual(response.status_code, 302)
    
    def test_logged_access(self):
        User.objects.create_user(username='testuser', password='Testpass0')
        self.client.login(username='testuser', password='Testpass0')
        response = self.client.get('/spedizione/')
        self.assertEqual(response.status_code, 404)