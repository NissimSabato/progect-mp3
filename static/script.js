// הצגת קלט שם התקייה
function showFolderInput() {
    document.getElementById('folderNameContainer').style.display = 'block';
    document.getElementById('finishButton').style.display = 'inline';
    document.getElementById('packageButton').style.display = 'none'; // הסתרת כפתור ארוז
}

// שליחת בקשת אריזת השירים לשרת
async function packageSongs() {
    const folderName = document.getElementById('folderName').value;
    if (!folderName) {
        alert("אנא הכנס שם תקייה");
        return;
    }

    try {
        const response = await fetch('/package_songs', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + localStorage.getItem('access_token')  // הנח שהטוקן שמור ב-localStorage
            },
            body: JSON.stringify({ folder_name: folderName })
        });

        const data = await response.json();
        if (response.ok) {
            alert('השירים נארזו בהצלחה בתקייה: ' + data.folder_path);
            
            // סגירת הקלט והצגת כפתור "ארוז" שוב
            document.getElementById('folderNameContainer').style.display = 'none';
            document.getElementById('finishButton').style.display = 'none';
            document.getElementById('packageButton').style.display = 'inline';
            
            // רענון הטבלה של היסטוריית ההורדות
            refreshDownloadHistory(); // קרא לפונקציה שאחראית לרענון היסטוריית ההורדות
        } else {
            alert('שגיאה: ' + data.error);
        }
    } catch (error) {
        alert('שגיאה: ' + error.message);
    }
}

// פונקציה לרענון היסטוריית ההורדות מבלי לרענן את כל העמוד
function refreshDownloadHistory() {
    fetch('/download-history', {
        method: 'GET',
        headers: {
            'Authorization': 'Bearer ' + localStorage.getItem('access_token')
        }
    })
    .then(response => response.json())
    .then(data => {
        let tbody = document.querySelector('#history-container tbody');
        tbody.innerHTML = ''; // ניקוי התוכן הקיים
        
        data.forEach((item, index) => {
            tbody.innerHTML += `
                <tr>
                    <td>${index + 1}</td>
                    <td>${item.SongName}</td>
                    <td>
                        <span class="play-btn" onclick="playSong(${item.DownloadID}, '${item.SongName}')">▶️ השמע</span>
                    </td>
                    <td>
                        <span class="delete-btn" onclick="removeRow(this, ${item.DownloadID}, 'download')">&times;</span>
                    </td>
                </tr>
            `;
        });
    })
    .catch(error => console.error('Error:', error));
}




document.getElementById('searchButton').addEventListener('click', function() {
    const query = document.getElementById('searchInput').value;
    if (query) {
        const searchIndicator = document.getElementById('searchIndicator');
        searchIndicator.style.display = 'block';
        searchIndicator.textContent = 'מחפש...';

        const token = localStorage.getItem('access_token'); // קבלת ה-JWT

        fetch(`/search?query=${encodeURIComponent(query)}`, {
            method: 'GET',
            headers: {
                'Authorization': 'Bearer ' + token, // שליחת ה-JWT בכותרת
                'Content-Type': 'application/json'
            }
        })
        .then(response => {
            if (response.status === 401) {
                alert('המשתמש אינו מורשה. נא להתחבר מחדש.');
                return;
            }
            return response.json();
        })
        .then(results => {
            const list = document.getElementById('resultsList');
            list.innerHTML = '';
            results.forEach((video, index) => {
                const li = document.createElement('li');
                li.innerHTML = `<img src="${video.thumbnail}" alt="Thumbnail"> ${index + 1}. ${video.title}`;
                li.addEventListener('click', () => selectVideo(video));
                list.appendChild(li);
            });
            searchIndicator.style.display = 'none';
        })
        .catch(error => {
            alert('שגיאה בחיפוש: ' + error.message);
            searchIndicator.style.display = 'none';
        });
    }
});

// פונקציה לבחירת וידאו ולהפעלת הורדה בלחיצה על כפתור ההורדה
function selectVideo(video) {
    const downloadButton = document.getElementById('downloadButton');
    downloadButton.disabled = false;  // מאפשר לחיצה על הכפתור לאחר בחירת הוידאו
    downloadButton.onclick = function() {
        startDownload(video.url, video.title);  // מפעיל את הורדת הוידאו
    };
}

// פונקציה להתחלת ההורדה
function startDownload(url, title) {
    const token = localStorage.getItem('access_token');  // קבלת ה-JWT מה-localStorage
    const downloadButton = document.getElementById('downloadButton');
    const progressBar = document.getElementById('progressBar');
    const searchIndicator = document.getElementById('searchIndicator');

    downloadButton.disabled = true;  // מנטרל את כפתור ההורדה במהלך ההורדה
    progressBar.style.width = '0';   // מאפס את פס ההתקדמות
    searchIndicator.textContent = 'ממתין להורדה...';  // הודעת סטטוס במהלך ההורדה

    // ביצוע בקשה להורדה עם JWT בכותרת
    fetch(`/download?url=${encodeURIComponent(url)}&title=${encodeURIComponent(title)}`, {
        method: 'GET',
        headers: {
            'Authorization': 'Bearer ' + token,  // הוספת JWT לכותרת הבקשה
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        if (!response.ok) {  // בדיקת סטטוס התשובה
            throw new Error('שגיאה בהורדה: ' + response.statusText);
        }
        const reader = response.body.getReader();  // קריאת גוף התשובה כזרם נתונים
        const contentLength = +response.headers.get('Content-Length');
        let receivedLength = 0;

        function read() {
            return reader.read().then(({ done, value }) => {
                if (done) {
                    progressBar.style.width = '100%';  // עדכון פס ההתקדמות ל-100% בסיום
                    alert('ההורדה הושלמה בהצלחה!');
                    searchIndicator.textContent = '';  // הסתרת ההודעה בסיום ההורדה
                    return;
                }

                receivedLength += value.length;  // חישוב האחוז שהתקבל
                progressBar.style.width = `${(receivedLength / contentLength) * 100}%`;  // עדכון פס ההתקדמות
                return read();  // קריאה חוזרת לפונקציה להמשך קריאה של הנתונים
            });
        }
        read();  // קריאה ראשונית לפונקציה
    })
    .catch(error => {  // טיפול בשגיאות
        alert('שגיאה בהורדה: ' + error.message);
        searchIndicator.textContent = '';  // הסתרת ההודעה במקרה של שגיאה
    });
}
refreshDownloadHistory(); // קרא לפונקציה שאחראית לרענון היסטוריית ההורדות***


// פונקציה למחיקת שורה בטבלה וגם מהמסד
function removeRow(button, id, type) {
    const row = button.closest('tr');

    let url = '';
    if (type === 'download') {
        url = `/delete-download/${id}`;
    } else if (type === 'search') {
        url = `/delete-search/${id}`;
    }

    fetch(url, {
        method: 'DELETE',
        headers: {
            'Authorization': 'Bearer ' + localStorage.getItem('access_token')
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.message) {
            row.remove();  // מחיקת השורה מהטבלה לאחר המחיקה מהשרת
        } else {
            console.error(data.error);
        }
    })
    .catch(error => console.error('Error:', error));
}

// ודא שהקוד רץ לאחר טעינת העמוד
document.addEventListener('DOMContentLoaded', function() {
    // לחצן להראות את היסטוריית ההורדות
    const showDownloadHistoryButton = document.getElementById('show-download-history');
    
    if (showDownloadHistoryButton) {
        showDownloadHistoryButton.onclick = function() {
            fetch('/download-history', {
                method: 'GET',
                headers: {
                    'Authorization': 'Bearer ' + localStorage.getItem('access_token')
                }
            })
            .then(response => response.json())
            .then(data => {
                let historyContainer = document.getElementById('history-container');
                historyContainer.innerHTML = `
                    <h3>היסטוריית הורדות</h3>
                    <table>
                        <thead>
                            <tr>
                                <th>#</th>
                                <th>שם השיר</th>
                                <th>נגן</th> <!-- עמודת נגן -->
                                <th>מחק</th> <!-- עמודת פעולות חדשה -->
                            </tr>
                        </thead>
                        <tbody>
                        </tbody>
                    </table>
                `;

                let tbody = historyContainer.querySelector('tbody');
                data.forEach((item, index) => {
                    tbody.innerHTML += `
                        <tr>
                            <td>${index + 1}</td>
                            <td>${item.SongName}</td>
                            <td>
                                <span class="play-btn" onclick="playSong(${item.DownloadID}, '${item.SongName}')">▶️ השמע</span> <!-- הכפתור נמצא בעמודה נפרדת -->
                            </td>
                            <td>
                                <span class="delete-btn" onclick="removeRow(this, ${item.DownloadID}, 'download')">&times;</span> <!-- כפתור המחיקה בעמודה הכי ימנית -->
                            </td>
                        </tr>
                    `;
                });

                // הוספת הכפתור 'ארוז' מתחת לטבלה
                let packageButtonHtml = `
                    <tr>
                        <td colspan="4" style="text-align: center;">
                            <button id="packageButton" onclick="showFolderInput()">ארוז</button>
                        </td>
                    </tr>
                `;
                tbody.innerHTML += packageButtonHtml; // הוספת השורה עם הכפתור

            })
            .catch(error => console.error('Error:', error));
        };
    }
});

// פונקציה להשמעת השיר
function playSong(downloadId, songName) {
    console.log(`Trying to play song with download ID: ${downloadId}`);
    fetch(`/play_song/${downloadId}`, {
        method: 'GET',
        headers: {
            'Authorization': 'Bearer ' + localStorage.getItem('access_token')
        }
    })
    .then(response => {
        if (response.ok) {
            return response.blob();
        } else {
            throw new Error('Unable to play song');
        }
    })
    .then(blob => {
        const audioUrl = URL.createObjectURL(blob);
        const audioPlayer = document.getElementById('audio-player');
        const audioSource = document.getElementById('audio-source');
        
        audioSource.src = audioUrl; // עדכון ה-src של ה-audio
        audioPlayer.load(); // טעינת המקור החדש

        // הצגת דיב עבור השמעה
        showPlayDialog(songName);
        audioPlayer.play().catch(error => console.error('Error playing audio:', error));
    })
    .catch(error => console.error('Error:', error));
}

// פונקציה להראות דיב להשמעת השיר
function showPlayDialog(songName) {
    const playDialog = document.getElementById('song-dialog');
    playDialog.style.display = 'block';
    const songTitle = playDialog.querySelector('.song-title');
    songTitle.textContent = songName; // עדכון שם השיר
}

// פונקציה לסגור את הדיב מבלי לאפס את השיר
function closePlayDialog() {
    const playDialog = document.getElementById('song-dialog');
    playDialog.style.display = 'none';
    const audioPlayer = document.getElementById('audio-player');
    audioPlayer.pause(); // עצור את הנגינה
    // לא ננקה את ה-src, כך שניתן יהיה להפעיל את השיר שוב
}

// פונקציה לשחזור חיפוש
function repeatSearch(query) {
    // עדכון שדה החיפוש עם המונח
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.value = query; // מכניס את המונח לשדה החיפוש
    }

    // מצא את כפתור החיפוש ולחץ עליו
    const searchButton = document.getElementById('searchButton');
    if (searchButton) {
        searchButton.click();  // מפעיל לחיצה על כפתור החיפוש
    }
}

// פונקציה להצגת היסטוריית חיפושים
document.getElementById('show-search-history').onclick = function() {
    fetch('/search-history', {
        method: 'GET',
        headers: {
            'Authorization': 'Bearer ' + localStorage.getItem('access_token')  // הוספת הטוקן
        }
    })
    .then(response => response.json())
    .then(data => {
        let historyContainer = document.getElementById('history-container');
        historyContainer.innerHTML = `
            <h3>היסטוריית חיפושים</h3>
            <table>
                <thead>
                    <tr>
                        <th>#</th>
                        <th>מונח חיפוש</th>
                        <th>חיפוש חוזר</th>
                        <th>מחק</th>
                    </tr>
                </thead>
                <tbody>
                </tbody>
            </table>
        `;

        let tbody = historyContainer.querySelector('tbody');
        data.forEach((item, index) => {
            tbody.innerHTML += `
                <tr>
                    <td>${index + 1}</td>
                    <td>${item.SearchTerm}</td>
                    <td><span class="search-repeat-btn" onclick="repeatSearch('${item.SearchTerm}')">&#x1F501;</span></td> <!-- אייקון חיפוש חוזר -->
                    <td><span class="delete-btn" onclick="removeRow(this, ${item.SearchID}, 'search')">&times;</span></td> <!-- כפתור מחיקה -->
                </tr>
            `;
        });
    })
    .catch(error => console.error('Error:', error));
};

