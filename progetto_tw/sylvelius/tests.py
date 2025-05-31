from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse

# Create your tests here.
class AnonUrlsTestCase(TestCase):
    def test_home_page(self):
        response = self.client.get('/')
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

    def test_annuncio_profilo_creazioni(self):
        response = self.client.get('/account/profilo/creazioni/')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('sylvelius:login') + "?auth=error&next=/account/profilo/creazioni/") # type: ignore
    
    def test_annuncio_profilo_creazioni_crea(self):
        response = self.client.get('/account/profilo/creazioni/crea/')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('sylvelius:login') + "?auth=error&next=/account/profilo/creazioni/crea/") # type: ignore
    
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

    def test_pagamento(self):
        response = self.client.get('/pagamento/')
        self.assertEqual(response.status_code, 405)
    
    def test_pagamento_ok(self):
        response = self.client.get('/pagamento_ok/')
        self.assertEqual(response.status_code, 200)

    def test_pagamento_nonok(self):
        response = self.client.get('/pagamento_nonok/')
        self.assertEqual(response.status_code, 200)

    def test_paypal_pcc(self):
        response = self.client.get('/paypal/pcc/')
        self.assertEqual(response.status_code, 405)
    
    def test_paypal_coa(self):
        response = self.client.get('/paypal/coa/')
        self.assertEqual(response.status_code, 405)

class LoggedUrlsTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='Testpass0')
        self.client.login(username='testuser', password='Testpass0')

    def test_profilo_page(self):
        response = self.client.get('/account/profilo/')
        self.assertEqual(response.status_code, 200)

    def test_profilo_edit_page(self):
        response = self.client.get('/account/profilo/modifica/')
        self.assertEqual(response.status_code, 200)

    def test_profilo_delete_page(self):
        response = self.client.get('/account/profilo/elimina/')
        self.assertEqual(response.status_code, 200)