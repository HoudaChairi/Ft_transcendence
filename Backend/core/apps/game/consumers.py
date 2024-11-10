from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from core.apps.authentication.models import Player, Match
import json
import asyncio
import random
import math
import time
import uuid
from typing import Dict, List, Set, Optional
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime, timedelta

@dataclass
class Vector3:
    x: float
    y: float
    z: float = 0

    def __add__(self, other: 'Vector3') -> 'Vector3':
        return Vector3(self.x + other.x, self.y + other.y, self.z + other.z)

    def __mul__(self, scalar: float) -> 'Vector3':
        return Vector3(self.x * scalar, self.y * scalar, self.z * scalar)

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

class RateLimiter:
    def __init__(self, limit: int, window: timedelta):
        self.limit = limit
        self.window = window
        self.requests = {}

    def is_allowed(self, user_id: str) -> bool:
        now = datetime.now()
        if user_id not in self.requests:
            self.requests[user_id] = []

        self.requests[user_id] = [
            time for time in self.requests[user_id]
            if now - time < self.window
        ]

        if len(self.requests[user_id]) >= self.limit:
            return False

        self.requests[user_id].append(now)
        return True

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
    last_update: float = time.time()

    def is_valid(self, constants: Dict) -> bool:
        if abs(self.ball_position.x) > constants['COURT_WIDTH'] or \
           abs(self.ball_position.y) > constants['COURT_HEIGHT']:
            return False
            
        max_paddle_y = constants['COURT_HEIGHT'] - constants['PADDLE_HEIGHT']
        for pos in self.paddle_positions.values():
            if abs(pos.y) > max_paddle_y:
                return False
        
        return True

class GameConsumer(AsyncWebsocketConsumer):
    GAME_CONSTANTS = {
        'MIN_DIR': 0.5,
        'VELOCITY': 800,
        'FACTOR': 1.5,
        'WIN_SCORE': 10,
        'PADDLE_SPEED': 800,
        'PADDLE_HEIGHT': 280,
        'BALL_RADIUS': 60,
        'COURT_HEIGHT': 785,
        'COURT_WIDTH': 1600,
        'FRAME_TIME': 0.016
    }

    connected_players = {}
    player_groups = {}
    games_data = {}
    rate_limiter = RateLimiter(limit=60, window=timedelta(seconds=1))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.username: Optional[str] = None

    async def connect(self):
        try:
            await self.accept()
        except Exception as e:
            print(f"Error in connect: {e}")
            await self.close()

    async def disconnect(self, close_code):
        try:
            if self.username:
                group_id = self.player_groups.get(self.username)
                if group_id:
                    game = self.games_data.get(group_id)
                    if game and game.is_running:
                        await self.handle_disconnect_win(group_id)
                    await self.channel_layer.group_discard(group_id, self.channel_name)
                    await self.remove_player_from_game(group_id)

                self.connected_players.pop(self.username, None)
                self.player_groups.pop(self.username, None)
        except Exception as e:
            print(f"Error in disconnect: {e}")

    async def remove_player_from_game(self, group_id: str) -> None:
        if group_id in self.games_data:
            game = self.games_data[group_id]
            game.connected_players.pop(self.username, None)
            if not game.connected_players:
                del self.games_data[group_id]

    async def receive(self, text_data: str) -> None:
        try:
            if not self.rate_limiter.is_allowed(self.username or 'anonymous'):
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': 'Rate limit exceeded'
                }))
                return

            data = json.loads(text_data)
            
            if not isinstance(data, dict):
                raise ValueError("Invalid message format")

            if 'username' in data:
                if not isinstance(data['username'], str):
                    raise ValueError("Invalid username format")
                # Pass tournament_data if it exists
                tournament_data = data.get('tournament_data')
                await self.handle_new_player(data['username'], tournament_data)
                
            elif 'action' in data:
                if data['action'] not in ['move', 'stop_move']:
                    raise ValueError("Invalid action")
                    
                if data['action'] == 'move':
                    if 'direction' not in data:
                        raise ValueError("Missing direction")
                    await self.move_paddle(data['direction'])
                else:
                    await self.stop_paddle()
                    
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON format'
            }))
        except ValueError as e:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': str(e)
            }))
        except Exception as e:
            print(f"Error in receive: {e}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Internal server error'
            }))

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

    async def handle_new_player(self, username: str, tournament_data: Optional[dict] = None) -> None:
        try:
            self.username = username
            self.connected_players[username] = self.channel_name

            # Tournament game handling
            if tournament_data:
                print(f"Tournament game starting: {tournament_data}")
                self.tournament_data = tournament_data  # Store tournament data
                group_id = f"{tournament_data['player1']}_{tournament_data['player2']}"
                self.player_groups[username] = group_id
                
                if len(self.connected_players) == 2:
                    await self.create_tournament_game(
                        tournament_data['player1'],
                        tournament_data['player2'],
                        tournament_data
                    )
            else:
                if await self.handle_reconnection_attempt(username):
                    return

                if len(self.connected_players) % 2 == 0:
                    await self.create_game()
        except Exception as e:
            print(f"Error in handle_new_player: {e}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Failed to join game'
            }))

    async def handle_reconnection_attempt(self, username: str) -> bool:
        group_id = self.player_groups.get(username)
        if group_id and group_id in self.games_data:
            game = self.games_data[group_id]
            if game.is_running:
                await self.channel_layer.group_add(group_id, self.channel_name)
                await self.send(text_data=json.dumps({
                    'type': 'reconnected',
                    'gameState': {
                        'paddlePositions': [asdict(pos) for pos in game.paddle_positions.values()],
                        'ballPosition': asdict(game.ball_position),
                        'scoreL': game.score_left,
                        'scoreR': game.score_right
                    }
                }))
                return True
        return False
    
    async def create_tournament_game(self, player1: str, player2: str, tournament_data: dict) -> None:
        group_id = f"{player1}_{player2}"
        
        self.games_data[group_id] = self.create_initial_game_state(player1, player2)
        self.games_data[group_id].tournament_data = tournament_data

        for player in (player1, player2):
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
                    },
                    "tournament": True
                }
            }
        )
        
        asyncio.create_task(self.run_game_loop(group_id))

    async def handle_game_end(self, winner: str) -> None:
        group_id = self.player_groups.get(self.username)
        if group_id:
            game = self.games_data[group_id]
            
            tournament_data = getattr(game, 'tournament_data', None)
            if tournament_data:
                await self.channel_layer.send(
                    tournament_data['consumer'],
                    {
                        'type': 'receive',
                        'text_data': json.dumps({
                            'type': 'game_complete',
                            'tournament_id': tournament_data['tournament_id'],
                            'match_id': tournament_data['match_id'],
                            'winner': winner
                        })
                    }
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
            
            await self.handle_game_end(winner)

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

    def update_paddle_positions(self, game: GameState) -> None:
        C = self.GAME_CONSTANTS
        max_y = C['COURT_HEIGHT'] - C['PADDLE_HEIGHT']
        current_time = time.time()
        delta_time = current_time - game.last_update
        
        for player_id, direction in game.paddle_directions.items():
            if direction != Direction.NONE:
                current_pos = game.paddle_positions[player_id]
                new_y = max(min(
                    current_pos.y + (direction.value * C['PADDLE_SPEED'] * delta_time),
                    max_y
                ), -max_y)
                
                new_pos = Vector3(current_pos.x, new_y, current_pos.z)
                
                if self.validate_paddle_movement(current_pos, new_pos, delta_time):
                    game.paddle_positions[player_id] = new_pos
                    game.paddle_boxes[player_id]["min"].y = new_y - C['PADDLE_HEIGHT']
                    game.paddle_boxes[player_id]["max"].y = new_y + C['PADDLE_HEIGHT']

        game.last_update = current_time

    async def handle_disconnect_win(self, group_id: str) -> None:
        if group_id in self.games_data:
            game = self.games_data[group_id]
            winner = next((player for player in game.connected_players if player != self.username), None)
            
            if winner:
                p1 = next(key for key, value in game.player_labels.items() if value == 'player1')
                p2 = next(key for key, value in game.player_labels.items() if value == 'player2')
                await database_sync_to_async(self.create_match_record)(p1, p2, winner, game.score_left, game.score_right)
                
                await self.handle_game_end(winner)
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

    @classmethod
    def create_initial_game_state(cls, player1: str, player2: str) -> GameState:
        C = cls.GAME_CONSTANTS
        
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
            ball_direction=cls.start_ball_direction()
        )

    @classmethod
    def start_ball_direction(cls) -> Vector3:
        C = cls.GAME_CONSTANTS
        x = random.uniform(-1.0, 1.0)
        y = random.uniform(-1.0, 1.0)
        x = math.copysign(max(abs(x), C['MIN_DIR']), x)
        
        direction = Vector3(x, y).normalize()
        return direction * (C['VELOCITY'] * C['FACTOR'])

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

    def handle_player_collision(self, paddle_pos: Vector3, ball_pos: Vector3) -> Vector3:
        C = self.GAME_CONSTANTS
        
        # Calculate relative position and velocity
        relative_y = (ball_pos.y - paddle_pos.y) / (C['PADDLE_HEIGHT'])
        
        # Add some randomness to make gameplay less predictable
        random_factor = 1.0 + (random.random() * 0.1)  # ±5% random variation
        
        # Non-linear angle calculation with sweet spot
        # This creates a "sweet spot" near the center-edges of the paddle
        sweet_spot = abs(relative_y) - 0.5
        if abs(sweet_spot) < 0.2:
            # Hit in sweet spot - more controlled, faster return
            power_factor = 1.3
            relative_y = relative_y * 0.8  # More controlled angle
        else:
            # Hit away from sweet spot - more extreme angles, normal speed
            power_factor = 1.0
            relative_y = math.copysign(math.pow(abs(relative_y), 0.7), relative_y)
        
        # Calculate angle (up to 75 degrees for very extreme edge hits)
        angle = relative_y * (math.pi * 0.42)
        
        # Calculate direction with sweet spot bonus
        direction = Vector3(
            math.cos(angle) * math.copysign(1, ball_pos.x - paddle_pos.x),
            math.sin(angle),
            0
        ).normalize()
        
        # Ensure minimum horizontal movement
        direction.x = math.copysign(max(abs(direction.x), C['MIN_DIR']), direction.x)
        
        # Calculate final speed including all factors
        edge_speed = 1.0 + (abs(relative_y) * 0.6)  # Up to 60% faster on edges
        final_speed = C['VELOCITY'] * C['FACTOR'] * edge_speed * power_factor * random_factor
        
        return direction * final_speed

    def validate_paddle_movement(self, old_pos: Vector3, new_pos: Vector3, delta_time: float) -> bool:
        C = self.GAME_CONSTANTS
        max_movement = C['PADDLE_SPEED'] * delta_time * 1.1  # 10% tolerance
        
        movement = math.sqrt((new_pos.y - old_pos.y) ** 2)
        return movement <= max_movement

    async def run_game_loop(self, group_id: str) -> None:
        C = self.GAME_CONSTANTS
        game = self.games_data[group_id]
        last_update = time.time()

        while group_id in self.games_data and game.is_running:
            current_time = time.time()
            delta_time = current_time - last_update
            
            # Skip frame if we're running too fast
            if delta_time < C['FRAME_TIME']:
                await asyncio.sleep(C['FRAME_TIME'] - delta_time)
                continue
                
            # Update game state
            self.update_paddle_positions(game)
            new_position = game.ball_position + game.ball_direction * delta_time

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
                    break
            else:
                game.ball_position = new_position

            if not game.is_valid(C):
                print(f"Invalid game state detected in group {group_id}")
                game.is_running = False
                break

            await self.broadcast_game_state(group_id, game)
            last_update = current_time

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

# ------------------------------------------------------------------------------------------------------------- #

class TournamentState(Enum):
    WAITING = "waiting"
    SEMIFINALS = "semifinals"
    FINALS = "finals"
    COMPLETED = "completed"

@dataclass
class TournamentMatch:
    match_id: str
    player1: str
    player2: str
    winner: Optional[str] = None
    game_completed: bool = False

@dataclass
class Tournament:
    id: str
    players: List[str]
    state: TournamentState
    matches: Dict[str, TournamentMatch]
    current_round_matches: Set[str]
    winners: List[str]

class TournamentConsumer(AsyncWebsocketConsumer):
    tournaments: Dict[str, Tournament] = {}
    player_to_tournament: Dict[str, str] = {}
    waiting_players: List[str] = []
    connected_players: Set[str] = set()  # Using Set prevents duplicates
    active_connections: Dict[str, AsyncWebsocketConsumer] = {}
    PLAYERS_PER_TOURNAMENT = 4

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.username: Optional[str] = None
        self.tournament_id: Optional[str] = None

    async def connect(self):
        await self.accept()

    async def disconnect(self, close_code):
        if self.username:
            # Remove from waiting list if present
            if self.username in self.waiting_players:
                self.waiting_players.remove(self.username)
            
            # Remove from connected players and active connections
            self.connected_players.discard(self.username)
            self.active_connections.pop(self.username, None)
            
            # Handle tournament cleanup
            tournament_id = self.player_to_tournament.get(self.username)
            if tournament_id:
                tournament = self.tournaments.get(tournament_id)
                if tournament:
                    if tournament.state == TournamentState.WAITING:
                        tournament.players.remove(self.username)
                        if not tournament.players:
                            del self.tournaments[tournament_id]
                    self.player_to_tournament.pop(self.username, None)
            
            await self.broadcast_player_lists()

    async def broadcast_player_lists(self):
        """Broadcast complete player information to all connected players"""
        players_in_tournaments = {}
        for tournament_id, tournament in self.tournaments.items():
            players_in_tournaments[tournament_id] = {
                'players': tournament.players,
                'state': tournament.state.value,
                'matches': {
                    match_id: {
                        'player1': match.player1,
                        'player2': match.player2,
                        'winner': match.winner,
                        'completed': match.game_completed
                    }
                    for match_id, match in tournament.matches.items()
                }
            }

        message = {
            "type": "players_update",
            "data": {
                "waiting_players": self.waiting_players,
                "all_connected_players": list(self.connected_players),
                "tournaments": players_in_tournaments
            }
        }

        # Send to ALL connected players
        for connection in self.active_connections.values():
            await connection.send(text_data=json.dumps(message))

    async def handle_join_tournament(self, username: str):
        self.username = username
        
        # Check if player is already in a tournament
        if username in self.player_to_tournament:
            await self.send(text_data=json.dumps({
                "type": "error",
                "message": "Already in a tournament"
            }))
            return
            
        # Check if player is already waiting
        if username in self.waiting_players:
            await self.send(text_data=json.dumps({
                "type": "error",
                "message": "Already in waiting list"
            }))
            return

        # Add to connected players and waiting list
        self.connected_players.add(username)
        self.active_connections[username] = self
        self.waiting_players.append(username)
        
        # Broadcast updated player lists
        await self.broadcast_player_lists()
        
        # Check if we have enough players to start a tournament
        if len(self.waiting_players) >= self.PLAYERS_PER_TOURNAMENT:
            tournament_players = self.waiting_players[:self.PLAYERS_PER_TOURNAMENT]
            self.waiting_players = self.waiting_players[self.PLAYERS_PER_TOURNAMENT:]
            
            # Check if any of these players is already in a tournament
            if any(player in self.player_to_tournament for player in tournament_players):
                # Remove players that are already in tournaments
                tournament_players = [p for p in tournament_players if p not in self.player_to_tournament]
                # Add remaining players back to waiting list
                self.waiting_players.extend(tournament_players)
                await self.broadcast_player_lists()
                return
                
            await self.create_tournament(tournament_players)
            await self.broadcast_player_lists()

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            
            if 'type' not in data:
                return
            
            if data['type'] == 'join_tournament':
                await self.handle_join_tournament(data['username'])
            elif data['type'] == 'game_complete':
                await self.handle_game_complete(
                    data['tournament_id'],
                    data['match_id'],
                    data['winner']
                )
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON format'
            }))

    async def broadcast_waiting_players(self):
        message = {
            "type": "waiting_players",
            "players": self.waiting_players
        }
        await self.send(text_data=json.dumps(message))

    async def create_tournament(self, players: List[str]):
        tournament_id = str(uuid.uuid4())
        
        # Create semifinals matches
        match1_id = f"{tournament_id}_semi1"
        match2_id = f"{tournament_id}_semi2"
        
        matches = {
            match1_id: TournamentMatch(match1_id, players[0], players[1]),
            match2_id: TournamentMatch(match2_id, players[2], players[3])
        }
        
        tournament = Tournament(
            id=tournament_id,
            players=players,
            state=TournamentState.SEMIFINALS,
            matches=matches,
            current_round_matches={match1_id, match2_id},
            winners=[]
        )
        
        self.tournaments[tournament_id] = tournament
        
        # Assign players to tournament
        for player in players:
            self.player_to_tournament[player] = tournament_id
            
        # Start semifinals matches
        await self.start_matches(tournament)

    async def start_matches(self, tournament: Tournament):
        for match_id in tournament.current_round_matches:
            match = tournament.matches[match_id]
            
            # Create a new game group ID
            game_group_id = f"{match.player1}_{match.player2}"
            
            # Send match ready notification to both players using their specific connections
            for player in [match.player1, match.player2]:
                if player in self.active_connections:
                    connection = self.active_connections[player]
                    opponent = match.player2 if player == match.player1 else match.player1
                    message = {
                        "type": "match_ready",
                        "opponent": opponent,
                        "tournament_id": tournament.id,
                        "match_id": match_id,
                        "game_group_id": game_group_id,
                        "consumer": self.channel_name  # Keep track of tournament consumer
                    }
                    await connection.send(text_data=json.dumps(message))
                else:
                    print(f"Warning: Player {player} not found in active connections")

    async def handle_game_complete(self, tournament_id: str, match_id: str, winner: str):
        tournament = self.tournaments.get(tournament_id)
        if not tournament or match_id not in tournament.matches:
            return
            
        match = tournament.matches[match_id]
        match.winner = winner
        match.game_completed = True
        
        self.cleanup_stale_tournaments()  # Add cleanup call
        await self.broadcast_player_lists()
        
        # Check if all current round matches are complete
        all_complete = all(
            tournament.matches[mid].game_completed 
            for mid in tournament.current_round_matches
        )
        
        if all_complete:
            if tournament.state == TournamentState.SEMIFINALS:
                await self.start_finals(tournament)
            elif tournament.state == TournamentState.FINALS:
                await self.end_tournament(tournament)

    async def start_finals(self, tournament: Tournament):
        # Get winners from semifinals
        semifinal_winners = [
            tournament.matches[match_id].winner
            for match_id in tournament.current_round_matches
        ]
        
        # Create finals match
        finals_match_id = f"{tournament.id}_finals"
        tournament.matches[finals_match_id] = TournamentMatch(
            finals_match_id,
            semifinal_winners[0],
            semifinal_winners[1]
        )
        
        tournament.state = TournamentState.FINALS
        tournament.current_round_matches = {finals_match_id}
        
        # Start finals match
        await self.start_matches(tournament)

    async def end_tournament(self, tournament: Tournament):
        finals_match = tournament.matches[next(iter(tournament.current_round_matches))]
        tournament.state = TournamentState.COMPLETED
        
        # Remove players from tournament tracking
        for player in tournament.players:
            self.player_to_tournament.pop(player, None)
        
        # Notify players about tournament end
        for player in tournament.players:
            try:
                if player in self.active_connections:
                    await self.active_connections[player].send(text_data=json.dumps({
                        "type": "tournament_complete",
                        "tournament_id": tournament.id,
                        "winner": finals_match.winner
                    }))
            except Exception as e:
                print(f"Error notifying player {player} about tournament end: {e}")
        
        # Remove tournament
        self.tournaments.pop(tournament.id, None)
        
        # Broadcast final state update
        await self.broadcast_player_lists()

    def cleanup_stale_tournaments(self):
        """Remove completed tournaments and update player statuses"""
        completed_tournaments = [
            t_id for t_id, tournament in self.tournaments.items()
            if tournament.state == TournamentState.COMPLETED
        ]
        
        for t_id in completed_tournaments:
            tournament = self.tournaments[t_id]
            for player in tournament.players:
                self.player_to_tournament.pop(player, None)
            self.tournaments.pop(t_id)

    async def tournament_update(self, event):
        await self.send(text_data=json.dumps(event['message']))