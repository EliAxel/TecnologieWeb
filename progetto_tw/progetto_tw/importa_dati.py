import json
import os
import django

# Imposta le variabili d'ambiente per Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'progetto_tw.settings')
django.setup()

from django.contrib.auth.models import User
from sylvelius.models import Annuncio, Ordine, Creazione
from datetime import datetime

def delete_db():
    # Elimina tutti gli oggetti esistenti
    Annuncio.objects.all().delete()
    Ordine.objects.all().delete()
    Creazione.objects.all().delete()

import json
from django.contrib.auth.models import User
from sylvelius.models import Annuncio, Ordine, Creazione

def init_db():
    # Carica il file JSON
    with open('static/json/dati.json', 'r', encoding='utf-8') as file:
        dati = json.load(file)

    # Importa Annunci
    for annuncio_data in dati.get('annunci', []):
        annuncio, created = Annuncio.objects.update_or_create(
            id=annuncio_data['id'],
            defaults={
                'titolo': annuncio_data['titolo'],
                'descrizione': annuncio_data['descrizione'],
                'prezzo': annuncio_data['prezzo'],
                'data_pubblicazione': annuncio_data['data_pubblicazione'],
                'immagine': annuncio_data['immagine'],
            }
        )

    # Importa Ordini
    for ordine_data in dati.get('ordini', []):
        try:
            utente = User.objects.get(username=ordine_data['utente_username'])
        except User.DoesNotExist:
            continue

        try:
            annuncio = Annuncio.objects.get(id=ordine_data['annuncio_id'])
        except Annuncio.DoesNotExist:
            continue

        ordine, created = Ordine.objects.update_or_create(
            utente=utente,
            annuncio=annuncio,
            data_ordine=ordine_data['data_ordine'],
            defaults={
                'quantita': ordine_data['quantita'],
                'stato': ordine_data['stato'],
            }
        )

    # Importa Creazioni
    for creazione_data in dati.get('creazioni', []):
        try:
            utente = User.objects.get(username=creazione_data['utente_username'])
        except User.DoesNotExist:
            continue

        try:
            annuncio = Annuncio.objects.get(id=creazione_data['annuncio_id'])
        except Annuncio.DoesNotExist:
            continue

        creazione, created = Creazione.objects.update_or_create(
            utente=utente,
            annuncio=annuncio,
            defaults={
                'data_creazione': creazione_data['data_creazione']
            }
        )
