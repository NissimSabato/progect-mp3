import webbrowser
from flask import Flask, request, jsonify, send_from_directory, render_template
from flask_jwt_extended import JWTManager, create_access_token, get_jwt_identity, jwt_required
from yt_dlp import YoutubeDL
from moviepy.editor import AudioFileClip
import os
import threading
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import shutil

# הגדרת האפליקציה והחיבור למסד הנתונים
app = Flask(__name__)

# הגדרות חיבור למסד הנתונים
server = r'DELL-I7POWERPC\SQLEXPRESS'
database = 'NISSIM'
connection_string = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={database};Trusted_Connection=yes;"
app.config['SQLALCHEMY_DATABASE_URI'] = f'mssql+pyodbc:///?odbc_connect={connection_string}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False




# מפתח סודי עבור JWT
app.config['JWT_SECRET_KEY'] = 'super-secret-key'  # יש לשנות מפתח זה למשהו מאובטח

# אתחול SQLAlchemy ו-JWT
db = SQLAlchemy(app)
jwt = JWTManager(app)



@app.route('/')
def serve_html():
    # מחזיר את קובץ ה-HTML הראשי
    return send_from_directory(os.path.dirname(os.path.abspath(__file__)), 'index.html')



# הגדרת מודלים לטבלאות במסד הנתונים
class User(db.Model):
    __tablename__ = 'Users'
    UserID = db.Column(db.Integer, primary_key=True)
    id = db.Column(db.Integer)
    username = db.Column(db.String(50), nullable=False, unique=True)
    password = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(100), nullable=False, unique=True)
    role = db.Column(db.String(20), default='user')  # ברירת מחדל: משתמש רגיל
    CreatedAt = db.Column(db.DateTime, default=datetime.utcnow)

class Song(db.Model):
    __tablename__ = 'Songs'
    SongID = db.Column(db.Integer, primary_key=True)
    SongName = db.Column(db.String(100), nullable=False)
    ArtistName = db.Column(db.String(100), nullable=False)
    Genre = db.Column(db.String(50))
    ReleaseDate = db.Column(db.DateTime)
    Duration = db.Column(db.Integer)  # Duration in seconds

class DownloadHistory(db.Model):
    __tablename__ = 'DownloadHistory'
    DownloadID = db.Column(db.Integer, primary_key=True)
    UserID = db.Column(db.Integer, db.ForeignKey('Users.UserID'), nullable=False)
    SongID = db.Column(db.Integer, db.ForeignKey('Songs.SongID'), nullable=False)
    DownloadDate = db.Column(db.DateTime, default=datetime.utcnow)
    FilePath = db.Column(db.String(255), nullable=False)  # עמודה חדשה לשמירת נתיב הקובץ


class SearchHistory(db.Model):
    __tablename__ = 'SearchHistory'
    SearchID = db.Column(db.Integer, primary_key=True)
    UserID = db.Column(db.Integer, db.ForeignKey('Users.UserID'), nullable=False)
    SearchTerm = db.Column(db.String(100), nullable=False)
    SearchDate = db.Column(db.DateTime, default=datetime.utcnow)

class SearchStatistics(db.Model):
    __tablename__ = 'SearchStatistics'
    StatID = db.Column(db.Integer, primary_key=True)
    SongID = db.Column(db.Integer, db.ForeignKey('Songs.SongID'), nullable=False)
    SearchCount = db.Column(db.Integer, default=0)

###
class ActiveSession(db.Model):
    __tablename__ = 'ActiveSessions'
    SessionID = db.Column(db.Integer, primary_key=True)
    UserID = db.Column(db.Integer, db.ForeignKey('Users.UserID'), nullable=False)
    LoginTime = db.Column(db.DateTime, default=datetime.utcnow)
    LastActivityTime = db.Column(db.DateTime, default=datetime.utcnow)
    IsActive = db.Column(db.Boolean, default=True)

    user = db.relationship('User', backref=db.backref('active_sessions', lazy=True))


###

# יצירת טבלאות בבסיס הנתונים אם הן לא קיימות
with app.app_context():
    db.create_all()



# נתיב לרישום משתמשים
@app.route('/auth/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    email = data.get('email')


    # בדיקה אם המשתמש כבר קיים
    if User.query.filter_by(email=email).first():
        return jsonify({'message': 'User already exists'}), 400

    # שמירת הסיסמה כ-Hash
    hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

    # יצירת משתמש חדש
    new_user = User(username=username, email=email, password=hashed_password)
    db.session.add(new_user)
    db.session.commit()
    
    return jsonify({'message': 'נרשמת בהצלחה'}), 201

# עדכון נתיב ההתחברות כדי להחזיר שם משתמש וסטטוס
@app.route('/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    # חיפוש המשתמש לפי הדוא"ל
    user = User.query.filter_by(email=email).first()

    # בדיקת הסיסמה
    if not user or not check_password_hash(user.password, password):
        return jsonify({'message': 'Invalid credentials'}), 401

    # קבלת ה-UserID
    UserID = user.UserID

    # יצירת טוקן גישה (JWT)
    access_token = create_access_token(identity=UserID)  # type: ignore
    
    # החזרת שם המשתמש והסטטוס בנוסף לטוקן הגישה
    return jsonify({
        'access_token': access_token,
        'username': user.username
    })

# נתיב לקבלת פרטי המשתמש המחובר (JWT חובה)
@app.route('/auth/me', methods=['GET'])
@jwt_required()
def get_current_user():
    UserID = get_jwt_identity()
    user = User.query.get(UserID)
    
    if not user:
        return jsonify({'message': 'User not found'}), 404
    
    return jsonify({
        'UserID': user.UserID,
        'username': user.username,
        'email': user.email
        # 'role': user.role
    })


# שמירת תוצאות חיפוש ב-Cache
search_cache = {}

# פונקציה לחיפוש ב-YouTube ושמירת נתונים במסד
def search_youtube(query, UserID):
    if query in search_cache:
        return search_cache[query]

    ydl_opts = {
        'quiet': True,
        'skip_download': True,
        'default_search': 'ytsearch10',
        'format': 'bestaudio/best',
        'noplaylist': True,
    }

    with YoutubeDL(ydl_opts) as ydl:
        result = ydl.extract_info(query, download=False)

    results = []

    with app.app_context():  # הוספת הקשר אפליקציה
        for video in result['entries'][:25]:
            song_duration = int(video['duration'])  # קבלת זמן השיר
            song = Song.query.filter_by(SongName=f"r{video['title']}", ArtistName=video['uploader']).first()

            if not song:
                # הוספת שיר חדש אם לא קיים
                song = Song(SongName=video['title'], ArtistName=video['uploader'], Duration=song_duration)
                db.session.add(song)

            results.append({"title": video["title"], "url": video["webpage_url"], "thumbnail": video.get("thumbnail")})

            # עדכון הסטטיסטיקה של החיפוש
            stat = SearchStatistics.query.filter_by(SongID=song.SongID).first()
            if stat:
                stat.SearchCount += 1
            else:
                new_stat = SearchStatistics(SongID=song.SongID, SearchCount=1)
                db.session.add(new_stat)

        # קריאה לפונקציה לשמירת היסטוריית חיפושים
        if UserID:  # השתמש בשם החדש
            save_search_history(UserID, query, datetime)

        db.session.commit()  # שמירת כל השינויים

    search_cache[query] = results  # שמירת תוצאות ב-Cache
    return results

# פונקציה לשמירת היסטוריית חיפושים בבסיס הנתונים
def save_search_history(UserID, SearchTerm,datetime):
    try:
        with app.app_context():
            # יצירת רשומה חדשה בהיסטוריית החיפושים
            new_search = SearchHistory(UserID=UserID, SearchTerm=SearchTerm, SearchDate=datetime.utcnow())
            db.session.add(new_search)
            db.session.commit()
            print(f"Search term '{SearchTerm}' saved for user {UserID}")
    except Exception as e:
        print(f"Error saving search history: {str(e)}")

# פונקציה להורדת וידאו מ-YouTube כקובץ MP3 ושמירת ההיסטוריה במסד
def download_youtube_video_as_mp3(url, title, output_path, user_id=None):
    try:
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(output_path, f"{title}.mp4"),
            'quiet': True,
        }

        with YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            video_file = ydl.prepare_filename(info_dict)

        if not os.path.exists(video_file):
            return f"שגיאה: הקובץ {video_file} לא נשמר."

        print(f"Saved video file: {video_file}")

        try:
            audio_output_path = os.path.join(output_path, f"{title}.mp3")
            with AudioFileClip(video_file) as audio_clip:
                audio_clip.write_audiofile(audio_output_path)
            os.remove(video_file)
            print(f"Converted video to MP3 and removed original file: {video_file}")

            # שמירת היסטוריית ההורדה
            with app.app_context():  # הוספת הקשר אפליקציה
                song = Song.query.filter_by(SongName=title).first()
                if not song:
                    song = Song(SongName=title)
                    db.session.add(song)
                    db.session.commit()

                if user_id:
                    download_entry = DownloadHistory(UserID=user_id, SongID=song.SongID,FilePath=audio_output_path)
                    db.session.add(download_entry)

                db.session.commit()  # שמירת השינויים

        except Exception as e:
            return f"שגיאה בהמרה: {str(e)}"

    except Exception as e:
        return str(e)

    return None
# מסלול לחיפוש YouTube
@app.route('/search_youtube', methods=['POST'])
@jwt_required()  # מאמת את הטוקן הנוכחי
def search_youtube_route():
    data = request.get_json()

    # קבלת הנתונים מהבקשה
    query = data.get('query')
    user_id = data.get('userID')  # קבלת ה-userID מהבקשה
    UserID = get_jwt_identity()
    user = User.query.get(UserID)
    # בדיקה שהנתונים קיימים
    if not query or not user_id:
        return jsonify({"error": "Missing query or user ID"}), 400

    # קבלת ה-user ID מהטוקן
    user_id_from_token = get_jwt_identity()  # חילוץ ה-user ID מהטוקן

    # בדיקה שה-userID מהבקשה תואם ל-userID מהטוקן
    if user_id != user_id_from_token:
        return jsonify({"error": "Unauthorized user ID"}), 403

    try:
        # קריאה לפונקציה לחיפוש ביוטיוב
        results = search_youtube(query, user_id)
        return jsonify({"results": results}), 200  # החזרת התוצאות ללקוח
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# מסלול לחיפוש שירים ב-YouTube
@app.route('/search')
@jwt_required()
def search():
    UserID = get_jwt_identity()  # לזהות את המשתמש המחובר לפי ה-JWT
    user = User.query.get(UserID)

    print(UserID)  # הדפסת ה-UserID לבדיקה
    query = request.args.get('query')
    
    # חיפוש ב-YouTube עם השאילתא שנמסרה
    results = search_youtube(query, UserID)  # העברת UserID לפונקציה לחיפוש
    
    # # שמירת היסטוריית החיפוש אם ה-UserID קיים
    # if UserID:
    #     save_search_history(UserID, query, datetime)

    return jsonify(results)

# מסלול להורדת שירים
@app.route('/download')
@jwt_required()
def download():
    UserID = get_jwt_identity()
    url = request.args.get('url')
    title = request.args.get('title')
    
    output_path = r"C:\Users\user\OneDrive\שולחן העבודה\שירים גיבוי\הורדות שלי\downloads"  # עדכון הנתיב לנתיב שלך
    os.makedirs(output_path, exist_ok=True)

    # הפעלת הורדה בתהליכון נפרד (Thread)
    download_thread = threading.Thread(target=download_and_notify, args=(url, title, output_path, UserID))
    download_thread.start()
    
    return jsonify({"success": True, "message": "ההורדה החלה ברקע."})

# פונקציה להורדה והודעה
def download_and_notify(url, title, output_path, UserID=None):
    error = download_youtube_video_as_mp3(url, title, output_path, UserID)
    if (error):
        print(f"Error during download: {error}")
    else:
        print("Download completed successfully.")

# מסלול להצגת היסטוריית הורדות
@app.route('/download-history')
@jwt_required()
def download_history():
    UserID = get_jwt_identity()  # לזהות את המשתמש המחובר לפי ה-JWT
    downloads = DownloadHistory.query.filter_by(UserID=UserID).all()  # קבלת כל ההורדות של המשתמש
    
    download_list = []
    for download in downloads:
        song = Song.query.get(download.SongID)  # קבלת פרטי השיר מההורדה
        download_list.append({
            'DownloadID': download.DownloadID,
            'SongName': song.SongName,
            'ArtistName': song.ArtistName,
            'DownloadDate': download.DownloadDate.strftime('%Y-%m-%d %H:%M:%S'),  # פורמט התאריך
        })
    
    return jsonify(download_list)  # החזרת רשימת ההורדות בפורמט JSON


# מסלול להצגת היסטוריית חיפושים
@app.route('/search-history')
@jwt_required()
def search_history():
    UserID = get_jwt_identity()  # לזהות את המשתמש המחובר לפי ה-JWT
    searches = SearchHistory.query.filter_by(UserID=UserID).all()  # קבלת כל החיפושים של המשתמש
    
    search_list = []
    for search in searches:
        search_list.append({
            'SearchID': search.SearchID,
            'SearchTerm': search.SearchTerm,
            'SearchDate': search.SearchDate.strftime('%Y-%m-%d %H:%M:%S'),  # פורמט התאריך
        })
    
    return jsonify(search_list)  # החזרת רשימת החיפושים בפורמט JSON

import os
from flask import jsonify, send_from_directory
from flask_jwt_extended import jwt_required, get_jwt_identity

# פונקציה למחיקת קובץ פיזי מהשרת
def remove_physical_file(file_path):
    """פונקציה למחיקת קובץ פיזי"""
    if os.path.exists(file_path):
        os.remove(file_path)
        return True
    return False

# מסלול למחיקת הורדה מהיסטוריית ההורדות וגם מהשרת
@app.route('/delete-download/<int:download_id>', methods=['DELETE'])
@jwt_required()
def delete_download(download_id):
    UserID = get_jwt_identity()  # לזהות את המשתמש המחובר לפי ה-JWT
    download = DownloadHistory.query.filter_by(DownloadID=download_id, UserID=UserID).first()

    if download:
        # קריאה לפונקציה למחיקת הקובץ הפיזי
        if remove_physical_file(download.FilePath):
            db.session.delete(download)
            db.session.commit()
            return jsonify({'message': 'ההורדה נמחקה בהצלחה והקובץ הפיזי נמחק'}), 200
        else:
            return jsonify({'error': 'לא ניתן למחוק את הקובץ הפיזי'}), 500
    else:
        return jsonify({'error': 'ההורדה לא נמצאה או אין לך הרשאה למחוק אותה'}), 404


# מסלול להשמעת שיר כל עוד הוא קיים על השרת
@app.route('/play_song/<int:download_id>')
@jwt_required()
def play_song(download_id):
    UserID = get_jwt_identity()  # לזהות את המשתמש המחובר לפי ה-JWT
    download_entry = DownloadHistory.query.filter_by(DownloadID=download_id, UserID=UserID).first()
    
    if not download_entry:
        return jsonify({"error": "Download not found"}), 404

    # בדוק אם הקובץ קיים על השרת
    if os.path.exists(download_entry.FilePath):
        # שלח את השיר מהמיקום הפיזי שלו
        return send_from_directory(os.path.dirname(download_entry.FilePath), os.path.basename(download_entry.FilePath))
    else:
        return jsonify({"error": "הקובץ לא נמצא על השרת"}), 404


# מסלול למחיקת מונח חיפוש מהיסטוריית החיפושים
@app.route('/delete-search/<int:search_id>', methods=['DELETE'])
@jwt_required()
def delete_search(search_id):
    UserID = get_jwt_identity()  # לזהות את המשתמש המחובר לפי ה-JWT
    search = SearchHistory.query.filter_by(SearchID=search_id, UserID=UserID).first()

    if search:
        db.session.delete(search)
        db.session.commit()
        return jsonify({'message': 'החיפוש נמחק בהצלחה'}), 200
    else:
        return jsonify({'error': 'החיפוש לא נמצא או אין לך הרשאה למחוק אותו'}), 404



# # מנהל


@app.route('/package_songs', methods=['POST'])
@jwt_required()
def package_songs():
    data = request.get_json()
    folder_name = data.get('folder_name')  # קבלת שם התקייה מהבקשה
    user_id = get_jwt_identity()  # קבלת ה-UserID
    
    if not folder_name:
        return jsonify({'error': 'Missing folder name'}), 400

    try:
        # מיקום התקייה לשירים על ה-Desktop
        desktop_path = os.path.join(os.path.join(os.environ['USERPROFILE']), 'OneDrive', 'שולחן העבודה')
        target_folder = os.path.join(desktop_path, folder_name)

        # בדיקת יצירת תקייה
        if not os.path.exists(target_folder):
            os.makedirs(target_folder)
            print(f"Folder created: {target_folder}")
        else:
            print(f"Folder already exists: {target_folder}")

        # אחזור השירים של המשתמש
        songs = DownloadHistory.query.filter_by(UserID=user_id).all()

        if not songs:
            return jsonify({'error': 'No songs found for the user'}), 404

        # העתקת כל קובץ השיר לתקייה ומחיקה מהתקייה המקורית והבסיס נתונים
        for song in songs:
            song_path = song.FilePath
            if os.path.exists(song_path):
                # העתקה לתקיית היעד
                shutil.copy(song_path, target_folder)
                print(f"Copied song: {song_path} to {target_folder}")
                
                # מחיקת הקובץ המקורי
                os.remove(song_path)
                print(f"Deleted song: {song_path}")

                # מחיקת השיר מהבסיס נתונים
                db.session.delete(song)

            else:
                print(f"Song not found: {song_path}")

        # שמירת השינויים בבסיס נתונים
        db.session.commit()

        return jsonify({'message': 'Songs packaged and deleted successfully', 'folder_path': target_folder}), 200

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': str(e)}), 500

# # נתיב להצגת לוח המנהלה
# @app.route('/static/admin_dashboard', methods=['GET'])
# @jwt_required()
# def admin_dashboard():
#     current_user = get_jwt_identity()
#     user = User.query.get(current_user)
#     if user.role != 'admin':
#         return jsonify({'message': 'Access forbidden: Admins only'}), 403

#     # קבלת כל המשתמשים והשירים
#     users = User.query.all()
#     songs = Song.query.all()
#     return render_template('admin_dashboard.html', users=users, songs=songs)

# # נתיב להוספת משתמש חדש
# @app.route('/admin/add_user', methods=['POST'])
# @jwt_required()
# def add_user():
#     current_user = get_jwt_identity()
#     user = User.query.get(current_user)
#     if user.role != 'admin':
#         return jsonify({'message': 'Access forbidden: Admins only'}), 403

#     data = request.get_json()
#     username = data.get('username')
#     password = data.get('password')
#     email = data.get('email')
#     role = data.get('role', 'user')

#     hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
#     new_user = User(username=username, email=email, password=hashed_password, role=role)
#     db.session.add(new_user)
#     db.session.commit()
    
#     return jsonify({'message': 'User added successfully'}), 201

# # נתיב למחיקת משתמש
# @app.route('/admin/delete_user/<int:user_id>', methods=['DELETE'])
# @jwt_required()
# def delete_user(user_id):
#     current_user = get_jwt_identity()
#     user = User.query.get(current_user)
#     if user.role != 'admin':
#         return jsonify({'message': 'Access forbidden: Admins only'}), 403

#     user_to_delete = User.query.get(user_id)
#     if not user_to_delete:
#         return jsonify({'message': 'User not found'}), 404
    
#     db.session.delete(user_to_delete)
#     db.session.commit()
    
#     return jsonify({'message': 'User deleted successfully'}), 200

# # נתיב להוספת שיר חדש
# @app.route('/admin/add_song', methods=['POST'])
# @jwt_required()
# def add_song():
#     current_user = get_jwt_identity()
#     user = User.query.get(current_user)
#     if user.role != 'admin':
#         return jsonify({'message': 'Access forbidden: Admins only'}), 403

#     data = request.get_json()
#     song_name = data.get('song_name')
#     artist_name = data.get('artist_name')
#     genre = data.get('genre')
#     release_date = data.get('release_date')

#     new_song = Song(SongName=song_name, ArtistName=artist_name, Genre=genre, ReleaseDate=release_date)
#     db.session.add(new_song)
#     db.session.commit()

#     return jsonify({'message': 'Song added successfully'}), 201

# # נתיב למחיקת שיר
# @app.route('/admin/delete_song/<int:song_id>', methods=['DELETE'])
# @jwt_required()
# def delete_song(song_id):
#     current_user = get_jwt_identity()
#     user = User.query.get(current_user)
#     if user.role != 'admin':
#         return jsonify({'message': 'Access forbidden: Admins only'}), 403

#     song_to_delete = Song.query.get(song_id)
#     if not song_to_delete:
#         return jsonify({'message': 'Song not found'}), 404
    
#     db.session.delete(song_to_delete)
#     db.session.commit()
    
#     return jsonify({'message': 'Song deleted successfully'}), 200


# פונקציה לפתיחת הדפדפן אוטומטית בטעינת הממשק
def open_browser():
    webbrowser.open_new('http://localhost:5000/static/index.html')

# הרצת האפליקציה עם פתיחת דפדפן אוטומטית
if __name__ == '__main__':
    threading.Timer(1, open_browser).start()  # ממתין שנייה לפני פתיחת הדפדפן
    app.run(debug=True)
