
// פונקציה לבדיקת תוקף ה-JWT
function isTokenExpired(token) {
    try {
        const payload = JSON.parse(atob(token.split('.')[1])); // שליפת ה-payload מה-token (JWT)
        const exp = payload.exp; // תאריך התפוגה (ב- Unix timestamp)
        const currentTime = Math.floor(Date.now() / 1000); // הזמן הנוכחי ב- Unix timestamp
        return exp < currentTime; // מחזיר true אם ה-token פג
    } catch (error) {
        console.error('שגיאה בבדיקת ה-JWT:', error);
        return true; // במקרה של שגיאה, נניח שה-token פג
    }
}
// פונקציה לבדיקת תוקף ה-token
function checkTokenValidity() {
    const token = localStorage.getItem('access_token');
    if (token) {
        if (isTokenExpired(token)) {
            alert('תוקף החיבור שלך פג, אנא התנתק והתחבר מחדש.');
            logout(); // מבצע ניתוק
        }
    }
}



        // הצגת טופס התחברות
function showLoginForm() {
    document.getElementById('main-content').innerHTML = `
        <h2>התחברות</h2>
        <form id="login-form">
            <input type="email" id="email" placeholder="אימייל" required>
            <input type="password" id="password" placeholder="סיסמה" required>
            <button type="button" onclick="login()">התחבר</button>
        </form>
        <div id="message"></div>
    `;
}

// התחברות משתמש - עדכון עם שם משתמש וסטטוס
function login() {
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;

    fetch('/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
    })
    .then(response => response.json())
    .then(data => {
        if (data.access_token) {
            localStorage.setItem('access_token', data.access_token);
            localStorage.setItem('username', data.username); // שמירת שם המשתמש
            document.getElementById('message').textContent = 'התחברת בהצלחה';

            // הסתרת טופס ההתחברות
            document.getElementById('main-content').style.display = 'none'; // מסתיר את הטופס

            updateButtons();
            displayUserInfo(); // הצגת שם המשתמש והסטטוס
        } else {
            document.getElementById('message').textContent = 'התחברות נכשלה';
        }
    })
    .catch(error => {
        console.error('Error:', error);
        document.getElementById('message').textContent = 'שגיאה בהתחברות';
    });

}

function displayUserInfo() {
    const username = localStorage.getItem('username');

    // המרת הסטטוס מאנגלית לעברית

    if (username) {
        document.getElementById('user-info').innerHTML = `<span>${username}</span> `;
        document.getElementById('user-info').style.display = 'inline-block';
    } else {
        document.getElementById('user-info').style.display = 'none';
    }
}

// הצגת טופס הרשמה
function showRegisterForm() {
    document.getElementById('main-content').innerHTML = `
        <h2>הרשמה</h2>
        <form id="register-form">
            <input type="text" id="username" placeholder="שם משתמש" required>
            <input type="email" id="email" placeholder="אימייל" required>
            <input type="password" id="password" placeholder="סיסמה" required>
            <button type="button" onclick="register()">הרשם</button>
        </form>
        <div id="message"></div>
    `;
}

// הרשמה
function register() {
    const username = document.getElementById('username').value;
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;

    fetch('/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, email, password})
    })
    .then(response => response.json())
    .then(data => {
        document.getElementById('message').textContent = data.message;
    })
    .catch(error => {
        console.error('Error:', error);
        document.getElementById('message').textContent = 'שגיאה בהרשמה';
    });
}


// הצגת כפתורים מעודכנים בהתאם לסטטוס ההתחברות
function updateButtons() {
    const isLoggedIn = localStorage.getItem('access_token') !== null;
    const loginButton = document.getElementById('login-button');
    const registerButton = document.getElementById('register-button');
    const logout = document.getElementById('logout');
    const logoutButton = document.getElementById('logout-button');
    const downloadHistoryButton = document.getElementById('show-download-history');
    const searchHistoryButton = document.getElementById('show-search-history');
    const historyContainer = document.getElementById('history-container'); // הוספת משתנה עבור ה-history-container
    const mainContent = document.getElementById('main-content'); // הוספת משתנה עבור ה-main-content

    if (isLoggedIn) {
        if (loginButton) loginButton.style.display = 'none';
        if (registerButton) registerButton.style.display = 'none';
        if (logout) logoutButton.style.display = 'inline-block';
        if (logoutButton) logoutButton.style.display = 'inline-block';
        if (downloadHistoryButton) downloadHistoryButton.style.display = 'inline-block'; // הצג כפתור היסטוריית הורדות
        if (searchHistoryButton) searchHistoryButton.style.display = 'inline-block'; // הצג כפתור היסטוריית חיפושים
        if (historyContainer) historyContainer.style.display = 'block'; // הצג את ה-history-container
        if (mainContent) mainContent.style.display = 'none'; // הסתר את ה-main-content
    } else {
        if (loginButton) loginButton.style.display = 'inline-block';
        if (registerButton) registerButton.style.display = 'inline-block';
        if (logoutButton) logoutButton.style.display = 'none';
        if (logout) logoutButton.style.display = 'none';
        if (downloadHistoryButton) downloadHistoryButton.style.display = 'none'; // הסתר כפתור היסטוריית הורדות
        if (searchHistoryButton) searchHistoryButton.style.display = 'none'; // הסתר כפתור היסטוריית חיפושים
        if (historyContainer) historyContainer.style.display = 'none'; // הסתר את ה-history-container
        if (mainContent) mainContent.style.display = 'block'; // הצג את ה-main-content
    }
}

// פונקציה לניתוק
// ניתוק - הסרת שם משתמש וסטטוס
function logout() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('username'); // הסרת שם המשתמש
    alert('התנתקת בהצלחה');
    updateButtons();
    document.getElementById('main-content').innerHTML = ''; // לנקות את התוכן
    displayUserInfo(); // עדכון תצוגת שם המשתמש לאחר ניתוק
    
    // רענון הדף
    window.location.reload();
}

// פונקציה לבדיקת סטטוס התחברות בעת טעינת הדף
function checkLoginStatus() {
    updateButtons(); // לעדכן את הכפתורים בעת טעינת הדף
    displayUserInfo(); // להציג את שם המשתמש והסטטוס אם שמור ב-localStorage
}

window.onload = checkLoginStatus;
window.onload = function() {
    checkTokenValidity(); // בדיקת תוקף ה-token בעת טעינת הדף
    checkLoginStatus();   // עדכון כפתורים ותצוגת משתמש
};


document.getElementById('dashboard-button').addEventListener('click', function() {
    const token = localStorage.getItem('token'); // הנחה שהטוקן נשמר ב-localStorage
    if (token) {
        fetch('/admin/dashboard', {
            method: 'GET',
            headers: {
                'Authorization': 'Bearer ' + token
            }
        })
        .then(response => {
            if (response.ok) {
                // אם הבקשה הצליחה, העבר לדף הלוח בקרה
                window.location.href = '/admin/dashboard';
            } else {
                alert('לא מורשה לגשת לדף זה');
            }
        })
        .catch(error => console.error('Error:', error));
    } else {
        alert('לא נמצא טוקן');
    }
});
        // פונקציה לפתיחת התפריט
        function openNav() {
            document.getElementById("sideMenu").style.width = "400px";
            document.getElementById("history-container").style.width = "300px";
            document.getElementById("main-content").style.width = "300px";
            document.body.style.overflow = "hidden"; // מונע גלילה כשהתפריט פתוח
}

// פונקציה לסגירת התפריט
function closeNav() {
    document.getElementById("sideMenu").style.width = "0";
    document.getElementById("history-container").style.width = "0";
    document.getElementById("main-content").style.width = "0";
    document.body.style.overflow = "auto"; // מחזיר את הגלילה כשהתפריט סגור
}

    // סגירת התפריט בלחיצה מחוץ לו
    document.addEventListener('click', function(event) {
        const sideMenu = document.getElementById('sideMenu');
        const mainContent = document.getElementById('mainContent');
        const historyContainer = document.getElementById('historyContainer');
        const openBtn = document.querySelector('.openbtn');

        if (sideMenu.style.width === '250px' && !sideMenu.contains(event.target) && !openBtn.contains(event.target)) {
            closeNav();
        }
        if (historyContainer.style.width === '250px' && !historyContainer.contains(event.target) && !openBtn.contains(event.target)) {
            closeNav();
        }
    });



