from django.test import TestCase
from django.contrib.auth.models import User, Group
from django.urls import reverse
import uuid

from sylvelius.forms import CustomUserCreationForm
from .models import (
    Ordine,
    Prodotto,
    Annuncio,
    CommentoAnnuncio,
    Tag,
    ImmagineProdotto
)
from purchase.models import Invoice
from progetto_tw.t_ests_constants import NEXT_PROD_ID

class AnonUrls(TestCase):

    def test_home_page(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        response = self.client.get('')
        self.assertEqual(response.status_code, 200)
    
    def test_signup_page(self):
        response = self.client.get('/register/')
        self.assertEqual(response.status_code, 200)

    def test_signin_page(self):
        response = self.client.get('/login/')
        self.assertEqual(response.status_code, 200)
        
    def test_logout_page(self):
        response = self.client.get('/logout/')
        self.assertEqual(response.status_code, 405)
    
    def test_accounts_profilo_page(self):
        response = self.client.get('/account/profilo/')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('sylvelius:login') + "?auth=error&next=/account/profilo/")  # type: ignore

    def test_accounts_profilo_edit_page(self):
        response = self.client.get('/account/profilo/modifica/')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('sylvelius:login') + "?auth=error&next=/account/profilo/modifica/") # type: ignore
    
    def test_accounts_profilo_delete_page(self):
        response = self.client.get('/account/profilo/elimina/')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('sylvelius:login') + "?auth=error&next=/account/profilo/elimina/") # type: ignore

    def test_annuncio_profilo_ordini(self):
        response = self.client.get('/account/profilo/ordini/')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('sylvelius:login') + "?auth=error&next=/account/profilo/ordini/") # type: ignore

    def test_annuncio_profilo_annunci(self):
        response = self.client.get('/account/profilo/annunci/')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('sylvelius:login') + "?auth=error&next=/account/profilo/annunci/") # type: ignore
    
    def test_annuncio_profilo_annunci_crea(self):
        response = self.client.get('/account/profilo/annunci/crea/')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('sylvelius:login') + "?auth=error&next=/account/profilo/annunci/crea/") # type: ignore
    
    def test_ricerca(self):
        response = self.client.get('/ricerca/')
        self.assertEqual(response.status_code, 200)

    def test_check_old_password(self):
        response = self.client.get('/check_old_password/')
        self.assertEqual(response.status_code, 405)   

    def test_check_username_exists(self):
        response = self.client.get('/check_username_exists/')
        self.assertEqual(response.status_code, 405)
    
    def test_check_login_credentials(self):
        response = self.client.get('/check_login_credentials/')
        self.assertEqual(response.status_code, 405)

class LoggedUrls(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='Testpass0')
        self.client.login(username='testuser', password='Testpass0')

    def test_logout_page(self):
        response = self.client.get('/logout/')
        self.assertEqual(response.status_code, 405)

    def test_profilo_page(self):
        response = self.client.get('/account/profilo/')
        self.assertEqual(response.status_code, 200)

    def test_profilo_edit_page(self):
        response = self.client.get('/account/profilo/modifica/')
        self.assertEqual(response.status_code, 200)

    def test_profilo_delete_page(self):
        response = self.client.get('/account/profilo/elimina/')
        self.assertEqual(response.status_code, 200)

    def test_profilo_ordini_page(self):
        response = self.client.get('/account/profilo/ordini/')
        self.assertEqual(response.status_code, 200)
    
    def test_profilo_annunci_page(self):
        response = self.client.get('/account/profilo/annunci/')
        self.assertEqual(response.status_code, 200)
    
    def test_profilo_annunci_crea_page(self):
        response = self.client.get('/account/profilo/annunci/crea/')
        self.assertEqual(response.status_code, 200)

class UrlsWithData(TestCase):
    def setUp(self):
        # Crea i tag
        tag1 = Tag.objects.create(nome='Tag01')
        tag2 = Tag.objects.create(nome='Tag02')
        user = User.objects.create_user(username='testuser', password='Testpass0')
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

        self.ann_uuid=uuid.uuid4()
        Annuncio.objects.create(
            uuid=self.ann_uuid,
            inserzionista=user,
            prodotto=prodotto,
            qta_magazzino=10,
            is_published=True
        )
    
    def test_account_profilo_annunci_nascondi_1(self):
        response = self.client.get('/account/profilo/annunci/nascondi/1/')
        self.assertEqual(response.status_code, 405)
    
    def test_account_profilo_annunci_elimina_1(self):
        response = self.client.get('/account/profilo/annunci/elimina/1/')
        self.assertEqual(response.status_code, 405)
    
    def test_annuncio_1(self):
        response = self.client.get(f'/annuncio/{self.ann_uuid}/')
        self.assertEqual(response.status_code, 200)
    
    def test_aggiungi_commento_1(self):
        response = self.client.get('/aggiungi_commento/1/')
        self.assertEqual(response.status_code, 405)

    def test_modifica_commento_1(self):
        response = self.client.get('/modifica_commento/1/')
        self.assertEqual(response.status_code, 405)

    def test_elimina_commento_1(self):
        response = self.client.get('/elimina_commento/1/')
        self.assertEqual(response.status_code, 405)
    
    def test_api_immagine(self):
        response = self.client.get(f'/api/immagine/{NEXT_PROD_ID}/')
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIn('url', data)
        self.assertEqual(data['url'],"/media/prodotti/immagini/test_image.jpg")
        response = self.client.get('/api/immagine/1/')
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIn('url', data)
        self.assertEqual(data['url'],"/static/img/default_product.png")
    
    def test_api_immagini(self):
        response = self.client.get(f'/api/immagini/{NEXT_PROD_ID}/')
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIn('urls', data)
        self.assertEqual(data['urls'][0],"/media/prodotti/immagini/test_image.jpg")

        response = self.client.get('/api/immagini/1/')
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIn('urls', data)
        self.assertEqual(data['urls'][0],"/static/img/default_product.png")

class ModelsTestingStringsCoverage(TestCase):
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
        
    def test_to_string(self):
        self.assertEqual(Tag.objects.get(nome="tag01").__str__(),"tag01")
        self.assertEqual(Prodotto.objects.get(id=NEXT_PROD_ID).immagini.first().__str__(),"Immagine di Prodotto di Test") #type: ignore
        self.assertEqual(Annuncio.objects.get(id=NEXT_PROD_ID).__str__(),"Prodotto di Test")
        self.assertEqual(CommentoAnnuncio.objects.get(id=NEXT_PROD_ID).__str__(),"testuser su Prodotto di Test - 4/5")
        self.assertEqual(Annuncio.objects.get(id=NEXT_PROD_ID).rating_medio,4)
        self.assertEqual(Annuncio.objects.get(id=NEXT_PROD_ID).rating_count,1)
        self.assertEqual(Ordine.objects.get(id=NEXT_PROD_ID).__str__(),"testuser - Prodotto di Test")
        self.assertEqual(Ordine.objects.get(id=NEXT_PROD_ID).totale,300.00)
        self.assertEqual(Ordine.objects.get(id=NEXT_PROD_ID).json_to_string,'{"address_line_1": "Via test", "admin_area_2": "Roma", "postal_code": "46029", "admin_area_1": "RM", "country_code": "IT"}')

class LoggedUrls2(TestCase):
    def setUp(self):
        user = User.objects.create_user(username='testuser', password='Testpass0')
        group, created = Group.objects.get_or_create(name='moderatori')
        user.groups.add(group)
        self.client.login(username='testuser', password='Testpass0')
    
    def test_pagamento_logged(self):
        response = self.client.post('/account/profilo/ordini/')
        self.assertEqual(response.status_code, 403)
    
    def test_form_custom_user_creation_form(self):
        form = CustomUserCreationForm(data={'username':'testuser2', 'password1': 'Testpass0', 'password2': 'Testpass0'})
        self.assertTrue(form.is_valid())
        form = CustomUserCreationForm(data={'password1': 'Testpass0', 'password2': 'Testpass0'})
        self.assertFalse(form.is_valid())
        form = CustomUserCreationForm(data={'username':'A12345678912345678901234567890123', 'password1': 'Testpass0', 'password2': 'Testpass0'})
        self.assertFalse(form.is_valid())
        form = CustomUserCreationForm(data={'username':'testuser3', 'password2': 'Testpass0'})
        self.assertFalse(form.is_valid())
        form = CustomUserCreationForm(data={'username':'testuser3', 'password1': 'A12345678912345678901234567890123', 'password2': 'A12345678912345678901234567890123'})
        self.assertFalse(form.is_valid())

