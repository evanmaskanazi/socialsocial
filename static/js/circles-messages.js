// Circles and Messages Management System with i18n support
// Complete Fixed Version with null safety and proper error handling

// Safe translation function with fallbacks
const t = (key, fallback = key) => {
    try {
        if (window.i18n && typeof window.i18n.translate === 'function') {
            const translation = window.i18n.translate(key);
            return translation || fallback;
        }
    } catch (error) {
        console.warn('Translation error:', error);
    }
    return fallback;
};

// Wait for i18n to be ready
function waitForI18n() {
    return new Promise((resolve) => {
        if (window.i18n && window.i18n.t) {
            resolve();
        } else {
            const checkInterval = setInterval(() => {
                if (window.i18n && window.i18n.t) {
                    clearInterval(checkInterval);
                    resolve();
                }
            }, 50);
            // Timeout after 5 seconds
            setTimeout(() => {
                clearInterval(checkInterval);
                resolve();
            }, 5000);
        }
    });
}

// ============================================================
// Time formatting function with null safety
// ============================================================
function formatMessageTime(timestamp) {
    try {
        if (!timestamp) return t('messages.unknown_time', 'Unknown time');

        const now = new Date();
        const msgTime = new Date(timestamp);

        if (isNaN(msgTime.getTime())) {
            return t('messages.unknown_time', 'Unknown time');
        }

        const diffSeconds = Math.floor((now - msgTime) / 1000);

        // Just now (less than 60 seconds)
        if (diffSeconds < 60) {
            return t('messages.just_now', 'Just now');
        }

        // Minutes ago
        if (diffSeconds < 3600) {
            const minutes = Math.floor(diffSeconds / 60);
            return `${minutes} ${t('messages.minutes_ago', 'min ago')}`;
        }

        // Hours ago (same day)
        if (msgTime.toDateString() === now.toDateString()) {
            return msgTime.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        }

        // Yesterday
        const yesterday = new Date(now);
        yesterday.setDate(yesterday.getDate() - 1);
        if (msgTime.toDateString() === yesterday.toDateString()) {
            return t('messages.yesterday', 'Yesterday');
        }

        // Older messages
        return msgTime.toLocaleDateString();
    } catch (error) {
        console.error('Error formatting time:', error);
        return t('messages.unknown_time', 'Unknown time');
    }
}

// ============================================================
// Safe HTML escape function
// ============================================================
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ===================
// CIRCLES MANAGEMENT
// ===================

const circlesHTML = `
<div class="circles-container">
    <style>
        .circles-container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }

        .circles-header {
            text-align: center;
            margin-bottom: 30px;
        }

        .circles-header h1 {
            color: #667eea;
            font-size: 2.5em;
            margin-bottom: 10px;
        }

        .user-search {
            max-width: 600px;
            margin: 0 auto 40px;
            position: relative;
        }

        .search-input {
            width: 100%;
            padding: 15px 50px 15px 20px;
            border: 2px solid #e1e8ed;
            border-radius: 30px;
            font-size: 16px;
            transition: all 0.3s;
        }

        .search-input:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }

        .search-btn {
            position: absolute;
            right: 5px;
            top: 50%;
            transform: translateY(-50%);
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border: none;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            color: white;
            cursor: pointer;
            transition: all 0.3s;
        }

        .search-results {
            position: absolute;
            top: 100%;
            left: 0;
            right: 0;
            background: white;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
            margin-top: 10px;
            max-height: 300px;
            overflow-y: auto;
            display: none;
            z-index: 10;
        }

        .search-results.active {
            display: block;
        }

        .search-result-item {
            padding: 15px 20px;
            border-bottom: 1px solid #f0f0f0;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
            transition: background 0.2s;
        }

        .search-result-item:hover {
            background: #f8f9fa;
        }

        .user-info {
            display: flex;
            align-items: center;
            gap: 15px;
        }

        .user-avatar {
            width: 40px;
            height: 40px;
            border-radius: 50%;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
        }

        .add-to-circle-btn {
            background: #667eea;
            color: white;
            border: none;
            padding: 8px 15px;
            border-radius: 20px;
            cursor: pointer;
            font-size: 14px;
            transition: all 0.3s;
        }

        .add-to-circle-btn:hover {
            background: #764ba2;
        }

        .circles-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 30px;
        }

        .circle-card {
            background: white;
            border-radius: 20px;
            padding: 25px;
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.08);
            transition: all 0.3s;
        }

        .circle-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.15);
        }

        .circle-header {
            display: flex;
            align-items: center;
            gap: 15px;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 2px solid #f0f0f0;
        }

        .circle-icon {
            font-size: 2em;
        }

        .circle-title {
            font-size: 1.5em;
            color: #2d3436;
            font-weight: 600;
        }

        .circle-count {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 14px;
            margin-left: auto;
        }

        .circle-members {
            max-height: 300px;
            overflow-y: auto;
        }

        .member-item {
            display: flex;
            align-items: center;
            gap: 15px;
            padding: 10px;
            border-radius: 10px;
            transition: background 0.2s;
        }

        .member-item:hover {
            background: #f8f9fa;
        }

        .member-name {
            flex-grow: 1;
            color: #2d3436;
        }

        .remove-btn {
            background: #ff6b6b;
            color: white;
            border: none;
            padding: 5px 10px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 12px;
            opacity: 0;
            transition: all 0.3s;
        }

        .member-item:hover .remove-btn {
            opacity: 1;
        }

        .empty-state {
            text-align: center;
            padding: 40px;
            color: #8898aa;
        }

        .empty-state-icon {
            font-size: 3em;
            margin-bottom: 15px;
            opacity: 0.5;
        }
    </style>

    <div class="circles-header">
        <h1 data-i18n="circles.title">Your Circles</h1>
        <p style="color: #8898aa;" data-i18n="circles.subtitle">Organize your connections</p>
    </div>

    <div class="user-search">
        <input type="text" class="search-input" id="userSearchInput" data-i18n="circles.search_placeholder" placeholder="Search users...">
        <button class="search-btn" onclick="searchUsers()">🔍</button>
        <div class="search-results" id="searchResults"></div>
    </div>

    <div class="circles-grid">
        <div class="circle-card">
            <div class="circle-header">
                <span class="circle-icon">👥</span>
                <span class="circle-title" data-i18n="circles.general">General</span>
                <span class="circle-count" id="generalCount">0</span>
            </div>
            <div class="circle-members" id="generalMembers">
                <div class="empty-state">
                    <div class="empty-state-icon">👥</div>
                    <p data-i18n="circles.no_members">No members yet</p>
                </div>
            </div>
        </div>

        <div class="circle-card">
            <div class="circle-header">
                <span class="circle-icon">❤️</span>
                <span class="circle-title" data-i18n="circles.close_friends">Close Friends</span>
                <span class="circle-count" id="closeFriendsCount">0</span>
            </div>
            <div class="circle-members" id="closeFriendsMembers">
                <div class="empty-state">
                    <div class="empty-state-icon">❤️</div>
                    <p data-i18n="circles.no_members">No members yet</p>
                </div>
            </div>
        </div>

        <div class="circle-card">
            <div class="circle-header">
                <span class="circle-icon">👨‍👩‍👧‍👦</span>
                <span class="circle-title" data-i18n="circles.family">Family</span>
                <span class="circle-count" id="familyCount">0</span>
            </div>
            <div class="circle-members" id="familyMembers">
                <div class="empty-state">
                    <div class="empty-state-icon">👨‍👩‍👧‍👦</div>
                    <p data-i18n="circles.no_members">No members yet</p>
                </div>
            </div>
        </div>
    </div>
</div>
`;

// Circles JavaScript Functions
let circlesData = {
    general: [],
    close_friends: [],
    family: []
};

async function loadCircles() {
    try {
        const response = await fetch('/api/circles', {
            credentials: 'include'
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();
        circlesData = {
            general: data.general || [],
            close_friends: data.close_friends || [],
            family: data.family || []
        };

        updateCirclesDisplay();
    } catch (error) {
        console.error('Error loading circles:', error);
        showNotification(t('error.loading_circles', 'Error loading circles'), 'error');
    }
}

function updateCirclesDisplay() {
    updateCircleDisplay('general', circlesData.general, 'generalMembers', 'generalCount');
    updateCircleDisplay('close_friends', circlesData.close_friends, 'closeFriendsMembers', 'closeFriendsCount');
    updateCircleDisplay('family', circlesData.family, 'familyMembers', 'familyCount');
}

function updateCircleDisplay(circleType, members, containerId, countId) {
    const container = document.getElementById(containerId);
    const count = document.getElementById(countId);

    if (!container || !count) return;

    count.textContent = members ? members.length : 0;

    if (!members || members.length === 0) {
        const icon = circleType === 'general' ? '👥' :
                    circleType === 'close_friends' ? '❤️' : '👨‍👩‍👧‍👦';
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">${icon}</div>
                <p data-i18n="circles.no_members">${t('circles.no_members', 'No members yet')}</p>
            </div>
        `;
    } else {
        container.innerHTML = members.map(member => {
            if (!member || !member.username || !member.id) return '';
            return `
                <div class="member-item">
                    <div class="user-avatar">${member.username[0].toUpperCase()}</div>
                    <div class="member-name">${escapeHtml(member.username)}</div>
                    <button class="remove-btn" onclick="removeFromCircle(${member.id}, '${circleType}')" data-i18n="btn.remove">${t('btn.remove', 'Remove')}</button>
                </div>
            `;
        }).filter(html => html).join('');
    }
}

async function searchUsers() {
    const input = document.getElementById('userSearchInput');
    if (!input) return;

    const query = input.value;
    if (query.length < 2) {
        const results = document.getElementById('searchResults');
        if (results) results.classList.remove('active');
        return;
    }

    try {
        const response = await fetch(`/api/users/search?q=${encodeURIComponent(query)}`, {
            credentials: 'include'
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();
        displaySearchResults(data.users || []);
    } catch (error) {
        console.error('Error searching users:', error);
        showNotification(t('error.searching', 'Error searching users'), 'error');
    }
}

function displaySearchResults(users) {
    const resultsContainer = document.getElementById('searchResults');
    if (!resultsContainer) return;

    if (!users || users.length === 0) {
        resultsContainer.innerHTML = `<div class="search-result-item">${t('circles.no_users_found', 'No users found')}</div>`;
    } else {
        resultsContainer.innerHTML = users.map(user => {
            if (!user || !user.username || !user.id) return '';
            return `
                <div class="search-result-item">
                    <div class="user-info">
                        <div class="user-avatar">${user.username[0].toUpperCase()}</div>
                        <div>
                            <div style="font-weight: 600;">${escapeHtml(user.username)}</div>
                            <div style="font-size: 14px; color: #8898aa;">${escapeHtml(user.email || '')}</div>
                        </div>
                    </div>
                    <select class="add-to-circle-btn" onchange="addToCircle(${user.id}, this.value, '${escapeHtml(user.username).replace(/'/g, "\\'")}')">
                        <option value="">${t('circles.add_to_circle', 'Add to circle...')}</option>
                        <option value="general">${t('circles.general', 'General')}</option>
                        <option value="close_friends">${t('circles.close_friends', 'Close Friends')}</option>
                        <option value="family">${t('circles.family', 'Family')}</option>
                    </select>
                </div>
            `;
        }).filter(html => html).join('');
    }

    resultsContainer.classList.add('active');
}

async function addToCircle(userId, circleType, username) {
    if (!circleType || !userId) return;

    try {
        const response = await fetch('/api/circles', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'include',
            body: JSON.stringify({
                user_id: userId,
                circle_type: circleType
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to add to circle');
        }

        const circleNames = {
            'general': t('circles.general', 'General'),
            'close_friends': t('circles.close_friends', 'Close Friends'),
            'family': t('circles.family', 'Family')
        };

        showNotification(
            `${username} ${t('circles.user_added', 'added to')} ${circleNames[circleType]} ${t('circles.circle', 'circle')}`,
            'success'
        );

        loadCircles();

        const searchResults = document.getElementById('searchResults');
        const searchInput = document.getElementById('userSearchInput');
        if (searchResults) searchResults.classList.remove('active');
        if (searchInput) searchInput.value = '';
    } catch (error) {
        console.error('Error adding to circle:', error);
        showNotification(error.message || t('error.saving', 'Error saving'), 'error');
    }
}

async function removeFromCircle(userId, circleType) {
    if (!confirm(t('circles.remove_confirm', 'Remove this member from the circle?'))) return;

    try {
        const response = await fetch('/api/circles/remove', {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'include',
            body: JSON.stringify({
                user_id: userId,
                circle_type: circleType
            })
        });

        if (!response.ok) {
            throw new Error('Failed to remove from circle');
        }

        showNotification(t('circles.user_removed', 'User removed'), 'success');
        loadCircles();
    } catch (error) {
        console.error('Error removing from circle:', error);
        showNotification(t('error.removing', 'Error removing user'), 'error');
    }
}

// ===================
// MESSAGES SYSTEM
// ===================

const messagesHTML = `
<div class="messages-container">
    <style>
        .messages-container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            display: grid;
            grid-template-columns: 350px 1fr;
            gap: 30px;
            height: 80vh;
        }

        @media (max-width: 768px) {
            .messages-container {
                grid-template-columns: 1fr;
                height: auto;
            }
        }

        .conversations-sidebar {
            background: white;
            border-radius: 20px;
            padding: 20px;
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.08);
            overflow-y: auto;
        }

        .sidebar-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 2px solid #f0f0f0;
        }

        .sidebar-title {
            font-size: 1.5em;
            color: #2d3436;
            font-weight: 600;
        }

        .new-message-btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 20px;
            cursor: pointer;
            transition: all 0.3s;
        }

        .conversation-item {
            display: flex;
            align-items: center;
            gap: 15px;
            padding: 15px;
            border-radius: 10px;
            cursor: pointer;
            transition: all 0.2s;
            margin-bottom: 10px;
        }

        .conversation-item:hover {
            background: #f8f9fa;
        }

        .conversation-item.active {
            background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%);
        }

        .conversation-avatar {
            width: 50px;
            height: 50px;
            border-radius: 50%;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            flex-shrink: 0;
        }

        .conversation-info {
            flex-grow: 1;
            min-width: 0;
        }

        .conversation-name {
            font-weight: 600;
            color: #2d3436;
            margin-bottom: 5px;
        }

        .conversation-preview {
            font-size: 14px;
            color: #8898aa;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .unread-badge {
            background: #ff6b6b;
            color: white;
            padding: 3px 8px;
            border-radius: 10px;
            font-size: 12px;
        }

        .message-area {
            background: white;
            border-radius: 20px;
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.08);
            display: flex;
            flex-direction: column;
        }

        .message-header {
            padding: 20px;
            border-bottom: 2px solid #f0f0f0;
            display: flex;
            align-items: center;
            gap: 15px;
        }

        .message-recipient {
            flex-grow: 1;
            font-size: 1.2em;
            font-weight: 600;
            color: #2d3436;
        }

        .messages-display {
            flex-grow: 1;
            padding: 20px;
            overflow-y: auto;
            background: #f8f9fa;
        }

        .message-bubble {
            max-width: 70%;
            margin: 10px 0;
            padding: 15px 20px;
            border-radius: 20px;
            position: relative;
            word-wrap: break-word;
        }

        .message-sent {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            margin-left: auto;
            border-bottom-right-radius: 5px;
        }

        .message-received {
            background: white;
            border: 1px solid #e1e8ed;
            border-bottom-left-radius: 5px;
        }

        .message-time {
            font-size: 12px;
            opacity: 0.7;
            margin-top: 5px;
        }

        .message-input-area {
            padding: 20px;
            border-top: 2px solid #f0f0f0;
            display: flex;
            gap: 15px;
        }

        .message-input {
            flex-grow: 1;
            padding: 12px 20px;
            border: 2px solid #e1e8ed;
            border-radius: 25px;
            font-size: 16px;
            transition: all 0.3s;
        }

        .message-input:focus {
            outline: none;
            border-color: #667eea;
        }

        .send-btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 12px 25px;
            border-radius: 25px;
            cursor: pointer;
            transition: all 0.3s;
            font-size: 16px;
        }

        .send-btn:hover {
            transform: scale(1.05);
        }

        .send-btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
    </style>

    <div class="conversations-sidebar">
        <div class="sidebar-header">
            <div class="sidebar-title" data-i18n="messages.title">Messages</div>
        </div>
        <div id="conversationsList">
            <div style="text-align: center; padding: 20px; color: #8898aa;" data-i18n="messages.loading">Loading...</div>
        </div>
    </div>

    <div class="message-area">
        <div class="message-header">
            <div class="conversation-avatar" id="currentRecipientAvatar">?</div>
            <div class="message-recipient" id="currentRecipient" data-i18n="messages.select_conversation">Select a conversation</div>
        </div>

        <div class="messages-display" id="messagesDisplay">
            <div style="text-align: center; padding: 50px; color: #8898aa;" data-i18n="messages.select_conversation">
                Select a conversation to start messaging
            </div>
        </div>

        <div class="message-input-area">
            <input type="text" class="message-input" id="messageInput" data-i18n="messages.type_message" placeholder="Type a message..." disabled>
            <button class="send-btn" id="sendBtn" onclick="sendMessage()" disabled data-i18n="messages.send">Send</button>
        </div>
    </div>
</div>
`;

// Messages JavaScript Functions
let messagesData = {
    sent: [],
    received: []
};
let currentRecipient = null;
let currentUserId = null;

async function getCurrentUser() {
    try {
        const response = await fetch('/api/user/profile', {
            credentials: 'include'
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const user = await response.json();
        currentUserId = user.id;
        return user;
    } catch (error) {
        console.error('Error getting current user:', error);
        return null;
    }
}

async function loadMessages() {
    try {
        const response = await fetch('/api/messages', {
            credentials: 'include'
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();
        messagesData = {
            sent: data.sent || [],
            received: data.received || []
        };

        updateConversationsList();
    } catch (error) {
        console.error('Error loading messages:', error);
        const container = document.getElementById('conversationsList');
        if (container) {
            container.innerHTML = `<div style="text-align: center; padding: 20px; color: #ff6b6b;">${t('error.loading_messages', 'Error loading messages')}</div>`;
        }
    }
}

function updateConversationsList() {
    const conversations = {};

    // Safely process messages
    [...(messagesData.sent || []), ...(messagesData.received || [])].forEach(msg => {
        try {
            if (!msg || !msg.sender || !msg.recipient) return;

            const partnerId = msg.sender.id === currentUserId ? msg.recipient.id : msg.sender.id;
            const partnerName = msg.sender.id === currentUserId ?
                (msg.recipient.username || 'Unknown') :
                (msg.sender.username || 'Unknown');

            if (!conversations[partnerId]) {
                conversations[partnerId] = {
                    id: partnerId,
                    name: partnerName,
                    lastMessage: msg,
                    unread: 0
                };
            } else {
                // Update last message if newer
                if (new Date(msg.created_at) > new Date(conversations[partnerId].lastMessage.created_at)) {
                    conversations[partnerId].lastMessage = msg;
                }
            }

            // Count unread messages
            if (msg.recipient && msg.recipient.id === currentUserId && !msg.is_read) {
                conversations[partnerId].unread++;
            }
        } catch (error) {
            console.error('Error processing message:', error);
        }
    });

    // Display conversations
    const container = document.getElementById('conversationsList');
    if (!container) return;

    const conversationArray = Object.values(conversations).sort((a, b) =>
        new Date(b.lastMessage.created_at) - new Date(a.lastMessage.created_at)
    );

    if (conversationArray.length === 0) {
        container.innerHTML = `<div style="text-align: center; padding: 20px; color: #8898aa;" data-i18n="messages.no_conversations">${t('messages.no_conversations', 'No conversations yet')}</div>`;
    } else {
     container.innerHTML = conversationArray.map(conv => {
    try {
        const lastMsgSent = conv.lastMessage.sender && conv.lastMessage.sender.id === currentUserId;
        const youText = t('messages.you', 'You');
        const messagePreview = lastMsgSent
            ? `${youText}: ${conv.lastMessage.content || ''}`
            : conv.lastMessage.content || '';
        const timeDisplay = formatMessageTime(conv.lastMessage.created_at);

        return `
            <div class="conversation-item ${currentRecipient?.id === conv.id ? 'active' : ''}"
                 onclick="selectConversation(${conv.id}, '${escapeHtml(conv.name).replace(/'/g, "\\'")}')">
                <div class="conversation-avatar">${conv.name[0].toUpperCase()}</div>
                <div class="conversation-info">
                    <div class="conversation-name">
                        ${escapeHtml(conv.name)}
                        <span style="font-size: 12px; color: #8898aa; margin-left: 10px;">${timeDisplay}</span>
                    </div>
                    <div class="conversation-preview">${escapeHtml(messagePreview.substring(0, 50))}${messagePreview.length > 50 ? '...' : ''}</div>
                </div>
                ${conv.unread > 0 ? `<div class="unread-badge">${conv.unread}</div>` : ''}
            </div>
        `;
            } catch (error) {
                console.error('Error rendering conversation:', error);
                return '';
            }
        }).filter(html => html).join('');
    }
}

function selectConversation(recipientId, recipientName) {
    if (!recipientId || !recipientName) {
        console.error('Invalid recipient:', recipientId, recipientName);
        return;
    }

    currentRecipient = { id: recipientId, username: recipientName };

    // Update header
    const headerEl = document.getElementById('currentRecipient');
    const avatarEl = document.getElementById('currentRecipientAvatar');
    if (headerEl) headerEl.textContent = recipientName;
    if (avatarEl) avatarEl.textContent = recipientName[0].toUpperCase();

    // Enable input
    const inputEl = document.getElementById('messageInput');
    const sendBtn = document.getElementById('sendBtn');
    if (inputEl) inputEl.disabled = false;
    if (sendBtn) sendBtn.disabled = false;

    // Display messages
    displayConversationMessages(recipientId);

    // Mark messages as read
    markMessagesAsRead(recipientId);

    // Update active state
    updateConversationsList();
}

function displayConversationMessages(recipientId) {
    const container = document.getElementById('messagesDisplay');
    if (!container) return;

    const messages = [...(messagesData.sent || []), ...(messagesData.received || [])]
        .filter(msg => {
            try {
                return msg && msg.sender && msg.recipient &&
                    ((msg.sender.id === currentUserId && msg.recipient.id === recipientId) ||
                     (msg.sender.id === recipientId && msg.recipient.id === currentUserId));
            } catch (error) {
                return false;
            }
        })
        .sort((a, b) => new Date(a.created_at) - new Date(b.created_at));

    if (messages.length === 0) {
        container.innerHTML = `<div style="text-align: center; padding: 50px; color: #8898aa;" data-i18n="messages.start_conversation">${t('messages.start_conversation', 'Start the conversation!')}</div>`;
    } else {
        container.innerHTML = messages.map(msg => {
            try {
                const isSent = msg.sender && msg.sender.id === currentUserId;
                const time = formatMessageTime(msg.created_at);
                const senderPrefix = isSent ? t('messages.you', 'You') : (msg.sender.username || 'Unknown');

                return `
                    <div class="message-bubble ${isSent ? 'message-sent' : 'message-received'}">
                        <div style="font-size: 12px; font-weight: 600; margin-bottom: 5px; opacity: 0.8;">${escapeHtml(senderPrefix)}</div>
                        <div>${escapeHtml(msg.content || '')}</div>
                        <div class="message-time">${time}</div>
                    </div>
                `;
            } catch (error) {
                console.error('Error rendering message:', error);
                return '';
            }
        }).filter(html => html).join('');

        // Scroll to bottom
        setTimeout(() => {
            container.scrollTop = container.scrollHeight;
        }, 0);
    }
}

async function sendMessage() {
    const input = document.getElementById('messageInput');
    if (!input) return;

    const content = input.value.trim();

    if (!content || !currentRecipient) {
        console.error('No content or recipient');
        return;
    }

    try {
        const response = await fetch('/api/messages', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'include',
            body: JSON.stringify({
                recipient_id: currentRecipient.id,
                content: content
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        input.value = '';

        // Reload messages
        await loadMessages();

        // Reselect conversation to show new message
        if (currentRecipient) {
            displayConversationMessages(currentRecipient.id);
        }
    } catch (error) {
        console.error('Error sending message:', error);
        showNotification(t('error.sending_message', 'Error sending message'), 'error');
    }
}

async function markMessagesAsRead(recipientId) {
    try {
        await fetch(`/api/messages/read/${recipientId}`, {
            method: 'POST',
            credentials: 'include'
        });
    } catch (error) {
        console.error('Error marking messages as read:', error);
    }
}

// Notification function
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 15px 25px;
        background: ${type === 'success' ? 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' : '#ff6b6b'};
        color: white;
        border-radius: 10px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        z-index: 10000;
        animation: slideIn 0.3s ease;
    `;
    notification.textContent = message;
    document.body.appendChild(notification);

    setTimeout(() => notification.remove(), 3000);
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', async () => {
    // Wait for i18n
    await waitForI18n();

    // Apply initial translations
    if (window.i18n && window.i18n.applyLanguage) {
        window.i18n.applyLanguage();
    }

    // Get current user
    await getCurrentUser();

    // Load data based on page
    if (document.getElementById('conversationsList')) {
        loadMessages();
    }

    if (document.getElementById('generalMembers')) {
        loadCircles();
    }

    // Add event listener for Enter key in message input
    const messageInput = document.getElementById('messageInput');
    if (messageInput) {
        messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
    }

    // Close search results when clicking outside
    document.addEventListener('click', (e) => {
        const searchResults = document.getElementById('searchResults');
        const searchInput = document.getElementById('userSearchInput');
        if (searchResults && !searchResults.contains(e.target) && e.target !== searchInput) {
            searchResults.classList.remove('active');
        }
    });

    // Re-apply translations when language changes
       window.addEventListener('languageChanged', () => {
        if (window.i18n && window.i18n.applyLanguage) {
            window.i18n.applyLanguage();
        }

        // Reload conversations to apply new time translations
        if (document.getElementById('conversationsList')) {
            loadMessages();
            if (currentRecipient && currentRecipient.id) {
                displayConversationMessages(currentRecipient.id);
            }
        }

        // Reload circles to apply new translations
        if (document.getElementById('generalMembers')) {
            updateCirclesDisplay();
        }
    });
});