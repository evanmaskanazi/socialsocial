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
    'class_a': 'Class A (Family)'
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
function updateCircleDisplays() {
    console.log('Updating circle displays...');

    // Update all circle selectors in feed
    document.querySelectorAll('.circle-selector, .visibility-selector, select[name="circle"], .privacy-select').forEach(selector => {
        // Store current value
        const currentValue = selector.value;

        // Update all options
        selector.querySelectorAll('option').forEach(option => {
            const value = option.value;

            // Map old values to new display names
            if (value === 'general' || value === 'public') {
                option.textContent = '🌍 Public';
                option.value = 'public';
            } else if (value === 'close_friends' || value === 'class_b') {
                option.textContent = '👥 Class B (Friends)';
                option.value = 'class_b';
            } else if (value === 'family' || value === 'class_a') {
                option.textContent = '👨‍👩‍👧‍👦 Class A (Family)';
                option.value = 'class_a';
            } else if (value === 'private') {
                option.textContent = '🔒 Private';
                option.value = 'private';
            }
        });

        // Restore the selection with mapped value
        if (currentValue === 'general') selector.value = 'public';
        else if (currentValue === 'close_friends') selector.value = 'class_b';
        else if (currentValue === 'family') selector.value = 'class_a';
        else selector.value = currentValue;
    });

    // Update any text displays showing circle names
    document.querySelectorAll('[data-circle-display]').forEach(element => {
        const text = element.textContent;
        if (text === 'General') element.textContent = 'Public';
        else if (text === 'Close Friends') element.textContent = 'Class B (Friends)';
        else if (text === 'Family') element.textContent = 'Class A (Family)';
    });

    // Update feed post visibility labels
    document.querySelectorAll('.post-visibility, .feed-visibility').forEach(element => {
        const text = element.textContent.trim();
        if (text === 'General' || text === 'general') {
            element.textContent = 'Public';
        } else if (text === 'Close Friends' || text === 'close_friends') {
            element.textContent = 'Class B (Friends)';
        } else if (text === 'Family' || text === 'family') {
            element.textContent = 'Class A (Family)';
        }
    });
}

// Export functions for use in other files
if (typeof window !== 'undefined') {
    window.getDisplayName = getDisplayName;
    window.getInternalName = getInternalName;
    window.updateCircleDisplays = updateCircleDisplays;
}

// Call on page load
document.addEventListener('DOMContentLoaded', () => {
    console.log('Feed updates DOM loaded');
    setTimeout(updateCircleDisplays, 100);
});

// Also update when language changes
window.addEventListener('languageChanged', () => {
    setTimeout(updateCircleDisplays, 100);
});