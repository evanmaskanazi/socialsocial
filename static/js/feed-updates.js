// feed-updates.js - Circle display name mappings
const CIRCLE_EMOJIS = {
    'private': '🔒 ', 'public': '🌍 ', 'general': '🌍 ',
    'class_b': '👥 ', 'close_friends': '👥 ',
    'class_a': '👨‍👩‍👧‍👦 ', 'family': '👨‍👩‍👧‍👦 '
};

function getDisplayName(internalName) {
    return internalName;
}

function getInternalName(displayName) {
    const reverseMap = {
        'Public': 'public', 'Class B (Friends)': 'class_b',
        'Class A (Family)': 'class_a', 'Private': 'private'
    };
    return reverseMap[displayName] || displayName;
}

// Simple emoji removal - catches all Unicode emojis
function removeAllEmojis(text) {
    return text
        .replace(/[\u{1F000}-\u{1FAFF}\u{2600}-\u{27BF}\u{200D}\u{FE0F}]/ug, '')
        .replace(/\s+/g, ' ').trim();
}

// Update all dropdowns and displays
function updateCircleDisplays() {
    console.log('Updating circle displays...');

    // Update circle selectors
    document.querySelectorAll('.circle-selector, .visibility-selector, select[name="circle"], .privacy-select, .visibility-select, #circlesPrivacySelect').forEach(selector => {
        const currentValue = selector.value;

        selector.querySelectorAll('option').forEach(option => {
            const value = option.value;
            const i18nKey = option.getAttribute('data-i18n');

            // Use i18n translation if available
            if (i18nKey && window.i18n && window.i18n.translate) {
                const translation = window.i18n.translate(i18nKey);
                const cleanText = removeAllEmojis(translation);
                const emoji = CIRCLE_EMOJIS[value] || '';
                option.textContent = emoji + cleanText;
            }
        });

        selector.value = currentValue;
    });
}

// Export functions
if (typeof window !== 'undefined') {
    window.getDisplayName = getDisplayName;
    window.getInternalName = getInternalName;
    window.updateCircleDisplays = updateCircleDisplays;
}

// Initialize once when DOM ready
let initialized = false;
document.addEventListener('DOMContentLoaded', () => {
    if (!initialized) {
        initialized = true;
        setTimeout(updateCircleDisplays, 200);
    }
});

// Update on language change
window.addEventListener('languageChanged', updateCircleDisplays);

// Run immediately if DOM already ready
if ((document.readyState === 'complete' || document.readyState === 'interactive') && !initialized) {
    initialized = true;
    setTimeout(updateCircleDisplays, 200);
}

// Update all dropdowns and displays
function updateCircleDisplays() {
    console.log('Updating circle displays...');

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
                header.textContent = emoji + ' ' + removeAllEmojis(translatedText);
            }
        });
    }

    // Update all circle selectors in feed
    document.querySelectorAll('.circle-selector, .visibility-selector, select[name="circle"], .privacy-select, .visibility-select, #circlesPrivacySelect').forEach(selector => {
        // Store current value
        const currentValue = selector.value;

        // Update all options
        selector.querySelectorAll('option').forEach(option => {
            const value = option.value;
            const i18nKey = option.getAttribute('data-i18n');

            // ALWAYS use i18n translation if available
            if (i18nKey && window.i18n && window.i18n.translate) {
                const translation = window.i18n.translate(i18nKey);
                const cleanTranslation = removeAllEmojis(translation);
                const emoji = CIRCLE_EMOJIS[value] || '';

                // Set text with single emoji
                option.textContent = emoji ? emoji + ' ' + cleanTranslation : cleanTranslation;
            } else {
                // Fallback: just add emoji to existing text
                const currentText = removeAllEmojis(option.textContent);
                const emoji = CIRCLE_EMOJIS[value] || '';
                option.textContent = emoji ? emoji + ' ' + currentText : currentText;
            }
        });

        // Restore the selection
        selector.value = currentValue;
    });
}

// Export functions for use in other files
if (typeof window !== 'undefined') {
    window.getDisplayName = getDisplayName;
    window.getInternalName = getInternalName;
    window.updateCircleDisplays = updateCircleDisplays;
    window.removeAllEmojis = removeAllEmojis; // Export for debugging
}

// SIMPLIFIED initialization - only run once when DOM is ready
let initialized = false;
document.addEventListener('DOMContentLoaded', () => {
    if (initialized) return;
    initialized = true;

    console.log('Feed updates DOM loaded');
    // Single delayed call to let i18n initialize first
    setTimeout(updateCircleDisplays, 200);
});

// Update when language changes - but don't re-initialize
window.addEventListener('languageChanged', () => {
    console.log('Language changed, updating circle displays');
    updateCircleDisplays();
});

// Try to run immediately if DOM already ready
if (document.readyState === 'complete' || document.readyState === 'interactive') {
    if (!initialized) {
        initialized = true;
        setTimeout(updateCircleDisplays, 200);
    }
}