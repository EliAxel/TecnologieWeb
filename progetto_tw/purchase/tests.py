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

class FakePurchaseTests(TestCase):

    def setUp(self):
       self.post_data = {
           'amount': 1.0,
           'item_name': ''
       } 
        