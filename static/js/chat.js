// Chat application JavaScript
class ChatApp {
    constructor() {
        this.currentRoom = window.chatApp.currentRoom;
        this.nickname = window.chatApp.nickname;
        this.lastMessageId = 0;
        this.pollingInterval = null;
        this.isLoading = false;
        this.notificationsEnabled = false;
        this.currentEditingMessage = null;
        this.unreadMessages = 0;
        this.lastMessageCount = 0;

        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadMessages();
        this.startPolling();
        this.loadRooms();
        this.setupNotifications();
        this.setupMobileResponsiveness();
    }

    setupEventListeners() {
        // Message form submission
        const messageForm = document.getElementById('message-form');
        messageForm.addEventListener('submit', (e) => {
            e.preventDefault();
            this.sendMessage();
        });

        // Enter key to send message
        const messageInput = document.getElementById('message-input');
        messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        // Auto-focus message input
        messageInput.focus();

        // Create room form
        const createRoomForm = document.getElementById('create-room-form');
        createRoomForm.addEventListener('submit', (e) => {
            e.preventDefault();
            this.createRoom();
        });

        // Enter key in room name input
        const roomNameInput = document.getElementById('room-name-input');
        roomNameInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                this.createRoom();
            }
        });

        // Notification setup
        const notificationIcon = document.getElementById('notification-icon');
        if (notificationIcon) {
            notificationIcon.addEventListener('click', () => {
                this.requestNotificationPermission();
            });
        }

        // Mobile sidebar toggle
        const toggleSidebar = document.getElementById('toggle-sidebar');
        if (toggleSidebar) {
            toggleSidebar.addEventListener('click', () => {
                this.toggleMobileSidebar();
            });
        }
    }

    async loadMessages() {
        try {
            this.showLoading(true);
            const response = await fetch(`/api/messages/${this.currentRoom}`);

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();

            // Check for new messages for notifications
            if (data.messages.length > this.lastMessageCount && this.lastMessageCount > 0) {
                const newMessages = data.messages.slice(this.lastMessageCount);
                newMessages.forEach(message => {
                    if (message.nickname !== this.nickname) {
                        this.showNotification(message);
                    }
                });
            }
            this.lastMessageCount = data.messages.length;

            this.renderMessages(data.messages);
            this.updateRoomHeader(data.room_name, data.messages.length);

            if (data.messages.length > 0) {
                this.lastMessageId = Math.max(...data.messages.map(m => m.id));
            }
        } catch (error) {
            console.error('Error loading messages:', error);
            this.showError('Failed to load messages. Please refresh the page.');
        } finally {
            this.showLoading(false);
        }
    }

    async sendMessage() {
        const messageInput = document.getElementById('message-input');
        const message = messageInput.value.trim();

        if (!message) return;

        try {
            const response = await fetch('/api/send_message', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    room_id: this.currentRoom,
                    message: message
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();

            if (data.success) {
                messageInput.value = '';
                // Force immediate refresh of messages
                await this.loadMessages();
            } else {
                throw new Error(data.error || 'Failed to send message');
            }
        } catch (error) {
            console.error('Error sending message:', error);
            this.showError('Failed to send message. Please try again.');
        }
    }

    renderMessages(messages) {
        const messagesContainer = document.getElementById('messages');
        const wasAtBottom = this.isScrolledToBottom();

        messagesContainer.innerHTML = '';

        messages.forEach(message => {
            const messageElement = this.createMessageElement(message);
            messagesContainer.appendChild(messageElement);
        });

        // Auto-scroll to bottom if user was already at bottom or if it's the first load
        if (wasAtBottom || messagesContainer.children.length === messages.length) {
            this.scrollToBottom();
        }
    }

    createMessageElement(message) {
        const messageDiv = document.createElement('div');
        const isOwnMessage = message.nickname === this.nickname;
        const isPrivate = message.private || false;
        const isEdited = message.edited || false;

        messageDiv.className = `message ${isOwnMessage ? 'own' : ''} ${isPrivate ? 'private-message' : ''} ${isEdited ? 'edited' : ''}`;
        messageDiv.style.position = 'relative';

        messageDiv.innerHTML = `
            <div class="d-flex ${isOwnMessage ? 'justify-content-end' : 'justify-content-start'}">
                <div class="message-bubble">
                    ${!isOwnMessage ? `
                        <div class="message-header">
                            <strong class="clickable-username" onclick="chatAppInstance.openPrivateMessage('${this.escapeHtml(message.nickname)}')">${this.escapeHtml(message.nickname)}</strong>
                            <small class="message-time ms-2">${message.formatted_time}</small>
                            ${isPrivate ? '<i class="fas fa-lock ms-1" title="Private message"></i>' : ''}
                        </div>
                    ` : `
                        <div class="message-header text-end">
                            <small class="message-time">${message.formatted_time}</small>
                            ${isPrivate ? '<i class="fas fa-lock ms-1" title="Private message"></i>' : ''}
                        </div>
                    `}
                    <div class="message-content">
                        ${this.escapeHtml(message.message)}
                    </div>
                    ${isOwnMessage && !isPrivate ? `
                        <div class="message-actions">
                            <button class="btn btn-outline-secondary btn-sm" onclick="chatAppInstance.editMessage(${message.id}, '${this.escapeHtml(message.message).replace(/'/g, '&#39;')}')" title="Edit">
                                <i class="fas fa-edit"></i>
                            </button>
                            <button class="btn btn-outline-danger btn-sm" onclick="chatAppInstance.deleteMessage(${message.id})" title="Delete">
                                <i class="fas fa-trash"></i>
                            </button>
                        </div>
                    ` : ''}
                </div>
            </div>
        `;

        return messageDiv;
    }

    async createRoom() {
        const roomNameInput = document.getElementById('room-name-input');
        const roomName = roomNameInput.value.trim();

        if (!roomName) {
            this.showError('Please enter a room name');
            return;
        }

        try {
            const response = await fetch('/api/create_room', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    room_name: roomName
                })
            });

            const data = await response.json();

            if (data.success) {
                roomNameInput.value = '';

                // Close modal
                const modal = bootstrap.Modal.getInstance(document.getElementById('createRoomModal'));
                modal.hide();

                // Refresh rooms list
                await this.loadRooms();

                // Switch to new room
                this.switchRoom(data.room_id);
            } else {
                throw new Error(data.error || 'Failed to create room');
            }
        } catch (error) {
            console.error('Error creating room:', error);
            this.showError(error.message || 'Failed to create room. Please try again.');
        }
    }

    async loadRooms() {
        try {
            const response = await fetch('/api/rooms');

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            this.renderRooms(data.rooms);
        } catch (error) {
            console.error('Error loading rooms:', error);
        }
    }

    renderRooms(rooms) {
        const roomsList = document.getElementById('rooms-list');
        roomsList.innerHTML = '';

        rooms.forEach(room => {
            const roomElement = document.createElement('div');
            roomElement.className = `room-item ${room.id === this.currentRoom ? 'active' : ''}`;
            roomElement.setAttribute('data-room-id', room.id);
            roomElement.onclick = () => this.switchRoom(room.id);

            roomElement.innerHTML = `
                <div class="d-flex align-items-center p-2 rounded cursor-pointer">
                    <i class="fas fa-hashtag me-2"></i>
                    <span class="flex-grow-1">${this.escapeHtml(room.name)}</span>
                    ${room.message_count > 0 ? `<small class="text-muted">${room.message_count}</small>` : ''}
                </div>
            `;

            roomsList.appendChild(roomElement);
        });
    }

    switchRoom(roomId) {
        if (roomId === this.currentRoom) return;

        // Stop current polling
        this.stopPolling();

        // Update current room
        this.currentRoom = roomId;
        this.lastMessageId = 0;

        // Update URL without page reload
        const url = new URL(window.location);
        url.searchParams.set('room', roomId);
        window.history.pushState({}, '', url);

        // Update UI
        this.updateActiveRoom();
        this.loadMessages();
        this.startPolling();

        // Focus message input
        document.getElementById('message-input').focus();
    }

    updateActiveRoom() {
        // Update room selection in sidebar
        document.querySelectorAll('.room-item').forEach(item => {
            item.classList.remove('active');
            if (item.getAttribute('data-room-id') === this.currentRoom) {
                item.classList.add('active');
            }
        });
    }

    updateRoomHeader(roomName, messageCount) {
        document.getElementById('current-room-name').textContent = roomName;
        document.getElementById('message-count').textContent = `${messageCount} messages`;
    }

    startPolling() {
        // Poll for new messages every 2.5 seconds
        this.pollingInterval = setInterval(() => {
            this.loadMessages();
        }, 2500);
    }

    stopPolling() {
        if (this.pollingInterval) {
            clearInterval(this.pollingInterval);
            this.pollingInterval = null;
        }
    }

    isScrolledToBottom() {
        const container = document.getElementById('messages-container');
        return container.scrollTop + container.clientHeight >= container.scrollHeight - 10;
    }

    scrollToBottom() {
        const container = document.getElementById('messages-container');
        container.scrollTop = container.scrollHeight;
    }

    showLoading(show) {
        this.isLoading = show;
        const indicator = document.getElementById('loading-indicator');

        if (show) {
            indicator.classList.remove('d-none');
        } else {
            indicator.classList.add('d-none');
        }
    }

    showError(message) {
        // Create a toast for error messages
        const toastHtml = `
            <div class="toast align-items-center text-bg-danger border-0" role="alert">
                <div class="d-flex">
                    <div class="toast-body">
                        <i class="fas fa-exclamation-triangle me-2"></i>${this.escapeHtml(message)}
                    </div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
                </div>
            </div>
        `;

        // Add toast to container
        const toastContainer = document.querySelector('.position-fixed.top-0.end-0');
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = toastHtml;
        const toastElement = tempDiv.firstElementChild;

        toastContainer.appendChild(toastElement);

        // Show toast
        const toast = new bootstrap.Toast(toastElement);
        toast.show();

        // Remove from DOM after it's hidden
        toastElement.addEventListener('hidden.bs.toast', () => {
            toastElement.remove();
        });
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    // Handle page visibility change to pause/resume polling
    handleVisibilityChange() {
        if (document.hidden) {
            this.stopPolling();
        } else {
            this.startPolling();
            this.loadMessages(); // Refresh immediately when page becomes visible
        }
    }

    // Notification methods
    setupNotifications() {
        if ('Notification' in window) {
            if (Notification.permission === 'granted') {
                this.notificationsEnabled = true;
                this.updateNotificationIcon();
            }
        }
    }

    async requestNotificationPermission() {
        if (!('Notification' in window)) {
            this.showError('This browser does not support notifications');
            return;
        }

        const permission = await Notification.requestPermission();
        if (permission === 'granted') {
            this.notificationsEnabled = true;
            this.updateNotificationIcon();
            this.showSuccess('Notifications enabled!');
        } else {
            this.showError('Notification permission denied');
        }
    }

    updateNotificationIcon() {
        const icon = document.getElementById('notification-icon');
        if (icon) {
            if (this.notificationsEnabled) {
                icon.className = 'fas fa-bell text-success';
                icon.title = 'Notifications enabled';
            } else {
                icon.className = 'fas fa-bell text-muted';
                icon.title = 'Click to enable notifications';
            }
        }
    }

    showNotification(message) {
        if (this.notificationsEnabled && document.hidden && 'Notification' in window) {
            new Notification(`New message from ${message.nickname}`, {
                body: message.message,
                icon: '/static/favicon.ico'
            });
        }
    }

    // Message editing methods
    editMessage(messageId, currentText) {
        this.currentEditingMessage = messageId;
        const modal = new bootstrap.Modal(document.getElementById('editMessageModal'));
        document.getElementById('edit-message-input').value = currentText;
        modal.show();
    }

    async saveEditedMessage() {
        const newText = document.getElementById('edit-message-input').value.trim();
        if (!newText) {
            this.showError('Message cannot be empty');
            return;
        }

        try {
            const response = await fetch('/api/edit_message', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    room_id: this.currentRoom,
                    message_id: this.currentEditingMessage,
                    message: newText
                })
            });

            const data = await response.json();
            if (data.success) {
                const modal = bootstrap.Modal.getInstance(document.getElementById('editMessageModal'));
                modal.hide();
                await this.loadMessages();
                this.showSuccess('Message updated');
            } else {
                throw new Error(data.error || 'Failed to edit message');
            }
        } catch (error) {
            console.error('Error editing message:', error);
            this.showError(error.message || 'Failed to edit message');
        }
    }

    async deleteMessage(messageId) {
        if (!confirm('Are you sure you want to delete this message?')) {
            return;
        }

        try {
            const response = await fetch('/api/delete_message', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    room_id: this.currentRoom,
                    message_id: messageId
                })
            });

            const data = await response.json();
            if (data.success) {
                await this.loadMessages();
                this.showSuccess('Message deleted');
            } else {
                throw new Error(data.error || 'Failed to delete message');
            }
        } catch (error) {
            console.error('Error deleting message:', error);
            this.showError(error.message || 'Failed to delete message');
        }
    }

    // Private messaging methods
    openPrivateMessage(username) {
        if (username === this.nickname) {
            this.showError("You can't send a message to yourself");
            return;
        }

        const modal = new bootstrap.Modal(document.getElementById('privateMessageModal'));
        document.getElementById('recipient-input').value = username;
        document.getElementById('private-message-input').value = '';
        modal.show();
    }

    async sendPrivateMessage() {
        const recipient = document.getElementById('recipient-input').value.trim();
        const message = document.getElementById('private-message-input').value.trim();

        if (!recipient || !message) {
            this.showError('Recipient and message are required');
            return;
        }

        try {
            const response = await fetch('/api/send_private_message', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    recipient: recipient,
                    message: message
                })
            });

            const data = await response.json();
            if (data.success) {
                const modal = bootstrap.Modal.getInstance(document.getElementById('privateMessageModal'));
                modal.hide();
                this.showSuccess(`Private message sent to ${recipient}`);
            } else {
                throw new Error(data.error || 'Failed to send private message');
            }
        } catch (error) {
            console.error('Error sending private message:', error);
            this.showError(error.message || 'Failed to send private message');
        }
    }

    // Mobile responsiveness methods
    setupMobileResponsiveness() {
        // Create overlay for mobile sidebar
        const overlay = document.createElement('div');
        overlay.className = 'sidebar-overlay';
        overlay.addEventListener('click', () => {
            this.closeMobileSidebar();
        });
        document.body.appendChild(overlay);
    }

    toggleMobileSidebar() {
        const sidebar = document.getElementById('sidebar');
        const overlay = document.querySelector('.sidebar-overlay');

        if (sidebar.classList.contains('show')) {
            this.closeMobileSidebar();
        } else {
            sidebar.classList.add('show');
            overlay.classList.add('show');
        }
    }

    closeMobileSidebar() {
        const sidebar = document.getElementById('sidebar');
        const overlay = document.querySelector('.sidebar-overlay');

        sidebar.classList.remove('show');
        overlay.classList.remove('show');
    }

    showSuccess(message) {
        this.showToast(message, 'success');
    }

    showToast(message, type = 'info') {
        const toastHtml = `
            <div class="toast align-items-center text-bg-${type} border-0" role="alert">
                <div class="d-flex">
                    <div class="toast-body">
                        <i class="fas fa-${type === 'success' ? 'check' : type === 'danger' ? 'exclamation-triangle' : 'info'} me-2"></i>${this.escapeHtml(message)}
                    </div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
                </div>
            </div>
        `;

        const toastContainer = document.getElementById('toast-container');
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = toastHtml;
        const toastElement = tempDiv.firstElementChild;

        toastContainer.appendChild(toastElement);

        const toast = new bootstrap.Toast(toastElement, { delay: 3000 });
        toast.show();

        toastElement.addEventListener('hidden.bs.toast', () => {
            toastElement.remove();
        });
    }
}

// Global functions for HTML onclick handlers
window.switchRoom = function(roomId) {
    if (window.chatAppInstance) {
        window.chatAppInstance.switchRoom(roomId);
    }
};

window.createRoom = function() {
    if (window.chatAppInstance) {
        window.chatAppInstance.createRoom();
    }
};

window.sendPrivateMessage = function() {
    if (window.chatAppInstance) {
        window.chatAppInstance.sendPrivateMessage();
    }
};

window.saveEditedMessage = function() {
    if (window.chatAppInstance) {
        window.chatAppInstance.saveEditedMessage();
    }
};

window.deleteMessage = function() {
    if (window.chatAppInstance) {
        window.chatAppInstance.deleteMessage(window.chatAppInstance.currentEditingMessage);
    }
};

// Initialize the chat app when the page loads
document.addEventListener('DOMContentLoaded', function() {
    window.chatAppInstance = new ChatApp();

    // Handle page visibility changes
    document.addEventListener('visibilitychange', () => {
        window.chatAppInstance.handleVisibilityChange();
    });

    // Handle page unload to stop polling
    window.addEventListener('beforeunload', () => {
        window.chatAppInstance.stopPolling();
    });
});
