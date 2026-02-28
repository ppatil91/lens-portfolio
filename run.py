import os
import uuid
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import json
from flask_socketio import SocketIO, emit, join_room, leave_room
from models import db, User, Photo, Comment, Message
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from PIL import Image
import pillow_heif

# Register HEIF opener to handle HEIC files disguised as JPEG from iPhones
# Apple wale hamesha alag hi chalte hain yaar... (Apple always has to be different...)
pillow_heif.register_heif_opener()

# Application Configuration
app = Flask(__name__)
# Bro please don't leak this key... phat jayegi
app.config['SECRET_KEY'] = 'your_super_secret_key_here' # Change this in production
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///lens_portfolio.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# File Upload Configuration
UPLOAD_FOLDER = os.path.join('static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'heic'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Initialize Plugins
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
socketio = SocketIO(app, cors_allowed_origins="*")

# --- SOCKET.IO EVENTS ---
# Yeh Socket magic hai for instant DMs!
@socketio.on('join')
def on_join(data):
    if current_user.is_authenticated:
        # Creating a VIP room just for this user
        room = f"user_{current_user.id}"
        join_room(room)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- ROUTES ---

@app.route('/')
def index():
    # Public landing page
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'register':
            full_name = request.form.get('full_name')
            email = request.form.get('email')
            password = request.form.get('password')
            
            if not full_name or not email or not password:
                flash('All fields are required', 'error')
                return redirect(url_for('login') + '?signup=true')
                
            if len(password) < 6:
                flash('Password must be at least 6 characters long', 'error')
                return redirect(url_for('login') + '?signup=true')
            
            if User.query.filter_by(email=email).first():
                # Array yaar, already hai yeh email (Oh man, this email already exists)
                flash('Email address already exists', 'error')
                return redirect(url_for('login') + '?signup=true')
                
            new_user = User(full_name=full_name, email=email)
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()
            
            login_user(new_user)
            return redirect(url_for('dashboard'))
            
        elif action == 'login':
            email = request.form.get('email')
            password = request.form.get('password')
            
            user = User.query.filter_by(email=email).first()
            if user and user.check_password(password):
                login_user(user)
                return redirect(url_for('dashboard'))
            else:
                # Galat password bro, wapas try kar
                flash('Invalid email or password', 'error')
                return redirect(url_for('login'))
                
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    # Pass the current user's stats to the template
    user_photos = Photo.query.filter_by(user_id=current_user.id).order_by(Photo.upload_date.desc()).all()
    total_views = sum(photo.views for photo in user_photos)
    total_likes = sum(photo.likes for photo in user_photos)
    
    # Get user's saved photos
    saved_photos = current_user.saved
    
    # Get Top 10 Photos for Chart.js
    top_photos = Photo.query.filter_by(user_id=current_user.id).order_by(Photo.views.desc()).limit(10).all()
    
    # Safely convert to JSON strings for embedding in script tag
    labels = json.dumps([p.title for p in top_photos])
    views_data = json.dumps([p.views for p in top_photos])
    likes_data = json.dumps([p.likes for p in top_photos])
    
    return render_template('dashboard.html', 
                           photos=user_photos, 
                           views=total_views, 
                           likes=total_likes,
                           saved_photos=saved_photos,
                           top_photos_labels=labels,
                           top_photos_views=views_data,
                           top_photos_likes=likes_data)
# Dashboard data bhejne ka kaam khatam! (Dashboard data sending is done!)

# --- SEARCH USERS ROUTE ---
@app.route('/search')
@login_required
def search():
    # Grab the search query from the URL (e.g., /search?q=Parth)
    query = request.args.get('q', '')
    
    if query:
        # ilike() makes the search case-insensitive (finds "parth", "Parth", "PARTH")
        # The % symbols mean the query can be anywhere in the name
        found_users = User.query.filter(User.full_name.ilike(f'%{query}%')).all()
    else:
        found_users = []
        
    return render_template('search.html', users=found_users, query=query)

# --- SETTINGS ROUTE ---
@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        # Grab the text data
        new_name = request.form.get('full_name')
        new_bio = request.form.get('bio')
        
        # --- NEW: Handle the Avatar Upload ---
        if 'profile_image' in request.files:
            file = request.files['profile_image']
            
            # If the user actually selected a file
            if file and file.filename != '':
                if allowed_file(file.filename):
                    # Secure the name and add a UUID to prevent overwriting
                    original_filename = secure_filename(file.filename)
                    unique_filename = f"avatar_{uuid.uuid4().hex}_{original_filename}"
                    
                    # Save it to the static/uploads folder
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                    file.save(file_path)
                    
                    # Update the database record with the new filename
                    current_user.profile_image = unique_filename
                else:
                    flash('Invalid image format for avatar. Allowed types are: png, jpg, jpeg, gif, webp, heic', 'error')
                    return redirect(url_for('settings'))
        
        # Update text fields
        current_user.full_name = new_name
        current_user.bio = new_bio
        
        db.session.commit()
        return redirect(url_for('settings'))
        
    # If it's a GET request, just render the page
    return render_template('settings.html')

@app.route('/portfolio/<int:user_id>')
def portfolio(user_id):
    # Public masonry grid page
    user = User.query.get_or_404(user_id)
    photos = Photo.query.filter_by(user_id=user.id).order_by(Photo.upload_date.desc()).all()
    
    # Calculate total views and likes for the user
    total_views = sum(photo.views for photo in photos)
    total_likes = sum(photo.likes for photo in photos)
    
    return render_template('portfolio.html', user=user, photos=photos, views=total_views, likes=total_likes)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    if request.method == 'POST':
        if 'photo' not in request.files:
            flash('No file part', 'error')
            return redirect(request.url)
        file = request.files['photo']
        if file.filename == '':
            flash('No selected file', 'error')
            return redirect(request.url)
            
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            from datetime import datetime
            base, ext = os.path.splitext(filename)
            unique_filename = f"{base}_{int(datetime.now().timestamp())}{ext}"
            
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            file.save(file_path)
            
            # --- REALISTIC UPGRADE: Image Compression & Resize ---
            try:
                img = Image.open(file_path)
                
                # Convert HEIC or non-RGB (like transparent PNG) to RGB
                if img.format == 'HEIF' or img.mode != 'RGB':
                    img = img.convert('RGB')
                    
                # Resize if the image is massive (e.g., limit width to 1920px for HD viewing)
                max_width = 1920
                if img.width > max_width:
                    ratio = max_width / img.width
                    new_height = int(img.height * ratio)
                    img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
                
                # If it was an HEIC, change the extension to jpeg
                if unique_filename.lower().endswith('.heic'):
                    base = os.path.splitext(unique_filename)[0]
                    new_filename = f"{base}.jpeg"
                    new_file_path = os.path.join(app.config['UPLOAD_FOLDER'], new_filename)
                    # Save with optimized compression
                    img.save(new_file_path, optimize=True, quality=85)
                    os.remove(file_path)
                    unique_filename = new_filename
                else:
                    # Save with optimized compression over the original file
                    img.save(file_path, "JPEG", optimize=True, quality=85)
                    
            except Exception as e:
                print(f"Image conversion failed: {e}")
                # Clean up the broken file
                if os.path.exists(file_path):
                    os.remove(file_path)
                flash('The uploaded file appears to be corrupted or invalid.', 'error')
                return redirect(request.url)
            
            new_photo = Photo(
                title=request.form.get('title'),
                category=request.form.get('category'),
                description=request.form.get('description'),
                location=request.form.get('location'),
                tags=request.form.get('tags'),
                filename=unique_filename,
                user_id=current_user.id
            )
            db.session.add(new_photo)
            db.session.commit()
            
            flash('Photo uploaded successfully!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Allowed file types are png, jpg, jpeg, gif, webp', 'error')
            
    return render_template('upload.html')

@app.route('/photo/<int:photo_id>')
def view_photo(photo_id):
    photo = Photo.query.get_or_404(photo_id)
    # Increment view count
    photo.views += 1
    db.session.commit()
    
    # Check if current user saved this photo
    is_saved = False
    if current_user.is_authenticated:
        is_saved = photo in current_user.saved
        
    return render_template('photo.html', photo=photo, is_saved=is_saved)

from flask import jsonify

@app.route('/like/<int:photo_id>', methods=['POST'])
@login_required
def like_photo(photo_id):
    photo = Photo.query.get_or_404(photo_id)
    photo.likes += 1
    db.session.commit()
    return jsonify({'status': 'success', 'new_likes': photo.likes})

# --- COMMENT ROUTE ---
# Comments daalne ke liye function (Function to drop some comments)
@app.route('/comment/<int:photo_id>', methods=['POST'])
@login_required
def comment_photo(photo_id):
    photo = Photo.query.get_or_404(photo_id)
    content = request.form.get('content')
    
    if content and content.strip():
        # Acha comment haina?
        new_comment = Comment(content=content, user_id=current_user.id, photo_id=photo.id)
        db.session.add(new_comment)
        db.session.commit()
        flash('Comment added successfully!', 'success')
    else:
        # Khali comment nahi chalega re baba
        flash('Comment cannot be empty.', 'error')
        
    return redirect(url_for('view_photo', photo_id=photo.id))

# --- SAVE PHOTO ROUTE ---
@app.route('/save/<int:photo_id>', methods=['POST'])
@login_required
def save_photo(photo_id):
    photo = Photo.query.get_or_404(photo_id)
    
    if photo in current_user.saved:
        current_user.saved.remove(photo)
        status = 'unsaved'
    else:
        current_user.saved.append(photo)
        status = 'saved'
        
    db.session.commit()
    return jsonify({'status': 'success', 'action': status})

# --- CONNECT ROUTE ---
@app.route('/connect/<int:user_id>')
@login_required
def connect_user(user_id):
    user_to_connect = User.query.get_or_404(user_id)
    
    if user_to_connect == current_user:
        return redirect(url_for('portfolio', user_id=user_id))
        
    current_user.connect(user_to_connect)
    db.session.commit()
    
    return redirect(url_for('portfolio', user_id=user_id))

# --- DISCONNECT ROUTE ---
@app.route('/disconnect/<int:user_id>')
@login_required
def disconnect_user(user_id):
    user_to_disconnect = User.query.get_or_404(user_id)
    
    current_user.disconnect(user_to_disconnect)
    db.session.commit()
    
    return redirect(url_for('portfolio', user_id=user_id))

# --- DELETE PHOTO ROUTE ---
@app.route('/delete_photo/<int:photo_id>', methods=['POST'])
@login_required
def delete_photo(photo_id):
    photo = Photo.query.get_or_404(photo_id)
    
    # Ensure the user owns the photo
    if photo.user_id != current_user.id:
        # Returning a 403 Forbidden
        return "You do not have permission to delete this photo.", 403
        
    try:
        # Delete file from filesystem
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], photo.filename)
        if os.path.exists(file_path):
            os.remove(file_path)
            
        # Delete from database
        db.session.delete(photo)
        db.session.commit()
        flash('Photo deleted successfully.', 'success')
    except Exception as e:
        print(f"Error deleting photo: {e}")
        db.session.rollback()
        flash('An error occurred while deleting the photo.', 'error')
        
    return redirect(url_for('dashboard'))

# --- ERROR HANDLERS ---
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500

# --- HOME FEED ROUTE ---
@app.route('/feed')
@login_required
def feed():
    # 1. Get a list of IDs for everyone the current user follows
    followed_ids = [u.id for u in current_user.followed]
    
    # 2. Add the current user's own ID so their photos show up in their feed too
    followed_ids.append(current_user.id)
    
    # 3. Query the Photo table for any photo belonging to these IDs, newest first
    feed_photos = Photo.query.filter(Photo.user_id.in_(followed_ids)).order_by(Photo.upload_date.desc()).all()
    
    return render_template('feed.html', photos=feed_photos)

# --- EXPLORE ROUTE ---
@app.route('/explore')
def explore():
    # Get all photos globally
    photos = Photo.query.order_by(Photo.upload_date.desc()).all()
    
    # Extract unique tags across all photos to generate trending tags
    all_tags = set()
    for photo in photos:
        if photo.tags:
            # Assuming tags are comma-separated strings
            tags_list = [t.strip().lower() for t in photo.tags.split(',') if t.strip()]
            all_tags.update(tags_list)
            
    # Convert set back to sorted list for the template
    trending_tags = sorted(list(all_tags))
    
    # Basic categories we want to always show
    categories = ['Landscape', 'Portrait', 'Architecture', 'Nature', 'Street', 'Abstract']
    
    return render_template('explore.html', photos=photos, trending_tags=trending_tags, categories=categories)
# Explore logic done. Ab photo dhundho mst! (Explore logic done. Now browse awesome photos!)

# --- MESSAGES ROUTES ---

@app.route('/messages')
@login_required
def messages_inbox():
    # Get a list of all users the current user has sent or received messages from
    # Complex query to find distinct users... or we can do it in Python for simplicity
    
    # Let's get all messages involving the current user
    all_msgs = Message.query.filter(
        (Message.sender_id == current_user.id) | (Message.recipient_id == current_user.id)
    ).order_by(Message.timestamp.desc()).all()
    
    # Group them by the *other* user to find recent conversations
    conversations = {}
    for msg in all_msgs:
        other_user = msg.recipient if msg.sender_id == current_user.id else msg.sender
        if other_user.id not in conversations:
            conversations[other_user.id] = {
                'user': other_user,
                'last_message': msg,
                'unread_count': 0
            }
        # Count unread messages sent TO the current user
        if msg.recipient_id == current_user.id and not msg.read:
            conversations[other_user.id]['unread_count'] += 1
            
    # Sort conversations by last message timestamp (already mostly sorted, but good to be certain)
    sorted_convos = sorted(conversations.values(), key=lambda x: x['last_message'].timestamp, reverse=True)
            
    return render_template('messages_inbox.html', conversations=sorted_convos)


@app.route('/messages/<int:user_id>', methods=['GET', 'POST'])
@login_required
def chat(user_id):
    other_user = User.query.get_or_404(user_id)
    
    if other_user.id == current_user.id:
        if request.headers.get('Accept') == 'application/json':
            # Khud se baatein matt kar pagal (Don't talk to yourself crazy person)
            return jsonify({'status': 'error', 'message': "You cannot message yourself."}), 400
        flash("You cannot message yourself.", "error")
        return redirect(url_for('messages_inbox'))
        
    if request.method == 'POST':
        # Check if the request is sending JSON data instead of form data
        if request.is_json:
            data = request.get_json()
            content = data.get('content')
        else:
            content = request.form.get('content')
            
        if content and content.strip():
            new_msg = Message(sender_id=current_user.id, recipient_id=other_user.id, content=content.strip())
            db.session.add(new_msg)
            db.session.commit()
            
            
            msg_data = {
                'content': new_msg.content,
                'timestamp': new_msg.timestamp.strftime('%I:%M %p'),
                'sender_id': current_user.id
            }
            
            # Emit back to recipient via web socket instantly
            # Zoom! Message gaya. (Zoom! Message sent.)
            socketio.emit('receive_message', msg_data, room=f"user_{other_user.id}")
            
            # If the request expects JSON, return the new message data
            if request.headers.get('Accept') == 'application/json' or request.is_json:
                return jsonify({
                    'status': 'success',
                    'message': msg_data
                })
            
    # Mark messages from other_user to current_user as read
    Message.query.filter_by(sender_id=other_user.id, recipient_id=current_user.id, read=False).update({'read': True})
    db.session.commit()
    
    # Fetch message history
    messages = Message.query.filter(
        ((Message.sender_id == current_user.id) & (Message.recipient_id == other_user.id)) |
        ((Message.sender_id == other_user.id) & (Message.recipient_id == current_user.id))
    ).order_by(Message.timestamp.asc()).all()
    
    return render_template('chat.html', other_user=other_user, messages=messages)

@app.route('/api/messages/<int:user_id>/recent')
@login_required
def api_recent_messages(user_id):
    """
    API endpoint for polling new messages.
    Expects a timestamp parameter `since` (Unix timestamp).
    """
    since_timestamp_str = request.args.get('since', 0)
    try:
        since_timestamp = float(since_timestamp_str)
        since_date = datetime.fromtimestamp(since_timestamp)
    except ValueError:
        return jsonify({'error': 'Invalid timestamp'}), 400
        
    # Find new messages FROM the other user TO the current user that were sent AFTER the timestamp
    new_messages = Message.query.filter(
        Message.sender_id == user_id,
        Message.recipient_id == current_user.id,
        Message.timestamp > since_date
    ).order_by(Message.timestamp.asc()).all()
    
    # Mark them as read immediately since they are being delivered
    if new_messages:
        for msg in new_messages:
            msg.read = True
        db.session.commit()
        
    messages_data = [{
        'id': msg.id,
        'content': msg.content,
        'timestamp': msg.timestamp.strftime('%I:%M %p'),
        'sender_id': msg.sender_id
    } for msg in new_messages]
    
    return jsonify({'messages': messages_data})

@app.context_processor
def inject_unread_count():
    if current_user.is_authenticated:
        count = Message.query.filter_by(recipient_id=current_user.id, read=False).count()
        return dict(unread_messages_count=count)
    return dict(unread_messages_count=0)


# Create tables before first request
with app.app_context():
    db.create_all()
    # Ensure upload directory exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

if __name__ == '__main__':
    socketio.run(app, debug=True, port=5000)