import * as THREE from 'three';

import { HOME, GAME, CHAT, LEADERBOARD } from './Home';
import { PANER } from './Paner';
import { SBOOK, SETTINGS } from './Settings';
import { MATCHESSCORE, USERSPROFILE } from './UsersProfile';
import {
	ALL_PLAYERS,
	BLOCKED,
	CHAT_INFO,
	ELEMENT,
	FRIENDS,
	MAINCHAT,
	PENDING,
	RECIVED,
	SECOND,
	SENT,
} from './Chat';
import { ADD, BLOCK, PLAY, REMOVE, UNBLOCK } from './ChatBtn';
import { LEGEND, LEGEND_CHAT, LEGEND_LEADERBOARD } from './Legend';
import { LEADERBOARDMAIN } from './Leaderboard';
import { SIGNIN, SIGNUP, TWOFASIGN } from './Sign';
import { LOGIN } from './Login';
import {
	CHANGE_AVATAR,
	CHANGE_EMAIL,
	CHANGE_FIRST_NAME,
	CHANGE_LAST_NAME,
	CHANGE_PASSWORD,
	CHANGE_USERNAME,
	DISTWOFA,
	REMOTE,
	TWOFA,
} from './Sbook';
import { CHOICES, MATCHMAKING, OFFLINE } from './Start';

import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { RGBELoader } from 'three/examples/jsm/loaders/RGBELoader.js';
import { TextGeometry } from 'three/addons/geometries/TextGeometry.js';
import { FontLoader } from 'three/addons/loaders/FontLoader.js';
import { TTFLoader } from 'three/addons/loaders/TTFLoader.js';
import {
	CSS2DRenderer,
	CSS2DObject,
} from 'three/addons/renderers/CSS2DRenderer.js';

class Game {
	#camera;
	#scene;
	#renderer;
	#controls;
	#mixer;
	#font;
	#ttf;
	#css2DRenderer;
	#css2DObject = {};
	#home;

	#ball;
	#player;
	#player2;
	#goalR;
	#goalL;
	#walls;
	#scoreLText;
	#scoreRText;
	#scoreL = 0;
	#scoreR = 0;

	#velocity = 5;
	#factor = 1;
	#ballDirection = new THREE.Vector3();
	#minDir = 0.69;
	#playerDirection = 0;
	#player2Direction = 0;
	#hasChanges = false;

	#ballBox = new THREE.Box3();
	#playerBox = new THREE.Box3();
	#player2Box = new THREE.Box3();
	#goalRBox = new THREE.Box3();
	#goalLBox = new THREE.Box3();
	#wallsBoxes = [];

	#lastFrameTime = 0;
	#frameRate = 60;

	#chatWebSocket = {};
	#chatuser;
	#gameWebSocket;
	#tournamentWebSocket;
	#currentMatch;
	#onlineSocket;
	#onlineUsers;

	#loggedUser;
	#enabled2fa = false;
	#isRemote = false;
	#selectedTab = 1;

	constructor() {
		this.#home = {
			home: HOME,
			game: GAME,
			chat: CHAT,
			leaderboard: LEADERBOARD,
		};
		this.#init();
	}

	#init() {
		this.#createScene();
		this.#createCamera();
		this.#createRenderer();
		this.#addDOMElem();
		// this.#createControls();
		this.#loadEnvironment();
		this.#loadFont();
		window.addEventListener('resize', () => this.#onWindowResize());
		this.#animate();
		this.#HomePage();
		this.#LoginPage();
	}

	#createScene() {
		this.#scene = new THREE.Scene();
	}

	#createCamera() {
		this.#camera = new THREE.PerspectiveCamera(
			75,
			window.innerWidth / window.innerHeight,
			0.5,
			1000
		);
		this.#camera.position.set(0, 15, 10);
		this.#camera.lookAt(new THREE.Vector3(0, 0, 0));
	}

	#createRenderer() {
		this.#renderer = new THREE.WebGLRenderer({ antialias: true });
		this.#renderer.setPixelRatio(window.devicePixelRatio);
		this.#renderer.setSize(window.innerWidth, window.innerHeight);
		this.#renderer.toneMapping = THREE.ACESFilmicToneMapping;
		this.#renderer.toneMappingExposure = 1;
		document.body.appendChild(this.#renderer.domElement);

		this.#css2DRenderer = new CSS2DRenderer();
		this.#css2DRenderer.setSize(window.innerWidth, window.innerHeight);
		document.body.appendChild(this.#css2DRenderer.domElement);
	}

	#addDOMElem() {
		this.#addLoginCss2D();
		this.#addSignInCss2D();
		this.#addSignUpCss2D();
		this.#addHomeCss2D();
		this.#addGameCss2D();
		this.#addOfflineCss2D();
		this.#addMatchmakingCss2D();
		this.#addPanerCss2D();
		this.#addSettingsCss2D();
		this.#addSbookSettingsCss2D();
		this.#addChatBtnCss2D();
		this.#addProfilePic();
		this.#addChatCss2D();
		this.#addLegendCss2d();
		this.#addLeaderboardCss2D();
		this.#addEventListeners();
	}

	#addEventListeners() {
		this.#css2DObject.sign.element
			.querySelector('.sign-in-text')
			.addEventListener('click', e => this.#switchSign('register'));
		this.#css2DObject.sign.element
			.querySelector('.login2')
			.addEventListener('click', e => this.#Login());
		this.#css2DObject.register.element
			.querySelector('.sign-in-text')
			.addEventListener('click', e => this.#switchSign('sign'));
		this.#css2DObject.register.element
			.querySelector('.login1')
			.addEventListener('click', e => this.#Register());
		this.#css2DObject.home.element.addEventListener('click', e => {
			const btn = e.target.closest('.square2');
			if (btn) this.#switchHome(btn.dataset.id);
		});
		this.#css2DObject.settings.element.addEventListener('click', () =>
			this.#toggleSBook()
		);
		this.#css2DObject.profilepic.element.addEventListener('click', () =>
			this.#toggleUsersProfile(this.#loggedUser)
		);
		this.#css2DObject.chat.element
			.querySelector('.vector-icon')
			.addEventListener('click', () => {
				this.#handelChatSent();
			});
		this.#css2DObject.chat.element
			.querySelector('.message')
			.addEventListener('keydown', e => {
				if (e.key === 'Enter') this.#handelChatSent();
			});
		this.#css2DObject.login.element.addEventListener('click', e => {
			const btn = e.target.closest('.btn-sign');
			if (btn) {
				this.#switchSign(btn.dataset.id);
			}
		});
		this.#css2DObject.signOverlay.element.addEventListener('click', e =>
			this.#toggleSign()
		);
		this.#css2DObject.upOverlay.element.addEventListener('click', e =>
			this.#toggleUsersProfile()
		);
		this.#css2DObject.sbOverlay.element.addEventListener('click', e =>
			this.#toggleSBook()
		);
		this.#css2DObject.sbsettingOverlay.element.addEventListener(
			'click',
			e => this.#toggleSettings()
		);
		['sign', 'register'].forEach(ele => {
			this.#css2DObject[ele].element
				.querySelector('.parent')
				.addEventListener('click', e => {
					const btn = e.target.closest('.icon');
					if (btn) {
						const go42 = {
							42: this.#login42,
							google: this.#loginGoogle,
						};
						go42[btn.dataset.id]();
					}
				});
		});
		this.#css2DObject.sbook.element
			.querySelector('.setting-frame-parent')
			.addEventListener('click', e => {
				const btn = e.target.closest('.setting-frame');
				if (btn) this.#sbookSettings(btn);
			});
		this.#css2DObject.chat.element
			.querySelector('.infos-chat')
			.addEventListener('click', e => {
				const btn = e.target.closest('.chat-btn');
				if (btn) {
					const user =
						this.#css2DObject.chat.element.querySelector(
							'.infos-chat'
						).dataset.user;
					this.#chatBtns(btn, user);
				}
			});
		this.#css2DObject.btnOverlay.element.addEventListener('click', e =>
			this.#toggleChatBtn()
		);
		this.#css2DObject.chat.element
			.querySelector('.all-players')
			.addEventListener('click', e => {
				const btn = e.target.closest('.radio-button-unchecked-icon');
				if (btn) this.#switchChatTab(btn.dataset.id);
			});
	}

	async #login42() {
		try {
			const backendLoginUrl = `api/auth/42/login/`;

			window.location.href = backendLoginUrl;
		} catch (error) {
			alert('Login initiation error:', error);
		}
	}

	async #loginGoogle() {
		try {
			const backendLoginUrl = `api/auth/google/`;

			window.location.href = backendLoginUrl;
		} catch (error) {
			alert('Login initiation error:', error);
		}
	}

	#changeUsername() {
		try {
			this.#css2DObject.sbsetting.element.innerHTML = CHANGE_USERNAME;
			['sbsetting', 'sbsettingOverlay'].forEach(ele => {
				this.#scene.add(this.#css2DObject[ele]);
			});
			this.#css2DObject.sbsetting.element
				.querySelector('.sette-wrapper')
				.addEventListener('click', async e => {
					const username =
						this.#css2DObject.sbsetting.element.querySelector(
							'.username-user'
						).value;

					const response = await fetch(`api/update-infos/`, {
						method: 'POST',
						headers: {
							'Content-Type': 'application/json',
							Authorization: `Bearer ${localStorage.getItem(
								'accessToken'
							)}`,
						},
						body: JSON.stringify({
							tournament_username: username,
						}),
					});
					const data = await response.json();
					if (response.ok) {
						this.#toggleSettings();
						this.#switchHome(window.location.pathname.slice(1));
					} else {
						const errorMessage =
							Object.values(data).flat().join(', ') ||
							'An error occurred. Please try again.';
						alert('Error updating password: ' + errorMessage);
						this.#css2DObject.sbsetting.element.querySelector(
							'.username-user'
						).value = '';
					}
				});
		} catch (error) {
			alert(error);
		}
	}

	#changePassword() {
		try {
			this.#css2DObject.sbsetting.element.innerHTML = CHANGE_PASSWORD;
			['sbsetting', 'sbsettingOverlay'].forEach(ele => {
				this.#scene.add(this.#css2DObject[ele]);
			});

			this.#css2DObject.sbsetting.element
				.querySelector('.sette-wrapper')
				.addEventListener('click', async e => {
					const oldpass =
						this.#css2DObject.sbsetting.element.querySelector(
							'#oldpass'
						).value;
					const newpass =
						this.#css2DObject.sbsetting.element.querySelector(
							'#newpass'
						).value;
					const confpass =
						this.#css2DObject.sbsetting.element.querySelector(
							'#confpass'
						).value;

					if (newpass !== confpass) {
						this.#css2DObject.sbsetting.element.querySelector(
							'#newpass'
						).value = '';
						this.#css2DObject.sbsetting.element.querySelector(
							'#confpass'
						).value = '';
						alert("Passwords don't match");
						return;
					}

					const response = await fetch(`api/update-password/`, {
						method: 'POST',
						headers: {
							'Content-Type': 'application/json',
							Authorization: `Bearer ${localStorage.getItem(
								'accessToken'
							)}`,
						},
						body: JSON.stringify({
							old_password: oldpass,
							new_password: newpass,
						}),
					});

					const data = await response.json();

					if (response.ok) {
						this.#toggleSettings();
					} else {
						this.#css2DObject.sbsetting.element.querySelector(
							'#oldpass'
						).value = '';
						this.#css2DObject.sbsetting.element.querySelector(
							'#newpass'
						).value = '';
						this.#css2DObject.sbsetting.element.querySelector(
							'#confpass'
						).value = '';
						const errorMessage =
							Object.values(data).flat().join(', ') ||
							'An error occurred. Please try again.';
						alert('Error updating password: ' + errorMessage);
					}
				});
		} catch (error) {
			alert('An unexpected error occurred: ' + error.message);
		}
	}

	#changeFirstName() {
		try {
			this.#css2DObject.sbsetting.element.innerHTML = CHANGE_FIRST_NAME;
			['sbsetting', 'sbsettingOverlay'].forEach(ele => {
				this.#scene.add(this.#css2DObject[ele]);
			});
			this.#css2DObject.sbsetting.element
				.querySelector('.sette-wrapper')
				.addEventListener('click', async e => {
					const first =
						this.#css2DObject.sbsetting.element.querySelector(
							'.username-user'
						).value;

					const response = await fetch(`api/update-infos/`, {
						method: 'POST',
						headers: {
							'Content-Type': 'application/json',
							Authorization: `Bearer ${localStorage.getItem(
								'accessToken'
							)}`,
						},
						body: JSON.stringify({
							first_name: first,
						}),
					});
					const data = await response.json();
					if (response.ok) {
						this.#toggleSettings();
					} else {
						alert('Error updating First Name: ' + data.message);
						this.#css2DObject.sbsetting.element.querySelector(
							'.username-user'
						).value = '';
					}
				});
		} catch (error) {
			alert(error);
		}
	}

	#changeLastName() {
		try {
			this.#css2DObject.sbsetting.element.innerHTML = CHANGE_LAST_NAME;
			['sbsetting', 'sbsettingOverlay'].forEach(ele => {
				this.#scene.add(this.#css2DObject[ele]);
			});
			this.#css2DObject.sbsetting.element
				.querySelector('.sette-wrapper')
				.addEventListener('click', async e => {
					const last =
						this.#css2DObject.sbsetting.element.querySelector(
							'.username-user'
						).value;

					const response = await fetch(`api/update-infos/`, {
						method: 'POST',
						headers: {
							'Content-Type': 'application/json',
							Authorization: `Bearer ${localStorage.getItem(
								'accessToken'
							)}`,
						},
						body: JSON.stringify({
							last_name: last,
						}),
					});

					const data = await response.json();

					if (response.ok) {
						this.#toggleSettings();
					} else {
						alert(
							'Error updating Last Name: ' +
								(data.message || 'Unknown error occurred.')
						);
					}
				});
		} catch (error) {
			alert('Error: ' + error.message);
		}
	}

	async #changeEmail() {
		try {
			this.#css2DObject.sbsetting.element.innerHTML = CHANGE_EMAIL;
			['sbsetting', 'sbsettingOverlay'].forEach(ele => {
				this.#scene.add(this.#css2DObject[ele]);
			});

			const emailInput =
				this.#css2DObject.sbsetting.element.querySelector(
					'.username-user'
				);
			const submitButton =
				this.#css2DObject.sbsetting.element.querySelector(
					'.sette-wrapper'
				);

			emailInput.value = '';

			submitButton.addEventListener('click', async e => {
				const email = emailInput.value;

				const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
				if (!emailPattern.test(email)) {
					alert('Please enter a valid email address.');
					return;
				}

				try {
					const response = await fetch(`api/update-infos/`, {
						method: 'POST',
						headers: {
							'Content-Type': 'application/json',
							Authorization: `Bearer ${localStorage.getItem(
								'accessToken'
							)}`,
						},
						body: JSON.stringify({ email: email }),
					});

					const data = await response.json();

					if (response.ok) {
						this.#toggleSettings();
					} else {
						const errorMessage =
							Object.values(data).flat().join(', ') ||
							'An error occurred. Please try again.';
						alert('Error updating email: ' + errorMessage);
					}
				} catch (error) {
					alert('Network error: ' + fetchError.message);
				}
			});
		} catch (error) {
			alert('Error: ' + error.message);
		}
	}

	#changeAvatar() {
		this.#css2DObject.sbsetting.element.innerHTML = CHANGE_AVATAR;
		['sbsetting', 'sbsettingOverlay'].forEach(ele => {
			this.#scene.add(this.#css2DObject[ele]);
		});

		this.#css2DObject.sbsetting.element
			.querySelector('.sette-wrapper')
			.addEventListener('click', async e => {
				const fileInput =
					this.#css2DObject.sbsetting.element.querySelector(
						'#avatarUpload'
					);
				const file = fileInput.files[0];
				if (file) {
					const formData = new FormData();
					formData.append('avatar', file);

					try {
						const response = await fetch(`api/avatar/`, {
							method: 'POST',
							headers: {
								Authorization: `Bearer ${localStorage.getItem(
									'accessToken'
								)}`,
							},
							body: formData,
						});

						if (!response.ok) {
							throw new Error('Network response was not ok');
						}
						const data = await response.json();
						this.#css2DObject.profilepic.element.src = data.avatar;
						this.#toggleSettings();
					} catch (error) {
						alert('Failed to upload avatar. Please try again.');
					}
				} else {
					alert('Please select an image to upload.');
				}
			});

		this.#css2DObject.sbsetting.element
			.querySelector('#avatarImage')
			.addEventListener('click', e =>
				this.#css2DObject.sbsetting.element
					.querySelector('#avatarUpload')
					.click()
			);
		this.#css2DObject.sbsetting.element
			.querySelector('#avatarUpload')
			.addEventListener('change', e => {
				const file = e.target.files[0];
				if (file) {
					const reader = new FileReader();
					reader.onload = e => {
						this.#css2DObject.sbsetting.element.querySelector(
							'#avatarImage'
						).src = e.target.result;
					};
					reader.readAsDataURL(file);
				}
			});
	}

	async #handleTwoFA(twofa) {
		try {
			const tfa = this.#css2DObject.sbsetting.element;

			['sbsetting', 'sbsettingOverlay'].forEach(ele => {
				this.#scene.add(this.#css2DObject[ele]);
			});
			if (this.#isRemote) {
				this.#css2DObject.sbsetting.element.innerHTML = REMOTE;
			} else {
				if (!this.#enabled2fa) {
					this.#css2DObject.sbsetting.element.innerHTML = TWOFA;
					const response = await fetch(`api/enable-2fa/`, {
						method: 'POST',
						headers: {
							'Content-Type': 'application/json',
							Authorization: `Bearer ${localStorage.getItem(
								'accessToken'
							)}`,
						},
					});

					const data = await response.json();
					if (response.ok) {
						tfa.querySelector('#qrcode').src = data.qr_code;
						tfa.querySelector('.sette-wrapper').addEventListener(
							'click',
							async e => {
								const degit = tfa.querySelector('#digit').value;
								const response = await fetch(
									`api/confirm-2fa/`,
									{
										method: 'POST',
										headers: {
											'Content-Type': 'application/json',
											Authorization: `Bearer ${localStorage.getItem(
												'accessToken'
											)}`,
										},
										body: JSON.stringify({ otp: degit }),
									}
								);
								const otpdata = await response.json();
								if (response.ok) {
									this.#enabled2fa = true;
									twofa.querySelector(
										'.fa-icon1'
									).src = `/textures/svg/2FA ON.svg`;
									twofa
										.querySelector('.factor-authentication')
										.classList.remove(
											'factor-authentication-op'
										);
									this.#toggleSettings();
								} else {
									alert(
										`otp: ${Object.values(otpdata)
											.flat()
											.join(', ')}`
									);
								}
							}
						);
					} else {
						alert(`otp: ${Object.values(data).flat().join(', ')}`);
					}
				} else {
					this.#css2DObject.sbsetting.element.innerHTML = DISTWOFA;
					tfa.querySelector('#yes').addEventListener(
						'click',
						async e => {
							const otp = tfa.querySelector('#digit').value;
							const response = await fetch(`api/disable-2fa/`, {
								method: 'POST',
								headers: {
									'Content-Type': 'application/json',
									Authorization: `Bearer ${localStorage.getItem(
										'accessToken'
									)}`,
								},
								body: JSON.stringify({ otp: otp }),
							});

							const data = await response.json();
							if (response.ok) {
								this.#enabled2fa = false;
								twofa.querySelector(
									'.fa-icon1'
								).src = `/textures/svg/2FA OFF.svg`;
								twofa
									.querySelector('.factor-authentication')
									.classList.add('factor-authentication-op');
								this.#toggleSettings();
							} else {
								alert(
									`otp: ${Object.values(data)
										.flat()
										.join(', ')}`
								);
							}
						}
					);
					tfa.querySelector('#no').addEventListener(
						'click',
						async e => {
							this.#toggleSettings();
						}
					);
				}
			}
		} catch (error) {
			alert(error);
		}
	}

	async #logout() {
		try {
			const response = await fetch(`api/logout/`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					Authorization: `Bearer ${localStorage.getItem(
						'accessToken'
					)}`,
				},
				body: JSON.stringify({
					refresh: localStorage.getItem('refreshToken'),
				}),
			});

			if (response.ok) {
				const twofa = this.#css2DObject.sbook.element;

				this.#enabled2fa = false;
				this.#isRemote = false;
				this.#selectedTab = 1;
				localStorage.removeItem('accessToken');
				localStorage.removeItem('refreshToken');

				this.#switchHome('home');
				this.#toggleSBook();
				twofa.querySelector(
					'.fa-icon1'
				).src = `/textures/svg/2FA OFF.svg`;
				twofa
					.querySelector('.factor-authentication')
					.classList.add('factor-authentication-op');
				this.#LoginPage();
			} else {
				const errorData = await response.json();
				throw new Error(errorData.detail || 'Logout failed');
			}
		} catch (error) {
			alert(error);
		}
	}

	#sbookSettings(btn) {
		const setting = {
			username: this.#changeUsername.bind(this),
			password: this.#changePassword.bind(this),
			first: this.#changeFirstName.bind(this),
			last: this.#changeLastName.bind(this),
			email: this.#changeEmail.bind(this),
			avatar: this.#changeAvatar.bind(this),
			twofa: this.#handleTwoFA.bind(this, btn),
			logout: this.#logout.bind(this),
		};
		setting[btn.dataset.id]();
	}

	async #addUser(user) {
		try {
			this.#css2DObject.chatBtn.element.innerHTML = ADD;
			this.#css2DObject.chatBtn.element.querySelector(
				'.send-invite-to'
			).textContent = `Send Invite to ${user} ?`;

			['chatBtn', 'btnOverlay'].forEach(ele => {
				this.#scene.add(this.#css2DObject[ele]);
			});

			const noButton =
				this.#css2DObject.chatBtn.element.querySelector('#no');
			const yesButton =
				this.#css2DObject.chatBtn.element.querySelector('#yes');

			noButton.addEventListener('click', () => {
				this.#toggleChatBtn();
			});

			yesButton.addEventListener('click', async () => {
				const response = await fetch(
					`api/manage/friendship/add/${user}/`,
					{
						method: 'POST',
						headers: {
							'Content-Type': 'application/json',
							Authorization: `Bearer ${localStorage.getItem(
								'accessToken'
							)}`,
						},
					}
				);

				const data = await response.json();
				if (response.ok) {
					this.#toggleChatBtn();
					this.#switchChatTab(this.#selectedTab);
				} else {
					alert(
						`Error declining friend request: ${Object.values(data)
							.flat()
							.join(', ')}`
					);
				}
			});
		} catch (error) {
			alert('Error adding user:', error);
		}
	}

	async #removeUser(user) {
		try {
			this.#css2DObject.chatBtn.element.innerHTML = REMOVE;
			this.#css2DObject.chatBtn.element.querySelector(
				'.send-invite-to'
			).textContent = `Remove ${user} from friends?`;

			['chatBtn', 'btnOverlay'].forEach(ele => {
				this.#scene.add(this.#css2DObject[ele]);
			});

			const noButton =
				this.#css2DObject.chatBtn.element.querySelector('#no');
			const yesButton =
				this.#css2DObject.chatBtn.element.querySelector('#yes');

			noButton.addEventListener('click', () => {
				this.#toggleChatBtn();
			});

			yesButton.addEventListener('click', async () => {
				const response = await fetch(
					`api/manage/friendship/remove/${user}/`,
					{
						method: 'POST',
						headers: {
							'Content-Type': 'application/json',
							Authorization: `Bearer ${localStorage.getItem(
								'accessToken'
							)}`,
						},
					}
				);
				const data = await response.json();
				if (response.ok) {
					this.#toggleChatBtn();
					this.#switchChatTab(2);
				} else {
					alert(
						`Error declining friend request: ${Object.values(data)
							.flat()
							.join(', ')}`
					);
				}
			});
		} catch (error) {
			alert('Error removing user:', error);
		}
	}

	async #playUser(user) {
		this.#css2DObject.chatBtn.element.innerHTML = PLAY;
		this.#css2DObject.chatBtn.element.querySelector(
			'.select-new-username'
		).textContent = `Start a Game With ${user}`;
		['chatBtn', 'btnOverlay'].forEach(ele => {
			this.#scene.add(this.#css2DObject[ele]);
		});
	}

	async #blockUser(user) {
		try {
			this.#css2DObject.chatBtn.element.innerHTML = BLOCK;
			this.#css2DObject.chatBtn.element.querySelector(
				'.send-invite-to'
			).textContent = `Block ${user}?`;

			['chatBtn', 'btnOverlay'].forEach(ele => {
				this.#scene.add(this.#css2DObject[ele]);
			});

			const noButton =
				this.#css2DObject.chatBtn.element.querySelector('#no');
			const yesButton =
				this.#css2DObject.chatBtn.element.querySelector('#yes');

			noButton.addEventListener('click', () => {
				this.#toggleChatBtn();
			});

			yesButton.addEventListener('click', async () => {
				const response = await fetch(
					`api/manage/friendship/block/${user}/`,
					{
						method: 'POST',
						headers: {
							'Content-Type': 'application/json',
							Authorization: `Bearer ${localStorage.getItem(
								'accessToken'
							)}`,
						},
					}
				);

				const data = await response.json();
				if (response.ok) {
					this.#toggleChatBtn();
					this.#switchChatTab(this.#selectedTab);
				} else {
					alert(
						`Error declining friend request: ${Object.values(data)
							.flat()
							.join(', ')}`
					);
				}
			});
		} catch (error) {
			alert('Error blocking user:', error);
		}
	}

	async #acceptUser(user) {
		try {
			const response = await fetch(
				`api/manage/friendship/accept/${user}/`,
				{
					method: 'POST',
					headers: {
						'Content-Type': 'application/json',
						Authorization: `Bearer ${localStorage.getItem(
							'accessToken'
						)}`,
					},
				}
			);

			const data = await response.json();
			if (response.ok) {
				this.#switchChatTab(3);
			} else {
				alert(
					`Error declining friend request: ${Object.values(data)
						.flat()
						.join(', ')}`
				);
			}
		} catch (error) {
			alert('Error accepting friend request:', error);
		}
	}

	async #declineUser(user) {
		try {
			const response = await fetch(
				`api/manage/friendship/decline/${user}/`,
				{
					method: 'POST',
					headers: {
						'Content-Type': 'application/json',
						Authorization: `Bearer ${localStorage.getItem(
							'accessToken'
						)}`,
					},
				}
			);

			const data = await response.json();
			if (response.ok) {
				this.#switchChatTab(3);
			} else {
				alert(
					`Error declining friend request: ${Object.values(data)
						.flat()
						.join(', ')}`
				);
			}
		} catch (error) {
			alert('Error declining friend request:', error);
		}
	}

	async #unblockUser(user) {
		try {
			this.#css2DObject.chatBtn.element.innerHTML = UNBLOCK;
			this.#css2DObject.chatBtn.element.querySelector(
				'.send-invite-to'
			).textContent = `Unblock ${user}?`;

			['chatBtn', 'btnOverlay'].forEach(ele => {
				this.#scene.add(this.#css2DObject[ele]);
			});

			const noButton =
				this.#css2DObject.chatBtn.element.querySelector('#no');
			const yesButton =
				this.#css2DObject.chatBtn.element.querySelector('#yes');

			noButton.addEventListener('click', () => {
				this.#toggleChatBtn();
			});

			yesButton.addEventListener('click', async () => {
				const response = await fetch(
					`api/manage/friendship/unblock/${user}/`,
					{
						method: 'POST',
						headers: {
							'Content-Type': 'application/json',
							Authorization: `Bearer ${localStorage.getItem(
								'accessToken'
							)}`,
						},
					}
				);
				const data = await response.json();
				if (response.ok) {
					this.#toggleChatBtn();
					this.#switchChatTab(4);
				} else {
					alert(
						`Error declining friend request: ${Object.values(data)
							.flat()
							.join(', ')}`
					);
				}
			});
		} catch (error) {
			alert('Error unblocking user:', error);
		}
	}

	#chatBtns(btn, user) {
		const usr = {
			profile: this.#toggleUsersProfile.bind(this, user),
			add: this.#addUser.bind(this, user),
			play: this.#playUser.bind(this, user),
			block: this.#blockUser.bind(this, user),
			remove: this.#removeUser.bind(this, user),
			unblock: this.#unblockUser.bind(this, user),
		};
		usr[btn.dataset.id]();
	}

	#addLoginCss2D() {
		const loginContainer = document.createElement('div');
		loginContainer.className = 'sign-inup';
		loginContainer.innerHTML = LOGIN;

		this.#css2DObject.login = new CSS2DObject(loginContainer);
		this.#css2DObject.login.name = 'login';

		const overlayContainer = document.createElement('div');
		overlayContainer.className = 'overlay';

		this.#css2DObject.signOverlay = new CSS2DObject(overlayContainer);
		this.#css2DObject.signOverlay.name = 'overlay';
	}

	#switchSign(sign) {
		this.#toggleSign();
		[sign, 'signOverlay'].forEach(ele => {
			this.#scene.add(this.#css2DObject[ele]);
		});
	}

	#toggleSign() {
		['sign', 'register', 'signOverlay', 'valid'].forEach(ele => {
			this.#scene.remove(this.#css2DObject[ele]);
		});
	}

	#addSignInCss2D() {
		const signContainer = document.createElement('div');
		signContainer.className = 'login';
		signContainer.innerHTML = SIGNIN;

		this.#css2DObject.sign = new CSS2DObject(signContainer);
		this.#css2DObject.sign.name = 'sign in';

		const validContainer = document.createElement('div');
		validContainer.className = 'login';
		validContainer.innerHTML = TWOFASIGN;

		this.#css2DObject.valid = new CSS2DObject(validContainer);
		this.#css2DObject.valid.name = 'valid';
		this.#css2DObject.valid.renderOrder = 10;
	}

	#addSignUpCss2D() {
		const registerContainer = document.createElement('div');
		registerContainer.className = 'register';
		registerContainer.innerHTML = SIGNUP;

		this.#css2DObject.register = new CSS2DObject(registerContainer);
		this.#css2DObject.register.name = 'sign up';
	}

	#addHomeCss2D() {
		const homeContainer = document.createElement('div');
		homeContainer.className = 'home';
		homeContainer.innerHTML = HOME;

		this.#css2DObject.home = new CSS2DObject(homeContainer);
		this.#css2DObject.home.name = 'home';
		this.#css2DObject.home.renderOrder = 1;
	}

	#addGameCss2D() {
		const homeContainer = document.createElement('div');
		homeContainer.className = 'container';
		homeContainer.innerHTML = CHOICES;

		this.#css2DObject.game = new CSS2DObject(homeContainer);
		this.#css2DObject.game.name = 'game';
	}

	#addOfflineCss2D() {
		const homeContainer = document.createElement('div');
		homeContainer.className = 'container';
		homeContainer.innerHTML = OFFLINE;

		this.#css2DObject.offline = new CSS2DObject(homeContainer);
		this.#css2DObject.offline.name = 'offline';
	}

	#addMatchmakingCss2D() {
		const homeContainer = document.createElement('div');
		homeContainer.className = 'container-match';
		homeContainer.innerHTML = MATCHMAKING;

		this.#css2DObject.match = new CSS2DObject(homeContainer);
		this.#css2DObject.match.name = 'match';
	}

	#addLegendCss2d() {
		const legendContainer = document.createElement('div');
		legendContainer.className = 'legend';
		legendContainer.innerHTML = LEGEND;

		this.#css2DObject.legend = new CSS2DObject(legendContainer);
		this.#css2DObject.legend.name = 'legend';
		this.#css2DObject.legend.renderOrder = 1;
	}

	#addPanerCss2D() {
		const panerContainer = document.createElement('div');
		panerContainer.className = 'paner';
		panerContainer.innerHTML = PANER;

		this.#css2DObject.paner = new CSS2DObject(panerContainer);
		this.#css2DObject.paner.name = 'paner';
		this.#css2DObject.paner.renderOrder = 2;
	}

	#addSettingsCss2D() {
		const settingsContainer = document.createElement('div');
		settingsContainer.className = 'settings';
		settingsContainer.innerHTML = SETTINGS;

		this.#css2DObject.settings = new CSS2DObject(settingsContainer);
		this.#css2DObject.settings.name = 'settings';
		this.#css2DObject.settings.renderOrder = 3;

		const sbookContainer = document.createElement('div');
		sbookContainer.className = 'sbook-1';
		sbookContainer.innerHTML = SBOOK;

		this.#css2DObject.sbook = new CSS2DObject(sbookContainer);
		this.#css2DObject.sbook.name = 'sbook';
		this.#css2DObject.sbook.renderOrder = 8;

		const overlayContainer = document.createElement('div');
		overlayContainer.className = 'overlay';

		this.#css2DObject.sbOverlay = new CSS2DObject(overlayContainer);
		this.#css2DObject.sbOverlay.name = 'overlay';
		this.#css2DObject.sbOverlay.renderOrder = 7;
	}

	#addSbookSettingsCss2D() {
		const usernameContainer = document.createElement('div');
		usernameContainer.className = 'frame-parent-user';
		usernameContainer.innerHTML = CHANGE_USERNAME;

		this.#css2DObject.sbsetting = new CSS2DObject(usernameContainer);
		this.#css2DObject.sbsetting.name = 'change user';
		this.#css2DObject.sbsetting.renderOrder = 10;

		const overlayContainer = document.createElement('div');
		overlayContainer.className = 'overlay';

		this.#css2DObject.sbsettingOverlay = new CSS2DObject(overlayContainer);
		this.#css2DObject.sbsettingOverlay.name = 'overlay';
		this.#css2DObject.sbsettingOverlay.renderOrder = 9;
	}

	#addChatBtnCss2D() {
		const btnContainer = document.createElement('div');
		btnContainer.className = 'frame-parent-user';
		btnContainer.innerHTML = BLOCK;

		this.#css2DObject.chatBtn = new CSS2DObject(btnContainer);
		this.#css2DObject.chatBtn.name = 'block';
		this.#css2DObject.chatBtn.renderOrder = 10;

		const overlayContainer = document.createElement('div');
		overlayContainer.className = 'overlay';

		this.#css2DObject.btnOverlay = new CSS2DObject(overlayContainer);
		this.#css2DObject.btnOverlay.name = 'overlay';
		this.#css2DObject.btnOverlay.renderOrder = 9;
	}

	#toggleChatBtn() {
		['chatBtn', 'btnOverlay'].forEach(ele => {
			this.#scene.remove(this.#css2DObject[ele]);
		});
	}

	#toggleSettings() {
		['sbsetting', 'sbsettingOverlay'].forEach(ele => {
			this.#scene.remove(this.#css2DObject[ele]);
		});
	}

	#toggleSBook() {
		if (this.#scene.getObjectByName('sbook')) {
			this.#scene.remove(this.#css2DObject.sbook);
			this.#scene.remove(this.#css2DObject.sbOverlay);
			return;
		}
		this.#scene.add(this.#css2DObject.sbook);
		this.#scene.add(this.#css2DObject.sbOverlay);
	}

	#addProfilePic() {
		const ppContainer = document.createElement('img');
		ppContainer.className = 'profile-pic-icon';
		ppContainer.alt = '';
		ppContainer.id = 'profilePicImage';

		this.#css2DObject.profilepic = new CSS2DObject(ppContainer);
		this.#css2DObject.profilepic.name = 'profilepic';
		this.#css2DObject.profilepic.renderOrder = 4;

		const usersProfileContainer = document.createElement('div');
		usersProfileContainer.className = 'users-profile';
		usersProfileContainer.innerHTML = USERSPROFILE;

		this.#css2DObject.usersprofile = new CSS2DObject(usersProfileContainer);
		this.#css2DObject.usersprofile.name = 'usersprofile';
		this.#css2DObject.usersprofile.renderOrder = 6;

		const overlayContainer = document.createElement('div');
		overlayContainer.className = 'overlay';

		this.#css2DObject.upOverlay = new CSS2DObject(overlayContainer);
		this.#css2DObject.upOverlay.name = 'overlay';
		this.#css2DObject.upOverlay.renderOrder = 5;
	}

	#loadAccepted(data) {
		this.#addChatUsers(data.accepted);
		const userElem =
			this.#css2DObject.chat.element.querySelectorAll('.element');
		userElem.forEach(user => {
			user.querySelector('.indicator-icon1').id = 'remove';
			user.querySelector('.indicator-icon1').src =
				'/textures/svg/delete.svg';
			const username =
				user.querySelector('.sword-prowess-lv').textContent;
			user.querySelector('#remove').addEventListener('click', e => {
				this.#removeUser(username);
			});
		});
	}

	#loadPending(data) {
		this.#addChatUsers(data.pending);
		const userElem =
			this.#css2DObject.chat.element.querySelectorAll('.element');
		userElem.forEach(user => {
			user.querySelector('.indicator-icon1').id = 'accepte';
			user.querySelector('.indicator-icon1').src =
				'/textures/svg/check.svg';
			const img = document.createElement('img');
			img.innerHTML = SECOND.trim();
			img.firstChild.src = '/textures/svg/close.svg';
			img.firstChild.id = 'decline';
			user.appendChild(img.firstChild);
			const username =
				user.querySelector('.sword-prowess-lv').textContent;

			user.querySelector('#accepte').addEventListener('click', e => {
				this.#acceptUser(username);
			});
			user.querySelector('#decline').addEventListener('click', e => {
				this.#declineUser(username);
			});
		});
	}

	#loadBlocked(data) {
		this.#addChatUsers(data.blocked);
		const userElem =
			this.#css2DObject.chat.element.querySelectorAll('.element');
		userElem.forEach(user => {
			user.querySelector('.indicator-icon1').id = 'unblock';
			user.querySelector('.indicator-icon1').src =
				'/textures/svg/unblock.svg';
			const username =
				user.querySelector('.sword-prowess-lv').textContent;
			user.querySelector('#unblock').addEventListener('click', e => {
				this.#unblockUser(username);
			});
		});
	}

	async #switchChatTab(btn) {
		try {
			this.#css2DObject.chat.element.querySelector(
				'.infos-chat'
			).innerHTML = '';
			this.#css2DObject.chat.element.querySelector(
				'.recived-parent'
			).innerHTML = '';
			this.#chatuser = undefined;
			const id = {
				1: ALL_PLAYERS,
				2: FRIENDS,
				3: PENDING,
				4: BLOCKED,
			};
			this.#css2DObject.chat.element.querySelector(
				'.all-players'
			).innerHTML = id[btn];
			this.#selectedTab = btn;
			const response = await fetch(`api/manage/friendship/`, {
				method: 'GET',
				headers: {
					'Content-Type': 'application/json',
					Authorization: `Bearer ${localStorage.getItem(
						'accessToken'
					)}`,
				},
			});
			const data = await response.json();
			if (response.ok) {
				const stat = {
					1: this.#chatUsers.bind(this),
					2: this.#loadAccepted.bind(this, data),
					3: this.#loadPending.bind(this, data),
					4: this.#loadBlocked.bind(this, data),
				};

				stat[btn]();
			}
		} catch (error) {
			alert(error);
		}
	}

	async #loadChat(user, userData) {
		try {
			this.#chatWebSocket[user].elem
				.querySelector('#message')
				?.removeAttribute('src');

			const template = document.createElement('template');
			template.innerHTML = CHAT_INFO.trim();

			const info = template.content.firstChild;
			info.querySelector('.frame-item').src = userData.avatar;
			info.querySelector('.indicator-icon12').src =
				this.#chatWebSocket[user].elem.querySelector(
					'.indicator-icon'
				).src;
			info.querySelector(
				'.meriem-el-mountasser'
			).textContent = `${userData.first.trim()} ${userData.last.trim()}`;

			const chatInfoElement =
				this.#css2DObject.chat.element.querySelector('.infos-chat');

			chatInfoElement.innerHTML = '';
			this.#css2DObject.chat.element.querySelector(
				'.infos-chat'
			).dataset.user = user;

			chatInfoElement.appendChild(info);

			const recived =
				this.#css2DObject.chat.element.querySelector('.recived-parent');
			recived.innerHTML = '';

			const response = await fetch(
				`api/chat/room/${this.#loggedUser}/${user}/`,
				{
					method: 'GET',
					headers: {
						Authorization: `Bearer ${localStorage.getItem(
							'accessToken'
						)}`,
					},
				}
			);
			const data = await response.json();
			if (response.ok) {
				data.messages.forEach(message => {
					if (message.sender === user)
						this.#addRecivedMessage(message.content);
					else this.#addSentMessage(message.content);
					const lastMessage = recived.lastChild;
					lastMessage.scrollIntoView({ behavior: 'auto' });
				});
			}
			this.#chatuser = user;
		} catch (error) {
			alert(error);
		}
	}

	#addChatUsers(users) {
		for (const key in this.#chatWebSocket)
			this.#chatWebSocket[key].sock.close();
		this.#css2DObject.chat.element.querySelector(
			'.element-parent'
		).innerHTML = '';
		users.forEach(user => {
			if (user.username !== this.#loggedUser) {
				const src = this.#onlineUsers.includes(user.username)
					? `/textures/svg/Indicator online.svg`
					: `/textures/svg/Indicator offline.svg`;
				const userTemp = document.createElement('template');
				userTemp.innerHTML = ELEMENT.trim();

				const userHTML = userTemp.content.firstChild;
				userHTML.querySelector('.element-child').src = user.avatar;
				userHTML.querySelector('.sword-prowess-lv').textContent =
					user.username;
				userHTML.querySelector('.indicator-icon').src = src;
				this.#css2DObject.chat.element
					.querySelector('.element-parent')
					.appendChild(userHTML);

				userHTML.addEventListener('click', e => {
					if (!e.target.classList.contains('skip')) {
						const data = e.target
							.closest('.element')
							.querySelector('.sword-prowess-lv').textContent;
						if (data) this.#loadChat(data, user);
					}
				});

				const room = [this.#loggedUser, user.username].sort().join('_');
				this.#chatWebSocket[user.username] = {};
				this.#chatWebSocket[user.username].elem = userHTML;
				this.#chatWebSocket[user.username].sock = new WebSocket(
					`wss://${window.location.host}/api/ws/chat/${room}/`
				);
				this.#chatWebSocket[user.username].sock.onmessage = e => {
					const data = JSON.parse(e.data);
					if (data.error) {
						return;
					}
					if (user.username === this.#chatuser) {
						if (data.sender === user.username)
							this.#addRecivedMessage(data.message);
						else this.#addSentMessage(data.message);
						const chatContainer =
							this.#css2DObject.chat.element.querySelector(
								'.recived-parent'
							);
						const lastMessage = chatContainer.lastChild;
						lastMessage.scrollIntoView({ behavior: 'smooth' });
					} else {
						this.#chatWebSocket[user.username].elem.querySelector(
							'#message'
						).src = `/textures/svg/Indicator message.svg`;
					}
				};
			}
		});
	}

	async #chatUsers() {
		try {
			this.#css2DObject.chat.element.querySelector(
				'.mel-moun'
			).textContent = this.#loggedUser;
			const response = await fetch(`api/users/`, {
				method: 'GET',
				headers: {
					Authorization: `Bearer ${localStorage.getItem(
						'accessToken'
					)}`,
				},
			});
			const data = await response.json();
			if (response.ok) {
				this.#addChatUsers(data.users);
			}
		} catch (error) {
			alert(error);
		}
	}

	#setMatchHistory(matches) {
		this.#css2DObject.usersprofile.element.querySelector(
			'.matches-score-parent'
		).innerHTML = '';
		matches.slice(-10).forEach(match => {
			const matchTemp = document.createElement('template');
			matchTemp.innerHTML = MATCHESSCORE.trim();
			const matchHTML = matchTemp.content.firstChild;

			const time = new Date(match.date_played);
			matchHTML.dataset.tooltip = `${time.toLocaleString()}`;

			matchHTML.querySelector('.user-2').textContent = match.player1;
			matchHTML.querySelector('.user-1').textContent = match.player2;
			matchHTML.querySelector('#score1').textContent =
				match.score_player1;
			matchHTML.querySelector('#score2').textContent =
				match.score_player2;
			matchHTML.querySelector('#avatar1').src = match.player1_avatar;
			matchHTML.querySelector('#avatar2').src = match.player2_avatar;

			this.#css2DObject.usersprofile.element
				.querySelector('.matches-score-parent')
				.appendChild(matchHTML);
		});
	}

	#setUserProfileFields(data) {
		const profile = this.#css2DObject.usersprofile.element;
		const gender = { F: 'Female', M: 'Male', null: '__' };

		profile.querySelector('.frame-icon').src = data.avatar;
		profile.querySelector('#first').textContent = data.first_name;
		profile.querySelector('#last').textContent = data.last_name;
		profile.querySelector('#username').textContent = data.username;
		profile.querySelector('#gender').textContent = gender[data.gender];
		profile.querySelector('#t_games').textContent = data.t_games;
		profile.querySelector('#wins').textContent = data.wins;
		profile.querySelector('#losses').textContent = data.losses;
		profile.querySelector('#t_points').textContent = data.t_points;
		profile.querySelector('#goals_f').textContent = data.goals_f;
		profile.querySelector('#goals_a').textContent = data.goals_a;
	}

	async #loadUserProfile(user) {
		try {
			const response = await fetch(`api/user/${user}`, {
				method: 'GET',
				headers: {
					Authorization: `Bearer ${localStorage.getItem(
						'accessToken'
					)}`,
				},
			});
			const data = await response.json();
			if (response.ok) {
				this.#setUserProfileFields(data);
				this.#setMatchHistory(data.matches);
			}
		} catch (error) {
			alert(error);
		}
	}

	#toggleUsersProfile(user) {
		if (this.#scene.getObjectByName('usersprofile')) {
			this.#scene.remove(this.#css2DObject.usersprofile);
			this.#scene.remove(this.#css2DObject.upOverlay);
			return;
		}
		this.#loadUserProfile(user);
		this.#scene.add(this.#css2DObject.usersprofile);
		this.#scene.add(this.#css2DObject.upOverlay);
	}

	#addLeaderboardCss2D() {
		const leaderboardContainer = document.createElement('div');
		leaderboardContainer.className = 'leaderboard';
		leaderboardContainer.innerHTML = LEADERBOARDMAIN;

		this.#css2DObject.leaderboard = new CSS2DObject(leaderboardContainer);
		this.#css2DObject.leaderboard.name = 'leaderboard';
	}

	#addChatCss2D() {
		const chatContainer = document.createElement('div');
		chatContainer.className = 'chat-interface';
		chatContainer.innerHTML = MAINCHAT;

		this.#css2DObject.chat = new CSS2DObject(chatContainer);
		this.#css2DObject.chat.name = 'chat';
	}

	#handelChatSent() {
		const message = this.#css2DObject.chat.element
			.querySelector('.message')
			.value.trim();
		if (message && this.#chatWebSocket[this.#chatuser]?.sock) {
			this.#css2DObject.chat.element
				.querySelector('.message')
				.addEventListener('keyup', e => {
					if (e.key === 'Enter')
						this.#css2DObject.chat.element.querySelector(
							'.message'
						).value = '';
				});
			this.#chatWebSocket[this.#chatuser].sock.send(
				JSON.stringify({
					message: message,
					username: this.#loggedUser,
				})
			);
			this.#css2DObject.chat.element.querySelector('.message').value = '';
		}
	}

	#addSentMessage(message) {
		const sentMessage = document.createElement('template');
		sentMessage.innerHTML = SENT.trim();
		sentMessage.content.firstChild.querySelector('.you').textContent =
			message;
		this.#css2DObject.chat.element
			.querySelector('.recived-parent')
			.appendChild(sentMessage.content.firstChild);
	}

	#addRecivedMessage(message) {
		const sentMessage = document.createElement('template');
		sentMessage.innerHTML = RECIVED.trim();
		sentMessage.content.firstChild.querySelector('.you').textContent =
			message;
		this.#css2DObject.chat.element
			.querySelector('.recived-parent')
			.appendChild(sentMessage.content.firstChild);
	}

	#createControls() {
		this.#controls = new OrbitControls(
			this.#camera,
			this.#renderer.domElement
		);
		this.#controls.addEventListener('change', () => this.#render());
		this.#controls.target.set(0, 0, 0);
		this.#controls.update();
	}

	#loadEnvironment() {
		new RGBELoader().setPath('textures/').load(
			'royal_esplanade_1k.hdr',
			texture => {
				texture.mapping = THREE.EquirectangularReflectionMapping;
				this.#scene.background = texture;
				this.#scene.environment = texture;
				this.#loadModelGLTF();
			},
			undefined,
			error => console.error('Error loading HDR texture:', error)
		);
	}

	#loadModelGLTF() {
		const loader = new GLTFLoader().setPath('models/');
		loader.load(
			'Game Play.gltf',
			async gltf => {
				const model = gltf.scene;
				await this.#renderer.compileAsync(
					model,
					this.#camera,
					this.#scene
				);
				this.#scene.add(model);
				this.#setObjects(model);

				this.#mixer = new THREE.AnimationMixer(model);
				gltf.animations.forEach(clip =>
					this.#mixer.clipAction(clip).play()
				);

				this.#render();
			},
			undefined,
			error => console.error('Error loading GLTF model:', error)
		);
	}

	#loadFont() {
		this.#ttf = new TTFLoader();

		this.#ttf.load('fonts/Gabriela-Regular.ttf', ttf => {
			this.#font = new FontLoader().parse(ttf);
		});
	}

	#onWindowResize() {
		this.#camera.aspect = window.innerWidth / window.innerHeight;
		this.#camera.updateProjectionMatrix();
		this.#renderer.setSize(window.innerWidth, window.innerHeight);
		this.#css2DRenderer.setSize(window.innerWidth, window.innerHeight);
		this.#render();
	}

	#render() {
		this.#renderer.render(this.#scene, this.#camera);
	}

	#animate() {
		const now = performance.now();
		const delta = (now - this.#lastFrameTime) / 1000;

		if (now - this.#lastFrameTime > 1000 / this.#frameRate) {
			this.#lastFrameTime = now;
			this.#update();
			if (this.#mixer) this.#mixer.update(delta);
			if (this.#hasChanges) this.#render();
			this.#hasChanges = false;
		}

		requestAnimationFrame(() => this.#animate());
		this.#css2DRenderer.render(this.#scene, this.#camera);
		this.#renderer.render(this.#scene, this.#camera);
	}

	#update() {
		this.#hasChanges = false;
		if (this.#ball) {
			this.#ball.position.add(this.#ballDirection);
			this.#ball.rotation.x += this.#ballDirection.x;
			this.#ball.rotation.y += this.#ballDirection.y;
			this.#ballBox.setFromObject(this.#ball);
			// this.#checkCollisions();
			this.#hasChanges = true;
		}
		if (this.#player) {
			this.#handelePlayerMovement(
				this.#player,
				this.#playerBox,
				this.#playerDirection,
				'Racket'
			);
		}
		if (this.#player2) {
			this.#handelePlayerMovement(
				this.#player2,
				this.#player2Box,
				this.#player2Direction,
				'Racket001'
			);
		}
	}

	#resetScore() {
		this.#scoreL = 0;
		this.#scoreR = 0;
		this.#updateScoreL('0');
		this.#updateScoreR('0');
	}

	#updateScoreL(newText) {
		if (this.#font && this.#scoreLText) {
			this.#scoreLText.geometry.dispose();

			const newTextGeometry = new TextGeometry(newText, {
				font: this.#font,
				size: 2,
				depth: 0,
			});
			newTextGeometry.computeBoundingBox();

			const boundingBox = newTextGeometry.boundingBox;
			const xOffset = (boundingBox.max.x - boundingBox.min.x) / 2;
			const yOffset = (boundingBox.max.y - boundingBox.min.y) / 2;

			newTextGeometry.translate(-xOffset, -yOffset, 0);

			this.#scoreLText.geometry = newTextGeometry;

			this.#scoreLText.rotation.set(0.296706, Math.PI, Math.PI);

			this.#hasChanges = true;
		}
	}

	#updateScoreR(newText) {
		if (this.#font && this.#scoreRText) {
			this.#scoreRText.geometry.dispose();

			const newTextGeometry = new TextGeometry(newText, {
				font: this.#font,
				size: 2,
				depth: 0,
			});
			newTextGeometry.computeBoundingBox();

			const boundingBox = newTextGeometry.boundingBox;
			const xOffset = (boundingBox.max.x - boundingBox.min.x) / 2;
			const yOffset = (boundingBox.max.y - boundingBox.min.y) / 2;

			newTextGeometry.translate(-xOffset, -yOffset, 0);

			this.#scoreRText.geometry = newTextGeometry;

			this.#scoreRText.rotation.set(0.296706, Math.PI, Math.PI);

			this.#hasChanges = true;
		}
	}

	#handelePlayerMovement(player, playerBox, playerDirection, name) {
		const wallBox =
			playerDirection === 1 ? this.#wallsBoxes[0] : this.#wallsBoxes[1];

		playerBox.setFromObject(player.getObjectByName(name));
		const target = player.position.y + this.#velocity * playerDirection;
		for (
			;
			player.position.y !== target;
			player.position.y += playerDirection
		) {
			if (playerBox.intersectsBox(wallBox)) break;
		}
		this.#hasChanges = true;
	}

	#checkPlayerCollisions(player, playerDirection, name) {
		const newPlayer = player.clone();
		const wallBox =
			playerDirection === 1 ? this.#wallsBoxes[0] : this.#wallsBoxes[1];

		newPlayer.position.y += this.#velocity * playerDirection;

		const playerBox = new THREE.Box3().setFromObject(
			newPlayer.getObjectByName(name)
		);

		if (playerBox.intersectsBox(wallBox)) {
			return false;
		}
		return true;
	}

	#checkCollisions() {
		this.#wallsBoxes.forEach((wallBox, i) => {
			if (this.#ballBox.intersectsBox(wallBox)) {
				this.#handleBallWallCollision(i);
			}
		});

		if (this.#ballBox.intersectsBox(this.#goalRBox)) {
			this.#handleBallGoalCollision('goalR');
		}
		if (this.#ballBox.intersectsBox(this.#goalLBox)) {
			this.#handleBallGoalCollision('goalL');
		}

		if (this.#ballBox.intersectsBox(this.#playerBox)) {
			this.#handlePlayerCollision(this.#player);
		}

		if (this.#ballBox.intersectsBox(this.#player2Box)) {
			this.#handlePlayerCollision(this.#player2);
		}
	}

	#handlePlayerCollision(player) {
		const direction = this.#ball.position
			.clone()
			.sub(player.position)
			.normalize();
		direction.x =
			Math.sign(direction.x) *
			Math.max(Math.abs(direction.x), this.#minDir);
		direction.y =
			Math.sign(direction.y) *
			Math.max(Math.abs(direction.y), this.#minDir);
		direction.z =
			Math.sign(direction.z) *
			Math.max(Math.abs(direction.z), this.#minDir);
		this.#ballDirection = direction.multiplyScalar(
			this.#velocity * this.#factor
		);
	}

	#handleBallWallCollision() {
		this.#ballDirection.y = -this.#ballDirection.y;
	}

	#handleBallGoalCollision(goal) {
		goal === 'goalR' ? this.#scoreL++ : this.#scoreR++;
		this.#ball.position.set(0, 0, 0);
		this.#updateScoreL(String(this.#scoreL));
		this.#updateScoreR(String(this.#scoreR));
		this.startBall();
	}

	#setObjects(model) {
		this.#ball = model.getObjectByName('Ball');
		this.#player = model.getObjectByName('Player');
		this.#player2 = model.getObjectByName('PlayerTwo');
		this.#goalR = model.getObjectByName('Goal_Right');
		this.#goalL = model.getObjectByName('Goal_Left');
		this.#walls = model.getObjectByName('Walls');
		this.#walls.children.forEach(wall =>
			this.#wallsBoxes.push(new THREE.Box3().setFromObject(wall))
		);
		this.#goalRBox.setFromObject(this.#goalR);
		this.#goalLBox.setFromObject(this.#goalL);
		this.#scoreLText = model.getObjectByName('ScoreL');
		this.#scoreRText = model.getObjectByName('ScoreR');

		this.#resetScore();
	}

	// moveUp() {
	// 	if (this.#checkPlayerCollisions(this.#player, -1, 'Racket')) {
	// 		this.#playerDirection = -1;
	// 		this.#hasChanges = true;
	// 	} else {
	// 		this.#playerDirection = 0;
	// 		this.#hasChanges = true;
	// 	}
	// }

	// moveDown() {
	// 	if (this.#checkPlayerCollisions(this.#player, 1, 'Racket')) {
	// 		this.#playerDirection = 1;
	// 		this.#hasChanges = true;
	// 	} else {
	// 		this.#playerDirection = 0;
	// 		this.#hasChanges = true;
	// 	}
	// }

	// moveUp2() {
	// 	if (this.#checkPlayerCollisions(this.#player2, -1, 'Racket001')) {
	// 		this.#player2Direction = -1;
	// 		this.#hasChanges = true;
	// 	} else {
	// 		this.#player2Direction = 0;
	// 		this.#hasChanges = true;
	// 	}
	// }

	// moveDown2() {
	// 	if (this.#checkPlayerCollisions(this.#player2, 1, 'Racket001')) {
	// 		this.#player2Direction = 1;
	// 		this.#hasChanges = true;
	// 	} else {
	// 		this.#player2Direction = 0;
	// 		this.#hasChanges = true;
	// 	}
	// }

	// startBall() {
	// 	let x = this.#random(-1.0, 1.0);
	// 	let y = this.#random(-1.0, 1.0);

	// 	if (Math.abs(x) < this.#minDir) x = Math.sign(x) * this.#minDir;
	// 	if (Math.abs(y) < this.#minDir) y = Math.sign(y) * this.#minDir;

	// 	this.#ballDirection = new THREE.Vector3(x, y).multiplyScalar(
	// 		this.#velocity * this.#factor
	// 	);
	// 	this.#hasChanges = true;
	// }

	// stopPlayerMovement() {
	// 	this.#playerDirection = 0;
	// 	this.#hasChanges = true;
	// }

	// stopPlayer2Movement() {
	// 	this.#player2Direction = 0;
	// 	this.#hasChanges = true;
	// }

	#random(min, max) {
		return Math.random() * (max - min) + min;
	}

	dispose() {
		if (this.#ball) this.#ball.geometry.dispose();
		if (this.#ball.material) this.#ball.material.dispose();
		if (this.#renderer) {
			this.#renderer.dispose();
			this.#renderer = null;
		}
		this.#scene.traverse(object => {
			if (object.geometry) object.geometry.dispose();
			if (object.material) object.material.dispose();
		});
	}

	async #loggedin() {
		try {
			const access = localStorage.getItem('accessToken');
			const refresh = localStorage.getItem('refreshToken');
			const twofa = this.#css2DObject.sbook.element;

			if (access) {
				const response = await fetch(`api/verify-token/`, {
					method: 'POST',
					headers: {
						'Content-Type': 'application/json',
					},
					body: JSON.stringify({
						token: access,
					}),
				});
				if (response.ok) {
					const data = await response.json();
					this.#css2DObject.profilepic.element.src = data.avatar;
					this.#loggedUser = data.username;
					this.#isRemote = data.remote;
					if (data.otp_required) {
						twofa.querySelector(
							'.fa-icon1'
						).src = `/textures/svg/2FA ON.svg`;
						twofa
							.querySelector('.factor-authentication')
							.classList.remove('factor-authentication-op');
						this.#enabled2fa = true;
					}
					return true;
				} else {
					if (refresh) {
						const refreshResponse = await fetch(
							`api/refresh-token/`,
							{
								method: 'POST',
								headers: {
									'Content-Type': 'application/json',
								},
								body: JSON.stringify({
									refresh: refresh,
								}),
							}
						);

						if (refreshResponse.ok) {
							const data = await refreshResponse.json();
							this.#css2DObject.profilepic.element.src =
								data.avatar;
							this.#loggedUser = data.username;
							localStorage.setItem('accessToken', data.access);
							this.#isRemote = data.remote;
							if (data.otp_required) {
								twofa.querySelector(
									'.fa-icon1'
								).src = `/textures/svg/2FA ON.svg`;
								twofa
									.querySelector('.factor-authentication')
									.classList.remove(
										'factor-authentication-op'
									);
								this.#enabled2fa = true;
							}
							return true;
						}
					}
				}
			}
			return false;
		} catch (error) {
			alert('Error during authentication:', error);
			return false;
		}
	}

	#validateEmail(email) {
		const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
		return re.test(email);
	}

	async #Register() {
		const { value: email } =
			this.#css2DObject.register.element.querySelector('#email');
		const { value: username } =
			this.#css2DObject.register.element.querySelector('#username');
		const { value: password } =
			this.#css2DObject.register.element.querySelector('#password');
		const { value: confirmPassword } =
			this.#css2DObject.register.element.querySelector('#confpassword');
		const { value: gender } =
			this.#css2DObject.register.element.querySelector('#gender');

		const errors = [];

		if (!email || !this.#validateEmail(email)) {
			errors.push('Please enter a valid email address');
		}

		if (!username || username.length < 3) {
			errors.push('Username must be at least 3 characters long');
		}

		if (!password || password.length < 8) {
			errors.push('Password must be at least 8 characters long');
		}

		if (password !== confirmPassword) {
			errors.push("Passwords don't match");
		}

		if (errors.length > 0) {
			alert(errors.join('\n'));
			return false;
		}

		try {
			const response = await fetch(`api/register/`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
				},
				body: JSON.stringify({
					email,
					username,
					password,
					confirmPassword,
					gender,
				}),
			});

			const data = await response.json();
			if (response.ok) {
				localStorage.setItem('accessToken', data.access);
				localStorage.setItem('refreshToken', data.refresh);
				this.#css2DObject.profilepic.element.src = data.avatar;
				this.#loggedUser = data.username;
				this.#HomePage();
			} else {
				let errorMessage = 'Registration failed:\n';

				const errorFields = [
					'email',
					'username',
					'password',
					'non_field_errors',
				];
				errorFields.forEach(field => {
					if (data[field]) {
						errorMessage += `${field}: ${data[field].join(', ')}\n`;
					}
				});

				alert(errorMessage.trim());
			}
		} catch (error) {
			alert('Registration error:', error);
		}
	}

	async #Login() {
		try {
			const { value: username } =
				this.#css2DObject.sign.element.querySelector('#username');
			const { value: password } =
				this.#css2DObject.sign.element.querySelector('#password');

			const response = await fetch(`api/login/`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
				},
				body: JSON.stringify({ username, password }),
			});
			const data = await response.json();
			if (response.ok) {
				if (!data.otp_required) {
					this.#enabled2fa = false;
					const tokens = data.tokens;
					this.#css2DObject.profilepic.element.src = data.avatar;
					this.#loggedUser = data.username;
					localStorage.setItem('accessToken', tokens.access);
					localStorage.setItem('refreshToken', tokens.refresh);
					this.#HomePage();
				} else {
					this.#scene.add(this.#css2DObject.valid);
					this.#scene.remove(this.#css2DObject.sign);
					this.#css2DObject.valid.element
						.querySelector('.login2')
						.addEventListener('click', async e => {
							const { value: code } =
								this.#css2DObject.valid.element.querySelector(
									'#digit'
								);
							const response = await fetch(`api/login/`, {
								method: 'POST',
								headers: {
									'Content-Type': 'application/json',
								},
								body: JSON.stringify({
									username,
									password,
									otp: code,
								}),
							});
							const data = await response.json();
							if (response.ok) {
								this.#enabled2fa = true;
								const twofa = this.#css2DObject.sbook.element;

								const tokens = data.tokens;
								this.#css2DObject.profilepic.element.src =
									data.avatar;
								this.#loggedUser = data.username;
								localStorage.setItem(
									'accessToken',
									tokens.access
								);
								localStorage.setItem(
									'refreshToken',
									tokens.refresh
								);
								twofa.querySelector(
									'.fa-icon1'
								).src = `/textures/svg/2FA ON.svg`;
								twofa
									.querySelector('.factor-authentication')
									.classList.remove(
										'factor-authentication-op'
									);
								this.#HomePage();
							} else {
								alert(Object.values(data).flat().join(', '));
							}
						});
				}
			} else {
				alert(Object.values(data).flat().join(', '));
			}
		} catch (error) {
			alert('Error:', error);
		}
	}

	async #LoginPage() {
		const stat = await this.#loggedin();
		if (!stat) {
			['home', 'paner', 'settings', 'profilepic'].forEach(ele => {
				this.#scene.remove(this.#css2DObject[ele]);
			});
			this.#scene.add(this.#css2DObject.login);
		}
	}

	#HomePage() {
		this.#toggleSign();
		this.#scene.remove(this.#css2DObject.login);
		['home', 'paner', 'settings', 'profilepic'].forEach(ele => {
			this.#scene.add(this.#css2DObject[ele]);
		});
	}

	#initializeGame() {
		this.#ball?.position.set(0, 0, 0);
		this.#player?.position.set(-1300, 0, 0);
		this.#player2?.position.set(1300, 0, 0);
		this.#updateScoreL('0');
		this.#updateScoreR('0');
	}

	#resetGameState() {
		// Reset scores
		this.#updateScoreL('0');
		this.#updateScoreR('0');

		// Reset ball position if needed
		if (this.#ball) {
			this.#ball.position.set(0, 0, 0);
		}

		// Reset paddle positions if needed
		if (this.#player) {
			this.#player.position.set(-1300, 0, 0);
		}
		if (this.#player2) {
			this.#player2.position.set(1300, 0, 0);
		}

		this.#hasChanges = true;
	}

	#updateGameState(game_data) {
		if (this.#ball) {
			// Update ball position
			this.#ball.position.set(
				game_data.ballPosition.x,
				game_data.ballPosition.y,
				game_data.ballPosition.z
			);

			// Add rotation for visual effect only
			this.#ball.rotation.x += game_data.ballDirection.x;
			this.#ball.rotation.y += game_data.ballDirection.y;
		}

		// Update paddles
		game_data.paddlePositions.forEach(paddle => {
			const paddleMesh =
				paddle.playerId === 'player1' ? this.#player : this.#player2;
			if (paddleMesh) {
				paddleMesh.position.set(
					paddle.position.x,
					paddle.position.y,
					paddle.position.z
				);
			}
		});

		// Update scores
		if (game_data.scoreL !== undefined && game_data.scoreR !== undefined) {
			this.#updateScoreL(String(game_data.scoreL));
			this.#updateScoreR(String(game_data.scoreR));
		}

		this.#hasChanges = true;
	}

	#matchmaking(data) {
		['player1', 'player2'].forEach(player => {
			this.#css2DObject.match.element.querySelector(
				`#${player}`
			).textContent = data[player].usr;
			this.#css2DObject.match.element.querySelector(
				`#${player}-avatar`
			).src = data[player].avatar;
		});
		setTimeout(() => {
			this.#scene.remove(this.#css2DObject.match);
			this.#css2DObject.match.element.innerHTML = MATCHMAKING;
		}, 4000);
	}

	#twoPlayer() {
		// Remove current game menu
		this.#scene.remove(this.#css2DObject.game);
		this.#scene.add(this.#css2DObject.match);

		this.#css2DObject.match.element.querySelector('#player1').textContent =
			this.#loggedUser;
		this.#css2DObject.match.element.querySelector('#player1-avatar').src =
			document.querySelector('#profilePicImage').src;

		// Close any existing connection
		if (this.#gameWebSocket) {
			this.#gameWebSocket.close();
			this.#gameWebSocket = null;
		}

		// Reset game state
		this.#resetGameState();

		try {
			this.#gameWebSocket = new WebSocket(
				`wss://${window.location.host}/api/ws/game/`
			);

			this.#gameWebSocket.onopen = () => {
				const initData = {
					username: this.#loggedUser,
				};
				this.#gameWebSocket.send(JSON.stringify(initData));
				this.#initializeGame();
			};

			this.#gameWebSocket.onmessage = e => {
				try {
					const data = JSON.parse(e.data);

					if (data.type === 'game_start') {
						this.#matchmaking(data.players);
					}
					if (data.type === 'update') {
						this.#updateGameState(data);
					} else if (data.type === 'game_end') {
						// Handle game end
						this.#resetGameState();
						this.#gameWebSocket.close();
						this.#gameWebSocket = null;
						this.#scene.add(this.#css2DObject.game); // Return to menu
					} else if (data.type === 'error') {
						console.error('Game error:', data.message);
						this.#gameWebSocket.close();
						this.#gameWebSocket = null;
						this.#scene.add(this.#css2DObject.game); // Return to menu
					}
				} catch (error) {
					console.error('Error processing game message:', error);
				}
			};

			this.#gameWebSocket.onerror = error => {
				console.error('WebSocket error:', error);
				this.#gameWebSocket = null;
				this.#scene.add(this.#css2DObject.game); // Return to menu
			};

			this.#gameWebSocket.onclose = () => {
				if (this.#gameWebSocket) {
					this.#gameWebSocket = null;
					this.#resetGameState();
					this.#scene.add(this.#css2DObject.game); // Return to menu
				}
			};
		} catch (error) {
			console.error('Failed to create WebSocket connection:', error);
			this.#gameWebSocket = null;
			this.#scene.add(this.#css2DObject.game); // Return to menu
		}
	}

	#startTournamentMatch(matchData) {
		// Check if we're already in this match
		if (
			this.#currentMatch &&
			this.#currentMatch.match_id === matchData.match_id
		) {
			console.log('Already in this match, ignoring duplicate message');
			return;
		}

		// Store current match
		this.#currentMatch = matchData;

		// Close existing connection if any
		if (this.#gameWebSocket) {
			this.#gameWebSocket.close();
			this.#gameWebSocket = null;
		}

		// Create new connection
		try {
			this.#gameWebSocket = new WebSocket(
				`wss://${window.location.host}/api/ws/game/`
			);

			this.#gameWebSocket.onopen = () => {
				console.log('Tournament game connecting...');

				this.#gameWebSocket.send(
					JSON.stringify({
						username: this.#loggedUser,
						tournament_data: {
							player1: matchData.player1,
							player2: matchData.player2,
							tournament_id: matchData.tournament_id,
							match_id: matchData.match_id,
							consumer: matchData.consumer,
						},
					})
				);
				this.#initializeGame();
			};

			this.#gameWebSocket.onmessage = e => {
				try {
					const data = JSON.parse(e.data);
					if (data.type === 'update') {
						this.#updateGameState(data);
					} else if (data.type === 'game_end') {
						console.log('Game ended:', data);
						this.#currentMatch = null; // Clear current match
						this.#gameWebSocket.close();
						this.#gameWebSocket = null;
					}
				} catch (error) {
					console.error('Error handling game message:', error);
				}
			};

			this.#gameWebSocket.onerror = error => {
				console.error('Game WebSocket error:', error);
			};

			this.#gameWebSocket.onclose = () => {
				console.log('Game connection closed');
				this.#gameWebSocket = null;
			};
		} catch (error) {
			console.error('Error creating game connection:', error);
			this.#gameWebSocket = null;
			this.#currentMatch = null;
		}
	}

	#tournament() {
		if (this.#tournamentWebSocket) {
			this.#tournamentWebSocket.close();
			this.#tournamentWebSocket = null;
		}

		this.#tournamentWebSocket = new WebSocket(
			`wss://${window.location.host}/api/ws/tournament/`
		);

		this.#tournamentWebSocket.onopen = () => {
			console.log('Connected to tournament WebSocket.');
			this.#tournamentWebSocket.send(
				JSON.stringify({
					type: 'join_tournament',
					username: this.#loggedUser,
				})
			);
		};

		this.#tournamentWebSocket.onmessage = e => {
			try {
				const data = JSON.parse(e.data);
				console.log('Tournament message received:', data);

				if (data.type === 'match_ready') {
					// Double check this is our match
					if (
						this.#loggedUser === data.player1 ||
						this.#loggedUser === data.player2
					) {
						console.log(
							`Match notification for ${this.#loggedUser}:`,
							data
						);
						if (
							!this.#currentMatch ||
							this.#currentMatch.match_id !== data.match_id
						) {
							console.log('Starting new match:', data);
							this.#startTournamentMatch(data);
						}
					}
				} else if (data.type === 'players_update') {
					console.log('Players list updated:', data.data);
				}
			} catch (error) {
				console.error('Error handling tournament message:', error);
			}
		};

		this.#tournamentWebSocket.onerror = error => {
			console.error('Tournament WebSocket error:', error);
		};

		this.#tournamentWebSocket.onclose = () => {
			console.log('Tournament connection closed');
			this.#tournamentWebSocket = null;
			// Optional: Attempt to reconnect after a delay
			// setTimeout(() => this.#tournament(), 3000);
		};
	}

	cleanup() {
		if (this.#gameWebSocket) {
			this.#gameWebSocket.close();
			this.#gameWebSocket = null;
		}
		if (this.#tournamentWebSocket) {
			this.#tournamentWebSocket.close();
			this.#tournamentWebSocket = null;
		}
		this.#currentMatch = null;
	}

	#offline() {
		this.#scene.remove(this.#css2DObject.game);
		this.#scene.add(this.#css2DObject.offline);
		this.#css2DObject.offline.element
			.querySelector('.card-container')
			.addEventListener('click', e => {
				const btn = e.target.closest('.card').id;
				if (btn) {
				}
			});
	}

	#online() {
		this.#scene.remove(this.#css2DObject.game);
		this.#twoPlayer();
	}

	#tournamentl() {}

	#GamePage() {
		this.#css2DObject.game.element
			.querySelector('.card-container')
			.addEventListener('click', e => {
				const btn = e.target.closest('.card').id;
				if (btn) {
					const choices = {
						offline: this.#offline.bind(this),
						online: this.#online.bind(this),
						tournament: this.#tournamentl.bind(this),
					};
					choices[btn]();
				}
			});
	}

	#switchHome(home) {
		if (this.#gameWebSocket) this.#gameWebSocket.close();
		if (home !== 'chat') this.#onlineSocket?.close();

		const legendText = {
			chat: LEGEND_CHAT,
			leaderboard: LEGEND_LEADERBOARD,
		};

		['game', 'chat', 'leaderboard', 'offline'].forEach(ele => {
			this.#scene.remove(this.#css2DObject[ele]);
		});

		this.#css2DObject.home.element.innerHTML = this.#home[home];

		if (home !== 'home' && home !== 'game') {
			this.#css2DObject.profilepic.element.classList.add(
				'profile-pic-tran'
			);

			if (legendText[home]) {
				this.#css2DObject.legend.element.querySelector(
					'.dont-bother-me'
				).textContent = legendText[home];
				this.#scene.add(this.#css2DObject.legend);
			}
		} else {
			this.#css2DObject.profilepic.element.classList.remove(
				'profile-pic-tran'
			);
			this.#scene.remove(this.#css2DObject.legend);
		}
		if (home === 'chat') {
			this.#switchChatTab(1);
			this.#onlineSocket = new WebSocket(
				`wss://${window.location.host}/api/ws/online_status/${
					this.#loggedUser
				}/`
			);

			this.#onlineSocket.onopen = e => {};

			this.#onlineSocket.onmessage = e => {
				const data = JSON.parse(e.data);
				this.#onlineUsers = data.online_users;
				this.#switchChatTab(this.#selectedTab);
			};

			this.#onlineSocket.onerror = error => {
				console.error('WebSocket error:', error);
			};

			this.#onlineSocket.onclose = e => {};
		}
		if (home === 'game') {
			this.#GamePage();
		}

		history.replaceState(null, null, `/${home}`);
		this.#scene.add(this.#css2DObject[home]);
	}

	sendMovement(direction) {
		this.#gameWebSocket?.send(
			JSON.stringify({
				action: 'move',
				direction: direction,
			})
		);
	}

	stopMovement() {
		this.#gameWebSocket?.send(
			JSON.stringify({
				action: 'stop_move',
			})
		);
	}
}

export default new Game();
