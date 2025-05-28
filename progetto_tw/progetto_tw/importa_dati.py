import json
import os
import django
from django.contrib.auth.models import User
from sylvelius.models import Annuncio, ImmagineProdotto, Ordine, Creazione, Tag, Prodotto

# Imposta le variabili d'ambiente per Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'progetto_tw.settings')
django.setup()

def delete_db():
    ImmagineProdotto.objects.all().delete()
    Creazione.objects.all().delete()
    Ordine.objects.all().delete()
    Annuncio.objects.all().delete()
    Prodotto.objects.all().delete()
    Tag.objects.all().delete()


def init_db():
    with open('static/json/dati.json', 'r', encoding='utf-8') as file:
        dati = json.load(file)

    # Importa Prodotti
    for prodotto_data in dati.get('prodotti', []):
        prodotto, created = Prodotto.objects.update_or_create(
            id=prodotto_data['id'],
            defaults={
                'nome': prodotto_data['nome'],
                'descrizione_breve': prodotto_data.get('descrizione_breve', ''),
                'prezzo': prodotto_data['prezzo'],
            }
        )

        # Gestione dei tag
        tag_names = prodotto_data.get('tag', [])
        prodotto.tags.clear()
        for tag_name in tag_names:
            tag_obj, _ = Tag.objects.get_or_create(nome=tag_name.lower())
            prodotto.tags.add(tag_obj)

        # Gestione delle immagini
        immagini = prodotto_data.get('immagini', []) or []
        prodotto.immagini.all().delete()
        for img in immagini:
            ImmagineProdotto.objects.create(
                prodotto=prodotto,
                immagine=img['immagine']
            )

    # Importa Annunci
    for annuncio_data in dati.get('annunci', []):
        try:
            prodotto = Prodotto.objects.get(id=annuncio_data['prodotto_id'])
        except Prodotto.DoesNotExist:
            continue

        Annuncio.objects.update_or_create(
            prodotto=prodotto,
            defaults={
                'data_pubblicazione': annuncio_data.get('data_pubblicazione'),
                'qta_magazzino': annuncio_data.get('qta_magazzino', 0),
                'is_published': annuncio_data.get('is_published', True)
            }
        )

    # Importa Ordini
    for ordine_data in dati.get('ordini', []):
        try:
            utente = User.objects.get(username=ordine_data['utente_username'])
        except User.DoesNotExist:
            continue

        try:
            prodotto = Prodotto.objects.get(id=ordine_data['prodotto_id']) 
        except Prodotto.DoesNotExist:
            continue

        Ordine.objects.update_or_create(
            utente=utente,
            prodotto=prodotto,
            data_ordine=ordine_data.get('data_ordine'),
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
            prodotto = Prodotto.objects.get(id=creazione_data['prodotto_id'])
            annuncio = Annuncio.objects.filter(prodotto=prodotto).first()
            if not annuncio:
                continue
        except Prodotto.DoesNotExist:
            continue

        Creazione.objects.update_or_create(
            utente=utente,
            annuncio=annuncio,
            defaults={
                'data_creazione': creazione_data.get('data_creazione')
            }
        )
