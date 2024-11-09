from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from core.apps.authentication.models import Player, Match
import json
import asyncio
import random
import math
from typing import Dict, Tuple, ClassVar, Optional
from dataclasses import dataclass, asdict
from enum import Enum

@dataclass
class Vector3:
    x: float
    y: float
    z: float = 0

    def __add__(self, other: 'Vector3') -> 'Vector3':
        return Vector3(self.x + other.x, self.y + other.y, self.z + other.z)

    def normalize(self) -> 'Vector3':
        magnitude = math.sqrt(self.x * self.x + self.y * self.y + self.z * self.z)
        if magnitude == 0:
            return self
        return Vector3(self.x/magnitude, self.y/magnitude, self.z/magnitude)

class Direction(Enum):
    NONE = 0
    UP = -1
    DOWN = 1

    @classmethod
    def from_string(cls, direction: str) -> 'Direction':
        if direction == 'moveUp':
            return cls.UP
        elif direction == 'moveDown':
            return cls.DOWN
        return cls.NONE

@dataclass
class GameState:
    connected_players: Dict[str, str]
    player_labels: Dict[str, str]
    paddle_positions: Dict[str, Vector3]
    paddle_directions: Dict[str, Direction]
    paddle_boxes: Dict[str, Dict[str, Vector3]]
    ball_position: Vector3
    ball_direction: Vector3
    score_left: int = 0
    score_right: int = 0
    is_running: bool = True

class GameConsumer(AsyncWebsocketConsumer):
    # Class constants
    GAME_CONSTANTS: ClassVar[Dict] = {
        'MIN_DIR': 0.83,
        'VELOCITY': 80,
        'FACTOR': 1,
        'WIN_SCORE': 10,
        'PADDLE_SPEED': 45,
        'PADDLE_HEIGHT': 280,
        'BALL_RADIUS': 60,
        'COURT_HEIGHT': 785,
        'COURT_WIDTH': 1600,
        'FRAME_TIME': 0.033
    }

    connected_players: ClassVar[Dict[str, str]] = {}
    player_groups: ClassVar[Dict[str, str]] = {}
    games_data: ClassVar[Dict[str, GameState]] = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.username: Optional[str] = None

    async def connect(self):
        await self.accept()

    async def disconnect(self, close_code):
        if self.username:
            group_id = self.player_groups.get(self.username)
            if group_id:
                game = self.games_data.get(group_id)
                if game and game.is_running:
                    game.is_running = False
                    winner = next((player for player in game.connected_players if player != self.username), None)
                    
                    if winner:
                        p1 = next(key for key, value in game.player_labels.items() if value == 'player1')
                        p2 = next(key for key, value in game.player_labels.items() if value == 'player2')
                        await database_sync_to_async(self.create_match_record)(p1, p2, winner, game.score_left, game.score_right)
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

                await self.channel_layer.group_discard(group_id, self.channel_name)
                await self.remove_player_from_game(group_id)

            self.connected_players.pop(self.username, None)
            self.player_groups.pop(self.username, None)

    async def remove_player_from_game(self, group_id: str) -> None:
        if group_id in self.games_data:
            game = self.games_data[group_id]
            game.connected_players.pop(self.username, None)
            if not game.connected_players:
                del self.games_data[group_id]

    async def handle_disconnect_win(self, group_id: str) -> None:
        if group_id in self.games_data:
            game = self.games_data[group_id]
            winner = next((player for player in game.connected_players if player != self.username), None)
            
            if winner:
                p1 = next(key for key, value in game.player_labels.items() if value == 'player1')
                p2 = next(key for key, value in game.player_labels.items() if value == 'player2')
                await database_sync_to_async(self.create_match_record)(p1, p2, winner, game.score_left, game.score_right)
                
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
            game.is_running = False

    async def receive(self, text_data: str) -> None:
        data = json.loads(text_data)

        if 'username' in data:
            await self.handle_new_player(data['username'])
        elif data.get('action') == 'move':
            await self.move_paddle(data['direction'])
        elif data.get('action') == 'stop_move':
            await self.stop_paddle()

    async def handle_new_player(self, username: str) -> None:
        self.username = username
        self.connected_players[username] = self.channel_name

        if len(self.connected_players) % 2 == 0:
            await self.create_game()

    async def create_game(self) -> None:
        player_list = list(self.connected_players.keys())
        player1, player2 = player_list[-2:]
        group_id = f"{player1}_{player2}"

        self.games_data[group_id] = self.create_initial_game_state(player1, player2)

        for player in (player1, player2):
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

    @staticmethod
    def create_initial_game_state(player1: str, player2: str) -> GameState:
        C = GameConsumer.GAME_CONSTANTS
        
        paddle1_pos = Vector3(-1300, 0, 0)
        paddle2_pos = Vector3(1300, 0, 0)
        
        return GameState(
            connected_players={player1: player1, player2: player2},
            player_labels={player1: 'player1', player2: 'player2'},
            paddle_positions={player1: paddle1_pos, player2: paddle2_pos},
            paddle_directions={player1: Direction.NONE, player2: Direction.NONE},
            paddle_boxes={
                player1: {
                    "min": Vector3(-1400, -C['PADDLE_HEIGHT'], 0),
                    "max": Vector3(-1200, C['PADDLE_HEIGHT'], 0)
                },
                player2: {
                    "min": Vector3(1200, -C['PADDLE_HEIGHT'], 0),
                    "max": Vector3(1400, C['PADDLE_HEIGHT'], 0)
                }
            },
            ball_position=Vector3(0, 0, 0),
            ball_direction=GameConsumer.start_ball_direction(),
            is_running=True
        )

    @classmethod
    def start_ball_direction(cls) -> Vector3:
        C = cls.GAME_CONSTANTS
        x = random.uniform(-1.0, 1.0)
        y = random.uniform(-1.0, 1.0)
        x = math.copysign(max(abs(x), C['MIN_DIR']), x)
        
        direction = Vector3(x, y).normalize()
        return Vector3(
            direction.x * C['VELOCITY'] * C['FACTOR'],
            direction.y * C['VELOCITY'] * C['FACTOR']
        )

    def handle_player_collision(self, paddle_pos: Vector3, ball_pos: Vector3) -> Vector3:
        C = self.GAME_CONSTANTS
        direction = Vector3(
            ball_pos.x - paddle_pos.x,
            ball_pos.y - paddle_pos.y,
            0
        ).normalize()

        direction.x = math.copysign(max(abs(direction.x), C['MIN_DIR']), direction.x)
        direction.y = math.copysign(max(abs(direction.y), C['MIN_DIR']), direction.y)

        return Vector3(
            direction.x * C['VELOCITY'] * C['FACTOR'],
            direction.y * C['VELOCITY'] * C['FACTOR'],
            0
        )

    async def check_win_condition(self, game: GameState, group_id: str) -> bool:
        winner = None
        if game.score_left >= self.GAME_CONSTANTS['WIN_SCORE']:
            winner = next(player for player, label in game.player_labels.items() if label == 'player1')
        elif game.score_right >= self.GAME_CONSTANTS['WIN_SCORE']:
            winner = next(player for player, label in game.player_labels.items() if label == 'player2')

        if winner:
            game.is_running = False
            
            p1 = next(key for key, value in game.player_labels.items() if value == 'player1')
            p2 = next(key for key, value in game.player_labels.items() if value == 'player2')
            await database_sync_to_async(self.create_match_record)(p1, p2, winner, game.score_left, game.score_right)

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

    async def run_game_loop(self, group_id: str) -> None:
        C = self.GAME_CONSTANTS
        game = self.games_data[group_id]

        while group_id in self.games_data and game.is_running:
            self.update_paddle_positions(game)
            new_position = game.ball_position + game.ball_direction

            if abs(new_position.y) >= C['COURT_HEIGHT']:
                game.ball_direction.y *= -1
                new_position.y = math.copysign(C['COURT_HEIGHT'], new_position.y)

            for player_id, paddle_box in game.paddle_boxes.items():
                if (paddle_box["min"].x <= new_position.x <= paddle_box["max"].x and
                    paddle_box["min"].y <= new_position.y <= paddle_box["max"].y):
                    
                    game.ball_direction = self.handle_player_collision(
                        game.paddle_positions[player_id],
                        new_position
                    )
                    
                    new_position.x = (paddle_box["max"].x + C['BALL_RADIUS'] 
                                    if game.ball_direction.x > 0 
                                    else paddle_box["min"].x - C['BALL_RADIUS'])
                    break

            if abs(new_position.x) >= C['COURT_WIDTH']:
                if new_position.x > 0:
                    game.score_left += 1
                else:
                    game.score_right += 1
                
                game.ball_position = Vector3(0, 0, 0)
                game.ball_direction = self.start_ball_direction()
                
                if await self.check_win_condition(game, group_id):
                    await self.broadcast_game_state(group_id, game)
                    break
            else:
                game.ball_position = new_position

            await self.broadcast_game_state(group_id, game)
            await asyncio.sleep(C['FRAME_TIME'])

    def update_paddle_positions(self, game: GameState) -> None:
        C = self.GAME_CONSTANTS
        max_y = C['COURT_HEIGHT'] - C['PADDLE_HEIGHT']
        
        for player_id, direction in game.paddle_directions.items():
            if direction != Direction.NONE:
                current_y = game.paddle_positions[player_id].y
                new_y = max(min(current_y + (direction.value * C['PADDLE_SPEED']), max_y), -max_y)
                
                game.paddle_positions[player_id].y = new_y
                game.paddle_boxes[player_id]["min"].y = new_y - C['PADDLE_HEIGHT']
                game.paddle_boxes[player_id]["max"].y = new_y + C['PADDLE_HEIGHT']

        group_id = next((group_id for group_id, game_state in self.games_data.items() if self.username in game_state.connected_players), None)
        if group_id:
            asyncio.create_task(self.broadcast_game_state(group_id, game))

    async def move_paddle(self, direction: str) -> None:
        group_id = self.player_groups.get(self.username)
        if group_id and self.username in self.games_data[group_id].paddle_directions:
            self.games_data[group_id].paddle_directions[self.username] = Direction.from_string(direction)
            self.update_paddle_positions(self.games_data[group_id])

    async def stop_paddle(self) -> None:
        group_id = self.player_groups.get(self.username)
        if group_id and self.username in self.games_data[group_id].paddle_directions:
            self.games_data[group_id].paddle_directions[self.username] = Direction.NONE
            asyncio.create_task(self.broadcast_game_state(group_id, self.games_data[group_id]))

    async def broadcast_game_state(self, group_id: str, game: GameState) -> None:
        await self.channel_layer.group_send(
            group_id,
            {
                'type': 'game_update',
                'data': {
                    "type": "update",
                    "paddlePositions": [
                        {
                            "playerId": game.player_labels[player_id],
                            "position": asdict(game.paddle_positions[player_id]),
                            "direction": game.paddle_directions[player_id].value
                        }
                        for player_id in game.connected_players
                    ],
                    "ballPosition": asdict(game.ball_position),
                    "ballDirection": asdict(game.ball_direction),
                    "scoreL": game.score_left,
                    "scoreR": game.score_right,
                    "paddleBoxes": {
                        k: {"min": asdict(v["min"]), "max": asdict(v["max"])}
                        for k, v in game.paddle_boxes.items()
                    }
                }
            }
        )

    async def game_update(self, event: Dict) -> None:
        await self.send(text_data=json.dumps(event['data']))

    def create_match_record(self, player1_username: str, player2_username: str, winner: str, score_player1: int, score_player2: int):
        try:
            player1 = Player.objects.get(username=player1_username)
            player2 = Player.objects.get(username=player2_username)

            winning_player = player1 if winner == player1.username else player2
            losing_player = player2 if winner == player1.username else player1

            Match.objects.create(
                player1=player1,
                player2=player2,
                winner=winning_player,
                loser=losing_player,
                score_player1=score_player1,
                score_player2=score_player2
            )

            if winner == player1.username:
                player1.wins += 1
                player2.losses += 1
            else:
                player1.losses += 1
                player2.wins += 1

            player1.t_games += 1
            player1.goals_f += score_player1
            player1.goals_a += score_player2

            player2.t_games += 1
            player2.goals_f += score_player2
            player2.goals_a += score_player1

            player1.t_points += 3 if winner == player1.username else -1
            player2.t_points += 3 if winner == player2.username else -1

            player1.save()
            player2.save()

        except Player.DoesNotExist:
            pass