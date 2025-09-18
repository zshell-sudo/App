# Multi-Room Chat Application

A feature-rich real-time multi-room chat application built with Flask. Users can join different chat rooms, send public and private messages, edit their own messages, and receive browser notifications for new messages. The application features a responsive dark-themed interface with mobile support and uses server-side polling for real-time updates.

## ✨ Features

- **Multi-room chat** - Create and join different chat rooms
- **Real-time messaging** - Messages update in real-time using HTTP polling
- **Private messaging** - Send direct messages to other users
- **Message editing** - Edit your own messages after sending
- **OAuth Authentication** - Login with Google or GitHub accounts
- **Responsive design** - Works on desktop and mobile devices
- **Dark theme** - Modern dark interface with Bootstrap 5
- **Browser notifications** - Get notified when new messages arrive
- **Message history** - View recent message history in each room

## 🚀 Quick Start

### Prerequisites

- Python 3.11 or higher
- PostgreSQL database (optional - uses in-memory storage by default)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd multi-room-chat
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Run the application**
   ```bash
   python main.py
   ```

The application will be available at `http://localhost:5000`

## 🔧 Configuration

### Environment Variables

Copy `.env.example` to `.env` and configure the following variables:

#### Required Variables
- `SESSION_SECRET` - Secret key for Flask sessions
- `DATABASE_URL` - PostgreSQL connection string (optional)

#### OAuth Configuration
To enable Google and GitHub login, you need to set up OAuth applications:

**Google OAuth Setup:**
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable the Google+ API
4. Go to APIs & Services > Credentials
5. Create OAuth 2.0 Client ID
6. Add your domain to authorized domains
7. Set redirect URI: `https://yourdomain.com/auth/google/callback`
8. Copy Client ID and Client Secret to your `.env` file

**GitHub OAuth Setup:**
1. Go to [GitHub Developer Settings](https://github.com/settings/developers)
2. Click "New OAuth App"
3. Fill in application details
4. Set Authorization callback URL: `https://yourdomain.com/auth/github/callback`
5. Copy Client ID and Client Secret to your `.env` file

#### Optional Variables
- `TELEGRAM_BOT_TOKEN` - For Telegram notifications
- `TELEGRAM_CHAT_ID` - Telegram chat to send notifications to

## 🌐 Deployment

### Deploy to Vercel

1. **Install Vercel CLI**
   ```bash
   npm i -g vercel
   ```

2. **Deploy**
   ```bash
   vercel --prod
   ```

3. **Set environment variables in Vercel dashboard**
   - Go to your project in Vercel dashboard
   - Navigate to Settings > Environment Variables
   - Add all variables from your `.env` file

**Important for Vercel**: The `vercel.json` configuration includes `includeFiles` to ensure Flask templates are bundled with the serverless function. Static assets are automatically served by Vercel's CDN.

### Deploy to Railway

1. **Connect your GitHub repository to Railway**
2. **Set environment variables in Railway dashboard**
3. **Deploy automatically on push**

### Deploy to Render

1. **Connect your GitHub repository to Render**
2. **Set build command:** `pip install -r requirements.txt`
3. **Set start command:** `gunicorn main:app`
4. **Add environment variables**

### Deploy to Heroku

1. **Install Heroku CLI and login**
   ```bash
   heroku create your-app-name
   ```

2. **Set environment variables**
   ```bash
   heroku config:set SESSION_SECRET=your-secret
   heroku config:set GOOGLE_CLIENT_ID=your-id
   # ... add other variables
   ```

3. **Deploy**
   ```bash
   git push heroku main
   ```

## 🏗️ Architecture

### Frontend
- **Framework**: Server-rendered templates with Flask/Jinja2
- **Styling**: Bootstrap 5 with dark theme
- **JavaScript**: Vanilla JS for real-time updates and interactions
- **Icons**: Font Awesome 6

### Backend
- **Framework**: Flask (Python)
- **Authentication**: OAuth 2.0 (Google, GitHub)
- **Database**: PostgreSQL with SQLAlchemy (optional)
- **Storage**: In-memory dictionaries (default)
- **Real-time**: HTTP polling

### Data Storage
- **Default**: In-memory storage using Python dictionaries
- **Optional**: PostgreSQL database for persistence
- **Sessions**: Flask's built-in session handling

## 🔌 API Endpoints

### Authentication
- `GET /login` - Login page
- `GET /auth/google` - Initiate Google OAuth
- `GET /auth/github` - Initiate GitHub OAuth
- `GET /logout` - User logout

### Chat API
- `GET /api/messages/<room_slug>` - Get messages for a room
- `POST /api/send_message` - Send a message
- `POST /api/edit_message` - Edit a message
- `POST /api/delete_message` - Delete a message
- `POST /api/create_room` - Create a new room
- `GET /api/rooms` - Get list of all rooms

### Private Messages
- `POST /api/send_private_message` - Send private message
- `GET /api/private_messages` - Get private messages

### System
- `GET /health` - Health check endpoint

## 🛠️ Development

### Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env

# Run in development mode
python main.py
```

### Database Setup (Optional)
```bash
# Install PostgreSQL locally or use cloud provider
# Update DATABASE_URL in .env
# The app will automatically create tables on startup
```

### Project Structure
```
├── app.py              # Main Flask application
├── main.py             # Entry point and WSGI application
├── models.py           # Database models (SQLAlchemy)
├── requirements.txt    # Python dependencies
├── vercel.json         # Vercel deployment configuration
├── static/             # Static assets (CSS, JS)
│   ├── css/
│   └── js/
└── templates/          # Jinja2 templates
    ├── index.html
    └── login.html
```

## 🔒 Security

- OAuth 2.0 authentication with Google and GitHub
- Session-based authentication
- Environment variables for sensitive data
- Proxy-aware middleware for secure deployments

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is open source and available under the [MIT License](LICENSE).

## 🆘 Support

If you encounter any issues:

1. Check the [Issues](../../issues) page
2. Make sure all environment variables are set correctly
3. Verify OAuth applications are configured properly
4. Check server logs for error messages

## 🚀 Recent Updates

- ✅ Flask application configured for multiple hosting platforms
- ✅ Vercel deployment ready with serverless configuration  
- ✅ PostgreSQL database support with SQLAlchemy
- ✅ OAuth authentication with Google and GitHub
- ✅ In-memory storage for quick setup
- ✅ Mobile-responsive dark theme interface
- ✅ Real-time messaging with HTTP polling
