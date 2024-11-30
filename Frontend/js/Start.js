export const CHOICES = `<div class="card-container">
	<div class="card-wrapper">
		<div class="card" id="offline">
			<img src="/textures/png/OfflineG.png" class="card-content" alt="" />
			<div class="card-title title-offline">Offline</div>
		</div>
	</div>
	<div class="card-wrapper">
		<div class="card" id="online">
			<img src="/textures/png/Online.png" class="card-content" alt="" />
			<div class="card-title title-online">Online</div>
		</div>
	</div>
	<div class="card-wrapper">
		<div class="card" id="tournament">
			<img src="/textures/png/Tournament.png" class="card-content" alt="" />
			<div class="card-title title-tournament">Tournament</div>
		</div>
	</div>
</div>`;

export const OFFLINE = `<div class="card-container">
	<div class="card-wrapper">
		<div class="card" id="singleplayer">
			<img src="/textures/png/Singleplayer.png" class="card-content" alt="" />
			<div class="card-title title-offline">Singleplayer</div>
		</div>
	</div>
	<div class="card-wrapper">
		<div class="card" id="multiplayer">
			<img src="/textures/png/Multiplayer.png" class="card-content" alt="" />
			<div class="card-title title-online">Multiplayer</div>
		</div>
	</div>
</div>`;

export const MATCHMAKING = `<div class="comparison-wrapper">
	<div class="user-container">
		<img class="user-image" src="" alt="" id="player1-avatar" />
		<div class="username-match" id="player1">Username 1</div>
	</div>
	<div class="center-icon-container">
		<div class="center-icon-wrapper">
			<img class="center-icon" src="/textures/svg/VS 1.svg" alt="" />
		</div>
	</div>
	<div class="user-container">
		<div class="username-match" id="player2">Matchmaking ...</div>
		<img class="user-image" alt="" id="player2-avatar" />
	</div>
</div>`;

export const TOURNAMENT = `<div class="bracket-section right-bracket">
	<div class="player-container top">
		<img
			class="player-image"
			src=""
			id="player3-avatar"
		/>
		<div class="player-name" id="player3">Player 3</div>
	</div>
	<div class="player-container bottom">
		<div class="player-name text-right" id="player4">Player 4</div>
		<img
			class="player-image"
			src=""
			id="player4-avatar"
		/>
	</div>
	<div class="winner-container">
		<img
			class="winner-image"
			src=""
			id="winner2-avatar"
		/>
		<div class="player-name" id="winner2"></div>
	</div>
</div>
<div class="bracket-section left-bracket">
	<div class="player-container bottom">
		<img
			class="player-image"
			src=""
			id="player2-avatar"
		/>
		<div class="player-name" id="player2">Player 2</div>
	</div>
	<div class="player-container top">
		<div class="player-name text-right" id="player1">Player 1</div>
		<img
			class="player-image"
			src=""
			id="player1-avatar"
		/>
	</div>
	<div class="winner-container">
		<div class="player-name text-right" id="winner1"></div>
		<img
			class="winner-image"
			src=""
			id="winner1-avatar"
		/>
	</div>
</div>
<div class="final-winner-container">
	<img
		class="final-winner-image"
		src=""
		id="final-avatar"
	/>
	<div class="final-winner-name" id="final"></div>
</div>`;

export const START = `<div class="comparison-wrapper">
	<div class="user-container">
		<img class="user-image" src="" alt="" id="player1-avatar" />
		<div class="username-match" id="player1">Username 1</div>
	</div>
	<div class="center-icon-container">
		<div class="center-icon-wrapper">
			<img class="center-icon" src="/textures/svg/VS 1.svg" alt="" />
		</div>
	</div>
	<div class="user-container">
		<div class="username-match" id="player2">Matchmaking ...</div>
		<img class="user-image" alt="" id="player2-avatar" />
	</div>
</div>
<div class="start-button">
	<img class="button-background" src="/textures/svg/Start.svg" alt="" />
	<div class="start-text">Start</div>
</div>`;

export const WIN = `<div class="left-player">
	<div class="player-content">
		<div id="win-username" class="player-name"></div>
		<div class="frame-container">
			<img class="frame-win" src="textures/svg/wood.svg" />
			<img id="win-avatar" class="avatar" src="" />
		</div>
	</div>
	<div class="nameplate-container">
		<img class="nameplate" src="textures/svg/win.svg" />
	</div>
</div>
<div class="right-player">
	<div class="player-content">
		<div id="lose-username" class="player-name"></div>
		<div class="frame-container">
			<img class="frame-win" src="textures/svg/wood.svg" />
			<img id="lose-avatar" class="avatar" src="" />
		</div>
	</div>
	<div class="nameplate-container">
		<img class="nameplate" src="textures/svg/lose.svg" />
	</div>
</div>
<div class="score-container">
	<div id="win-score" class="score">0</div>
	<div class="separator"></div>
	<div id="lose-score" class="score">0</div>
</div>`;
