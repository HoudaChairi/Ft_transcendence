from dataclasses import dataclass
from typing import Dict, List, Set, Optional
from enum import Enum
import math
import time
import json

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
    tournament_data: Optional[dict] = None

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