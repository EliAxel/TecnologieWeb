from django.db import models
import json
from django.core.validators import MinValueValidator, MaxValueValidator
from progetto_tw.constants import (
    MAX_TAGS_CHARS,
    MAX_PROD_NOME_CHARS,
    MAX_PROD_DESC_BR_CHARS,
    MAX_PROD_DESC_CHARS,
    MIN_PROD_PREZZO_VALUE,
    MAX_PROD_PREZZO_DIGITS_DECIMAL,
    PROD_CONDIZIONE_CHOICES,
    MIN_ANNU_QTA_MAGAZZINO_VALUE,
    MAX_ANNU_QTA_MAGAZZINO_VALUE,
    MAX_COMMNT_TESTO_CHARS,
    MIN_COMMNT_RATING_VALUE,
    MAX_COMMNT_RATING_VALUE,
    MAX_ORDN_INVOICE_CHARS,
    MAX_ANNU_UUID_CHARS,
    MIN_ORDN_QUANTITA_VALUE,
    ORDN_STATO_CONSEGNA_CHOICES,
    INVALID_COMMNT_RATING_VALUE,
    MAX_MESSAGE_MESSAGE_VALUE,
    ALIQUOTE_LIST,
    MAX_MESSAGE_TITLE_VALUE
)


# Create your models here.
class Tag(models.Model):
    nome = models.CharField(max_length=MAX_TAGS_CHARS, unique=True)

    def __str__(self):
        return self.nome

    def save(self, *args, **kwargs):
        self.nome = self.nome.lower()  # Converti in minuscolo
        super().save(*args, **kwargs)

class Prodotto(models.Model):
    nome = models.CharField(max_length=MAX_PROD_NOME_CHARS)
    descrizione_breve = models.CharField(max_length=MAX_PROD_DESC_BR_CHARS)
    descrizione = models.TextField(max_length=MAX_PROD_DESC_CHARS, blank=True, null=True)
    prezzo = models.DecimalField(max_digits=MAX_PROD_PREZZO_DIGITS_DECIMAL[0],
                                  decimal_places=MAX_PROD_PREZZO_DIGITS_DECIMAL[1],
                                  validators=[MinValueValidator(MIN_PROD_PREZZO_VALUE)])
    iva = models.PositiveIntegerField(choices=ALIQUOTE_LIST, default=22)
    condizione = models.CharField(choices=PROD_CONDIZIONE_CHOICES, default='nuovo')
    tags = models.ManyToManyField(Tag, related_name='prodotti', blank=True)

class ImmagineProdotto(models.Model):
    prodotto = models.ForeignKey(Prodotto, on_delete=models.CASCADE, related_name='immagini')
    immagine = models.ImageField(upload_to='prodotti/immagini/', blank=True, null=True)

    def __str__(self):
        return f"Immagine di {self.prodotto.nome}"

class Annuncio(models.Model):
    uuid = models.CharField(max_length=MAX_ANNU_UUID_CHARS, unique=True, blank=True, null=True)
    inserzionista = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='annunci')
    prodotto = models.OneToOneField(Prodotto, on_delete=models.CASCADE, related_name='annunci')
    data_pubblicazione = models.DateTimeField(auto_now_add=True)
    qta_magazzino = models.PositiveIntegerField(
        validators=[
            MinValueValidator(MIN_ANNU_QTA_MAGAZZINO_VALUE),
            MaxValueValidator(MAX_ANNU_QTA_MAGAZZINO_VALUE)
            ],
        default=MIN_ANNU_QTA_MAGAZZINO_VALUE
    )
    is_published = models.BooleanField(default=True)

    def __str__(self):
        return self.prodotto.nome
    
    class Meta:
        ordering = ['-data_pubblicazione']

    @property
    def rating_medio(self):
        commenti = self.commenti.all() # type: ignore
        if not commenti:
            return INVALID_COMMNT_RATING_VALUE
        return sum(commento.rating for commento in commenti) / len(commenti)
    
    @property
    def rating_count(self):
        return self.commenti.count() # type: ignore

class CommentoAnnuncio(models.Model):
    annuncio = models.ForeignKey(Annuncio, on_delete=models.CASCADE, related_name='commenti')
    utente = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='commenti_annunci')
    testo = models.TextField(max_length=MAX_COMMNT_TESTO_CHARS)
    rating = models.PositiveIntegerField(
        validators=[MinValueValidator(MIN_COMMNT_RATING_VALUE), MaxValueValidator(MAX_COMMNT_RATING_VALUE)]
    )
    data_pubblicazione = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.utente.username} su {self.annuncio.prodotto.nome} - {self.rating}/5"

class Ordine(models.Model):
    invoice = models.CharField(max_length=MAX_ORDN_INVOICE_CHARS, unique=True, blank=True, null=True)
    utente = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='ordini')
    prodotto = models.ForeignKey(Prodotto, on_delete=models.CASCADE, related_name='ordini')
    quantita = models.PositiveIntegerField(default=MIN_ORDN_QUANTITA_VALUE,
                                           validators=[MinValueValidator(MIN_ORDN_QUANTITA_VALUE)])
    data_ordine = models.DateTimeField(auto_now_add=True)
    luogo_consegna = models.JSONField(null=True)
    stato_consegna = models.CharField(choices=ORDN_STATO_CONSEGNA_CHOICES, default='da spedire')

    def __str__(self):
        return self.utente.username + " - " + self.prodotto.nome
    
    @property
    def totale(self):
        return self.prodotto.prezzo * self.quantita
    
    @property
    def json_to_string(self):
        return json.dumps(self.luogo_consegna)
    
class Notification(models.Model):
    recipient = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='notifications', null=True, blank=True)
    sender = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='sent_notifications')
    
    title = models.CharField(max_length=MAX_MESSAGE_TITLE_VALUE)
    message = models.CharField(max_length=MAX_MESSAGE_MESSAGE_VALUE)
    created_at = models.DateTimeField(auto_now_add=True)
    read = models.BooleanField(default=False)
    is_global = models.BooleanField(default=False)

    class Meta:
        ordering = ['created_at']
