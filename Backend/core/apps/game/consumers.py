from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .game_models import *
from .managers import GameManager, TournamentManager
from .config import GAME_CONSTANTS, TOURNAMENT_CONFIG
from core.apps.authentication.models import Player, Match
import json
import asyncio
from dataclasses import asdict
from typing import Dict, Set

class GameConsumer(AsyncWebsocketConsumer):
    game_manager = GameManager()
    waiting_players = {}
    connected_players = {}
    player_groups = {}
    games_data = {}
    active_invites = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.username: Optional[str] = None

    async def connect(self):
        try:
            await self.channel_layer.group_add("game_invites", self.channel_name)
            await self.accept()
        except Exception as e:
            await self.close()

    async def disconnect(self, close_code):
        try:
            if self.username:
                await self.channel_layer.group_discard("game_invites", self.channel_name)
                
                group_id = self.player_groups.get(self.username)
                if group_id:
                    game = self.games_data.get(group_id)
                    if game:
                        opponent = next((player for player in game.connected_players if player != self.username), None)
                        if opponent:
                            p1 = next(key for key, value in game.player_labels.items() if value == 'player1')
                            p2 = next(key for key, value in game.player_labels.items() if value == 'player2')

                            score_left = 6 if opponent == p1 else 0
                            score_right = 0 if opponent == p1 else 6

                            await self.create_match_record(p1, p2, opponent, score_left, score_right)
                            await self.handle_game_end(opponent)

                            await self.channel_layer.group_send(
                                group_id,
                                {
                                    'type': 'game_update',
                                    'data': {
                                        "type": "game_end",
                                        "winner": opponent,
                                        "score": {
                                            "player1": {
                                                "usr": p1,
                                                "avatar": await self.get_player_avatar(p1),
                                                "score": score_left
                                            },
                                            "player2": {
                                                "usr": p2,
                                                "avatar": await self.get_player_avatar(p2),
                                                "score": score_right
                                            }
                                        },
                                        "reason": "disconnect"
                                    }
                                }
                            )
                            game.is_running = False

                    await self.channel_layer.group_discard(group_id, self.channel_name)
                    await self.remove_player_from_game(group_id)

                self.connected_players.pop(self.username, None)
                self.waiting_players.pop(self.username, None)
                self.player_groups.pop(self.username, None)
        except Exception as e:
            pass
    
    async def handle_disconnect_win(self, group_id: str) -> None:
        if group_id in self.games_data:
            game = self.games_data[group_id]
            winner = next((player for player in game.connected_players if player != self.username), None)
            
            if winner:
                p1 = next(key for key, value in game.player_labels.items() if value == 'player1')
                p2 = next(key for key, value in game.player_labels.items() if value == 'player2')

                if self.username == p1:
                    score_left = 0
                    score_right = 6
                else:
                    score_left = 6
                    score_right = 0
                
                await self.create_match_record(p1, p2, winner, score_left, score_right)
                
                await self.handle_game_end(winner)
                await self.channel_layer.group_send(
                    group_id,
                    {
                        'type': 'game_update',
                        'data': {
                            "type": "game_end",
                            "winner": winner,
                            "score": {
                                "player1": {
                                    "usr": p1,
                                    "avatar": await self.get_player_avatar(p1),
                                    "score": score_left
                                },
                                "player2": {
                                    "usr": p2,
                                    "avatar": await self.get_player_avatar(p2),
                                    "score": score_right
                                }
                            },
                            "reason": "disconnect"
                        }
                    }
                )
                game.is_running = False


    async def remove_player_from_game(self, group_id: str) -> None:
        if group_id in self.games_data:
            game = self.games_data[group_id]
            if self.username in game.connected_players:
                game.connected_players.pop(self.username, None)
            if not game.connected_players:
                del self.games_data[group_id]

    async def receive(self, text_data=None):
        try:
            data = json.loads(text_data)
            
            if data.get('username'):
                if data.get('invite_game'):
                    await self.handle_invite_game(data['username'], data['opponent'])
                else:
                    await self.handle_new_player(data['username'], data.get('tournament_data'))
            elif data.get('action') in ['move', 'stop_move']:
                group_id = self.player_groups.get(self.username)
                if group_id and group_id in self.games_data:
                    game = self.games_data[group_id]
                    if self.username in game.paddle_directions:
                        if data['action'] == 'move':
                            await self.move_paddle(data['direction'])
                        else:
                            await self.stop_paddle()

        except Exception as e:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Internal server error'
            }))
    
    async def handle_invite_game(self, username: str, opponent: str):
        self.username = username
        group_id = f"{opponent}_{username}" if opponent < username else f"{username}_{opponent}"
        
        self.player_groups[username] = group_id
        self.connected_players[username] = self.channel_name
        await self.channel_layer.group_add(group_id, self.channel_name)

        if group_id not in self.games_data:
            self.games_data[group_id] = self.game_manager.create_initial_state(
                username if username < opponent else opponent,
                opponent if username < opponent else username
            )
        
        game = self.games_data[group_id]
        game.player_labels = {
            username if username < opponent else opponent: 'player1',
            opponent if username < opponent else username: 'player2'
        }

        if len([p for p in self.connected_players if p in [username, opponent]]) == 2:
            await self.channel_layer.group_send(
                group_id,
                {
                    'type': 'game_update',
                    'data': {
                        "type": "game_start",
                        "players": {
                            "player1": {
                                "usr": username if username < opponent else opponent,
                                "avatar": await self.get_player_avatar(username if username < opponent else opponent)
                            },
                            "player2": {
                                "usr": opponent if username < opponent else username,
                                "avatar": await self.get_player_avatar(opponent if username < opponent else username)
                            }
                        },
                        "tournament": False
                    }
                }
            )
            asyncio.create_task(self.delayed_game_start(group_id))
        else:
            await self.send(text_data=json.dumps({
                'type': 'waiting',
                'message': 'Waiting for opponent to join...'
            }))

    async def handle_send_invite(self, recipient):
       invite_id = f"{self.username}_{recipient}"
       self.active_invites[invite_id] = {
           'sender': self.username,
           'recipient': recipient,
           'status': 'pending'
       }
       
       await self.channel_layer.group_send(
           "game_invites",
           {
               'type': 'send_game_invite',
               'invite_id': invite_id,
               'sender': self.username,
               'recipient': recipient
           }
       )

    async def handle_invite_response(self, invite_id, response):
       if invite_id in self.active_invites:
           invite = self.active_invites[invite_id]
           
           if response == 'accepted':
               group_id = invite_id
               
               for player in [invite['sender'], invite['recipient']]:
                   self.connected_players[player] = self.channel_name
                   self.player_groups[player] = group_id
                   await self.channel_layer.group_add(group_id, self.channel_name)

               self.games_data[group_id] = self.game_manager.create_initial_state(
                   invite['sender'], 
                   invite['recipient']
               )
               
               await self.channel_layer.group_send(
                   group_id,
                   {
                       'type': 'game_update',
                       'data': {
                           "type": "game_start",
                           "players": {
                               "player1": {
                                   "usr": invite['sender'],
                                   "avatar": await self.get_player_avatar(invite['sender'])
                               },
                               "player2": {
                                   "usr": invite['recipient'], 
                                   "avatar": await self.get_player_avatar(invite['recipient'])
                               }
                           },
                           "tournament": False
                       }
                   }
               )
               
               asyncio.create_task(self.delayed_game_start(group_id))
           
           await self.channel_layer.group_send(
               "game_invites", 
               {
                   'type': 'broadcast_invite_response',
                   'invite_id': invite_id,
                   'response': response,
                   'sender': invite['sender'],
                   'recipient': invite['recipient']
               }
           )
           
           del self.active_invites[invite_id]

    async def broadcast_invite_response(self, event):
        if self.username in [event['sender'], event['recipient']]:
            await self.send(text_data=json.dumps({
                'type': 'invite_response',
                'invite_id': event['invite_id'],
                'response': event['response'],
                'sender': event['sender'],
                'recipient': event['recipient']
            }))

    async def send_game_invite(self, event):
       if self.username == event['recipient']:
           await self.send(text_data=json.dumps({
               'type': 'game_invite',
               'invite_id': event['invite_id'],
               'sender': event['sender']
           }))

    @database_sync_to_async
    def get_player_avatar(self, username: str) -> str:
        try:
            player = Player.objects.get(username=username)
            return player.get_avatar_url()
        except Player.DoesNotExist:
            pass

    async def setup_matchmaking_game(self, players):
        player1, player2 = players
        group_id = f"{player1}_{player2}"
        
        for player in (player1, player2):
            self.player_groups[player] = group_id
            await self.channel_layer.group_add(group_id, self.connected_players[player])
            self.waiting_players.pop(player, None)

        if self.username == player2:
            self.games_data[group_id] = self.game_manager.create_initial_state(player1, player2)
            await self.send_game_start(group_id, player1, player2)
            asyncio.create_task(self.delayed_game_start(group_id))

    async def send_game_start(self, group_id, player1, player2):
        await self.channel_layer.group_send(
            group_id,
            {
                'type': 'game_update',
                'data': {
                    "type": "game_start",
                    "players": {
                        "player1": {
                            "usr": player1,
                            "avatar": await self.get_player_avatar(player1)
                        },
                        "player2": {
                            "usr": player2,
                            "avatar": await self.get_player_avatar(player2)
                        }
                    },
                    "tournament": False
                }
            }
        )

    async def send_waiting_message(self):
        await self.send(text_data=json.dumps({
            'type': 'waiting',
            'message': 'Waiting for second player...'
        }))

    async def handle_new_player(self, username: str, tournament_data: Optional[dict] = None) -> None:
        try:
            self.username = username
            
            if username in self.player_groups:
                return

            if tournament_data:
                group_id = f"{tournament_data['player1']}_{tournament_data['player2']}"
                
                if username not in [tournament_data['player1'], tournament_data['player2']]:
                    return

                self.player_groups[username] = group_id
                self.connected_players[username] = self.channel_name
                
                if group_id not in self.games_data:
                    self.games_data[group_id] = self.game_manager.create_initial_state(
                        tournament_data['player1'],
                        tournament_data['player2']
                    )
                    self.games_data[group_id].tournament_data = tournament_data
                
                await self.channel_layer.group_add(group_id, self.channel_name)
                
                connected_players = [p for p in self.connected_players 
                                if p in [tournament_data['player1'], tournament_data['player2']]]
                
                if len(connected_players) == 2:
                    await self.start_game(group_id)
            else:
                self.connected_players[username] = self.channel_name
                self.waiting_players[username] = self.channel_name
                
                if len(self.waiting_players) >= 2:
                    available_players = list(self.waiting_players.keys())
                    
                    if len(available_players) >= 2:
                        player1, player2 = available_players[-2:]
                        group_id = f"{player1}_{player2}"

                        player1_avatar = await self.get_player_avatar(player1)
                        player2_avatar = await self.get_player_avatar(player2)
                        
                        for player in (player1, player2):
                            self.player_groups[player] = group_id
                            await self.channel_layer.group_add(
                                group_id,
                                self.connected_players[player]
                            )
                            self.waiting_players.pop(player, None)

                        if username == player2:
                            self.games_data[group_id] = self.game_manager.create_initial_state(player1, player2)
                            
                            await self.channel_layer.group_send(
                                group_id,
                                {
                                    'type': 'game_update',
                                    'data': {
                                        "type": "game_start",
                                        "players": {
                                            "player1": {
                                                "usr": player1,
                                                "avatar": player1_avatar
                                            },
                                            "player2": {
                                                "usr": player2,
                                                "avatar": player2_avatar
                                            }
                                        },
                                        "tournament": False
                                    }
                                }
                            )
                            
                            asyncio.create_task(self.delayed_game_start(group_id))
                    else:
                        await self.send(text_data=json.dumps({
                            'type': 'waiting',
                            'message': 'Waiting for second player...'
                        }))
                else:
                    await self.send(text_data=json.dumps({
                        'type': 'waiting',
                        'message': 'Waiting for second player...'
                    }))

        except Exception as e:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Failed to join game'
            }))

    async def delayed_game_start(self, group_id: str):
        """Start game after delay"""
        await asyncio.sleep(5)
        game = self.games_data[group_id]
        game.ball_direction = self.game_manager.start_ball_direction()
        game.is_running = True
        asyncio.create_task(self.run_game_loop(group_id))

    async def create_game(self) -> None:
        player_list = list(self.connected_players.keys())
        player1, player2 = player_list[-2:]
        group_id = f"{player1}_{player2}"

        self.games_data[group_id] = self.game_manager.create_initial_state(player1, player2)

        for player in (player1, player2):
            self.player_groups[player] = group_id
            await self.channel_layer.group_add(
                group_id,
                self.connected_players[player]
            )

        await self.start_game(group_id)

    async def start_game(self, group_id: str):
        """Start a new game"""
        game = self.games_data[group_id]
        
        await self.channel_layer.group_send(
            group_id,
            {
                'type': 'game_update',
                'data': {
                    "type": "game_start",
                    "players": {
                        "player1": {
                            "usr": next(p for p, l in game.player_labels.items() if l == 'player1'),
                            "avatar": "textures/svg/M.svg"
                        },
                        "player2": {
                            "usr": next(p for p, l in game.player_labels.items() if l == 'player2'),
                            "avatar": "textures/svg/M.svg"
                        }
                    },
                    "tournament": False
                }
            }
        )

        await asyncio.sleep(5)
        game.ball_direction = self.game_manager.start_ball_direction()
        game.is_running = True
        asyncio.create_task(self.run_game_loop(group_id))

    async def create_tournament_game(self, player1: str, player2: str, tournament_data: dict) -> None:
        group_id = f"{player1}_{player2}"
        
        self.games_data[group_id] = self.game_manager.create_initial_state(player1, player2)
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
                'type': 'game_start',
                'data': {
                    "type": "game_start",
                    "players": {
                        "player1": {
                            "usr": player1,
                            "avatar": "textures/svg/M.svg"
                        },
                        "player2": {
                            "usr": player2,
                            "avatar": "textures/svg/M.svg"
                        }
                    },
                    "tournament": True
                }
            }
        )
        
        asyncio.create_task(self.run_game_loop(group_id))

    async def run_game_loop(self, group_id: str) -> None:
        C = GAME_CONSTANTS
        game = self.games_data[group_id]
        last_update = time.time()

        while group_id in self.games_data and game.is_running:
            current_time = time.time()
            delta_time = current_time - last_update
            
            if delta_time < C['FRAME_TIME']:
                await asyncio.sleep(C['FRAME_TIME'] - delta_time)
                continue

            try:
                self.update_paddle_positions(game)

                new_x = game.ball_position.x + (game.ball_direction.x * delta_time)
                new_y = game.ball_position.y + (game.ball_direction.y * delta_time)
                new_position = Vector3(new_x, new_y, 0)

                if abs(new_position.y) >= C['COURT_HEIGHT']:
                    game.ball_direction.y *= -1
                    new_position.y = math.copysign(C['COURT_HEIGHT'], new_position.y)

                for player_id, paddle_box in game.paddle_boxes.items():
                    if (paddle_box["min"].x <= new_position.x <= paddle_box["max"].x and
                        paddle_box["min"].y <= new_position.y <= paddle_box["max"].y):
                        game.ball_direction.x *= -1
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
                    game.ball_direction = self.game_manager.start_ball_direction()
                    if await self.check_win_condition(game, group_id):
                        break
                else:
                    game.ball_position = new_position

                await self.broadcast_game_state(group_id, game)
                last_update = current_time

            except Exception as e:
                continue

    async def game_start(self, event):
        await self.send(text_data=json.dumps(event['data']))

    async def game_update(self, event):
        await self.send(text_data=json.dumps(event['data']))

    async def game_end(self, event):
        await self.send(text_data=json.dumps(event['data']))

    async def move_paddle(self, direction: str) -> None:
        group_id = self.player_groups.get(self.username)
        if group_id and self.username in self.games_data[group_id].paddle_directions:
            game = self.games_data[group_id]
            game.paddle_directions[self.username] = Direction.from_string(direction)
            self.update_paddle_positions(game)

    async def stop_paddle(self) -> None:
        group_id = self.player_groups.get(self.username)
        if group_id and self.username in self.games_data[group_id].paddle_directions:
            self.games_data[group_id].paddle_directions[self.username] = Direction.NONE
            asyncio.create_task(self.broadcast_game_state(group_id, self.games_data[group_id]))

    async def broadcast_game_state(self, group_id: str, game: GameState) -> None:
        try:
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
        except Exception as e:
            pass

    async def check_win_condition(self, game: GameState, group_id: str) -> bool:
        winner = None
        if game.score_left >= GAME_CONSTANTS['WIN_SCORE']:
            winner = next(player for player, label in game.player_labels.items() if label == 'player1')
        elif game.score_right >= GAME_CONSTANTS['WIN_SCORE']:
            winner = next(player for player, label in game.player_labels.items() if label == 'player2')

        if winner:
            game.is_running = False
            
            p1 = next(key for key, value in game.player_labels.items() if value == 'player1')
            p2 = next(key for key, value in game.player_labels.items() if value == 'player2')
            await self.create_match_record(p1, p2, winner, game.score_left, game.score_right)
            
            if hasattr(game, 'tournament_data') and game.tournament_data:
                try:
                    message = {
                        'type': 'game_complete',
                        'tournament_id': game.tournament_data['tournament_id'],
                        'match_id': game.tournament_data['match_id'],
                        'winner': winner
                    }
                    
                    if 'consumer' in game.tournament_data:
                        await self.channel_layer.send(
                            game.tournament_data['consumer'],
                            {
                                'type': 'receive',
                                'text_data': json.dumps(message)
                            }
                        )
                except Exception as e:
                    pass

            await self.channel_layer.group_send(
                group_id,
                {
                    'type': 'game_update',
                    'data': {
                        "type": "game_end",
                        "winner": winner,
                        "score": {
                            "player1": {
                                "usr": p1,
                                "avatar": await self.get_player_avatar(p1),
                                "score": game.score_left
                            },
                            "player2": {
                                "usr": p2,
                                "avatar": await self.get_player_avatar(p2),
                                "score": game.score_right
                            }
                        },
                        "reason": "score"
                    }
                }
            )
            return True
        return False
    
    @database_sync_to_async
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


        except Player.DoesNotExist as e:
            pass
        except Exception as e:
            pass

    async def handle_game_end(self, winner: str) -> None:
        group_id = self.player_groups.get(self.username)
        if group_id:
            game = self.games_data[group_id]
            tournament_data = getattr(game, 'tournament_data', None)
            
            if tournament_data:
                try:
                    message = {
                        'type': 'game_complete',
                        'tournament_id': tournament_data['tournament_id'],
                        'match_id': tournament_data['match_id'],
                        'winner': winner
                    }
                    
                    await self.channel_layer.send(
                        tournament_data['consumer'],
                        {
                            'type': 'receive',
                            'data': message
                        }
                    )
                except Exception as e:
                    pass

    def update_paddle_positions(self, game: GameState) -> None:
        C = GAME_CONSTANTS
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

    def validate_paddle_movement(self, old_pos: Vector3, new_pos: Vector3, delta_time: float) -> bool:
        C = GAME_CONSTANTS
        max_movement = C['PADDLE_SPEED'] * delta_time * 1.1
        movement = math.sqrt((new_pos.y - old_pos.y) ** 2)
        return movement <= max_movement

class TournamentConsumer(AsyncWebsocketConsumer):
    tournament_manager = TournamentManager()
    connected_players: Set[str] = set()
    player_channels: Dict[str, str] = {}
    TOURNAMENT_GROUP = 'tournament_group'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.username: Optional[str] = None
        self.tournament_id: Optional[str] = None
        self.active_connections: Dict[str, AsyncWebsocketConsumer] = {}

    async def connect(self):
        await self.accept()
        await self.channel_layer.group_add(
            self.TOURNAMENT_GROUP,
            self.channel_name
        )

    async def disconnect(self, close_code):
        if self.username:
            if self.username in self.tournament_manager.waiting_players:
                self.tournament_manager.waiting_players.remove(self.username)
            
            self.connected_players.discard(self.username)
            
            tournament = self.tournament_manager.get_player_tournament(self.username)
            if tournament and tournament.state == TournamentState.WAITING:
                tournament.players.remove(self.username)
                if not tournament.players:
                    del self.tournament_manager.tournaments[tournament.id]
            
            await self.broadcast_player_lists()

    async def receive(self, text_data=None):
        try:
            
            if isinstance(text_data, dict):
                data = text_data.get('text_data')
                if data:
                    data = json.loads(data)
                else:
                    data = text_data
            else:
                data = json.loads(text_data)
            
            if data.get('type') == 'join_tournament':
                await self.handle_join_tournament(data['username'])
            elif data.get('type') == 'game_complete':
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
        except Exception as e:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Internal server error'
            }))

    async def handle_join_tournament(self, username: str):
        self.username = username
        self.connected_players.add(username)
        
        if username not in self.tournament_manager.waiting_players:
            self.tournament_manager.waiting_players.append(username)
            
        await self.broadcast_player_lists()
        
        if len(self.tournament_manager.waiting_players) >= TOURNAMENT_CONFIG['PLAYERS_PER_TOURNAMENT']:
            tournament_players = self.tournament_manager.waiting_players[:TOURNAMENT_CONFIG['PLAYERS_PER_TOURNAMENT']]
            self.tournament_manager.waiting_players = self.tournament_manager.waiting_players[TOURNAMENT_CONFIG['PLAYERS_PER_TOURNAMENT']:]
            tournament = self.tournament_manager.create_tournament(tournament_players)
            
            for player in tournament_players:
                if player in self.connected_players:
                    self.tournament_id = tournament.id
            
            await self.start_tournament_matches(tournament)
            await self.broadcast_player_lists()

    @database_sync_to_async
    def get_player_details(self, username: str) -> dict:
        try:
            player = Player.objects.get(username=username)
            return {
                "username": player.tournament_username,
                "avatar": player.get_avatar_url()
            }
        except Player.DoesNotExist:
            pass

    async def broadcast_player_lists(self):
        try:
            players_in_tournaments = {}
            for t_id, tournament in self.tournament_manager.tournaments.items():
                semifinal_matches = {match_id: match for match_id, match in tournament.matches.items() if 'semi' in match_id}
                
                semi1_winner = next((match.winner for match_id, match in semifinal_matches.items() if 'semi1' in match_id), None)
                semi2_winner = next((match.winner for match_id, match in semifinal_matches.items() if 'semi2' in match_id), None)
                
                tournament_players = [await self.get_player_details(player) for player in tournament.players]
                
                players_in_tournaments[t_id] = {
                    'matches': {
                        match_id: {
                            'player1': await self.get_player_details(match.player1),
                            'player2': await self.get_player_details(match.player2),
                            'winner': await self.get_player_details(match.winner) if match.winner else None,
                            'completed': match.game_completed,
                            'match_type': 'semi1' if 'semi1' in match_id else 'semi2' if 'semi2' in match_id else 'finals'
                        }
                        for match_id, match in tournament.matches.items()
                    },
                    'semifinal_winners': {
                        'semi1': await self.get_player_details(semi1_winner) if semi1_winner else None,
                        'semi2': await self.get_player_details(semi2_winner) if semi2_winner else None
                    },
                    'state': tournament.state.value,
                    'players': tournament_players
                }

            await self.channel_layer.group_send(
                self.TOURNAMENT_GROUP,
                {
                    "type": "tournament_update",
                    "message": {
                        "type": "players_update",
                        "data": {
                            "waiting_players": [await self.get_player_details(player) for player in self.tournament_manager.waiting_players],
                            "all_connected_players": [await self.get_player_details(player) for player in self.connected_players],
                            "tournaments": players_in_tournaments,
                            "tournament_states": {t_id: t.state.value for t_id, t in self.tournament_manager.tournaments.items()}
                        }
                    }
                }
            )
        except Exception as e:
            pass

    async def tournament_update(self, event):
        try:
            message = event['message']
            if message['type'] == 'players_update':
                tournament = self.tournament_manager.get_player_tournament(self.username)
                
                filtered_data = {
                    'waiting_players': message['data']['waiting_players'],
                    'all_connected_players': message['data']['all_connected_players'],
                    'tournaments': {},
                    'tournament_states': {}
                }
                
                if tournament:
                    tournament_id = tournament.id
                    filtered_data['tournaments'][tournament_id] = message['data']['tournaments'][tournament_id]
                    filtered_data['tournament_states'][tournament_id] = message['data']['tournament_states'][tournament_id]

                message['data'] = filtered_data
                    
            await self.send(text_data=json.dumps(message))
        except Exception as e:
            pass

    async def start_tournament_matches(self, tournament: Tournament):
        """Send match notifications to appropriate players"""
        for match_id in tournament.current_round_matches:
            match = tournament.matches[match_id]
            game_group_id = f"{match.player1}_{match.player2}"

            player1_details = await self.get_player_details(match.player1)
            player2_details = await self.get_player_details(match.player2)

            await self.channel_layer.group_send(
                self.TOURNAMENT_GROUP,
                {
                    "type": "match_notification",
                    "match_data": {
                        "type": "match_ready",
                        "player1": player1_details.get('username'),
                        "player2": player2_details.get('username'),
                        "avatar1": player1_details.get('avatar'),
                        "avatar2": player2_details.get('avatar'),
                        "tournament_id": tournament.id,
                        "match_id": match_id,
                        "game_group_id": game_group_id,
                        "consumer": self.channel_name
                    }
                }
            )

    async def match_notification(self, event):
        """Handle match notifications"""
        match_data = event["match_data"]
        
        if self.username in [match_data["player1"], match_data["player2"]]:
            match_data["opponent"] = (
                match_data["player2"] 
                if self.username == match_data["player1"] 
                else match_data["player1"]
            )
            await self.send(text_data=json.dumps(match_data))

    async def tournament_match_ready(self, event):
        """Handle match ready messages"""
        message = event["message"]
        if self.username == message["recipient"]:
            await self.send(text_data=json.dumps(message))


    async def handle_game_complete(self, tournament_id: str, match_id: str, winner: str):
        tournament = self.tournament_manager.tournaments.get(tournament_id)
        if not tournament:
            return
        
        success, next_action = self.tournament_manager.handle_match_complete(tournament_id, match_id, winner)

        if not success:
            return
            
        if next_action == 'finals':
            finals_match = self.tournament_manager.setup_finals(tournament_id)
            if finals_match:
                game_group_id = f"{finals_match.player1}_{finals_match.player2}"
                player1_details = await self.get_player_details(finals_match.player1)
                player2_details = await self.get_player_details(finals_match.player2)
                match_data = {
                    "type": "match_ready",
                    "player1": player1_details.get('username'),
                    "player2": player2_details.get('username'),
                    "avatar1": player1_details.get('avatar'),
                    "avatar2": player2_details.get('avatar'),
                    "tournament_id": tournament_id,
                    "match_id": finals_match.match_id,
                    "game_group_id": game_group_id,
                    "consumer": self.channel_name,
                    "tournament_data": {
                        "tournament_id": tournament_id,
                        "match_id": finals_match.match_id,
                        "player1": finals_match.player1,
                        "player2": finals_match.player2
                    }
                }

                for player in [finals_match.player1, finals_match.player2]:
                    try:
                        await self.channel_layer.group_send(
                            self.TOURNAMENT_GROUP,
                            {
                                "type": "match_notification",
                                "match_data": {
                                    **match_data,
                                    "opponent": finals_match.player2 if player == finals_match.player1 else finals_match.player1
                                }
                            }
                        )
                    except Exception as e:
                        pass
                
        elif next_action == 'complete':
            await self.end_tournament(tournament)
        
        await self.broadcast_player_lists()

    async def start_matches(self, tournament: Tournament):
        for match_id in tournament.current_round_matches:
            match = tournament.matches[match_id]
            game_group_id = f"{match.player1}_{match.player2}"
            
            player1_details = await self.get_player_details(match.player1)
            player2_details = await self.get_player_details(match.player2)
            for player in [match.player1, match.player2]:
                try:
                    message = {
                        "type": "match_ready",
                        "opponent": match.player2 if player == match.player1 else match.player1,
                        "tournament_id": tournament.id,
                        "match_id": match_id,
                        "game_group_id": game_group_id,
                        "consumer": self.channel_name,
                        "player1": player1_details.get('username'),
                        "player2": player2_details.get('username'),
                        "avatar1": player1_details.get('avatar'),
                        "avatar2": player2_details.get('avatar'),
                    }
                    if player in self.active_connections:
                        await self.active_connections[player].send(text_data=json.dumps(message))
                except Exception as e:
                    pass

    async def start_finals(self, tournament: Tournament):
        semifinal_winners = [
            tournament.matches[match_id].winner
            for match_id in tournament.current_round_matches
        ]
        
        finals_match_id = f"{tournament.id}_finals"
        tournament.matches[finals_match_id] = TournamentMatch(
            finals_match_id,
            semifinal_winners[0],
            semifinal_winners[1]
        )
        
        tournament.state = TournamentState.FINALS
        tournament.current_round_matches = {finals_match_id}
        
        await self.start_matches(tournament)

    async def end_tournament(self, tournament: Tournament):
        finals_match = tournament.matches[next(iter(tournament.current_round_matches))]
        tournament.state = TournamentState.COMPLETED
        
        winner = await self.get_player_details(finals_match.winner)
        message = {
            "type": "tournament_complete",
            "tournament_id": tournament.id,
            "winner": winner
        }
        
        await self.channel_layer.group_send(
            self.TOURNAMENT_GROUP,
            {
                "type": "tournament_update",
                "message": message
            }
        )
        
        for player in tournament.players:
            self.tournament_manager.player_to_tournament.pop(player, None)
        del self.tournament_manager.tournaments[tournament.id]
        
        await self.broadcast_player_lists()
