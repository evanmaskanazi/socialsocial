// PJ816 Version 1800 - CRITICAL FIX: Trigger emails now sent without watcher login
// ROOT CAUSE: check_parameter_triggers() required login and only ran on polling
// FIX: Added background trigger scheduler that runs every 5 minutes
// Emails are sent automatically when trigger conditions are met
// PJ815 Version 1705 - CRITICAL FIX: Reverted broken v1704 trigger deduplication
// ROOT CAUSE: v1704 merged triggers upfront, but triggers use OLD schema (parameter_name)
// Merging with bool(None)=False caused all alert flags to be False
// FIX: Process each trigger row individually, deduplicate RESULTS not inputs
// PJ813 Version 1703 - Fixed: Each date range creates separate alert, all patterns found
// PJ812 Version 1706 - Fixed language selector resetting by blocking non-user-initiated changes
// PJ812 Version 1702 - Trigger emails work without login, fixed double messages, more alerts visible
// PJ812 Version 1701 - Fixed trigger check to verify login first, improved date formatting
// PJ811 Version 1700 - Fixed trigger alerts vanishing, alerts now persist in database
// PJ810 Version 1600 - Fixed double message sending, configurable trigger alert display
// PJ809 Version 1500 - Backend fix for duplicate detection window (no JS changes needed)
// PJ808 Version 1400 - Backend fix for cooldown blocking (no JS changes needed)
// PJ807 FIX APPLIED: Fixed JavaScript errors in displayParameterAlerts
// PJ806 FIX APPLIED: Fixed duplicate email spam from trigger alerts
// PJ706 FIX APPLIED: Default privacy changed from 'public' to 'private' for new accounts
// Social Parameters Save/Load System with i18n support and numeric ratings
// COMPLETE FIXED VERSION - Includes language selector and all fixes
//
// PJ815 Changes (version 1705):
// - CRITICAL FIX: Reverted broken v1704 trigger deduplication approach
// - ROOT CAUSE: v1704 merged triggers by watched_id but triggers use OLD schema (parameter_name)
// - When merging with bool(t.mood_alert) where t.mood_alert=None, got False - lost all flags
// - FIX: Process each trigger row individually, use patterns_seen SET to deduplicate RESULTS
// - BACKEND: Each trigger checked for its actual schema (old vs new) and processed accordingly
// - BACKEND: Added [PJ815 DEBUG] and [PJ815 PATTERN] logging for diagnostics
//
// PJ813 Changes (version 1703):
// - FIX: checkParameterAlerts now checks if user is logged in before making API call
// - This prevents 401 errors when the function fires before login completes
// - Frontend now calls checkParameterAlerts() 3 seconds after successful login
// - Better error handling for non-authenticated responses
//
// PJ812 Changes (version 1702):
// - BACKEND: process_parameter_triggers now sends emails even when watcher not logged in
// - BACKEND: Added privacy checks to process_parameter_triggers (matching check_triggers)
// - BACKEND: Increased alerts limit from 50 to 100 for full month display
// - FRONTEND: Fixed double message sending with improved debouncing
// - FRONTEND: Increased alerts-list height to 600px for better visibility
//
// PJ811 Changes (version 1700):
// - CRITICAL FIX: Trigger alerts no longer vanish on page refresh
// - Backend now creates persistent database alerts with proper duplicate detection
// - Frontend no longer adds ephemeral DOM alerts that disappear
// - Alerts are now loaded from /api/alerts like other notifications
// - checkParameterAlerts still polls for patterns but alerts persist in DB
// - TRIGGER_ALERT_DISPLAY_MODE now controls ADDITIONAL visual feedback only
// - Emails are sent when alerts are created (if email_on_alert enabled)
//
// PJ810 Changes (version 1600):
// - Fixed double message sending when pressing Enter
// - Added TRIGGER_ALERT_DISPLAY_MODE configuration:
//   'overlay' = Yellow floating alerts (original behavior)
//   'standard' = Alerts in the Alerts section like other notifications
// - Default is 'standard' to match other alert types
//
// PJ809 Changes (version 1500):
// - Backend only: Reduced duplicate detection from 1 day to 4 hours
// - Backend only: Added enhanced logging for save_parameters
// - No frontend changes needed
//
// PJ808 Changes:
// - Backend only: Removed 24-hour cooldown that was blocking all alerts
// - No frontend changes needed
//
// PJ807 Changes:
// - Fixed TypeError in displayParameterAlerts when alert.level is undefined
// - Now handles both new schema (with level/dates/values) and old schema (without) gracefully
// - Added null checks for all alert fields to prevent crashes
//
// PJ806 Changes:
// - Reduced checkParameterAlerts polling from 60 seconds to 5 minutes
// - The /api/parameters/check-triggers endpoint is now READ-ONLY
// - Alerts are created ONLY when parameters are saved (not when polling)

// ============================================================================
// PJ812 CONFIGURATION: How to display trigger alerts from polling
// ============================================================================
// Options:
//   'overlay'  - Yellow floating alerts on right side (additional visual feedback)
//   'standard' - Silent mode - alerts are in Alerts section via /api/alerts (default)
//   'disabled' - Don't show any polling feedback (alerts still in DB)
// 
// NOTE: Alerts are NOW ALWAYS created in the database when patterns are found.
//       This setting only controls ADDITIONAL visual feedback from polling.
//       Real alerts always appear in the Alerts section via loadAlerts().
// ============================================================================
const TRIGGER_ALERT_DISPLAY_MODE = 'standard';  // Change to 'overlay' for yellow popups

// ============================================================
// MVP-FIX: Notification Polyfill - ensures showNotification always works
// ============================================================
(function() {
    if (typeof window.showNotification !== 'function') {
        function ensureToastContainer() {
            let container = document.getElementById('toastContainer');
            if (!container) {
                container = document.createElement('div');
                container.id = 'toastContainer';
                container.style.cssText = 'position:fixed;top:20px;right:20px;z-index:10000;display:flex;flex-direction:column;gap:10px;';
                document.body.appendChild(container);
            }
            return container;
        }

        window.showNotification = function(message, type) {
            type = type || 'info';
            const container = ensureToastContainer();
            
            const toast = document.createElement('div');
            const colors = {
                success: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
                error: 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)',
                warning: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)',
                info: 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)'
            };
            
            toast.style.cssText = 'padding:16px 24px;border-radius:12px;color:white;font-weight:500;box-shadow:0 4px 20px rgba(0,0,0,0.2);display:flex;align-items:center;gap:12px;max-width:350px;animation:toastSlideIn 0.3s ease;background:' + (colors[type] || colors.info);
            
            if (!document.getElementById('toastAnimStyles')) {
                const style = document.createElement('style');
                style.id = 'toastAnimStyles';
                style.textContent = '@keyframes toastSlideIn{from{transform:translateX(100%);opacity:0}to{transform:translateX(0);opacity:1}}@keyframes toastSlideOut{from{transform:translateX(0);opacity:1}to{transform:translateX(100%);opacity:0}}';
                document.head.appendChild(style);
            }
            
            const icons = { success: '✓', error: '✕', warning: '⚠', info: 'ℹ' };
            const iconSpan = document.createElement('span');
            iconSpan.textContent = icons[type] || icons.info;
            toast.appendChild(iconSpan);
            
            const msgSpan = document.createElement('span');
            msgSpan.textContent = message;
            toast.appendChild(msgSpan);
            
            const closeBtn = document.createElement('button');
            closeBtn.textContent = '×';
            closeBtn.style.cssText = 'background:none;border:none;color:white;font-size:18px;cursor:pointer;margin-left:auto;opacity:0.8;';
            closeBtn.onclick = function() { removeToast(toast); };
            toast.appendChild(closeBtn);
            
            container.appendChild(toast);
            
            function removeToast(t) {
                if (!t || !t.parentNode) return;
                t.style.animation = 'toastSlideOut 0.3s ease forwards';
                setTimeout(function() { if (t.parentNode) t.parentNode.removeChild(t); }, 300);
            }
            
            setTimeout(function() { removeToast(toast); }, 5000);
        };
        
        console.log('[parameters-social.js] Notification polyfill installed');
    }
})();

// Translation function helper
const pt = (key) => window.i18n ? window.i18n.translate(key) : key;

// State management
let currentDate = new Date();
let selectedRatings = {};
let datesWithData = new Set(JSON.parse(localStorage.getItem('savedParameterDates') || '[]'));
window.selectedPrivacy = {};
let savedParameterState = {};

// Add function to save parameter state
function saveParameterState(date) {
    const state = {};

    // Save all parameter values AND privacy settings
    ['mood', 'energy', 'sleep_quality', 'physical_activity', 'anxiety'].forEach(param => {
        // Find selected rating button
        const selected = document.querySelector(`.rating-button.selected[data-category="${param}"]`);
        if (selected) {
            state[param] = selected.dataset.value;
        }

        // Save privacy settings
        const privacySelect = document.querySelector(`select[data-category="${param}"]`);
        if (privacySelect) {
            state[`${param}_privacy`] = privacySelect.value;
            // Also update global privacy object
            window.selectedPrivacy[param] = privacySelect.value;
        }
    });

    // Save notes
    const notesField = document.querySelector('textarea');
    if (notesField) {
        state.notes = notesField.value;
    }

    // Store in session storage for persistence
    sessionStorage.setItem(`parameters_${date}`, JSON.stringify(state));
    savedParameterState[date] = state;
}

// Add function to restore state
// Add function to restore state
function restoreParameterState(state) {
    ['mood', 'energy', 'sleep_quality', 'physical_activity', 'anxiety'].forEach(param => {
        if (state[param]) {
            const button = document.querySelector(`.rating-button[data-category="${param}"][data-value="${state[param]}"]`);
            if (button) {
                document.querySelectorAll(`.rating-button[data-category="${param}"]`).forEach(b => {
                    b.classList.remove('selected');
                });
                button.classList.add('selected');
                // Update selectedRatings
                selectedRatings[param] = parseInt(state[param]);
            }
        }

        // Restore privacy settings
        if (state[`${param}_privacy`]) {
            const select = document.querySelector(`select[data-category="${param}"]`);
            if (select) {
                select.value = state[`${param}_privacy`];
                window.selectedPrivacy[param] = state[`${param}_privacy`];
            }
        }
    });

    if (state.notes) {
        const notesField = document.querySelector('textarea');
        if (notesField) {
            notesField.value = state.notes;
        }
    }
}

function updatePrivacy(categoryId, privacyLevel) {
    if (!window.selectedPrivacy) {
        window.selectedPrivacy = {};
    }
    window.selectedPrivacy[categoryId] = privacyLevel;
    console.log('Privacy updated:', categoryId, privacyLevel);
}

// Load most recent privacy settings from any previous entry
// This ensures privacy preferences persist even when starting a new day
async function loadMostRecentPrivacySettings() {
    try {
        // Fetch the list of dates with saved parameters
        const datesResponse = await fetch('/api/parameters/dates');
        if (!datesResponse.ok) return;
        
        const datesResult = await datesResponse.json();
        if (!datesResult.success || !datesResult.dates || datesResult.dates.length === 0) {
            console.log('No previous entries found for privacy settings');
            return;
        }
        
        // Get the most recent date (dates are typically returned in chronological or reverse order)
        const sortedDates = datesResult.dates.sort((a, b) => new Date(b) - new Date(a));
        const mostRecentDate = sortedDates[0];
        
        console.log('Loading privacy settings from most recent entry:', mostRecentDate);
        
        // Fetch the most recent entry
        const recentResponse = await fetch(`/api/parameters?date=${mostRecentDate}`);
        if (!recentResponse.ok) return;
        
        const recentResult = await recentResponse.json();
        if (!recentResult.success || !recentResult.data) return;
        
        // Apply privacy settings from the most recent entry
        ['mood', 'energy', 'sleep_quality', 'physical_activity', 'anxiety'].forEach(param => {
            const privacyKey = `${param}_privacy`;
            const privacyValue = recentResult.data[privacyKey] || 'private';
            
            window.selectedPrivacy[param] = privacyValue;
            
            // Update the dropdown UI
            const selector = document.querySelector(`select[data-category="${param}"]`);
            if (selector) {
                selector.value = privacyValue;
            }
        });
        
        console.log('Privacy settings loaded from recent entry:', window.selectedPrivacy);
    } catch (error) {
        console.log('Could not load recent privacy settings:', error);
    }
}

// Tooltip functions
function showTooltip(categoryId, event) {
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }

    // Get the translated tooltip text
    const tooltipKey = `tooltip.${categoryId}`;
    const tooltipText = pt(tooltipKey);

    // Get the category info for the title
    const category = PARAMETER_CATEGORIES.find(c => c.id === categoryId);
    const categoryName = pt(category?.nameKey || categoryId);
    const categoryEmoji = category?.emoji || '';

    // Create modal
    const modal = document.createElement('div');
    modal.className = 'tooltip-modal';
    modal.id = 'tooltipModal';
    modal.innerHTML = `
        <div class="tooltip-content">
            <button class="tooltip-close" onclick="closeTooltip()">×</button>
            <h3>${categoryEmoji} ${categoryName}</h3>
            <p>${tooltipText}</p>
        </div>
    `;

    document.body.appendChild(modal);

    // Close on background click
    modal.addEventListener('click', function(e) {
        if (e.target === modal) {
            closeTooltip();
        }
    });

    // Close on escape key
    document.addEventListener('keydown', handleTooltipEscape);
}

function closeTooltip() {
    const modal = document.getElementById('tooltipModal');
    if (modal) {
        modal.remove();
    }
    document.removeEventListener('keydown', handleTooltipEscape);
}

function handleTooltipEscape(e) {
    if (e.key === 'Escape') {
        closeTooltip();
    }
}

// Export tooltip functions
window.showTooltip = showTooltip;
window.closeTooltip = closeTooltip;

// ESSENTIAL 5 PARAMETER CATEGORIES ONLY - ratings 1-4
const CIRCLE_EMOJIS = {
    'private': '🔒',
    'public': '🌍',
    'general': '🌍',
    'class_b': '👥',
    'close_friends': '👥',
    'class_a': '👨‍👩‍👧‍👦',
    'family': '👨‍👩‍👧‍👦'
};

// Diary entries use 1-4 scale (Fix #2 only affects the chart Y-axis, not entry values)
const PARAMETER_CATEGORIES = [
    {
        id: 'mood',
        emoji: '😊',
        nameKey: 'parameters.mood',
        descriptionKey: 'parameters.mood_desc',
        min: 1,
        max: 4
    },
    {
        id: 'energy',
        emoji: '⚡',
        nameKey: 'parameters.energy',
        descriptionKey: 'parameters.energy_desc',
        min: 1,
        max: 4
    },
    {
        id: 'sleep_quality',
        emoji: '😴',
        nameKey: 'parameters.sleep_quality',
        descriptionKey: 'parameters.sleep_quality_desc',
        min: 1,
        max: 4
    },
    {
        id: 'physical_activity',
        emoji: '🏃',
        nameKey: 'parameters.physical_activity',
        descriptionKey: 'parameters.physical_activity_desc',
        min: 1,
        max: 4
    },
    {
        id: 'anxiety',
        emoji: '😰',
        nameKey: 'parameters.anxiety',
        descriptionKey: 'parameters.anxiety_desc',
        min: 1,
        max: 4
    }
];

// Add translations for parameters
const addParameterTranslations = () => {
    if (window.i18n && window.i18n.translations) {
        // English translations
        if (!window.i18n.translations.en['parameters.mood']) {
            Object.assign(window.i18n.translations.en, {
                'parameters.title': 'Diary',
                'parameters.select_date': 'Select Date',
                'parameters.mood': 'Mood',
                'parameters.mood_desc': 'Overall emotional state',
                'parameters.energy': 'Energy',
                'parameters.energy_desc': 'Physical and mental energy levels',
                'parameters.sleep_quality': 'Sleep Quality',
                'parameters.sleep_quality_desc': 'Quality of sleep',
                'parameters.physical_activity': 'Physical Activity',
                'parameters.physical_activity_desc': 'Physical activity level',
                'parameters.anxiety': 'Anxiety',
                'parameters.anxiety_desc': 'Level of anxiety experienced',
                'parameters.notes': 'Notes',
                'parameters.notes_placeholder': 'Additional thoughts for today...',
                'parameters.save': 'Save Parameters',
                'parameters.load': 'Load Parameters',
                'parameters.clear': 'Clear Form',
                'parameters.home': 'Home',
                'parameters.saved': 'Parameters saved successfully!',
                'parameters.loaded': 'Parameters loaded for',
                'parameters.cleared': 'Form cleared',
                'parameters.no_saved': 'No saved parameters for this date',
                'parameters.today_label': 'Today',
                'error.saving': 'Error saving parameters',
                'privacy.public': 'Public',
'privacy.class_b': 'Close Friends',
'privacy.class_a': 'Family',
'privacy.private': 'Private',
                'error.loading': 'Error loading parameters',
                // Common UI elements
                'common.back_to_following': '← Back to Following',
                'common.monday': 'Mon',
                'common.tuesday': 'Tue',
                'common.wednesday': 'Wed',
                'common.thursday': 'Thu',
                'common.friday': 'Fri',
                'common.saturday': 'Sat',
                'common.sunday': 'Sun',
                'common.today': 'Today',
                'following.your_level_of_access': 'Your Level of Access:',
                'following.view_full_profile': 'View Full Profile',
                'following.circles': 'Circles',
                'alerts.wellness_alert': 'Wellness Alert for',
                'alerts.mood_low': '\'s mood has been less than 3.0 for 3 consecutive days',
                'alerts.energy_low': '\'s energy has been less than 3.0 for 3 consecutive days',
                // Tooltip help texts
                'tooltip.mood': 'How good or bad have you felt today?\n\n1 = Bad - Feeling down, sad, or low\n2 = Below average - Not your best, but managing\n3 = Okay - Reasonably stable or neutral\n4 = Good - Feeling positive, content, or upbeat\n\nRemember: Mood fluctuates naturally day to day. You\'re tracking patterns over time to understand yourself better, not judging individual days. Even difficult days provide valuable information.',
                'tooltip.energy': 'This tracks your physical stamina and mental sharpness throughout the day.\n\n1 = Depleted - Exhausted, struggling to focus or complete basic tasks\n2 = Low - Tired and running on reserves, everything feels effortful\n3 = Moderate - Decent energy to get things done, can focus reasonably well, some fatigue by day\'s end\n4 = High - Energized and alert, easy to focus and accomplish tasks, feeling capable\n\nRemember: Low energy isn\'t laziness - it\'s information. Many factors affect energy (sleep, stress, nutrition, health). Tracking patterns helps you identify what supports or drains you.',
                'tooltip.sleep_quality': 'This tracks how well you slept, not just how long. Quality matters as much as quantity, and one rough night doesn\'t define a pattern.\n\n1 = Poor - Barely slept or very disrupted, woke unrefreshed\n2 = Restless - Some sleep but frequently woke, still tired\n3 = Fair - Slept reasonably well with minor interruptions\n4 = Good - Slept soundly, woke feeling refreshed\n\nRemember: Sleep is affected by stress, environment, health, and many other factors. You\'re tracking patterns to understand what helps or hinders your rest, not to achieve perfect sleep every night.',
                'tooltip.physical_activity': 'This scale captures your overall physical activity - considering both how long and how intensely you moved today.\n\n1 = Minimal - Rest day, very light movement, or brief activity (under 15 min)\n2 = Light - Short activity (15-30 min) at easy pace, OR longer gentle movement (Examples: short walk, stretching, light household tasks)\n3 = Moderate - 30-60 min of moderate activity OR shorter vigorous activity (Examples: brisk walk, active errands, standard workout)\n4 = Substantial - Extended activity (60+ min), high-intensity workout, OR multiple activity sessions\n\nRemember: This tracks your movement patterns, not your worth. Rest is essential. The goal is awareness and gradual progress, not perfection.',
                'tooltip.anxiety': 'Anxiety is a normal human emotion that everyone experiences. This scale tracks how much anxiety interferes with your daily life, not whether you feel anxious at all.\n\n1 = Manageable - Feeling calm or any anxiety present doesn\'t interfere with activities\n2 = Noticeable - Some anxiety, but still able to do what you need to do\n3 = Challenging - Anxiety is making some activities difficult\n4 = Overwhelming - Anxiety is significantly interfering with daily functioning\n\nRemember: The goal isn\'t to eliminate all anxiety, but to keep it at levels where you can still engage with your life.'
            });
        }

        // Hebrew translations
        if (!window.i18n.translations.he['parameters.mood']) {
            Object.assign(window.i18n.translations.he, {
                'parameters.title': 'יומן',
                'parameters.select_date': 'בחר תאריך',
                'parameters.mood': 'מצב רוח',
                'parameters.mood_desc': 'מצב רגשי כללי',
                'parameters.energy': 'אנרגיה',
                'parameters.energy_desc': 'רמות אנרגיה פיזית ומנטלית',
                'parameters.sleep_quality': 'איכות שינה',
                'parameters.sleep_quality_desc': 'איכות השינה',
                'parameters.physical_activity': 'פעילות גופנית',
                'parameters.physical_activity_desc': 'רמת פעילות גופנית',
                'parameters.anxiety': 'חרדה',
                'parameters.anxiety_desc': 'רמת החרדה שחוויתי',
                'parameters.notes': 'הערות',
                'parameters.notes_placeholder': 'מחשבות נוספות להיום...',
                'parameters.save': 'שמור פרמטרים',
                'parameters.load': 'טען פרמטרים',
                'parameters.clear': 'נקה טופס',
                'parameters.home': 'בית',
                'parameters.saved': 'הפרמטרים נשמרו בהצלחה!',
                'parameters.loaded': 'פרמטרים נטענו עבור',
                'parameters.cleared': 'הטופס נוקה',
                'parameters.no_saved': 'אין פרמטרים שמורים לתאריך זה',
                'parameters.today_label': 'היום',
                'error.saving': 'שגיאה בשמירת פרמטרים',
                'privacy.public': 'ציבורי',
'privacy.class_b': 'חברים קרובים',
'privacy.class_a': 'משפחה',
'privacy.private': 'פרטי',
                'error.loading': 'שגיאה בטעינת פרמטרים',
                // Common UI elements
                'common.back_to_following': '→ חזרה למעקב',
                'common.monday': 'ב\'',
                'common.tuesday': 'ג\'',
                'common.wednesday': 'ד\'',
                'common.thursday': 'ה\'',
                'common.friday': 'ו\'',
                'common.saturday': 'ש\'',
                'common.sunday': 'א\'',
                'common.today': 'היום',
                'following.your_level_of_access': ':רמת הגישה שלך',
                'following.view_full_profile': 'צפה בפרופיל המלא',
                'following.circles': 'מעגלים',
                'alerts.wellness_alert': 'התראת בריאות עבור',
                'alerts.mood_low': 'מצב הרוח היה נמוך מ-3.0 במשך 3 ימים רצופים',
                'alerts.energy_low': 'האנרגיה הייתה נמוכה מ-3.0 במשך 3 ימים רצופים',
                // Tooltip help texts
                'tooltip.mood': 'עד כמה הרגשת טוב או רע היום?\n\n1 = רע - מרגיש מדוכא, עצוב או שפל\n2 = מתחת לממוצע - לא במיטבך, אבל מתמודד\n3 = בסדר - יציב או נייטרלי באופן סביר\n4 = טוב - מרגיש חיובי, שבע רצון או אופטימי\n\nזכור: מצב הרוח משתנה באופן טבעי מיום ליום. אתה עוקב אחר דפוסים לאורך זמן כדי להבין את עצמך טוב יותר, לא שופט ימים בודדים. גם ימים קשים מספקים מידע חשוב.',
                'tooltip.energy': 'זה עוקב אחר הסיבולת הפיזית והחדות המנטלית שלך לאורך היום.\n\n1 = מרוקן - מותש, מתקשה להתרכז או להשלים משימות בסיסיות\n2 = נמוך - עייף ורץ על רזרבות, הכל מרגיש מאמץ\n3 = בינוני - אנרגיה סבירה לעשות דברים, יכול להתרכז באופן סביר, קצת עייפות בסוף היום\n4 = גבוה - אנרגטי וערני, קל להתרכז ולהשיג משימות, מרגיש מסוגל\n\nזכור: אנרגיה נמוכה היא לא עצלות - זה מידע. גורמים רבים משפיעים על אנרגיה (שינה, מתח, תזונה, בריאות). מעקב אחר דפוסים עוזר לך לזהות מה תומך או מרוקן אותך.',
                'tooltip.sleep_quality': 'זה עוקב אחר איך ישנת, לא רק כמה זמן. איכות חשובה לא פחות מכמות, ולילה קשה אחד לא מגדיר דפוס.\n\n1 = גרוע - כמעט לא ישנתי או שינה מופרעת מאוד, התעוררתי לא רענן\n2 = חסר מנוחה - קצת שינה אבל התעוררתי הרבה, עדיין עייף\n3 = סביר - ישנתי באופן סביר עם הפרעות קלות\n4 = טוב - ישנתי היטב, התעוררתי רענן\n\nזכור: שינה מושפעת ממתח, סביבה, בריאות וגורמים רבים אחרים. אתה עוקב אחר דפוסים כדי להבין מה עוזר או מפריע למנוחה שלך, לא להשיג שינה מושלמת כל לילה.',
                'tooltip.physical_activity': 'סקאלה זו לוכדת את הפעילות הגופנית הכוללת שלך - בהתחשב גם בכמה זמן וגם באיזו עוצמה זזת היום.\n\n1 = מינימלי - יום מנוחה, תנועה קלה מאוד, או פעילות קצרה (פחות מ-15 דקות)\n2 = קל - פעילות קצרה (15-30 דקות) בקצב קל, או תנועה עדינה ארוכה יותר (דוגמאות: הליכה קצרה, מתיחות, משימות בית קלות)\n3 = בינוני - 30-60 דקות של פעילות בינונית או פעילות אינטנסיבית קצרה יותר (דוגמאות: הליכה מהירה, סידורים פעילים, אימון רגיל)\n4 = משמעותי - פעילות ממושכת (60+ דקות), אימון באינטנסיביות גבוהה, או מספר מפגשי פעילות\n\nזכור: זה עוקב אחר דפוסי התנועה שלך, לא הערך שלך. מנוחה חיונית. המטרה היא מודעות והתקדמות הדרגתית, לא שלמות.',
                'tooltip.anxiety': 'חרדה היא רגש אנושי נורמלי שכולם חווים. סקאלה זו עוקבת אחר כמה חרדה מפריעה לחיי היומיום שלך, לא האם אתה מרגיש חרד בכלל.\n\n1 = ניתן לניהול - מרגיש רגוע או כל חרדה קיימת לא מפריעה לפעילויות\n2 = מורגש - קצת חרדה, אבל עדיין מסוגל לעשות מה שצריך\n3 = מאתגר - חרדה מקשה על חלק מהפעילויות\n4 = מציף - חרדה מפריעה משמעותית לתפקוד היומיומי\n\nזכור: המטרה אינה לחסל את כל החרדה, אלא לשמור עליה ברמות שבהן אתה עדיין יכול לעסוק בחיים שלך.'
            });
        }

        // Arabic translations
        if (!window.i18n.translations.ar['parameters.mood']) {
            Object.assign(window.i18n.translations.ar, {
                'parameters.title': 'المذكرة',
                'parameters.select_date': 'اختر التاريخ',
                'parameters.mood': 'المزاج',
                'parameters.mood_desc': 'الحالة العاطفية العامة',
                'parameters.energy': 'الطاقة',
                'parameters.energy_desc': 'مستويات الطاقة الجسدية والعقلية',
                'parameters.sleep_quality': 'جودة النوم',
                'parameters.sleep_quality_desc': 'جودة النوم',
                'parameters.physical_activity': 'النشاط البدني',
                'parameters.physical_activity_desc': 'مستوى النشاط البدني',
                'parameters.anxiety': 'القلق',
                'parameters.anxiety_desc': 'مستوى القلق المُجرب',
                'parameters.notes': 'ملاحظات',
                'parameters.notes_placeholder': 'أفكار إضافية لليوم...',
                'parameters.save': 'حفظ المعاملات',
                'parameters.load': 'تحميل المعاملات',
                'parameters.clear': 'مسح النموذج',
               'parameters.home': 'الصفحة الرئيسية',
                'parameters.saved': 'تم حفظ المعاملات بنجاح!',
                'parameters.loaded': 'تم تحميل المعاملات لـ',
                'parameters.cleared': 'تم مسح النموذج',
                'parameters.no_saved': 'لا توجد معاملات محفوظة لهذا التاريخ',
                'parameters.today_label': 'اليوم',
                'error.saving': 'خطأ في حفظ المعاملات',
                'privacy.public': 'عام',
'privacy.class_b': 'الأصدقاء المقربون',
'privacy.class_a': 'العائلة',
'privacy.private': 'خاص',
                'error.loading': 'خطأ في تحميل المعاملات',
                // Common UI elements
                'common.back_to_following': '→ العودة إلى المتابعة',
                'common.monday': 'الاثنين',
                'common.tuesday': 'الثلاثاء',
                'common.wednesday': 'الأربعاء',
                'common.thursday': 'الخميس',
                'common.friday': 'الجمعة',
                'common.saturday': 'السبت',
                'common.sunday': 'الأحد',
                'common.today': 'اليوم',
                'following.your_level_of_access': ':مستوى وصولك',
                'following.view_full_profile': 'عرض الملف الشخصي الكامل',
                'following.circles': 'الدوائر',
                'alerts.wellness_alert': 'تنبيه العافية لـ',
                'alerts.mood_low': 'كان المزاج أقل من 3.0 لمدة 3 أيام متتالية',
                'alerts.energy_low': 'كانت الطاقة أقل من 3.0 لمدة 3 أيام متتالية',
                // Tooltip help texts
                'tooltip.mood': 'كيف شعرت اليوم - جيد أم سيء؟\n\n1 = سيء - تشعر بالإحباط أو الحزن أو الانخفاض\n2 = أقل من المتوسط - لست في أفضل حالاتك، لكنك تتدبر أمرك\n3 = بخير - مستقر أو محايد بشكل معقول\n4 = جيد - تشعر بالإيجابية أو الرضا أو التفاؤل\n\nتذكر: المزاج يتقلب بشكل طبيعي من يوم لآخر. أنت تتتبع الأنماط بمرور الوقت لفهم نفسك بشكل أفضل، وليس للحكم على الأيام الفردية. حتى الأيام الصعبة توفر معلومات قيمة.',
                'tooltip.energy': 'هذا يتتبع قدرتك البدنية وحدتك الذهنية طوال اليوم.\n\n1 = مستنفد - منهك، تكافح للتركيز أو إكمال المهام الأساسية\n2 = منخفض - متعب وتعمل على الاحتياطي، كل شيء يبدو مرهقاً\n3 = معتدل - طاقة جيدة لإنجاز الأمور، يمكنك التركيز بشكل معقول، بعض الإرهاق بنهاية اليوم\n4 = عالي - نشيط ومنتبه، سهل التركيز وإنجاز المهام، تشعر بالقدرة\n\nتذكر: الطاقة المنخفضة ليست كسلاً - إنها معلومات. عوامل كثيرة تؤثر على الطاقة (النوم، التوتر، التغذية، الصحة). تتبع الأنماط يساعدك على تحديد ما يدعمك أو يستنزفك.',
                'tooltip.sleep_quality': 'هذا يتتبع مدى جودة نومك، وليس فقط المدة. الجودة مهمة بقدر الكمية، وليلة صعبة واحدة لا تحدد نمطاً.\n\n1 = سيء - بالكاد نمت أو نوم مضطرب جداً، استيقظت غير منتعش\n2 = مضطرب - بعض النوم لكن استيقظت كثيراً، لا زلت متعباً\n3 = مقبول - نمت بشكل معقول مع انقطاعات طفيفة\n4 = جيد - نمت بعمق، استيقظت منتعشاً\n\nتذكر: النوم يتأثر بالتوتر والبيئة والصحة وعوامل أخرى كثيرة. أنت تتتبع الأنماط لفهم ما يساعد أو يعيق راحتك، وليس لتحقيق نوم مثالي كل ليلة.',
                'tooltip.physical_activity': 'هذا المقياس يلتقط نشاطك البدني الكلي - مع الأخذ بعين الاعتبار المدة والشدة.\n\n1 = الحد الأدنى - يوم راحة، حركة خفيفة جداً، أو نشاط قصير (أقل من 15 دقيقة)\n2 = خفيف - نشاط قصير (15-30 دقيقة) بوتيرة سهلة، أو حركة لطيفة أطول (أمثلة: مشي قصير، تمدد، مهام منزلية خفيفة)\n3 = معتدل - 30-60 دقيقة من النشاط المعتدل أو نشاط مكثف أقصر (أمثلة: مشي سريع، مهام نشطة، تمرين عادي)\n4 = كبير - نشاط ممتد (60+ دقيقة)، تمرين عالي الشدة، أو جلسات نشاط متعددة\n\nتذكر: هذا يتتبع أنماط حركتك، وليس قيمتك. الراحة ضرورية. الهدف هو الوعي والتقدم التدريجي، وليس الكمال.',
                'tooltip.anxiety': 'القلق هو عاطفة إنسانية طبيعية يختبرها الجميع. هذا المقياس يتتبع مدى تدخل القلق في حياتك اليومية، وليس ما إذا كنت تشعر بالقلق على الإطلاق.\n\n1 = يمكن التحكم فيه - تشعر بالهدوء أو أي قلق موجود لا يتدخل في الأنشطة\n2 = ملحوظ - بعض القلق، لكن لا تزال قادراً على فعل ما تحتاجه\n3 = صعب - القلق يجعل بعض الأنشطة صعبة\n4 = طاغي - القلق يتدخل بشكل كبير في الأداء اليومي\n\nتذكر: الهدف ليس القضاء على كل القلق، بل الحفاظ عليه في مستويات حيث لا يزال بإمكانك الانخراط في حياتك.'
            });
        }

        // Russian translations
        if (!window.i18n.translations.ru['parameters.mood']) {
            Object.assign(window.i18n.translations.ru, {
                'parameters.title': 'Дневник',
                'parameters.select_date': 'Выберите дату',
                'parameters.mood': 'Настроение',
                'parameters.mood_desc': 'Общее эмоциональное состояние',
                'parameters.energy': 'Энергия',
                'parameters.energy_desc': 'Уровни физической и ментальной энергии',
                'parameters.sleep_quality': 'Качество сна',
                'parameters.sleep_quality_desc': 'Качество сна',
                'parameters.physical_activity': 'Физическая активность',
                'parameters.physical_activity_desc': 'Уровень физической активности',
                'parameters.anxiety': 'Тревожность',
                'parameters.anxiety_desc': 'Уровень испытанной тревожности',
                'parameters.notes': 'Заметки',
                'parameters.notes_placeholder': 'Дополнительные мысли на сегодня...',
                'parameters.save': 'Сохранить параметры',
                'parameters.load': 'Загрузить параметры',
                'parameters.clear': 'Очистить форму',
                'parameters.home': 'Главная',
                'parameters.saved': 'Параметры успешно сохранены!',
                'parameters.loaded': 'Параметры загружены для',
                'parameters.cleared': 'Форма очищена',
                'parameters.no_saved': 'Нет сохраненных параметров для этой даты',
                'parameters.today_label': 'Сегодня',
                'error.saving': 'Ошибка сохранения параметров',
                'privacy.public': 'Публичный',
'privacy.class_b': 'Близкие друзья',
'privacy.class_a': 'Семья',
'privacy.private': 'Приватный',
                'error.loading': 'Ошибка загрузки параметров',
                // Common UI elements
                'common.back_to_following': '← Назад к подпискам',
                'common.monday': 'Пн',
                'common.tuesday': 'Вт',
                'common.wednesday': 'Ср',
                'common.thursday': 'Чт',
                'common.friday': 'Пт',
                'common.saturday': 'Сб',
                'common.sunday': 'Вс',
                'common.today': 'Сегодня',
                'following.your_level_of_access': 'Ваш уровень доступа:',
                'following.view_full_profile': 'Просмотреть полный профиль',
                'following.circles': 'Круги',
                'alerts.wellness_alert': 'Предупреждение о здоровье для',
                'alerts.mood_low': 'настроение было ниже 3.0 в течение 3 дней подряд',
                'alerts.energy_low': 'энергия была ниже 3.0 в течение 3 дней подряд',
                // Tooltip help texts
                'tooltip.mood': 'Насколько хорошо или плохо вы себя чувствовали сегодня?\n\n1 = Плохо - Чувствуете себя подавленным, грустным или упавшим\n2 = Ниже среднего - Не в лучшей форме, но справляетесь\n3 = Нормально - Достаточно стабильное или нейтральное состояние\n4 = Хорошо - Чувствуете себя позитивно, довольным или оптимистичным\n\nПомните: Настроение естественно колеблется день ото дня. Вы отслеживаете закономерности со временем, чтобы лучше понять себя, а не осуждать отдельные дни. Даже трудные дни дают ценную информацию.',
                'tooltip.energy': 'Это отслеживает вашу физическую выносливость и умственную остроту в течение дня.\n\n1 = Истощён - Измотан, трудно сосредоточиться или выполнить базовые задачи\n2 = Низкая - Устал и работаете на резервах, всё требует усилий\n3 = Умеренная - Достаточно энергии для выполнения дел, можете сносно концентрироваться, некоторая усталость к концу дня\n4 = Высокая - Энергичный и бодрый, легко сосредоточиться и выполнять задачи, чувствуете себя способным\n\nПомните: Низкая энергия - это не лень, это информация. Многие факторы влияют на энергию (сон, стресс, питание, здоровье). Отслеживание закономерностей помогает определить, что вас поддерживает или истощает.',
                'tooltip.sleep_quality': 'Это отслеживает качество вашего сна, а не только продолжительность. Качество важно не меньше количества, и одна плохая ночь не определяет закономерность.\n\n1 = Плохо - Почти не спал или очень прерывистый сон, проснулся неотдохнувшим\n2 = Беспокойный - Немного поспал, но часто просыпался, всё ещё устал\n3 = Нормально - Спал достаточно хорошо с незначительными прерываниями\n4 = Хорошо - Спал крепко, проснулся отдохнувшим\n\nПомните: На сон влияют стресс, окружение, здоровье и многие другие факторы. Вы отслеживаете закономерности, чтобы понять, что помогает или мешает вашему отдыху, а не достичь идеального сна каждую ночь.',
                'tooltip.physical_activity': 'Эта шкала фиксирует вашу общую физическую активность - учитывая как продолжительность, так и интенсивность.\n\n1 = Минимальная - День отдыха, очень лёгкое движение или короткая активность (менее 15 мин)\n2 = Лёгкая - Короткая активность (15-30 мин) в лёгком темпе ИЛИ более длительное мягкое движение (Примеры: короткая прогулка, растяжка, лёгкие домашние дела)\n3 = Умеренная - 30-60 мин умеренной активности ИЛИ более короткая интенсивная активность (Примеры: быстрая ходьба, активные дела, обычная тренировка)\n4 = Значительная - Продолжительная активность (60+ мин), высокоинтенсивная тренировка ИЛИ несколько сессий активности\n\nПомните: Это отслеживает ваши двигательные паттерны, а не вашу ценность. Отдых необходим. Цель - осознанность и постепенный прогресс, а не совершенство.',
                'tooltip.anxiety': 'Тревога - это нормальная человеческая эмоция, которую испытывают все. Эта шкала отслеживает, насколько тревога мешает вашей повседневной жизни, а не испытываете ли вы тревогу вообще.\n\n1 = Управляемая - Чувствуете спокойствие или имеющаяся тревога не мешает деятельности\n2 = Заметная - Некоторая тревога, но всё ещё можете делать то, что нужно\n3 = Сложная - Тревога затрудняет некоторые виды деятельности\n4 = Подавляющая - Тревога значительно мешает повседневному функционированию\n\nПомните: Цель не в том, чтобы устранить всю тревогу, а в том, чтобы поддерживать её на уровне, при котором вы всё ещё можете жить своей жизнью.'
            });
        }

        // Add month translations if missing
        const months = ['january', 'february', 'march', 'april', 'may', 'june',
                       'july', 'august', 'september', 'october', 'november', 'december'];

        months.forEach((month, index) => {
            const key = `month.${month}`;

            // English
            if (!window.i18n.translations.en[key]) {
                window.i18n.translations.en[key] = month.charAt(0).toUpperCase() + month.slice(1);
            }

            // Hebrew months
            const hebrewMonths = ['ינואר', 'פברואר', 'מרץ', 'אפריל', 'מאי', 'יוני',
                                  'יולי', 'אוגוסט', 'ספטמבר', 'אוקטובר', 'נובמבר', 'דצמבר'];
            if (!window.i18n.translations.he[key]) {
                window.i18n.translations.he[key] = hebrewMonths[index];
            }

            // Arabic months
            const arabicMonths = ['يناير', 'فبراير', 'مارس', 'أبريل', 'مايو', 'يونيو',
                                  'يوليو', 'أغسطس', 'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر'];
            if (!window.i18n.translations.ar[key]) {
                window.i18n.translations.ar[key] = arabicMonths[index];
            }

            // Russian months
            const russianMonths = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
                                   'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'];
            if (!window.i18n.translations.ru[key]) {
                window.i18n.translations.ru[key] = russianMonths[index];
            }
        });
    }
};

// Format date for display
// Format date for display
function formatDate(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

// Convert date format from backend to YYYY-MM-DD
function convertDateFormat(dateStr) {
    // Convert from "Fri, 10 Oct 2025 00:00:00 GMT" to "2025-10-10"
    const date = new Date(dateStr);
    return formatDate(date);
}

// Load saved dates from backend
async function loadSavedDates() {
    try {
        const response = await fetch('/api/parameters/dates');
        if (response.ok) {
            const data = await response.json();
            if (data.dates) {
                // Convert date formats
                const formattedDates = data.dates.map(convertDateFormat);
                datesWithData = new Set(formattedDates);
                localStorage.setItem('savedParameterDates', JSON.stringify(formattedDates));
                updateCalendar(); // Refresh to show green dots
            }
        }
    } catch (error) {
        console.error('Error loading saved dates:', error);
    }
}

// Show message function - FIXED SCOPE
window.showMessage = function(text, type = 'success', duration = 5000, isFlashy = false) {
    const container = document.getElementById('messageContainer');
    if (!container) {
        console.error('Message container not found');
        return;
    }

    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type} ${isFlashy ? 'flashy' : ''}`;

    if (isFlashy) {
        const flashyContent = document.createElement('div');
        flashyContent.className = 'flashy-content';

        const icon1 = document.createElement('span');
        icon1.className = 'flashy-icon';
        icon1.textContent = '🌟';

        const flashyText = document.createElement('p');
        flashyText.className = 'flashy-text';
        flashyText.textContent = text;

        const icon2 = document.createElement('span');
        icon2.className = 'flashy-icon';
        icon2.textContent = '🌟';

        flashyContent.appendChild(icon1);
        flashyContent.appendChild(flashyText);
        flashyContent.appendChild(icon2);
        messageDiv.appendChild(flashyContent);

        window.scrollTo({ top: 0, behavior: 'smooth' });
    } else {
        messageDiv.textContent = text;
    }

    container.appendChild(messageDiv);

    setTimeout(() => {
        messageDiv.style.animation = 'fadeOut 0.5s ease-out';
        setTimeout(() => messageDiv.remove(), 500);
    }, duration);
};

// Main initialization function
// Main initialization function
function initializeParameters() {
    console.log('Initializing parameters system...');

    // Initialize global variables
    window.selectedPrivacy = window.selectedPrivacy || {};

    // Set default privacy to public for all parameters (matches backend default)
    // These will be overwritten when we auto-load today's saved data
    ['mood', 'energy', 'sleep_quality', 'physical_activity', 'anxiety'].forEach(param => {
        if (!window.selectedPrivacy[param]) {
            window.selectedPrivacy[param] = 'private';
        }
    });

    // Add translations first
    addParameterTranslations();

    //  setTimeout(() => {
      //  fetchAllParameterDates();
   // }, 500);

    // Get container
    const container = document.getElementById('parametersContainer');
    if (!container) {
        console.error('Parameters container not found!');
        return;
    }

    // Clear any existing content
    container.innerHTML = '';

    // Create main structure with language selector and 5 categories
    const html = `
        <div class="parameters-page">
            <!-- Language Selector -->
            <div class="language-selector-wrapper">
                <select id="languageSelector" class="language-selector">
                    <option value="en">English</option>
                    <option value="he">עברית</option>
                    <option value="ar">العربية</option>
                    <option value="ru">Русский</option>
                </select>
            </div>

            <div class="parameters-header">
                <h1 data-i18n="parameters.title">Diary</h1>
            </div>

            <div id="messageContainer"></div>

            <div class="parameters-card">
                <!-- Date Selection -->
                <div class="date-section">
                    <label data-i18n="parameters.select_date">Select Date</label>
                    <div class="date-controls">
                        <button class="date-nav-btn" onclick="previousMonth()">◀</button>
                        <div class="calendar-display">
                            <span id="currentMonthYear"></span>
                        </div>
                        <button class="date-nav-btn" onclick="nextMonth()">▶</button>
                    </div>
                    <div id="calendarGrid" class="calendar-grid"></div>
                </div>

                <!-- Parameters Section - ONLY 5 CATEGORIES -->
                <div class="parameters-section">
                  ${PARAMETER_CATEGORIES.map(category => {
    const privacy = window.selectedPrivacy[category.id] || 'private';
    return `
        <div class="parameter-item">
            <div class="parameter-header">
                <span class="parameter-emoji">${category.emoji}</span>
                <div class="parameter-info">
                    <span class="parameter-name" data-i18n="${category.nameKey}">${category.nameKey}</span>
                    <span class="tooltip-icon" data-tooltip-key="tooltip.${category.id}" onclick="showTooltip('${category.id}', event)" title="">ⓘ</span>
                    <span class="parameter-description" data-i18n="${category.descriptionKey}">${category.descriptionKey}</span>
                </div>
                <div class="privacy-selector">
          <select class="privacy-select"
        data-category="${category.id}"
        onchange="updatePrivacy('${category.id}', this.value)">
    <option value="private" data-i18n="privacy.private" ${privacy === 'private' ? 'selected' : ''}>
        Private
    </option>
    <option value="class_a" data-i18n="privacy.class_a" ${privacy === 'class_a' ? 'selected' : ''}>
        Family
    </option>
    <option value="class_b" data-i18n="privacy.class_b" ${privacy === 'class_b' ? 'selected' : ''}>
        Close Friends
    </option>
    <option value="public" data-i18n="privacy.public" ${privacy === 'public' ? 'selected' : ''}>
        Public
    </option>
</select>
                </div>
            </div>
            <div class="rating-buttons" id="${category.id}-buttons">
                ${[1, 2, 3, 4].map(value => `
                    <button class="rating-button"
                            data-category="${category.id}"
                            data-value="${value}"
                            onclick="selectRating('${category.id}', ${value})">
                        ${value}
                    </button>
                `).join('')}
            </div>
        </div>
    `;
}).join('')}
                </div>

                <!-- Notes Section -->
                <div class="notes-section">
                    <label data-i18n="parameters.notes">Notes</label>
                    <textarea id="notesInput"
                              data-i18n-placeholder="parameters.notes_placeholder"
                              placeholder="Additional thoughts for today..."></textarea>
                </div>

                <!-- Action Buttons -->
                <div class="action-buttons">
                    <button class="btn btn-primary" onclick="saveParameters()" data-i18n="parameters.save">Save Parameters</button>
                    <button class="btn btn-secondary" onclick="loadParameters()" data-i18n="parameters.load">Load Parameters</button>
                    <button class="btn btn-clear" onclick="clearParameters()" data-i18n="parameters.clear">Clear Form</button>
                    <button class="btn btn-menu" onclick="goToHome()" data-i18n="parameters.home">Home</button>
                </div>
            </div>
        </div>
    `;

    container.innerHTML = html;

    // Add styles
    addParameterStyles();

    // Setup language selector (now async - uses .then() for non-blocking execution)
    setupLanguageSelector().then(() => {
        console.log('[INIT] Language selector setup complete');
    }).catch(err => {
        console.error('[INIT] Language selector setup error:', err);
    });

    // Initialize calendar
    updateCalendar();

    // Auto-load today's parameters (including privacy settings) from server
    // This fixes the issue where privacy settings reset after browser cache clear
    const todayStr = formatDate(new Date());
    setTimeout(async () => {
        try {
            const response = await fetch(`/api/parameters?date=${todayStr}`);
            if (response.ok) {
                const result = await response.json();
                if (result.success && result.data) {
                    console.log('Auto-loaded today\'s parameters:', result.data);
                    
                    // Check if today has actual saved data (any non-zero parameter value)
                    const hasRealData = result.data.parameters && 
                        Object.values(result.data.parameters).some(v => v && v > 0);
                    
                    if (hasRealData) {
                        // Load privacy settings from today's saved data
                        ['mood', 'energy', 'sleep_quality', 'physical_activity', 'anxiety'].forEach(param => {
                            const privacyKey = `${param}_privacy`;
                            const privacyValue = result.data[privacyKey] || 'private';
                            
                            window.selectedPrivacy[param] = privacyValue;
                            
                            // Update the dropdown UI
                            const selector = document.querySelector(`select[data-category="${param}"]`);
                            if (selector) {
                                selector.value = privacyValue;
                            }
                        });
                        
                        // Also load ratings if they exist
                        if (result.data.parameters) {
                            Object.keys(result.data.parameters).forEach(categoryId => {
                                const value = result.data.parameters[categoryId];
                                if (value) {
                                    selectRating(categoryId, value);
                                }
                            });
                        }
                        
                        // Load notes
                        const notesInput = document.getElementById('notesInput');
                        if (notesInput && result.data.notes) {
                            notesInput.value = result.data.notes;
                        }
                    } else {
                        // No saved data for today - try to load privacy settings from most recent entry
                        console.log('No data for today, fetching most recent privacy settings...');
                        await loadMostRecentPrivacySettings();
                    }
                    
                    // Apply emojis to reflect loaded privacy
                    applyEmojisToPrivacySelectors();
                }
            }
        } catch (error) {
            console.log('No saved parameters for today, trying to load recent privacy settings');
            // Try to load most recent privacy settings even if today's fetch fails
            await loadMostRecentPrivacySettings();
            applyEmojisToPrivacySelectors();
        }
    }, 200);


 //setTimeout(() => {
   //     loadSavedDates();
    //}, 500);

   console.log('Parameters system initialized successfully');

    // Call fetchAllParameterDates after a delay to ensure everything is loaded
    setTimeout(() => {
        if (typeof fetchAllParameterDates === 'function') {
            fetchAllParameterDates();
        }
    }, 1000);

  const year = currentDate.getFullYear();
    const month = currentDate.getMonth();
    setTimeout(() => checkMonthData(year, month), 100);


    // Apply translations
    if (window.i18n && window.i18n.applyLanguage) {
        window.i18n.applyLanguage();
    }

   console.log('Parameters system initialized successfully with language selector and 5 categories');

    // Apply emojis to privacy selectors after a brief delay
    setTimeout(applyEmojisToPrivacySelectors, 150);
}

// P101 FIX: Setup language selector with backend as source of truth
async function setupLanguageSelector() {
    console.log('[PS LANG DEBUG P101] ========================================');
    console.log('[PS LANG DEBUG P101] setupLanguageSelector() STARTED');
    console.log('[PS LANG DEBUG P101] Timestamp:', new Date().toISOString());
    
    const selector = document.getElementById('languageSelector');
    if (!selector) {
        console.error('[PS LANG DEBUG P101] ERROR: Selector not found!');
        return;
    }
    
    console.log('[PS LANG DEBUG P101] INITIAL STATE:');
    console.log('[PS LANG DEBUG P101]   selector.value:', selector.value);
    console.log('[PS LANG DEBUG P101]   localStorage.selectedLanguage:', localStorage.getItem('selectedLanguage'));
    console.log('[PS LANG DEBUG P101]   i18n.currentLanguage:', window.i18n?.currentLanguage);

    // P101 FIX: Check justLoggedIn flag FIRST - if just logged in, trust localStorage
    const justLoggedIn = sessionStorage.getItem('justLoggedIn');
    console.log('[PS LANG DEBUG P101] justLoggedIn flag:', justLoggedIn);
    
    let currentLang = null;
    let backendLang = null;
    
    if (justLoggedIn) {
        // User just logged in - localStorage was set at login time, trust it
        currentLang = localStorage.getItem('selectedLanguage') || 'en';
        console.log('[PS LANG DEBUG P101] justLoggedIn=true, using localStorage:', currentLang);
    } else {
        // Not just logged in - fetch from backend (SOURCE OF TRUTH)
        try {
            console.log('[PS LANG DEBUG P101] Fetching backend profile...');
            const profileResponse = await fetch('/api/user/profile', {
                credentials: 'include'
            });
            if (profileResponse.ok) {
                const profile = await profileResponse.json();
                backendLang = profile.preferred_language || profile.language;
                console.log('[PS LANG DEBUG P101] Backend language from profile:', backendLang);
            } else {
                console.log('[PS LANG DEBUG P101] Profile fetch failed, status:', profileResponse.status);
            }
        } catch (e) {
            console.error('[PS LANG DEBUG P101] Profile fetch error:', e);
        }

        // P101 FIX: Backend is SOURCE OF TRUTH - use it if available
        if (backendLang) {
            currentLang = backendLang;
            // Update localStorage to MATCH backend (not vice versa!)
            const oldLocal = localStorage.getItem('selectedLanguage');
            if (oldLocal !== currentLang) {
                console.log('[PS LANG DEBUG P101] Updating localStorage from', oldLocal, 'to', currentLang);
            }
        } else {
            // Fallback to localStorage only if backend unavailable
            currentLang = localStorage.getItem('selectedLanguage') || 
                          localStorage.getItem('userLanguage') ||
                          (window.i18n?.getCurrentLanguage?.()) ||
                          'en';
            console.log('[PS LANG DEBUG P101] Backend unavailable, using fallback:', currentLang);
        }
    }

    console.log('[PS LANG DEBUG P101] Resolved language:', currentLang);

    // Sync localStorage with the determined language
    localStorage.setItem('selectedLanguage', currentLang);
    localStorage.setItem('userLanguage', currentLang);
    console.log('[PS LANG DEBUG P101] localStorage updated to:', currentLang);

    // CRITICAL FIX: Set programmatic flag BEFORE setting selector value
    console.log('[PS LANG DEBUG P101] Setting selector value with programmatic flag...');
    window._updatingSelectorProgrammatically = true;
    selector.value = currentLang;
    window._updatingSelectorProgrammatically = false;
    console.log('[PS LANG DEBUG P101] Selector value set to:', selector.value);

    // Update i18n if available
    if (window.i18n && window.i18n.setLanguage) {
        console.log('[PS LANG DEBUG P101] Calling i18n.setLanguage...');
        await window.i18n.setLanguage(currentLang);
    }

    // Force a re-render of the selector to ensure it displays properly
    setTimeout(() => {
        if (!selector.value || selector.value === '') {
            console.warn('[PS LANG DEBUG P101] Selector empty after timeout, forcing to:', currentLang);
            window._updatingSelectorProgrammatically = true;
            selector.value = currentLang || 'en';
            window._updatingSelectorProgrammatically = false;
        }
    }, 10);

    // Track user interaction with the selector for this file too
    selector.addEventListener('mousedown', function() {
        console.log('[PS LANG P101] User mousedown on selector');
        window._userClickedLanguageSelector = true;
        window._lastLanguageSelectorInteraction = Date.now();
    });

    // Handle language change - only fires for USER-INITIATED changes
    selector.addEventListener('change', function() {
        console.log('[PS CHANGE DEBUG P101] ========================================');
        console.log('[PS CHANGE DEBUG P101] CHANGE EVENT FIRED');
        console.log('[PS CHANGE DEBUG P101] Timestamp:', new Date().toISOString());
        console.log('[PS CHANGE DEBUG P101] _updatingSelectorProgrammatically:', window._updatingSelectorProgrammatically);
        console.log('[PS CHANGE DEBUG P101] _userClickedLanguageSelector:', window._userClickedLanguageSelector);
        console.log('[PS CHANGE DEBUG P101] this.value:', this.value);
        
        // FIX: Skip if being updated programmatically
        if (window._updatingSelectorProgrammatically) {
            console.log('[PS CHANGE DEBUG P101] Programmatic update - SKIPPING');
            console.log('[PS CHANGE DEBUG P101] ========================================');
            return;
        }
        
        const newLang = this.value;
        const storedLang = localStorage.getItem('selectedLanguage');
        const timeSinceInteraction = Date.now() - (window._lastLanguageSelectorInteraction || 0);
        
        console.log('[PS CHANGE DEBUG P101] New language:', newLang);
        console.log('[PS CHANGE DEBUG P101] Stored language:', storedLang);
        console.log('[PS CHANGE DEBUG P101] Time since interaction:', timeSinceInteraction, 'ms');
        
        // FIX: Validate the new language - if empty, restore from localStorage
        if (!newLang || newLang === '') {
            console.error('[PS CHANGE DEBUG P101] EMPTY LANGUAGE - restoring to:', storedLang || 'en');
            window._updatingSelectorProgrammatically = true;
            this.value = storedLang || 'en';
            window._updatingSelectorProgrammatically = false;
            console.log('[PS CHANGE DEBUG P101] ========================================');
            return;
        }

        // P101 FIX: Double-check that this is a real user interaction
        // If not, block the change and restore to stored value
        const isRealUserInteraction = window._userClickedLanguageSelector && timeSinceInteraction < 10000;
        if (!isRealUserInteraction && newLang !== storedLang) {
            console.error('[PS CHANGE DEBUG P101] SUSPICIOUS CHANGE BLOCKED!');
            console.error('[PS CHANGE DEBUG P101]   Not a confirmed user interaction');
            console.error('[PS CHANGE DEBUG P101]   Restoring to:', storedLang);
            window._updatingSelectorProgrammatically = true;
            this.value = storedLang || 'en';
            window._updatingSelectorProgrammatically = false;
            console.log('[PS CHANGE DEBUG P101] ========================================');
            return;
        }

        console.log('[PS CHANGE DEBUG P101] Valid user-initiated change to:', newLang);
        
        // Save to localStorage BEFORE any other actions
        localStorage.setItem('selectedLanguage', newLang);
        localStorage.setItem('userLanguage', newLang);

        // Update i18n if available
        if (window.i18n && window.i18n.setLanguage) {
            window.i18n.setLanguage(newLang);
        }

        // Update RTL
        const rtlLanguages = ['ar', 'he'];
        if (rtlLanguages.includes(newLang)) {
            document.body.setAttribute('dir', 'rtl');
        } else {
            document.body.setAttribute('dir', 'ltr');
        }

        // Update translations
        updateTranslations();

        // Send to server to save preference - ONLY for user-initiated changes
        console.log('[PS CHANGE DEBUG P101] POSTing to /api/user/language:', newLang);
        if (window.fetch) {
            // CRITICAL: Set flag to allow this POST through the interceptor
            window._allowLanguagePost = true;
            console.log('[PS CHANGE DEBUG P101] Set _allowLanguagePost = true');
            
            fetch('/api/user/language', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'include',
                body: JSON.stringify({ language: newLang })
            }).then(resp => {
                console.log('[PS CHANGE DEBUG P101] POST response status:', resp.status);
            }).catch(err => {
                console.error('[PS CHANGE DEBUG P101] POST error:', err);
            });
        }
        
        // Reset the user interaction flag
        window._userClickedLanguageSelector = false;
        
        console.log('[PS CHANGE DEBUG P101] ========================================');
    });

    // Set initial RTL direction based on current language
    const rtlLanguages = ['ar', 'he'];
    if (rtlLanguages.includes(currentLang)) {
        document.body.setAttribute('dir', 'rtl');
    } else {
        document.body.setAttribute('dir', 'ltr');
    }

    // Apply translations after setting language
    if (typeof updateTranslations === 'function') {
        updateTranslations();
    }
    
    console.log('[PS LANG DEBUG P101] FINAL STATE:');
    console.log('[PS LANG DEBUG P101]   selector.value:', selector.value);
    console.log('[PS LANG DEBUG P101]   localStorage.selectedLanguage:', localStorage.getItem('selectedLanguage'));
    console.log('[PS LANG DEBUG P101] setupLanguageSelector() COMPLETED');
    console.log('[PS LANG DEBUG P101] ========================================');
}

// Add parameter-specific styles
function addParameterStyles() {
    if (document.getElementById('parameterStyles')) return;

    const style = document.createElement('style');
    style.id = 'parameterStyles';
    style.textContent = `
        .parameters-page {
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            position: relative;
        }

        /* Language Selector */
        .language-selector-wrapper {
            position: absolute;
            top: 20px;
            right: 20px;
            z-index: 100;
        }

        [dir="rtl"] .language-selector-wrapper {
            right: auto;
            left: 20px;
        }

        .language-selector {
            padding: 8px 12px;
            border: 2px solid #667eea;
            border-radius: 8px;
            background: white;
            color: #667eea;
            font-weight: 600;
            cursor: pointer;
            min-width: 120px;
            font-size: 14px;
        }

        .language-selector:hover {
            background: #f8f9fa;
        }

        .parameters-header {
            text-align: center;
            margin-bottom: 30px;
            margin-top: 60px;
        }

        .parameters-header h1 {
            color: white;
            font-size: 2.5em;
            margin: 0;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }

        .parameters-card {
            background: white;
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }

        .date-section {
            margin-bottom: 30px;
        }

        .date-section label {
            display: block;
            font-weight: 600;
            color: #333;
            margin-bottom: 15px;
            font-size: 1.1em;
        }

        .date-controls {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 20px;
            margin-bottom: 20px;
        }

        .date-nav-btn {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            font-size: 18px;
            cursor: pointer;
            transition: transform 0.3s ease;
        }

        .date-nav-btn:hover {
            transform: scale(1.1);
        }

        .calendar-display {
            font-size: 1.3em;
            font-weight: 600;
            color: #333;
            min-width: 200px;
            text-align: center;
        }

        .calendar-grid {
            display: grid;
            grid-template-columns: repeat(7, 1fr);
            gap: 8px;
            margin-top: 15px;
        }

        .calendar-day {
            padding: 10px;
            text-align: center;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            cursor: pointer;
            background: white;
            transition: all 0.3s ease;
        }

        .calendar-day:hover {
            background: #f0f0f0;
            transform: translateY(-2px);
        }

        .calendar-day.selected {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-color: #667eea;
        }

        .calendar-day.today {
            border-color: #667eea;
            font-weight: bold;
        }


.calendar-day.has-data {
    position: relative;
}

.data-indicator {
    position: absolute;
    bottom: 2px;
    left: 50%;
    transform: translateX(-50%);
    color: #10b981;
    font-size: 8px;
}



        .parameters-section {
            margin: 30px 0;
        }

        .parameter-item {
            margin-bottom: 25px;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 10px;
        }

        .parameter-header {
            display: flex;
            align-items: center;
            margin-bottom: 15px;
        }

        .parameter-emoji {
            font-size: 2em;
            margin-right: 15px;
        }

        [dir="rtl"] .parameter-emoji {
            margin-right: 0;
            margin-left: 15px;
        }

        .parameter-info {
            display: flex;
            flex-direction: column;
        }

        .parameter-name {
            font-weight: 600;
            font-size: 1.1em;
            color: #333;
        }

        .tooltip-icon {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 18px;
            height: 18px;
            border-radius: 50%;
            background: #667eea;
            color: white;
            font-size: 12px;
            font-weight: bold;
            cursor: pointer;
            margin-left: 8px;
            vertical-align: middle;
            transition: all 0.2s ease;
            font-style: normal;
        }

        .tooltip-icon:hover {
            background: #764ba2;
            transform: scale(1.1);
        }

        [dir="rtl"] .tooltip-icon {
            margin-left: 0;
            margin-right: 8px;
        }

        .tooltip-modal {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.5);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 10000;
            animation: fadeIn 0.2s ease;
        }

        .tooltip-content {
            background: white;
            border-radius: 15px;
            padding: 25px;
            max-width: 500px;
            width: 90%;
            max-height: 80vh;
            overflow-y: auto;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
            position: relative;
        }

        .tooltip-content h3 {
            margin: 0 0 15px 0;
            color: #667eea;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .tooltip-content p {
            margin: 0;
            line-height: 1.6;
            color: #333;
            white-space: pre-line;
        }

        .tooltip-close {
            position: absolute;
            top: 15px;
            right: 15px;
            background: #f0f0f0;
            border: none;
            width: 30px;
            height: 30px;
            border-radius: 50%;
            cursor: pointer;
            font-size: 18px;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.2s ease;
        }

        .tooltip-close:hover {
            background: #e0e0e0;
            transform: scale(1.1);
        }

        [dir="rtl"] .tooltip-close {
            right: auto;
            left: 15px;
        }

        .parameter-description {
            font-size: 0.9em;
            color: #666;
            margin-top: 3px;
        }

        .rating-buttons {
            display: flex;
            gap: 10px;
            justify-content: center;
        }

        .rating-button {
            width: 60px;
            height: 60px;
            border: 2px solid #ddd;
            background: white;
            border-radius: 10px;
            font-size: 1.3em;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            color: #333;
        }

        .rating-button:hover {
            background: #f0f0f0;
            transform: translateY(-3px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }

        .rating-button.selected {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-color: #667eea;
            transform: scale(1.1);
        }

        .notes-section {
            margin: 30px 0;
        }

        .notes-section label {
            display: block;
            font-weight: 600;
            color: #333;
            margin-bottom: 10px;
            font-size: 1.1em;
        }

        .notes-section textarea {
            width: 100%;
            min-height: 120px;
            padding: 12px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 1em;
            resize: vertical;
        }

        .action-buttons {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            justify-content: center;
            margin-top: 30px;
        }

        .btn {
            padding: 12px 24px;
            border: none;
            border-radius: 8px;
            font-size: 1em;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
        }

        .btn-primary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }

        .btn-secondary {
            background: #6c757d;
            color: white;
        }

        .btn-clear {
            background: #dc3545;
            color: white;
        }

        .btn-menu {
            background: #28a745;
            color: white;
        }

        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(0,0,0,0.2);
        }

        #messageContainer {
            margin-bottom: 20px;
        }

        .message {
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 10px;
            animation: slideInDown 0.5s ease;
        }

        .message.success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }

        .message.error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }

        .message.info {
            background: #d1ecf1;
            color: #0c5460;
            border: 1px solid #bee5eb;
        }

        .message.flashy {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 25px;
            font-size: 1.2em;
            animation: pulse 2s infinite;
        }

        .flashy-content {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 15px;
        }

        .flashy-icon {
            font-size: 2em;
            animation: rotate 2s linear infinite;
        }

        .flashy-text {
            margin: 0;
            font-weight: 600;
        }

        @keyframes slideInDown {
            from {
                opacity: 0;
                transform: translateY(-20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        @keyframes fadeOut {
            from { opacity: 1; }
            to { opacity: 0; }
        }

        @keyframes pulse {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.02); }
        }

        @keyframes rotate {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
        }

        /* Mobile Responsiveness */
        @media (max-width: 768px) {
            .parameters-page { padding: 10px; }
            .parameters-card { padding: 20px; }
            .rating-button {
                width: 50px;
                height: 50px;
                font-size: 1.1em;
            }
            .action-buttons { flex-direction: column; }
            .btn { width: 100%; }
            .language-selector-wrapper {
                position: relative;
                top: 0;
                right: 0;
                margin-bottom: 20px;
            }
        }


  .invite-cta {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 15px;
            padding: 25px;
            margin: 20px 0;
            color: white;
            position: relative;
            animation: slideIn 0.5s ease-out;
            box-shadow: 0 10px 30px rgba(102, 126, 234, 0.3);
        }

        .cta-content h3 {
            margin: 0 0 10px 0;
            font-size: 1.4em;
            color: white;
        }

        .cta-content p {
            margin: 0 0 20px 0;
            opacity: 0.95;
        }

        .cta-actions {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }

        .cta-button {
            padding: 12px 20px;
            border: none;
            border-radius: 8px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
            flex: 1;
            min-width: 150px;
        }

        .cta-button.primary {
            background: white;
            color: #667eea;
        }

        .cta-button.primary:hover {
            transform: scale(1.05);
            box-shadow: 0 5px 15px rgba(255, 255, 255, 0.3);
        }

        .cta-button.secondary {
            background: rgba(255, 255, 255, 0.2);
            color: white;
            border: 2px solid white;
        }

        .cta-button.secondary:hover {
            background: rgba(255, 255, 255, 0.3);
            transform: scale(1.05);
        }

        .cta-close {
            position: absolute;
            top: 10px;
            right: 10px;
            background: rgba(255, 255, 255, 0.2);
            border: none;
            color: white;
            width: 30px;
            height: 30px;
            border-radius: 50%;
            cursor: pointer;
            font-size: 18px;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.2s;
        }

        .cta-close:hover {
            background: rgba(255, 255, 255, 0.4);
            transform: scale(1.1);
        }

        @keyframes slideIn {
            from {
                opacity: 0;
                transform: translateY(-20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        @media (max-width: 768px) {
            .cta-actions {
                flex-direction: column;
            }

            .cta-button {
                width: 100%;
            }
        }

        [dir="rtl"] .cta-close {
            right: auto;
            left: 10px;
        }



    `;
    document.head.appendChild(style);
}

// Calendar functions - FIXED: Removed async
// Calendar functions - FIXED: Removed async and preserves green dots
function updateCalendar() {
    const calendarGrid = document.getElementById('calendarGrid');
    const currentMonthYear = document.getElementById('currentMonthYear');

    if (!calendarGrid || !currentMonthYear) return;

    const year = currentDate.getFullYear();
    const month = currentDate.getMonth();
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    const daysInMonth = lastDay.getDate();
    const startingDayOfWeek = firstDay.getDay();

    // Update month/year display with translation
    const monthKey = `month.${['january', 'february', 'march', 'april', 'may', 'june',
                               'july', 'august', 'september', 'october', 'november', 'december'][month]}`;
    currentMonthYear.textContent = `${pt(monthKey)} ${year}`;

    // Clear calendar
    calendarGrid.innerHTML = '';

    // Add day headers with translations
    const dayHeaders = [
        {key: 'common.sunday', fallback: 'Sun'},
        {key: 'common.monday', fallback: 'Mon'},
        {key: 'common.tuesday', fallback: 'Tue'},
        {key: 'common.wednesday', fallback: 'Wed'},
        {key: 'common.thursday', fallback: 'Thu'},
        {key: 'common.friday', fallback: 'Fri'},
        {key: 'common.saturday', fallback: 'Sat'}
    ];
    dayHeaders.forEach(day => {
        const header = document.createElement('div');
        header.className = 'calendar-header';
        header.textContent = pt(day.key) || day.fallback;
        header.style.fontWeight = 'bold';
        header.style.fontSize = '0.9em';
        calendarGrid.appendChild(header);
    });

    // Add empty cells for days before month starts
    for (let i = 0; i < startingDayOfWeek; i++) {
        const emptyCell = document.createElement('div');
        calendarGrid.appendChild(emptyCell);
    }

    // Get today's date for comparison (normalized to start of day)
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    // Add days of the month
    const selectedDateStr = formatDate(currentDate);

    for (let day = 1; day <= daysInMonth; day++) {
        const dayCell = document.createElement('div');
        dayCell.className = 'calendar-day';
        dayCell.textContent = day;

        const cellDate = new Date(year, month, day);
        const cellDateStr = formatDate(cellDate);

        // Check if this is a future date
        const isFutureDate = cellDate > today;

        // Add data-date attribute for targeting
        dayCell.setAttribute('data-date', cellDateStr);

        // Disable future dates
        if (isFutureDate) {
            dayCell.style.opacity = '0.3';
            dayCell.style.cursor = 'not-allowed';
            dayCell.style.pointerEvents = 'none';
            dayCell.title = 'Future date - not available';
        } else {
            // Check if this date has saved data and add green dot
            if (datesWithData.has(cellDateStr)) {
                dayCell.style.position = 'relative';
                const dot = document.createElement('span');
                dot.className = 'data-indicator';
                dot.textContent = '●';
                dot.style.cssText = 'color: #10b981; font-size: 8px; position: absolute; bottom: 2px; left: 50%; transform: translateX(-50%);';
                dayCell.appendChild(dot);
            }

            if (cellDateStr === formatDate(today)) {
                dayCell.classList.add('today');
                dayCell.title = pt('parameters.today_label');
            }

            if (cellDateStr === selectedDateStr) {
                dayCell.classList.add('selected');
            }

            // Only add click handler for past/present dates
            dayCell.onclick = () => selectDate(cellDate);
        }

        calendarGrid.appendChild(dayCell);
    }

    // Check for saved data for current month (only for past dates)
    checkMonthData(year, month);
}


// Check for saved data in current month
// Check for saved data in current month - FIXED to only show dots for actual saved data
async function checkMonthData(year, month) {
    // Get today's date for comparison (normalized)
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    // Clear all existing dots first
    document.querySelectorAll('.calendar-day .data-indicator').forEach(dot => dot.remove());

    // Clear the local storage cache to force fresh check
    datesWithData.clear();

    try {
        // Get all saved dates for this user from the server
        const response = await fetch('/api/parameters/dates');
        if (response.ok) {
            const result = await response.json();
            if (result.dates && Array.isArray(result.dates)) {
                // Update our local set with actual saved dates
                datesWithData = new Set(result.dates);
                localStorage.setItem('savedParameterDates', JSON.stringify([...datesWithData]));

                // Add dots only to dates that actually have data
                result.dates.forEach(dateStr => {
                    const dayElement = document.querySelector(`.calendar-day[data-date="${dateStr}"]`);
                    if (dayElement && !dayElement.querySelector('.data-indicator')) {
                        // Check if this is not a future date
                        const cellDate = new Date(dateStr);
                        if (cellDate <= today) {
                            dayElement.style.position = 'relative';
                            const dot = document.createElement('span');
                            dot.className = 'data-indicator';
                            dot.textContent = '●';
                            dot.style.cssText = 'color: #10b981; font-size: 8px; position: absolute; bottom: 2px; left: 50%; transform: translateX(-50%);';
                            dayElement.appendChild(dot);
                        }
                    }
                });
            }
        }
    } catch (error) {
        console.error('Error checking month data:', error);
        // On error, just don't show any dots rather than showing incorrect ones
        datesWithData.clear();
    }
}


// Check if a specific date has saved data and add green dot
async function checkDateForData(dateStr, dayElement) {
    try {
        const response = await fetch(`/api/parameters?date=${dateStr}`);
        if (response.ok) {
            const result = await response.json();
            if (result.success && result.data) {
                // Add green dot
                if (!dayElement.querySelector('.data-indicator')) {
                    const dot = document.createElement('span');
                    dot.className = 'data-indicator';
                    dot.textContent = '●';
                    dot.style.cssText = 'color: #10b981; font-size: 8px; position: absolute; bottom: 2px; left: 50%; transform: translateX(-50%);';
                    dayElement.style.position = 'relative';
                    dayElement.appendChild(dot);
                }
            }
        }
    } catch (error) {
        // Silently ignore errors
    }
}




// Debounce utility to prevent excessive API calls
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

// Loading flag to prevent concurrent API calls
let isLoadingDates = false;




// Fetch all dates with saved parameters from backend
// FIND THIS:
async function fetchAllParameterDates() {
    // Prevent concurrent calls
    if (isLoadingDates) {
        console.log('Already loading dates, skipping...');
        return;
    }

    isLoadingDates = true;
    try {
        const response = await fetch('/api/parameters/dates');
        const result = await response.json();

        if (result.success && result.dates) {
            // Clear and rebuild the datesWithData set
            datesWithData.clear();
            result.dates.forEach(date => datesWithData.add(date));

            // Save to localStorage for offline access
            localStorage.setItem('savedParameterDates', JSON.stringify(result.dates));

            // Update all calendar days with green dots
            result.dates.forEach(dateStr => {
                const dayElement = document.querySelector(`.calendar-day[data-date="${dateStr}"]`);
                if (dayElement && !dayElement.querySelector('.data-indicator')) {
                    dayElement.style.position = 'relative';
                    const dot = document.createElement('span');
                    dot.className = 'data-indicator';
                    dot.textContent = '●';
                    dot.style.cssText = 'color: #10b981; font-size: 8px; position: absolute; bottom: 2px; left: 50%; transform: translateX(-50%);';
                    dayElement.appendChild(dot);
                }
            });
        }
   } catch (error) {
        console.error('Error fetching parameter dates:', error);
        // Fall back to localStorage if API fails
        const stored = localStorage.getItem('savedParameterDates');
        if (stored) {
            try {
                const dates = JSON.parse(stored);
                datesWithData.clear();
                dates.forEach(date => datesWithData.add(date));
            } catch (e) {
                console.error('Error parsing stored dates:', e);
            }
        }
    } finally {
        // Always reset loading flag
        isLoadingDates = false;
    }
}


// Function to handle following from parameters view with trigger option
function followFromParameters(userId, username) {
    // Create modal for follow with trigger option
    const modal = document.createElement('div');
    modal.className = 'modal-overlay';
    modal.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0,0,0,0.5);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 10000;
    `;

    modal.innerHTML = `
        <div class="modal-content" style="
            background: white;
            padding: 2rem;
            border-radius: 12px;
            max-width: 400px;
            width: 90%;
            box-shadow: 0 4px 20px rgba(0,0,0,0.15);
        ">
            <h3 style="margin-top: 0;">Follow ${username}'s Parameters</h3>

            <div style="margin: 1.5rem 0;">
                <label style="
                    display: flex;
                    align-items: center;
                    padding: 0.75rem;
                    background: #f8f9fa;
                    border-radius: 8px;
                    cursor: pointer;
                ">
                    <input type="checkbox" id="followTrigger" style="
                        width: 20px;
                        height: 20px;
                        margin-right: 0.75rem;
                        cursor: pointer;
                    " checked>
                    <div>
                        <div style="font-weight: 500;">Get parameter alerts</div>
                        <div style="font-size: 0.875rem; color: #666; margin-top: 0.25rem;">
                            Receive notifications when their parameters trigger
                        </div>
                    </div>
                </label>
            </div>

            <div style="margin: 1.5rem 0;">
                <label style="display: block; margin-bottom: 0.5rem; font-weight: 500;">
                    Add a note (optional):
                </label>
                <textarea id="followNote" style="
                    width: 100%;
                    min-height: 80px;
                    padding: 0.75rem;
                    border: 1px solid #ddd;
                    border-radius: 8px;
                    font-size: 14px;
                    resize: vertical;
                " placeholder="Let them know why you're following..."></textarea>
            </div>

            <div style="display: flex; gap: 1rem; justify-content: flex-end;">
                <button class="btn-secondary" onclick="this.closest('.modal-overlay').remove()">
                    Cancel
                </button>
                <button class="btn-primary" onclick="confirmFollowWithParameters(${userId}, '${username}')">
                    Follow
                </button>
            </div>
        </div>
    `;

    document.body.appendChild(modal);

    // Close on background click
    modal.addEventListener('click', (e) => {
        if (e.target === modal) modal.remove();
    });
}

async function confirmFollowWithParameters(userId, username) {
    const trigger = document.getElementById('followTrigger')?.checked || false;
    const note = document.getElementById('followNote')?.value || '';

    try {
        const response = await fetch(`/api/follow/${userId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                note: note,
                trigger: trigger
            }),
            credentials: 'include'
        });

        if (response.ok) {
            document.querySelector('.modal-overlay')?.remove();

            // Show success notification
            if (window.showNotification) {
                const message = trigger
                    ? `Following ${username} with parameter alerts enabled`
                    : `Following ${username}`;
                window.showNotification(message, 'success');
            } else {
                window.showNotification(`Successfully followed ${username}`, 'success');
            }

            // Refresh following list if available
            if (typeof loadFollowing === 'function') {
                loadFollowing();
            }
        } else {
            throw new Error('Failed to follow user');
        }
    } catch (error) {
        console.error('Error following user:', error);
        window.showNotification('Failed to follow user', 'error');
    }
}



// Load indicators for visible month after a delay
function loadMonthIndicators() {
    // Only check for saved data after user action, not automatically
    const calendarDays = document.querySelectorAll('.calendar-day[data-date]');
    calendarDays.forEach(dayElement => {
        const dateStr = dayElement.getAttribute('data-date');
        if (dateStr) {
            // Check this specific date
            checkDateForData(dateStr, dayElement);
        }
    });
}

function selectDate(date) {
    currentDate = date;
    updateCalendar();

    // Refresh saved dates when changing dates
     if (typeof fetchAllParameterDates === 'function') {
        fetchAllParameterDates();
    }

    // Clear current ratings when changing date
    selectedRatings = {};
    document.querySelectorAll('.rating-button').forEach(btn => {
        btn.classList.remove('selected');
    });
    // Clear notes field when changing date
    const notesInput = document.getElementById('notesInput');
    if (notesInput) {
        notesInput.value = '';
    }
    // Don't auto-load - user must click Load button
}

function previousMonth() {
    currentDate.setMonth(currentDate.getMonth() - 1);
    updateCalendar();

    // Refresh dates for new month
    if (typeof fetchAllParameterDates === 'function') {
        fetchAllParameterDates();
    }
}

function nextMonth() {
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    // Calculate what the next month would be
    const nextMonthDate = new Date(
        currentDate.getFullYear(),
        currentDate.getMonth() + 1,
        1
    );
    nextMonthDate.setHours(0, 0, 0, 0);

    // Don't allow going past current month
    if (nextMonthDate > today) {
        showMessage('Cannot view future months', 'error', 2000);
        return;
    }

    currentDate.setMonth(currentDate.getMonth() + 1);
    updateCalendar();

    // Refresh dates for new month
    if (typeof fetchAllParameterDates === 'function') {
        fetchAllParameterDates();
    }
}

// Rating selection
function selectRating(categoryId, value) {
    selectedRatings[categoryId] = value;

    // Update UI
    const buttons = document.querySelectorAll(`#${categoryId}-buttons .rating-button`);
    buttons.forEach(btn => {
        if (parseInt(btn.dataset.value) === value) {
            btn.classList.add('selected');
        } else {
            btn.classList.remove('selected');
        }
    });
}

async function saveParameters() {
    const notes = document.getElementById('notesInput')?.value || '';
    const dateStr = formatDate(currentDate);

    // Save state before submitting
    saveParameterState(dateStr);

    // Validate that at least one rating is selected
    if (Object.keys(selectedRatings).length === 0) {
        window.showMessage(pt('error.saving') + ': Please select at least one rating', 'error');
        return;
    }

    const data = {
        date: dateStr,
        mood: selectedRatings.mood || null,
        energy: selectedRatings.energy || null,
        sleep_quality: selectedRatings.sleep_quality || null,
        physical_activity: selectedRatings.physical_activity || null,
        anxiety: selectedRatings.anxiety || null,
        mood_privacy: window.selectedPrivacy.mood || 'private',
        energy_privacy: window.selectedPrivacy.energy || 'private',
        sleep_quality_privacy: window.selectedPrivacy.sleep_quality || 'private',
        physical_activity_privacy: window.selectedPrivacy.physical_activity || 'private',
        anxiety_privacy: window.selectedPrivacy.anxiety || 'private',
        notes: notes
    };

    try {
        const response = await fetch('/api/parameters', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        });

        const result = await response.json();

        if (result.success) {
            window.showMessage(getRandomPositiveMessage(), 'success', 5000, true);

             // Show invite CTA after successful save
            showInviteCTA();

            // Add this date to our tracking set
            datesWithData.add(dateStr)
            localStorage.setItem('savedParameterDates', JSON.stringify([...datesWithData]));

            // Add green dot to current date
            const currentDayElement = document.querySelector(`.calendar-day[data-date="${dateStr}"]`);
            if (currentDayElement && !currentDayElement.querySelector('.data-indicator')) {
                currentDayElement.style.position = 'relative';
                const dot = document.createElement('span');
                dot.className = 'data-indicator';
                dot.textContent = '●';
                dot.style.cssText = 'color: #10b981; font-size: 8px; position: absolute; bottom: 2px; left: 50%; transform: translateX(-50%);';
                currentDayElement.appendChild(dot);
            }
        } else {
            window.showMessage(pt('error.saving') + ': ' + (result.message || 'Unknown error'), 'error');
        }
    } catch (error) {
        console.error('Save error:', error);
        window.showMessage(pt('error.saving') + ': ' + error.message, 'error');
    }
}





async function loadParameters(showMsg = true) {
    const dateStr = formatDate(currentDate);

    try {
        const response = await fetch(`/api/parameters?date=${dateStr}`);

        if (!response.ok) {
            // Try to restore from session storage if API fails
            const stored = sessionStorage.getItem(`parameters_${dateStr}`);
            if (stored) {
                const state = JSON.parse(stored);
                restoreParameterState(state);
                if (showMsg) {
                    window.showMessage('Restored from session cache', 'info');
                }
                return;
            }

            if (showMsg && response.status === 404) {
                window.showMessage(pt('parameters.no_saved'), 'info');
            }
            return;
        }

        const result = await response.json();

     if (result.success && result.data) {
            // Load ratings
            selectedRatings = result.data.parameters || {};

            // Update UI
            Object.keys(selectedRatings).forEach(categoryId => {
                selectRating(categoryId, selectedRatings[categoryId]);
            });

            // Load privacy settings for each parameter
          ['mood', 'energy', 'sleep_quality', 'physical_activity', 'anxiety'].forEach(param => {
                const privacyKey = `${param}_privacy`;
                // Check both direct property and nested in data - FIXED to load from correct location
                const privacyValue = result.data[privacyKey] || result.data[param + '_privacy'] || 'private';

                window.selectedPrivacy[param] = privacyValue;

                // Update the dropdown
                const selector = document.querySelector(`select[data-category="${param}"]`);
                if (selector) {
                    selector.value = privacyValue;
                }
            });

            // Load notes
            const notesInput = document.getElementById('notesInput');
            if (notesInput && result.data.notes) {
                notesInput.value = result.data.notes;
            }

            // Save to session storage for persistence
          const state = {
    ...selectedRatings,
    mood_privacy: result.data.mood_privacy || 'private',
    energy_privacy: result.data.energy_privacy || 'private',
    sleep_quality_privacy: result.data.sleep_quality_privacy || 'private',
    physical_activity_privacy: result.data.physical_activity_privacy || 'private',
    anxiety_privacy: result.data.anxiety_privacy || 'private',
    notes: result.data.notes || ''
};
sessionStorage.setItem(`parameters_${dateStr}`, JSON.stringify(state));

            // Add this date to our tracking set
            datesWithData.add(dateStr);
            localStorage.setItem('savedParameterDates', JSON.stringify([...datesWithData]));

            // Mark current date as having data
            const currentDayElement = document.querySelector(`.calendar-day[data-date="${dateStr}"]`);
            if (currentDayElement && !currentDayElement.querySelector('.data-indicator')) {
                currentDayElement.style.position = 'relative';
                const dot = document.createElement('span');
                dot.className = 'data-indicator';
                dot.textContent = '●';
                dot.style.cssText = 'color: #10b981; font-size: 8px; position: absolute; bottom: 2px; left: 50%; transform: translateX(-50%);';
                currentDayElement.appendChild(dot);
            }

            if (showMsg) {
                window.showMessage(pt('parameters.loaded') + ' ' + dateStr, 'success');
            }
        }
    } catch (error) {
        console.error('Load error:', error);

        // Try to restore from session storage on error
        const stored = sessionStorage.getItem(`parameters_${dateStr}`);
        if (stored) {
            const state = JSON.parse(stored);
            restoreParameterState(state);
            if (showMsg) {
                window.showMessage('Restored from session cache', 'info');
            }
            return;
        }

        if (showMsg) {
            window.showMessage(pt('error.loading') + ': ' + error.message, 'error');
        }
    }
}






// Clear parameters
function clearParameters() {
    selectedRatings = {};
    document.querySelectorAll('.rating-button').forEach(btn => {
        btn.classList.remove('selected');
    });

    const notesInput = document.getElementById('notesInput');
    if (notesInput) {
        notesInput.value = '';
    }

    window.showMessage(pt('parameters.cleared'), 'info');
}

// Navigate to main menu - FIXED
function goToHome() {
    // Navigate to home view in the same page
    if (typeof showView === 'function') {
        showView('home');
    } else {
        window.location.href = '/#home';
    }
}


// Apply emojis to privacy dropdowns
function applyEmojisToPrivacySelectors() {
    document.querySelectorAll('.privacy-select').forEach(selector => {
        const currentValue = selector.value;

        selector.querySelectorAll('option').forEach(option => {
            const value = option.value;
            let text = option.textContent;

            // Remove any existing emojis
            text = text.replace(/[\u{1F000}-\u{1FAFF}\u{2600}-\u{27BF}\u{200D}\u{FE0F}\u{FE0E}]/ug, '').trim();

            // Add single emoji
            const emoji = CIRCLE_EMOJIS[value] || '';
            option.textContent = emoji ? emoji + ' ' + text : text;
        });

        selector.value = currentValue;
    });
}


// Update translations dynamically
function updateTranslations() {
    if (!window.i18n) return;

    // Re-add translations in case language changed
    addParameterTranslations();

    // Update all translatable elements
    document.querySelectorAll('[data-i18n]').forEach(element => {
        const key = element.getAttribute('data-i18n');
        if (key) {
            // For option elements, preserve emoji prefix
            if (element.tagName === 'OPTION') {
                const currentText = element.textContent;
                const emojiMatch = currentText.match(/^([\u{1F300}-\u{1F9FF}]|[\u{2600}-\u{26FF}]|[\u{2700}-\u{27BF}])\s*/u);
                const emoji = emojiMatch ? emojiMatch[0] : '';
                element.textContent = emoji + pt(key);
            } else {
                element.textContent = pt(key);
            }
        }
    });

    // Update placeholders
    document.querySelectorAll('[data-i18n-placeholder]').forEach(element => {
        const key = element.getAttribute('data-i18n-placeholder');
        if (key) {
            element.placeholder = pt(key);
        }
    });

    // Update calendar to reflect new language
    updateCalendar();
}

// Get random positive message
function getRandomPositiveMessage() {
    const messages = {
        'en': [
            "Amazing work! You're tracking your wellness journey beautifully! 💪",
            "Fantastic job! Your dedication to self-awareness is inspiring! ⭐",
            "Wonderful! Every parameter logged is a step towards understanding yourself better! 🌈",
            "Brilliant! You're building valuable insights about your wellbeing! 🎯",
            "Outstanding! Your consistency in tracking is your superpower! 🦸"
        ],
        'he': [
            "עבודה מדהימה! אתה עוקב אחר מסע הבריאות שלך בצורה יפהפייה! 💪",
            "עבודה פנטסטית! המסירות שלך למודעות עצמית מעוררת השראה! ⭐",
            "נפלא! כל פרמטר שנרשם הוא צעד להבנה טובה יותר של עצמך! 🌈",
            "מבריק! אתה בונה תובנות חשובות על הרווחה שלך! 🎯",
            "יוצא מן הכלל! העקביות שלך במעקב היא כוח העל שלך! 🦸"
        ],
        'ar': [
            "عمل رائع! أنت تتابع رحلتك الصحية بشكل جميل! 💪",
            "عمل رائع! إخلاصك للوعي الذاتي ملهم! ⭐",
            "رائع! كل معامل مسجل هو خطوة نحو فهم نفسك بشكل أفضل! 🌈",
            "ممتاز! أنت تبني رؤى قيمة حول رفاهيتك! 🎯",
            "متميز! ثباتك في التتبع هو قوتك الخارقة! 🦸"
        ],
        'ru': [
            "Потрясающая работа! Вы прекрасно отслеживаете свой путь к здоровью! 💪",
            "Фантастическая работа! Ваша преданность самосознанию вдохновляет! ⭐",
            "Замечательно! Каждый записанный параметр - это шаг к лучшему пониманию себя! 🌈",
            "Блестяще! Вы создаете ценные инсайты о своем благополучии! 🎯",
            "Выдающийся результат! Ваша последовательность в отслеживании - это ваша суперсила! 🦸"
        ]
    };

    const lang = window.i18n?.getCurrentLanguage?.() || 'en';
    const langMessages = messages[lang] || messages['en'];
    return langMessages[Math.floor(Math.random() * langMessages.length)];
}



function showInviteCTA() {
    // Check if CTA already exists to avoid duplicates
    if (document.getElementById('inviteCTA')) {
        return;
    }

    const messageContainer = document.getElementById('messageContainer');
    const calendarSection = document.querySelector('.date-section');

    if (!messageContainer || !calendarSection) {
        console.warn('Cannot show invite CTA - containers not found');
        return;
    }

    // Create CTA div
    const ctaDiv = document.createElement('div');
    ctaDiv.id = 'inviteCTA';
    ctaDiv.className = 'invite-cta';

    // Get current user's username for shareable link
    fetch('/api/auth/session')
        .then(response => response.json())
        .then(data => {
            const username = data.user?.username || 'user';
            const inviteLink = `${window.location.origin}/invite/${username}`;

            ctaDiv.innerHTML = `
                <div class="cta-content">
                    <h3 data-i18n="invite.cta_title">🎉 Great job tracking your wellness!</h3>
                    <p data-i18n="invite.cta_subtitle">Share your journey with others:</p>

                    <div class="cta-actions">
                        <button class="cta-button primary" onclick="copyInviteLink('${inviteLink}')">
                            <span data-i18n="invite.copy_link">📋 Copy Your Invite Link</span>
                        </button>
                        <button class="cta-button secondary" onclick="showInviteTab()">
                            <span data-i18n="invite.invite_friends">👥 Invite Friends</span>
                        </button>
                        <button class="cta-button secondary" onclick="findPeopleToFollow()">
                            <span data-i18n="invite.find_people">🔍 Find People to Follow</span>
                        </button>
                    </div>

                    <button class="cta-close" onclick="closeInviteCTA()">✕</button>
                </div>
            `;

            // Insert before calendar
            calendarSection.parentNode.insertBefore(ctaDiv, calendarSection);

            // Apply translations if i18n is available
            if (window.i18n && window.i18n.applyLanguage) {
                window.i18n.applyLanguage();
            }

            // Auto-hide after 15 seconds
            setTimeout(() => {
                closeInviteCTA();
            }, 15000);
        })
        .catch(error => {
            console.error('Error fetching user info for CTA:', error);
        });
}

function copyInviteLink(link) {
    navigator.clipboard.writeText(link).then(() => {
        window.showMessage(pt('invite.link_copied') || 'Invite link copied to clipboard! 📋', 'success', 3000);
    }).catch(err => {
        console.error('Failed to copy:', err);
        // Fallback: show the link
        prompt('Copy this link:', link);
    });
}

function closeInviteCTA() {
    const cta = document.getElementById('inviteCTA');
    if (cta) {
        cta.style.animation = 'fadeOut 0.3s ease-out';
        setTimeout(() => cta.remove(), 300);
    }
}

function showInviteTab() {
    // Redirect to main page with invite view selected
    if (typeof showView === 'function') {
        showView('invite');
    } else {
        window.location.href = '/?view=invite';
    }
}

function findPeopleToFollow() {
    // Redirect to main page with following view
    if (typeof showView === 'function') {
        showView('following');
    } else {
        window.location.href = '/?view=following';
    }
}


// Listen for language changes and reapply emojis
window.addEventListener('languageChanged', () => {
    setTimeout(applyEmojisToPrivacySelectors, 50);
});

// Initialize on DOM ready (with safety checks)
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        if (document.getElementById('parametersContainer') && !window.parametersInitialized) {
            window.parametersInitialized = true;
            initializeParameters();
        }
    });
} else {
    if (document.getElementById('parametersContainer') && !window.parametersInitialized) {
        window.parametersInitialized = true;
        initializeParameters();
    }
}

// Export functions for global access
window.initializeParameters = initializeParameters;
window.updateTranslations = updateTranslations;
window.previousMonth = previousMonth;
window.nextMonth = nextMonth;
window.saveParameters = saveParameters;
window.loadParameters = loadParameters;
window.clearParameters = clearParameters;
window.selectRating = selectRating;
window.goToHome = goToHome;
window.updatePrivacy = updatePrivacy;
window.fetchAllParameterDates = fetchAllParameterDates;
window.showInviteCTA = showInviteCTA;
window.copyInviteLink = copyInviteLink;
window.closeInviteCTA = closeInviteCTA;
window.showInviteTab = showInviteTab;
window.findPeopleToFollow = findPeopleToFollow;
window.applyEmojisToPrivacySelectors = applyEmojisToPrivacySelectors;

console.log('Parameters-social.js loaded - FIXED VERSION with calendar display and no auto-loading');
// ===================
// PARAMETER TRIGGERS MANAGEMENT SYSTEM
// ===================

// State for triggers
let currentTriggers = {};
let parameterAlerts = [];

// View user parameters function
window.viewUserParameters = function(userId, username) {
    // Create modal to display user's parameters
    const modalHtml = `
        <div id="userParametersModal" class="modal" style="display: block; position: fixed; z-index: 10000; left: 0; top: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5);">
            <div class="modal-content" style="background: white; margin: 5% auto; padding: 30px; width: 90%; max-width: 800px; border-radius: 20px; max-height: 80vh; overflow-y: auto;">
                <span class="close" onclick="closeUserParametersModal()" style="float: right; font-size: 28px; cursor: pointer;">&times;</span>
                <h2 data-i18n="parameters.view_user">${username}'s Parameters</h2>
                <div id="userParametersContent">Loading...</div>
            </div>
        </div>
    `;

    document.body.insertAdjacentHTML('beforeend', modalHtml);

    // Load user's parameters
    fetch(`/api/parameters/user/${userId}`)
        .then(response => response.json())
        .then(data => {
            displayUserParameters(data, userId, username);
            // Add trigger controls after loading parameters
            setTimeout(() => {
                addTriggerControls(userId, username);
            }, 500);
        })
        .catch(error => {
            console.error('Error loading user parameters:', error);
            document.getElementById('userParametersContent').innerHTML =
                '<p style="color: red;">Error loading parameters</p>';
        });
}

function displayUserParameters(data, userId, username) {
    const content = document.getElementById('userParametersContent');
    if (!content) return;

    if (!data.parameters || data.parameters.length === 0) {
        content.innerHTML = '<p>No parameters available for this user.</p>';
        return;
    }

    let html = '<div class="parameters-history" style="margin-top: 20px;">';

    // Group parameters by date
    const paramsByDate = {};
    data.parameters.forEach(param => {
        const date = new Date(param.date).toLocaleDateString();
        if (!paramsByDate[date]) {
            paramsByDate[date] = [];
        }
        paramsByDate[date].push(param);
    });

    // Display parameters organized by date
    Object.entries(paramsByDate).forEach(([date, params]) => {
        html += `
            <div style="margin-bottom: 20px; padding: 15px; background: #f9f9f9; border-radius: 10px;">
                <h4 style="color: #2d3436; margin-bottom: 10px;">${date}</h4>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px;">
        `;

        params.forEach(param => {
            const icon = getParameterIcon(param.parameter_name);
            const value = param.value || 'N/A';
            const color = getValueColor(param.parameter_name, value);

            html += `
                <div style="padding: 10px; background: white; border-radius: 8px; border-left: 3px solid ${color};">
                    <div style="font-size: 12px; color: #666;">${icon} ${param.parameter_name}</div>
                    <div style="font-size: 18px; font-weight: bold; color: ${color};">${value}/4</div>
                </div>
            `;
        });

        html += '</div></div>';
    });

    html += '</div>';
    content.innerHTML = html;

    // Add trigger settings if viewing another user's parameters that we follow
    const currentUserId = parseInt(localStorage.getItem('userId') || sessionStorage.getItem('userId'));
    if (userId && userId !== currentUserId) {
        // Check if we follow this user
        fetch('/api/following')
            .then(response => response.json())
            .then(followingData => {
                const isFollowing = followingData.following?.some(u => u.id === userId);
                if (isFollowing) {
                    addTriggerSettings(content, userId, username);
                }
            })
            .catch(error => console.error('Error checking follow status:', error));
    }
}

// Add function to create trigger settings UI
function addTriggerSettings(container, userId, username) {
    const triggerContainer = document.createElement('div');
    triggerContainer.className = 'trigger-settings-container';
    triggerContainer.style.cssText = `
        background: #f8f9fa;
        border: 1px solid #dee2e6;
        border-radius: 8px;
        padding: 20px;
        margin: 20px 0;
    `;

    const title = document.createElement('h3');
    title.textContent = 'Alert Triggers';
    title.style.cssText = 'margin: 0 0 15px 0; color: #495057;';
    triggerContainer.appendChild(title);

    const description = document.createElement('p');
    description.textContent = `Set up alerts for ${username}'s parameters. You'll be notified when values are concerning for 2 consecutive days.`;
    description.style.cssText = 'color: #6c757d; margin-bottom: 20px; font-size: 14px;';
    triggerContainer.appendChild(description);

    // Parameter trigger settings
    const parameters = [
        { name: 'mood', label: 'Mood', icon: '😊',
          thresholds: { yellow: [2,2], orange: [[1,2],[2,1]], red: [1,1] } },
        { name: 'energy', label: 'Energy', icon: '⚡',
          thresholds: { yellow: [2,2], orange: [[1,2],[2,1]], red: [1,1] } },
        { name: 'sleep_quality', label: 'Sleep Quality', icon: '😴',
          thresholds: { yellow: [2,2], orange: [[1,2],[2,1]], red: [1,1] } },
        { name: 'physical_activity', label: 'Physical Activity', icon: '🏃',
          thresholds: { yellow: [2,2], orange: [[1,2],[2,1]], red: [1,1] } },
        { name: 'anxiety', label: 'Anxiety', icon: '😰',
          thresholds: { yellow: [3,3], orange: [[3,4],[4,3]], red: [4,4] } }
    ];

    // Load existing triggers
    fetch(`/api/triggers/${userId}`)
        .then(response => response.json())
        .then(triggers => {
            const triggersForm = document.createElement('div');

            parameters.forEach(param => {
                const paramRow = document.createElement('div');
                paramRow.style.cssText = `
                    display: flex;
                    align-items: center;
                    padding: 10px;
                    border-bottom: 1px solid #e9ecef;
                `;

                const checkbox = document.createElement('input');
                checkbox.type = 'checkbox';
                checkbox.id = `trigger-${param.name}`;
                checkbox.checked = triggers[param.name + '_alert'] || false;
                checkbox.style.cssText = 'margin-right: 10px;';

                const label = document.createElement('label');
                label.htmlFor = `trigger-${param.name}`;
                label.style.cssText = `
                    flex: 1;
                    cursor: pointer;
                    display: flex;
                    align-items: center;
                `;
                label.innerHTML = `
                    <span style="font-size: 20px; margin-right: 10px;">${param.icon}</span>
                    <span style="font-weight: 500;">${param.label}</span>
                `;

                const thresholdInfo = document.createElement('div');
                thresholdInfo.style.cssText = `
                    font-size: 12px;
                    color: #6c757d;
                    margin-left: auto;
                `;

                if (param.name === 'anxiety') {
                    thresholdInfo.innerHTML = `
                        <span style="color: #ffc107;">●</span> 3 for 2 days |
                        <span style="color: #ff9800;">●</span> 3/4 or 4/3 |
                        <span style="color: #f44336;">●</span> 4 for 2 days
                    `;
                } else {
                    thresholdInfo.innerHTML = `
                        <span style="color: #ffc107;">●</span> 2 for 2 days |
                        <span style="color: #ff9800;">●</span> 1/2 or 2/1 |
                        <span style="color: #f44336;">●</span> 1 for 2 days
                    `;
                }

                paramRow.appendChild(checkbox);
                paramRow.appendChild(label);
                paramRow.appendChild(thresholdInfo);
                triggersForm.appendChild(paramRow);
            });

            // Save button
            const saveButton = document.createElement('button');
            saveButton.textContent = 'Save Trigger Settings';
            saveButton.className = 'btn btn-primary';
            saveButton.style.cssText = `
                margin-top: 20px;
                padding: 10px 20px;
                background: #6B46C1;
                color: white;
                border: none;
                border-radius: 5px;
                cursor: pointer;
                font-weight: 500;
            `;

            saveButton.onclick = () => {
                const triggerSettings = {};
                parameters.forEach(param => {
                    const checkbox = document.getElementById(`trigger-${param.name}`);
                    triggerSettings[param.name + '_alert'] = checkbox.checked;
                });

                fetch(`/api/triggers/${userId}`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(triggerSettings)
                })
                .then(response => response.json())
                .then(result => {
                    if (result.success) {
                        window.showNotification('Trigger settings saved successfully!', 'success');
                    } else {
                        window.showNotification('Error saving trigger settings', 'error');
                    }
                })
                .catch(error => {
                    console.error('Error saving triggers:', error);
                    window.showNotification('Error saving trigger settings', 'error');
                });
            };

            triggersForm.appendChild(saveButton);
            triggerContainer.appendChild(triggersForm);
        })
        .catch(error => {
            console.error('Error loading triggers:', error);
            triggerContainer.innerHTML += '<p style="color: red;">Error loading trigger settings</p>';
        });

    // Insert after the title but before the parameters
    const h2Title = container.querySelector('h2');
    if (h2Title && h2Title.nextSibling) {
        container.insertBefore(triggerContainer, h2Title.nextSibling);
    } else {
        container.appendChild(triggerContainer);
    }
}
function getParameterIcon(paramName) {
    const icons = {
        'mood': '😊',
        'energy': '⚡',
        'sleep_quality': '😴',
        'physical_activity': '🏃',
        'anxiety': '😰'
    };
    return icons[paramName] || '📊';
}

function getValueColor(paramName, value) {
    const val = parseInt(value);
    if (paramName === 'anxiety') {
        // For anxiety, high is bad
        if (val >= 3) return '#ff4444';
        if (val === 2) return '#ff8800';
        return '#44ff44';
    } else {
        // For others, low is bad
        if (val <= 2) return '#ff4444';
        if (val === 3) return '#ff8800';
        return '#44ff44';
    }
}

window.closeUserParametersModal = function() {
    const modal = document.getElementById('userParametersModal');
    if (modal) modal.remove();
}

// Add trigger controls to the modal
function addTriggerControls(userId, username) {
    const triggerHtml = `
        <div class="trigger-controls" style="background: #f9f9f9; padding: 15px; border-radius: 8px; margin: 15px 0;">
            <h4 data-i18n="triggers.set">Set Alert Triggers</h4>
            <p style="font-size: 14px; color: #666;">
                Get alerts when ${username}'s parameters are concerning
            </p>

            <div class="trigger-options" style="margin: 15px 0;">
                <label style="display: block; margin: 8px 0;">
                    <input type="checkbox" id="moodTrigger" onchange="updateTrigger('mood')">
                    <span data-i18n="triggers.mood">Mood Alert</span>
                    <small style="color: #999;"> (Low: 1-2)</small>
                </label>

                <label style="display: block; margin: 8px 0;">
                    <input type="checkbox" id="energyTrigger" onchange="updateTrigger('energy')">
                    <span data-i18n="triggers.energy">Energy Alert</span>
                    <small style="color: #999;"> (Low: 1-2)</small>
                </label>

                <label style="display: block; margin: 8px 0;">
                    <input type="checkbox" id="sleepTrigger" onchange="updateTrigger('sleep')">
                    <span data-i18n="triggers.sleep">Sleep Quality Alert</span>
                    <small style="color: #999;"> (Low: 1-2)</small>
                </label>

                <label style="display: block; margin: 8px 0;">
                    <input type="checkbox" id="physicalTrigger" onchange="updateTrigger('physical')">
                    <span data-i18n="triggers.physical">Physical Activity Alert</span>
                    <small style="color: #999;"> (Low: 1-2)</small>
                </label>

                <label style="display: block; margin: 8px 0;">
                    <input type="checkbox" id="anxietyTrigger" onchange="updateTrigger('anxiety')">
                    <span data-i18n="triggers.anxiety">Anxiety Alert</span>
                    <small style="color: #999;"> (High: 3-4)</small>
                </label>
            </div>

            <button onclick="saveTriggers(${userId})" class="btn btn-primary" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; padding: 10px 20px; border-radius: 10px; cursor: pointer;">
                Save Trigger Settings
            </button>
        </div>
    `;

    // Find where to insert triggers in the modal
    const content = document.getElementById('userParametersContent');
    if (content) {
        // Insert at the top of the content
        content.insertAdjacentHTML('afterbegin', triggerHtml);
    }

    loadTriggers(userId);
}

async function loadTriggers(userId) {
    try {
        const response = await fetch(`/api/parameters/triggers/${userId}`);
        const data = await response.json();

        currentTriggers = data;

        if (document.getElementById('moodTrigger')) {
            document.getElementById('moodTrigger').checked = data.mood_alert || false;
            document.getElementById('energyTrigger').checked = data.energy_alert || false;
            document.getElementById('sleepTrigger').checked = data.sleep_alert || false;
            document.getElementById('physicalTrigger').checked = data.physical_alert || false;
            document.getElementById('anxietyTrigger').checked = data.anxiety_alert || false;
        }

    } catch (error) {
        console.error('Failed to load triggers:', error);
    }
}

window.updateTrigger = function(param) {
    const checkbox = document.getElementById(param + 'Trigger');
    if (checkbox) {
        currentTriggers[param + '_alert'] = checkbox.checked;
    }
}

window.saveTriggers = async function(userId) {
    try {
        const response = await fetch(`/api/parameters/triggers/${userId}`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                mood_alert: document.getElementById('moodTrigger')?.checked || false,
                energy_alert: document.getElementById('energyTrigger')?.checked || false,
                sleep_alert: document.getElementById('sleepTrigger')?.checked || false,
                physical_alert: document.getElementById('physicalTrigger')?.checked || false,
                anxiety_alert: document.getElementById('anxietyTrigger')?.checked || false
            })
        });

        const data = await response.json();
        if (data.success) {
            window.showMessage('Trigger settings saved', 'success');
        } else {
            window.showMessage(data.error || 'Failed to save triggers', 'error');
        }

    } catch (error) {
        console.error('Failed to save triggers:', error);
        window.showMessage('Failed to save triggers', 'error');
    }
}

async function checkParameterAlerts() {
    try {
        console.log('[PJ812] checkParameterAlerts called - checking for trigger patterns');
        
        // PJ812 FIX: Check if user is logged in first to avoid 401 errors
        const sessionResponse = await fetch('/api/auth/session');
        if (!sessionResponse.ok || sessionResponse.status === 401) {
            console.log('[PJ812] User not logged in, skipping trigger check');
            return;
        }
        
        const sessionData = await sessionResponse.json();
        if (!sessionData.authenticated) {
            console.log('[PJ812] Session not authenticated, skipping trigger check');
            return;
        }
        
        console.log('[PJ812] User is authenticated, checking triggers...');
        const response = await fetch('/api/parameters/check-triggers');
        
        if (!response.ok) {
            console.log('[PJ812] check-triggers returned status:', response.status);
            return;
        }
        
        const data = await response.json();

        console.log('[PJ812] check-triggers response:', data);
        
        if (data.alerts && data.alerts.length > 0) {
            console.log(`[PJ812] Found ${data.alerts.length} trigger patterns`);
            console.log(`[PJ812] Alerts created: ${data.alerts_created || 0}, Duplicates skipped: ${data.alerts_skipped_duplicate || 0}`);
            
            // PJ812: Only show visual feedback if configured
            // Database alerts are now created by the backend and will appear in /api/alerts
            if (TRIGGER_ALERT_DISPLAY_MODE === 'overlay') {
                displayParameterAlerts(data.alerts);
            }
            
            // PJ812: Refresh the alerts list to show any newly created alerts
            if (data.alerts_created > 0 && typeof loadAlerts === 'function') {
                console.log('[PJ812] New alerts created, refreshing alerts list...');
                setTimeout(() => {
                    loadAlerts().catch(err => console.error('[PJ812] Error refreshing alerts:', err));
                }, 500);
            }
        } else {
            console.log('[PJ812] No trigger patterns found');
        }

    } catch (error) {
        console.error('[PJ812] Failed to check alerts:', error);
    }
}

function displayParameterAlerts(alerts) {
    // PJ810: Check display mode configuration
    if (TRIGGER_ALERT_DISPLAY_MODE === 'disabled') {
        console.log('[PJ810] Trigger alert display is disabled');
        return;
    }
    
    // PJ810: Standard mode - add to Alerts section like other notifications
    if (TRIGGER_ALERT_DISPLAY_MODE === 'standard') {
        displayParameterAlertsStandard(alerts);
        return;
    }
    
    // Original overlay mode - yellow floating alerts
    let alertContainer = document.getElementById('parameterAlerts');
    if (!alertContainer) {
        alertContainer = document.createElement('div');
        alertContainer.id = 'parameterAlerts';
        alertContainer.style.cssText = 'position: fixed; top: 80px; right: 20px; z-index: 1000; max-width: 350px;';
        document.body.appendChild(alertContainer);
    }

    alerts.forEach(alert => {
        const alertDiv = document.createElement('div');
        // PJ806 FIX: Handle both new schema (with level) and old schema (without level)
        const alertLevel = alert.level || 'warning';  // Default to warning if no level
        const bgColor = alertLevel === 'critical' ? '#ff4444' :
                        alertLevel === 'high' ? '#ff8800' : '#ffcc00';

        alertDiv.style.cssText = `
            background: ${bgColor};
            color: white;
            padding: 15px;
            margin: 10px 0;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.2);
            animation: slideIn 0.3s ease;
        `;

        // PJ806 FIX: Handle both schema formats for dates/values display
        let datesDisplay = '';
        let valuesDisplay = '';
        if (alert.dates && alert.dates.length >= 2) {
            datesDisplay = `Dates: ${alert.dates[0]} and ${alert.dates[alert.dates.length - 1]}`;
        } else if (alert.end_date) {
            // Old schema format
            datesDisplay = `End date: ${alert.end_date}`;
        }
        if (alert.values && alert.values.length > 0) {
            valuesDisplay = `Values: ${alert.values.join(', ')}`;
        } else if (alert.condition_text) {
            // Old schema format
            valuesDisplay = `Condition: ${alert.condition_text}`;
        }

        alertDiv.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <strong>${alertLevel.toUpperCase()} ALERT</strong>
                <button onclick="this.parentElement.parentElement.remove()"
                        style="background: none; border: none; color: white; cursor: pointer; font-size: 20px;">✕</button>
            </div>
            <div style="margin-top: 8px;">
                <strong>${alert.user || 'Unknown'}</strong> - ${alert.parameter || 'parameter'}
            </div>
            <div style="font-size: 12px; margin-top: 5px;">
                ${datesDisplay}<br>
                ${valuesDisplay}
            </div>
        `;

        document.getElementById('parameterAlerts').appendChild(alertDiv);

        // Auto-remove after 30 seconds
        setTimeout(() => alertDiv.remove(), 30000);
    });
}

// PJ812: Updated function - no longer adds ephemeral DOM alerts
// Alerts are now created in the database by the backend and will be
// loaded by loadAlerts() which fetches from /api/alerts
function displayParameterAlertsStandard(alerts) {
    console.log('[PJ812] displayParameterAlertsStandard called with', alerts.length, 'patterns');
    console.log('[PJ812] These alerts are now persisted in the database');
    console.log('[PJ812] They will appear in the Alerts section via loadAlerts()');
    
    // PJ812: No longer adding ephemeral DOM alerts that would vanish
    // The backend now creates real database alerts that persist
    // loadAlerts() will fetch and display them properly
    
    // If you want to show a brief notification that new alerts were found:
    if (alerts.length > 0 && typeof showNotification === 'function') {
        // Only show if this is genuinely new (not already showing in alerts)
        const alertsContainer = document.getElementById('alertsList');
        if (alertsContainer) {
            const existingAlertCount = alertsContainer.querySelectorAll('.alert-item').length;
            if (existingAlertCount === 0) {
                console.log('[PJ812] No existing alerts in DOM, loadAlerts will populate');
            }
        }
    }
}

// Add CSS animation for alerts
if (!document.getElementById('parameterAlertsStyles')) {
    const style = document.createElement('style');
    style.id = 'parameterAlertsStyles';
    style.textContent = `
        @keyframes slideIn {
            from {
                transform: translateX(100%);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
    `;
    document.head.appendChild(style);
}

// PJ812 FIX: The /api/parameters/check-triggers endpoint now creates database alerts.
// Alerts are created with 24-hour duplicate detection per (watcher, user, parameter) combo.
// This polling triggers alert creation and emails for users who have email_on_alert enabled.
// loadAlerts() fetches the persisted alerts from /api/alerts.
// PJ812: Increased interval to 5 minutes (300000ms) to prevent excessive API calls.
// PJ812: Now checks if user is logged in before making API call to avoid 401 errors.
setInterval(checkParameterAlerts, 300000);  // Changed from 60000 (1 min) to 300000 (5 min)

// Check on page load (but only if logged in)
document.addEventListener('DOMContentLoaded', function() {
    console.log('[PJ812] parameters-social.js loaded - will check triggers in 2 seconds');
    setTimeout(checkParameterAlerts, 2000);
});

// Export trigger functions
window.viewUserParameters = viewUserParameters;
window.closeUserParametersModal = closeUserParametersModal;
window.checkParameterAlerts = checkParameterAlerts;

console.log('[PJ811] Parameters-social.js v1801 P101 loaded - trigger alerts now persist in database');
