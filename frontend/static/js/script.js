import { login } from './pages/login.js';
import { register } from './pages/register.js';

// Function to check if the user is authenticated
// const isAuthenticated = () => {
//     const token = localStorage.getItem('accessToken');
//     // Check if token exists and is not an empty string
//     return token && token !== '';
// };



document.addEventListener('DOMContentLoaded', function() {

    // Check if user is logged in
    if (isAuthenticated()) {
        console.log('User is logged in.');
        // You can redirect the user or display a welcome message
        // Example: Redirect to home if already logged in
        // window.location.href = "/home.html";
    } else {
        console.log('User is not logged in.');
        // Optionally, redirect to the login page if they are not logged in
        // window.location.href = "/login.html";
    }

    // Login form handling
    const loginForm = document.getElementById("loginForm");
    if (loginForm) {
        loginForm.addEventListener("submit", function(event) {
            event.preventDefault();
            const username = document.getElementById("username").value;
            const password = document.getElementById("password").value;
            login(username, password);
        });
    }

    // Register form handling
    const registerForm = document.getElementById("registerForm");
    if (registerForm) {
        registerForm.addEventListener("submit", async function(event) {
            event.preventDefault();
            
            const submitButton = this.querySelector('button[type="submit"]');
            const originalButtonText = submitButton.textContent;
            
            submitButton.disabled = true;
            submitButton.textContent = 'Registering...';
            
            const email = document.getElementById("email").value;
            const username = document.getElementById("username").value;
            const password = document.getElementById("password").value;
            const confirmPassword = document.getElementById("confirmPassword").value;
            
            try {
                await register(email, username, password, confirmPassword);
            } finally {
                submitButton.disabled = false;
                submitButton.textContent = originalButtonText;
            }
        });
    }

    // Form handling for updating display name
    document.addEventListener('DOMContentLoaded', function() {
        const updateNameForm = document.getElementById("updateNameForm");

        if (updateNameForm) {
            updateNameForm.addEventListener("submit", function(event) {
                event.preventDefault();  // Prevent the form from submitting normally
                const displayName = document.getElementById("displayName").value;
                updateDisplayName(displayName);  // Call the function to update the name
            });
        }
    });

});

// understand: 
// [] DOM
// [] addEventListener
// [] getElementById
// [] preventDefault
// [] querySelector
// [] why this: submitButton.disabled = true;
// []  submitButton.disabled = false;
//     submitButton.textContent = originalButtonText;

// Event listeners
// Form handling
// Async/await for the register function
// Error handling with try/finally