from channels.generic.websocket import AsyncWebsocketConsumer
import json
import asyncio
import random

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

        self.games_data[group_id] = {
            "connected_players": {player1: {}, player2: {}},
            "player_labels": {player1: 'player1', player2: 'player2'},
            "paddle_positions": {
                player1: {"x": -1300, "y": 0, "z": 0},
                player2: {"x": 1300, "y": 0, "z": 0}
            },
            "paddle_boxes": {
                player1: {
                    "min": {"x": -1400, "y": -340, "z": 0},
                    "max": {"x": -1200, "y": 340, "z": 0}
                },
                player2: {
                    "min": {"x": 1200, "y": -340, "z": 0},
                    "max": {"x": 1400, "y": 340, "z": 0}
                }
            },
            "ball_position": {"x": 0, "y": 0, "z": 0},
            "ball_direction": self.start_ball_direction(),
            "ball_box": {
                "min": {"x": -60, "y": -60, "z": -60},
                "max": {"x": 60, "y": 60, "z": 60}
            },
            "scoreL": 0,
            "scoreR": 0,
            "is_running": True
        }

        for player in [player1, player2]:
            self.player_groups[player] = group_id
            await self.channel_layer.group_add(
                group_id,
                self.connected_players[player]
            )

        await asyncio.sleep(5)
        asyncio.create_task(self.run_game_loop(group_id))

    def start_ball_direction(self):
        x = random.uniform(-1.0, 1.0)
        y = random.uniform(-1.0, 1.0)

        min_dir = 0.69
        if abs(x) < min_dir:
            x = min_dir if x > 0 else -min_dir
        if abs(y) < min_dir:
            y = min_dir if y > 0 else -min_dir

        velocity = 35
        factor = 1.2
        return {
            "x": x * velocity * factor,
            "y": y * velocity * factor,
            "z": 0
        }

    async def run_game_loop(self, group_id):
        """Main game loop handling ball movement"""
        while group_id in self.games_data and self.games_data[group_id].get("is_running", False):
            game = self.games_data[group_id]
            new_position = {
                "x": game["ball_position"]["x"] + game["ball_direction"]["x"],
                "y": game["ball_position"]["y"] + game["ball_direction"]["y"],
                "z": 0
            }

            if new_position["y"] >= 725 or new_position["y"] <= -725:
                game["ball_direction"]["y"] *= -1
                new_position["y"] = max(min(new_position["y"], 725), -725)

            for player_id, paddle_box in game["paddle_boxes"].items():
                if (paddle_box["min"]["x"] <= new_position["x"] <= paddle_box["max"]["x"] and
                    paddle_box["min"]["y"] <= new_position["y"] <= paddle_box["max"]["y"]):
                    game["ball_direction"]["x"] *= -1
                    break

            if new_position["x"] >= 1600:
                game["scoreL"] += 1
                game["ball_position"] = {"x": 0, "y": 0, "z": 0}
                new_position = game["ball_position"]
                game["ball_direction"] = self.start_ball_direction()
            elif new_position["x"] <= -1600:
                game["scoreR"] += 1
                game["ball_position"] = {"x": 0, "y": 0, "z": 0}
                new_position = game["ball_position"]
                game["ball_direction"] = self.start_ball_direction()
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
                        "scoreR": game["scoreR"],
                        "paddleBoxes": game["paddle_boxes"]
                    }
                }
            )

            await asyncio.sleep(0.033)

    async def move_paddle(self, direction):
        group_id = self.player_groups.get(self.username)
        if group_id and self.username in self.games_data[group_id]["paddle_positions"]:
            if direction == 'moveUp':
                new_y = self.games_data[group_id]["paddle_positions"][self.username]['y'] - 120
            elif direction == 'moveDown':
                new_y = self.games_data[group_id]["paddle_positions"][self.username]['y'] + 120
            else:
                return

            new_y = max(min(new_y, 520), -520)
            self.games_data[group_id]["paddle_positions"][self.username]['y'] = new_y

            paddle_label = self.games_data[group_id]["player_labels"][self.username]
            self.games_data[group_id]["paddle_boxes"][self.username]["min"]["y"] = new_y - 340
            self.games_data[group_id]["paddle_boxes"][self.username]["max"]["y"] = new_y + 340

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
                        "scoreR": self.games_data[group_id]["scoreR"],
                        "paddleBoxes": self.games_data[group_id]["paddle_boxes"]
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
                        "scoreR": self.games_data[group_id]["scoreR"],
                        "paddleBoxes": self.games_data[group_id]["paddle_boxes"]
                    }
                }
            )

    async def game_update(self, event):
        await self.send(text_data=json.dumps(event['data']))
