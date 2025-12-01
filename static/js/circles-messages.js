// Circles and Messages Management System with i18n support
// Complete Fixed Version with null safety and proper error handling

// Translation helper
const translateCircle = (key) => {
    return window.i18n && window.i18n.translate ? window.i18n.translate(key) : key;
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
window.circlesHTML = `
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

.circle-privacy-section {
            max-width: 600px;
            margin: 0 auto 30px;
            padding: 20px;
            background: white;
            border-radius: 15px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
        }

        .circle-privacy-section label {
            display: block;
            font-size: 16px;
            font-weight: 600;
            color: #667eea;
            margin-bottom: 10px;
        }

        .circle-privacy-section .privacy-select {
            width: 100%;
            padding: 12px 15px;
            border: 2px solid #e1e8ed;
            border-radius: 10px;
            font-size: 16px;
            background: white;
            cursor: pointer;
            transition: all 0.3s;
        }

        .circle-privacy-section .privacy-select:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
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
    display: block !important;
    visibility: visible !important;
    z-index: 9999 !important;
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

        <!-- Language Selector -->
        <div style="text-align: center; margin-bottom: 20px;">
            <label for="languageSelect" style="margin-right: 10px; color: #8898aa;" data-i18n="settings.language">Language:</label>
            <select id="languageSelect" onchange="window.i18n.setLanguage(this.value)" style="padding: 8px 15px; border: 2px solid #dfe1e6; border-radius: 8px; font-size: 14px; background: white; cursor: pointer;">
                <option value="en">English</option>
                <option value="he">עברית (Hebrew)</option>
                <option value="ar">العربية (Arabic)</option>
                <option value="ru">Русский (Russian)</option>
            </select>
        </div>

      <!-- Circle Privacy Selector -->
<div class="circle-privacy-section" id="circlesPrivacySelector" style="display: none;">
    <label data-i18n="circles.privacy_label">Circle Visibility</label>
    <select id="circlesPrivacySelect" class="privacy-select" onchange="updateCirclesPrivacy(this.value)">
        <option value="public" data-i18n="privacy.public">Public</option>
        <option value="class_b" data-i18n="privacy.class_b">Close Friends</option>
        <option value="class_a" data-i18n="privacy.class_a">Family</option>
        <option value="private" data-i18n="privacy.private">Private</option>
    </select>
</div>

        <div class="user-search">
        <input type="text" class="search-input" id="userSearchInput" data-i18n="circles.search_placeholder" placeholder="Search users...">
        <button class="search-btn" onclick="searchUsers()">🔍</button>
        <div class="search-results" id="searchResults"></div>
    </div>

    <!-- Recommended Users to Add to Circle Section -->
    <div id="circleRecommendationsSection" style="max-width: 600px; margin: 0 auto 30px; background: white; border-radius: 15px; padding: 20px; box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);">
        <h3 style="color: #667eea; margin-bottom: 15px;" data-i18n="circles.recommended_title">Recommended Users to Add to Circle</h3>
        <div id="circleRecommendationsList" style="max-height: 300px; overflow-y: auto;"></div>
    </div>

<div class="circles-grid">
        <div class="circle-card" data-circle="general">
            <div class="circle-header">
                <span class="circle-icon">👥</span>
                <span class="circle-title" data-i18n="circles.title_public">Public</span>
                <span class="circle-count" id="publicCount">0</span>
            </div>
            <div class="circle-members" id="publicMembers">
                <div class="empty-state">
                    <div class="empty-state-icon">👥</div>
                    <p data-i18n="circles.no_members">No members yet</p>
                </div>
            </div>
        </div>

        <div class="circle-card" data-circle="close_friends">
            <div class="circle-header">
                <span class="circle-icon">❤️</span>
                <span class="circle-title" data-i18n="circles.title_class_b">Close Friends</span>
                <span class="circle-count" id="class_bCount">0</span>
            </div>
            <div class="circle-members" id="class_bMembers">
                <div class="empty-state">
                    <div class="empty-state-icon">❤️</div>
                    <p data-i18n="circles.no_members">No members yet</p>
                </div>
            </div>
        </div>

        <div class="circle-card" data-circle="family">
        <div class="circle-header">
                <span class="circle-icon">👨‍👩‍👧‍👦</span>
                <span class="circle-title" data-i18n="circles.title_class_a">Family</span>
                <span class="circle-count" id="class_aCount">0</span>
            </div>
            <div class="circle-members" id="class_aMembers">
                <div class="empty-state">
                    <div class="empty-state-icon">👨‍👩‍👧‍👦</div>
                    <p data-i18n="circles.no_members">No members yet</p>
                </div>
            </div>
        </div>
    </div>

    <!-- Home Button - INSERT THIS SECTION -->
    <div style="text-align: center; margin-top: 40px; margin-bottom: 20px;">
        <button onclick="window.location.href='/'" style="
            background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
            color: white;
            border: none;
            padding: 15px 40px;
            border-radius: 50px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            box-shadow: 0 4px 15px rgba(40, 167, 69, 0.3);
            transition: all 0.3s ease;
            display: inline-flex;
            align-items: center;
            gap: 10px;
        " onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 6px 20px rgba(40, 167, 69, 0.4)'" onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 15px rgba(40, 167, 69, 0.3)'">
            <span style="font-size: 20px;">🏠</span>
            <span data-i18n="nav.home">Home</span>
        </button>
    </div>
    <!-- End Home Button -->

</div>
`;

// Circles Data Storage - maps backend names to frontend display
let circlesData = {
    general: [],      // Maps to "Public" display
    close_friends: [], // Maps to "Close Friends" display
    family: []        // Maps to "Family" display
};


let isLoadingCircles = false;
let loadCirclesTimeout = null;
// Prevent rapid language switching
let lastLanguageChange = 0;
const LANGUAGE_CHANGE_DELAY = 500; // ms


// NEW: Function to show private circles message
function showPrivateCirclesMessage() {
    const container = document.querySelector('.circles-grid');
    if (container) {
        container.innerHTML = `
            <div style="
                grid-column: 1 / -1;
                text-align: center;
                padding: 40px;
                background: white;
                border-radius: 15px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            ">
                <div style="font-size: 48px; margin-bottom: 20px;">🔒</div>
                <h3 style="color: #667eea; margin-bottom: 10px;">Private Circles</h3>
                <p style="color: #8898aa;">This user's circles are private.</p>
            </div>
        `;
    }
}






// Load circles from backend
// Load circles from backend
async function loadCircles() {
    // Debounce: prevent multiple simultaneous loads
    if (isLoadingCircles) {
        console.log('Already loading circles, skipping duplicate call...');
        return;
    }

    // Clear any pending timeout
    if (loadCirclesTimeout) {
        clearTimeout(loadCirclesTimeout);
    }

    isLoadingCircles = true;

    try {
        // NEW: Check if viewing another user's circles
        const urlParams = new URLSearchParams(window.location.search);
        const viewingUserId = urlParams.get('user_id');

        // CRITICAL: Load privacy setting FIRST before loading circles
        // This ensures the dropdown shows the correct value
        await loadCirclesPrivacy(viewingUserId);

        // Build URL with optional user_id parameter
        let url = '/api/circles';
        if (viewingUserId) {
            url += `?user_id=${viewingUserId}`;
            console.log(`Loading circles for user ${viewingUserId}`);
        } else {
            console.log('Loading own circles');
        }

        const response = await fetch(url);
        if (response.status === 401) {
            window.location.href = '/';
            return;
        }

        const circles = await response.json();

        // Disable/enable privacy dropdown based on viewing context
        const privacySelect = document.getElementById('circlesPrivacySelect');
        if (privacySelect) {
            privacySelect.disabled = viewingUserId ? true : false;
        }



        console.log('Loaded circles data:', circles);

        // Store globally for debugging
        window.circlesData = circles;

        // Check if circles are private
      // Check if circles are private
        if (circles.private) {
            // Display privacy message for all circle types - ALWAYS show the same message
            const publicMembers = document.getElementById('publicMembers');
            const classBMembers = document.getElementById('class_bMembers');
            const classAMembers = document.getElementById('class_aMembers');

           const privateMessage = `
                <div class="empty-state">
                    <div class="empty-state-icon">🔒</div>
                    <p data-i18n="circles.circles_private">Circles set to private</p>
                </div>`;

            // ALWAYS show private message regardless of whether circles have members or not
            if (publicMembers) {
                publicMembers.innerHTML = privateMessage;
            }
            if (classBMembers) {
                classBMembers.innerHTML = privateMessage;
            }
            if (classAMembers) {
                classAMembers.innerHTML = privateMessage;
            }

            // RE-APPLY TRANSLATIONS after setting innerHTML
           // RE-APPLY TRANSLATIONS after setting innerHTML
if (window.i18n && window.i18n.applyLanguage) {
    const currentLang = window.i18n.getCurrentLanguage ? window.i18n.getCurrentLanguage() : 'en';
    console.log('Applying language to private message:', currentLang);
    window.i18n.applyLanguage(currentLang);
}

            // Set counts to 0
            const publicCount = document.getElementById('publicCount');
            const classBCount = document.getElementById('class_bCount');
            const classACount = document.getElementById('class_aCount');
            if (publicCount) publicCount.textContent = '0';
            if (classBCount) classBCount.textContent = '0';
            if (classACount) classACount.textContent = '0';

            return;
}
      // Update display for Public - Backend NOW returns 'public'
        const publicMembers = document.getElementById('publicMembers');
        if (publicMembers) {
            if (circles.public && circles.public.length > 0) {
                publicMembers.innerHTML = '';
                circles.public.forEach(member => {
                    const memberDiv = createMemberElement(member, 'public');
                    publicMembers.appendChild(memberDiv);
                });
            } else {
                publicMembers.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-state-icon">👥</div>
                        <p data-i18n="circles.no_members">No members yet</p>
                    </div>`;
            }
            document.getElementById('publicCount').textContent = circles.public.length || 0;
        }

        // Update display for Class B/Friends - Backend NOW returns 'class_b'
        const classBMembers = document.getElementById('class_bMembers');
        if (classBMembers) {
            if (circles.class_b && circles.class_b.length > 0) {
                classBMembers.innerHTML = '';
                circles.class_b.forEach(member => {
                    const memberDiv = createMemberElement(member, 'class_b');
                    classBMembers.appendChild(memberDiv);
                });
            } else {
                classBMembers.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-state-icon">❤️</div>
                        <p data-i18n="circles.no_members">No members yet</p>
                    </div>`;
            }
            document.getElementById('class_bCount').textContent = circles.class_b.length || 0;
        }

        // Update display for Class A/Family - Backend NOW returns 'class_a'
        const classAMembers = document.getElementById('class_aMembers');
        if (classAMembers) {
            if (circles.class_a && circles.class_a.length > 0) {
                classAMembers.innerHTML = '';
                circles.class_a.forEach(member => {
                    const memberDiv = createMemberElement(member, 'class_a');
                    classAMembers.appendChild(memberDiv);
                });
            } else {
                classAMembers.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-state-icon">👨‍👩‍👧‍👦</div>
                        <p data-i18n="circles.no_members">No members yet</p>
                    </div>`;
            }
            document.getElementById('class_aCount').textContent = circles.class_a.length || 0;
        }

        // Re-apply translations after modifying DOM
        if (window.i18n && window.i18n.applyLanguage) {
            const currentLang = window.i18n.getCurrentLanguage ? window.i18n.getCurrentLanguage() : 'en';
            window.i18n.applyLanguage(currentLang);
        }

        updateCircleTitles();

        // Load circle recommendations
        loadCircleRecommendations();

    } catch (error) {
        console.error('Error loading circles:', error);
        if (window.showMessage) {
            window.showMessage('Error loading circles', 'error');
        }
    } finally {
        // Reset the loading flag after a short delay to prevent rapid successive calls
        loadCirclesTimeout = setTimeout(() => {
            isLoadingCircles = false;
        }, 300);
    }
}



// Load recommended users to add to circles
async function loadCircleRecommendations() {
    console.log('[CircleRecs] ========================================');
    console.log('[CircleRecs] Starting loadCircleRecommendations...');
    console.log('[CircleRecs] Time:', new Date().toISOString());
    
    try {
        const recommendationsContainer = document.getElementById("circleRecommendationsList");
        if (!recommendationsContainer) {
            console.error('[CircleRecs] ERROR: Container #circleRecommendationsList not found in DOM');
            return;
        }
        console.log('[CircleRecs] Container found');

        // Show loading state
        recommendationsContainer.innerHTML = `<p style="color: #8898aa; text-align: center;">Loading recommendations...</p>`;

        console.log('[CircleRecs] Fetching /api/circles/recommendations...');
        const response = await fetch("/api/circles/recommendations", {
            credentials: 'include'
        });
        
        console.log('[CircleRecs] Response status:', response.status);
        console.log('[CircleRecs] Response ok:', response.ok);
        
        if (!response.ok) {
            console.error("[CircleRecs] FAILED to load circle recommendations");
            console.error("[CircleRecs] Status:", response.status);
            const errorText = await response.text();
            console.error("[CircleRecs] Response body:", errorText);
            recommendationsContainer.innerHTML = `<p style="color: #8898aa; text-align: center;" data-i18n="circles.no_recommendations">No recommendations available</p>`;
            return;
        }

        const data = await response.json();
        console.log('[CircleRecs] Response data:', JSON.stringify(data, null, 2));
        
        // Log debug info from backend if available
        if (data.debug) {
            console.log('[CircleRecs] Backend debug info:');
            console.log('[CircleRecs]   - User city:', data.debug.user_city);
            console.log('[CircleRecs]   - Following count:', data.debug.following_count);
            console.log('[CircleRecs]   - Followers count:', data.debug.followers_count);
            console.log('[CircleRecs]   - Mutual count:', data.debug.mutual_count);
            console.log('[CircleRecs]   - In circles count:', data.debug.in_circles_count);
        }

        if (!data.recommendations || data.recommendations.length === 0) {
            console.log('[CircleRecs] No recommendations returned from API');
            console.log('[CircleRecs] This could mean:');
            console.log('[CircleRecs]   1. No users in same city');
            console.log('[CircleRecs]   2. All potential users already in circles');
            console.log('[CircleRecs]   3. No following/follower connections');
            recommendationsContainer.innerHTML = `<p style="color: #8898aa; text-align: center;" data-i18n="circles.no_recommendations">No recommendations available</p>`;
            if (window.i18n && window.i18n.applyLanguage) {
                window.i18n.applyLanguage(window.i18n.getCurrentLanguage ? window.i18n.getCurrentLanguage() : "en");
            }
            return;
        }

        console.log('[CircleRecs] Building HTML for', data.recommendations.length, 'recommendations');
        let html = "";
        data.recommendations.forEach((user, index) => {
            console.log(`[CircleRecs] Rec ${index + 1}: ${user.username} (${user.selected_city}) - ${user.reason}`);
            const reasonKey = user.reason_key || "circles.reason_default";
            // Escape username for onclick to prevent XSS and quote issues
            const escapedUsername = (user.username || '').replace(/'/g, "\\'").replace(/"/g, '\\"');
            html += `
                <div class="member-item" style="display: flex; align-items: center; gap: 15px; padding: 12px; border-radius: 10px; transition: background 0.2s; margin-bottom: 8px; background: #f8f9fa;">
                    <div class="user-avatar" style="width: 40px; height: 40px; border-radius: 50%; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; display: flex; align-items: center; justify-content: center; font-weight: bold;">
                        ${(user.username || "U")[0].toUpperCase()}
                    </div>
                    <div style="flex-grow: 1;">
                        <div style="font-weight: 600; color: #2d3436;">${user.username}</div>
                        <div style="font-size: 12px; color: #8898aa;" data-i18n="${reasonKey}">${user.reason}</div>
                        ${user.selected_city ? `<div style="font-size: 11px; color: #adb5bd;">📍 ${user.selected_city}</div>` : ""}
                    </div>
                    <button onclick="showCircleAddMenu(${user.id}, '${escapedUsername}')" 
                        style="background: linear-gradient(135deg, #28a745 0%, #20c997 100%); color: white; border: none; padding: 8px 16px; border-radius: 20px; cursor: pointer; font-size: 14px; font-weight: 500; transition: all 0.3s;"
                        onmouseover="this.style.transform='scale(1.05)'" 
                        onmouseout="this.style.transform='scale(1)'">
                        <span data-i18n="circles.add_to_circle">Add to Circle</span>
                    </button>
                </div>
            `;
        });

        recommendationsContainer.innerHTML = html;

        if (window.i18n && window.i18n.applyLanguage) {
            const currentLang = window.i18n.getCurrentLanguage ? window.i18n.getCurrentLanguage() : "en";
            window.i18n.applyLanguage(currentLang);
        }
        
        console.log('[CircleRecs] SUCCESS: Displayed', data.recommendations.length, 'recommendations');
        console.log('[CircleRecs] ========================================');

    } catch (error) {
        console.error("[CircleRecs] EXCEPTION in loadCircleRecommendations:");
        console.error("[CircleRecs] Error:", error);
        console.error("[CircleRecs] Stack:", error.stack);
        const recommendationsContainer = document.getElementById("circleRecommendationsList");
        if (recommendationsContainer) {
            recommendationsContainer.innerHTML = `<p style="color: #8898aa; text-align: center;" data-i18n="circles.no_recommendations">No recommendations available</p>`;
        }
    }
}

// Show menu to select which circle to add user to
function showCircleAddMenu(userId, username) {
    const currentLang = window.i18n && window.i18n.getCurrentLanguage ? window.i18n.getCurrentLanguage() : "en";
    
    const labels = {
        "en": { public: "Public", close_friends: "Close Friends", family: "Family", title: "Add to which circle?" },
        "he": { public: "ציבורי", close_friends: "חברים קרובים", family: "משפחה", title: "להוסיף לאיזה מעגל?" },
        "ar": { public: "عام", close_friends: "أصدقاء مقربون", family: "عائلة", title: "إضافة إلى أي دائرة?" },
        "ru": { public: "Публичный", close_friends: "Близкие друзья", family: "Семья", title: "Добавить в какой круг?" }
    };
    
    const t = labels[currentLang] || labels["en"];
    
    const choice = prompt(
        `${t.title}

` +
        `1. ${t.public}
` +
        `2. ${t.close_friends}
` +
        `3. ${t.family}

` +
        `Enter 1, 2, or 3:`
    );
    
    if (!choice) return;
    
    const circleMap = {
        "1": "public",
        "2": "class_b",
        "3": "class_a"
    };
    
    const circleType = circleMap[choice.trim()];
    if (!circleType) {
        showNotification("Invalid choice", "error");
        return;
    }
    
    addToCircle(userId, circleType);
}

window.loadCircleRecommendations = loadCircleRecommendations;
window.showCircleAddMenu = showCircleAddMenu;


// Create member element
function createMemberElement(member, circleType) {
    const memberDiv = document.createElement('div');
    memberDiv.className = 'member-item';
    memberDiv.innerHTML = `
        <div class="user-avatar">${(member.display_name || member.username || member.email || 'U')[0].toUpperCase()}</div>
        <div class="member-name">${member.display_name || member.username || member.email}</div>
        <button class="remove-btn" onclick="removeFromCircle(${member.id}, '${circleType}')">Remove</button>
    `;
    return memberDiv;
}


// Re-render circles UI without reloading data from server
function renderCirclesUI() {
    console.log('Re-rendering circles UI with current data');

    // Use cached circles data
    if (!window.circlesData) {
        console.log('No circles data available to render');
        return;
    }

    const circles = window.circlesData;

    // Check if circles are private
    if (circles.private) {
        console.log('Circles are private, skipping render');
        return;
    }

    // Re-render Public circle
    const publicMembers = document.getElementById('publicMembers');
    if (publicMembers && circles.public) {
        publicMembers.innerHTML = '';
        if (circles.public.length > 0) {
            circles.public.forEach(member => {
                publicMembers.appendChild(createMemberElement(member, 'public'));
            });
        } else {
            publicMembers.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">👥</div>
                    <p data-i18n="circles.no_members">${t('circles.no_members', 'No members yet')}</p>
                </div>`;
        }
    }

    // Re-render Class B circle
    const classBMembers = document.getElementById('class_bMembers');
    if (classBMembers && circles.class_b) {
        classBMembers.innerHTML = '';
        if (circles.class_b.length > 0) {
            circles.class_b.forEach(member => {
                classBMembers.appendChild(createMemberElement(member, 'class_b'));
            });
        } else {
            classBMembers.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">👥</div>
                    <p data-i18n="circles.no_members">${t('circles.no_members', 'No members yet')}</p>
                </div>`;
        }
    }

    // Re-render Class A circle
    const classAMembers = document.getElementById('class_aMembers');
    if (classAMembers && circles.class_a) {
        classAMembers.innerHTML = '';
        if (circles.class_a.length > 0) {
            circles.class_a.forEach(member => {
                classAMembers.appendChild(createMemberElement(member, 'class_a'));
            });
        } else {
            classAMembers.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">👥</div>
                    <p data-i18n="circles.no_members">${t('circles.no_members', 'No members yet')}</p>
                </div>`;
        }
    }

    console.log('Circles UI re-rendered successfully');
}

// Export the function
if (typeof window !== 'undefined') {
    window.renderCirclesUI = renderCirclesUI;
}

// Search users
async function searchUsers() {
    const searchInput = document.getElementById('userSearchInput');
    const query = searchInput.value.trim();

    if (!query) return;

    try {
        const response = await fetch(`/api/users/search?q=${encodeURIComponent(query)}`);
        const data = await response.json();
        const users = data.users || [];

        const searchResults = document.getElementById('searchResults');
        searchResults.innerHTML = '';
        searchResults.classList.add('active');

        if (users.length === 0) {
            searchResults.innerHTML = '<div class="search-result-item">No users found</div>';
      } else {
            users.forEach(user => {
                const resultItem = document.createElement('div');
                resultItem.className = 'search-result-item';

                // Build user details
                const displayName = user.display_name || user.username;
                const email = user.email || '';
                const bio = user.bio || '';
                const occupation = user.occupation || '';
                const interests = user.interests || '';

                // Build detail line (occupation and interests)
                let detailLine = '';
                if (occupation && interests) {
                    detailLine = `<div style="font-size: 12px; color: #6c757d; margin-top: 2px;">${occupation} • ${interests}</div>`;
                } else if (occupation) {
                    detailLine = `<div style="font-size: 12px; color: #6c757d; margin-top: 2px;">${occupation}</div>`;
                } else if (interests) {
                    detailLine = `<div style="font-size: 12px; color: #6c757d; margin-top: 2px;">${interests}</div>`;
                }

               resultItem.innerHTML = `
                    <div class="user-info">
                        <div class="user-avatar">${(displayName || 'U')[0].toUpperCase()}</div>
                        <div style="flex: 1; min-width: 0;">
                            <div style="font-weight: 600;">${displayName}</div>
                            <div style="font-size: 13px; color: #8898aa;">${email}</div>
                            ${detailLine}
                        </div>
                    </div>
                    <select onchange="if(this.value) addToCircle('${user.id}', this.value, '${displayName}')" style="margin-left: 10px; flex-shrink: 0;">
                        <option value="">Add to circle...</option>
                        <option value="public" data-i18n="circles.public">Public</option>
                        <option value="class_b" data-i18n="circles.class_b">Close Friends</option>
                        <option value="class_a" data-i18n="circles.class_a">Family</option>
                    </select>
                `;
                searchResults.appendChild(resultItem);
            });
        }
    } catch (error) {
        console.error('Error searching users:', error);
    }
}


// Initialize circles
// Initialize circles
async function initializeCircles() {
    console.log('Initializing circles...');
    // Get user_id from URL if viewing another user's circles
    const urlParams = new URLSearchParams(window.location.search);
    const viewingUserId = urlParams.get('user_id');

    // Load circles privacy setting (with optional user_id)
    await loadCirclesPrivacy(viewingUserId);
    await loadCircles();

    // Re-apply translations after circles are loaded
    if (window.i18n && window.i18n.applyLanguage) {
        const currentLang = window.i18n.getCurrentLanguage ? window.i18n.getCurrentLanguage() : 'en';
        window.i18n.applyLanguage(currentLang);
    }

    // Close search results when clicking outside
    document.addEventListener('click', (e) => {
        const searchContainer = document.querySelector('.user-search');
        if (!searchContainer && e.target.id !== 'userSearchInput') {
            const searchResults = document.getElementById('searchResults');
            if (searchResults) {
                searchResults.classList.remove('active');
            }
        }
    });
}

// Update all circle displays with current data
function updateCirclesDisplay() {
    // Use the correct keys from backend
    if (window.circlesData) {
        updateCircleDisplay('public', window.circlesData.public, 'publicMembers', 'publicCount');
        updateCircleDisplay('class_b', window.circlesData.class_b, 'class_bMembers', 'class_bCount');
        updateCircleDisplay('class_a', window.circlesData.class_a, 'class_aMembers', 'class_aCount');
    }

    updateCircleTitles();
}

// Update individual circle display
// Update individual circle display
function updateCircleDisplay(circleType, members, containerId, countId) {
    const container = document.getElementById(containerId);
    const count = document.getElementById(countId);

    if (!container || !count) return;

    count.textContent = members ? members.length : 0;

    if (!members || members.length === 0) {
        const icon = circleType === 'public' ? '👥' :
                    circleType === 'class_b' ? '❤️' : '👨‍👩‍👧‍👦';
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

    // Re-apply translations after DOM modification
    if (window.i18n && window.i18n.applyLanguage) {
        const currentLang = window.i18n.getCurrentLanguage ? window.i18n.getCurrentLanguage() : 'en';
        window.i18n.applyLanguage(currentLang);
    }
}

// Export for use in other files
if (typeof window !== 'undefined') {
    window.loadCircles = loadCircles;
    window.initializeCircles = initializeCircles;
    window.searchUsers = searchUsers;
    window.addToCircle = addToCircle;
    window.updatePrivacyDropdownTranslations = updatePrivacyDropdownTranslations;
    window.removeFromCircle = removeFromCircle;
    window.updateCirclesDisplay = updateCirclesDisplay;  // Export the display update function
}



// Force update circle title translations
function updateCircleTitles() {
    if (!window.i18n || !window.i18n.translate) return;

    const t = window.i18n.translate;

    // Update Public circle title
    const publicTitle = document.querySelector('[data-circle="general"] .circle-title');
    if (publicTitle) {
        publicTitle.textContent = t('circles.title_public', 'Public');
    }

    // Update Class B circle title
    const classBTitle = document.querySelector('[data-circle="close_friends"] .circle-title');
    if (classBTitle) {
        classBTitle.textContent = t('circles.title_class_b', 'Close Friends');
    }

    // Update Class A circle title
    const classATitle = document.querySelector('[data-circle="family"] .circle-title');
    if (classATitle) {
        classATitle.textContent = t('circles.title_class_a', 'Family');
    }
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
    'public': t('circles.public', 'Public'),
    'class_b': t('circles.class_b', 'Close Friends'),
    'class_a': t('circles.class_a', 'Family'),
    // Support old names for backwards compatibility
    'general': t('circles.public', 'Public'),
    'close_friends': t('circles.class_b', 'Close Friends'),
    'family': t('circles.class_a', 'Family')
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




function addCircleTranslations() {
    if (window.i18n && window.i18n.translations) {
        // Update English translations
      // Update English translations
        Object.assign(window.i18n.translations.en, {
           'circles.public': 'Public',
            'circles.class_b': 'Close Friends',
            'circles.class_a': 'Family',
            'circles.add_to_circle': 'Add to Circle',
            'circles.privacy_label': 'Circle Visibility',
            'circles.circles_private': 'Circles set to private',
            'circles.search_placeholder': 'Search users by name or email...',
            'circles.no_permission': 'You don\'t have permission to view these circles',
            'circles.no_members': 'No members yet',
            'circles.visibility_label': 'Who can see your circles',
            'circles.visibility_private': 'Private',
            'circles.visibility_public': 'Public',
            'circles.visibility_class_b': 'Close Friends',
            'circles.visibility_class_a': 'Family',
            'circles.title_public': 'Public',
'circles.title_class_b': 'Close Friends',
'circles.title_class_a': 'Family',
'circles.your_access_level': 'Your Level of Access',
            'privacy.public': 'Public',
            'privacy.class_b': 'Close Friends',
            'privacy.class_a': 'Family',
            'privacy.private': 'Private'
        });

        // Update Hebrew translations
      // Update Hebrew translations
        Object.assign(window.i18n.translations.he, {
            'circles.public': 'ציבורי',
            'circles.class_b': 'חברים קרובים',
            'circles.class_a': 'משפחה',
            'circles.add_to_circle': 'הוסף למעגל',
            'circles.privacy_label': 'נראות מעגלים',
            'circles.circles_private': 'מעגלים מוגדרים כפרטיים',
            'circles.search_placeholder': 'חפש משתמשים לפי שם או אימייל...',
            'circles.no_permission': 'אין לך הרשאה לצפות במעגלים אלה',
            'circles.no_members': 'עדיין אין חברים',
            'circles.visibility_label': 'מי יכול לראות את המעגלים שלך',
            'circles.visibility_private': 'פרטי',
            'circles.visibility_public': 'ציבורי',
            'circles.visibility_class_b': 'חברים קרובים ❤️',
            'circles.visibility_class_a': 'משפחה 👨‍👩‍👧‍👦',
            'circles.your_access_level': 'רמת הגישה שלך',
            'circles.title_public': 'ציבורי',
'circles.title_class_b': 'חברים קרובים',
'circles.title_class_a': 'משפחה',
            'privacy.public': 'ציבורי',
            'privacy.class_b': 'חברים קרובים',
            'privacy.class_a': 'משפחה',
            'privacy.private': 'פרטי'
        });

        // Update Arabic translations
     // Update Arabic translations
        Object.assign(window.i18n.translations.ar, {
            'circles.public': 'عام',
            'circles.class_b': 'الأصدقاء المقربون',
            'circles.class_a': 'العائلة',
            'circles.add_to_circle': 'أضف إلى الدائرة',
            'circles.privacy_label': 'رؤية الدوائر',
            'circles.circles_private': 'تم تعيين الدوائر كخاصة',
            'circles.search_placeholder': 'ابحث عن المستخدمين بالاسم أو البريد الإلكتروني...',
            'circles.no_permission': 'ليس لديك إذن لعرض هذه الدوائر',
            'circles.no_members': 'لا يوجد أعضاء بعد',
            'circles.visibility_label': 'من يمكنه رؤية دوائرك',
            'circles.visibility_private': 'خاص',
            'circles.visibility_public': 'عام',
            'circles.visibility_class_b': 'الأصدقاء المقربون ❤️',
            'circles.visibility_class_a': 'العائلة 👨‍👩‍👧‍👦',
            'circles.title_public': 'عام',
'circles.title_class_b': 'الأصدقاء المقربون',
'circles.title_class_a': 'العائلة',
'circles.your_access_level': 'مستوى وصولك',
            'privacy.public': 'عام',
            'privacy.class_b': 'الأصدقاء المقربون',
            'privacy.class_a': 'العائلة',
            'privacy.private': 'خاص'
        });

        // Update Russian translations
     // Update Russian translations
     // Update Russian translations
        Object.assign(window.i18n.translations.ru, {
             'circles.public': 'Публичный',
            'circles.class_b': 'Близкие друзья',
            'circles.class_a': 'Семья',
            'circles.add_to_circle': 'Добавить в круг',
            'circles.privacy_label': 'Видимость кругов',
            'circles.circles_private': 'Круги установлены как приватные',
            'circles.search_placeholder': 'Поиск пользователей по имени или email...',
            'circles.no_permission': 'У вас нет разрешения на просмотр этих кругов',
            'circles.no_members': 'Пока нет участников',
            'circles.visibility_label': 'Кто может видеть ваши круги',
            'circles.visibility_private': 'Приватный',
            'circles.visibility_public': 'Публичный',
            'circles.visibility_class_b': 'Близкие друзья ❤️',
            'circles.visibility_class_a': 'Семья 👨‍👩‍👧‍👦',
            'circles.your_access_level': 'Ваш уровень доступа',
            'circles.title_public': 'Публичный',
'circles.title_class_b': 'Близкие друзья',
'circles.title_class_a': 'Семья',
            'privacy.public': 'Публичный',
            'privacy.class_b': 'Близкие друзья',
            'privacy.class_a': 'Семья',
            'privacy.private': 'Приватный'
        });

        // Update privacy dropdown translations immediately
        if (typeof updatePrivacyDropdownTranslations === 'function') {
            updatePrivacyDropdownTranslations();
        }
    }
}




function updatePrivacyDropdownTranslations() {
    const privacySelect = document.getElementById('circlesPrivacySelect');
    if (!privacySelect) return;

    const currentValue = privacySelect.value;

    // Update each option with emoji + translation
    privacySelect.querySelectorAll('option').forEach(option => {
        const value = option.value;
        const i18nKey = option.getAttribute('data-i18n');

        if (i18nKey && window.i18n && window.i18n.translate) {
            // Get translation
            const translation = window.i18n.translate(i18nKey);

            // Remove any existing emojis from translation
            const cleanTranslation = translation
                .replace(/[\u{1F000}-\u{1FAFF}\u{2600}-\u{27BF}\u{200D}\u{FE0F}\u{FE0E}]/ug, '')
                .replace(/\s+/g, ' ')
                .trim();

            // Emoji map
            const emojiMap = {
                'private': '🔒',
                'public': '🌍',
                'class_b': '👥',
                'class_a': '👨‍👩‍👧‍👦'
            };

            // Add emoji based on value
            const emoji = emojiMap[value] || '';
            option.textContent = emoji ? cleanTranslation + ' ' + emoji : cleanTranslation;
        }
    });

    // Restore the selected value
    privacySelect.value = currentValue;
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
if (typeof currentRecipient === 'undefined') {
    var currentRecipient = null;
}
if (typeof currentUserId === 'undefined') {
    var currentUserId = null;
}

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

// ============================================================
// CIRCLES PRIVACY FUNCTIONS
// ============================================================

async function loadCirclesPrivacy(viewingUserId = null) {
    try {
        // Build URL with optional user_id parameter
        let url = '/api/circles/privacy';
        if (viewingUserId) {
            url += `?user_id=${viewingUserId}`;
        }

        const response = await fetch(url, {
            credentials: 'include'
        });

        if (response.ok) {
            const data = await response.json();
            const privacyLevel = data.privacy || data.circles_privacy || 'private';

            // Control visibility of entire privacy selector section
            const privacySelector = document.getElementById('circlesPrivacySelector');
            const selector = document.getElementById('circlesPrivacySelect');

            if (privacySelector) {
                // Only show privacy selector if viewing own circles
                if (viewingUserId) {
                    privacySelector.style.display = 'none';
                    console.log('[loadCirclesPrivacy] Hidden privacy selector (viewing another user)');
                } else {
                    privacySelector.style.display = 'block';
                    console.log('[loadCirclesPrivacy] Showing privacy selector (own circles)');
                }
            }

            if (selector) {
                selector.value = privacyLevel;
            }
        }
    } catch (error) {
        console.error('Error loading circles privacy:', error);
    }
}

async function updateCirclesPrivacy(privacyLevel) {
    try {
        const response = await fetch('/api/circles/privacy', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'include',
            body: JSON.stringify({
                privacy_level: privacyLevel
            })
        });

        if (response.ok) {
            showNotification(
                t('circles.privacy_updated', 'Privacy setting updated'),
                'success'
            );
        } else {
            throw new Error('Failed to update privacy');
        }
    } catch (error) {
        console.error('Error updating circles privacy:', error);
        showNotification(
            t('error.updating_privacy', 'Error updating privacy'),
            'error'
        );
    }
}


// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', async () => {
    // Wait for i18n
    await waitForI18n();

    // Apply initial translations
    // RE-APPLY TRANSLATIONS after setting innerHTML
if (window.i18n && window.i18n.applyLanguage) {
    const currentLang = window.i18n.getCurrentLanguage ? window.i18n.getCurrentLanguage() : 'en';
    window.i18n.applyLanguage(currentLang);
}

    // Get current user
    await getCurrentUser();

    // Load data based on page
    if (document.getElementById('conversationsList')) {
        loadMessages();
    }

     if (document.getElementById('publicMembers')) {
        addCircleTranslations();  // Add this line
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


});
// ===================
// NEW FOLLOWING SECTION WITH USER SEARCH - ADDED FEATURES
// ===================

// Update/Add the updateFollowingSection function
function updateFollowingSection() {
    const followingSection = document.getElementById('followingSection');
    if (!followingSection) return;

    fetch('/api/following')
        .then(response => response.json())
        .then(data => {
            let html = '<h2 data-i18n="following.title">Following</h2>';

            if (data.following && data.following.length > 0) {
                html += '<div class="following-list">';
                data.following.forEach(user => {
                    html += `<div class="user-card" data-user-id="${user.id}">
                        <div class="user-name">${escapeHtml(user.username)}</div>
                        ${user.note ? `<div class="user-note">${escapeHtml(user.note)}</div>` : ''}
                        <button onclick="unfollowUser(${user.id})" class="btn btn-secondary">Unfollow</button>
                    </div>`;
                });
                html += '</div>';
            } else {
                html += '<p>You are not following anyone yet.</p>';
            }

            followingSection.innerHTML = html;

            // Add search functionality after updating section
            setTimeout(() => {
                addUserSearchToFollowing();
            }, 100);
        })
        .catch(error => {
            console.error('Error loading following list:', error);
            followingSection.innerHTML = '<h2>Following</h2><p>Error loading following list</p>';
        });
}

// Add User Search Functionality to Following Section
function addUserSearchToFollowing() {
    const followingSection = document.getElementById('followingSection');
    if (!followingSection) return;

    // Check if search container already exists
    if (document.getElementById('userSearchContainer')) return;

    const searchHtml = `
        <div id="userSearchContainer" class="user-search-container" style="margin: 20px 0; padding: 15px; background: #f9f9f9; border-radius: 8px;">
            <h3 data-i18n="follow.search_users">Search users to follow</h3>
            <div style="display: flex; gap: 10px; margin: 10px 0;">
                <input type="text" id="followSearchInput"
                       placeholder="Enter username or email"
                       data-i18n-placeholder="follow.search_placeholder"
                       style="flex: 1; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
                <button onclick="searchUsersToFollow()" class="btn btn-primary" style="padding: 8px 16px;">
                    🔍 Search
                </button>
            </div>
            <div id="followSearchResults" style="margin-top: 15px;"></div>
        </div>
    `;

    // Insert after the h2 title
    const title = followingSection.querySelector('h2');
    if (title) {
        title.insertAdjacentHTML('afterend', searchHtml);
    }
}

async function searchUsersToFollow() {
    const query = document.getElementById('followSearchInput').value.trim();
    if (query.length < 1) {
        showNotification('Please enter at least 1 character', 'warning');
        return;
    }

    try {
        const response = await fetch(`/api/users/search?q=${encodeURIComponent(query)}`);
        const data = await response.json();

        const resultsDiv = document.getElementById('followSearchResults');
        if (!data.users || data.users.length === 0) {
            resultsDiv.innerHTML = '<p>No users found</p>';
            return;
        }

        let html = '<div class="search-results-list">';
        data.users.forEach(user => {
            html += `
                <div class="user-card" style="display: flex; justify-content: space-between; align-items: center; padding: 10px; background: white; margin: 5px 0; border-radius: 8px;">
                    <div>
                        <strong>${escapeHtml(user.username)}</strong><br>
                        <small style="color: #666;">${escapeHtml(user.email)}</small>
                    </div>
                    ${user.is_following ?
                        '<span style="color: green;">Following ✓</span>' :
                        `<button onclick="followWithNote(${user.id}, '${escapeHtml(user.username).replace(/'/g, "\\'")}')" class="btn btn-primary" style="padding: 6px 12px;">Follow</button>`
                    }
                </div>
            `;
        });
        html += '</div>';
        resultsDiv.innerHTML = html;

    } catch (error) {
        console.error('Search error:', error);
        showNotification('Search failed', 'error');
    }
}

function followWithNote(userId, username) {
    const note = prompt(`Add a note for ${username} (optional, max 300 characters):`);

    fetch(`/api/follow/${userId}`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({note: note || ''})
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification(`You are now following ${username}`, 'success');
            // Refresh search results if visible
            const searchInput = document.getElementById('followSearchInput');
            if (searchInput && searchInput.value) {
                searchUsersToFollow();
            }
            updateFollowingSection(); // Refresh following list
        } else {
            showNotification(data.error || 'Failed to follow user', 'error');
        }
    })
    .catch(error => {
        console.error('Follow error:', error);
        showNotification('Failed to follow user', 'error');
    });
}

function unfollowUser(userId) {
    if (!confirm('Are you sure you want to unfollow this user?')) return;

    fetch(`/api/unfollow/${userId}`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'}
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showNotification('User unfollowed', 'success');
            updateFollowingSection();
        } else {
            showNotification(data.error || 'Failed to unfollow user', 'error');
        }
    })
    .catch(error => {
        console.error('Unfollow error:', error);
        showNotification('Failed to unfollow user', 'error');
    });
}

// Update existing follow buttons to include note option
function updateFollowButtons() {
    const followButtons = document.querySelectorAll('.follow-btn');
    followButtons.forEach(button => {
        if (!button.hasAttribute('data-note-enabled')) {
            button.setAttribute('data-note-enabled', 'true');
            const userId = button.getAttribute('data-user-id');
            const username = button.parentElement.querySelector('.user-name')?.textContent || 'this user';
            button.onclick = function() {
                followWithNote(userId, username);
            };
        }
    });
}

// Instant search with debounce for following view
let followSearchDebounceTimer = null;

async function searchUsersToFollowInstant(query) {
    const resultsContainer = document.getElementById('followSearchResults');

    // Clear previous timer
    if (followSearchDebounceTimer) {
        clearTimeout(followSearchDebounceTimer);
    }

    // If empty query, hide results
    if (!query || query.trim().length < 1) {
        if (resultsContainer) {
            resultsContainer.style.display = 'none';
            resultsContainer.innerHTML = '';
        }
        return;
    }

    // Debounce: wait 200ms before searching
    followSearchDebounceTimer = setTimeout(async () => {
        try {
            const token = localStorage.getItem('token');
            const response = await fetch(`/api/users/search?q=${encodeURIComponent(query.trim())}`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (!response.ok) throw new Error('Search failed');

            const data = await response.json();

            // Check if response is an array (valid users list)
            const users = Array.isArray(data) ? data : [];

            if (resultsContainer) {
                if (users.length === 0) {
                    resultsContainer.innerHTML = '<p style="text-align: center; color: #6B7280;">No users found</p>';
                } else {
                    resultsContainer.innerHTML = users.map(user => `
                        <div style="display: flex; align-items: center; justify-content: space-between; padding: 10px; border-bottom: 1px solid #E5E7EB;">
                            <div style="display: flex; align-items: center; gap: 10px;">
                                <div style="width: 40px; height: 40px; border-radius: 50%; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); display: flex; align-items: center; justify-content: center; color: white; font-weight: bold;">
                                    ${user.username.charAt(0).toUpperCase()}
                                </div>
                                <div>
                                    <strong>${user.username}</strong>
                                    ${user.bio ? `<p style="font-size: 12px; color: #6B7280; margin: 0;">${user.bio.substring(0, 50)}${user.bio.length > 50 ? '...' : ''}</p>` : ''}
                                </div>
                            </div>
                            <button onclick="followUser('${user.username}')" class="btn btn-primary" style="padding: 6px 16px; font-size: 14px;">
                                Follow
                            </button>
                        </div>
                    `).join('');
                }
                resultsContainer.style.display = 'block';
            }
        } catch (error) {
            console.error('Search error:', error);
            if (resultsContainer) {
                resultsContainer.innerHTML = '<p style="text-align: center; color: #EF4444;">Search failed. Please try again.</p>';
                resultsContainer.style.display = 'block';
            }
        }
    }, 200);
}

// Export the new functions
window.updateFollowingSection = updateFollowingSection;
window.addUserSearchToFollowing = addUserSearchToFollowing;
window.searchUsersToFollow = searchUsersToFollow;
window.searchUsersToFollowInstant = searchUsersToFollowInstant;
window.followWithNote = followWithNote;
window.unfollowUser = unfollowUser;
window.updateFollowButtons = updateFollowButtons;

// Add initialization for new features
const originalDOMContentLoaded = document.addEventListener;
document.addEventListener('DOMContentLoaded', function() {
    // Check for following section and initialize if present
    setTimeout(() => {
        if (document.getElementById('followingSection')) {
            updateFollowingSection();
            // Initialize follow buttons after a delay
            setTimeout(() => {
                updateFollowButtons();
            }, 500);
        }
    }, 1000);
});

console.log('Circles-messages.js UPDATED with following features');