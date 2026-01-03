// feed-updates.js - Circle display name mappings
// Version P315 - Reverted to P204 approach: NO emojis in HTML, add dynamically
// P204 logic works because i18n runs first, then we add emojis after

// Emoji map - NO trailing spaces
const CIRCLE_EMOJIS = {
    'private': '🔒',
    'public': '🌍',
    'general': '🌍',
    'class_b': '👥',
    'close_friends': '👥',
    'class_a': '👨‍👩‍👧‍👦',
    'family': '👨‍👩‍👧‍👦'
};

function getDisplayName(internalName) {
    return internalName;
}

function getInternalName(displayName) {
    const reverseMap = {
        'Public': 'public',
        'Close Friends': 'class_b',
        'Family': 'class_a',
        'Private': 'private'
    };
    return reverseMap[displayName] || displayName;
}

// Remove all emojis from text
function removeAllEmojis(text) {
    if (!text) return '';
    return text
        .replace(/[\u{1F000}-\u{1FAFF}\u{2600}-\u{27BF}\u{200D}\u{FE0F}\u{FE0E}]/ug, '')
        .replace(/\s+/g, ' ')
        .trim();
}

// Update all dropdowns and displays
function updateCircleDisplays() {
    console.log('[P315] Updating circle displays...');

    // Fix circles page headers - ONLY if they exist
    const circleHeaders = document.querySelectorAll('.circle-header h2, .circle-name');
    if (circleHeaders.length > 0) {
        circleHeaders.forEach(header => {
            const currentText = removeAllEmojis(header.textContent);

            // Get the internal value from the header's data attribute or text
            let internalValue = header.getAttribute('data-circle-type');
            if (!internalValue) {
                // Fallback: guess from text
                if (currentText.includes('General') || currentText.includes('Public')) {
                    internalValue = 'public';
                } else if (currentText.includes('Close Friends') || currentText.includes('Class B')) {
                    internalValue = 'class_b';
                } else if (currentText.includes('Family') || currentText.includes('Class A')) {
                    internalValue = 'class_a';
                }
            }

            // Let i18n handle the translation, we just add emoji
            if (internalValue && window.i18n && window.i18n.translate) {
                const i18nKey = `privacy.${internalValue}`;
                const translatedText = window.i18n.translate(i18nKey);
                const emoji = CIRCLE_EMOJIS[internalValue] || '';
                header.textContent = emoji + (emoji ? ' ' : '') + removeAllEmojis(translatedText);
            }
        });
    }

    // Update all circle selectors in feed AND parameters page
    document.querySelectorAll('.circle-selector, .visibility-selector, select[name="circle"], .privacy-select, .visibility-select, #circlesPrivacySelect').forEach(selector => {
        // Store current value
        const currentValue = selector.value;

        // Update all options
        selector.querySelectorAll('option').forEach(option => {
            const value = option.value;
            const i18nKey = option.getAttribute('data-i18n');
            const currentText = option.textContent;

            // Check if this option has duplicate emojis
            const emojiCount = (currentText.match(/[\u{1F000}-\u{1FAFF}\u{2600}-\u{27BF}]/ug) || []).length;

            // ALWAYS use i18n translation if available
            if (i18nKey && window.i18n && window.i18n.translate) {
                const translation = window.i18n.translate(i18nKey);
                const cleanTranslation = removeAllEmojis(translation);
                const emoji = CIRCLE_EMOJIS[value] || '';

                // Set text with single emoji
                option.textContent = emoji ? emoji + ' ' + cleanTranslation : cleanTranslation;
            } else if (emojiCount > 1) {
                // Fix duplicate emojis even without i18n
                const cleanText = removeAllEmojis(currentText);
                const emoji = CIRCLE_EMOJIS[value] || '';
                option.textContent = emoji ? emoji + ' ' + cleanText : cleanText;
            } else if (emojiCount === 0) {
                // Add emoji if missing
                const emoji = CIRCLE_EMOJIS[value] || '';
                option.textContent = emoji ? emoji + ' ' + currentText.trim() : currentText.trim();
            }
            // If emojiCount === 1, leave it alone (already correct)
        });

        // Restore the selection
        selector.value = currentValue;
    });

    console.log('[P315] ✅ Circle displays updated');
}

// Export functions for use in other files
if (typeof window !== 'undefined') {
    window.getDisplayName = getDisplayName;
    window.getInternalName = getInternalName;
    window.updateCircleDisplays = updateCircleDisplays;
    window.removeAllEmojis = removeAllEmojis;
}

// SIMPLIFIED initialization - only run once when DOM is ready
let initialized = false;

function initialize() {
    if (initialized) return;
    initialized = true;
    console.log('[P315] Feed updates initializing...');
    // Single delayed call to let i18n initialize first
    setTimeout(updateCircleDisplays, 200);
}

document.addEventListener('DOMContentLoaded', initialize);

// Update when language changes
window.addEventListener('languageChanged', () => {
    console.log('[P315] Language changed, updating circle displays');
    updateCircleDisplays();
});

// Try to run immediately if DOM already ready
if (document.readyState === 'complete' || document.readyState === 'interactive') {
    initialize();
}

console.log('[P315] ✅ feed-updates.js loaded');
