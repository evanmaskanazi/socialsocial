// Complete Follow Requests Management for TheraSocial
// follow-requests.js - Full Implementation

class FollowRequestsManager {
    constructor() {
        this.requests = [];
        this.refreshInterval = null;
        this.initialized = false;
    }

    async init() {
        if (this.initialized) return;

        await this.loadRequests();
        this.render();
        this.startAutoRefresh();
        this.initialized = true;
    }

    startAutoRefresh() {
        // Refresh every 30 seconds
        this.refreshInterval = setInterval(() => {
            this.loadRequests();
        }, 30000);
    }

    stopAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
    }

    async loadRequests() {
        try {
            const response = await fetch('/api/follow-requests/received', {
                credentials: 'include'
            });

            if (response.ok) {
                const data = await response.json();
                const oldCount = this.requests.length;
                this.requests = data.requests || [];

                // Show notification for new requests
                if (this.requests.length > oldCount && oldCount > 0) {
                    this.showNotification('New follow request received!');
                }

                // Update UI
                this.updateBadge();
                if (document.getElementById('follow-requests-container')) {
                    this.render();
                }
            }
        } catch (error) {
            console.error('Error loading follow requests:', error);
        }
    }

    updateBadge() {
        // Update badge on main page
        const badge = document.getElementById('follow-requests-badge');
        if (badge) {
            if (this.requests.length > 0) {
                badge.textContent = this.requests.length;
                badge.style.display = 'inline-block';
            } else {
                badge.style.display = 'none';
            }
        }

        // Update badge in navigation
        const navBadge = document.querySelector('.nav-follow-badge');
        if (navBadge) {
            if (this.requests.length > 0) {
                navBadge.textContent = this.requests.length;
                navBadge.style.display = 'inline-block';
            } else {
                navBadge.style.display = 'none';
            }
        }
    }

    render() {
        const container = document.getElementById('follow-requests-container');
        if (!container) return;

        if (this.requests.length === 0) {
            container.innerHTML = `
                <div class="follow-requests-empty">
                    <div class="empty-icon">👥</div>
                    <h3>No pending follow requests</h3>
                    <p>When someone wants to follow your wellness journey, you'll see their request here.</p>
                    <p class="hint">Share your profile link to invite others to follow you!</p>
                </div>
            `;
            return;
        }

        container.innerHTML = `
            <div class="follow-requests-section">
                <div class="section-header">
                    <h2>Follow Requests (${this.requests.length})</h2>
                    <p class="section-subtitle">Choose what level of access to grant each person</p>
                </div>

                <div class="privacy-explanation">
                    <h4>Privacy Levels Explained:</h4>
                    <div class="privacy-levels">
                        <div class="privacy-level">
                            <span class="privacy-badge public">Public</span>
                            <span>Basic parameters only</span>
                        </div>
                        <div class="privacy-level">
                            <span class="privacy-badge class_b">Class B</span>
                            <span>More details for close friends</span>
                        </div>
                        <div class="privacy-level">
                            <span class="privacy-badge class_a">Class A</span>
                            <span>Full access for family members</span>
                        </div>
                    </div>
                </div>

                <div class="follow-requests-list">
                    ${this.requests.map(request => this.renderRequest(request)).join('')}
                </div>
            </div>
        `;

        // Attach event listeners after rendering
        this.attachEventListeners();
    }

    renderRequest(request) {
        const timeAgo = this.formatTimeAgo(request.created_at);
        const firstLetter = (request.requester_name || 'U').charAt(0).toUpperCase();

        return `
            <div class="follow-request-card" data-request-id="${request.id}">
                <div class="request-avatar">
                    <div class="avatar-circle" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">
                        ${firstLetter}
                    </div>
                </div>

                <div class="request-info">
                    <div class="request-name">${request.requester_name || 'Anonymous User'}</div>
                    <div class="request-time">Requested ${timeAgo}</div>
                </div>

                <div class="request-controls">
                    <div class="privacy-selector-wrapper">
                        <label for="privacy-${request.id}">Grant access:</label>
                        <select class="privacy-select" id="privacy-${request.id}" data-request-id="${request.id}">
                            <option value="public">Public Access</option>
                            <option value="class_b" selected>Class B (Friends)</option>
                            <option value="class_a">Class A (Family)</option>
                        </select>
                    </div>

                    <div class="request-actions">
                        <button class="btn-accept" data-request-id="${request.id}" onclick="followRequestsManager.acceptRequest(${request.id})">
                            ✓ Accept
                        </button>
                        <button class="btn-reject" data-request-id="${request.id}" onclick="followRequestsManager.rejectRequest(${request.id})">
                            ✗ Reject
                        </button>
                    </div>
                </div>
            </div>
        `;
    }

    formatTimeAgo(dateString) {
        const date = new Date(dateString);
        const now = new Date();
        const seconds = Math.floor((now - date) / 1000);

        if (seconds < 60) return 'just now';

        const minutes = Math.floor(seconds / 60);
        if (minutes < 60) return `${minutes} minute${minutes !== 1 ? 's' : ''} ago`;

        const hours = Math.floor(minutes / 60);
        if (hours < 24) return `${hours} hour${hours !== 1 ? 's' : ''} ago`;

        const days = Math.floor(hours / 24);
        if (days < 7) return `${days} day${days !== 1 ? 's' : ''} ago`;

        if (days < 30) {
            const weeks = Math.floor(days / 7);
            return `${weeks} week${weeks !== 1 ? 's' : ''} ago`;
        }

        return date.toLocaleDateString();
    }

    attachEventListeners() {
        // Privacy selector change listeners
        document.querySelectorAll('.privacy-select').forEach(select => {
            select.addEventListener('change', (e) => {
                const requestId = e.target.dataset.requestId;
                console.log(`Privacy level changed to ${e.target.value} for request ${requestId}`);
            });
        });
    }

    async acceptRequest(requestId) {
        const privacySelect = document.querySelector(`#privacy-${requestId}`);
        const privacyLevel = privacySelect ? privacySelect.value : 'public';

        await this.respondToRequest(requestId, 'accept', privacyLevel);
    }

    async rejectRequest(requestId) {
        if (confirm('Are you sure you want to reject this follow request?')) {
            await this.respondToRequest(requestId, 'reject');
        }
    }

    async respondToRequest(requestId, action, privacyLevel = 'public') {
        try {
            const response = await fetch(`/api/follow-requests/${requestId}/respond`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'include',
                body: JSON.stringify({
                    action: action,
                    privacy_level: privacyLevel
                })
            });

            if (response.ok) {
                // Animate card removal
                const card = document.querySelector(`[data-request-id="${requestId}"]`);
                if (card) {
                    card.style.animation = 'slideOut 0.3s ease';
                    setTimeout(() => {
                        // Reload requests after animation
                        this.loadRequests();
                    }, 300);
                }

                // Show success message
                const message = action === 'accept' ?
                    `Follow request accepted! They can now see your ${privacyLevel.replace('_', ' ')} parameters.` :
                    'Follow request rejected.';

                this.showMessage(message, 'success');
            } else {
                const error = await response.json();
                this.showMessage(error.error || `Failed to ${action} request`, 'error');
            }
        } catch (error) {
            console.error(`Error ${action}ing follow request:`, error);
            this.showMessage(`Failed to ${action} request. Please try again.`, 'error');
        }
    }

    showMessage(message, type = 'info') {
        if (typeof showSuccess === 'function' && type === 'success') {
            showSuccess(message);
        } else if (typeof showError === 'function' && type === 'error') {
            showError(message);
        } else {
            // Fallback alert
            alert(message);
        }
    }

    showNotification(message) {
        // Browser notification if permitted
        if ('Notification' in window && Notification.permission === 'granted') {
            new Notification('TheraSocial', {
                body: message,
                icon: '/static/img/icon.png'
            });
        } else {
            this.showMessage(message, 'info');
        }
    }

    // Send a follow request to another user
    async sendFollowRequest(targetUserId) {
        try {
            const response = await fetch('/api/follow-requests', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'include',
                body: JSON.stringify({
                    target_id: targetUserId
                })
            });

            if (response.ok) {
                this.showMessage('Follow request sent! You\'ll be notified when they respond.', 'success');
                return true;
            } else {
                const error = await response.json();
                this.showMessage(error.error || 'Failed to send follow request', 'error');
                return false;
            }
        } catch (error) {
            console.error('Error sending follow request:', error);
            this.showMessage('Failed to send follow request. Please try again.', 'error');
            return false;
        }
    }

    destroy() {
        this.stopAutoRefresh();
        this.initialized = false;
    }
}

// Create global instance
let followRequestsManager;

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    followRequestsManager = new FollowRequestsManager();

    // Auto-initialize if container exists
    if (document.getElementById('follow-requests-container')) {
        followRequestsManager.init();
    } else {
        // Still load for badge updates
        followRequestsManager.loadRequests();
    }
});

// Clean up on page unload
window.addEventListener('beforeunload', () => {
    if (followRequestsManager) {
        followRequestsManager.destroy();
    }
});

// Add animation styles
const followRequestStyles = document.createElement('style');
followRequestStyles.textContent = `
    @keyframes slideOut {
        from {
            opacity: 1;
            transform: translateX(0);
        }
        to {
            opacity: 0;
            transform: translateX(100%);
        }
    }
`;
document.head.appendChild(followRequestStyles);