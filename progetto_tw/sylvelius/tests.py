from django.test import TestCase, RequestFactory, Client
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User, Group, AnonymousUser
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.core.exceptions import PermissionDenied
from django.views import View

import tempfile
import shutil
import json
import uuid
from decimal import Decimal
from unittest.mock import patch

from .models import (
    Annuncio, CommentoAnnuncio, ImmagineProdotto,
    Ordine, Tag, Prodotto, Notification
)
from .views import (
    RicercaAnnunciView, send_notification, 
    mark_notifications_read, create_notification, annulla_ordine_free, 
    check_if_annuncio_is_valid, annulla_ordine
)
from sylvelius.forms import CustomUserCreationForm
from progetto_tw.mixins import ModeratoreAccessForbiddenMixin
from purchase.models import Invoice
from progetto_tw.constants import (
    MAX_PAGINATOR_COMMENTI_ANNUNCIO_VALUE,
    MAX_UNAME_CHARS, 
    MAX_PWD_CHARS,
    MAX_PAGINATOR_RICERCA_VALUE,
    MAX_PAGINATOR_COMMENTI_DETTAGLI_VALUE,
    MAX_ANNUNCI_PER_DETTAGLI_VALUE,
    _MODS_GRP_NAME,
    _NEXT_PROD_ID
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
        tag1 = Tag.objects.create(nome='Tag01')
        tag2 = Tag.objects.create(nome='Tag02')
        user = User.objects.create_user(username='testuser', password='Testpass0')
        prodotto = Prodotto.objects.create(
            id=_NEXT_PROD_ID,
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
        response = self.client.get(f'/api/immagine/{_NEXT_PROD_ID}/')
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
        response = self.client.get(f'/api/immagini/{_NEXT_PROD_ID}/')
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
        tag1 = Tag.objects.create(nome='Tag01')
        tag2 = Tag.objects.create(nome='Tag02')
        self.user = User.objects.create_user(username='testuser', password='Testpass0')
        prodotto = Prodotto.objects.create(
            id=_NEXT_PROD_ID,
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
        
    def test_to_string(self):
        self.assertEqual(Tag.objects.get(nome="tag01").__str__(),"tag01")
        self.assertEqual(Prodotto.objects.get(id=_NEXT_PROD_ID).immagini.first().__str__(),"Immagine di Prodotto di Test") #type: ignore
        self.assertEqual(Annuncio.objects.get(id=_NEXT_PROD_ID).__str__(),"Prodotto di Test")
        self.assertEqual(CommentoAnnuncio.objects.get(id=_NEXT_PROD_ID).__str__(),"testuser su Prodotto di Test - 4/5")
        self.assertEqual(Annuncio.objects.get(id=_NEXT_PROD_ID).rating_medio,4)
        self.assertEqual(Annuncio.objects.get(id=_NEXT_PROD_ID).rating_count,1)
        self.assertEqual(Ordine.objects.get(id=_NEXT_PROD_ID).__str__(),"testuser - Prodotto di Test")
        self.assertEqual(Ordine.objects.get(id=_NEXT_PROD_ID).totale,300.00)
        self.assertEqual(Ordine.objects.get(id=_NEXT_PROD_ID).json_to_string,'{"address_line_1": "Via test", "admin_area_2": "Roma", "postal_code": "46029", "admin_area_1": "RM", "country_code": "IT"}')

class LoggedUrls2(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='Testpass0')
        self.group, created = Group.objects.get_or_create(name=_MODS_GRP_NAME)
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
        
        self.moderator_group, _ = Group.objects.get_or_create(name=_MODS_GRP_NAME)
        
        self.temp_media_dir = tempfile.mkdtemp()
        settings.MEDIA_ROOT = self.temp_media_dir
        
    def tearDown(self):
        shutil.rmtree(self.temp_media_dir)
    
    def test_send_notification(self):
        response = send_notification(title="Test", message="Global message", global_notification=True)
        self.assertIsNone(response)  
        response = send_notification(user_id=self.user.id, title="Test", message="User message") #type:ignore
        self.assertIsNone(response)

        response = send_notification(title="Test", message="User message")
        self.assertIsNone(response)
    
    def test_mark_notifications_read(self):
        Notification.objects.create(
            recipient=self.user,
            title="Test",
            message="Test message",
            read=False
        )
        
        request = self.factory.post(reverse('sylvelius:mark_notifications_read'))
        request.user = self.user
        
        response = mark_notifications_read(request)
        response_data = json.loads(response.content.decode())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response_data, {'status': 'ok'})
        
        notification = Notification.objects.get(recipient=self.user)
        self.assertTrue(notification.read)
    
    def test_create_notification(self):
        notifica = create_notification(
            recipient=self.user,
            title="User Notification",
            message="Test message"
        )
        self.assertIsInstance(notifica, Notification)
        self.assertEqual(notifica.recipient, self.user)
        self.assertFalse(notifica.read)
        
        notifica = create_notification(
            title="Global Notification",
            message="Global message",
            is_global=True
        )
        self.assertTrue(notifica.is_global)
        self.assertIsNone(notifica.recipient)
    
    def test_annulla_ordine_free(self):
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
        
        ordine = Ordine.objects.create(
            utente=self.user,
            prodotto=prodotto,
            stato_consegna='da spedire'
        )
        
        request = self.factory.post('/')
        request.user = self.user
        response = annulla_ordine_free(request, ordine.id) #type:ignore
        response_data = json.loads(response.content.decode())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response_data, {"status": "success"})
        
        ordine.refresh_from_db()
        self.assertEqual(ordine.stato_consegna, 'annullato')
        
        self.assertTrue(Notification.objects.filter(
            recipient=venditore,
            title="Ordine annullato"
        ).exists())
        
        ordine_venditore = Ordine.objects.create(
            utente=self.user,
            prodotto=prodotto,
            stato_consegna='da spedire'
        )
        request.user = venditore
        response = annulla_ordine_free(request, ordine_venditore.id) #type:ignore
        self.assertEqual(response.status_code, 200)
        
        self.assertTrue(Notification.objects.filter(
            recipient=self.user,
            title="Ordine rifiutato"
        ).exists())
        
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
        post_data = {
            'nome': 'Prodotto Valido',
            'descrizione_breve': 'Descrizione breve valida',
            'prezzo': '10.00',
            'iva': '22',
            'tags': 'tag1,tag2',
            'qta_magazzino': '5',
            'condizione': 'nuovo'
        }
        
        image = SimpleUploadedFile(
            name='test_image.jpg',
            content=b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x00\x00\x00\x21\xf9\x04\x01\x0a\x00\x01\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x4c\x01\x00\x3b',
            content_type='image/jpeg'
        )
        
        request = self.factory.post('/', post_data)
        request.FILES['immagini'] = image
        
        result = check_if_annuncio_is_valid(request)
        self.assertIsNone(result)
        
        test_cases = [
            ({'nome': ''}, {'evento': 'noval'}),  # Campo nome vuoto
            ({'nome': 'a'*201}, {'evento': 'lentxt'}),  # Nome troppo lungo
            ({'prezzo': 'abc'}, {'evento': 'prerr'}),  # Prezzo non numerico
            ({'prezzo': '-1'}, {'evento': 'price'}),  # Prezzo negativo
            ({'iva': '99'}, {'evento': 'cond'}),  # IVA non valida
            ({'qta_magazzino': 'abc'}, {'evento': 'qtaerr'}),  # Quantità non numerica
            ({'qta_magazzino': '-1'}, {'evento': 'qta'}),  # Quantità troppo bassa
            ({'tags': 'a'*51}, {'evento': 'tagchar'}),  # Tag troppo lungo
            ({'tags': ','.join(['tag']*51)}, {'evento': 'tagn'}),  # Troppi tag
            ({'condizione': 'non_valida'}, {'evento': 'cond'}),  # Condizione non valida
        ]
        
        for data, expected in test_cases:
            modified_data = post_data.copy()
            modified_data.update(data)
            request = self.factory.post('/', modified_data)
            request.FILES['immagini'] = image
            result = check_if_annuncio_is_valid(request)
            self.assertEqual(result, expected)
        
        invalid_image = SimpleUploadedFile(
            name='test_image.txt',
            content=b'Not an image',
            content_type='text/plain'
        )
        
        request = self.factory.post('/', post_data)
        request.FILES['immagini'] = invalid_image
        result = check_if_annuncio_is_valid(request)
        self.assertEqual(result, {'evento': 'imgtype'})
        
        request = self.factory.post('/', data={**post_data, 'immagini': [image]*11})
        result = check_if_annuncio_is_valid(request)
        self.assertEqual(result, {'evento': 'imgn'})

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
        self.assertEqual(result, {'evento': 'imgproportion'})

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
        self.assertEqual(result, {'evento': 'imgsize'})
        
class ViewTests(TestCase):
    def setUp(self):
        Annuncio.objects.all().delete()
        CommentoAnnuncio.objects.all().delete()
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username='testuser', password='testpass123'
        )
        self.user2 = User.objects.create_user(
            username='testuser2', password='testpass123'
        )
        self.group = Group.objects.create(name=_MODS_GRP_NAME)
        self.client = Client()
        
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
        
        self.commento = CommentoAnnuncio.objects.create(
            annuncio=self.annuncio,
            utente=self.user,
            testo="Commento di test",
            rating=4
        )
        
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
        response = self.client.get(reverse('sylvelius:register'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'sylvelius/register.html')
        
        response = self.client.post(reverse('sylvelius:register'), {
            'username': 'newuser',
            'password1': 'complexpassword123',
            'password2': 'complexpassword123'
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(username='newuser').exists())
        
        response = self.client.post(reverse('sylvelius:register'), {
            'username': 'newuser',
            'password1': 'complexpassword123',
            'password2': 'differentpassword'
        })
        self.assertEqual(response.status_code, 302)

    def test_login_page_view(self):
        response = self.client.get(reverse('sylvelius:login'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'sylvelius/login.html')
        
        response = self.client.post(reverse('sylvelius:login'), {
            'username': 'testuser',
            'password': 'testpass123'
        }, follow=True)
        self.assertTrue(response.context['user'].is_authenticated)
        self.client.logout()
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
        response = self.client.get(reverse('sylvelius:profile'))
        self.assertEqual(response.status_code, 302)  
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('sylvelius:profile'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'sylvelius/profile/profile.html')
        self.assertIn('user', response.context)
        self.assertIn('annunci', response.context)
        self.assertIn('ordini', response.context)
        
        moderator = User.objects.create_user(
            username='moderator', password='modpass123'
        )
        moderator_group = Group.objects.get(name=_MODS_GRP_NAME)
        moderator.groups.add(moderator_group)
        
        self.client.login(username='moderator', password='modpass123')
        response = self.client.get(reverse('sylvelius:profile'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('user_without_is_active', response.context)

    def test_profilo_delete_page_view(self):
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(reverse('sylvelius:profile_delete'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'sylvelius/profile/profile_delete.html')
        self.assertEqual(response.context['user'], self.user)
        
        response = self.client.post(reverse('sylvelius:profile_delete'))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(User.objects.filter(username='testuser').exists())
        
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
        
        Ordine.objects.create(
            utente=self.user,
            prodotto=self.prodotto,
            stato_consegna='spedito'
        )
        response = self.client.post(reverse('sylvelius:profile_delete'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'sylvelius/profile/profile_delete.html')
        self.assertIn('evento', response.context)
        self.assertEqual(response.context['evento'], 'ship')
        self.assertTrue(User.objects.filter(username='testuser').exists())
        
        Ordine.objects.all().delete()
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
        self.assertIn('evento', response.context)
        self.assertEqual(response.context['evento'], 'shipd')
        self.assertTrue(User.objects.filter(username='testuser').exists())
    
    def test_profilo_ordini_page_view(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('sylvelius:profile_ordini'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'sylvelius/profile/profile_ordini.html')
        self.assertIn('ordini', response.context)
        
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
    
    def test_annuncio_detail_view(self):
        url = reverse('sylvelius:dettagli_annuncio', args=[self.annuncio.uuid])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'sylvelius/annuncio/dettagli_annuncio.html')
        self.assertIn('annuncio', response.context)
        self.assertIn('commenti', response.context)
        self.assertEqual(response.context['annuncio'], self.annuncio)
        self.assertIn(self.commento, response.context['commenti'])
        self.assertIsNone(response.context.get('get_commento'))
        self.assertFalse(response.context['ha_acquistato'])
        self.assertTrue(response.context['non_ha_commentato'])
        
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(url)
        self.assertIn('ha_acquistato', response.context)
        self.assertIn('non_ha_commentato', response.context)
        self.assertEqual(response.context['get_commento'], self.commento)
        self.assertFalse(response.context['ha_acquistato'])
        self.assertFalse(response.context['non_ha_commentato'])
        
        self.ordine.stato_consegna = 'consegnato'
        self.ordine.save()
        response = self.client.get(url)
        self.assertTrue(response.context['ha_acquistato'])
        
        self.annuncio.is_published = False
        self.annuncio.save()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)
        self.annuncio.is_published = True
        self.annuncio.save()
        
        self.user.groups.add(self.group)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        
        self.annuncio.is_published = False
        self.annuncio.save()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.annuncio.is_published = True
        self.annuncio.save()
        
        self.user.is_active = False
        self.user.save()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)
        self.user.is_active = True
        self.user.save()
        
        CommentoAnnuncio.objects.filter(utente=self.user).delete()
        response = self.client.get(url)
        self.assertTrue(response.context['non_ha_commentato'])
        self.assertIsNone(response.context['get_commento'])
        
        for i in range(MAX_PAGINATOR_COMMENTI_ANNUNCIO_VALUE):
            CommentoAnnuncio.objects.create(
                annuncio=self.annuncio,
                utente=self.user,
                testo=f"Commento {i}",
                rating=3
            )
        response = self.client.get(url)
        self.assertEqual(len(response.context['commenti']), MAX_PAGINATOR_COMMENTI_ANNUNCIO_VALUE-1)
        self.assertFalse(response.context['has_next'])
        
        response = self.client.get(url + '?page=2')
        self.assertEqual(response.status_code, 200)
        
        inactive_user = User.objects.create_user(
            username='inactive', password='testpass123', is_active=False
        )
        inactive_comment = CommentoAnnuncio.objects.create(
            annuncio=self.annuncio,
            utente=inactive_user,
            testo="Commento utente non attivo",
            rating=2
        )
        response = self.client.get(url)
        self.assertIn(inactive_comment, response.context['commenti'])
        self.client.force_login(self.user2)
        response = self.client.get(url)
        self.assertNotIn(inactive_comment, response.context['commenti'])
        
        response = self.client.get(url)
        all_comments = CommentoAnnuncio.objects.filter(annuncio=self.annuncio).count()
        self.assertLess(len(response.context['commenti']), all_comments)
        
        fake_uuid = uuid.uuid4()
        url = reverse('sylvelius:dettagli_annuncio', args=[fake_uuid])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

class FunctionBasedViewTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username='testuser', password='testpass123'
        )
        self.groups = Group.objects.create(name=_MODS_GRP_NAME)
        self.client = Client()
        
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
        
        self.commento = CommentoAnnuncio.objects.create(
            annuncio=self.annuncio,
            utente=self.user,
            testo="Commento di test",
            rating=4
        )
        
        self.ordine = Ordine.objects.create(
            utente=self.user,
            prodotto=self.prodotto,
            stato_consegna='da spedire'
        )
    
    def test_toggle_pubblicazione(self):
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.post(
            reverse('sylvelius:nascondi_annuncio', args=[self.annuncio.id]), #type:ignore
            HTTP_REFERER=reverse('sylvelius:profile_annunci')
        )
        self.assertEqual(response.status_code, 302)
        self.annuncio.refresh_from_db()
        self.assertFalse(self.annuncio.is_published)
        
        response = self.client.post(
            reverse('sylvelius:nascondi_annuncio', args=[self.annuncio.id]), #type:ignore
            HTTP_REFERER=reverse('sylvelius:profile_annunci')
        )
        self.assertEqual(response.status_code, 302)
        self.annuncio.refresh_from_db()
        self.assertTrue(self.annuncio.is_published)
    
    def test_delete_pubblicazione(self):
        self.client.login(username='testuser', password='testpass123')
        
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
        
        moderator = User.objects.create_user(username='moderator', password='modpass123')
        moderator.groups.add(self.groups)
        
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
        
        response = self.client.post(
            reverse('sylvelius:check_old_password'),
            data=json.dumps({'old_password': 'testpass123'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['valid'])
        
        response = self.client.post(
            reverse('sylvelius:check_old_password'),
            data=json.dumps({'old_password': 'wrongpassword'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['valid'])
    
    def test_check_username_exists(self):
        response = self.client.post(
            reverse('sylvelius:check_username_exists'),
            data=json.dumps({'username': 'testuser'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['exists'])
        
        response = self.client.post(
            reverse('sylvelius:check_username_exists'),
            data=json.dumps({'username': 'nonexistentuser'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['exists'])
    
    def test_check_login_credentials(self):
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
        moderator_user = User.objects.create_user(
            username='moderator',
            password='modpass123'
        )
        moderator_user.groups.add(self.groups)
        
        commento = CommentoAnnuncio.objects.create(
            annuncio=self.annuncio,
            utente=self.user,  
            testo="Commento da eliminare da moderatore",
            rating=4
        )
        
        self.client.login(username='moderator', password='modpass123')
        
        response = self.client.post(
            reverse('sylvelius:elimina_commento', args=[commento.id]), #type:ignore
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "success"})
        self.assertFalse(CommentoAnnuncio.objects.filter(id=commento.id).exists()) #type:ignore  
  
    def test_espelli_utente(self):
        moderator = User.objects.create_user(
            username='moderator', password='modpass123'
        )
        moderator_group = Group.objects.get(name=_MODS_GRP_NAME)
        moderator.groups.add(moderator_group)
        
        self.client.login(username='moderator', password='modpass123')
        
        user_to_ban = User.objects.create_user(
            username='usertoban', password='testpass123'
        )
        
        response = self.client.post(
            reverse('sylvelius:espelli_utente', args=['ban', user_to_ban.id]) #type:ignore
        )
        self.assertEqual(response.status_code, 302)
        user_to_ban.refresh_from_db()
        self.assertFalse(user_to_ban.is_active)
        
        response = self.client.post(
            reverse('sylvelius:espelli_utente', args=['unban', user_to_ban.id]) #type:ignore
        )
        self.assertEqual(response.status_code, 302)
        user_to_ban.refresh_from_db()
        self.assertTrue(user_to_ban.is_active)
        
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
        moderator = User.objects.create_user(
            username='moderator', password='modpass123'
        )
        moderator_group = Group.objects.get(name=_MODS_GRP_NAME)
        moderator.groups.add(moderator_group)
        
        self.client.login(username='moderator', password='modpass123')
        
        banned_user = User.objects.create_user(
            username='banneduser', password='testpass123',
            is_active=False
        )
        
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
        
        buyer = User.objects.create_user(
            username='buyer', password='testpass123'
        )
        
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
        
        with patch('sylvelius.views.annulla_ordine_free') as mock_annulla:
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
            
            args, _ = mock_annulla.call_args_list[0]
            request_passed = args[0]
            ordine_id_passed = args[1]
            
            self.assertEqual(request_passed.user, moderator)
            self.assertEqual(ordine_id_passed, ordine_inserzionista.id)#type:ignore
            
            args, _ = mock_annulla.call_args_list[1]
            request_passed = args[0]
            ordine_id_passed = args[1]
            
            self.assertEqual(request_passed.user, moderator)
            self.assertEqual(ordine_id_passed, ordine_utente.id)#type:ignore
            
            self.assertFalse(Annuncio.objects.filter(inserzionista=banned_user).exists())
            self.assertFalse(CommentoAnnuncio.objects.filter(utente=banned_user).exists())
            self.assertFalse(Ordine.objects.filter(utente=banned_user).exists())
            self.assertFalse(Ordine.objects.filter(prodotto__annunci__inserzionista=banned_user).exists())
    @patch('sylvelius.views.annulla_ordine_free')
    def test_annulla_ordine(self, mock_annulla_ordine_free):
        mock_annulla_ordine_free.return_value = JsonResponse({"status": "success"})
        
        request = self.factory.post('/')
        request.user = self.user
        prodotto = Prodotto.objects.create(
            nome="Prodotto Test",
            descrizione_breve="Descrizione breve",
            prezzo=10.00
        )        
        ordine = Ordine.objects.create(
            utente=self.user,
            prodotto=prodotto,
            stato_consegna='da spedire'
        )
        response = annulla_ordine(request, ordine.id) #type:ignore

        self.assertEqual(response.status_code, 200)
        mock_annulla_ordine_free.assert_called_once_with(request, ordine.id)#type:ignore

class AnnuncioCreationTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username='testuser', password='testpass123'
        )
        self.client = Client()
        
        self.temp_media_dir = tempfile.mkdtemp()
        settings.MEDIA_ROOT = self.temp_media_dir
        
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
        
        self.assertTrue(Annuncio.objects.filter(prodotto__nome='Nuovo Prodotto').exists())
        annuncio = Annuncio.objects.get(prodotto__nome='Nuovo Prodotto')
        self.assertEqual(annuncio.inserzionista, self.user)
        self.assertEqual(annuncio.qta_magazzino, 10)
        
        prodotto = annuncio.prodotto
        self.assertEqual(prodotto.descrizione_breve, 'Descrizione breve')
        self.assertEqual(prodotto.prezzo, Decimal('19.99'))
        self.assertEqual(prodotto.iva, 22)
        
        self.assertEqual(prodotto.tags.count(), 3)
        
        self.assertEqual(ImmagineProdotto.objects.filter(prodotto=prodotto).count(), 1)
    
    def test_profilo_crea_annuncio_page_view_post_invalid(self):
        self.client.login(username='testuser', password='testpass123')
        
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
            self.assertIn(error_code, response.context['evento'])
    
    def test_profilo_modifica_annuncio_page_view_get(self):
        self.client.login(username='testuser', password='testpass123')
        
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
        
        tag1 = Tag.objects.create(nome='tag1')
        tag2 = Tag.objects.create(nome='tag2')
        prodotto.tags.add(tag1, tag2)
        
        response = self.client.get(
            reverse('sylvelius:modifica_annuncio', args=[annuncio.id]) #type:ignore
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'sylvelius/annuncio/modifica_annuncio.html')
        
        self.assertEqual(response.context['titolo_mod'], 'Prodotto Originale')
        self.assertEqual(response.context['desc_br_mod'], 'Descrizione originale')
        self.assertEqual(response.context['tags_mod'], ['tag1', 'tag2'])
    
    def test_profilo_modifica_annuncio_page_view_post_valid(self):
        self.client.login(username='testuser', password='testpass123')
        
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
        
        tag1 = Tag.objects.create(nome='tag1')
        tag2 = Tag.objects.create(nome='tag2')
        prodotto.tags.add(tag1, tag2)
        
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
        
        annuncio.refresh_from_db()
        prodotto.refresh_from_db()
        
        self.assertEqual(prodotto.nome, 'Prodotto Modificato')
        self.assertEqual(prodotto.descrizione_breve, 'Descrizione breve modificata')
        self.assertEqual(prodotto.prezzo, 25.00)
        self.assertEqual(prodotto.iva, 22)
        self.assertEqual(prodotto.condizione, 'nuovo')
        self.assertEqual(annuncio.qta_magazzino, 7)
        
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
            self.assertIn(error_code, response.context['evento'])

class ProfiloEditTests(TestCase):

    def setUp(self):
        Annuncio.objects.all().delete()
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username='testuser', password='testpass123'
        )
        self.group = Group.objects.create(name=_MODS_GRP_NAME)
        self.client = Client()
        
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
        
        self.commento = CommentoAnnuncio.objects.create(
            annuncio=self.annuncio,
            utente=self.user,
            testo="Commento di test",
            rating=4
        )
        
        self.ordine = Ordine.objects.create(
            utente=self.user,
            prodotto=self.prodotto,
            stato_consegna='da spedire'
        )
 
    def test_profilo_edit_page_view_get(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(reverse('sylvelius:profile_edit'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'sylvelius/profile/profile_edit.html')

    def test_profilo_edit_page_view_post_valid_username(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('sylvelius:profile_edit'), {
            'username': 'newusername',
            'old_password': 'testpass123',
            'new_password1': '',
            'new_password2': ''
        })
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertEqual(self.user.username, 'newusername')

    def test_profilo_edit_page_view_post_valid_password(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('sylvelius:profile_edit'), {
            'username': 'testuser',
            'old_password': 'testpass123',
            'new_password1': 'newpass123',
            'new_password2': 'newpass123'
        })
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('newpass123'))

    def test_profilo_edit_page_view_post_wrong_old_password(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('sylvelius:profile_edit'), {
            'username': 'testuser',
            'old_password': 'wrongpass',
            'new_password1': 'newpass123',
            'new_password2': 'newpass123'
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('evento', response.context)
        self.assertEqual(response.context['evento'], 'pwd')

    def test_profilo_edit_page_view_post_missing_old_password(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('sylvelius:profile_edit'), {
            'username': 'testuser',
            'old_password': '',
            'new_password1': 'newpass123',
            'new_password2': 'newpass123'
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('evento', response.context)
        self.assertEqual(response.context['evento'], 'pwd')

    def test_profilo_edit_page_view_post_existing_username(self):
        User.objects.create_user(username='existinguser', password='testpass123')
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('sylvelius:profile_edit'), {
            'username': 'existinguser',
            'old_password': 'testpass123',
            'new_password1': '',
            'new_password2': ''
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('evento', response.context)
        self.assertEqual(response.context['evento'], 'usr')

    def test_profilo_edit_page_view_post_long_username(self):
        long_username = 'a' * (MAX_UNAME_CHARS + 1)
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('sylvelius:profile_edit'), {
            'username': long_username,
            'old_password': 'testpass123',
            'new_password1': '',
            'new_password2': ''
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('evento', response.context)
        self.assertEqual(response.context['evento'], 'usr')

    def test_profilo_edit_page_view_post_long_password(self):
        long_password = 'a' * (MAX_PWD_CHARS + 1)
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('sylvelius:profile_edit'), {
            'username': 'testuser',
            'old_password': 'testpass123',
            'new_password1': long_password,
            'new_password2': long_password
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('evento', response.context)
        self.assertEqual(response.context['evento'], 'pwd')

    def test_profilo_edit_page_view_post_password_mismatch(self):
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(reverse('sylvelius:profile_edit'), {
            'username': 'testuser',
            'old_password': 'testpass123',
            'new_password1': 'newpass123',
            'new_password2': 'differentpass'
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('evento', response.context)
        self.assertEqual(response.context['evento'], 'pwd')

    def test_profilo_edit_page_view_login_required(self):
        response = self.client.get(reverse('sylvelius:profile_edit'))
        self.assertEqual(response.status_code, 302)
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
        cls.tag1 = Tag.objects.create(nome='elettronica')
        cls.tag2 = Tag.objects.create(nome='abbigliamento')
        cls.tag3 = Tag.objects.create(nome='casa')
        
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
        
        self.assertEqual(len(context['annunci']), 3)
        self.assertIn(self.annuncio1, context['annunci'])
        self.assertIn(self.annuncio2, context['annunci'])
        self.assertIn(self.annuncio3, context['annunci'])
        
        self.assertEqual(context['page'], 1)
        self.assertFalse(context['has_next'])
        self.assertFalse(context['has_previous'])

    def test_ricerca_per_testo(self):
        request = self.factory.get(reverse('sylvelius:ricerca_annunci'), {'q': 'Smartphone'})
        view = RicercaAnnunciView()
        view.request = request
        
        context = view.get_context_data()
        self.assertEqual(len(context['annunci']), 1)
        self.assertIn(self.annuncio1, context['annunci'])
        
        request = self.factory.get(reverse('sylvelius:ricerca_annunci'), {'q': 'caldo'})
        view.request = request
        
        context = view.get_context_data()
        self.assertEqual(len(context['annunci']), 1)
        self.assertIn(self.annuncio2, context['annunci'])
        
        request = self.factory.get(reverse('sylvelius:ricerca_annunci'), {'q': 'elettronica'})
        view.request = request
        
        context = view.get_context_data()
        self.assertEqual(len(context['annunci']), 1)
        self.assertIn(self.annuncio1, context['annunci'])

    def test_filtro_categoria(self):
        request = self.factory.get(reverse('sylvelius:ricerca_annunci'), {'categoria': 'elettronica'})
        view = RicercaAnnunciView()
        view.request = request
        
        context = view.get_context_data()
        self.assertEqual(len(context['annunci']), 1)
        self.assertIn(self.annuncio1, context['annunci'])
        
        request = self.factory.get(reverse('sylvelius:ricerca_annunci'), {'categoria': 'elettronica,casa'})
        view = RicercaAnnunciView()
        view.request = request
        
        context = view.get_context_data()
        self.assertEqual(len(context['annunci']), 0)
        
        request = self.factory.get(reverse('sylvelius:ricerca_annunci'), {'categoria': 'Inesistente'})
        view.request = request
        
        context = view.get_context_data()
        self.assertEqual(len(context['annunci']), 0)

        request = self.factory.get(reverse('sylvelius:ricerca_annunci'), {'categoria': ' '})
        view.request = request
        
        context = view.get_context_data()
        self.assertEqual(len(context['annunci']), 3)

        request = self.factory.get(reverse('sylvelius:ricerca_annunci'), {'categoria': '  , , ,, ,   ,elettronica,, ,  ,'})
        view.request = request
        
        context = view.get_context_data()
        self.assertEqual(len(context['annunci']), 1)

    def test_filtro_condizione(self):
        request = self.factory.get(reverse('sylvelius:ricerca_annunci'), {'condition': 'nuovo'})
        view = RicercaAnnunciView()
        view.request = request
        
        context = view.get_context_data()
        self.assertEqual(len(context['annunci']), 2)
        self.assertIn(self.annuncio1, context['annunci'])
        
        request = self.factory.get(reverse('sylvelius:ricerca_annunci'), {'condition': 'usato'})
        view.request = request
        
        context = view.get_context_data()
        self.assertEqual(len(context['annunci']), 1)
        self.assertIn(self.annuncio2, context['annunci'])
        
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
        request = self.factory.get(reverse('sylvelius:ricerca_annunci'), {'qta_mag': 'qta-pres'})
        view = RicercaAnnunciView()
        view.request = request
        
        context = view.get_context_data()
        self.assertEqual(len(context['annunci']), 2)
        self.assertIn(self.annuncio1, context['annunci'])
        self.assertIn(self.annuncio3, context['annunci'])
        
        request = self.factory.get(reverse('sylvelius:ricerca_annunci'), {'qta_mag': 'qta-manc'})
        view.request = request
        
        context = view.get_context_data()
        self.assertEqual(len(context['annunci']), 1)
        self.assertIn(self.annuncio2, context['annunci'])

    def test_filtro_rating(self):
        request = self.factory.get(reverse('sylvelius:ricerca_annunci'), {'search_by_rating': '4'})
        view = RicercaAnnunciView()
        view.request = request
        
        context = view.get_context_data()
        self.assertEqual(len(context['annunci']), 1)
        self.assertIn(self.annuncio1, context['annunci'])
        
        request = self.factory.get(reverse('sylvelius:ricerca_annunci'), {'search_by_rating': '2'})
        view.request = request
        
        context = view.get_context_data()
        self.assertEqual(len(context['annunci']), 1)
        self.assertIn(self.annuncio3, context['annunci'])
        
        request = self.factory.get(reverse('sylvelius:ricerca_annunci'), {'search_by_rating': 'starred'})
        view.request = request
        
        context = view.get_context_data()
        self.assertEqual(len(context['annunci']), 2)
        self.assertIn(self.annuncio1, context['annunci'])
        self.assertIn(self.annuncio3, context['annunci'])
        
        request = self.factory.get(reverse('sylvelius:ricerca_annunci'), {'search_by_rating': 'none'})
        view.request = request
        
        context = view.get_context_data()
        self.assertEqual(len(context['annunci']), 1)
        self.assertIn(self.annuncio2, context['annunci'])
        
        request = self.factory.get(reverse('sylvelius:ricerca_annunci'), {'search_by_rating': 'invalid'})
        view.request = request
        
        context = view.get_context_data()
        self.assertEqual(len(context['annunci']), 3)

        request = self.factory.get(reverse('sylvelius:ricerca_annunci'), {'search_by_rating': '100'})
        view.request = request
        
        context = view.get_context_data()
        self.assertEqual(len(context['annunci']), 3)

    def test_filtro_prezzo(self):
        request = self.factory.get(reverse('sylvelius:ricerca_annunci'), {'prezzo_min': '100'})
        view = RicercaAnnunciView()
        view.request = request
        
        context = view.get_context_data()
        self.assertEqual(len(context['annunci']), 2)
        self.assertIn(self.annuncio1, context['annunci'])
        self.assertIn(self.annuncio3, context['annunci'])
        
        request = self.factory.get(reverse('sylvelius:ricerca_annunci'), {'prezzo_max': '100'})
        view.request = request
        
        context = view.get_context_data()
        self.assertEqual(len(context['annunci']), 1)
        self.assertIn(self.annuncio2, context['annunci'])
        
        request = self.factory.get(reverse('sylvelius:ricerca_annunci'), {'prezzo_min': '50', 'prezzo_max': '200'})
        view.request = request
        
        context = view.get_context_data()
        self.assertEqual(len(context['annunci']), 1)
        self.assertIn(self.annuncio3, context['annunci'])
        
        request = self.factory.get(reverse('sylvelius:ricerca_annunci'), {'prezzo_min': 'invalid', 'prezzo_max': 'invalid'})
        view.request = request
        
        context = view.get_context_data()
        self.assertEqual(len(context['annunci']), 3)

    def test_ordinamento_risultati(self):
        request = self.factory.get(reverse('sylvelius:ricerca_annunci'), {'sort': 'data-desc'})
        view = RicercaAnnunciView()
        view.request = request
        
        context = view.get_context_data()
        self.assertEqual(context['annunci'][0], self.annuncio3)
        self.assertEqual(context['annunci'][1], self.annuncio2)
        self.assertEqual(context['annunci'][2], self.annuncio1)
        
        request = self.factory.get(reverse('sylvelius:ricerca_annunci'), {'sort': 'data-asc'})
        view.request = request
        
        context = view.get_context_data()
        self.assertEqual(context['annunci'][0], self.annuncio1)
        self.assertEqual(context['annunci'][1], self.annuncio2)
        self.assertEqual(context['annunci'][2], self.annuncio3)
        
        request = self.factory.get(reverse('sylvelius:ricerca_annunci'), {'sort': 'prezzo-asc'})
        view.request = request
        
        context = view.get_context_data()
        self.assertEqual(context['annunci'][0], self.annuncio2)
        self.assertEqual(context['annunci'][1], self.annuncio3)
        self.assertEqual(context['annunci'][2], self.annuncio1)
        
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
        
        request = self.factory.get(reverse('sylvelius:ricerca_annunci'))
        view = RicercaAnnunciView()
        view.request = request
        
        context = view.get_context_data()
        self.assertEqual(len(context['annunci']), MAX_PAGINATOR_RICERCA_VALUE)
        self.assertEqual(context['page'], 1)
        self.assertTrue(context['has_next'])
        self.assertFalse(context['has_previous'])
        
        request = self.factory.get(reverse('sylvelius:ricerca_annunci'), {'page': '2'})
        view.request = request
        
        context = view.get_context_data()
        self.assertEqual(len(context['annunci']), 5 + 3)  # 5 nuovi + 3 originali - MAX_PAGINATOR_RICERCA_VALUE
        self.assertEqual(context['page'], 2)
        self.assertFalse(context['has_next'])
        self.assertTrue(context['has_previous'])
        
        request = self.factory.get(reverse('sylvelius:ricerca_annunci'), {'page': 'invalid'})
        view.request = request
        
        context = view.get_context_data()
        self.assertEqual(context['page'], 1)

        request = self.factory.get(reverse('sylvelius:ricerca_annunci'), {'page': '0'})
        view.request = request
        
        context = view.get_context_data()
        self.assertEqual(context['page'], 2)

    def test_combinazione_filtri(self):
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
        
        request = self.factory.get(reverse('sylvelius:ricerca_annunci'), {
            'q': 'Smartphone',
            'condition': 'US',
            'prezzo_min': '1000'
        })
        view.request = request
        
        context = view.get_context_data()
        self.assertEqual(len(context['annunci']), 0)

    def test_annunci_non_pubblicati(self):
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

    def test_filtro_inserzionista(self):
        request = self.factory.get(reverse('sylvelius:ricerca_annunci'), {'inserzionista': 'testuser'})
        request.user = self.user 
        view = RicercaAnnunciView()
        view.request = request
        
        context = view.get_context_data()
        self.assertEqual(len(context['annunci']), 3)
        self.assertIn(self.annuncio1, context['annunci'])
        self.assertIn(self.annuncio2, context['annunci'])
        self.assertIn(self.annuncio3, context['annunci'])
        
        request = self.factory.get(reverse('sylvelius:ricerca_annunci'), {'inserzionista': 'nonexistent'})
        request.user = self.user 
        view.request = request
        
        context = view.get_context_data()
        self.assertEqual(len(context['annunci']), 0)

    def test_filtro_inserzionista_con_moderatore(self):
        moderator = get_user_model().objects.create_user(username='moderator', password='12345')
        moderator.groups.create(name=_MODS_GRP_NAME)
        
        prod_privato = Prodotto.objects.create(
            nome='Prodotto Privato Moderatore',
            descrizione_breve='Dovrebbe apparire solo per moderatori',
            prezzo=100,
            condizione='nuovo'
        )
        annuncio_privato = Annuncio.objects.create(
            prodotto=prod_privato,
            inserzionista=self.user,
            qta_magazzino=1,
            is_published=False
        )
        
        request = self.factory.get(reverse('sylvelius:ricerca_annunci'), {'inserzionista': 'testuser'})
        request.user = moderator
        view = RicercaAnnunciView()
        view.request = request
        
        context = view.get_context_data()
        self.assertEqual(len(context['annunci']), 4)  # 3 pubblicati + 1 non pubblicato
        self.assertIn(annuncio_privato, context['annunci'])

    def test_filtri_vuoti_o_invalidi(self):
        request = self.factory.get(reverse('sylvelius:ricerca_annunci'), {
            'q': '',
            'categoria': '',
            'condition': '',
            'search_by_rating': '',
            'prezzo_min': '',
            'prezzo_max': '',
            'qta_mag': ''
        })
        view = RicercaAnnunciView()
        view.request = request
        
        context = view.get_context_data()
        self.assertEqual(len(context['annunci']), 3)  
        request = self.factory.get(reverse('sylvelius:ricerca_annunci'), {
            'prezzo_min': 'abc',
            'prezzo_max': 'def',
            'page': 'invalid'
        })
        view.request = request
        
        context = view.get_context_data()
        self.assertEqual(len(context['annunci']), 3)  # Dovrebbe ignorare i filtri non validi
        self.assertEqual(context['page'], 1)  # Dovrebbe tornare alla pagina 1

    def test_ordinamento_rating(self):
        request = self.factory.get(reverse('sylvelius:ricerca_annunci'), {'sort': 'best-star'})
        view = RicercaAnnunciView()
        view.request = request
        
        context = view.get_context_data()
        self.assertEqual(context['annunci'][0], self.annuncio1)
        self.assertEqual(context['annunci'][1], self.annuncio3)
        self.assertEqual(context['annunci'][2], self.annuncio2)
        
        request = self.factory.get(reverse('sylvelius:ricerca_annunci'), {'sort': 'worst-star'})
        view.request = request
        
        context = view.get_context_data()
        self.assertEqual(context['annunci'][0], self.annuncio2)
        self.assertEqual(context['annunci'][1], self.annuncio3)
        self.assertEqual(context['annunci'][2], self.annuncio1)

    def test_annunci_utente_disattivato(self):
        self.user.is_active = False
        self.user.save()
        
        request = self.factory.get(reverse('sylvelius:ricerca_annunci'))
        view = RicercaAnnunciView()
        view.request = request
        
        context = view.get_context_data()
        self.assertEqual(len(context['annunci']), 0)
        
        self.user.is_active = True
        self.user.save()

class TestModeratoreAccessForbiddenMixin(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.normal_user = User.objects.create_user(username='normale', password='test123')
        cls.moderatore_user = User.objects.create_user(username='moderatore', password='test123')
        
        moderatori_group = Group.objects.create(name=_MODS_GRP_NAME)
        cls.moderatore_user.groups.add(moderatori_group)
        
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
        """Verifica che il controllo funzioni solo per il gruppo _MODS_GRP_NAME"""
        altro_group = Group.objects.create(name='altro_gruppo')
        user = User.objects.create_user(username='altro', password='test123')
        user.groups.add(altro_group)
        
        request = self.factory.get('/')
        request.user = user
        response = self.test_view(request)
        self.assertEqual(response.status_code, 200)

class ProfiloDetailsPageViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        
        self.normal_user = User.objects.create_user(
            username='normaluser',
            password='testpass123',
            is_active=True
        )
        
        self.moderator_user = User.objects.create_user(
            username='moderator',
            password='modpass123',
            is_active=True
        )
        
        moderator_group = Group.objects.create(name=_MODS_GRP_NAME)
        self.moderator_user.groups.add(moderator_group)
        
        self.prodotto1 = Prodotto.objects.create(
            nome='Prodotto 1',
            descrizione_breve='Descrizione breve 1',
            prezzo=10.00,
            iva=22,
            condizione='nuovo'
        )
        
        self.prodotto2 = Prodotto.objects.create(
            nome='Prodotto 2',
            descrizione_breve='Descrizione breve 2',
            prezzo=20.00,
            iva=22,
            condizione='usato'
        )
        
        self.annuncio1 = Annuncio.objects.create(
            inserzionista=self.normal_user,
            prodotto=self.prodotto1,
            is_published=True
        )
        
        self.annuncio2 = Annuncio.objects.create(
            inserzionista=self.normal_user,
            prodotto=self.prodotto2,
            is_published=False
        )
        
        self.commento1 = CommentoAnnuncio.objects.create(
            annuncio=self.annuncio1,
            utente=self.moderator_user,
            testo='Ottimo prodotto!',
            rating=5
        )
        
        self.commento2 = CommentoAnnuncio.objects.create(
            annuncio=self.annuncio1,
            utente=self.normal_user,
            testo='Buono ma non eccezionale',
            rating=3
        )
        
        self.normal_user_url = reverse('sylvelius:dettagli_profilo', kwargs={'user_profile': self.normal_user.username})
        self.moderator_user_url = reverse('sylvelius:dettagli_profilo', kwargs={'user_profile': self.moderator_user.username})

    def test_get_queryset_for_moderator_user(self):
        """Test che un moderatore possa vedere tutti gli annunci, anche non pubblicati"""
        self.client.force_login(self.moderator_user)
        response = self.client.get(self.normal_user_url)
        
        self.assertEqual(response.status_code, 200)
        
        self.assertEqual(response.context['annunci_count'], 2)
        
        annunci_in_context = response.context['annunci']
        self.assertEqual(len(annunci_in_context), 2)
        
    def test_get_queryset_for_normal_user(self):
        """Test che un utente normale veda solo gli annunci pubblicati"""
        self.client.force_login(self.normal_user)
        response = self.client.get(self.normal_user_url)
        
        self.assertEqual(response.status_code, 200)
        
        self.assertEqual(response.context['annunci_count'], 1)
        
        annunci_in_context = response.context['annunci']
        self.assertEqual(len(annunci_in_context), 1)
        self.assertEqual(annunci_in_context[0].prodotto.nome, 'Prodotto 1')
        
    def test_normal_user_cannot_view_moderator_profile(self):
        """Test che un utente normale non possa vedere il profilo di un moderatore"""
        self.client.force_login(self.normal_user)
        response = self.client.get(self.moderator_user_url)
        self.assertEqual(response.status_code, 404)
            
    def test_moderator_can_view_moderator_profile(self):
        """Test che un moderatore possa vedere il profilo di un altro moderatore"""
        another_moderator = User.objects.create_user(
            username='anothermod',
            password='modpass123',
            is_active=True
        )
        another_moderator.groups.add(Group.objects.get(name=_MODS_GRP_NAME))
        
        url = reverse('sylvelius:dettagli_profilo', kwargs={'user_profile': another_moderator.username})
        self.client.force_login(self.moderator_user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        
    def test_pagination_of_comments(self):
        """Test che i commenti siano paginati correttamente"""
        for i in range(MAX_PAGINATOR_COMMENTI_DETTAGLI_VALUE + 5):
            prodotto = Prodotto.objects.create(
                nome=f'Prodotto Commento {i}',
                descrizione_breve=f'Descrizione breve {i}',
                prezzo=10.00 + i,
                iva=22,
                condizione='nuovo'
            )
            annuncio = Annuncio.objects.create(
                inserzionista=self.normal_user,
                prodotto=prodotto,
                is_published=True
            )
            CommentoAnnuncio.objects.create(
                annuncio=annuncio,
                utente=self.normal_user,
                testo=f'Commento {i}',
                rating=4
            )

        self.client.force_login(self.moderator_user)
        response = self.client.get(self.normal_user_url + '?page=2')

        self.assertFalse(response.context['has_next'])
        self.assertTrue(response.context['has_previous'])
        self.assertEqual(response.context['page'], 2)

        commenti_in_context = response.context['commenti']
        self.assertLessEqual(len(commenti_in_context), MAX_PAGINATOR_COMMENTI_DETTAGLI_VALUE)
        
    def test_inactive_user_profile_returns_404(self):
        """Test che il profilo di un utente inattivo restituisca 404"""
        inactive_user = User.objects.create_user(
            username='inactive',
            password='testpass123',
            is_active=False
        )
        
        url = reverse('sylvelius:dettagli_profilo', kwargs={'user_profile': inactive_user.username})
        self.client.force_login(self.normal_user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)
            
    def test_annunci_ordered_by_rating(self):
        """Test che gli annunci siano ordinati per rating medio"""
        prodotto3 = Prodotto.objects.create(
            nome='Prodotto 3',
            descrizione_breve='Descrizione breve 3',
            prezzo=30.00,
            iva=22,
            condizione='nuovo'
        )
        annuncio3 = Annuncio.objects.create(
            inserzionista=self.normal_user,
            prodotto=prodotto3,
            is_published=True
        )
        
        CommentoAnnuncio.objects.create(
            annuncio=annuncio3,
            utente=self.moderator_user,
            testo='Eccellente!',
            rating=5
        )
        CommentoAnnuncio.objects.create(
            annuncio=annuncio3,
            utente=self.normal_user,
            testo='Fantastico',
            rating=5
        )
        
        self.client.force_login(self.moderator_user)
        response = self.client.get(self.normal_user_url)
        
        annunci_in_context = response.context['annunci']
        self.assertEqual(annunci_in_context[0].prodotto.nome, 'Prodotto 3')
        
    def test_max_annunci_per_dettagli_value(self):
        """Test che vengano mostrati al massimo MAX_ANNUNCI_PER_DETTAGLI_VALUE annunci"""
        for i in range(MAX_ANNUNCI_PER_DETTAGLI_VALUE + 5):
            prodotto = Prodotto.objects.create(
                nome=f'Extra Prodotto {i}',
                descrizione_breve=f'Descrizione breve {i}',
                prezzo=10.00 + i,
                iva=22,
                condizione='nuovo'
            )
            Annuncio.objects.create(
                inserzionista=self.normal_user,
                prodotto=prodotto,
                is_published=True
            )
        
        self.client.force_login(self.moderator_user)
        response = self.client.get(self.normal_user_url)
        
        annunci_in_context = response.context['annunci']
        self.assertEqual(len(annunci_in_context), MAX_ANNUNCI_PER_DETTAGLI_VALUE)
        
        self.assertEqual(response.context['annunci_count'], MAX_ANNUNCI_PER_DETTAGLI_VALUE + 5 + 2)
