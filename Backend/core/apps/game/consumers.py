from channels.generic.websocket import AsyncWebsocketConsumer
import json
import asyncio

class GameConsumer(AsyncWebsocketConsumer):
    connected_players = {}
    player_groups = {}
    games_data = {}

    async def connect(self):
        self.username = None
        await self.accept()

    async def disconnect(self, close_code):
        if self.username:
            group_id = self.player_groups.get(self.username)
            if group_id:
                await self.channel_layer.group_discard(group_id, self.channel_name)
                await self.remove_player_from_game(group_id)
            self.connected_players.pop(self.username, None)
            self.player_groups.pop(self.username, None)

    async def remove_player_from_game(self, group_id):
        if group_id in self.games_data:
            self.games_data[group_id]["connected_players"].pop(self.username, None)
            if not self.games_data[group_id]["connected_players"]:
                del self.games_data[group_id]

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

        # Create the game data
        self.games_data[group_id] = {
            "connected_players": {player1: {}, player2: {}},
            "player_labels": {player1: 'player1', player2: 'player2'},
            "paddle_positions": {
                player1: {"x": -1300, "y": 0, "z": 0},
                player2: {"x": 1300, "y": 0, "z": 0}
            },
            "ball_position": {"x": 0, "y": 0, "z": 0},
            "ball_direction": {"x": 1, "y": 1, "z": 0},
            "scoreL": 0,
            "scoreR": 0,
            "is_running": True
        }

        # Add players to the group
        for player in [player1, player2]:
            self.player_groups[player] = group_id
            await self.channel_layer.group_add(
                group_id,
                self.connected_players[player]
            )

        await asyncio.sleep(5)
        asyncio.create_task(self.run_game_loop(group_id))

    async def run_game_loop(self, group_id):
        """Main game loop handling ball movement"""
        while group_id in self.games_data and self.games_data[group_id].get("is_running", False):
            game = self.games_data[group_id]
            new_position = {
                "x": game["ball_position"]["x"] + game["ball_direction"]["x"] * 10,
                "y": game["ball_position"]["y"] + game["ball_direction"]["y"] * 10,
                "z": 0
            }
            
            # Ball collision with walls
            if new_position["y"] >= 730 or new_position["y"] <= -730:
                game["ball_direction"]["y"] *= -1
                new_position["y"] = max(min(new_position["y"], 730), -730)

            # Ball collision with paddles
            for player_id, position in game["paddle_positions"].items():
                if (abs(new_position["x"] - position["x"]) < 30 and
                    abs(new_position["y"] - position["y"]) < 150):
                    game["ball_direction"]["x"] *= -1
                    break

            # Ball collision with goals
            if new_position["x"] >= 1600:
                game["scoreL"] += 1
                game["ball_position"] = {"x": 0, "y": 0, "z": 0}
                new_position = game["ball_position"]
            elif new_position["x"] <= -1600:
                game["scoreR"] += 1
                game["ball_position"] = {"x": 0, "y": 0, "z": 0}
                new_position = game["ball_position"]
            else:
                game["ball_position"] = new_position

            await self.channel_layer.group_send(
                group_id,
                {
                    'type': 'game_update',
                    'data': {
                        "type": "update",
                        "paddlePositions": [
                            {
                                "playerId": label,
                                "position": game["paddle_positions"][player_id],
                                "direction": 0
                            }
                            for player_id, label in game["player_labels"].items()
                        ],
                        "ballPosition": game["ball_position"],
                        "ballDirection": game["ball_direction"],
                        "scoreL": game["scoreL"],
                        "scoreR": game["scoreR"]
                    }
                }
            )
            
            await asyncio.sleep(0.033)

    async def move_paddle(self, direction):
        group_id = self.player_groups.get(self.username)
        if group_id and self.username in self.games_data[group_id]["paddle_positions"]:
            if direction == 'moveUp':
                new_y = self.games_data[group_id]["paddle_positions"][self.username]['y'] - 60
            elif direction == 'moveDown':
                new_y = self.games_data[group_id]["paddle_positions"][self.username]['y'] + 60
            else:
                return

            new_y = max(min(new_y, 520), -520)
            self.games_data[group_id]["paddle_positions"][self.username]['y'] = new_y

            await self.channel_layer.group_send(
                group_id,
                {
                    'type': 'game_update',
                    'data': {
                        "type": "update",
                        "paddlePositions": [
                            {
                                "playerId": label,
                                "position": self.games_data[group_id]["paddle_positions"][player_id],
                                "direction": 1 if direction == 'moveDown' else -1 if player_id == self.username else 0
                            }
                            for player_id, label in self.games_data[group_id]["player_labels"].items()
                        ],
                        "ballPosition": self.games_data[group_id]["ball_position"],
                        "ballDirection": self.games_data[group_id]["ball_direction"],
                        "scoreL": self.games_data[group_id]["scoreL"],
                        "scoreR": self.games_data[group_id]["scoreR"]
                    }
                }
            )

    async def stop_paddle(self):
        group_id = self.player_groups.get(self.username)
        if group_id:
            await self.channel_layer.group_send(
                group_id,
                {
                    'type': 'game_update',
                    'data': {
                        "type": "update",
                        "paddlePositions": [
                            {
                                "playerId": label,
                                "position": self.games_data[group_id]["paddle_positions"][player_id],
                                "direction": 0
                            }
                            for player_id, label in self.games_data[group_id]["player_labels"].items()
                        ],
                        "ballPosition": self.games_data[group_id]["ball_position"],
                        "ballDirection": self.games_data[group_id]["ball_direction"],
                        "scoreL": self.games_data[group_id]["scoreL"],
                        "scoreR": self.games_data[group_id]["scoreR"]
                    }
                }
            )

    async def game_update(self, event):
        """Handler for game update messages"""
        await self.send(text_data=json.dumps(event['data']))
