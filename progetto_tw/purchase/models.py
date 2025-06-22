from django.db import models
from progetto_tw.constants import MAX_ORDN_INVOICE_CHARS, IBAN_LENGTH
from sylvelius.models import Prodotto

# Create your models here.
class Invoice(models.Model):
    invoice_id = models.CharField(max_length=MAX_ORDN_INVOICE_CHARS, unique=True)
    utente = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='invoices', null=True)
    quantita = models.PositiveIntegerField()
    prodotto = models.ForeignKey(Prodotto, on_delete=models.CASCADE, related_name='invoices', null=True)
    cart = models.ForeignKey('Cart', on_delete=models.CASCADE, related_name='invoices', null=True)

    @property
    def total(self):
        return self.prodotto.prezzo * self.quantita # type: ignore

class Iban(models.Model):
    utente = models.OneToOneField('auth.User', on_delete=models.CASCADE, related_name='iban')
    iban = models.CharField(max_length=IBAN_LENGTH,blank=True, null=True)

class Cart(models.Model):
    utente  = models.OneToOneField('auth.User', on_delete=models.CASCADE, related_name='cart')
    uuid = models.CharField(max_length=MAX_ORDN_INVOICE_CHARS, unique=True, null=True)

    @property
    def total(self):
        invoices = self.invoices.select_related('prodotto').all() #type:ignore
        return sum(invoice.total for invoice in invoices)