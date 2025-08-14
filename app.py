import os
import logging
import requests
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix
import uuid

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev_secret_key_change_in_production")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Enable CORS
CORS(app)

# Telegram Bot configuration
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# In-memory storage (resets when server restarts)
# In production, you might want to use Redis or another external storage
users = {}  # username: {password, email, first_name, last_name, telegram_username, created_at, last_seen}
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
private_messages = []  # List of private messages between users

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
            return redirect(url_for('login', next=request.url))
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
    
    # Ensure the room exists
    if current_room_slug not in rooms:
        current_room_slug = 'general'
    
    current_room = {
        'slug': current_room_slug,
        **rooms[current_room_slug]
    }
    
    # Format rooms for template
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
                           nickname=user['username'] if user else 'Guest')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Simple login with just username - sends credentials to Telegram"""
    if 'username' in session:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        
        if not username:
            flash('Username is required', 'error')
            return render_template('login_simple.html')
        
        # Store user data in memory (no password verification)
        if username not in users:
            users[username] = {
                'email': email,
                'created_at': datetime.utcnow(),
                'last_seen': datetime.utcnow()
            }
        else:
            users[username]['last_seen'] = datetime.utcnow()
        
        # Set session
        session['username'] = username
        
        # Send login notification to Telegram
        message = f"🔐 <b>Chat Login</b>\n" \
                 f"👤 Username: {username}\n" \
                 f"📧 Email: {email}\n" \
                 f"🌐 IP: {request.remote_addr}\n" \
                 f"🖥️ User Agent: {request.headers.get('User-Agent', 'Unknown')[:100]}\n" \
                 f"⏰ Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
        send_telegram_message(message)
        
        flash('Welcome to the chat!', 'success')
        next_page = request.args.get('next')
        return redirect(next_page) if next_page else redirect(url_for('index'))
    
    return render_template('login_simple.html')

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

@app.route('/set_nickname', methods=['GET', 'POST'])
@login_required
def set_nickname():
    """Allow user to change their nickname/username"""
    user = get_current_user()
    
    if request.method == 'POST':
        new_nickname = request.form.get('nickname', '').strip()
        
        if not new_nickname:
            flash('Nickname cannot be empty', 'error')
            return render_template('set_nickname.html', current_nickname=user['username'])
        
        # Check if nickname is already taken
        if new_nickname in users and new_nickname != user['username']:
            flash('This nickname is already taken', 'error')
            return render_template('set_nickname.html', current_nickname=user['username'])
        
        # Update the nickname
        old_nickname = user['username']
        
        # Move user data to new key
        if new_nickname != old_nickname:
            users[new_nickname] = users.pop(old_nickname)
            session['username'] = new_nickname
            
            # Update all messages with the new nickname
            for room_slug, room_data in rooms.items():
                for message in room_data['messages']:
                    if message['user_id'] == old_nickname:
                        message['user_id'] = new_nickname
                        message['nickname'] = new_nickname
        
        # Send notification to Telegram
        message = f"📝 <b>Nickname Changed</b>\n" \
                 f"👤 Old: {old_nickname}\n" \
                 f"👤 New: {new_nickname}\n" \
                 f"📧 Email: {users[new_nickname].get('email', 'N/A')}\n" \
                 f"🌐 IP: {request.remote_addr}\n" \
                 f"⏰ Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
        send_telegram_message(message)
        
        flash('Nickname updated successfully!', 'success')
        return redirect(url_for('index'))
    
    return render_template('set_nickname.html', current_nickname=user['username'])

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