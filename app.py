import os
import logging
import requests
import jwt
import secrets
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv
import uuid

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev_secret_key_change_in_production")
app.config['SERVER_NAME'] = 'localhost:5000'  # Required for authlib redirect URIs
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
CORS(app)

# Initialize OAuth
oauth = OAuth(app)

# Load environment variables
load_dotenv()

# Google OAuth configuration
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")

# GitHub OAuth configuration
GITHUB_CLIENT_ID = os.environ.get("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = os.environ.get("GITHUB_CLIENT_SECRET")

# Register OAuth clients
oauth.register(
    name='google',
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

oauth.register(
    name='github',
    client_id=GITHUB_CLIENT_ID,
    client_secret=GITHUB_CLIENT_SECRET,
    access_token_url='https://github.com/login/oauth/access_token',
    authorize_url='https://github.com/login/oauth/authorize',
    api_base_url='https://api.github.com/',
    client_kwargs={'scope': 'user:email'}
)

# In-memory storage
users = {}
rooms = {
    'general': {
        'name': 'General',
        'messages': [],
        'created_by': 'system',
        'created_at': datetime.utcnow()
    },
    'random': {
        'name': 'Random',
        'messages': [],
        'created_by': 'system',
        'created_at': datetime.utcnow()
    }
}
private_messages = []

# Telegram configuration
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_telegram_message(message):
    """Send a message to Telegram"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        app.logger.warning("Telegram credentials not configured")
        return False
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }
        response = requests.post(url, data=data)
        return response.status_code == 200
    except Exception as e:
        app.logger.error(f"Failed to send Telegram message: {e}")
        return False

def login_required(f):
    """Decorator to require login"""
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash('Please log in to continue', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

def get_current_user():
    """Get current logged in user data"""
    username = session.get('username')
    if username and username in users:
        return {'username': username, **users[username]}
    return None

@app.route('/')
@login_required
def index():
    """Main chat interface"""
    current_room_slug = request.args.get('room', 'general')
    if current_room_slug not in rooms:
        current_room_slug = 'general'
    current_room = {
        'slug': current_room_slug,
        **rooms[current_room_slug]
    }
    rooms_list = []
    for slug, room_data in rooms.items():
        rooms_list.append({
            'slug': slug,
            'name': room_data['name'],
            'message_count': len(room_data['messages'])
        })
    user = get_current_user()
    return render_template('index.html',
                         rooms=rooms_list,
                         current_room=current_room,
                         nickname=user.get('name', user['username']) if user else 'Guest')

@app.route('/login')
def login():
    """Login page"""
    if 'username' in session:
        return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/auth/google')
def google_auth():
    """Initiate Google OAuth flow"""
    try:
        # Generate a nonce for OpenID Connect
        nonce = secrets.token_urlsafe(32)
        session['google_nonce'] = nonce
        redirect_uri = url_for('google_callback', _external=True)
        print(f"Redirecting to Google auth URL with redirect_uri: {redirect_uri}, nonce: {nonce}")
        return oauth.google.authorize_redirect(redirect_uri, nonce=nonce)
    except Exception as e:
        app.logger.error(f"Error initiating Google OAuth: {str(e)}", exc_info=True)
        flash(f'Failed to start Google authentication: {str(e)}', 'error')
        return redirect(url_for('login'))

@app.route('/auth/google/callback')
def google_callback():
    code = request.args.get('code')
    token_data = {
        'code': code,
        'client_id': GOOGLE_CLIENT_ID,
        'client_secret': GOOGLE_CLIENT_SECRET,
        'redirect_uri': url_for('google_callback', _external=True),
        'grant_type': 'authorization_code'
    }
    token_res = requests.post('https://oauth2.googleapis.com/token', data=token_data)
    token_json = token_res.json()
    access_token = token_json.get('access_token')

    user_res = requests.get(
        'https://www.googleapis.com/oauth2/v2/userinfo',
        headers={'Authorization': f'Bearer {access_token}'}
    )
    user_info = user_res.json()

    google_id = user_info.get('id')
    name = user_info.get('name')
    email = user_info.get('email')
    picture = user_info.get('picture')
    username = email.split('@')[0]

    existing_user = next(
        (u for u, data in users.items() if data.get('provider') == 'google' and data.get('provider_id') == google_id),
        None
    )

    if existing_user:
        users[existing_user]['last_seen'] = datetime.utcnow()
        session['username'] = existing_user
        session['nickname'] = users[existing_user].get('username', existing_user)
    else:
        if username in users:
            username = f"{username}_{google_id[:4]}"
        users[username] = {
            'name': username,
            'email': email,
            'picture': picture,
            'provider': 'google',
            'provider_id': google_id,
            'created_at': datetime.utcnow(),
            'last_seen': datetime.utcnow()
        }
        session['username'] = username
        session['nickname'] = name

    return redirect(url_for('index'))


@app.route('/auth/github')
def github_auth():
    """Initiate GitHub OAuth flow"""
    try:
        redirect_uri = url_for('github_callback', _external=True)
        print(f"Redirecting to GitHub auth URL with redirect_uri: {redirect_uri}")
        return oauth.github.authorize_redirect(redirect_uri)
    except Exception as e:
        app.logger.error(f"Error initiating GitHub OAuth: {str(e)}", exc_info=True)
        flash(f'Failed to start GitHub authentication: {str(e)}', 'error')
        return redirect(url_for('login'))

@app.route('/auth/github/callback')
def github_callback():
    code = request.args.get('code')
    if not code:
        return "Missing code", 400

    # Step 1: Exchange code for access token
    token_res = requests.post(
        'https://github.com/login/oauth/access_token',
        data={
            'client_id': GITHUB_CLIENT_ID,
            'client_secret': GITHUB_CLIENT_SECRET,
            'code': code,
            'redirect_uri': url_for('github_callback', _external=True)  # MUST match GitHub App settings
        },
        headers={'Accept': 'application/json'}
    )
    token_json = token_res.json()

    access_token = token_json.get('access_token')
    if not access_token:
        return f"Error getting token: {token_json}", 400

    # Step 2: Use the access token to get user info
    user_res = requests.get(
        'https://api.github.com/user',

        headers={'Authorization': f'token {access_token}'}
    )
    user_info = user_res.json()

    if 'message' in user_info and user_info['message'] == 'Bad credentials':
        return f"GitHub error: {user_info}", 401

    # Step 3: Get email if missing
    email = user_info.get('email')
    if not email:
        email_res = requests.get(
            'https://api.github.com/user/emails',
            headers={'Authorization': f'token {access_token}'}
        )
        emails = email_res.json()
        if isinstance(emails, list) and emails:
            primary_email = next((e['email'] for e in emails if e.get('primary')), emails[0]['email'])
            email = primary_email

    github_id = str(user_info.get('id'))
    name = user_info.get('name') or user_info.get('login')
    username = user_info.get('login')

    existing_user = next(
        (u for u, data in users.items() if data.get('provider') == 'github' and data.get('provider_id') == github_id),
        None
    )

    if existing_user:
        users[existing_user]['last_seen'] = datetime.utcnow()
        session['username'] = existing_user
        session['nickname'] = users[existing_user].get('name', existing_user)
    else:
        if username in users:
            username = f"{username}_{github_id[:4]}"
        users[username] = {
            'name': name,
            'email': email,
            'picture': user_info.get('avatar_url'),
            'provider': 'github',
            'provider_id': github_id,
            'created_at': datetime.utcnow(),
            'last_seen': datetime.utcnow()
        }
        session['username'] = username
        session['nickname'] = name

    return redirect(url_for('index'))


@app.route('/logout')
@login_required
def logout():
    """User logout"""
    user = get_current_user()
    if user:
        message = f"🚪 <b>Chat Logout</b>\n" \
                  f"👤 Username: {user['username']}\n" \
                  f"📧 Email: {user.get('email', 'N/A')}\n" \
                  f"🌐 IP: {request.remote_addr}\n" \
                  f"⏰ Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
        send_telegram_message(message)
    session.pop('username', None)
    session.pop('google_nonce', None)
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))

@app.route('/api/messages/<room_slug>')
@login_required
def get_messages(room_slug):
    """Get messages for a specific room"""
    if room_slug not in rooms:
        return jsonify({'error': 'Room not found'}), 404
    
    messages = rooms[room_slug]['messages'][-50:]  # Last 50 messages
    
    return jsonify({
        'messages': messages,
        'room_name': rooms[room_slug]['name']
    })

@app.route('/api/send_message', methods=['POST'])
@login_required
def send_message():
    """Send a message to a room"""
    data = request.get_json()
    room_slug = data.get('room_id')
    message_text = data.get('message', '').strip()
    
    if not room_slug or not message_text:
        return jsonify({'error': 'Room ID and message are required'}), 400
    
    if room_slug not in rooms:
        return jsonify({'error': 'Room not found'}), 404
    
    user = get_current_user()
    message_id = str(uuid.uuid4())
    timestamp = datetime.utcnow()
    
    message = {
        'id': message_id,
        'user_id': user['username'],
        'nickname': user['username'],
        'message': message_text,
        'timestamp': timestamp.isoformat(),
        'formatted_time': timestamp.strftime('%H:%M'),
        'edited': False
    }
    
    rooms[room_slug]['messages'].append(message)
    
    # Update user last seen
    users[user['username']]['last_seen'] = timestamp
    
    return jsonify({
        'success': True,
        'message': message
    })

@app.route('/api/edit_message', methods=['POST'])
@login_required
def edit_message():
    """Edit an existing message"""
    data = request.get_json()
    message_id = data.get('message_id')
    new_text = data.get('message', '').strip()
    room_slug = data.get('room_id')
    
    if not message_id or not new_text or not room_slug:
        return jsonify({'error': 'Message ID, new text, and room ID are required'}), 400
    
    if room_slug not in rooms:
        return jsonify({'error': 'Room not found'}), 404
    
    user = get_current_user()
    
    # Find and update the message
    for message in rooms[room_slug]['messages']:
        if message['id'] == message_id and message['user_id'] == user['username']:
            message['message'] = new_text
            message['edited'] = True
            message['edited_at'] = datetime.utcnow().isoformat()
            
            return jsonify({
                'success': True,
                'message': message
            })
    
    return jsonify({'error': 'Message not found or not authorized'}), 404

@app.route('/api/delete_message', methods=['POST'])
@login_required
def delete_message():
    """Delete a message"""
    data = request.get_json()
    message_id = data.get('message_id')
    room_slug = data.get('room_id')
    
    if not message_id or not room_slug:
        return jsonify({'error': 'Message ID and room ID are required'}), 400
    
    if room_slug not in rooms:
        return jsonify({'error': 'Room not found'}), 404
    
    user = get_current_user()
    
    # Find and remove the message
    messages = rooms[room_slug]['messages']
    for i, message in enumerate(messages):
        if message['id'] == message_id and message['user_id'] == user['username']:
            messages.pop(i)
            return jsonify({'success': True})
    
    return jsonify({'error': 'Message not found or not authorized'}), 404

@app.route('/api/create_room', methods=['POST'])
@login_required
def create_room():
    """Create a new chat room"""
    data = request.get_json()
    room_name = data.get('room_name', '').strip()
    
    if not room_name:
        return jsonify({'error': 'Room name is required'}), 400
    
    room_slug = room_name.lower().replace(' ', '_').replace('-', '_')
    room_slug = ''.join(c for c in room_slug if c.isalnum() or c == '_')
    
    if room_slug in rooms:
        return jsonify({'error': 'Room already exists'}), 400
    
    user = get_current_user()
    
    rooms[room_slug] = {
        'name': room_name,
        'messages': [],
        'created_by': user['username'],
        'created_at': datetime.utcnow()
    }
    
    return jsonify({'success': True, 'room_id': room_slug, 'room_name': room_name})

@app.route('/api/rooms')
@login_required
def get_rooms():
    """Get list of all rooms"""
    room_list = []
    
    for slug, room_data in rooms.items():
        room_list.append({
            'id': slug,
            'name': room_data['name'],
            'message_count': len(room_data['messages'])
        })
    
    return jsonify({'rooms': room_list})

@app.route('/api/send_private_message', methods=['POST'])
@login_required
def send_private_message():
    """Send a private message to another user"""
    data = request.get_json()
    recipient_username = data.get('recipient', '').strip()
    message_text = data.get('message', '').strip()
    
    if not recipient_username or not message_text:
        return jsonify({'error': 'Recipient and message are required'}), 400
    
    if recipient_username not in users:
        return jsonify({'error': 'User not found'}), 404
    
    user = get_current_user()
    message_id = str(uuid.uuid4())
    timestamp = datetime.utcnow()
    
    message = {
        'id': message_id,
        'from_user_id': user['username'],
        'from_nickname': user['username'],
        'to_user_id': recipient_username,
        'to_nickname': recipient_username,
        'message': message_text,
        'timestamp': timestamp.isoformat(),
        'formatted_time': timestamp.strftime('%H:%M'),
        'is_private': True
    }
    
    private_messages.append(message)
    
    return jsonify({
        'success': True,
        'message': message
    })

@app.route('/api/private_messages')
@login_required
def get_private_messages():
    """Get private messages for the current user"""
    user = get_current_user()
    
    # Filter messages where user is sender or recipient
    user_messages = [
        msg for msg in private_messages 
        if msg['from_user_id'] == user['username'] or msg['to_user_id'] == user['username']
    ]
    
    # Sort by timestamp and get last 50
    user_messages.sort(key=lambda x: x['timestamp'])
    user_messages = user_messages[-50:]
    
    return jsonify({'messages': user_messages})

# Health check endpoint
@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'users_count': len(users),
        'rooms_count': len(rooms),
        'total_messages': sum(len(room['messages']) for room in rooms.values())
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)