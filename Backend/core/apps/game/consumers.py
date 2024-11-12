from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .game_models import *
from .managers import GameManager, TournamentManager
from .config import GAME_CONSTANTS, TOURNAMENT_CONFIG
import json
import asyncio
from dataclasses import asdict

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
            self.username = username
            self.connected_players[username] = self.channel_name

            if tournament_data:
                group_id = f"{tournament_data['player1']}_{tournament_data['player2']}"
                
                # Verify this player is part of the game
                if username not in [tournament_data['player1'], tournament_data['player2']]:
                    print(f"Player {username} not authorized for game {group_id}")
                    return

                self.player_groups[username] = group_id
                
                # Create or join game
                if group_id not in self.games_data:
                    # Use game_manager with both players
                    self.games_data[group_id] = self.game_manager.create_initial_state(
                        tournament_data['player1'],
                        tournament_data['player2']
                    )
                    self.games_data[group_id].tournament_data = tournament_data
                
                # Add to group
                await self.channel_layer.group_add(group_id, self.channel_name)
                
                # If both players connected, start game
                connected_players = [p for p in self.connected_players if p in [tournament_data['player1'], tournament_data['player2']]]
                if len(connected_players) == 2:
                    await self.start_game(group_id)

        except Exception as e:
            print(f"Error in handle_new_player: {str(e)}")
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
            
            p1 = next(key for key, value in game.player_labels.items() if value == 'player1')
            p2 = next(key for key, value in game.player_labels.items() if value == 'player2')
            await database_sync_to_async(self.create_match_record)(p1, p2, winner, game.score_left, game.score_right)
            
            await self.handle_game_end(winner)
            await self.channel_layer.group_send(
                group_id,
                {
                    'type': 'game_end',
                    'data': {
                        "type": "game_end",
                        "winner": winner,
                        "reason": "score"
                    }
                }
            )
            return True
        return False

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

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            
            if data.get('type') == 'join_tournament':
                await self.handle_join_tournament(data['username'])
            elif data.get('type') == 'game_complete':
                await self.handle_game_complete(
                    data['tournament_id'],
                    data['match_id'],
                    data['winner']
                )
        except Exception as e:
            print(f"Error in tournament receive: {str(e)}")
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
                "tournaments": players_in_tournaments
            }
        }

        # Broadcast to group
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
        if self.tournament_manager.handle_match_complete(tournament_id, match_id, winner):
            tournament = self.tournament_manager.tournaments[tournament_id]
            await self.broadcast_player_lists()
            
            all_complete = all(
                match.game_completed 
                for match in tournament.matches.values() 
                if match.match_id in tournament.current_round_matches
            )
            
            if all_complete:
                if tournament.state == TournamentState.SEMIFINALS:
                    await self.start_finals(tournament)
                elif tournament.state == TournamentState.FINALS:
                    await self.end_tournament(tournament)

    async def start_matches(self, tournament: Tournament):
        for match_id in tournament.current_round_matches:
            match = tournament.matches[match_id]
            game_group_id = f"{match.player1}_{match.player2}"
            
            # Send match ready notification to both players
            for player in [match.player1, match.player2]:
                try:
                    message = {
                        "type": "match_ready",
                        "opponent": match.player2 if player == match.player1 else match.player1,
                        "player1": match.player1,
                        "player2": match.player2,
                        "tournament_id": tournament.id,
                        "match_id": match_id,
                        "game_group_id": game_group_id,
                        "consumer": self.channel_name
                    }
                    await self.send(text_data=json.dumps(message))
                except Exception as e:
                    print(f"Error notifying player {player}: {e}")

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
        
        await self.start_tournament_matches(tournament)

    async def end_tournament(self, tournament: Tournament):
        finals_match = tournament.matches[next(iter(tournament.current_round_matches))]
        tournament.state = TournamentState.COMPLETED
        
        # Notify all tournament players about the winner
        for player in tournament.players:
            try:
                message = {
                    "type": "tournament_complete",
                    "tournament_id": tournament.id,
                    "winner": finals_match.winner
                }
                await self.send(text_data=json.dumps(message))
            except Exception as e:
                print(f"Error notifying player {player} about tournament end: {e}")
        
        # Cleanup tournament data
        for player in tournament.players:
            self.tournament_manager.player_to_tournament.pop(player, None)
        del self.tournament_manager.tournaments[tournament.id]
        
        await self.broadcast_player_lists()