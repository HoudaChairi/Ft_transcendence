from channels.generic.websocket import AsyncWebsocketConsumer
import json

class OnlineStatusConsumer(AsyncWebsocketConsumer):
    online_users = set()

    async def connect(self):
        self.username = self.scope['url_route']['kwargs']['username']
        self.online_users.add(self.username)
        await self.channel_layer.group_add("online_users_group", self.channel_name)

        await self.accept()
        
        await self.broadcast_online_users()

    async def disconnect(self, close_code):
        self.online_users.discard(self.username)
        await self.channel_layer.group_discard("online_users_group", self.channel_name)

        await self.broadcast_online_users()
        

    async def broadcast_online_users(self):
        online_users_list = list(self.online_users)

        await self.channel_layer.group_send(
            "online_users_group",
            {
                'type': 'send_online_users',
                'online_users': online_users_list
            }
        )

    async def send_online_users(self, event):
        online_users_list = event['online_users']
        await self.send(text_data=json.dumps({
            'online_users': online_users_list
        }))