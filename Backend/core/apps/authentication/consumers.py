from channels.generic.websocket import AsyncWebsocketConsumer
import json

class OnlineStatusConsumer(AsyncWebsocketConsumer):
    online_users = set()
    user_status = {}
    game_invites = {}
    active_invites = {}

    async def connect(self):
        self.username = self.scope['url_route']['kwargs']['username']
        self.online_users.add(self.username)
        self.user_status[self.username] = "available"
        await self.channel_layer.group_add("online_users_group", self.channel_name)
        await self.accept()
        await self.broadcast_online_users()

    async def disconnect(self, close_code):
        self.online_users.discard(self.username)
        self.user_status.pop(self.username, None)
        
        # Find and cancel any invites where the disconnecting user is the sender
        invites_to_cancel = [
            invite_id 
            for invite_id, invite in self.game_invites.items()
            if invite['sender'] == self.username
        ]
        
        # Cancel each invite
        for invite_id in invites_to_cancel:
            invite = self.game_invites[invite_id]
            await self.channel_layer.group_send(
                "online_users_group",
                {
                    'type': 'broadcast_invite_response',
                    'invite_id': invite_id,
                    'response': 'cancelled',
                    'sender': self.username,
                    'recipient': invite['recipient'],
                    'message': 'Invite cancelled - sender disconnected'
                }
            )
            del self.game_invites[invite_id]
        
        await self.channel_layer.group_discard("online_users_group", self.channel_name)
        await self.broadcast_online_users()

    async def receive(self, text_data):
        data = json.loads(text_data)
        
        if data['type'] == 'game_invite':
            recipient = data['recipient']
            sender = data['sender']
            
            # Remove any existing invites from this sender
            invites_to_remove = [
                invite_id for invite_id, invite in self.game_invites.items()
                if invite['sender'] == sender
            ]
            
            for invite_id in invites_to_remove:
                # Send cancellation notification
                await self.channel_layer.group_send(
                    "online_users_group",
                    {
                        'type': 'broadcast_invite_response',
                        'invite_id': invite_id,
                        'response': 'cancelled',
                        'sender': sender,
                        'recipient': self.game_invites[invite_id]['recipient']
                    }
                )
                del self.game_invites[invite_id]
            
            if recipient in self.online_users:
                invite_id = f"{sender}_{recipient}"
                self.game_invites[invite_id] = {
                    'sender': sender,
                    'recipient': recipient,
                    'status': 'pending'
                }
                
                await self.channel_layer.group_send(
                    "online_users_group",
                    {
                        'type': 'send_game_invite',
                        'invite_id': invite_id,
                        'recipient': recipient,
                        'sender': sender
                    }
                )
        elif data['type'] == 'invite_response':
            sender = data['sender']
            recipient = data['recipient']
            invite_id = f"{sender}_{recipient}"
            
            if invite_id in self.game_invites:
                await self.handle_invite_response(invite_id, data['response'])

    async def broadcast_invite_response(self, event):
        if self.username in [event['sender'], event['recipient']]:
            await self.send(text_data=json.dumps({
                'type': 'invite_response',
                'invite_id': event['invite_id'],
                'response': event['response'],
                'sender': event['sender'],
                'recipient': event['recipient']
            }))

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
        await self.send(text_data=json.dumps({
            'online_users': event['online_users']
        }))

    async def send_game_invite(self, event):
        if self.username == event['recipient']:
            await self.send(text_data=json.dumps({
                'type': 'game_invite',
                'invite_id': event['invite_id'],
                'sender': event['sender']
            }))

    async def handle_invite_response(self, invite_id: str, response: str):
        if invite_id in self.game_invites:
            invite = self.game_invites[invite_id]
            
            if response == 'accepted':
                # Notify both players to start game
                await self.channel_layer.group_send(
                    "online_users_group",
                    {
                        'type': 'start_game',
                        'sender': invite['sender'],
                        'recipient': invite['recipient']
                    }
                )
            
            del self.game_invites[invite_id]

    async def start_game(self, event):
        if self.username in [event['sender'], event['recipient']]:
            await self.send(text_data=json.dumps({
                'type': 'start_game',
                'sender': event['sender'],
                'recipient': event['recipient']
            }))