// Complete Utility Functions for TheraSocial
// utilities.js - Full Implementation

// Show success message toast
function showSuccess(message, duration = 3000) {
    removeExistingToasts();

    const toast = document.createElement('div');
    toast.className = 'toast toast-success';
    toast.innerHTML = `
        <span class="toast-icon">✓</span>
        <span class="toast-message">${message}</span>
    `;

    document.body.appendChild(toast);

    // Trigger animation
    setTimeout(() => toast.classList.add('show'), 10);

    // Auto-remove
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

// Show error message toast
function showError(message, duration = 4000) {
    removeExistingToasts();

    const toast = document.createElement('div');
    toast.className = 'toast toast-error';
    toast.innerHTML = `
        <span class="toast-icon">✗</span>
        <span class="toast-message">${message}</span>
    `;

    document.body.appendChild(toast);

    // Trigger animation
    setTimeout(() => toast.classList.add('show'), 10);

    // Auto-remove
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

// Show info message toast
function showInfo(message, duration = 3000) {
    removeExistingToasts();

    const toast = document.createElement('div');
    toast.className = 'toast toast-info';
    toast.innerHTML = `
        <span class="toast-icon">ℹ</span>
        <span class="toast-message">${message}</span>
    `;

    document.body.appendChild(toast);

    // Trigger animation
    setTimeout(() => toast.classList.add('show'), 10);

    // Auto-remove
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

// Remove existing toasts
function removeExistingToasts() {
    document.querySelectorAll('.toast').forEach(toast => {
        toast.remove();
    });
}

// Format date for display
function formatDate(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diff = now - date;

    const seconds = Math.floor(diff / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);

    if (days > 7) {
        // Return formatted date
        return date.toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined
        });
    } else if (days > 1) {
        return `${days} days ago`;
    } else if (days === 1) {
        return 'Yesterday';
    } else if (hours > 1) {
        return `${hours} hours ago`;
    } else if (hours === 1) {
        return '1 hour ago';
    } else if (minutes > 1) {
        return `${minutes} minutes ago`;
    } else if (minutes === 1) {
        return '1 minute ago';
    } else {
        return 'Just now';
    }
}

// Format date for input fields
function formatDateForInput(date) {
    const d = new Date(date);
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

// Debounce function for search/typing inputs
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Throttle function for scroll/resize events
function throttle(func, limit) {
    let inThrottle;
    return function() {
        const args = arguments;
        const context = this;
        if (!inThrottle) {
            func.apply(context, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

// API request wrapper with error handling
async function apiRequest(url, options = {}) {
    try {
        const defaultOptions = {
            credentials: 'include',
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            }
        };

        const response = await fetch(url, { ...defaultOptions, ...options });

        if (!response.ok) {
            const error = await response.json().catch(() => ({ error: 'Request failed' }));
            throw new Error(error.error || error.message || 'Request failed');
        }

        return await response.json();
    } catch (error) {
        console.error('API request failed:', error);
        showError(error.message || 'Request failed. Please try again.');
        throw error;
    }
}

// Check authentication status
async function checkAuth() {
    try {
        const response = await fetch('/api/auth/session', {
            credentials: 'include'
        });
        return response.ok;
    } catch (error) {
        console.error('Auth check failed:', error);
        return false;
    }
}

// Redirect to login if not authenticated
async function requireAuth() {
    const isAuthenticated = await checkAuth();
    if (!isAuthenticated) {
        window.location.href = '/';
        return false;
    }
    return true;
}

// Load user preferences from localStorage
function loadUserPreferences() {
    const preferences = localStorage.getItem('userPreferences');
    return preferences ? JSON.parse(preferences) : {
        theme: 'light',
        language: 'en',
        notifications: true,
        autoSave: true
    };
}

// Save user preferences to localStorage
function saveUserPreferences(preferences) {
    localStorage.setItem('userPreferences', JSON.stringify(preferences));
}

// Get cookie value by name
function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
    return null;
}

// Set cookie
function setCookie(name, value, days = 7) {
    const date = new Date();
    date.setTime(date.getTime() + (days * 24 * 60 * 60 * 1000));
    const expires = `expires=${date.toUTCString()}`;
    document.cookie = `${name}=${value};${expires};path=/`;
}

// Delete cookie
function deleteCookie(name) {
    document.cookie = `${name}=;expires=Thu, 01 Jan 1970 00:00:00 GMT;path=/`;
}

// Copy text to clipboard
async function copyToClipboard(text) {
    try {
        if (navigator.clipboard && window.isSecureContext) {
            await navigator.clipboard.writeText(text);
        } else {
            // Fallback for older browsers
            const textArea = document.createElement('textarea');
            textArea.value = text;
            textArea.style.position = 'fixed';
            textArea.style.left = '-999999px';
            document.body.appendChild(textArea);
            textArea.focus();
            textArea.select();
            document.execCommand('copy');
            textArea.remove();
        }
        showSuccess('Copied to clipboard!');
        return true;
    } catch (error) {
        console.error('Failed to copy:', error);
        showError('Failed to copy to clipboard');
        return false;
    }
}

// Validate email address
function validateEmail(email) {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
}

// Validate password strength
function validatePassword(password) {
    const minLength = password.length >= 8;
    const hasUpperCase = /[A-Z]/.test(password);
    const hasLowerCase = /[a-z]/.test(password);
    const hasNumbers = /\d/.test(password);
    const hasSpecialChar = /[!@#$%^&*(),.?":{}|<>]/.test(password);

    const strength = {
        valid: minLength,
        score: 0,
        feedback: []
    };

    if (!minLength) strength.feedback.push('At least 8 characters required');
    if (hasUpperCase) strength.score++;
    else strength.feedback.push('Add uppercase letters');
    if (hasLowerCase) strength.score++;
    else strength.feedback.push('Add lowercase letters');
    if (hasNumbers) strength.score++;
    else strength.feedback.push('Add numbers');
    if (hasSpecialChar) strength.score++;
    else strength.feedback.push('Add special characters');

    return strength;
}

// Generate random ID
function generateId() {
    return '_' + Math.random().toString(36).substr(2, 9);
}

// Smooth scroll to element
function smoothScrollTo(elementId, offset = 0) {
    const element = document.getElementById(elementId);
    if (element) {
        const top = element.getBoundingClientRect().top + window.pageYOffset - offset;
        window.scrollTo({
            top: top,
            behavior: 'smooth'
        });
    }
}

// Request browser notification permission
async function requestNotificationPermission() {
    if (!('Notification' in window)) {
        console.log('This browser does not support notifications');
        return false;
    }

    if (Notification.permission === 'granted') {
        return true;
    }

    if (Notification.permission !== 'denied') {
        const permission = await Notification.requestPermission();
        return permission === 'granted';
    }

    return false;
}

// Show browser notification
function showNotification(title, body, icon = '/static/img/icon.png') {
    if (Notification.permission === 'granted') {
        new Notification(title, {
            body: body,
            icon: icon,
            badge: icon,
            vibrate: [200, 100, 200],
            tag: 'therasocial-notification',
            renotify: true
        });
    }
}

// Initialize tooltips
function initTooltips() {
    document.querySelectorAll('[data-tooltip]').forEach(element => {
        element.addEventListener('mouseenter', showTooltip);
        element.addEventListener('mouseleave', hideTooltip);
    });
}

function showTooltip(event) {
    const text = event.target.dataset.tooltip;
    const tooltip = document.createElement('div');
    tooltip.className = 'tooltip';
    tooltip.textContent = text;
    document.body.appendChild(tooltip);

    const rect = event.target.getBoundingClientRect();
    tooltip.style.top = `${rect.top - tooltip.offsetHeight - 5}px`;
    tooltip.style.left = `${rect.left + (rect.width - tooltip.offsetWidth) / 2}px`;

    event.target._tooltip = tooltip;
}

function hideTooltip(event) {
    if (event.target._tooltip) {
        event.target._tooltip.remove();
        delete event.target._tooltip;
    }
}

// Add toast styles dynamically
const utilityStyles = document.createElement('style');
utilityStyles.textContent = `
    .toast {
        position: fixed;
        top: 20px;
        right: 20px;
        min-width: 250px;
        max-width: 400px;
        padding: 16px 20px;
        background: white;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        display: flex;
        align-items: center;
        gap: 12px;
        opacity: 0;
        transform: translateX(400px);
        transition: all 0.3s ease;
        z-index: 100000;
    }

    .toast.show {
        opacity: 1;
        transform: translateX(0);
    }

    .toast-icon {
        font-size: 20px;
        font-weight: bold;
        width: 24px;
        height: 24px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 50%;
    }

    .toast-success {
        background: #4caf50;
        color: white;
    }

    .toast-error {
        background: #f44336;
        color: white;
    }

    .toast-info {
        background: #2196f3;
        color: white;
    }

    .toast-message {
        flex: 1;
        line-height: 1.5;
    }

    .tooltip {
        position: absolute;
        background: #333;
        color: white;
        padding: 6px 12px;
        border-radius: 4px;
        font-size: 14px;
        white-space: nowrap;
        z-index: 10000;
        pointer-events: none;
    }

    .tooltip::after {
        content: '';
        position: absolute;
        top: 100%;
        left: 50%;
        margin-left: -5px;
        border-width: 5px;
        border-style: solid;
        border-color: #333 transparent transparent transparent;
    }

    @media (max-width: 768px) {
        .toast {
            right: 10px;
            left: 10px;
            max-width: none;
        }
    }
`;

document.head.appendChild(utilityStyles);

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    initTooltips();
});

// Export for use in other modules
window.TheraSocialUtils = {
    showSuccess,
    showError,
    showInfo,
    formatDate,
    formatDateForInput,
    debounce,
    throttle,
    apiRequest,
    checkAuth,
    requireAuth,
    loadUserPreferences,
    saveUserPreferences,
    getCookie,
    setCookie,
    deleteCookie,
    copyToClipboard,
    validateEmail,
    validatePassword,
    generateId,
    smoothScrollTo,
    requestNotificationPermission,
    showNotification
};