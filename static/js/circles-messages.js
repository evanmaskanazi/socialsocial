// Circles and Messages Management System with i18n support
// Add this to your main dashboard or create separate pages

// Use translation function helper
const t = (key) => window.i18n ? window.i18n.translate(key) : key;

// ============================================================
// FIX 1: Time formatting function with "just now" support
// ============================================================
function formatMessageTime(timestamp) {
    const now = new Date();
    const msgTime = new Date(timestamp);
    const diffSeconds = Math.floor((now - msgTime) / 1000);

    // Just now (less than 60 seconds)
    if (diffSeconds < 60) {
        return t('messages.just_now');
    }

    // Minutes ago
    if (diffSeconds < 3600) {
        const minutes = Math.floor(diffSeconds / 60);
        return `${minutes} ${t('messages.minutes_ago')}`;
    }

    // Hours ago (same day)
    if (msgTime.toDateString() === now.toDateString()) {
        return msgTime.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }

    // Yesterday
    const yesterday = new Date(now);
    yesterday.setDate(yesterday.getDate() - 1);
    if (msgTime.toDateString() === yesterday.toDateString()) {
        return t('messages.yesterday');
    }

    // Older messages
    return msgTime.toLocaleDateString();
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
        <h1 id="circlesPageTitle">${t('circles.title')}</h1>
        <p style="color: #8898aa;" id="circlesSubtitle">${t('circles.subtitle')}</p>
    </div>

    <div class="user-search">
        <input type="text" class="search-input" id="userSearchInput" placeholder="${t('circles.search_placeholder')}">
        <button class="search-btn" onclick="searchUsers()">🔍</button>
        <div class="search-results" id="searchResults"></div>
    </div>

    <div class="circles-grid">
        <div class="circle-card">
            <div class="circle-header">
                <span class="circle-icon">👥</span>
                <span class="circle-title" id="generalTitle">${t('circles.general')}</span>
                <span class="circle-count" id="generalCount">0</span>
            </div>
            <div class="circle-members" id="generalMembers">
                <div class="empty-state">
                    <div class="empty-state-icon">👥</div>
                    <p id="generalEmpty">${t('circles.no_members')}</p>
                </div>
            </div>
        </div>

        <div class="circle-card">
            <div class="circle-header">
                <span class="circle-icon">❤️</span>
                <span class="circle-title" id="closeFriendsTitle">${t('circles.close_friends')}</span>
                <span class="circle-count" id="closeFriendsCount">0</span>
            </div>
            <div class="circle-members" id="closeFriendsMembers">
                <div class="empty-state">
                    <div class="empty-state-icon">❤️</div>
                    <p id="closeFriendsEmpty">${t('circles.no_members')}</p>
                </div>
            </div>
        </div>

        <div class="circle-card">
            <div class="circle-header">
                <span class="circle-icon">👨‍👩‍👧‍👦</span>
                <span class="circle-title" id="familyTitle">${t('circles.family')}</span>
                <span class="circle-count" id="familyCount">0</span>
            </div>
            <div class="circle-members" id="familyMembers">
                <div class="empty-state">
                    <div class="empty-state-icon">👨‍👩‍👧‍👦</div>
                    <p id="familyEmpty">${t('circles.no_members')}</p>
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
        const response = await fetch('/api/circles');
        if (response.ok) {
            circlesData = await response.json();
            updateCirclesDisplay();
        }
    } catch (error) {
        console.error('Error loading circles:', error);
    }
}

function updateCirclesDisplay() {
    // Update General circle
    updateCircleDisplay('general', circlesData.general, 'generalMembers', 'generalCount');

    // Update Close Friends circle
    updateCircleDisplay('close_friends', circlesData.close_friends, 'closeFriendsMembers', 'closeFriendsCount');

    // Update Family circle
    updateCircleDisplay('family', circlesData.family, 'familyMembers', 'familyCount');
}

function updateCircleDisplay(circleType, members, containerId, countId) {
    const container = document.getElementById(containerId);
    const count = document.getElementById(countId);

    count.textContent = members.length;

    if (members.length === 0) {
        const icon = circleType === 'general' ? '👥' :
                    circleType === 'close_friends' ? '❤️' : '👨‍👩‍👧‍👦';
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">${icon}</div>
                <p>${t('circles.no_members')}</p>
            </div>
        `;
    } else {
        container.innerHTML = members.map(member => `
            <div class="member-item">
                <div class="user-avatar">${member.username[0].toUpperCase()}</div>
                <div class="member-name">${member.username}</div>
                <button class="remove-btn" onclick="removeFromCircle(${member.id}, '${circleType}')">${t('btn.remove')}</button>
            </div>
        `).join('');
    }
}

async function searchUsers() {
    const query = document.getElementById('userSearchInput').value;
    if (query.length < 2) return;

    try {
        const response = await fetch(`/api/users/search?q=${encodeURIComponent(query)}`);
        if (response.ok) {
            const users = await response.json();
            displaySearchResults(users);
        }
    } catch (error) {
        console.error('Error searching users:', error);
    }
}

function displaySearchResults(users) {
    const resultsContainer = document.getElementById('searchResults');

    if (users.length === 0) {
        resultsContainer.innerHTML = `<div class="search-result-item">${t('circles.no_users_found')}</div>`;
    } else {
        resultsContainer.innerHTML = users.map(user => `
            <div class="search-result-item">
                <div class="user-info">
                    <div class="user-avatar">${user.username[0].toUpperCase()}</div>
                    <div>
                        <div style="font-weight: 600;">${user.username}</div>
                        <div style="font-size: 14px; color: #8898aa;">${user.email}</div>
                    </div>
                </div>
                <select class="add-to-circle-btn" onchange="addToCircle(${user.id}, this.value, '${user.username}')">
                    <option value="">${t('circles.add_to_circle')}</option>
                    <option value="general">${t('circles.general')}</option>
                    <option value="close_friends">${t('circles.close_friends')}</option>
                    <option value="family">${t('circles.family')}</option>
                </select>
            </div>
        `).join('');
    }

    resultsContainer.classList.add('active');
}

async function addToCircle(userId, circleType, username) {
    if (!circleType) return;

    try {
        const response = await fetch('/api/circles', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                user_id: userId,
                circle_type: circleType
            })
        });

        if (response.ok) {
            const circleNames = {
                'general': t('circles.general'),
                'close_friends': t('circles.close_friends'),
                'family': t('circles.family')
            };
            showNotification(`${username} ${t('circles.user_added')} ${circleNames[circleType]} ${t('circles.circle')}`, 'success');
            loadCircles();
            document.getElementById('searchResults').classList.remove('active');
            document.getElementById('userSearchInput').value = '';
        } else {
            const error = await response.json();
            showNotification(error.error || t('error.saving'), 'error');
        }
    } catch (error) {
        console.error('Error adding to circle:', error);
    }
}

async function removeFromCircle(userId, circleType) {
    if (!confirm(t('circles.remove_confirm'))) return;

    try {
        const response = await fetch('/api/circles/remove', {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                user_id: userId,
                circle_type: circleType
            })
        });

        if (response.ok) {
            showNotification(t('circles.user_removed'), 'success');
            loadCircles();
        }
    } catch (error) {
        console.error('Error removing from circle:', error);
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

        .new-message-modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.5);
            z-index: 1000;
            align-items: center;
            justify-content: center;
        }

        .new-message-modal.active {
            display: flex;
        }

        .modal-content {
            background: white;
            border-radius: 20px;
            padding: 30px;
            width: 500px;
            max-width: 90%;
        }

        .modal-header {
            font-size: 1.5em;
            font-weight: 600;
            color: #2d3436;
            margin-bottom: 20px;
        }

        .recipient-select {
            width: 100%;
            padding: 12px;
            border: 2px solid #e1e8ed;
            border-radius: 10px;
            font-size: 16px;
            margin-bottom: 20px;
        }

        .modal-actions {
            display: flex;
            gap: 15px;
            justify-content: flex-end;
        }
    </style>

    <div class="conversations-sidebar">
        <div class="sidebar-header">
            <div class="sidebar-title" id="messagesSidebarTitle">${t('messages.title')}</div>
            <button class="new-message-btn" onclick="showNewMessageModal()" id="newMessageBtn">${t('messages.new')}</button>
        </div>
        <div id="conversationsList"></div>
    </div>

    <div class="message-area">
        <div class="message-header">
            <div class="conversation-avatar" id="currentRecipientAvatar">?</div>
            <div class="message-recipient" id="currentRecipient">${t('messages.select_conversation')}</div>
        </div>

        <div class="messages-display" id="messagesDisplay">
            <div style="text-align: center; padding: 50px; color: #8898aa;" id="messagesPlaceholder">
                ${t('messages.select_conversation')}
            </div>
        </div>

        <div class="message-input-area">
            <input type="text" class="message-input" id="messageInput" placeholder="${t('messages.type_message')}" disabled>
            <button class="send-btn" id="sendBtn" onclick="sendMessage()" disabled>${t('messages.send')}</button>
        </div>
    </div>

    <div class="new-message-modal" id="newMessageModal">
        <div class="modal-content">
            <div class="modal-header" id="newMessageModalTitle">${t('messages.new_message')}</div>
            <select class="recipient-select" id="recipientSelect">
                <option value="">${t('messages.select_recipient')}</option>
            </select>
            <textarea class="message-input" id="newMessageText" placeholder="${t('messages.type_message')}" style="width: 100%; min-height: 100px; border-radius: 10px;"></textarea>
            <div class="modal-actions">
                <button class="btn-cancel" onclick="hideNewMessageModal()">${t('btn.cancel')}</button>
                <button class="btn-save" onclick="startNewConversation()">${t('btn.send')}</button>
            </div>
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

async function loadMessages() {
    try {
        const response = await fetch('/api/messages');
        if (response.ok) {
            messagesData = await response.json();
            updateConversationsList();
        }
    } catch (error) {
        console.error('Error loading messages:', error);
    }
}

// ============================================================
// FIX 2: Updated updateConversationsList with translations
// ============================================================
function updateConversationsList() {
    // Group messages by conversation partner
    const conversations = {};

    [...messagesData.sent, ...messagesData.received].forEach(msg => {
        const partnerId = msg.sender.id === currentUserId ? msg.recipient.id : msg.sender.id;
        const partnerName = msg.sender.id === currentUserId ? msg.recipient.username : msg.sender.username;

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
        if (msg.recipient.id === currentUserId && !msg.is_read) {
            conversations[partnerId].unread++;
        }
    });

    // Display conversations
    const container = document.getElementById('conversationsList');
    const conversationArray = Object.values(conversations).sort((a, b) =>
        new Date(b.lastMessage.created_at) - new Date(a.lastMessage.created_at)
    );

    if (conversationArray.length === 0) {
        container.innerHTML = `<div style="text-align: center; padding: 20px; color: #8898aa;">${t('messages.no_conversations')}</div>`;
    } else {
        container.innerHTML = conversationArray.map(conv => {
            // Determine if last message was sent or received
            const lastMsgSent = conv.lastMessage.sender.id === currentUserId;
            const messagePreview = lastMsgSent
                ? `${t('messages.you')}: ${conv.lastMessage.content}`
                : `${t('messages.newMessageFrom')} ${conv.name}: ${conv.lastMessage.content}`;

            return `
                <div class="conversation-item ${currentRecipient?.id === conv.id ? 'active' : ''}" onclick="selectConversation(${conv.id}, '${conv.name}')">
                    <div class="conversation-avatar">${conv.name[0].toUpperCase()}</div>
                    <div class="conversation-info">
                        <div class="conversation-name">${conv.name}</div>
                        <div class="conversation-preview">${messagePreview}</div>
                    </div>
                    ${conv.unread > 0 ? `<div class="unread-badge">${conv.unread}</div>` : ''}
                </div>
            `;
        }).join('');
    }
}

function selectConversation(recipientId, recipientName) {
    currentRecipient = { id: recipientId, username: recipientName };

    // Update header
    document.getElementById('currentRecipient').textContent = recipientName;
    document.getElementById('currentRecipientAvatar').textContent = recipientName[0].toUpperCase();

    // Enable input
    document.getElementById('messageInput').disabled = false;
    document.getElementById('sendBtn').disabled = false;

    // Display messages
    displayConversationMessages(recipientId);

    // Mark messages as read
    markMessagesAsRead(recipientId);

    // Update active state
    updateConversationsList();
}

// ============================================================
// FIX 3: Updated displayConversationMessages with sender prefix and time
// ============================================================
function displayConversationMessages(recipientId) {
    const container = document.getElementById('messagesDisplay');
    const messages = [...messagesData.sent, ...messagesData.received]
        .filter(msg =>
            (msg.sender.id === currentUserId && msg.recipient.id === recipientId) ||
            (msg.sender.id === recipientId && msg.recipient.id === currentUserId)
        )
        .sort((a, b) => new Date(a.created_at) - new Date(b.created_at));

    if (messages.length === 0) {
        container.innerHTML = `<div style="text-align: center; padding: 50px; color: #8898aa;">${t('messages.start_conversation')}</div>`;
    } else {
        container.innerHTML = messages.map(msg => {
            const isSent = msg.sender.id === currentUserId;
            const time = formatMessageTime(msg.created_at);
            const senderPrefix = isSent ? t('messages.you') : msg.sender.username;

            return `
                <div class="message-bubble ${isSent ? 'message-sent' : 'message-received'}">
                    <div style="font-size: 12px; font-weight: 600; margin-bottom: 5px; opacity: 0.8;">${senderPrefix}</div>
                    <div>${msg.content}</div>
                    <div class="message-time">${time}</div>
                </div>
            `;
        }).join('');

        // Scroll to bottom
        container.scrollTop = container.scrollHeight;
    }
}

// ============================================================
// FIX 4: Updated sendMessage with "You" and "Just now"
// ============================================================
async function sendMessage() {
    const input = document.getElementById('messageInput');
    const content = input.value.trim();

    if (!content || !currentRecipient) return;

    try {
        const response = await fetch('/api/messages', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                recipient_id: currentRecipient.id,
                content: content
            })
        });

        if (response.ok) {
            input.value = '';
            loadMessages();

            // Add message to display immediately with translations
            const container = document.getElementById('messagesDisplay');
            const messageHtml = `
                <div class="message-bubble message-sent">
                    <div style="font-size: 12px; font-weight: 600; margin-bottom: 5px; opacity: 0.8;">${t('messages.you')}</div>
                    <div>${content}</div>
                    <div class="message-time">${t('messages.just_now')}</div>
                </div>
            `;
            container.innerHTML += messageHtml;
            container.scrollTop = container.scrollHeight;
        }
    } catch (error) {
        console.error('Error sending message:', error);
    }
}

async function markMessagesAsRead(recipientId) {
    const unreadMessages = messagesData.received.filter(msg =>
        msg.sender.id === recipientId && !msg.is_read
    );

    for (const msg of unreadMessages) {
        try {
            await fetch(`/api/messages/${msg.id}/read`, {
                method: 'PUT'
            });
        } catch (error) {
            console.error('Error marking message as read:', error);
        }
    }
}

async function showNewMessageModal() {
    const modal = document.getElementById('newMessageModal');
    const select = document.getElementById('recipientSelect');

    // Load users for recipient selection
    try {
        const response = await fetch('/api/users/search?q=');
        if (response.ok) {
            const users = await response.json();
            select.innerHTML = `<option value="">${t('messages.select_recipient')}</option>` +
                users.map(user => `<option value="${user.id}">${user.username}</option>`).join('');
        }
    } catch (error) {
        console.error('Error loading users:', error);
    }

    modal.classList.add('active');
}

function hideNewMessageModal() {
    document.getElementById('newMessageModal').classList.remove('active');
    document.getElementById('recipientSelect').value = '';
    document.getElementById('newMessageText').value = '';
}

async function startNewConversation() {
    const recipientId = document.getElementById('recipientSelect').value;
    const content = document.getElementById('newMessageText').value.trim();

    if (!recipientId || !content) {
        alert(t('messages.select_and_type'));
        return;
    }

    try {
        const response = await fetch('/api/messages', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                recipient_id: parseInt(recipientId),
                content: content
            })
        });

        if (response.ok) {
            hideNewMessageModal();
            loadMessages();
            showNotification(t('messages.message_sent'), 'success');
        }
    } catch (error) {
        console.error('Error starting conversation:', error);
    }
}

// Initialize
let currentUserId = null;

async function getCurrentUser() {
    try {
        const response = await fetch('/api/user/profile');
        if (response.ok) {
            const user = await response.json();
            currentUserId = user.id;
        }
    } catch (error) {
        console.error('Error getting current user:', error);
    }
}

// Add event listener for Enter key in message input
document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('messageInput')) {
        document.getElementById('messageInput').addEventListener('keypress', (e) => {
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

    // Initialize
    getCurrentUser().then(() => {
        if (window.location.pathname.includes('circles')) {
            loadCircles();
        }
        if (window.location.pathname.includes('messages')) {
            loadMessages();
        }
    });
});

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