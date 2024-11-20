class Vector3 {
	constructor(x, y, z = 0) {
		this.x = x;
		this.y = y;
		this.z = z;
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

const GAME_CONSTANTS = {
	MIN_DIR: 0.5,
	VELOCITY: 30,
	FACTOR: 1.2,
	WIN_SCORE: 5,
	PADDLE_SPEED: 30,
	PADDLE_HEIGHT: 280,
	COURT_HEIGHT: 785,
	BALL_RADIUS: 60,
};

export { Vector3, GAME_CONSTANTS };
