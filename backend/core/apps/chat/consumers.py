import json
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from authentication.models import Player
from .models import Message


class ChatConsumer(AsyncWebsocketConsumer):