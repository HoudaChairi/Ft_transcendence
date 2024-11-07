from channels.generic.websocket import AsyncWebsocketConsumer
import json
import asyncio
import random
import math
from typing import Dict, Tuple

class GameConsumer(AsyncWebsocketConsumer):
    connected_players: Dict[str, str] = {}
    player_groups: Dict[str, str] = {}
    games_data: Dict[str, dict] = {}
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.min_dir = 0.5
        self.velocity = 65
        self.factor = 1
        self.username = None
        self.WIN_SCORE = 10
        self.PADDLE_SPEED = 30
        self.PADDLE_HEIGHT = 340
        self.BALL_RADIUS = 60
        self.COURT_HEIGHT = 780
        self.COURT_WIDTH = 1600

    async def connect(self):
        await self.accept()

    async def disconnect(self, close_code):
        if self.username:
            group_id = self.player_groups.get(self.username)
            if group_id:
                await self.handle_disconnect_win(group_id)
                await self.channel_layer.group_discard(group_id, self.channel_name)
                await self.remove_player_from_game(group_id)
            self.connected_players.pop(self.username, None)
            self.player_groups.pop(self.username, None)

    async def remove_player_from_game(self, group_id):
        if group_id in self.games_data:
            game = self.games_data[group_id]
            game["connected_players"].pop(self.username, None)
            if not game["connected_players"]:
                del self.games_data[group_id]

    async def handle_disconnect_win(self, group_id):
        if group_id in self.games_data:
            game = self.games_data[group_id]
            winner = next((player for player in game["connected_players"] if player != self.username), None)
            if winner:
                await self.channel_layer.group_send(
                    group_id,
                    {
                        'type': 'game_update',
                        'data': {
                            "type": "game_end",
                            "winner": winner,
                            "reason": "disconnect"
                        }
                    }
                )
            game["is_running"] = False

    async def receive(self, text_data):
        data = json.loads(text_data)

        if 'username' in data:
            self.username = data['username']
            self.connected_players[self.username] = self.channel_name

            if len(self.connected_players) % 2 == 0:
                await self.create_game()

        elif data.get('action') == 'move':
            await self.move_paddle(data['direction'])

        elif data.get('action') == 'stop_move':
            await self.stop_paddle()

    async def create_game(self):
        player_list = list(self.connected_players.keys())
        player1 = player_list[-2]
        player2 = player_list[-1]
        group_id = f"{player1}_{player2}"

        self.games_data[group_id] = {
            "connected_players": {
                player1: player1,
                player2: player2
            },
            "player_labels": {
                player1: 'player1',
                player2: 'player2'
            },
            "paddle_positions": {
                player1: {"x": -1300, "y": 0, "z": 0},
                player2: {"x": 1300, "y": 0, "z": 0}
            },
            "paddle_directions": {
                player1: 0,
                player2: 0
            },
            "paddle_boxes": {
                player1: {
                    "min": {"x": -1400, "y": -self.PADDLE_HEIGHT, "z": 0},
                    "max": {"x": -1200, "y": self.PADDLE_HEIGHT, "z": 0}
                },
                player2: {
                    "min": {"x": 1200, "y": -self.PADDLE_HEIGHT, "z": 0},
                    "max": {"x": 1400, "y": self.PADDLE_HEIGHT, "z": 0}
                }
            },
            "ball_position": {"x": 0, "y": 0, "z": 0},
            "ball_direction": self.start_ball_direction(),
            "ball_box": {
                "min": {"x": -self.BALL_RADIUS, "y": -self.BALL_RADIUS, "z": -self.BALL_RADIUS},
                "max": {"x": self.BALL_RADIUS, "y": self.BALL_RADIUS, "z": self.BALL_RADIUS}
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

        await asyncio.sleep(3)
        
        await self.channel_layer.group_send(
            group_id,
            {
                'type': 'game_update',
                'data': {
                    "type": "game_start",
                    "players": {
                        "player1": player1,
                        "player2": player2
                    }
                }
            }
        )
        
        asyncio.create_task(self.run_game_loop(group_id))

    def normalize_vector(self, x: float, y: float, z: float = 0) -> Tuple[float, float, float]:
        magnitude = math.sqrt(x*x + y*y + z*z)
        if magnitude == 0:
            return (x, y, z)
        return (x/magnitude, y/magnitude, z/magnitude)

    def start_ball_direction(self) -> dict:
        x = random.uniform(-1.0, 1.0)
        y = random.uniform(-1.0, 1.0)
        
        x = math.copysign(max(abs(x), self.min_dir), x)
        
        x, y, z = self.normalize_vector(x, y, 0)
        return {
            "x": x * self.velocity * self.factor,
            "y": y * self.velocity * self.factor,
            "z": 0
        }

    def handle_player_collision(self, paddle_pos: dict, ball_pos: dict) -> dict:
        relative_intersect_y = (paddle_pos["y"] - ball_pos["y"]) / self.PADDLE_HEIGHT
        bounce_angle = relative_intersect_y * (math.pi / 2.4)
        
        is_left_paddle = paddle_pos["x"] < 0
        direction_x = math.cos(bounce_angle) * (1 if is_left_paddle else -1)
        direction_y = -math.sin(bounce_angle)
        
        direction_x = math.copysign(max(abs(direction_x), self.min_dir), direction_x)
        
        x, y, z = self.normalize_vector(direction_x, direction_y, 0)
        return {
            "x": x * self.velocity * self.factor,
            "y": y * self.velocity * self.factor,
            "z": 0
        }

    async def check_win_condition(self, game: dict, group_id: str) -> bool:
        winner = None
        if game["scoreL"] >= self.WIN_SCORE:
            winner = next(player for player, label in game["player_labels"].items() 
                        if label == 'player1')
        elif game["scoreR"] >= self.WIN_SCORE:
            winner = next(player for player, label in game["player_labels"].items() 
                        if label == 'player2')

        if winner:
            game["is_running"] = False
            await self.channel_layer.group_send(
                group_id,
                {
                    'type': 'game_update',
                    'data': {
                        "type": "game_end",
                        "winner": winner,
                        "reason": "score"
                    }
                }
            )
            return True
        return False

    def update_paddle_positions(self, game: dict) -> None:
        max_y = self.COURT_HEIGHT - self.PADDLE_HEIGHT
        
        for player_id, direction in game["paddle_directions"].items():
            if direction != 0:
                current_y = game["paddle_positions"][player_id]["y"]
                new_y = max(min(current_y + (direction * self.PADDLE_SPEED), max_y), -max_y)
                
                game["paddle_positions"][player_id]["y"] = new_y
                game["paddle_boxes"][player_id]["min"]["y"] = new_y - self.PADDLE_HEIGHT
                game["paddle_boxes"][player_id]["max"]["y"] = new_y + self.PADDLE_HEIGHT

    async def run_game_loop(self, group_id: str) -> None:
        while group_id in self.games_data and self.games_data[group_id].get("is_running", False):
            game = self.games_data[group_id]
            
            self.update_paddle_positions(game)
            
            new_position = {
                "x": game["ball_position"]["x"] + game["ball_direction"]["x"],
                "y": game["ball_position"]["y"] + game["ball_direction"]["y"],
                "z": 0
            }

            if abs(new_position["y"]) >= self.COURT_HEIGHT:
                game["ball_direction"]["y"] *= -1
                new_position["y"] = math.copysign(self.COURT_HEIGHT, new_position["y"])

            for player_id, paddle_box in game["paddle_boxes"].items():
                if (paddle_box["min"]["x"] <= new_position["x"] <= paddle_box["max"]["x"] and
                    paddle_box["min"]["y"] <= new_position["y"] <= paddle_box["max"]["y"]):
                    
                    game["ball_direction"] = self.handle_player_collision(
                        game["paddle_positions"][player_id],
                        new_position
                    )
                    
                    if game["ball_direction"]["x"] > 0:
                        new_position["x"] = paddle_box["max"]["x"] + self.BALL_RADIUS
                    else:
                        new_position["x"] = paddle_box["min"]["x"] - self.BALL_RADIUS
                    break

            score_update = False
            if abs(new_position["x"]) >= self.COURT_WIDTH:
                if new_position["x"] > 0:
                    game["scoreL"] += 1
                else:
                    game["scoreR"] += 1
                score_update = True

            if score_update:
                game["ball_position"] = {"x": 0, "y": 0, "z": 0}
                new_position = game["ball_position"]
                game["ball_direction"] = self.start_ball_direction()
                
                if await self.check_win_condition(game, group_id):
                    await self.channel_layer.group_send(
                        group_id,
                        {
                            'type': 'game_update',
                            'data': {
                                "type": "update",
                                "paddlePositions": [
                                    {
                                        "playerId": game["player_labels"][player_id],
                                        "position": game["paddle_positions"][player_id],
                                        "direction": game["paddle_directions"][player_id]
                                    }
                                    for player_id in game["connected_players"]
                                ],
                                "ballPosition": game["ball_position"],
                                "ballDirection": game["ball_direction"],
                                "scoreL": game["scoreL"],
                                "scoreR": game["scoreR"],
                                "paddleBoxes": game["paddle_boxes"]
                            }
                        }
                    )
                    break
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
                                "playerId": game["player_labels"][player_id],
                                "position": game["paddle_positions"][player_id],
                                "direction": game["paddle_directions"][player_id]
                            }
                            for player_id in game["connected_players"]
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
                self.games_data[group_id]["paddle_directions"][self.username] = -1
            elif direction == 'moveDown':
                self.games_data[group_id]["paddle_directions"][self.username] = 1

    async def stop_paddle(self):
        group_id = self.player_groups.get(self.username)
        if group_id and self.username in self.games_data[group_id]["paddle_directions"]:
            self.games_data[group_id]["paddle_directions"][self.username] = 0

    async def game_update(self, event):
        await self.send(text_data=json.dumps(event['data']))