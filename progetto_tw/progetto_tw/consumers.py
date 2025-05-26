import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from sylvelius.models import Annuncio
from django.db.models import Q
from sylvelius.models import Tag

class SearchConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()

    async def disconnect(self, close_code):
        pass

    async def receive(self, text_data):
        data = json.loads(text_data)
        query = data.get('query', '').strip()
        suggestions = []

        if query:
            # Cerca titoli di Annuncio che contengono la query (case-insensitive)
            annunci = await self.get_annunci_by_query(query)
            suggestions = [a.titolo for a in annunci][:10]

        await self.send(text_data=json.dumps({
            'suggestions': suggestions
        }))

    @database_sync_to_async
    def get_annunci_by_query(self, query):
        # Trova annunci dove almeno una parola del titolo inizia per la query (case-insensitive)

        # Split il titolo in parole e cerca quelle che iniziano per la query
        # Usa regex per trovare parole che iniziano per la query
        regex = r'\b' + query
        return list(
            Annuncio.objects.filter(
                Q(titolo__iregex=regex),
                is_published=True
            ).order_by('titolo')
        )

class SearchTags(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()

    async def disconnect(self, close_code):
        pass

    async def receive(self, text_data):
        data = json.loads(text_data)
        query = data.get('query', '').strip()
        suggestions = []

        if query:
            # Cerca tag che contengono la query (case-insensitive)
            suggestions = await self.get_tags_by_query(query)

        await self.send(text_data=json.dumps({
            'suggestions': suggestions
        }))

    @database_sync_to_async
    def get_tags_by_query(self, query):
        # Trova tag che contengono la query (case-insensitive)
        return list(
            Tag.objects.filter(nome__icontains=query).values_list('nome', flat=True).order_by('nome')[:10]
        )
