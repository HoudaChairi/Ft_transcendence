
function updateDisplayName(displayName) {
    const token = localStorage.getItem('access_token');

    if (!token) {
        console.error('No access token found. Please log in.');
        return;
    }

    fetch('http://127.0.0.1:8000/api/update-name/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ display_name: displayName })  // Send the new display name
    })
    .then(response => {
        if (response.ok) {
            return response.json();
        } else {
            throw new Error('Failed to update display name');
        }
    })
    .then(data => {
        console.log('Display name updated successfully:', data);
    })
    .catch(error => console.error('Error:', error));
}
