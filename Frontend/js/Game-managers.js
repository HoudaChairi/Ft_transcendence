class Vector3 {
	constructor(x, y, z = 0) {
		this.x = x;
		this.y = y;
		this.z = z;
	}

	add(other) {
		return new Vector3(
			this.x + other.x,
			this.y + other.y,
			this.z + other.z
		);
	}

	multiply(scalar) {
		return new Vector3(this.x * scalar, this.y * scalar, this.z * scalar);
	}

	normalize() {
		const magnitude = Math.sqrt(
			this.x * this.x + this.y * this.y + this.z * this.z
		);
		if (magnitude === 0) return this;
		return new Vector3(
			this.x / magnitude,
			this.y / magnitude,
			this.z / magnitude
		);
	}
}

const Direction = {
	NONE: 0,
	UP: -1,
	DOWN: 1,

	fromString(direction) {
		if (direction === 'moveUp') return this.UP;
		if (direction === 'moveDown') return this.DOWN;
		return this.NONE;
	},
};

const GAME_CONSTANTS = {
	MIN_DIR: 0.5,
	VELOCITY: 30,
	FACTOR: 1.2,
	WIN_SCORE: 5,
	PADDLE_SPEED: 30,
	PADDLE_HEIGHT: 280,
	COURT_HEIGHT: 785,
};

class GameState {
	constructor(player1, player2) {
		this.connectedPlayers = { [player1]: player1, [player2]: player2 };
		this.playerLabels = { [player1]: 'player1', [player2]: 'player2' };
		this.paddlePositions = {
			[player1]: new Vector3(-1300, 0, 0),
			[player2]: new Vector3(1300, 0, 0),
		};
		this.paddleDirections = {
			[player1]: Direction.NONE,
			[player2]: Direction.NONE,
		};
		this.paddleBoxes = {
			[player1]: {
				min: new Vector3(-1400, -GAME_CONSTANTS.PADDLE_HEIGHT, 0),
				max: new Vector3(-1200, GAME_CONSTANTS.PADDLE_HEIGHT, 0),
			},
			[player2]: {
				min: new Vector3(1200, -GAME_CONSTANTS.PADDLE_HEIGHT, 0),
				max: new Vector3(1400, GAME_CONSTANTS.PADDLE_HEIGHT, 0),
			},
		};
		this.ballPosition = new Vector3(0, 0, 0);
		this.ballDirection = GameManager.startBallDirection();
		this.scoreLeft = 0;
		this.scoreRight = 0;
		this.isRunning = true;
		this.lastUpdate = Date.now();
		this.tournamentData = null;
	}
}

class GameManager {
	static createInitialState(player1, player2) {
		return new GameState(player1, player2);
	}

	static startBallDirection() {
		const angle = (Math.random() * Math.PI) / 2 - Math.PI / 4;
		const direction = Math.random() < 0.5 ? -1 : 1;

		const x = Math.cos(angle) * direction;
		const y = Math.sin(angle);

		const vector = new Vector3(x, y, 0).normalize();
		return vector.multiply(GAME_CONSTANTS.VELOCITY * GAME_CONSTANTS.FACTOR);
	}

	static handleCollision(paddlePos, ballPos) {
		const relativeY =
			(ballPos.y - paddlePos.y) / GAME_CONSTANTS.PADDLE_HEIGHT;
		const angle = relativeY * (Math.PI * 0.42);
		const direction = paddlePos.x < 0 ? -1 : 1;

		const x = Math.cos(angle) * direction;
		const y = Math.sin(angle);

		const vector = new Vector3(x, y, 0).normalize();
		return vector.multiply(GAME_CONSTANTS.VELOCITY * GAME_CONSTANTS.FACTOR);
	}

	static updatePaddlePositions(game) {
		const maxY = GAME_CONSTANTS.COURT_HEIGHT - GAME_CONSTANTS.PADDLE_HEIGHT;
		const currentTime = Date.now();
		const deltaTime = (currentTime - game.lastUpdate) / 1000;

		for (const [playerId, direction] of Object.entries(
			game.paddleDirections
		)) {
			if (direction !== Direction.NONE) {
				const currentPos = game.paddlePositions[playerId];
				const newY = Math.max(
					Math.min(
						currentPos.y +
							direction * GAME_CONSTANTS.PADDLE_SPEED * deltaTime,
						maxY
					),
					-maxY
				);

				const newPos = new Vector3(currentPos.x, newY, currentPos.z);
				if (
					GameManager.validatePaddleMovement(
						currentPos,
						newPos,
						deltaTime
					)
				) {
					game.paddlePositions[playerId] = newPos;
					game.paddleBoxes[playerId].min.y =
						newY - GAME_CONSTANTS.PADDLE_HEIGHT;
					game.paddleBoxes[playerId].max.y =
						newY + GAME_CONSTANTS.PADDLE_HEIGHT;
				}
			}
		}

		game.lastUpdate = currentTime;
	}

	static validatePaddleMovement(oldPos, newPos, deltaTime) {
		const maxMovement = GAME_CONSTANTS.PADDLE_SPEED * deltaTime * 1.1;
		const movement = Math.sqrt((newPos.y - oldPos.y) ** 2);
		return movement <= maxMovement;
	}

	static checkCollisions(game) {
		if (Math.abs(game.ballPosition.y) >= GAME_CONSTANTS.COURT_HEIGHT) {
			game.ballDirection.y *= -1;
			game.ballPosition.y =
				Math.sign(game.ballPosition.y) * GAME_CONSTANTS.COURT_HEIGHT;
		}

		for (const [playerId, paddleBox] of Object.entries(game.paddleBoxes)) {
			if (
				game.ballPosition.x >= paddleBox.min.x &&
				game.ballPosition.x <= paddleBox.max.x &&
				game.ballPosition.y >= paddleBox.min.y &&
				game.ballPosition.y <= paddleBox.max.y
			) {
				game.ballDirection = GameManager.handleCollision(
					game.paddlePositions[playerId],
					game.ballPosition
				);
				break;
			}
		}

		if (Math.abs(game.ballPosition.x) >= GAME_CONSTANTS.COURT_WIDTH) {
			if (game.ballPosition.x > 0) {
				game.scoreLeft++;
			} else {
				game.scoreRight++;
			}
			game.ballPosition = new Vector3(0, 0, 0);
			game.ballDirection = GameManager.startBallDirection();
			return true;
		}

		return false;
	}

	static updateGameState(game, deltaTime) {
		GameManager.updatePaddlePositions(game);

		const newX = game.ballPosition.x + game.ballDirection.x * deltaTime;
		const newY = game.ballPosition.y + game.ballDirection.y * deltaTime;
		game.ballPosition = new Vector3(newX, newY, 0);

		return GameManager.checkCollisions(game);
	}
}

export { GameManager, GameState, Vector3, Direction, GAME_CONSTANTS };
