// feed-updates.js - Circle display name mappings
const CIRCLE_MAPPINGS = {
    // Internal to display mappings
    'general': 'Public',
    'close_friends': 'Class B (Friends)',
    'family': 'Class A (Family)',
    'private': 'Private',
    // New internal names
    'public': 'Public',
    'class_b': 'Class B (Friends)',
    'class_a': 'Class A (Family)',
    // Numeric IDs
    1: 'Public',
    2: 'Class B (Friends)',
    3: 'Class A (Family)'
};

function getDisplayName(internalName) {
    return CIRCLE_MAPPINGS[internalName] || internalName;
}

function getInternalName(displayName) {
    // Map display names back to internal names
    const reverseMap = {
        'Public': 'public',
        'Class B (Friends)': 'class_b',
        'Class A (Family)': 'class_a',
        'Private': 'private'
    };
    return reverseMap[displayName] || displayName;
}

// Update all dropdowns and displays
// Update all dropdowns and displays
function updateCircleDisplays() {
    console.log('Updating circle displays...');

    // Fix circles page headers
    const circleHeaders = document.querySelectorAll('.circle-header h2, .circle-name');
    circleHeaders.forEach(header => {
        const text = header.textContent.trim();
        if (text === 'General') header.textContent = 'Public';
        else if (text === 'Close Friends') header.textContent = 'Class B (Friends)';
        else if (text === 'Family') header.textContent = 'Class A (Family)';
    });

    // Update all circle selectors in feed
    document.querySelectorAll('.circle-selector, .visibility-selector, select[name="circle"], .privacy-select, .visibility-select').forEach(selector => {
        // Store current value
        const currentValue = selector.value;

        // Update all options
        selector.querySelectorAll('option').forEach(option => {
            const value = option.value;
            const text = option.textContent.trim();
            const i18nKey = option.getAttribute('data-i18n');

          // If option has data-i18n attribute, use translation
            if (i18nKey && window.i18n && window.i18n.translate) {
                const translation = window.i18n.translate(i18nKey);
                // Extract emoji ONLY from the option's VALUE attribute, not from existing text
                let emoji = '';
                if (value === 'private') {
                    emoji = '🔒 ';
                } else if (value === 'public' || value === 'general') {
                    emoji = '🌐 ';
                } else if (value === 'close_friends' || value === 'class_b') {
                    emoji = '👥 ';
                } else if (value === 'family' || value === 'class_a') {
                    emoji = '👨‍👩‍👧‍👦 ';
                }
                // Remove any existing emoji from translation
                const cleanTranslation = translation.replace(/^([\u{1F300}-\u{1F9FF}]|[\u{2600}-\u{26FF}]|[\u{2700}-\u{27BF}]|🔒|🌐|👥|👨‍👩‍👧‍👦)\s*/u, '');
                option.textContent = emoji + cleanTranslation;
            } else {
                // Fallback: Map both by value AND by text
                if (value === 'general' || value === 'public' || text === 'General') {
                    option.textContent = 'Public';
                    option.value = 'public';
                } else if (value === 'close_friends' || value === 'class_b' || text === 'Close Friends') {
                    option.textContent = 'Class B (Friends)';
                    option.value = 'class_b';
                } else if (value === 'family' || value === 'class_a' || text === 'Family') {
                    option.textContent = 'Class A (Family)';
                    option.value = 'class_a';
                } else if (value === 'private') {
                    option.textContent = 'Private';
                    option.value = 'private';
                }
            }
        });

        // Restore the selection with mapped value
        if (currentValue === 'general') selector.value = 'public';
        else if (currentValue === 'close_friends') selector.value = 'class_b';
        else if (currentValue === 'family') selector.value = 'class_a';
        else selector.value = currentValue;
    });

    // Update all standalone dropdown options with data-i18n attributes
    // (This handles any dropdowns not caught by the selector above)
  // Update all standalone dropdown options with data-i18n attributes
    // (This handles any dropdowns not caught by the selector above)
    document.querySelectorAll('select option[data-i18n]').forEach(option => {
        const key = option.getAttribute('data-i18n');
        const value = option.value;
        if (key && window.i18n && window.i18n.translate) {
            const translation = window.i18n.translate(key);
            // Determine emoji based on VALUE, not existing text
            let emoji = '';
            if (value === 'private') {
                emoji = '🔒 ';
            } else if (value === 'public' || value === 'general') {
                emoji = '🌐 ';
            } else if (value === 'close_friends' || value === 'class_b') {
                emoji = '👥 ';
            } else if (value === 'family' || value === 'class_a') {
                emoji = '👨‍👩‍👧‍👦 ';
            }
            // Remove any existing emoji from translation
            const cleanTranslation = translation.replace(/^([\u{1F300}-\u{1F9FF}]|[\u{2600}-\u{26FF}]|[\u{2700}-\u{27BF}]|🔒|🌐|👥|👨‍👩‍👧‍👦)\s*/u, '');
            option.textContent = emoji + cleanTranslation;
        }
    });
}

// Export functions for use in other files
if (typeof window !== 'undefined') {
    window.getDisplayName = getDisplayName;
    window.getInternalName = getInternalName;
    window.updateCircleDisplays = updateCircleDisplays;
}

// Call on page load with delay to ensure DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    console.log('Feed updates DOM loaded');
    // Multiple attempts to ensure it runs
    setTimeout(updateCircleDisplays, 100);
    setTimeout(updateCircleDisplays, 500);
    setTimeout(updateCircleDisplays, 1000);
});

// Also update when language changes
window.addEventListener('languageChanged', () => {
    setTimeout(updateCircleDisplays, 100);
});

// Try to run immediately as well
if (document.readyState === 'complete' || document.readyState === 'interactive') {
    setTimeout(updateCircleDisplays, 100);
}