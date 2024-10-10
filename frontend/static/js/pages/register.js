
function validateEmail(email) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
}

export async function register(email, username, password, confirmPassword) {
    const errors = [];
    
    if (!email || !validateEmail(email)) {
        errors.push("Please enter a valid email address");
    }
    
    if (!username || username.length < 3) {
        errors.push("Username must be at least 3 characters long");
    }
    
    if (!password || password.length < 8) {
        errors.push("Password must be at least 8 characters long");
    }
    
    if (password !== confirmPassword) {
        errors.push("Passwords don't match");
    }
    
    if (errors.length > 0) {
        alert(errors.join('\n'));
        return false;
    }

    // If frontend validation passes, proceed with API call
    try {
        const response = await fetch('http://127.0.0.1:8000/api/register/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                email,
                username,
                password,
                confirmPassword
            })            
        });

        const data = await response.json();
        console.log(data)
        if (response.status === 201) {
            alert('Registration successful! Please login.');
            window.location.href = '/login.html';
            return true;
        } else {
            let errorMessage = 'Registration failed:\n';
            
            // Handle different types of errors from your DRF backend
            const errorFields = ['email', 'username', 'password', 'non_field_errors'];
            errorFields.forEach(field => {
                if (data[field]) {
                    errorMessage += `${field}: ${data[field].join(', ')}\n`;
                }
            });

            alert(errorMessage.trim());
            return false;
        }
    } catch (error) {
        console.error('Registration error:', error);
        alert('An error occurred during registration.');
        return false;
    }
}

// understand:
// [] test
// [] push
// [] forEach
// [] trim