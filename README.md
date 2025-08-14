# Overview

A feature-rich real-time multi-room chat application built with Flask. Users can join different chat rooms, send public and private messages, edit their own messages, and receive browser notifications for new messages. The application features a responsive dark-themed interface with mobile support and uses server-side polling for real-time updates.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Frontend Architecture
- **Single-page application** with server-rendered templates using Flask/Jinja2
- **Bootstrap 5** with dark theme for responsive UI components and mobile-first design
- **Vanilla JavaScript** (ChatApp class) for client-side interactivity, real-time updates, and advanced features
- **Font Awesome** icons for enhanced visual elements and action buttons
- **Client-side polling** mechanism for real-time message synchronization
- **Browser notifications** API integration for desktop alerts when window is not active
- **Mobile-responsive sidebar** with overlay and touch-friendly navigation

## Backend Architecture
- **Flask web framework** as the main application server with CORS enabled
- **Session-based user management** using Flask sessions for nickname storage and authentication
- **In-memory data storage** using Python dictionaries for rooms, messages, and private conversations
- **RESTful API endpoints** for message operations, room management, message editing, and private messaging
- **ProxyFix middleware** for proper handling behind reverse proxies
- **Message editing and deletion** capabilities with user authorization checks
- **Private messaging system** with user-to-user communication

## Data Storage
- **In-memory storage** using Python dictionaries for:
  - Room data (room ID, name, messages)
  - Active user tracking
  - Session management through Flask's built-in session handling
- **No persistent database** - data is lost when server restarts

## Authentication & Authorization
- **Simple nickname-based authentication** without passwords
- **Session-based user tracking** with server-side session storage
- **No role-based permissions** - all users have equal access to public rooms

## Real-time Communication
- **HTTP polling** instead of WebSockets for message updates
- **AJAX requests** for sending messages and room operations
- **Automatic message synchronization** with configurable polling intervals

# External Dependencies

## Frontend Dependencies
- **Bootstrap 5** (CDN) - UI framework and dark theme styling
- **Font Awesome 6** (CDN) - Icon library for user interface elements

## Backend Dependencies
- **Flask** - Core web framework for Python
- **Flask-CORS** - Cross-Origin Resource Sharing support
- **Werkzeug** - WSGI utilities including ProxyFix middleware

## Infrastructure
- **No external databases** - uses in-memory storage only
- **No third-party APIs** - self-contained chat application
- **Session management** through Flask's built-in session handling with configurable secret key
