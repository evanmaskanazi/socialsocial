// Feed Calendar System with Circle Name Mapping Support
// Complete version with all original functionality preserved

// Translation helper
// Feed Calendar System with Circle Name Mapping Support
// Complete version with all original functionality preserved

// Translation helper
const t = (key) => window.i18n ? window.i18n.translate(key) : key;

// Circle name mapping for feed - supports both old and new naming conventions
const FEED_CIRCLE_MAP = {
    'general': 'public',
    'close_friends': 'class_b',
    'family': 'class_a',
    'private': 'private',
    'public': 'public',
    'class_b': 'class_b',
    'class_a': 'class_a',
    1: 'public',
    2: 'class_b',
    3: 'class_a',
    4: 'private'
};

// Helper function to normalize circle names
function normalizeCircleName(circle) {
    return FEED_CIRCLE_MAP[circle] || circle;
}

// Helper to get display name for circles (also exported as getDisplayName for compatibility)
function getCircleDisplayName(circle) {
    const normalized = normalizeCircleName(circle);
    const displayMap = {
        'public': 'Public',
        'class_b': 'Class B (Friends)',
        'class_a': 'Class A (Family)',
        'private': 'Private',
        'general': 'Public',
        'close_friends': 'Class B (Friends)',
        'family': 'Class A (Family)',
        1: 'Public',
        2: 'Class B (Friends)',
        3: 'Class A (Family)',
        4: 'Private'
    };
    return displayMap[normalized] || displayMap[circle] || circle;
}

// Alias for compatibility with other modules
function getDisplayName(internalName) {
    return getCircleDisplayName(internalName);
}

let currentFeedDate = new Date();
let feedData = {};

// Format date for API calls
function formatFeedDate(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

// Format date for display
function formatDate(dateStr) {
    const date = new Date(dateStr);
    return date.toLocaleDateString();
}

// YOUR ORIGINAL addCalendarToFeed function - PRESERVED COMPLETELY
function addCalendarToFeed() {
    const feedSection = document.getElementById('feedSection');

    // Create calendar container
    const calendarHtml = `
        <div class="calendar-container" style="background: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
            <h3 style="color: #6366f1; margin-bottom: 15px;">
                <i class="fas fa-calendar-alt"></i> <span data-i18n="feed.calendar_title">${t('feed.calendar_title')}</span>
            </h3>

            <div class="date-controls" style="display: flex; gap: 10px; margin-bottom: 15px; flex-wrap: wrap;">
                <input type="date" id="activityDate" class="form-input" style="flex: 1; min-width: 200px;">
                <button id="loadActivityBtn" class="btn btn-secondary" style="padding: 10px 20px;">
                    <i class="fas fa-download"></i> <span data-i18n="feed.load_day">${t('feed.load_day')}</span>
                </button>
                <button id="saveActivityBtn" class="btn btn-primary" style="padding: 10px 20px;">
                    <i class="fas fa-save"></i> <span data-i18n="feed.save_day">${t('feed.save_day')}</span>
                </button>
                <button id="todayBtn" class="btn btn-outline" style="padding: 10px 20px;">
                    <span data-i18n="feed.today">${t('feed.today')}</span>
                </button>
            </div>

            <div id="activityStatus" style="margin-top: 10px;"></div>

            <!-- Daily mood and notes -->
            <div class="daily-mood-section" style="margin-top: 20px; padding: 15px; background: #f8f9fa; border-radius: 8px;">
                <h4 style="color: #6366f1; margin-bottom: 10px;" data-i18n="feed.mood_notes">${t('feed.mood_notes')}</h4>

                <div style="display: grid; gap: 15px;">
                    <div>
                        <label style="display: block; margin-bottom: 5px; font-weight: 500;" data-i18n="feed.how_feeling">${t('feed.how_feeling')}</label>
                        <select id="dailyMood" class="form-input" style="width: 100%;">
                            <option value="" data-i18n="feed.select_mood">${t('feed.select_mood')}</option>
                            <option value="😊 Great" data-i18n="mood.great">${t('mood.great')}</option>
                            <option value="🙂 Good" data-i18n="mood.good">${t('mood.good')}</option>
                            <option value="😐 Okay" data-i18n="mood.okay">${t('mood.okay')}</option>
                            <option value="😔 Down" data-i18n="mood.down">${t('mood.down')}</option>
                            <option value="😰 Anxious" data-i18n="mood.anxious">${t('mood.anxious')}</option>
                            <option value="😴 Tired" data-i18n="mood.tired">${t('mood.tired')}</option>
                            <option value="😡 Frustrated" data-i18n="mood.frustrated">${t('mood.frustrated')}</option>
                            <option value="🤗 Hopeful" data-i18n="mood.hopeful">${t('mood.hopeful')}</option>
                        </select>
                    </div>

                    <div>
                        <label style="display: block; margin-bottom: 5px; font-weight: 500;" data-i18n="feed.daily_reflection">${t('feed.daily_reflection')}</label>
                        <textarea id="dailyNotes" class="form-input" rows="3" style="width: 100%;"
                                  data-i18n-placeholder="feed.reflection_placeholder" placeholder="${t('feed.reflection_placeholder')}"></textarea>
                    </div>
                </div>
            </div>

            <!-- Activity summary -->
            <div class="activity-summary" style="margin-top: 20px; display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px;">
                <div class="stat-card" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 15px; border-radius: 8px;">
                    <div style="font-size: 24px; font-weight: bold;" id="postCount">0</div>
                    <div style="opacity: 0.9;" data-i18n="feed.posts_today">${t('feed.posts_today')}</div>
                </div>
                <div class="stat-card" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); color: white; padding: 15px; border-radius: 8px;">
                    <div style="font-size: 24px; font-weight: bold;" id="messageCount">0</div>
                    <div style="opacity: 0.9;" data-i18n="feed.messages_sent">${t('feed.messages_sent')}</div>
                </div>
                <div class="stat-card" style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); color: white; padding: 15px; border-radius: 8px;">
                    <div style="font-size: 24px; font-weight: bold;" id="commentCount">0</div>
                    <div style="opacity: 0.9;" data-i18n="feed.comments_made">${t('feed.comments_made')}</div>
                </div>
            </div>

            <!-- Calendar view with saved dates -->
            <div class="saved-dates" style="margin-top: 20px;">
                <h4 style="color: #6366f1; margin-bottom: 10px;">📅 <span data-i18n="feed.activity_history">${t('feed.activity_history')}</span></h4>
                <div id="savedDatesList" style="display: flex; flex-wrap: wrap; gap: 5px;"></div>
            </div>
        </div>
    `;

    // Insert calendar at the top of feed section
    const feedHeader = feedSection.querySelector('h2');
    if (feedHeader) {
        feedHeader.insertAdjacentHTML('afterend', calendarHtml);
    } else {
        feedSection.insertAdjacentHTML('afterbegin', calendarHtml);
    }

    // Set today's date as default
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('activityDate').value = today;

    // Add event listeners
    setupCalendarEventListeners();

    // Load saved dates
    loadSavedDates();

    // Load today's data
    loadActivityData(today);
}

function setupCalendarEventListeners() {
    // Today button
    document.getElementById('todayBtn').addEventListener('click', function() {
        const today = new Date().toISOString().split('T')[0];
        document.getElementById('activityDate').value = today;
        loadActivityData(today);
    });

    // Load activity button
    document.getElementById('loadActivityBtn').addEventListener('click', function() {
        const date = document.getElementById('activityDate').value;
        if (date) {
            loadActivityData(date);
        } else {
            showStatus(t('feed.select_date'), 'warning');
        }
    });

    // Save activity button
    document.getElementById('saveActivityBtn').addEventListener('click', function() {
        const date = document.getElementById('activityDate').value;
        if (date) {
            saveActivityData(date);
        } else {
            showStatus(t('feed.select_date'), 'warning');
        }
    });

    // Date change
    document.getElementById('activityDate').addEventListener('change', function() {
        loadActivityData(this.value);
    });
}

async function loadActivityData(date) {
    try {
        const response = await fetch(`/api/activity/${date}`);
        const data = await response.json();

        if (response.ok) {
            // Update counts
            document.getElementById('postCount').textContent = data.post_count || 0;
            document.getElementById('messageCount').textContent = data.message_count || 0;
            document.getElementById('commentCount').textContent = data.comment_count || 0;

            // Load mood entries
            if (data.mood_entries && data.mood_entries.length > 0) {
                const latestMood = data.mood_entries[data.mood_entries.length - 1];
                document.getElementById('dailyMood').value = latestMood.mood || '';
                document.getElementById('dailyNotes').value = latestMood.note || '';
            } else {
                document.getElementById('dailyMood').value = '';
                document.getElementById('dailyNotes').value = '';
            }

            // Also try to load parameters if they exist
            loadParametersForDate(date);

            showStatus(`${t('feed.loaded_activity')} ${formatDate(date)}`, 'success');
        } else {
            showStatus(t('feed.no_activity'), 'info');
            resetActivityDisplay();
        }
    } catch (error) {
        console.error('Error loading activity:', error);
        showStatus(t('error.loading'), 'error');
    }
}

async function saveActivityData(date) {
    try {
        const mood = document.getElementById('dailyMood').value;
        const notes = document.getElementById('dailyNotes').value;

        // Get current counts from display (these would be updated by actual posting/messaging)
        const postCount = parseInt(document.getElementById('postCount').textContent) || 0;
        const messageCount = parseInt(document.getElementById('messageCount').textContent) || 0;
        const commentCount = parseInt(document.getElementById('commentCount').textContent) || 0;

        const data = {
            post_count: postCount,
            message_count: messageCount,
            comment_count: commentCount
        };

        // Add mood entry if provided
        if (mood || notes) {
            data.mood_entry = {
                mood: mood,
                note: notes
            };
        }

        const response = await fetch(`/api/activity/${date}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });

        if (response.ok) {
            showStatus(`${t('feed.activity_saved')} ${formatDate(date)}`, 'success');
            loadSavedDates(); // Refresh saved dates list
        } else {
            showStatus(t('error.saving'), 'error');
        }
    } catch (error) {
        console.error('Error saving activity:', error);
        showStatus(t('error.saving'), 'error');
    }
}

// Helper functions
function showStatus(message, type = 'info') {
    const statusEl = document.getElementById('activityStatus');
    if (statusEl) {
        statusEl.innerHTML = `<div class="alert alert-${type}">${message}</div>`;
        setTimeout(() => {
            statusEl.innerHTML = '';
        }, 3000);
    }
}

function resetActivityDisplay() {
    document.getElementById('postCount').textContent = '0';
    document.getElementById('messageCount').textContent = '0';
    document.getElementById('commentCount').textContent = '0';
    document.getElementById('dailyMood').value = '';
    document.getElementById('dailyNotes').value = '';
}

async function loadSavedDates() {
    try {
        const response = await fetch('/api/activity/dates');
        if (response.ok) {
            const dates = await response.json();
            displaySavedDates(dates);
        }
    } catch (error) {
        console.error('Error loading saved dates:', error);
    }
}

function displaySavedDates(dates) {
    const container = document.getElementById('savedDatesList');
    if (!container) return;

    if (!dates || dates.length === 0) {
        container.innerHTML = '<span style="color: #999;">' + t('feed.no_saved_dates') + '</span>';
        return;
    }

    container.innerHTML = dates.map(date => `
        <button class="date-chip" onclick="loadActivityData('${date}')"
                style="padding: 5px 10px; background: #e0e7ff; color: #4c51bf; border: none; border-radius: 20px; cursor: pointer;">
            ${formatDate(date)}
        </button>
    `).join('');
}

async function loadParametersForDate(date) {
    // Integration with parameters system if available
    if (window.loadParameters && typeof window.loadParameters === 'function') {
        try {
            await window.loadParameters(date, false); // false to not show message
        } catch (error) {
            console.log('Parameters not available for this date');
        }
    }
}

// Feed posts with circle mapping
async function loadFeedForDate(date) {
    const dateStr = formatFeedDate(date);

    try {
        const response = await fetch(`/api/feed?date=${dateStr}`);
        if (!response.ok) {
            console.error('Failed to load feed');
            return;
        }

        const data = await response.json();

        // Normalize circle names in the response
        if (data.posts) {
            data.posts = data.posts.map(post => {
                if (post.circle) {
                    post.circle = normalizeCircleName(post.circle);
                }
                return post;
            });
        }

        feedData[dateStr] = data;
        displayFeedPosts(data.posts || []);

    } catch (error) {
        console.error('Error loading feed:', error);
    }
}

// Display feed posts with correct circle names
function displayFeedPosts(posts) {
    const container = document.getElementById('feedContainer');
    if (!container) return;

    if (posts.length === 0) {
        container.innerHTML = `
            <div class="empty-feed">
                <p>${t('feed.no_posts')}</p>
            </div>
        `;
        return;
    }

    container.innerHTML = posts.map(post => {
        // Get display name for the circle
        const circleDisplay = getCircleDisplayName(post.circle);

        return `
            <div class="feed-post" data-post-id="${post.id}">
                <div class="post-header">
                    <div class="post-user">
                        <span class="user-avatar">${post.username ? post.username[0].toUpperCase() : 'U'}</span>
                        <span class="username">${post.username || 'Unknown'}</span>
                    </div>
                    <div class="post-meta">
                        <span class="post-time">${formatPostTime(post.created_at)}</span>
                        <span class="post-visibility" data-circle-display>${circleDisplay}</span>
                    </div>
                </div>
                <div class="post-content">
                    ${post.content || ''}
                </div>
                ${post.parameters ? renderParameters(post.parameters) : ''}
            </div>
        `;
    }).join('');
}

// Create new feed post with circle normalization
async function createFeedPost(content, circle, parameters) {
    // Normalize the circle name before sending to backend
    const normalizedCircle = normalizeCircleName(circle);

    const data = {
        date: formatFeedDate(currentFeedDate),
        content: content,
        circle: normalizedCircle,
        parameters: parameters
    };

    try {
        const response = await fetch('/api/feed', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        });

        if (response.ok) {
            loadFeedForDate(currentFeedDate);
            if (window.showMessage) {
                window.showMessage(t('feed.post_created'), 'success');
            }
            return true;
        }
    } catch (error) {
        console.error('Error creating post:', error);
        if (window.showMessage) {
            window.showMessage(t('feed.post_error'), 'error');
        }
    }
    return false;
}

// Helper functions for feed
function renderParameters(params) {
    if (!params || Object.keys(params).length === 0) return '';

    return `
        <div class="post-parameters">
            ${Object.entries(params).map(([key, value]) => `
                <div class="parameter-item">
                    <span class="param-name">${t(`parameters.${key}`)}:</span>
                    <span class="param-value">${value}</span>
                </div>
            `).join('')}
        </div>
    `;
}

function formatPostTime(timestamp) {
    const date = new Date(timestamp);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

// Export functions
if (typeof window !== 'undefined') {
      window.loadFeedForDate = loadFeedForDate;
    window.createFeedPost = createFeedPost;
    window.addCalendarToFeed = addCalendarToFeed;
    window.loadActivityData = loadActivityData;
    window.saveActivityData = saveActivityData;
    window.getDisplayName = getDisplayName;
    window.getCircleDisplayName = getCircleDisplayName;
    window.normalizeCircleName = normalizeCircleName;
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', function() {
    // Check if we're on the feed page
    const feedSection = document.getElementById('feedSection');
    if (!feedSection) return;

    // Add calendar controls to feed page
    addCalendarToFeed();

    // Apply circle display updates
    if (window.updateCircleDisplays) {
        setTimeout(window.updateCircleDisplays, 100);
    }
});