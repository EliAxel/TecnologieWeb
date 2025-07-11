import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from sylvelius.models import Annuncio, Tag
from django.db.models import Q
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
        regex = r'\b' + query  
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
            suggestions = await self.get_tags_by_query(query)

        await self.send(text_data=json.dumps({
            'suggestions': suggestions
        }))

    @database_sync_to_async
    def get_tags_by_query(self, query):
        return list(
            Tag.objects.filter(nome__icontains=query).values_list('nome', flat=True).order_by('nome')[:MAX_WS_QUERIES]
        )
    
class GetNotifications(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        if self.user.is_anonymous:
            await self.close()
        else:
            # Gruppi personali e globali
            self.personal_group = f"user_{self.user.id}"
            self.global_group = "global"

            await self.channel_layer.group_add(self.personal_group, self.channel_name)#type: ignore
            await self.channel_layer.group_add(self.global_group, self.channel_name)#type: ignore

            await self.accept()

    async def disconnect(self, close_code):
        self.user = self.scope["user"]
        if self.user.is_anonymous:
            await self.close()
        else:
            await self.channel_layer.group_discard(self.personal_group, self.channel_name)#type: ignore
            await self.channel_layer.group_discard(self.global_group, self.channel_name) #type: ignore

    async def send_notification(self, event):
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'title': event['title'],
            'message': event['message']
        }))
