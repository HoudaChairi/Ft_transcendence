from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .game_models import *
from .managers import GameManager, TournamentManager
from .config import GAME_CONSTANTS, TOURNAMENT_CONFIG
from core.apps.authentication.models import Player, Match
import json
import asyncio
from dataclasses import asdict
from django.db import transaction

class GameConsumer(AsyncWebsocketConsumer):
    game_manager = GameManager()
    connected_players = {}
    player_groups = {}
    games_data = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.username: Optional[str] = None

    async def connect(self):
        try:
            await self.accept()
            print(f"Game WebSocket connected: {self.channel_name}")
        except Exception as e:
            print(f"Error in game connect: {e}")
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
            print(f"Error in game disconnect: {e}")
    
    async def handle_disconnect_win(self, group_id: str) -> None:
        if group_id in self.games_data:
            game = self.games_data[group_id]
            winner = next((player for player in game.connected_players if player != self.username), None)
            
            if winner:
                p1 = next(key for key, value in game.player_labels.items() if value == 'player1')
                p2 = next(key for key, value in game.player_labels.items() if value == 'player2')
                await self.create_match_record(p1, p2, winner, game.score_left, game.score_right)
                
                # Handle tournament game end
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


    async def remove_player_from_game(self, group_id: str) -> None:
        if group_id in self.games_data:
            game = self.games_data[group_id]
            if self.username in game.connected_players:
                game.connected_players.pop(self.username, None)
            if not game.connected_players:
                del self.games_data[group_id]
            print(f"Removed player {self.username} from game {group_id}")

    async def receive(self, text_data=None):
        try:
            data = json.loads(text_data)
            
            if 'username' in data:
                # Handle new player connection
                await self.handle_new_player(data['username'], data.get('tournament_data'))
            
            elif 'action' in data:
                # Only handle movement if game exists and player is in it
                group_id = self.player_groups.get(self.username)
                if not group_id or group_id not in self.games_data:
                    print(f"No active game for player {self.username}")
                    return

                game = self.games_data[group_id]
                if self.username not in game.paddle_directions:
                    print(f"Player {self.username} not in game paddle directions")
                    return

                # Handle movement
                if data['action'] == 'move' and 'direction' in data:
                    await self.move_paddle(data['direction'])
                elif data['action'] == 'stop_move':
                    await self.stop_paddle()

        except Exception as e:
            print(f"Error in game receive: {str(e)}, Player: {self.username}, Data: {text_data}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Internal server error'
            }))

    async def handle_new_player(self, username: str, tournament_data: Optional[dict] = None) -> None:
        try:
            print(f"\n=== New Player Joining ===")
            print(f"Username: {username}")
            print(f"Tournament data: {tournament_data}")
            
            self.username = username
            self.connected_players[username] = self.channel_name

            if tournament_data:
                group_id = f"{tournament_data['player1']}_{tournament_data['player2']}"
                print(f"Game group ID: {group_id}")
                
                if username not in [tournament_data['player1'], tournament_data['player2']]:
                    print(f"ERROR: Player {username} not authorized for game {group_id}")
                    return

                self.player_groups[username] = group_id
                
                if group_id not in self.games_data:
                    print(f"Creating new game state for {group_id}")
                    self.games_data[group_id] = self.game_manager.create_initial_state(
                        tournament_data['player1'],
                        tournament_data['player2']
                    )
                    self.games_data[group_id].tournament_data = tournament_data
                
                await self.channel_layer.group_add(group_id, self.channel_name)
                
                # Check if both players are connected
                connected_players = [p for p in self.connected_players 
                                  if p in [tournament_data['player1'], tournament_data['player2']]]
                print(f"Connected players for group {group_id}: {connected_players}")
                
                if len(connected_players) == 2:
                    print(f"Starting game for group {group_id}")
                    await self.start_game(group_id)

        except Exception as e:
            print(f"ERROR in handle_new_player: {str(e)}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Failed to join game'
            }))

    async def create_game(self) -> None:
        player_list = list(self.connected_players.keys())
        player1, player2 = player_list[-2:]
        group_id = f"{player1}_{player2}"

        # Use game_manager here too
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
        await asyncio.sleep(3)
        
        game = self.games_data[group_id]
        await self.channel_layer.group_send(
            group_id,
            {
                'type': 'game_update',
                'data': {
                    "type": "game_start",
                    "players": {
                        "player1": next(p for p, l in game.player_labels.items() if l == 'player1'),
                        "player2": next(p for p, l in game.player_labels.items() if l == 'player2')
                    },
                    "tournament": bool(game.tournament_data)
                }
            }
        )
        
        # Start the game loop immediately
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
                        "player1": player1,
                        "player2": player2
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
                # Update paddle positions
                self.update_paddle_positions(game)

                # Update ball position based on direction and time
                new_x = game.ball_position.x + (game.ball_direction.x * delta_time)
                new_y = game.ball_position.y + (game.ball_direction.y * delta_time)
                new_position = Vector3(new_x, new_y, 0)

                # Wall collisions (top/bottom)
                if abs(new_position.y) >= C['COURT_HEIGHT']:
                    game.ball_direction.y *= -1
                    new_position.y = math.copysign(C['COURT_HEIGHT'], new_position.y)

                # Paddle collisions
                for player_id, paddle_box in game.paddle_boxes.items():
                    if (paddle_box["min"].x <= new_position.x <= paddle_box["max"].x and
                        paddle_box["min"].y <= new_position.y <= paddle_box["max"].y):
                        # Reverse ball direction completely
                        game.ball_direction.x *= -1
                        # Place ball just outside paddle
                        new_position.x = (paddle_box["max"].x + C['BALL_RADIUS']
                                        if game.ball_direction.x > 0
                                        else paddle_box["min"].x - C['BALL_RADIUS'])
                        break

                # Scoring
                if abs(new_position.x) >= C['COURT_WIDTH']:
                    if new_position.x > 0:
                        game.score_left += 1
                    else:
                        game.score_right += 1
                    # Reset ball to the center
                    game.ball_position = Vector3(0, 0, 0)
                    game.ball_direction = self.game_manager.start_ball_direction()
                    if await self.check_win_condition(game, group_id):
                        break
                else:
                    game.ball_position = new_position

                # Send update
                await self.broadcast_game_state(group_id, game)
                last_update = current_time

            except Exception as e:
                print(f"Error in game loop: {str(e)}")
                continue

    # Channel layer handlers
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
            print(f"Error broadcasting game state: {str(e)}")

    async def check_win_condition(self, game: GameState, group_id: str) -> bool:
        winner = None
        if game.score_left >= GAME_CONSTANTS['WIN_SCORE']:
            winner = next(player for player, label in game.player_labels.items() if label == 'player1')
        elif game.score_right >= GAME_CONSTANTS['WIN_SCORE']:
            winner = next(player for player, label in game.player_labels.items() if label == 'player2')

        if winner:
            game.is_running = False
            print(f"\n=== Game Win Condition Met ===")
            print(f"Winner: {winner}")
            print(f"Tournament data: {game.tournament_data}")
            
            p1 = next(key for key, value in game.player_labels.items() if value == 'player1')
            p2 = next(key for key, value in game.player_labels.items() if value == 'player2')
            await self.create_match_record(p1, p2, winner, game.score_left, game.score_right)
            
            if hasattr(game, 'tournament_data') and game.tournament_data:
                print(f"Processing tournament game completion")
                try:
                    message = {
                        'type': 'game_complete',
                        'tournament_id': game.tournament_data['tournament_id'],
                        'match_id': game.tournament_data['match_id'],
                        'winner': winner
                    }
                    print(f"Sending tournament completion message: {message}")
                    
                    # Make sure we're using the correct consumer channel name
                    if 'consumer' in game.tournament_data:
                        await self.channel_layer.send(
                            game.tournament_data['consumer'],
                            {
                                'type': 'receive',
                                'text_data': json.dumps(message)
                            }
                        )
                        print(f"Sent tournament completion message to {game.tournament_data['consumer']}")
                    else:
                        print("ERROR: No consumer channel in tournament data")
                except Exception as e:
                    print(f"Error sending game completion: {str(e)}")
            else:
                print("Not a tournament game")

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

            # Update player stats
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

            print(f"Created match record: {player1} vs {player2}, winner: {winner}")

        except Player.DoesNotExist as e:
            print(f"Error creating match record: {str(e)}")
            pass
        except Exception as e:
            print(f"Unexpected error creating match record: {str(e)}")
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
                    
                    # Send through channel layer
                    await self.channel_layer.send(
                        tournament_data['consumer'],
                        {
                            'type': 'receive',
                            'data': message  # Send as data instead of text_data
                        }
                    )
                except Exception as e:
                    print(f"Error sending game completion: {str(e)}")

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
    player_channels: Dict[str, str] = {}  # Store channel names
    TOURNAMENT_GROUP = 'tournament_group'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.username: Optional[str] = None
        self.tournament_id: Optional[str] = None
        self.active_connections: Dict[str, AsyncWebsocketConsumer] = {}  # Add this

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
            print(f"\n=== Tournament Message Received ===")
            print(f"Text data: {text_data}")
            
            # If it's already a dict (from channel layer), process it directly
            if isinstance(text_data, dict):
                data = text_data.get('text_data')
                if data:
                    data = json.loads(data)
                else:
                    data = text_data
                print(f"Processed channel layer message: {data}")
            else:
                # If it's text data from WebSocket, parse it
                data = json.loads(text_data)
                print(f"Processed websocket message: {data}")
            
            if data.get('type') == 'join_tournament':
                await self.handle_join_tournament(data['username'])
            elif data.get('type') == 'game_complete':
                print(f"Handling game completion: {data}")
                await self.handle_game_complete(
                    data['tournament_id'],
                    data['match_id'],
                    data['winner']
                )
            
        except json.JSONDecodeError:
            print(f"Error decoding JSON: {text_data}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON format'
            }))
        except Exception as e:
            print(f"Error in tournament receive: {str(e)}")
            print(f"Text data was: {text_data}")
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
        
        # Check if we have enough players
        if len(self.tournament_manager.waiting_players) >= TOURNAMENT_CONFIG['PLAYERS_PER_TOURNAMENT']:
            print(f"Starting tournament with players: {self.tournament_manager.waiting_players[:4]}")  # Debug log
            tournament_players = self.tournament_manager.waiting_players[:TOURNAMENT_CONFIG['PLAYERS_PER_TOURNAMENT']]
            self.tournament_manager.waiting_players = self.tournament_manager.waiting_players[TOURNAMENT_CONFIG['PLAYERS_PER_TOURNAMENT']:]
            tournament = self.tournament_manager.create_tournament(tournament_players)
            await self.start_tournament_matches(tournament)


    async def broadcast_player_lists(self):
        players_in_tournaments = {}
        for tournament_id, tournament in self.tournament_manager.tournaments.items():
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
                "waiting_players": self.tournament_manager.waiting_players,
                "all_connected_players": list(self.connected_players),
                "tournaments": players_in_tournaments,
                "tournament_states": {
                    t_id: t.state.value 
                    for t_id, t in self.tournament_manager.tournaments.items()
                }
            }
        }

        print(f"Broadcasting tournament state: {message}")  # Debug log
        
        await self.channel_layer.group_send(
            self.TOURNAMENT_GROUP,
            {
                "type": "tournament_update",
                "message": message
            }
        )

    async def tournament_update(self, event):
        """Handle updates from channel layer"""
        await self.send(text_data=json.dumps(event['message']))

    async def start_tournament_matches(self, tournament: Tournament):
        """Send match notifications to appropriate players"""
        for match_id in tournament.current_round_matches:
            match = tournament.matches[match_id]
            game_group_id = f"{match.player1}_{match.player2}"

            # Send match ready notification to both players
            await self.channel_layer.group_send(
                self.TOURNAMENT_GROUP,
                {
                    "type": "match_notification",
                    "match_data": {
                        "type": "match_ready",
                        "player1": match.player1,
                        "player2": match.player2,
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
        
        # Only forward if this user is part of the match
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
        # Only send if this connection is for the intended recipient
        if self.username == message["recipient"]:
            await self.send(text_data=json.dumps(message))


    async def handle_game_complete(self, tournament_id: str, match_id: str, winner: str):
        print(f"\n=== Tournament Game Complete ===")
        print(f"Tournament: {tournament_id}")
        print(f"Match: {match_id}")
        print(f"Winner: {winner}")
        
        tournament = self.tournament_manager.tournaments.get(tournament_id)
        if not tournament:
            print(f"ERROR: Tournament {tournament_id} not found!")
            return
            
        print(f"Current tournament state: {tournament.state}")
        print(f"Current round matches: {tournament.current_round_matches}")
        print(f"Matches status: {[(mid, m.game_completed) for mid, m in tournament.matches.items()]}")
        
        # Use TournamentManager to handle the match completion
        success, next_action = self.tournament_manager.handle_match_complete(tournament_id, match_id, winner)
        
        print(f"Match completion result - Success: {success}, Next action: {next_action}")
        
        if not success:
            print(f"Failed to handle match completion!")
            return
            
        if next_action == 'finals':
            print("\n=== Setting Up Finals ===")
            finals_match = self.tournament_manager.setup_finals(tournament_id)
            if finals_match:
                print(f"Finals match created: {finals_match.player1} vs {finals_match.player2}")
                
                # Create the match notification
                game_group_id = f"{finals_match.player1}_{finals_match.player2}"
                match_data = {
                    "type": "match_ready",
                    "player1": finals_match.player1,
                    "player2": finals_match.player2,
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
                
                print(f"Sending finals match notification: {match_data}")
                
                # Send to both players individually
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
                        print(f"Sent finals notification to {player}")
                    except Exception as e:
                        print(f"Error sending finals notification to {player}: {str(e)}")
            else:
                print("Failed to setup finals match!")
                
        elif next_action == 'complete':
            print("\n=== Tournament Complete ===")
            await self.end_tournament(tournament)
        
        # Broadcast updated state
        await self.broadcast_player_lists()
        print("=== End of Game Complete Handler ===\n")

    async def start_matches(self, tournament: Tournament):
        print(f"Starting matches for tournament {tournament.id}")
        for match_id in tournament.current_round_matches:
            match = tournament.matches[match_id]
            game_group_id = f"{match.player1}_{match.player2}"
            
            print(f"Setting up match {match_id}: {match.player1} vs {match.player2}")
            
            # Send match ready notification to both players
            for player in [match.player1, match.player2]:
                try:
                    message = {
                        "type": "match_ready",
                        "opponent": match.player2 if player == match.player1 else match.player1,
                        "tournament_id": tournament.id,
                        "match_id": match_id,
                        "game_group_id": game_group_id,
                        "consumer": self.channel_name,
                        "player1": match.player1,
                        "player2": match.player2
                    }
                    if player in self.active_connections:
                        await self.active_connections[player].send(text_data=json.dumps(message))
                    else:
                        print(f"Warning: Player {player} not found in active connections")
                except Exception as e:
                    print(f"Error notifying player {player} about match: {e}")

    async def start_finals(self, tournament: Tournament):
        print("Setting up finals match")
        # Get winners from semifinals
        semifinal_winners = [
            tournament.matches[match_id].winner
            for match_id in tournament.current_round_matches
        ]
        
        print(f"Finals between: {semifinal_winners[0]} and {semifinal_winners[1]}")
        
        # Create finals match
        finals_match_id = f"{tournament.id}_finals"
        tournament.matches[finals_match_id] = TournamentMatch(
            finals_match_id,
            semifinal_winners[0],
            semifinal_winners[1]
        )
        
        # Update tournament state
        tournament.state = TournamentState.FINALS
        tournament.current_round_matches = {finals_match_id}
        
        # Start finals match
        await self.start_matches(tournament)

    async def end_tournament(self, tournament: Tournament):
        finals_match = tournament.matches[next(iter(tournament.current_round_matches))]
        tournament.state = TournamentState.COMPLETED
        
        # Notify all tournament players about the winner
        message = {
            "type": "tournament_complete",
            "tournament_id": tournament.id,
            "winner": finals_match.winner
        }
        
        await self.channel_layer.group_send(
            self.TOURNAMENT_GROUP,
            {
                "type": "tournament_update",
                "message": message
            }
        )
        
        # Cleanup tournament data
        for player in tournament.players:
            self.tournament_manager.player_to_tournament.pop(player, None)
        del self.tournament_manager.tournaments[tournament.id]
        
        await self.broadcast_player_lists()
