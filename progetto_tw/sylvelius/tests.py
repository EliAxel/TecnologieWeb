from decimal import Decimal
import json
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

from django.test import TestCase, RequestFactory, Client
from django.contrib.auth.models import User, Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.core.files import File
from django.conf import settings
import tempfile
import shutil
import os

from .models import (
    Annuncio, CommentoAnnuncio, ImmagineProdotto, 
    Ordine, Tag, Prodotto, Notification
)
from .views import (
    send_notification, mark_notifications_read, create_notification,
    annulla_ordine_free, check_if_annuncio_is_valid
)

class UtilityFunctionsTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username='testuser', password='testpass123'
        )
        self.client = Client()
        
        # Crea un gruppo moderatori se non esiste
        self.moderator_group, _ = Group.objects.get_or_create(name='moderatori')
        
        # Configurazione per i test con immagini
        self.temp_media_dir = tempfile.mkdtemp()
        settings.MEDIA_ROOT = self.temp_media_dir
        
    def tearDown(self):
        shutil.rmtree(self.temp_media_dir)
    
    def test_send_notification(self):
        # Testa l'invio di una notifica globale
        response = send_notification(title="Test", message="Global message", global_notification=True)
        self.assertIsNone(response)  # La funzione non ritorna nulla
        
        # Testa l'invio di una notifica a un utente specifico
        response = send_notification(user_id=self.user.id, title="Test", message="User message") #type:ignore
        self.assertIsNone(response)
    
    def test_mark_notifications_read(self):
        # Crea una notifica non letta
        Notification.objects.create(
            recipient=self.user,
            title="Test",
            message="Test message",
            read=False
        )
        
        # Simula una richiesta POST autenticata
        request = self.factory.post(reverse('sylvelius:mark_notifications_read'))
        request.user = self.user
        
        response = mark_notifications_read(request)
        response_data = json.loads(response.content.decode())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response_data, {'status': 'ok'})
        
        # Verifica che la notifica sia stata marcata come letta
        notification = Notification.objects.get(recipient=self.user)
        self.assertTrue(notification.read)
    
    def test_create_notification(self):
        # Testa la creazione di una notifica per utente
        notifica = create_notification(
            recipient=self.user,
            title="User Notification",
            message="Test message"
        )
        self.assertIsInstance(notifica, Notification)
        self.assertEqual(notifica.recipient, self.user)
        self.assertFalse(notifica.read)
        
        # Testa la creazione di una notifica globale
        notifica = create_notification(
            title="Global Notification",
            message="Global message",
            is_global=True
        )
        self.assertTrue(notifica.is_global)
        self.assertIsNone(notifica.recipient)
    
    def test_annulla_ordine_free(self):
        # Crea un venditore e un prodotto
        venditore = User.objects.create_user(
            username='venditore', password='testpass123'
        )
        prodotto = Prodotto.objects.create(
            nome="Prodotto Test",
            descrizione_breve="Descrizione breve",
            prezzo=10.00
        )
        annuncio = Annuncio.objects.create(
            inserzionista=venditore,
            prodotto=prodotto,
            qta_magazzino=5
        )
        
        # Crea un ordine
        ordine = Ordine.objects.create(
            utente=self.user,
            prodotto=prodotto,
            stato_consegna='da spedire'
        )
        
        # Testa l'annullamento da parte del compratore
        request = self.factory.post('/')
        request.user = self.user
        response = annulla_ordine_free(request, ordine.id) #type:ignore
        response_data = json.loads(response.content.decode())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response_data, {"status": "success"})
        
        ordine.refresh_from_db()
        self.assertEqual(ordine.stato_consegna, 'annullato')
        
        # Verifica che sia stata creata una notifica per il venditore
        self.assertTrue(Notification.objects.filter(
            recipient=venditore,
            title="Ordine annullato"
        ).exists())
        
        # Testa l'annullamento da parte del venditore
        ordine_venditore = Ordine.objects.create(
            utente=self.user,
            prodotto=prodotto,
            stato_consegna='da spedire'
        )
        request.user = venditore
        response = annulla_ordine_free(request, ordine_venditore.id) #type:ignore
        self.assertEqual(response.status_code, 200)
        
        # Verifica che sia stata creata una notifica per il compratore
        self.assertTrue(Notification.objects.filter(
            recipient=self.user,
            title="Ordine rifiutato"
        ).exists())
        
        # Testa il caso in cui l'ordine non esiste
        response = annulla_ordine_free(request, 9999)
        response_data = json.loads(response.content.decode())
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response_data, {
            "status": "error", 
            "message": "Ordine non trovato o già spedito"
        })
    
    def test_check_if_annuncio_is_valid(self):
        # Crea una richiesta POST valida
        post_data = {
            'nome': 'Prodotto Valido',
            'descrizione_breve': 'Descrizione breve valida',
            'prezzo': '10.00',
            'iva': '22',
            'tags': 'tag1,tag2',
            'qta_magazzino': '5',
            'condizione': 'nuovo'
        }
        
        # Crea un file immagine valido
        image = SimpleUploadedFile(
            name='test_image.jpg',
            content=b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x00\x00\x00\x21\xf9\x04\x01\x0a\x00\x01\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x4c\x01\x00\x3b',
            content_type='image/jpeg'
        )
        
        request = self.factory.post('/', post_data)
        request.FILES['immagini'] = image
        
        # Testa un annuncio valido
        result = check_if_annuncio_is_valid(request)
        self.assertIsNone(result)
        
        # Testa casi di errore
        test_cases = [
            ({'nome': ''}, {'notok': 'noval'}),  # Campo nome vuoto
            ({'nome': 'a'*201}, {'notok': 'lentxt'}),  # Nome troppo lungo
            ({'prezzo': 'abc'}, {'notok': 'prerr'}),  # Prezzo non numerico
            ({'prezzo': '-1'}, {'notok': 'price'}),  # Prezzo negativo
            ({'iva': '99'}, {'notok': 'cond'}),  # IVA non valida
            ({'qta_magazzino': 'abc'}, {'notok': 'qtaerr'}),  # Quantità non numerica
            ({'qta_magazzino': '-1'}, {'notok': 'qta'}),  # Quantità troppo bassa
            ({'tags': 'a'*51}, {'notok': 'tagchar'}),  # Tag troppo lungo
            ({'tags': ','.join(['tag']*51)}, {'notok': 'tagn'}),  # Troppi tag
            ({'condizione': 'non_valida'}, {'notok': 'cond'}),  # Condizione non valida
        ]
        
        for data, expected in test_cases:
            modified_data = post_data.copy()
            modified_data.update(data)
            request = self.factory.post('/', modified_data)
            request.FILES['immagini'] = image
            result = check_if_annuncio_is_valid(request)
            self.assertEqual(result, expected)
        
        # Testa errori nelle immagini
        invalid_image = SimpleUploadedFile(
            name='test_image.txt',
            content=b'Not an image',
            content_type='text/plain'
        )
        
        request = self.factory.post('/', post_data)
        request.FILES['immagini'] = invalid_image
        result = check_if_annuncio_is_valid(request)
        self.assertEqual(result, {'notok': 'imgtype'})
        
        # Testa troppe immagini (dovresti creare MAX_IMGS_PER_ANNU_VALUE + 1 immagini)
        # Questo dipende dalla tua implementazione specifica

class ViewTests(TestCase):
    def setUp(self):
        Annuncio.objects.all().delete()
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username='testuser', password='testpass123'
        )
        self.group = Group.objects.create(name='moderatori')
        self.client = Client()
        
        # Crea un prodotto e un annuncio per i test
        self.tag = Tag.objects.create(nome='test')
        self.prodotto = Prodotto.objects.create(
            nome="Prodotto Test",
            descrizione_breve="Descrizione breve",
            prezzo=10.00
        )
        self.prodotto.tags.add(self.tag)
        self.ann_uuid = uuid.uuid4()
        self.annuncio = Annuncio.objects.create(
            inserzionista=self.user,
            uuid=self.ann_uuid,
            prodotto=self.prodotto,
            qta_magazzino=5,
            is_published=True
        )
        
        # Crea un commento
        self.commento = CommentoAnnuncio.objects.create(
            annuncio=self.annuncio,
            utente=self.user,
            testo="Commento di test",
            rating=4
        )
        
        # Crea un ordine
        self.ordine = Ordine.objects.create(
            utente=self.user,
            prodotto=self.prodotto,
            stato_consegna='da spedire'
        )
    
    def test_home_page_view(self):
        response = self.client.get(reverse('sylvelius:home'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'sylvelius/home.html')
        self.assertIn('annunci', response.context)
        
        # Testa la paginazione
        for i in range(15):
            Prodotto.objects.create(
                nome=f"Prodotto {i}",
                descrizione_breve=f"Descrizione {i}",
                prezzo=10.00 + i
            )
            Annuncio.objects.create(
                inserzionista=self.user,
                prodotto=Prodotto.objects.last(),
                qta_magazzino=5,
                is_published=True
            )
        
        response = self.client.get(reverse('sylvelius:home') + '?page=2')
        self.assertEqual(response.status_code, 200)
    
    def test_registrazione_page_view(self):
        # Test GET
        response = self.client.get(reverse('sylvelius:register'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'sylvelius/register.html')
        
        # Test POST con dati validi
        response = self.client.post(reverse('sylvelius:register'), {
            'username': 'newuser',
            'password1': 'complexpassword123',
            'password2': 'complexpassword123'
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(username='newuser').exists())
        
        # Test POST con dati non validi
        response = self.client.post(reverse('sylvelius:register'), {
            'username': 'newuser',
            'password1': 'complexpassword123',
            'password2': 'differentpassword'
        })
        self.assertEqual(response.status_code, 302)  # Dovrebbe reindirizzare con errore
    
    def test_login_page_view(self):
        response = self.client.get(reverse('sylvelius:login'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'sylvelius/login.html')
        
        # Test login con credenziali valide
        response = self.client.post(reverse('sylvelius:login'), {
            'username': 'testuser',
            'password': 'testpass123'
        }, follow=True)
        self.assertTrue(response.context['user'].is_authenticated)
        self.client.logout()
        # Test login con credenziali non valide
        response = self.client.post(reverse('sylvelius:login'), {
            'username': 'testuser',
            'password': 'wrongpassword'
        })
        self.assertFalse(response.context['user'].is_authenticated)
    
    def test_logout_page_view(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('sylvelius:logout'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('sylvelius:home') + '?evento=logout')
    
    def test_profilo_page_view(self):
        # Test accesso non autenticato
        response = self.client.get(reverse('sylvelius:profile'))
        self.assertEqual(response.status_code, 302)  # Dovrebbe reindirizzare al login
        
        # Test accesso autenticato
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('sylvelius:profile'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'sylvelius/profile/profile.html')
        self.assertIn('user', response.context)
        self.assertIn('annunci', response.context)
        self.assertIn('ordini', response.context)
        
        # Test per moderatori
        moderator = User.objects.create_user(
            username='moderator', password='modpass123'
        )
        moderator_group = Group.objects.get(name='moderatori')
        moderator.groups.add(moderator_group)
        
        self.client.login(username='moderator', password='modpass123')
        response = self.client.get(reverse('sylvelius:profile'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('user_without_is_active', response.context)
    
    def test_annuncio_detail_view(self):
        url = reverse('sylvelius:dettagli_annuncio', args=[self.annuncio.uuid])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'sylvelius/annuncio/dettagli_annuncio.html')
        self.assertIn('annuncio', response.context)
        self.assertIn('commenti', response.context)
        
        # Testa il contesto per un utente autenticato
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(url)
        self.assertIn('ha_acquistato', response.context)
        self.assertIn('non_ha_commentato', response.context)
    
    def test_profilo_ordini_page_view(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('sylvelius:profile_ordini'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'sylvelius/profile/profile_ordini.html')
        self.assertIn('ordini', response.context)
        
        # Testa la paginazione
        for i in range(25):
            prodotto = Prodotto.objects.create(
                nome=f"Prodotto Ordine {i}",
                descrizione_breve=f"Descrizione {i}",
                prezzo=10.00 + i
            )
            Ordine.objects.create(
                utente=self.user,
                prodotto=prodotto
            )
        
        response = self.client.get(reverse('sylvelius:profile_ordini') + '?page=2')
        self.assertEqual(response.status_code, 200)
    
    def test_profilo_annunci_page_view(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('sylvelius:profile_annunci'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'sylvelius/profile/profile_annunci.html')
        self.assertIn('annunci', response.context)
        
        # Testa la paginazione
        for i in range(25):
            prodotto = Prodotto.objects.create(
                nome=f"Prodotto Annuncio {i}",
                descrizione_breve=f"Descrizione {i}",
                prezzo=10.00 + i
            )
            Annuncio.objects.create(
                inserzionista=self.user,
                prodotto=prodotto,
                qta_magazzino=5
            )
        
        response = self.client.get(reverse('sylvelius:profile_annunci') + '?page=2')
        self.assertEqual(response.status_code, 200)
    
    def test_ricerca_annunci_view(self):
        response = self.client.get(reverse('sylvelius:ricerca_annunci'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'sylvelius/ricerca.html')
        self.assertIn('annunci', response.context)
        
        # Testa la ricerca con parametri
        test_cases = [
            ({'q': 'Test'}, 1),  # Ricerca per testo
            ({'categoria': 'test'}, 1),  # Ricerca per categoria
            ({'prezzo_min': '5'}, 1),  # Prezzo minimo
            ({'prezzo_max': '15'}, 1),  # Prezzo massimo
            ({'sort': 'prezzo-asc'}, 1),  # Ordinamento
            ({'condition': 'nuovo'}, 1),  # Condizione
            ({'rating': '4'}, 1),  # Rating
            ({'qta_mag': 'qta-pres'}, 1)  # Quantità in magazzino
        ]
        
        for params, expected_count in test_cases:
            response = self.client.get(reverse('sylvelius:ricerca_annunci'), params)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(response.context['annunci']), expected_count)

class FunctionBasedViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username='testuser', password='testpass123'
        )
        self.groups = Group.objects.create(name='moderatori')
        self.client = Client()
        
        # Crea un prodotto e un annuncio per i test
        self.prodotto = Prodotto.objects.create(
            nome="Prodotto Test",
            descrizione_breve="Descrizione breve",
            prezzo=10.00
        )
        self.annuncio = Annuncio.objects.create(
            inserzionista=self.user,
            prodotto=self.prodotto,
            qta_magazzino=5,
            is_published=True
        )
        
        # Crea un commento
        self.commento = CommentoAnnuncio.objects.create(
            annuncio=self.annuncio,
            utente=self.user,
            testo="Commento di test",
            rating=4
        )
        
        # Crea un ordine
        self.ordine = Ordine.objects.create(
            utente=self.user,
            prodotto=self.prodotto,
            stato_consegna='da spedire'
        )
    
    def test_toggle_pubblicazione(self):
        self.client.login(username='testuser', password='testpass123')
        
        # Testa la disattivazione
        response = self.client.post(
            reverse('sylvelius:nascondi_annuncio', args=[self.annuncio.id]), #type:ignore
            HTTP_REFERER=reverse('sylvelius:profile_annunci')
        )
        self.assertEqual(response.status_code, 302)
        self.annuncio.refresh_from_db()
        self.assertFalse(self.annuncio.is_published)
        
        # Testa la riattivazione
        response = self.client.post(
            reverse('sylvelius:nascondi_annuncio', args=[self.annuncio.id]), #type:ignore
            HTTP_REFERER=reverse('sylvelius:profile_annunci')
        )
        self.assertEqual(response.status_code, 302)
        self.annuncio.refresh_from_db()
        self.assertTrue(self.annuncio.is_published)
    
    def test_delete_pubblicazione(self):
        self.client.login(username='testuser', password='testpass123')
        
        # Crea un annuncio da eliminare
        prodotto = Prodotto.objects.create(
            nome="Prodotto da eliminare",
            descrizione_breve="Descrizione",
            prezzo=10.00
        )
        annuncio = Annuncio.objects.create(
            inserzionista=self.user,
            prodotto=prodotto,
            qta_magazzino=5
        )
        
        response = self.client.post(
            reverse('sylvelius:elimina_annuncio', args=[annuncio.id]), #type:ignore
            HTTP_REFERER=reverse('sylvelius:profile_annunci')
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Annuncio.objects.filter(id=annuncio.id).exists()) #type:ignore
    
    def test_check_old_password(self):
        self.client.login(username='testuser', password='testpass123')
        
        # Password corretta
        response = self.client.post(
            reverse('sylvelius:check_old_password'),
            data=json.dumps({'old_password': 'testpass123'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['valid'])
        
        # Password errata
        response = self.client.post(
            reverse('sylvelius:check_old_password'),
            data=json.dumps({'old_password': 'wrongpassword'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['valid'])
    
    def test_check_username_exists(self):
        # Username esistente
        response = self.client.post(
            reverse('sylvelius:check_username_exists'),
            data=json.dumps({'username': 'testuser'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['exists'])
        
        # Username non esistente
        response = self.client.post(
            reverse('sylvelius:check_username_exists'),
            data=json.dumps({'username': 'nonexistentuser'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['exists'])
    
    def test_check_login_credentials(self):
        # Credenziali corrette
        response = self.client.post(
            reverse('sylvelius:check_login_credentials'),
            data=json.dumps({
                'username': 'testuser',
                'password': 'testpass123'
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['exists'])
        self.assertTrue(response.json()['valid_password'])
        self.assertTrue(response.json()['is_active'])
        
        # Password errata
        response = self.client.post(
            reverse('sylvelius:check_login_credentials'),
            data=json.dumps({
                'username': 'testuser',
                'password': 'wrongpassword'
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['exists'])
        self.assertFalse(response.json()['valid_password'])
        
        # Utente non esistente
        response = self.client.post(
            reverse('sylvelius:check_login_credentials'),
            data=json.dumps({
                'username': 'nonexistent',
                'password': 'whatever'
            }),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['exists'])
    
    def test_aggiungi_commento(self):
        self.client.login(username='testuser', password='testpass123')
        
        # Testa l'aggiunta di un commento valido
        response = self.client.post(
            reverse('sylvelius:aggiungi_commento', args=[self.annuncio.id]), #type:ignore
            {
                'testo': 'Nuovo commento',
                'rating': '5'
            },
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "success"})
        self.assertTrue(CommentoAnnuncio.objects.filter(
            annuncio=self.annuncio,
            testo='Nuovo commento'
        ).exists())
        
        # Testa l'aggiunta con dati non validi
        response = self.client.post(
            reverse('sylvelius:aggiungi_commento', args=[self.annuncio.id]), #type:ignore
            {
                'testo': '',  # Testo vuoto
                'rating': '6'  # Rating fuori range
            },
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 400)
    
    def test_modifica_commento(self):
        self.client.login(username='testuser', password='testpass123')
        
        # Testa la modifica di un commento valido
        response = self.client.post(
            reverse('sylvelius:modifica_commento', args=[self.commento.id]), #type:ignore
            {
                'testo': 'Commento modificato',
                'rating': '3'
            },
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "success"})
        self.commento.refresh_from_db()
        self.assertEqual(self.commento.testo, 'Commento modificato')
        self.assertEqual(self.commento.rating, 3)
        
        # Testa la modifica con dati non validi
        response = self.client.post(
            reverse('sylvelius:modifica_commento', args=[self.commento.id]), #type:ignore
            {
                'testo': '',  # Testo vuoto
                'rating': '6'  # Rating fuori range
            },
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 400)
    
    def test_elimina_commento(self):
        self.client.login(username='testuser', password='testpass123')
        
        # Testa l'eliminazione da parte dell'utente
        commento = CommentoAnnuncio.objects.create(
            annuncio=self.annuncio,
            utente=self.user,
            testo="Commento da eliminare",
            rating=4
        )
        
        response = self.client.post(
            reverse('sylvelius:elimina_commento', args=[commento.id]), #type:ignore
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "success"})
        self.assertFalse(CommentoAnnuncio.objects.filter(id=commento.id).exists()) #type:ignore
    
    def test_espelli_utente(self):
        # Crea un moderatore
        moderator = User.objects.create_user(
            username='moderator', password='modpass123'
        )
        moderator_group = Group.objects.get(name='moderatori')
        moderator.groups.add(moderator_group)
        
        self.client.login(username='moderator', password='modpass123')
        
        # Crea un utente da bannare
        user_to_ban = User.objects.create_user(
            username='usertoban', password='testpass123'
        )
        
        # Testa il ban
        response = self.client.post(
            reverse('sylvelius:espelli_utente', args=['ban', user_to_ban.id]) #type:ignore
        )
        self.assertEqual(response.status_code, 302)
        user_to_ban.refresh_from_db()
        self.assertFalse(user_to_ban.is_active)
        
        # Testa lo sban
        response = self.client.post(
            reverse('sylvelius:espelli_utente', args=['unban', user_to_ban.id]) #type:ignore
        )
        self.assertEqual(response.status_code, 302)
        user_to_ban.refresh_from_db()
        self.assertTrue(user_to_ban.is_active)
        
        # Testa che un utente normale non possa bannare
        normal_user = User.objects.create_user(
            username='normaluser', password='testpass123'
        )
        self.client.login(username='normaluser', password='testpass123')
        response = self.client.post(
            reverse('sylvelius:espelli_utente', args=['ban', user_to_ban.id]) #type:ignore
        )
        self.assertEqual(response.status_code, 403)
    
    def test_formatta_utente(self):
        # Crea un moderatore
        moderator = User.objects.create_user(
            username='moderator', password='modpass123'
        )
        moderator_group = Group.objects.get(name='moderatori')
        moderator.groups.add(moderator_group)
        
        self.client.login(username='moderator', password='modpass123')
        
        # Crea un utente bannato con dati da formattare
        banned_user = User.objects.create_user(
            username='banneduser', password='testpass123',
            is_active=False
        )
        
        # Crea dati associati all'utente
        prodotto = Prodotto.objects.create(
            nome="Prodotto Bannato",
            descrizione_breve="Descrizione",
            prezzo=10.00
        )
        annuncio = Annuncio.objects.create(
            inserzionista=banned_user,
            prodotto=prodotto,
            qta_magazzino=5
        )
        commento = CommentoAnnuncio.objects.create(
            annuncio=self.annuncio,
            utente=banned_user,
            testo="Commento bannato",
            rating=2
        )
        ordine = Ordine.objects.create(
            utente=banned_user,
            prodotto=self.prodotto,
            stato_consegna='da spedire'
        )
        
        # Testa la formattazione
        response = self.client.post(
            reverse('sylvelius:formatta_utente', args=[banned_user.id]) #type:ignore
        )
        self.assertEqual(response.status_code, 302)
        
        # Verifica che i dati siano stati eliminati
        self.assertFalse(Annuncio.objects.filter(inserzionista=banned_user).exists())
        self.assertFalse(CommentoAnnuncio.objects.filter(utente=banned_user).exists())
        self.assertFalse(Ordine.objects.filter(utente=banned_user).exists())
        
        # Testa che non si possa formattare un utente non bannato
        active_user = User.objects.create_user(
            username='activeuser', password='testpass123'
        )
        response = self.client.post(
            reverse('sylvelius:formatta_utente', args=[active_user.id]) #type:ignore
        )
        self.assertEqual(response.status_code, 403)
        
        # Testa che un utente normale non possa formattare
        normal_user = User.objects.create_user(
            username='normaluser', password='testpass123'
        )
        self.client.login(username='normaluser', password='testpass123')
        response = self.client.post(
            reverse('sylvelius:formatta_utente', args=[banned_user.id]) #type:ignore
        )
        self.assertEqual(response.status_code, 403)

class AnnuncioCreationTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username='testuser', password='testpass123'
        )
        self.client = Client()
        
        # Configurazione per i test con immagini
        self.temp_media_dir = tempfile.mkdtemp()
        settings.MEDIA_ROOT = self.temp_media_dir
        
        # Immagine valida per i test
        self.valid_image = SimpleUploadedFile(
            name='test_image.jpg',
            content=b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x00\x00\x00\x21\xf9\x04\x01\x0a\x00\x01\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x4c\x01\x00\x3b',
            content_type='image/jpeg'
        )
    
    def tearDown(self):
        shutil.rmtree(self.temp_media_dir)
    
    def test_profilo_crea_annuncio_page_view_get(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('sylvelius:crea_annuncio'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'sylvelius/annuncio/crea_annuncio.html')
    
    def test_profilo_crea_annuncio_page_view_post_valid(self):
        self.client.login(username='testuser', password='testpass123')
        
        post_data = {
            'nome': 'Nuovo Prodotto',
            'descrizione_breve': 'Descrizione breve',
            'descrizione': 'Descrizione completa',
            'prezzo': '19.99',
            'iva': '22',
            'tags': 'tag1,tag2,tag3',
            'qta_magazzino': '10',
            'condizione': 'nuovo'
        }
        
        response = self.client.post(
            reverse('sylvelius:crea_annuncio'),
            data={**post_data, 'immagini': self.valid_image},
            format='multipart'
        )
        
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('sylvelius:home') + '?evento=crea_annuncio')
        
        # Verifica che l'annuncio sia stato creato
        self.assertTrue(Annuncio.objects.filter(prodotto__nome='Nuovo Prodotto').exists())
        annuncio = Annuncio.objects.get(prodotto__nome='Nuovo Prodotto')
        self.assertEqual(annuncio.inserzionista, self.user)
        self.assertEqual(annuncio.qta_magazzino, 10)
        
        # Verifica che il prodotto sia stato creato
        prodotto = annuncio.prodotto
        self.assertEqual(prodotto.descrizione_breve, 'Descrizione breve')
        self.assertEqual(prodotto.prezzo, Decimal('19.99'))
        self.assertEqual(prodotto.iva, 22)
        
        # Verifica che i tag siano stati creati
        self.assertEqual(prodotto.tags.count(), 3)
        
        # Verifica che l'immagine sia stata salvata
        self.assertEqual(ImmagineProdotto.objects.filter(prodotto=prodotto).count(), 1)
    
    def test_profilo_crea_annuncio_page_view_post_invalid(self):
        self.client.login(username='testuser', password='testpass123')
        
        # Testa con dati non validi
        invalid_cases = [
            ({'nome': ''}, 'noval'),  # Nome vuoto
            ({'nome': 'a'*201}, 'lentxt'),  # Nome troppo lungo
            ({'prezzo': 'abc'}, 'prerr'),  # Prezzo non numerico
            ({'prezzo': '-1'}, 'price'),  # Prezzo negativo
            ({'iva': '99'}, 'cond'),  # IVA non valida
            ({'qta_magazzino': 'abc'}, 'qtaerr'),  # Quantità non numerica
            ({'qta_magazzino': '-1'}, 'qta'),  # Quantità troppo bassa
            ({'tags': 'a'*51}, 'tagchar'),  # Tag troppo lungo
            ({'tags': ','.join(['tag']*51)}, 'tagn'),  # Troppi tag
            ({'condizione': 'non_valida'}, 'cond'),  # Condizione non valida
        ]
        
        for data, error_code in invalid_cases:
            post_data = {
                'nome': 'Prodotto Valido',
                'descrizione_breve': 'Descrizione breve',
                'prezzo': '10.00',
                'iva': '22',
                'tags': 'tag1,tag2',
                'qta_magazzino': '5',
                'condizione': 'nuovo'
            }
            post_data.update(data)
            
            response = self.client.post(
                reverse('sylvelius:crea_annuncio'),
                data={**post_data, 'immagini': self.valid_image},
                format='multipart'
            )
            
            self.assertEqual(response.status_code, 200)
            self.assertIn(error_code, response.context['notok'])
    
    def test_profilo_modifica_annuncio_page_view_get(self):
        self.client.login(username='testuser', password='testpass123')
        
        # Crea un annuncio da modificare
        prodotto = Prodotto.objects.create(
            nome="Prodotto Originale",
            descrizione_breve="Descrizione originale",
            descrizione="Descrizione lunga originale",
            prezzo=15.00,
            iva=10,
            condizione='usato'
        )
        annuncio = Annuncio.objects.create(
            inserzionista=self.user,
            prodotto=prodotto,
            qta_magazzino=3
        )
        
        # Aggiungi alcuni tag
        tag1 = Tag.objects.create(nome='tag1')
        tag2 = Tag.objects.create(nome='tag2')
        prodotto.tags.add(tag1, tag2)
        
        response = self.client.get(
            reverse('sylvelius:modifica_annuncio', args=[annuncio.id]) #type:ignore
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'sylvelius/annuncio/modifica_annuncio.html')
        
        # Verifica che i dati dell'annuncio siano nel contesto
        self.assertEqual(response.context['titolo_mod'], 'Prodotto Originale')
        self.assertEqual(response.context['desc_br_mod'], 'Descrizione originale')
        self.assertEqual(response.context['tags_mod'], ['tag1', 'tag2'])
    
    def test_profilo_modifica_annuncio_page_view_post_valid(self):
        self.client.login(username='testuser', password='testpass123')
        
        # Crea un annuncio da modificare
        prodotto = Prodotto.objects.create(
            nome="Prodotto Originale",
            descrizione_breve="Descrizione originale",
            descrizione="Descrizione lunga originale",
            prezzo=15.00,
            iva=10,
            condizione='usato'
        )
        annuncio = Annuncio.objects.create(
            inserzionista=self.user,
            prodotto=prodotto,
            qta_magazzino=3
        )
        
        # Aggiungi alcuni tag
        tag1 = Tag.objects.create(nome='tag1')
        tag2 = Tag.objects.create(nome='tag2')
        prodotto.tags.add(tag1, tag2)
        
        # Dati per la modifica
        post_data = {
            'nome': 'Prodotto Modificato',
            'descrizione_breve': 'Descrizione breve modificata',
            'descrizione': 'Descrizione lunga modificata',
            'prezzo': '25.00',
            'iva': '22',
            'tags': 'newtag1,newtag2,newtag3',
            'qta_magazzino': '7',
            'condizione': 'nuovo'
        }
        
        response = self.client.post(
            reverse('sylvelius:modifica_annuncio', args=[annuncio.id]), #type:ignore
            data={**post_data, 'immagini': self.valid_image},
            format='multipart',
            follow=True
        )
        self.assertEqual(response.status_code, 200)
        
        # Verifica che l'annuncio sia stato modificato
        annuncio.refresh_from_db()
        prodotto.refresh_from_db()
        
        self.assertEqual(prodotto.nome, 'Prodotto Modificato')
        self.assertEqual(prodotto.descrizione_breve, 'Descrizione breve modificata')
        self.assertEqual(prodotto.prezzo, 25.00)
        self.assertEqual(prodotto.iva, 22)
        self.assertEqual(prodotto.condizione, 'nuovo')
        self.assertEqual(annuncio.qta_magazzino, 7)
        
        # Verifica che i tag siano stati aggiornati
        self.assertEqual(prodotto.tags.count(), 3)
        tag_names = [tag.nome for tag in prodotto.tags.all()]
        self.assertIn('newtag1', tag_names)
        self.assertIn('newtag2', tag_names)
        self.assertIn('newtag3', tag_names)
    
    def test_profilo_modifica_annuncio_page_view_post_invalid(self):
        self.client.login(username='testuser', password='testpass123')
        
        # Crea un annuncio da modificare
        prodotto = Prodotto.objects.create(
            nome="Prodotto Originale",
            descrizione_breve="Descrizione originale",
            prezzo=15.00,
            iva=10
        )
        annuncio = Annuncio.objects.create(
            inserzionista=self.user,
            prodotto=prodotto,
            qta_magazzino=3
        )
        
        # Testa con dati non validi
        invalid_cases = [
            ({'nome': ''}, 'noval'),  # Nome vuoto
            ({'nome': 'a'*201}, 'lentxt'),  # Nome troppo lungo
            ({'prezzo': 'abc'}, 'prerr'),  # Prezzo non numerico
            ({'prezzo': '-1'}, 'price'),  # Prezzo negativo
            ({'iva': '99'}, 'cond'),  # IVA non valida
            ({'qta_magazzino': 'abc'}, 'qtaerr'),  # Quantità non numerica
            ({'qta_magazzino': '-1'}, 'qta'),  # Quantità troppo bassa
            ({'tags': 'a'*51}, 'tagchar'),  # Tag troppo lungo
            ({'tags': ','.join(['tag']*51)}, 'tagn'),  # Troppi tag
            ({'condizione': 'non_valida'}, 'cond'),  # Condizione non valida
        ]
        
        for data, error_code in invalid_cases:
            post_data = {
                'nome': 'Prodotto Valido',
                'descrizione_breve': 'Descrizione breve',
                'prezzo': '10.00',
                'iva': '22',
                'tags': 'tag1,tag2',
                'qta_magazzino': '5',
                'condizione': 'nuovo'
            }
            post_data.update(data)
            
            response = self.client.post(
                reverse('sylvelius:modifica_annuncio', args=[annuncio.id]), #type:ignore
                data={**post_data, 'immagini': self.valid_image},
                format='multipart'
            )
            self.assertEqual(response.status_code, 200)
            self.assertIn(error_code, response.context['notok'])

