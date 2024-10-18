export const CHANGE_USERNAME = `<div class="frame-wrapper">
	<div class="rectangle-parent-user">
		<img
			class="rectangle-icon-user"
			alt=""
			src="/textures/svg/RectangleUP.svg"
		/>
		<div class="change-username">Change Username</div>
	</div>
</div>
<div class="select-new-username-parent">
	<div class="select-new-username">Select New Username</div>
	<div class="username-wrapper">
		<input type="text" class="username-user" placeholder="Username" id="username"/>
	</div>
	<div class="sette-wrapper">
		<div class="change-username">Sette</div>
	</div>
</div>`;

export const CHANGE_AVATAR = `<div class="frame-wrapper">
	<div class="rectangle-parent-user">
		<img
			class="rectangle-icon-user"
			alt=""
			src="/textures/svg/RectangleUP.svg"
		/>
		<div class="change-useranme">Change Avatar</div>
	</div>
</div>
<div class="select-new-username-parent">
	<div class="change-avatar">Select New Avatar</div>
	<div class="ellipse-wrapper">
		<input
			type="file"
			id="avatarUpload"
			style="display: none"
			accept="image/*"
		/>
		<img
			class="frame-child-user"
			id="avatarImage"
			alt="avatar"
			src="/textures/svg/Trans.svg"
			style="cursor: pointer"
		/>
	</div>
	<div class="sette-wrapper">
		<div class="change-avatar">Sette</div>
	</div>
</div>`;
