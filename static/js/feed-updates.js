// feed-updates.js - Circle display name mappings
// Version P308 - Fixed double emoji issue

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

// Remove all emojis from text - improved regex for ZWJ sequences
function removeAllEmojis(text) {
    if (!text) return '';
    return text
        // Remove emoji sequences including ZWJ combinations
        .replace(/[\u{1F300}-\u{1F9FF}\u{2600}-\u{27BF}\u{200D}\u{FE0F}\u{FE0E}\u{1F1E0}-\u{1F1FF}]/ug, '')
        .replace(/\s+/g, ' ')
        .trim();
}

// Check if text starts with any known emoji
function startsWithEmoji(text) {
    if (!text) return false;
    const emojiPattern = /^[\u{1F300}-\u{1F9FF}\u{2600}-\u{27BF}]/u;
    return emojiPattern.test(text.trim());
}

// Update all dropdowns and displays
function updateCircleDisplays() {
    console.log('[P308] Updating circle displays...');

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
                const cleanTranslation = removeAllEmojis(translatedText);
                const emoji = CIRCLE_EMOJIS[internalValue] || '';
                header.textContent = emoji + (emoji ? ' ' : '') + cleanTranslation;
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

            // P308 FIX: Get the expected emoji for this value
            const expectedEmoji = CIRCLE_EMOJIS[value] || '';
            
            // P308 FIX: Check if text already starts with the correct emoji
            const alreadyHasCorrectEmoji = currentText.trim().startsWith(expectedEmoji) && expectedEmoji !== '';
            
            if (alreadyHasCorrectEmoji) {
                // Already correct - clean up any trailing emojis but keep the leading one
                const textAfterEmoji = currentText.trim().substring(expectedEmoji.length).trim();
                const cleanText = removeAllEmojis(textAfterEmoji);
                if (cleanText !== textAfterEmoji) {
                    // There were extra emojis - fix it
                    option.textContent = expectedEmoji + ' ' + cleanText;
                }
                // Otherwise leave it alone
                return;
            }

            // Get clean text without any emojis
            const cleanText = removeAllEmojis(currentText);

            // P308 FIX: Only set text if we have either i18n or valid clean text
            if (i18nKey && window.i18n && window.i18n.translate) {
                const translation = window.i18n.translate(i18nKey);
                const cleanTranslation = removeAllEmojis(translation);
                // Set text with single emoji at start
                option.textContent = expectedEmoji ? expectedEmoji + ' ' + cleanTranslation : cleanTranslation;
            } else if (cleanText) {
                // No i18n - just add emoji to clean text
                option.textContent = expectedEmoji ? expectedEmoji + ' ' + cleanText : cleanText;
            }
        });

        // Restore the selection
        selector.value = currentValue;
    });

    console.log('[P308] ✅ Circle displays updated');
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
    console.log('[P308] Feed updates initializing...');
    // Single delayed call to let i18n initialize first
    setTimeout(updateCircleDisplays, 200);
}

document.addEventListener('DOMContentLoaded', initialize);

// Update when language changes
window.addEventListener('languageChanged', () => {
    console.log('[P308] Language changed, updating circle displays');
    updateCircleDisplays();
});

// Try to run immediately if DOM already ready
if (document.readyState === 'complete' || document.readyState === 'interactive') {
    initialize();
}

console.log('[P308] ✅ feed-updates.js loaded');
