document.addEventListener("DOMContentLoaded", () => {//to ensure that HTML elements are loaded before the functions are actually executed
    const tabSignIn = document.getElementById('tabSignIn');
    const tabSignUp = document.getElementById('tabSignUp');
    const signInSection = document.getElementById('signInSection');
    const signUpSection = document.getElementById('signUpSection');
    
    const messageBanner = document.getElementById('messageBanner');
    const loginForm = document.getElementById('loginForm');
    const registerForm = document.getElementById('registerForm');

    // Handle structural tab transitions
    tabSignIn.addEventListener('click', () => {
        tabSignUp.classList.remove('active');
        tabSignIn.classList.add('active');
        signUpSection.classList.remove('active');
        signInSection.classList.add('active');
        clearMessage();
    });

    tabSignUp.addEventListener('click', () => {
        tabSignIn.classList.remove('active');
        tabSignUp.classList.add('active');
        signInSection.classList.remove('active');
        signUpSection.classList.add('active');
        clearMessage();
    });

    function displayMessage(text, isError = true) {
        messageBanner.textContent = text;
        messageBanner.className = `message-banner ${isError ? 'error' : 'success'}`;
    }

    function clearMessage() {
        messageBanner.textContent = '';
        messageBanner.className = 'message-banner';
    }

    // PROCESS DISPATCH REGISTRATIONS
    registerForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = new URLSearchParams(new FormData(registerForm));

        try {
            const response = await fetch('/auth/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: formData
            });
            const data = await response.json();

            if (!response.ok) {
                displayMessage(data.detail || "Registration aborted by server.");
            } else {
                displayMessage(data.message, false);
                registerForm.reset();
                tabSignIn.click(); // Programmatically navigate to sign-in panel
            }
        } catch (err) {
            displayMessage("Network connection trace failure encountered.");
        }
    });

    // PROCESS ACCESS CREDENTIAL VERIFICATIONS
    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = new URLSearchParams(new FormData(loginForm));

        try {
            const response = await fetch('/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: formData,
                credentials:"include"
            });
            const data = await response.json();

            if (!response.ok) {
                displayMessage(data.detail || "Verification parameters invalid.");
            } else {
                displayMessage("Credentials validated. Redirecting profile...", false);
                
                // Inspect role profile configuration to resolve dynamic route target
                const checkUser = await fetch('/auth/protected',{credentials:'include'});
                const userProfile = await checkUser.json();

                if (userProfile.role === 'admin') {
                    window.location.href = 'http://localhost:5173/';
                } else if (userProfile.role === 'manager12') {
                    window.location.href = '/track';
                } else {
                    window.location.href = '/growth';
                }
            }
        } catch (err) {
            displayMessage("Network connection trace failure encountered.");
        }
    });
    document.querySelector('.forgot-pw').addEventListener('click', () => {
        window.location.href = '/auth/forgot-password-page';
    });
});
