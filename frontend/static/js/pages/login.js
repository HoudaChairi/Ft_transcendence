
export const login = async (username, password) => {
    try {
        const response = await fetch("http://127.0.0.1:8000/api/login/", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ username, password }),
        });
        
        if (response.ok) {
            const data = await response.json();
            const tokens = data.tokens;
            localStorage.setItem("accessToken", tokens.access);
            localStorage.setItem("refreshToken", tokens.refresh);
            console.log("Tokens saved successfully!");
            alert("Login successful!");
        } else {
            console.error("Login failed.");
            alert("Login failed!");
        }
    } catch (error) {
        console.error("Error:", error);
    }
};

// Understand :
// [] async and await
// [] fetch
// [] stringify