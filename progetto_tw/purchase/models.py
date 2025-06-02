from django.db import models

# Create your models here.
class Invoice(models.Model):
    invoice_id = models.CharField(max_length=255, unique=True)
    user_id = models.PositiveIntegerField()
    quantita = models.PositiveIntegerField()
    prodotto_id = models.PositiveIntegerField()