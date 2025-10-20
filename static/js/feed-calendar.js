/**
 * Feed Calendar functionality with i18n support
 * Adds calendar date picker to feed page for saving/loading daily activity
 */

// Use translation function helper
const t = (key) => window.i18n ? window.i18n.translate(key) : key;

document.addEventListener('DOMContentLoaded', function() {
    // Check if we're on the feed page
    const feedSection = document.getElementById('feedSection');
    if (!feedSection) return;

    // Add calendar controls to feed page
    addCalendarToFeed();
});

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

async function loadParametersForDate(date) {
    try {
        const response = await fetch(`/api/parameters/load/${date}`);
        const result = await response.json();

        if (result.success && result.data) {
            // Update mood selector if parameters have mood data
            if (result.data.mood && !document.getElementById('dailyMood').value) {
                // Map parameter moods to daily mood options if possible
                const moodMap = {
                    'happy': t('mood.happy'),
                    'good': t('mood.good'),
                    'okay': t('mood.okay'),
                    'sad': t('mood.sad'),
                    'anxious': t('mood.anxious'),
                    'tired': t('mood.tired'),
                    'frustrated': t('mood.frustrated'),
                    'hopeful': t('mood.hopeful')
                };

                const mappedMood = moodMap[result.data.mood.toLowerCase()];
                if (mappedMood) {
                    document.getElementById('dailyMood').value = mappedMood;
                }
            }

            // Add parameter notes to daily notes if available
            if (result.data.notes && !document.getElementById('dailyNotes').value) {
                document.getElementById('dailyNotes').value = result.data.notes;
            }
        }
    } catch (error) {
        console.error('Error loading parameters:', error);
    }
}

async function loadSavedDates() {
    try {
        // Try to get dates from both parameters and activities
        const response = await fetch('/api/parameters/dates');
        const data = await response.json();

        if (data.dates && data.dates.length > 0) {
            const datesList = document.getElementById('savedDatesList');
            datesList.innerHTML = '';

            // Sort dates in descending order
            data.dates.sort((a, b) => new Date(b) - new Date(a));

            // Show last 10 dates
            data.dates.slice(0, 10).forEach(date => {
                const dateBtn = document.createElement('button');
                dateBtn.className = 'date-chip';
                dateBtn.style.cssText = 'padding: 5px 10px; background: #e0e7ff; color: #4c1d95; border: none; border-radius: 15px; cursor: pointer; font-size: 12px;';
                dateBtn.textContent = formatDate(date);
                dateBtn.onclick = () => {
                    document.getElementById('activityDate').value = date;
                    loadActivityData(date);
                };
                datesList.appendChild(dateBtn);
            });

            if (data.dates.length > 10) {
                const moreText = document.createElement('span');
                moreText.style.cssText = 'padding: 5px 10px; color: #6b7280; font-size: 12px;';
                moreText.textContent = `+${data.dates.length - 10} ${t('feed.more_dates')}`;
                datesList.appendChild(moreText);
            }
        } else {
            document.getElementById('savedDatesList').innerHTML =
                `<p style="color: #6b7280; font-size: 14px;">${t('feed.no_saved_activity')}</p>`;
        }
    } catch (error) {
        console.error('Error loading saved dates:', error);
    }
}

function resetActivityDisplay() {
    document.getElementById('postCount').textContent = '0';
    document.getElementById('messageCount').textContent = '0';
    document.getElementById('commentCount').textContent = '0';
    document.getElementById('dailyMood').value = '';
    document.getElementById('dailyNotes').value = '';
}

function showStatus(message, type) {
    const statusDiv = document.getElementById('activityStatus');
    const colors = {
        success: '#10b981',
        error: '#ef4444',
        warning: '#f59e0b',
        info: '#3b82f6'
    };

    statusDiv.innerHTML = `
        <div style="padding: 10px; background: ${colors[type]}20; color: ${colors[type]}; border-radius: 5px; margin-top: 10px;">
            ${message}
        </div>
    `;

    setTimeout(() => {
        statusDiv.innerHTML = '';
    }, 3000);
}

function formatDate(dateStr) {
    const date = new Date(dateStr);
    const monthIndex = date.getMonth(); // 0-11
    const dayIndex = date.getDay(); // 0-6 (Sunday-Saturday)
    const dayOfMonth = date.getDate();
    const year = date.getFullYear();

    // Get translated day and month names using i18n
    const dayNames = ['sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat'];
    const translatedDay = t('day.' + dayNames[dayIndex]);
    const translatedMonth = t('calendar.' + monthIndex);

    // Format: "Mon, Oct 20, 2025" or "ב', אוק 20, 2025"
    return `${translatedDay}, ${translatedMonth} ${dayOfMonth}, ${year}`;
}

// Track post and message counts in real-time
function incrementPostCount() {
    const countEl = document.getElementById('postCount');
    if (countEl) {
        countEl.textContent = parseInt(countEl.textContent) + 1;
    }
}

function incrementMessageCount() {
    const countEl = document.getElementById('messageCount');
    if (countEl) {
        countEl.textContent = parseInt(countEl.textContent) + 1;
    }
}

// Export functions for use by other scripts
window.feedCalendar = {
    incrementPostCount,
    incrementMessageCount
};