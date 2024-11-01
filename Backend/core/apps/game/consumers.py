import asyncio
import json
from channels.generic.websocket import AsyncWebsocketConsumer

class GameConsumer(AsyncWebsocketConsumer):
    connected_players = {}
    player_groups = {}
    games_data = {}

    async def connect(self):
        self.username = None
        await self.accept()

    async def disconnect(self, close_code):
        if self.username in self.connected_players:
            group_id = self.player_groups.get(self.username)
            if group_id:
                await self.remove_player_from_game(group_id)

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
        group_id = f"{player1}_{player2}"

        self.player_groups[player1] = group_id
        self.player_groups[player2] = group_id

        self.games_data[group_id] = {
            "player_labels": {player1: 'player', player2: 'player2'},
            "paddle_positions": {
                player1: {"x": -1300, "y": 0, "z": 0},
                player2: {"x": 1300, "y": 0, "z": 0}
            },
            "ball_position": {"x": 0, "y": 0, "z": 0},
            "ball_direction": {"x": 1, "y": 1, "z": 0},  # Example direction vector
            "scoreL": 0,
            "scoreR": 0,
        }

        await self.send_initialization_data(player1, group_id)
        await self.send_initialization_data(player2, group_id)

        await asyncio.sleep(5)  # Delay to start ball movement
        asyncio.create_task(self.start_ball_movement(group_id))  # Start ball movement in background

    async def start_ball_movement(self, group_id):
        while True:
            game = self.games_data[group_id]
            ball_pos = game["ball_position"]
            ball_dir = game["ball_direction"]

            # Update ball position based on direction vector
            ball_pos["x"] += ball_dir["x"]
            ball_pos["y"] += ball_dir["y"]

            # Placeholder for collision detection
            await self.detect_collisions(group_id)

            # Send updated positions to players
            await self.update_positions(group_id)

            await asyncio.sleep(0.05)  # Ball update interval

    async def detect_collisions(self, group_id):
        game = self.games_data[group_id]
        ball_pos = game["ball_position"]
        ball_dir = game["ball_direction"]

        # Wall collision
        if ball_pos["y"] >= 785 or ball_pos["y"] <= -785:
            ball_dir["y"] *= -1

        # Goal collision
        if ball_pos["x"] >= 1600:
            game["scoreL"] += 1
            ball_pos["x"], ball_pos["y"] = 0, 0
            ball_dir["x"] *= -1
        elif ball_pos["x"] <= -1600:
            game["scoreR"] += 1
            ball_pos["x"], ball_pos["y"] = 0, 0
            ball_dir["x"] *= -1

        # Paddle collision (Placeholder)
        # Implement paddle collision based on paddle positions and ball position

    async def move_paddle(self, direction):
        group_id = self.player_groups.get(self.username)
        if group_id and self.username in self.games_data[group_id]["paddle_positions"]:
            if direction == 'moveUp':
                new_y = self.games_data[group_id]["paddle_positions"][self.username]['y'] - 80
            elif direction == 'moveDown':
                new_y = self.games_data[group_id]["paddle_positions"][self.username]['y'] + 80
            else:
                return

            new_y = max(min(new_y, 520), -520)
            self.games_data[group_id]["paddle_positions"][self.username]['y'] = new_y

            await self.update_positions(group_id, player_direction=direction)

    async def stop_paddle(self):
        group_id = self.player_groups.get(self.username)
        if group_id:
            await self.update_positions(group_id, player_direction=0)

    async def update_positions(self, group_id, player_direction=0):
        game = self.games_data[group_id]

        game_data = {
            "paddlePositions": [
                {
                    "playerId": label,
                    "position": pos,
                    "direction": 1 if player_direction == 'moveUp' else -1 if player_direction == 'moveDown' else 0
                }
                for player_id, pos in game["paddle_positions"].items()
                for label in [game["player_labels"][player_id]]
            ],
            "ballPosition": game["ball_position"],
            "ballDirection": game["ball_direction"],
            "scoreL": game["scoreL"],
            "scoreR": game["scoreR"]
        }

        for player_id in game["player_labels"]:
            await self.channel_layer.send(self.connected_players[player_id], {
                'type': 'send_update',
                'data': {
                    'type': 'update',
                    'game_data': game_data
                }
            })

    async def send_initialization_data(self, username, group_id):
        game = self.games_data[group_id]
        game_data = {
            'player1': list(game["player_labels"].keys())[0],
            'player2': list(game["player_labels"].keys())[1],
            'ballPosition': game["ball_position"],
            "wallPositions": [{"x": 0, "y": -785, "z": 15}, {"x": 0, "y": 785, "z": 15}],
            "goalPositions": [{"x": 1600, "y": 0, "z": 50}, {"x": -1600, "y": 0, "z": 50}],
            "paddlePositions": [{"playerId": label, "position": pos} for player_id, pos in game["paddle_positions"].items() for label in [game["player_labels"][player_id]]]
        }

        await self.channel_layer.send(self.connected_players[username], {
            'type': 'send_initialization',
            'data': {
                'type': 'init',
                'usernames': [game_data['player1'], game_data['player2']],
                **game_data
            }
        })

    async def send_update(self, event):
        await self.send(text_data=json.dumps(event['data']))

    async def send_initialization(self, event):
        await self.send(text_data=json.dumps(event['data']))
