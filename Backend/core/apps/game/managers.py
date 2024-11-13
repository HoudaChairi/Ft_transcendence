from .game_models import *
from .config import GAME_CONSTANTS
from typing import Dict, List, Optional, Tuple
import random
import uuid

class GameManager:
    @staticmethod
    def create_initial_state(player1: str, player2: str) -> GameState:
        C = GAME_CONSTANTS
        
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
            ball_direction=GameManager.start_ball_direction()
        )

    @staticmethod
    def start_ball_direction() -> Vector3:
        C = GAME_CONSTANTS
        angle = random.uniform(-math.pi/4, math.pi/4)
        direction = random.choice([-1, 1])
        
        x = math.cos(angle) * direction
        y = math.sin(angle)
        
        vector = Vector3(x, y, 0).normalize()
        return vector * (C['VELOCITY'] * C['FACTOR'])

    @staticmethod
    def handle_collision(paddle_pos: Vector3, ball_pos: Vector3) -> Vector3:
        C = GAME_CONSTANTS
        relative_y = (ball_pos.y - paddle_pos.y) / C['PADDLE_HEIGHT']
        angle = relative_y * (math.pi * 0.42)
        direction = -1 if paddle_pos.x < 0 else 1
        
        x = math.cos(angle) * direction
        y = math.sin(angle)
        
        vector = Vector3(x, y, 0).normalize()
        return vector * (C['VELOCITY'] * C['FACTOR'])

class TournamentManager:
    def __init__(self):
        self.tournaments: Dict[str, Tournament] = {}
        self.player_to_tournament: Dict[str, str] = {}
        self.waiting_players: List[str] = []

    def create_tournament(self, players: List[str]) -> Tournament:
        tournament_id = str(uuid.uuid4())
        
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
        
        for player in players:
            self.player_to_tournament[player] = tournament_id
            
        return tournament

    def get_player_tournament(self, player: str) -> Optional[Tournament]:
        tournament_id = self.player_to_tournament.get(player)
        return self.tournaments.get(tournament_id)

    def handle_match_complete(self, tournament_id: str, match_id: str, winner: str) -> Tuple[bool, Optional[str]]:
        """
        Handle match completion and return status and next action.
        Returns: (success, next_action)
            where next_action can be 'finals' or 'complete' or None
        """
        tournament = self.tournaments.get(tournament_id)
        if not tournament or match_id not in tournament.matches:
            print(f"Tournament {tournament_id} or match {match_id} not found")
            return False, None
            
        match = tournament.matches[match_id]
        match.winner = winner
        match.game_completed = True
        print(f"Match {match_id} completed: {winner} won")
        
        # Check if all current round matches are complete
        all_complete = all(
            tournament.matches[mid].game_completed 
            for mid in tournament.current_round_matches
        )
        
        if all_complete:
            if tournament.state == TournamentState.SEMIFINALS:
                return True, 'finals'
            elif tournament.state == TournamentState.FINALS:
                return True, 'complete'
        
        return True, None

    def setup_finals(self, tournament_id: str) -> Optional[TournamentMatch]:
        """Set up finals match and return the new match or None if error"""
        tournament = self.tournaments.get(tournament_id)
        if not tournament:
            return None
        
        # Get winners from semifinals
        semifinal_winners = [
            tournament.matches[match_id].winner
            for match_id in tournament.current_round_matches
        ]
        
        if len(semifinal_winners) != 2:
            print("Error: Need exactly 2 semifinal winners")
            return None
            
        # Create finals match
        finals_match_id = f"{tournament.id}_finals"
        finals_match = TournamentMatch(
            finals_match_id,
            semifinal_winners[0],
            semifinal_winners[1]
        )
        
        # Update tournament state
        tournament.matches[finals_match_id] = finals_match
        tournament.state = TournamentState.FINALS
        tournament.current_round_matches = {finals_match_id}
        
        return finals_match