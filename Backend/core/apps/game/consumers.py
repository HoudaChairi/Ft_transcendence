from channels.generic.websocket import AsyncWebsocketConsumer
import json

class GameConsumer(AsyncWebsocketConsumer):
    connected_players = {}
    game_rooms = {}

    async def connect(self):
        self.username = None
        self.room_group_name = None
        await self.accept()

    async def disconnect(self, close_code):
        if self.username in self.connected_players:
            del self.connected_players[self.username]
            if self.room_group_name:
                await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)

        if 'username' in data:
            self.username = data['username']
            self.connected_players[self.username] = self.channel_name

            if len(self.connected_players) % 2 == 0:
                player_list = list(self.connected_players.keys())
                player1 = player_list[-2]
                player2 = player_list[-1]

                game_data = {
                    'player1': player1,
                    'player2': player2,
                    'ballPosition': {"x": 0, "y": 0, "z": 0},
                    "wallPositions": [
                        {"x": 0, "y": -785, "z": 15},
                        {"x": 0, "y": 785, "z": 15}
                    ],
                    "goalPositions": [
                        {"x": 1600, "y": 0, "z": 50},
                        {"x": -1600, "y": 0, "z": 50}
                    ],
                    "paddlePositions": [
                        {"playerId": player1, "position": {"x": -1300, "y": 0, "z": 0}},
                        {"playerId": player2, "position": {"x": 1300, "y": 0, "z": 0}},
                    ]
                }

                await self.send_initialization_data(player1, game_data)
                await self.send_initialization_data(player2, game_data)

    async def send_initialization_data(self, username, game_data):
        await self.channel_layer.send(
            self.connected_players[username],
            {
                'type': 'send_game_data',
                'data': {
                    'type': 'init',
                    'usernames': [game_data['player1'], game_data['player2']],
                    **game_data
                }
            }
        )

    async def send_game_data(self, event):
        data = event['data']
        await self.send(text_data=json.dumps(data))
