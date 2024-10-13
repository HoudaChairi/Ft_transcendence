import json
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from authentication.models import Player
from .models import Message


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
    self.room_name = self.scope['url_route']['kwargs']['room_name']
    self.room_group_name = f'chat_{self.room_name}'

    await self.channel_layer.group_add(
        self.room_group_name,
        self.channel_name
    )

    await self.accept()