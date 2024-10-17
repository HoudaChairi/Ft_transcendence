import game from './Game';

const keyState = new Set();
const KEY_UP = 'ArrowUp';
const KEY_DOWN = 'ArrowDown';
const KEY_W = 'w';
const KEY_S = 's';
const KEY_START = ' ';

window.addEventListener('keydown', e => {
	keyState.add(e.key);
	updateMovement();
});

window.addEventListener('keyup', e => {
	keyState.delete(e.key);
	updateMovement();
});

function updateMovement() {
	game.stopPlayerMovement();
	game.stopPlayer2Movement();

	if (keyState.has(KEY_START)) game.startBall();
	if (keyState.has(KEY_UP)) game.moveUp2();
	if (keyState.has(KEY_DOWN)) game.moveDown2();
	if (keyState.has(KEY_W)) game.moveUp();
	if (keyState.has(KEY_S)) game.moveDown();
}
