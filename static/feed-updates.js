// Version P320 Lang - Uses existing CIRCLE_EMOJIS, does not redeclare
// feed-updates.js - Circle display name mappings
// Version Lang - Replaced hardcoded English visibility names with i18n lookups
// FIX: circles-messages.js already declares CIRCLE_EMOJIS with const
// So we just reference it directly - no redeclaration

(function() {
    'use strict';
    
    // Direct reference to existing CIRCLE_EMOJIS (from circles-messages.js)
    var emojis = CIRCLE_EMOJIS;

    function getDisplayName(internalName) {
        return internalName;
    }

    function getInternalName(displayName) {
        // Build reverse map dynamically from translations
        var t = (window.i18n && window.i18n.translate) ? window.i18n.translate.bind(window.i18n) : function(k) { return k; };
        var reverseMap = {};
        // Always include English fallbacks
        reverseMap['Public'] = 'public';
        reverseMap['Close Friends'] = 'class_b';
        reverseMap['Family'] = 'class_a';
        reverseMap['Private'] = 'private';
        // Add current language translations
        reverseMap[t('privacy.public')] = 'public';
        reverseMap[t('privacy.class_b')] = 'class_b';
        reverseMap[t('privacy.class_a')] = 'class_a';
        reverseMap[t('privacy.private')] = 'private';
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
        console.log('Updating circle displays...');

        // Fix circles page headers - ONLY if they exist
        var circleHeaders = document.querySelectorAll('.circle-header h2, .circle-name');
        if (circleHeaders.length > 0) {
            circleHeaders.forEach(function(header) {
                var currentText = removeAllEmojis(header.textContent);

                var internalValue = header.getAttribute('data-circle-type');
                if (!internalValue) {
                    // Match against both English and translated names
                    var t = (window.i18n && window.i18n.translate) ? window.i18n.translate.bind(window.i18n) : function(k) { return k; };
                    var publicNames = ['General', 'Public', removeAllEmojis(t('privacy.public')), removeAllEmojis(t('circles.title_public'))];
                    var classBNames = ['Close Friends', 'Class B', removeAllEmojis(t('privacy.class_b')), removeAllEmojis(t('circles.title_class_b'))];
                    var classANames = ['Family', 'Class A', removeAllEmojis(t('privacy.class_a')), removeAllEmojis(t('circles.title_class_a'))];
                    
                    if (publicNames.some(function(n) { return currentText.includes(n); })) {
                        internalValue = 'public';
                    } else if (classBNames.some(function(n) { return currentText.includes(n); })) {
                        internalValue = 'class_b';
                    } else if (classANames.some(function(n) { return currentText.includes(n); })) {
                        internalValue = 'class_a';
                    }
                }

                if (internalValue && window.i18n && window.i18n.translate) {
                    var i18nKey = 'privacy.' + internalValue;
                    var translatedText = window.i18n.translate(i18nKey);
                    var emoji = emojis[internalValue] || '';
                    header.textContent = emoji + (emoji ? ' ' : '') + removeAllEmojis(translatedText);
                }
            });
        }

        // Update all circle selectors
        document.querySelectorAll('.circle-selector, .visibility-selector, select[name="circle"], .privacy-select, .visibility-select, #circlesPrivacySelect').forEach(function(selector) {
            var currentValue = selector.value;

            selector.querySelectorAll('option').forEach(function(option) {
                var value = option.value;
                var i18nKey = option.getAttribute('data-i18n');
                var currentText = option.textContent;

                var matches = currentText.match(/[\u{1F000}-\u{1FAFF}\u{2600}-\u{27BF}]/ug);
                var emojiCount = matches ? matches.length : 0;

                var emoji = emojis[value] || '';

                if (i18nKey && window.i18n && window.i18n.translate) {
                    var translation = window.i18n.translate(i18nKey);
                    var cleanTranslation = removeAllEmojis(translation);
                    option.textContent = emoji ? emoji + ' ' + cleanTranslation : cleanTranslation;
                } else if (emojiCount > 1) {
                    var cleanText = removeAllEmojis(currentText);
                    option.textContent = emoji ? emoji + ' ' + cleanText : cleanText;
                } else if (emojiCount === 0) {
                    option.textContent = emoji ? emoji + ' ' + currentText.trim() : currentText.trim();
                }
            });

            selector.value = currentValue;
        });

        console.log('✅ Circle displays updated');
    }

    // Export functions to window
    window.getDisplayName = getDisplayName;
    window.getInternalName = getInternalName;
    window.updateCircleDisplays = updateCircleDisplays;
    window.removeAllEmojis = removeAllEmojis;

    // Initialize
    var initialized = false;
    
    function initialize() {
        if (initialized) return;
        initialized = true;
        console.log('Feed updates initializing...');
        setTimeout(updateCircleDisplays, 100);
        setTimeout(updateCircleDisplays, 300);
        setTimeout(updateCircleDisplays, 500);
        setTimeout(updateCircleDisplays, 1000);
    }

    if (document.readyState === 'complete' || document.readyState === 'interactive') {
        initialize();
    } else {
        document.addEventListener('DOMContentLoaded', initialize);
    }

    window.addEventListener('languageChanged', function() {
        console.log('Language changed, updating circle displays');
        updateCircleDisplays();
        setTimeout(updateCircleDisplays, 200);
    });

    console.log('✅ feed-updates.js loaded');
})();
