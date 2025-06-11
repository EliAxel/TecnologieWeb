from django.db import models
from progetto_tw.constants import MAX_ORDN_INVOICE_CHARS

# Create your models here.
class Invoice(models.Model):
    invoice_id = models.CharField(max_length=MAX_ORDN_INVOICE_CHARS, unique=True)
    user_id = models.PositiveIntegerField()
    quantita = models.PositiveIntegerField()
    prodotto_id = models.PositiveIntegerField()