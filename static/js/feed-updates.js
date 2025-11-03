// feed-updates.js - Add this new file
const CIRCLE_MAPPINGS = {
    // Old to new mappings
    'general': 'Public',
    'close_friends': 'Class B (Friends)',
    'family': 'Class A (Family)',
    'private': 'Private',
    // Also handle reverse lookups
    'Public': 'general',
    'Class B (Friends)': 'close_friends',
    'Class A (Family)': 'family',
    'Private': 'private'
};

function getDisplayName(internalName) {
    return CIRCLE_MAPPINGS[internalName] || internalName;
}

function getInternalName(displayName) {
    // Find the internal name from display name
    for (const [internal, display] of Object.entries(CIRCLE_MAPPINGS)) {
        if (display === displayName) {
            return internal;
        }
    }
    return displayName;
}

// Update all dropdowns and displays
function updateCircleDisplays() {
    // Update all circle selectors
    document.querySelectorAll('.circle-selector, .visibility-selector, select[name="circle"]').forEach(selector => {
        const options = selector.querySelectorAll('option');
        options.forEach(option => {
            const value = option.value;
            if (value === 'general') {
                option.textContent = 'Public';
                option.value = 'general';
            } else if (value === 'close_friends') {
                option.textContent = 'Class B (Friends)';
                option.value = 'close_friends';
            } else if (value === 'family') {
                option.textContent = 'Class A (Family)';
                option.value = 'family';
            }
        });
    });
}

// Call on page load
document.addEventListener('DOMContentLoaded', updateCircleDisplays);
