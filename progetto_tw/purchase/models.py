from django.db import models
from progetto_tw.constants import MAX_ORDN_INVOICE_CHARS, IBAN_LENGTH
from sylvelius.models import Prodotto

# Create your models here.
class Invoice(models.Model):
    uuid = models.CharField(max_length=MAX_ORDN_INVOICE_CHARS, unique=True)
    utente = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='invoices', null=True)
    quantita = models.PositiveIntegerField()
    prodotto = models.ForeignKey(Prodotto, on_delete=models.CASCADE, related_name='invoices', null=True)
    cart = models.ForeignKey('Cart', on_delete=models.CASCADE, related_name='invoices', null=True)

    @property
    def total(self):
        return self.prodotto.prezzo * self.quantita # type: ignore
    
    def __str__(self):
        utnt = "utente" if not self.utente else self.utente.username
        prd = "prodotto" if not self.prodotto else self.prodotto.nome
        return self.uuid + " - " + utnt + f" ({prd})"

class Iban(models.Model):
    utente = models.OneToOneField('auth.User', on_delete=models.CASCADE, related_name='iban')
    iban = models.CharField(max_length=IBAN_LENGTH,blank=True, null=True)

    def __str__(self):
        ibn = "IBAN" if not self.iban else self.iban
        return ibn + " - " + self.utente.username

class Cart(models.Model):
    utente  = models.OneToOneField('auth.User', on_delete=models.CASCADE, related_name='cart')
    uuid = models.CharField(max_length=MAX_ORDN_INVOICE_CHARS, unique=True, null=True)

    @property
    def total(self):
        invoices = self.invoices.select_related('prodotto').all() #type:ignore
        return sum(invoice.total for invoice in invoices)
    
    def __str__(self):
        return "Carrello di " + self.utente.username