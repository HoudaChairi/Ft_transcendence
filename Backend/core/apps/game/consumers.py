from channels.generic.websocket import AsyncWebsocketConsumer
import json

class GameConsumer(AsyncWebsocketConsumer):
    connected_players = {}
    player_groups = {}
    paddle_positions = {}

    async def connect(self):
        self.username = None
        await self.accept()

    async def disconnect(self, close_code):
        if self.username in self.connected_players:
            del self.connected_players[self.username]
            if self.username in self.player_groups:
                player_group = self.player_groups[self.username]
                del self.player_groups[self.username]
                await self.send(text_data=json.dumps({
                    'type': 'end_game',
                    'message': f'{self.username} has disconnected.'
                }))
                await self.channel_layer.group_discard(player_group, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)

        if 'username' in data:
            self.username = data['username']
            self.connected_players[self.username] = self.channel_name

            if len(self.connected_players) % 2 == 0:
                await self.create_game()

        elif data.get('action') == 'move':
            direction = data['direction']
            await self.move_paddle(direction)

        elif data.get('action') == 'stop_move':
            await self.stop_paddle()

    async def create_game(self):
        player_list = list(self.connected_players.keys())
        player1 = player_list[-2]
        player2 = player_list[-1]

        self.player_groups[player1] = player2
        self.player_groups[player2] = player1

        self.paddle_positions[player1] = {"x": -1300, "y": 0, "z": 0}
        self.paddle_positions[player2] = {"x": 1300, "y": 0, "z": 0}

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
                {"playerId": 'player', "position": self.paddle_positions[player1]},
                {"playerId": 'player2', "position": self.paddle_positions[player2]},
            ]
        }

        await self.send_initialization_data(player1, game_data)
        await self.send_initialization_data(player2, game_data)

    async def move_paddle(self, direction):
        player_id = self.username

        if player_id not in self.paddle_positions:
            return

        if direction == 'moveUp':
            new_y = self.paddle_positions[player_id]['y'] - 60
        elif direction == 'moveDown':
            new_y = self.paddle_positions[player_id]['y'] + 60
        else:
            return

        if new_y < -520:
            new_y = -520
        elif new_y > 520:
            new_y = 520

        self.paddle_positions[player_id]['y'] = new_y

        await self.update_paddle_positions()

    async def stop_paddle(self):
        player_id = self.username
        if player_id in self.paddle_positions:
            await self.update_paddle_positions()

    async def update_paddle_positions(self):
        game_data = {
            "paddlePositions": [
                {"playerId": 'player' if player_id == list(self.player_groups.keys())[0] else 'player2', "position": position}
                for player_id, position in self.paddle_positions.items()
            ]
        }

        for player_id in self.player_groups.keys():
            await self.channel_layer.send(self.connected_players[player_id], {
                'type': 'send_update',
                'data': {
                    'type': 'update',
                    'game_data': game_data
                }
            })

    async def send_initialization_data(self, username, game_data):
        await self.channel_layer.send(self.connected_players[username], {
            'type': 'send_initialization',
            'data': {
                'type': 'init',
                'usernames': [game_data['player1'], game_data['player2']],
                **game_data
            }
        })

    async def send_initialization(self, event):
        data = event['data']
        await self.send(text_data=json.dumps(data))

    async def send_update(self, event):
        data = event['data']
        await self.send(text_data=json.dumps(data))
