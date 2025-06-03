import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from sylvelius.models import Annuncio
from django.db.models import Q
from sylvelius.models import Tag
from progetto_tw.constants import MAX_WS_QUERIES

class SearchConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()

    async def disconnect(self, close_code):
        pass

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            query = data.get('query', '').strip()
            
            if query:
                suggestions = await self.get_suggestions(query)
            else:
                suggestions = []

            await self.send(text_data=json.dumps({
                'suggestions': suggestions
            }))
        except Exception as e:
            await self.send(text_data=json.dumps({
                'error': str(e)
            }))

    @database_sync_to_async
    def get_suggestions(self, query):
        # Versione più sicura della regex
        regex = r'\b' + query  # \m è l'equivalente di \b ma più robusto per le regex PostgreSQL
        annunci = Annuncio.objects.filter(
            Q(prodotto__nome__iregex=regex),
            is_published=True
        ).order_by('prodotto__nome').select_related('prodotto')[:MAX_WS_QUERIES]
        
        return [annuncio.prodotto.nome for annuncio in annunci]

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
            Tag.objects.filter(nome__icontains=query).values_list('nome', flat=True).order_by('nome')[:MAX_WS_QUERIES]
        )
