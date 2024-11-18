window.onload = async () => {
	if (window.location.pathname.includes('/login')) {
		const urlParams = new URLSearchParams(window.location.search);
		const accessToken = urlParams.get('access');
		const refreshToken = urlParams.get('refresh');

		if (accessToken && refreshToken) {
			localStorage.setItem('accessToken', accessToken);
			localStorage.setItem('refreshToken', refreshToken);

			history.replaceState(null, null, '/');

			window.location.reload();
		} else {
			alert('Login failed: No tokens received.');
		}
	}
};

import game from './Game';
