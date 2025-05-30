from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

# Create your models here.
class Tag(models.Model):
    nome = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.nome

    def save(self, *args, **kwargs):
        self.nome = self.nome.lower()  # Converti in minuscolo
        super().save(*args, **kwargs)

class Prodotto(models.Model):
    nome = models.CharField(max_length=100)
    descrizione_breve = models.CharField(max_length=255)
    descrizione = models.TextField(max_length=3000, blank=True, null=True)
    prezzo = models.DecimalField(max_digits=10, decimal_places=2)
    condizione = models.CharField(max_length=20, choices=[('nuovo', 'Nuovo'), ('usato', 'Usato')], default='nuovo')
    tags = models.ManyToManyField(Tag, related_name='prodotti', blank=True)

class ImmagineProdotto(models.Model):
    prodotto = models.ForeignKey(Prodotto, on_delete=models.CASCADE, related_name='immagini')
    immagine = models.ImageField(upload_to='prodotti/immagini/', blank=True, null=True)

    def __str__(self):
        return f"Immagine di {self.prodotto.nome}"

class Annuncio(models.Model):
    prodotto = models.OneToOneField(Prodotto, on_delete=models.CASCADE, related_name='annunci')
    data_pubblicazione = models.DateTimeField(auto_now_add=True)
    qta_magazzino = models.PositiveIntegerField(default=0)
    is_published = models.BooleanField(default=True)

    def __str__(self):
        return self.prodotto.nome
    
    @property
    def rating_medio(self):
        commenti = self.commenti.all() # type: ignore
        if not commenti:
            return -1
        return sum(commento.rating for commento in commenti) / len(commenti)
    
    @property
    def rating_count(self):
        return self.commenti.count() # type: ignore

class CommentoAnnuncio(models.Model):
    annuncio = models.ForeignKey(Annuncio, on_delete=models.CASCADE, related_name='commenti')
    utente = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='commenti_annunci')
    testo = models.TextField()
    rating = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        help_text="Valutazione da 0 a 5"
    )
    data_pubblicazione = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.utente.username} su {self.annuncio.prodotto.nome} - {self.rating}/5"

class Ordine(models.Model):
    invoice_id = models.CharField(max_length=255, unique=True, blank=True, null=True)
    utente = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='ordini')
    prodotto = models.ForeignKey(Prodotto, on_delete=models.CASCADE, related_name='ordini')
    quantita = models.PositiveIntegerField()
    data_ordine = models.DateTimeField(auto_now_add=True)
    luogo_consegna = models.JSONField(null=True, blank=True)
    stato_consegna = models.CharField(max_length=20, choices=[
        ('da spedire', 'Da spedire'),
        ('spedito', 'Spedito')
    ], default='da spedire')

    def __str__(self):
        return self.utente.username + " - " + self.prodotto.nome
    
    @property
    def totale(self):
        return self.prodotto.prezzo * self.quantita

    
class Creazione(models.Model):
    utente = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='creazioni')
    annuncio = models.ForeignKey(Annuncio, on_delete=models.CASCADE, related_name='creazioni')
    data_creazione = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.utente.username + " - " + self.annuncio.prodotto.nome
    
class Invoice(models.Model):
    invoice_id = models.CharField(max_length=255, unique=True)
    user_id = models.IntegerField()
    quantita = models.PositiveIntegerField()
    prodotto_id = models.IntegerField()