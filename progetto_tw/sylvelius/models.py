from django.db import models

# Create your models here.
class Tag(models.Model):
    nome = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.nome

    def save(self, *args, **kwargs):
        self.nome = self.nome.lower()  # Converti in minuscolo
        super().save(*args, **kwargs)

class Prodotto(models.Model):
    nome = models.CharField(max_length=255)
    descrizione_breve = models.CharField(max_length=255, blank=True, null=True)
    descrizione = models.TextField(blank=True, null=True)
    prezzo = models.DecimalField(max_digits=10, decimal_places=2)
    tags = models.ManyToManyField(Tag, related_name='prodotti', blank=True)

class Annuncio(models.Model):
    prodotto = models.OneToOneField(Prodotto, on_delete=models.CASCADE, related_name='annunci')
    data_pubblicazione = models.DateTimeField(auto_now_add=True)
    qta_magazzino = models.PositiveIntegerField(default=0)
    is_published = models.BooleanField(default=True)

    def __str__(self):
        return self.prodotto.nome

class ImmagineProdotto(models.Model):
    prodotto = models.ForeignKey(Prodotto, on_delete=models.CASCADE, related_name='immagini')
    immagine = models.ImageField(upload_to='prodotti/immagini/', blank=True, null=True)

    def __str__(self):
        return f"Immagine di {self.prodotto.nome}"

class Ordine(models.Model):
    utente = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='ordini')
    prodotto = models.ForeignKey(Prodotto, on_delete=models.CASCADE, related_name='ordini')
    quantita = models.PositiveIntegerField()
    stato = models.CharField(max_length=20, choices=[('in attesa', 'In attesa'), ('completato', 'Completato')], default='in attesa')
    data_ordine = models.DateTimeField(auto_now_add=True)
    luogo_consegna = models.CharField(max_length=255, blank=True, null=True)

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