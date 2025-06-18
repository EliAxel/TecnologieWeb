# Django imports
from django.test import TestCase, RequestFactory, Client
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User, Group,AnonymousUser
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.core.exceptions import PermissionDenied

# Standard library imports
import tempfile
import shutil
import json
import uuid
from decimal import Decimal
from unittest.mock import patch

from django.views import View

# Local imports
from .models import (
    Annuncio, CommentoAnnuncio, ImmagineProdotto,
    Ordine, Tag, Prodotto, Notification
)
from .views import (
    RicercaAnnunciView, send_notification, 
    mark_notifications_read, create_notification, annulla_ordine_free, 
    check_if_annuncio_is_valid, annulla_ordine
)
from .api_views import notifications_api
from sylvelius.forms import CustomUserCreationForm
from progetto_tw.mixins import ModeratoreAccessForbiddenMixin
from purchase.models import Invoice
from progetto_tw.t_ests_constants import NEXT_PROD_ID
from progetto_tw.constants import (
    MAX_UNAME_CHARS, 
    MAX_PWD_CHARS,
    MAX_PAGINATOR_RICERCA_VALUE
)
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
        self.user = User.objects.create_user(username='testuser', password='Testpass0')
        self.group, created = Group.objects.get_or_create(name='moderatori')
        self.user.groups.add(self.group)
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

    def test_api_notifications(self):
        Notification.objects.create(
            recipient=self.user,
            title='title',
            message='message',
            is_global=True,
            read=False
        )
        response = self.client.get(reverse('sylvelius:notifications_api'))
        self.assertEqual(response.status_code,200)
        response_data = json.loads(response.content.decode())[0]
        self.assertEqual(response_data['title'], 'title')
        self.assertEqual(response_data['message'], 'message')
        self.assertEqual(response_data['read'], False)

        self.client.logout()
        response = self.client.get(reverse('sylvelius:notifications_api'))
        self.assertEqual(response.status_code,200)
        response_data = json.loads(response.content.decode())
        self.assertEqual(response_data, [])

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

        response = send_notification(title="Test", message="User message")
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
        user2 = User.objects.create_user(
            username='user2', password='testpass123'
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
        
        request.user = user2
        response = annulla_ordine_free(request, ordine_venditore.id) #type:ignore
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
        
        request = self.factory.post('/', data={**post_data, 'immagini': [image]*11})
        result = check_if_annuncio_is_valid(request)
        self.assertEqual(result, {'notok': 'imgn'})

        image3x1 = SimpleUploadedFile(
            name='test_image.jpg',
            content=(
                b'\x47\x49\x46\x38\x39\x61\x03\x00\x01\x00\x80\x00\x00'
                b'\x00\x00\x00\xff\xff\xff\x21\xf9\x04\x00\x00\x00\x00\x00'
                b'\x2c\x00\x00\x00\x00\x03\x00\x01\x00\x00\x02\x02\x4c\x01\x00\x3b'
            ),
            content_type='image/jpeg'
        )

        request = self.factory.post('/', post_data)
        request.FILES['immagini'] = image3x1
        result = check_if_annuncio_is_valid(request)
        self.assertEqual(result, {'notok': 'imgproportion'})

        imagehuge = SimpleUploadedFile(
            name='test_image.jpg',
            content=(
                b'\x47\x49\x46\x38\x39\x61\x03\x00\x01\x00\x80\x00\x00'
                b'\x00\x00\x00\xff\xff\xff\x21\xf9\x04\x00\x00\x00\x00\x00'
                b'\x2c\x00\x00\x00\x00\x03\x00\x01\x00\x00\x02\x02\x4c\x01\x00\x3b'
            ) + b'\x00' * (5 * 1024 * 1024),
            content_type='image/jpeg'
        )

        request = self.factory.post('/', post_data)
        request.FILES['immagini'] = imagehuge
        result = check_if_annuncio_is_valid(request)
        self.assertEqual(result, {'notok': 'imgsize'})


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

        self.ordine2 = Ordine.objects.create(
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
        response = self.client.get(reverse('sylvelius:home') + '?page=0')
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse('sylvelius:home') + '?page=err')
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

    def test_profilo_delete_page_view(self):
        self.client.login(username='testuser', password='testpass123')
        
        # Test GET request
        response = self.client.get(reverse('sylvelius:profile_delete'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'sylvelius/profile/profile_delete.html')
        self.assertEqual(response.context['user'], self.user)
        
        # Test case 1: No orders - should delete successfully
        response = self.client.post(reverse('sylvelius:profile_delete'))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(User.objects.filter(username='testuser').exists())
        
        # Recreate user and product for next tests
        self.user = User.objects.create_user(
            username='testuser', password='testpass123'
        )
        self.prodotto = Prodotto.objects.create(
            nome="Test Product",
            descrizione_breve="Test description",
            prezzo=10.00
        )
        Annuncio.objects.create(
            inserzionista=self.user,
            uuid=uuid.uuid4(),
            prodotto=self.prodotto,
            qta_magazzino=5,
            is_published=True
        )
        self.client.login(username='testuser', password='testpass123')
        
        # Test case 2: User has "da spedire" orders as buyer and seller
        order_as_buyer = Ordine.objects.create(
            utente=self.user,
            prodotto=self.prodotto,
            stato_consegna='da spedire'
        )
        
        another_user = User.objects.create_user(
            username='anotheruser', password='testpass123'
        )
        another_product = Prodotto.objects.create(
            nome="Another Product",
            descrizione_breve="Descrizione breve",
            prezzo=20.00
        )
        Annuncio.objects.create(
            inserzionista=self.user,
            uuid=uuid.uuid4(),
            prodotto=another_product,
            qta_magazzino=3,
            is_published=True
        )
        order_as_seller = Ordine.objects.create(
            utente=another_user,
            prodotto=another_product,
            stato_consegna='da spedire'
        )
        
        response = self.client.post(reverse('sylvelius:profile_delete'))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(User.objects.filter(username='testuser').exists())
        
        # Recreate user and product for next tests
        self.user = User.objects.create_user(
            username='testuser', password='testpass123'
        )
        self.prodotto = Prodotto.objects.create(
            nome="Test Product",
            descrizione_breve="Test description",
            prezzo=10.00
        )
        Annuncio.objects.create(
            inserzionista=self.user,
            uuid=uuid.uuid4(),
            prodotto=self.prodotto,
            qta_magazzino=5,
            is_published=True
        )
        self.client.login(username='testuser', password='testpass123')
        
        # Test case 3: User has "spedito" order as buyer - should prevent deletion
        Ordine.objects.create(
            utente=self.user,
            prodotto=self.prodotto,
            stato_consegna='spedito'
        )
        response = self.client.post(reverse('sylvelius:profile_delete'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'sylvelius/profile/profile_delete.html')
        self.assertIn('err', response.context)
        self.assertEqual(response.context['err'], 'ship')
        self.assertTrue(User.objects.filter(username='testuser').exists())
        
        # Test case 4: User has "spedito" order as seller - should prevent deletion
        Ordine.objects.all().delete()  # Clear previous orders
        another_product = Prodotto.objects.create(
            nome="Another Product",
            descrizione_breve="Descrizione breve",
            prezzo=20.00
        )
        Annuncio.objects.create(
            inserzionista=self.user,
            uuid=uuid.uuid4(),
            prodotto=another_product,
            qta_magazzino=3,
            is_published=True
        )
        Ordine.objects.create(
            utente=another_user,
            prodotto=another_product,
            stato_consegna='spedito'
        )
        response = self.client.post(reverse('sylvelius:profile_delete'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'sylvelius/profile/profile_delete.html')
        self.assertIn('err', response.context)
        self.assertEqual(response.context['err'], 'shipd')
        self.assertTrue(User.objects.filter(username='testuser').exists())

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
            uuid=uuid.uuid4(),
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
        # Test per utente normale che elimina il proprio annuncio
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
        
        # Test per moderatore che elimina un annuncio
        # Crea un utente moderatore
        moderator = User.objects.create_user(username='moderator', password='modpass123')
        moderator.groups.add(self.groups)
        
        # Crea un annuncio di un altro utente
        another_user = User.objects.create_user(username='anotheruser', password='testpass123')
        another_prodotto = Prodotto.objects.create(
            nome="Prodotto di altro utente",
            descrizione_breve="Descrizione",
            prezzo=15.00
        )
        another_annuncio = Annuncio.objects.create(
            inserzionista=another_user,
            prodotto=another_prodotto,
            qta_magazzino=3
        )
        
        # Login come moderatore
        self.client.login(username='moderator', password='modpass123')
        
        response = self.client.post(
            reverse('sylvelius:elimina_annuncio', args=[another_annuncio.id]), #type:ignore
            HTTP_REFERER=reverse('sylvelius:home')
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Annuncio.objects.filter(id=another_annuncio.id).exists()) #type:ignore
        self.assertRedirects(response, f'{reverse("sylvelius:home")}?evento=elimina_pub')

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

        response = self.client.post(
            reverse('sylvelius:aggiungi_commento', args=[self.annuncio.id]), #type:ignore
            {
                'testo': 'Nuovo commento',
                'rating': '5'
            },
            HTTP_X_REQUESTED_WITH='err',follow=True
        )
        self.assertEqual(response.status_code, 200)

        response = self.client.post(
            reverse('sylvelius:aggiungi_commento', args=[self.annuncio.id]), #type:ignore
            {
                'testo': '',  # Testo vuoto
                'rating': '6'  # Rating fuori range
            },
            HTTP_X_REQUESTED_WITH='err',follow=True
        )
        self.assertEqual(response.status_code, 200)
    
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

        response = self.client.post(
            reverse('sylvelius:modifica_commento', args=[self.commento.id]), #type:ignore
            {
                'testo': 'Nuovo commento',
                'rating': '5'
            },
            HTTP_X_REQUESTED_WITH='err',follow=True
        )
        self.assertEqual(response.status_code, 200)

        response = self.client.post(
            reverse('sylvelius:modifica_commento', args=[self.commento.id]), #type:ignore
            {
                'testo': '',  # Testo vuoto
                'rating': '6'  # Rating fuori range
            },
            HTTP_X_REQUESTED_WITH='err',follow=True
        )
        self.assertEqual(response.status_code, 200)
    
    def test_elimina_commento(self):
        self.client.login(username='testuser', password='testpass123')
        
        # Test deletion by regular user
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

    def test_elimina_commento_moderatore(self):
        # Create a moderator user and group
        moderator_user = User.objects.create_user(
            username='moderator',
            password='modpass123'
        )
        moderator_user.groups.add(self.groups)
        
        # Create a comment by another user
        commento = CommentoAnnuncio.objects.create(
            annuncio=self.annuncio,
            utente=self.user,  # different user from moderator
            testo="Commento da eliminare da moderatore",
            rating=4
        )
        
        # Login as moderator
        self.client.login(username='moderator', password='modpass123')
        
        # Test deletion by moderator
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
        User.objects.create_user(
            username='user2', password='modpass123'
        )
        self.client.login(username='user2', password='modpass123')
        response = self.client.post(
                reverse('sylvelius:formatta_utente', args=[1234]) #type:ignore
            )
        self.assertEqual(response.status_code, 403)
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
        
        # Crea un utente acquirente
        buyer = User.objects.create_user(
            username='buyer', password='testpass123'
        )
        
        # Crea ordini associati all'utente bannato (sia come inserzionista che come acquirente)
        ordine_inserzionista = Ordine.objects.create(
            utente=buyer,
            prodotto=prodotto,
            stato_consegna='da spedire'
        )
        ordine_utente = Ordine.objects.create(
            utente=banned_user,
            prodotto=self.prodotto,
            stato_consegna='da spedire'
        )
        
        # Mock della funzione annulla_ordine_free
        with patch('sylvelius.views.annulla_ordine_free') as mock_annulla:
            # Testa la formattazione
            banned_user.is_active = True
            banned_user.save()
            response = self.client.post(
                reverse('sylvelius:formatta_utente', args=[banned_user.id]) #type:ignore
            )
            self.assertEqual(response.status_code, 403)
            banned_user.is_active = False
            banned_user.save()
            response = self.client.post(
                reverse('sylvelius:formatta_utente', args=[banned_user.id]) #type:ignore
            )
            self.assertEqual(response.status_code, 302)
            
            # Ottieni la request passata alla funzione mock
            args, _ = mock_annulla.call_args_list[0]
            request_passed = args[0]
            ordine_id_passed = args[1]
            
            # Verifica che la request sia corretta e che l'ID ordine sia quello atteso
            self.assertEqual(request_passed.user, moderator)
            self.assertEqual(ordine_id_passed, ordine_inserzionista.id)#type:ignore
            
            # Verifica il secondo ordine
            args, _ = mock_annulla.call_args_list[1]
            request_passed = args[0]
            ordine_id_passed = args[1]
            
            self.assertEqual(request_passed.user, moderator)
            self.assertEqual(ordine_id_passed, ordine_utente.id)#type:ignore
            
            # Verifica che i dati siano stati eliminati
            self.assertFalse(Annuncio.objects.filter(inserzionista=banned_user).exists())
            self.assertFalse(CommentoAnnuncio.objects.filter(utente=banned_user).exists())
            self.assertFalse(Ordine.objects.filter(utente=banned_user).exists())
            self.assertFalse(Ordine.objects.filter(prodotto__annunci__inserzionista=banned_user).exists())
    @patch('sylvelius.views.annulla_ordine_free')
    def test_annulla_ordine(self, mock_annulla_ordine_free):
        # Configure the mock to return a JsonResponse
        mock_annulla_ordine_free.return_value = JsonResponse({"status": "success"})
        
        request = self.factory.post('/')
        request.user = self.user
        prodotto = Prodotto.objects.create(
            nome="Prodotto Test",
            descrizione_breve="Descrizione breve",
            prezzo=10.00
        )        
        # Crea un ordine
        ordine = Ordine.objects.create(
            utente=self.user,
            prodotto=prodotto,
            stato_consegna='da spedire'
        )
        response = annulla_ordine(request, ordine.id) #type:ignore

        self.assertEqual(response.status_code, 200)
        # You might also want to verify the mock was called
        mock_annulla_ordine_free.assert_called_once_with(request, ordine.id)#type:ignore

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

        response = self.client.post(
            reverse('sylvelius:modifica_annuncio', args=[annuncio.id]), #type:ignore
            data=post_data,
            follow=True
        )
        self.assertEqual(response.status_code, 200)
    
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

class ProfiloEditTests(TestCase):

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
 
    def test_profilo_edit_page_view_get(self):
        # Test GET request usando Client invece di RequestFactory
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('sylvelius:profile_edit'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'sylvelius/profile/profile_edit.html')

    def test_profilo_edit_page_view_post_valid_username(self):
        # Test POST request con solo cambio username valido
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('sylvelius:profile_edit'), {
            'username': 'newusername',
            'old_password': 'testpass123',
            'new_password1': '',
            'new_password2': ''
        })
        self.assertEqual(response.status_code, 302)  # Redirect dopo successo
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, 'newusername')

    def test_profilo_edit_page_view_post_valid_password(self):
        # Test POST request con cambio password valido
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('sylvelius:profile_edit'), {
            'username': 'testuser',
            'old_password': 'testpass123',
            'new_password1': 'newpass123',
            'new_password2': 'newpass123'
        })
        self.assertEqual(response.status_code, 302)  # Redirect dopo successo
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('newpass123'))

    def test_profilo_edit_page_view_post_wrong_old_password(self):
        # Test POST request con vecchia password errata
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('sylvelius:profile_edit'), {
            'username': 'testuser',
            'old_password': 'wrongpass',
            'new_password1': 'newpass123',
            'new_password2': 'newpass123'
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('pwd', response.context)
        self.assertEqual(response.context['pwd'], 'bad')

    def test_profilo_edit_page_view_post_missing_old_password(self):
        # Test POST request senza vecchia password
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('sylvelius:profile_edit'), {
            'username': 'testuser',
            'old_password': '',
            'new_password1': 'newpass123',
            'new_password2': 'newpass123'
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('pwd', response.context)
        self.assertEqual(response.context['pwd'], 'bad')

    def test_profilo_edit_page_view_post_existing_username(self):
        # Test POST request con username già esistente
        User.objects.create_user(username='existinguser', password='testpass123')
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('sylvelius:profile_edit'), {
            'username': 'existinguser',
            'old_password': 'testpass123',
            'new_password1': '',
            'new_password2': ''
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('usr', response.context)
        self.assertEqual(response.context['usr'], 'bad')

    def test_profilo_edit_page_view_post_long_username(self):
        # Test POST request con username troppo lungo
        long_username = 'a' * (MAX_UNAME_CHARS + 1)
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('sylvelius:profile_edit'), {
            'username': long_username,
            'old_password': 'testpass123',
            'new_password1': '',
            'new_password2': ''
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('usr', response.context)
        self.assertEqual(response.context['usr'], 'bad')

    def test_profilo_edit_page_view_post_long_password(self):
        # Test POST request con password troppo lunga
        long_password = 'a' * (MAX_PWD_CHARS + 1)
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('sylvelius:profile_edit'), {
            'username': 'testuser',
            'old_password': 'testpass123',
            'new_password1': long_password,
            'new_password2': long_password
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('pwd', response.context)
        self.assertEqual(response.context['pwd'], 'bad')

    def test_profilo_edit_page_view_post_password_mismatch(self):
        # Test POST request con password non coincidenti
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('sylvelius:profile_edit'), {
            'username': 'testuser',
            'old_password': 'testpass123',
            'new_password1': 'newpass123',
            'new_password2': 'differentpass'
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('pwd', response.context)
        self.assertEqual(response.context['pwd'], 'bad')

    def test_profilo_edit_page_view_login_required(self):
        # Test che la view richieda l'accesso
        response = self.client.get(reverse('sylvelius:profile_edit'))
        self.assertEqual(response.status_code, 302)  # Redirect al login
        self.assertTrue(response.url.startswith(reverse('sylvelius:login'))) #type:ignore

class RicercaAnnunciViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.factory = RequestFactory()
        cls.user = get_user_model().objects.create_user(username='testuser', password='12345')
        Annuncio.objects.all().delete()
        Tag.objects.all().delete()
        Prodotto.objects.all().delete()
        CommentoAnnuncio.objects.all().delete()
        # Creazione tags
        cls.tag1 = Tag.objects.create(nome='elettronica')
        cls.tag2 = Tag.objects.create(nome='abbigliamento')
        cls.tag3 = Tag.objects.create(nome='casa')
        
        # Creazione prodotti e annunci
        cls.prod1 = Prodotto.objects.create(
            nome='Smartphone XYZ',
            descrizione_breve='Smartphone di ultima generazione',
            prezzo=599.99,
            condizione='nuovo'
        )
        cls.prod1.tags.add(cls.tag1)
        cls.annuncio1 = Annuncio.objects.create(
            prodotto=cls.prod1,
            inserzionista=cls.user,
            qta_magazzino=5,
            is_published=True
        )
        
        cls.prod2 = Prodotto.objects.create(
            nome='Maglione invernale',
            descrizione_breve='Maglione caldo per l\'inverno',
            prezzo=49.99,
            condizione='usato'
        )
        cls.prod2.tags.add(cls.tag2)
        cls.annuncio2 = Annuncio.objects.create(
            prodotto=cls.prod2,
            inserzionista=cls.user,
            qta_magazzino=0,
            is_published=True
        )
        
        cls.prod3 = Prodotto.objects.create(
            nome='Tavolo da pranzo',
            descrizione_breve='Tavolo in legno massello',
            prezzo=199.99
        )
        cls.prod3.tags.add(cls.tag3)
        cls.annuncio3 = Annuncio.objects.create(
            prodotto=cls.prod3,
            inserzionista=cls.user,
            qta_magazzino=2,
            is_published=True
        )
        
        # Creazione commenti con rating
        cls.commento1 = CommentoAnnuncio.objects.create(
            annuncio=cls.annuncio1,
            utente=cls.user,
            rating=4,
            testo='Ottimo prodotto'
        )
        cls.commento2 = CommentoAnnuncio.objects.create(
            annuncio=cls.annuncio1,
            utente=cls.user,
            rating=5,
            testo='Eccellente'
        )
        cls.commento3 = CommentoAnnuncio.objects.create(
            annuncio=cls.annuncio3,
            utente=cls.user,
            rating=2,
            testo='Discreto'
        )

    def test_ricerca_base(self):
        request = self.factory.get(reverse('sylvelius:ricerca_annunci'))
        view = RicercaAnnunciView()
        view.request = request
        
        context = view.get_context_data()
        
        # Verifica che tutti gli annunci pubblicati siano presenti
        self.assertEqual(len(context['annunci']), 3)
        self.assertIn(self.annuncio1, context['annunci'])
        self.assertIn(self.annuncio2, context['annunci'])
        self.assertIn(self.annuncio3, context['annunci'])
        
        # Verifica paginazione
        self.assertEqual(context['page'], 1)
        self.assertFalse(context['has_next'])
        self.assertFalse(context['has_previous'])

    def test_ricerca_per_testo(self):
        # Ricerca per nome prodotto
        request = self.factory.get(reverse('sylvelius:ricerca_annunci'), {'q': 'Smartphone'})
        view = RicercaAnnunciView()
        view.request = request
        
        context = view.get_context_data()
        self.assertEqual(len(context['annunci']), 1)
        self.assertIn(self.annuncio1, context['annunci'])
        
        # Ricerca per descrizione breve
        request = self.factory.get(reverse('sylvelius:ricerca_annunci'), {'q': 'caldo'})
        view.request = request
        
        context = view.get_context_data()
        self.assertEqual(len(context['annunci']), 1)
        self.assertIn(self.annuncio2, context['annunci'])
        
        # Ricerca per tag (senza usare il filtro categorie)
        request = self.factory.get(reverse('sylvelius:ricerca_annunci'), {'q': 'elettronica'})
        view.request = request
        
        context = view.get_context_data()
        self.assertEqual(len(context['annunci']), 1)
        self.assertIn(self.annuncio1, context['annunci'])

    def test_filtro_categoria(self):
        # Filtro per singola categoria
        request = self.factory.get(reverse('sylvelius:ricerca_annunci'), {'categoria': 'elettronica'})
        view = RicercaAnnunciView()
        view.request = request
        
        context = view.get_context_data()
        self.assertEqual(len(context['annunci']), 1)
        self.assertIn(self.annuncio1, context['annunci'])
        
        # Filtro per multiple categorie
        request = self.factory.get(reverse('sylvelius:ricerca_annunci'), {'categoria': 'elettronica,casa'})
        view = RicercaAnnunciView()
        view.request = request
        
        context = view.get_context_data()
        self.assertEqual(len(context['annunci']), 0)
        
        # Categoria inesistente
        request = self.factory.get(reverse('sylvelius:ricerca_annunci'), {'categoria': 'Inesistente'})
        view.request = request
        
        context = view.get_context_data()
        self.assertEqual(len(context['annunci']), 0)

        # Categoria inesistente
        request = self.factory.get(reverse('sylvelius:ricerca_annunci'), {'categoria': ' '})
        view.request = request
        
        context = view.get_context_data()
        self.assertEqual(len(context['annunci']), 3)

        request = self.factory.get(reverse('sylvelius:ricerca_annunci'), {'categoria': '  , , ,, ,   ,elettronica,, ,  ,'})
        view.request = request
        
        context = view.get_context_data()
        self.assertEqual(len(context['annunci']), 1)

    def test_filtro_condizione(self):
        # Filtro per condizione NU (Nuovo)
        request = self.factory.get(reverse('sylvelius:ricerca_annunci'), {'condition': 'nuovo'})
        view = RicercaAnnunciView()
        view.request = request
        
        context = view.get_context_data()
        self.assertEqual(len(context['annunci']), 2)
        self.assertIn(self.annuncio1, context['annunci'])
        
        # Filtro per condizione US (Usato)
        request = self.factory.get(reverse('sylvelius:ricerca_annunci'), {'condition': 'usato'})
        view.request = request
        
        context = view.get_context_data()
        self.assertEqual(len(context['annunci']), 1)
        self.assertIn(self.annuncio2, context['annunci'])
        
        # Condizione non valida (dovrebbe mostrare tutti gli annunci)
        request = self.factory.get(reverse('sylvelius:ricerca_annunci'), {'condition': 'INVALID'})
        view.request = request
        
        context = view.get_context_data()
        self.assertEqual(len(context['annunci']), 3)

        request = self.factory.get(reverse('sylvelius:ricerca_annunci'), {'condition': '  '})
        view.request = request
        
        context = view.get_context_data()
        self.assertEqual(len(context['annunci']), 3)

        request = self.factory.get(reverse('sylvelius:ricerca_annunci'), {'condition': ' , ,, '})
        view.request = request
        
        context = view.get_context_data()
        self.assertEqual(len(context['annunci']), 3)

    def test_filtro_qta_magazzino(self):
        # Solo prodotti disponibili
        request = self.factory.get(reverse('sylvelius:ricerca_annunci'), {'qta_mag': 'qta-pres'})
        view = RicercaAnnunciView()
        view.request = request
        
        context = view.get_context_data()
        self.assertEqual(len(context['annunci']), 2)
        self.assertIn(self.annuncio1, context['annunci'])
        self.assertIn(self.annuncio3, context['annunci'])
        
        # Solo prodotti non disponibili
        request = self.factory.get(reverse('sylvelius:ricerca_annunci'), {'qta_mag': 'qta-manc'})
        view.request = request
        
        context = view.get_context_data()
        self.assertEqual(len(context['annunci']), 1)
        self.assertIn(self.annuncio2, context['annunci'])

    def test_filtro_rating(self):
        # Rating specifico (4-5 stelle)
        request = self.factory.get(reverse('sylvelius:ricerca_annunci'), {'search_by_rating': '4'})
        view = RicercaAnnunciView()
        view.request = request
        
        context = view.get_context_data()
        self.assertEqual(len(context['annunci']), 1)
        self.assertIn(self.annuncio1, context['annunci'])
        
        # Rating specifico (2 stelle)
        request = self.factory.get(reverse('sylvelius:ricerca_annunci'), {'search_by_rating': '2'})
        view.request = request
        
        context = view.get_context_data()
        self.assertEqual(len(context['annunci']), 1)
        self.assertIn(self.annuncio3, context['annunci'])
        
        # Solo annunci con almeno un rating
        request = self.factory.get(reverse('sylvelius:ricerca_annunci'), {'search_by_rating': 'starred'})
        view.request = request
        
        context = view.get_context_data()
        self.assertEqual(len(context['annunci']), 2)
        self.assertIn(self.annuncio1, context['annunci'])
        self.assertIn(self.annuncio3, context['annunci'])
        
        # Solo annunci senza rating
        request = self.factory.get(reverse('sylvelius:ricerca_annunci'), {'search_by_rating': 'none'})
        view.request = request
        
        context = view.get_context_data()
        self.assertEqual(len(context['annunci']), 1)
        self.assertIn(self.annuncio2, context['annunci'])
        
        # Rating non valido (dovrebbe mostrare tutti)
        request = self.factory.get(reverse('sylvelius:ricerca_annunci'), {'search_by_rating': 'invalid'})
        view.request = request
        
        context = view.get_context_data()
        self.assertEqual(len(context['annunci']), 3)

        request = self.factory.get(reverse('sylvelius:ricerca_annunci'), {'search_by_rating': '100'})
        view.request = request
        
        context = view.get_context_data()
        self.assertEqual(len(context['annunci']), 3)

    def test_filtro_prezzo(self):
        # Prezzo minimo
        request = self.factory.get(reverse('sylvelius:ricerca_annunci'), {'prezzo_min': '100'})
        view = RicercaAnnunciView()
        view.request = request
        
        context = view.get_context_data()
        self.assertEqual(len(context['annunci']), 2)
        self.assertIn(self.annuncio1, context['annunci'])
        self.assertIn(self.annuncio3, context['annunci'])
        
        # Prezzo massimo
        request = self.factory.get(reverse('sylvelius:ricerca_annunci'), {'prezzo_max': '100'})
        view.request = request
        
        context = view.get_context_data()
        self.assertEqual(len(context['annunci']), 1)
        self.assertIn(self.annuncio2, context['annunci'])
        
        # Range di prezzo
        request = self.factory.get(reverse('sylvelius:ricerca_annunci'), {'prezzo_min': '50', 'prezzo_max': '200'})
        view.request = request
        
        context = view.get_context_data()
        self.assertEqual(len(context['annunci']), 1)
        self.assertIn(self.annuncio3, context['annunci'])
        
        # Prezzo non valido (dovrebbe essere ignorato)
        request = self.factory.get(reverse('sylvelius:ricerca_annunci'), {'prezzo_min': 'invalid', 'prezzo_max': 'invalid'})
        view.request = request
        
        context = view.get_context_data()
        self.assertEqual(len(context['annunci']), 3)

    def test_ordinamento_risultati(self):
        # Ordinamento per data decrescente (default)
        request = self.factory.get(reverse('sylvelius:ricerca_annunci'), {'sort': 'data-desc'})
        view = RicercaAnnunciView()
        view.request = request
        
        context = view.get_context_data()
        self.assertEqual(context['annunci'][0], self.annuncio3)
        self.assertEqual(context['annunci'][1], self.annuncio2)
        self.assertEqual(context['annunci'][2], self.annuncio1)
        
        # Ordinamento per data crescente
        request = self.factory.get(reverse('sylvelius:ricerca_annunci'), {'sort': 'data-asc'})
        view.request = request
        
        context = view.get_context_data()
        self.assertEqual(context['annunci'][0], self.annuncio1)
        self.assertEqual(context['annunci'][1], self.annuncio2)
        self.assertEqual(context['annunci'][2], self.annuncio3)
        
        # Ordinamento per prezzo crescente
        request = self.factory.get(reverse('sylvelius:ricerca_annunci'), {'sort': 'prezzo-asc'})
        view.request = request
        
        context = view.get_context_data()
        self.assertEqual(context['annunci'][0], self.annuncio2)
        self.assertEqual(context['annunci'][1], self.annuncio3)
        self.assertEqual(context['annunci'][2], self.annuncio1)
        
        # Ordinamento per prezzo decrescente
        request = self.factory.get(reverse('sylvelius:ricerca_annunci'), {'sort': 'prezzo-desc'})
        view.request = request
        
        context = view.get_context_data()
        self.assertEqual(context['annunci'][0], self.annuncio1)
        self.assertEqual(context['annunci'][1], self.annuncio3)
        self.assertEqual(context['annunci'][2], self.annuncio2)

        request = self.factory.get(reverse('sylvelius:ricerca_annunci'), {'sort': 'err'})
        view.request = request
        
        context = view.get_context_data()
        self.assertEqual(context['annunci'][0], self.annuncio3)
        self.assertEqual(context['annunci'][1], self.annuncio2)
        self.assertEqual(context['annunci'][2], self.annuncio1)

    def test_paginazione(self):
        # Creiamo più annunci per testare la paginazione
        for i in range(MAX_PAGINATOR_RICERCA_VALUE + 5):
            prod = Prodotto.objects.create(
                nome=f'Prodotto {i}',
                descrizione_breve=f'Descrizione {i}',
                prezzo=10 + i,
                condizione='NU'
            )
            Annuncio.objects.create(
                prodotto=prod,
                inserzionista=self.user,
                qta_magazzino=1,
                is_published=True
            )
        
        # Pagina 1 (default)
        request = self.factory.get(reverse('sylvelius:ricerca_annunci'))
        view = RicercaAnnunciView()
        view.request = request
        
        context = view.get_context_data()
        self.assertEqual(len(context['annunci']), MAX_PAGINATOR_RICERCA_VALUE)
        self.assertEqual(context['page'], 1)
        self.assertTrue(context['has_next'])
        self.assertFalse(context['has_previous'])
        
        # Pagina 2
        request = self.factory.get(reverse('sylvelius:ricerca_annunci'), {'page': '2'})
        view.request = request
        
        context = view.get_context_data()
        self.assertEqual(len(context['annunci']), 5 + 3)  # 5 nuovi + 3 originali - MAX_PAGINATOR_RICERCA_VALUE
        self.assertEqual(context['page'], 2)
        self.assertFalse(context['has_next'])
        self.assertTrue(context['has_previous'])
        
        # Pagina non valida (dovrebbe tornare alla prima pagina)
        request = self.factory.get(reverse('sylvelius:ricerca_annunci'), {'page': 'invalid'})
        view.request = request
        
        context = view.get_context_data()
        self.assertEqual(context['page'], 1)

        request = self.factory.get(reverse('sylvelius:ricerca_annunci'), {'page': '0'})
        view.request = request
        
        context = view.get_context_data()
        self.assertEqual(context['page'], 1)

    def test_combinazione_filtri(self):
        # Combinazione di più filtri
        request = self.factory.get(reverse('sylvelius:ricerca_annunci'), {
            'q': 'Smartphone',
            'condition': 'NU',
            'prezzo_min': '500',
            'prezzo_max': '600',
            'qta_mag': 'qta-pres',
            'search_by_rating': 'starred'
        })
        view = RicercaAnnunciView()
        view.request = request
        
        context = view.get_context_data()
        self.assertEqual(len(context['annunci']), 1)
        self.assertIn(self.annuncio1, context['annunci'])
        
        # Combinazione che non dovrebbe restituire risultati
        request = self.factory.get(reverse('sylvelius:ricerca_annunci'), {
            'q': 'Smartphone',
            'condition': 'US',
            'prezzo_min': '1000'
        })
        view.request = request
        
        context = view.get_context_data()
        self.assertEqual(len(context['annunci']), 0)

    def test_annunci_non_pubblicati(self):
        # Creiamo un annuncio non pubblicato
        prod = Prodotto.objects.create(
            nome='Prodotto Privato',
            descrizione_breve='Non dovrebbe apparire',
            prezzo=100,
            condizione='NU'
        )
        annuncio_privato = Annuncio.objects.create(
            prodotto=prod,
            inserzionista=self.user,
            qta_magazzino=1,
            is_published=False
        )
        
        request = self.factory.get(reverse('sylvelius:ricerca_annunci'))
        view = RicercaAnnunciView()
        view.request = request
        
        context = view.get_context_data()
        self.assertNotIn(annuncio_privato, context['annunci'])

class TestModeratoreAccessForbiddenMixin(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Creazione utenti e gruppi per i test
        cls.normal_user = User.objects.create_user(username='normale', password='test123')
        cls.moderatore_user = User.objects.create_user(username='moderatore', password='test123')
        
        # Creazione gruppo moderatori
        moderatori_group = Group.objects.create(name='moderatori')
        cls.moderatore_user.groups.add(moderatori_group)
        
        # View di test che usa il mixin
        class TestView(ModeratoreAccessForbiddenMixin, View):
            def get(self, request, *args, **kwargs):
                return HttpResponse("Accesso consentito")
        
        cls.test_view = TestView.as_view()
        cls.factory = RequestFactory()

    def test_utente_anonimo_può_accedere(self):
        """Verifica che un utente anonimo possa accedere"""
        request = self.factory.get('/')
        request.user = AnonymousUser()
        response = self.test_view(request)
        self.assertEqual(response.status_code, 200)

    def test_utente_normale_può_accedere(self):
        """Verifica che un utente normale (non moderatore) possa accedere"""
        request = self.factory.get('/')
        request.user = self.normal_user
        response = self.test_view(request)
        self.assertEqual(response.status_code, 200)

    def test_utente_moderatore_non_può_accedere(self):
        """Verifica che un utente moderatore riceva PermissionDenied"""
        request = self.factory.get('/')
        request.user = self.moderatore_user
        with self.assertRaises(PermissionDenied):
            self.test_view(request)

    def test_controllo_gruppo_moderatori(self):
        """Verifica che il controllo funzioni solo per il gruppo 'moderatori'"""
        # Creiamo un altro gruppo e utente
        altro_group = Group.objects.create(name='altro_gruppo')
        user = User.objects.create_user(username='altro', password='test123')
        user.groups.add(altro_group)
        
        request = self.factory.get('/')
        request.user = user
        response = self.test_view(request)
        self.assertEqual(response.status_code, 200)