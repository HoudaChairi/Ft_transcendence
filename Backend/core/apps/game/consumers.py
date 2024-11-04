from channels.generic.websocket import AsyncWebsocketConsumer
import json
import asyncio
import random
import math

class GameConsumer(AsyncWebsocketConsumer):
    connected_players = {}
    player_groups = {}
    games_data = {}
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.min_dir = 0.5
        self.velocity = 50
        self.factor = 1
        self.username = None

    async def connect(self):
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

    def start_ball_direction(self):
        x = random.uniform(-1.0, 1.0)
        y = random.uniform(-1.0, 1.0)

        x = math.copysign(max(abs(x), self.min_dir), x)
        y = math.copysign(max(abs(y), self.min_dir), y)

        return {
            "x": x * self.velocity * self.factor,
            "y": y * self.velocity * self.factor,
            "z": 0
        }

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

    def handle_player_collision(self, game, player_pos, ball_pos):
        """
        Calculate new ball direction after paddle collision with angle based on hit position
        """
        # Calculate relative intersection point (-1 to 1)
        relative_intersect_y = (player_pos["y"] - ball_pos["y"]) / 340  # 340 is half paddle height
        
        # Normalize between -1 and 1 and clamp
        bounce_angle = max(min(relative_intersect_y, 1.0), -1.0)
        
        # Determine if ball is hitting left or right paddle
        is_left_paddle = player_pos["x"] < 0
        
        # Set x direction based on which paddle was hit
        direction_x = 1 if is_left_paddle else -1
        
        # Calculate new direction
        # The bounce_angle affects the Y component
        # Higher bounce_angle = steeper upward trajectory
        # Lower bounce_angle = steeper downward trajectory
        direction = {
            "x": direction_x * self.min_dir,  # Maintain minimum x direction
            "y": -bounce_angle,  # Negative because positive relative_intersect_y means hit above center
            "z": 0
        }
        
        # Normalize the direction vector
        magnitude = math.sqrt(direction["x"]**2 + direction["y"]**2 + direction["z"]**2)
        if magnitude > 0:
            direction = {
                "x": direction["x"] / magnitude,
                "y": direction["y"] / magnitude,
                "z": direction["z"] / magnitude
            }
        
        # Apply minimum direction constraints
        direction = {
            "x": math.copysign(max(abs(direction["x"]), self.min_dir), direction["x"]),
            "y": direction["y"],  # Allow y to be smaller than min_dir for glancing shots
            "z": direction["z"]
        }
        
        # Apply velocity and factor
        return {
            "x": direction["x"] * self.velocity * self.factor,
            "y": direction["y"] * self.velocity * self.factor,
            "z": direction["z"] * self.velocity * self.factor
        }

    async def run_game_loop(self, group_id):
        """Main game loop handling ball movement with updated collision logic"""
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

            # Check for paddle collisions with new logic
            for player_id, paddle_box in game["paddle_boxes"].items():
                if (paddle_box["min"]["x"] <= new_position["x"] <= paddle_box["max"]["x"] and
                    paddle_box["min"]["y"] <= new_position["y"] <= paddle_box["max"]["y"]):
                    # Get paddle position for collision calculation
                    paddle_pos = game["paddle_positions"][player_id]
                    
                    # Calculate new direction using the new collision handler
                    game["ball_direction"] = self.handle_player_collision(
                        game,
                        paddle_pos,
                        new_position
                    )
                    
                    # Fix ball position to prevent teleporting
                    # If ball is moving right (positive x) and hits left paddle
                    if game["ball_direction"]["x"] > 0 and paddle_pos["x"] < 0:
                        new_position["x"] = paddle_box["max"]["x"] + 10
                    # If ball is moving left (negative x) and hits right paddle
                    elif game["ball_direction"]["x"] < 0 and paddle_pos["x"] > 0:
                        new_position["x"] = paddle_box["min"]["x"] - 10
                    
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
                new_y = self.games_data[group_id]["paddle_positions"][self.username]['y'] - 200
            elif direction == 'moveDown':
                new_y = self.games_data[group_id]["paddle_positions"][self.username]['y'] + 200
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