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
		<input type="text" class="username-user" placeholder="Username" />
	</div>
	<div class="sette-wrapper">
		<div class="change-username">Sette</div>
	</div>
</div>`;

export const CHANGE_PASSWORD = `<div class="frame-wrapper">
	<div class="rectangle-parent-user">
		<img
			class="rectangle-icon-user"
			alt=""
			src="/textures/svg/RectangleUP.svg"
		/>
		<div class="change-username">Change Password</div>
	</div>
</div>
<div class="select-new-username-parent">
	<div class="select-new-username">Change your Password!?</div>
	<div class="username-wrapper">
		<input
			type="password"
			class="username-user"
			placeholder="Old Password"
			id="oldpass"
		/>
	</div>
	<div class="username-wrapper">
		<input
			type="password"
			class="username-user"
			placeholder="New Password"
			id="newpass"
		/>
	</div>
	<div class="username-wrapper">
		<input
			type="password"
			class="username-user"
			placeholder="Confirm Password"
			id="confpass"
		/>
	</div>
	<div class="sette-wrapper">
		<div class="change-username">Sette</div>
	</div>
</div>`;

export const CHANGE_FIRST_NAME = `<div class="frame-wrapper">
	<div class="rectangle-parent-user">
		<img
			class="rectangle-icon-user"
			alt=""
			src="/textures/svg/RectangleUP.svg"
		/>
		<div class="change-username">Change First Name</div>
	</div>
</div>
<div class="select-new-username-parent">
	<div class="select-new-username">Select New First Name</div>
	<div class="username-wrapper">
		<input type="text" class="username-user" placeholder="First Name" />
	</div>
	<div class="sette-wrapper">
		<div class="change-username">Sette</div>
	</div>
</div>`;

export const CHANGE_LAST_NAME = `<div class="frame-wrapper">
	<div class="rectangle-parent-user">
		<img
			class="rectangle-icon-user"
			alt=""
			src="/textures/svg/RectangleUP.svg"
		/>
		<div class="change-username">Change Last Name</div>
	</div>
</div>
<div class="select-new-username-parent">
	<div class="select-new-username">Select New Last Name</div>
	<div class="username-wrapper">
		<input type="text" class="username-user" placeholder="Last Name" />
	</div>
	<div class="sette-wrapper">
		<div class="change-username">Sette</div>
	</div>
</div>`;

export const CHANGE_EMAIL = `<div class="frame-wrapper">
	<div class="rectangle-parent-user">
		<img
			class="rectangle-icon-user"
			alt=""
			src="/textures/svg/RectangleUP.svg"
		/>
		<div class="change-username">Change Email</div>
	</div>
</div>
<div class="select-new-username-parent">
	<div class="select-new-username">Select New Email</div>
	<div class="username-wrapper">
		<input type="email" class="username-user" placeholder="Email" />
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

export const REMOTE = `<div class="frame-wrapper">
<div class="rectangle-parent-user">
	<img
		class="rectangle-icon-user"
		alt=""
		src="/textures/svg/RectangleUP.svg"
	/>
	<div class="change-username">Remote</div>
</div>
</div>
<div class="select-new-username-parent">
<div class="select-new-username">You can't enable 2FA in a Remote account</div>
</div>`

export const TWOFA = `<div class="frame-wrapper">
	<div class="rectangle-parent-user">
		<img
			class="rectangle-icon-user"
			alt=""
			src="/textures/svg/RectangleUP.svg"
		/>
		<div class="change-useranme">2Factor Authentication</div>
	</div>
</div>
<div class="factor-authentication-parent">
	<div class="factor-authentication1">2Factor Authentication</div>
	<img class="qrcode" id="qrcode" src="" alt="qrcode" />
	<div class="username-wrapper">
		<input
			type="text"
			inputmode="numeric"
			maxlength="6"
			class="username-user"
			placeholder="6 Digit Code"
			oninput="this.value = this.value.replace(/[^0-9]/g, '').slice(0, 6)"
			id="digit"
		/>
	</div>
	<div class="sette-wrapper">
		<div class="change-username">Enable</div>
	</div>
</div>`;

export const DISTWOFA = `<div class="frame-wrapper">
<div class="rectangle-parent-user">
	<img
		class="rectangle-icon-user"
		alt=""
		src="/textures/svg/RectangleUP.svg"
	/>

	<div class="change-username">Disable 2FA</div>
</div>
</div>
<div class="send-invite-to-mel-moun-parent">
<div class="send-invite-to">Want to Disable 2FA?</div>
<div class="username-wrapper">
		<input
			type="text"
			inputmode="numeric"
			maxlength="6"
			class="username-user"
			placeholder="6 Digit Code"
			oninput="this.value = this.value.replace(/[^0-9]/g, '').slice(0, 6)"
			id="digit"
		/>
	</div>
<div class="sette-wrapper" id="yes">
	<div class="add-user">YES</div>
</div>
<div class="sette-wrapper" id="no">
	<div class="add-user">NO</div>
</div>
</div>`
