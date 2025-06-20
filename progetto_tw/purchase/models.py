from django.db import models
from progetto_tw.constants import MAX_ORDN_INVOICE_CHARS, IBAN_LENGTH

# Create your models here.
class Invoice(models.Model):
    invoice_id = models.CharField(max_length=MAX_ORDN_INVOICE_CHARS, unique=True)
    user_id = models.PositiveIntegerField()
    quantita = models.PositiveIntegerField()
    prodotto_id = models.PositiveIntegerField()
    cart = models.ForeignKey('Cart', on_delete=models.CASCADE, related_name='invoices', null=True)

class Iban(models.Model):
    utente = models.OneToOneField('auth.User', on_delete=models.CASCADE, related_name='iban')
    iban = models.CharField(max_length=IBAN_LENGTH,blank=True, null=True)

class Cart(models.Model):
    utente  = models.OneToOneField('auth.User', on_delete=models.CASCADE, related_name='cart')