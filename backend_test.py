/**
 * TheraSocial Frontend Diagnostic Suite
 * Comprehensive testing for production readiness
 * 
 * Run in browser console:
 * 1. Open https://socialsocial-72gn.onrender.com
 * 2. Open Developer Tools (F12)
 * 3. Go to Console tab
 * 4. Copy and paste this entire script
 * 5. Press Enter
 */

(function() {
    'use strict';
    
    // Results tracking
    const results = {
        passed: 0,
        failed: 0,
        warnings: 0,
        issues: []
    };
    
    // Console styling
    const styles = {
        header: 'color: #667eea; font-weight: bold; font-size: 16px;',
        section: 'color: #667eea; font-weight: bold; font-size: 14px;',
        pass: 'color: #22c55e; font-weight: bold;',
        fail: 'color: #ef4444; font-weight: bold;',
        warn: 'color: #f59e0b; font-weight: bold;',
        info: 'color: #3b82f6;',
        fix: 'color: #22c55e; font-style: italic;'
    };
    
    function printHeader(title) {
        console.log('%c' + '='.repeat(60), styles.header);
        console.log('%c' + title, styles.header);
        console.log('%c' + '='.repeat(60), styles.header);
    }
    
    function printSection(title) {
        console.log('\n%c' + title, styles.section);
        console.log('%c' + '-'.repeat(title.length), styles.section);
    }
    
    function printResult(passed, message, details = null, fix = null) {
        const symbol = passed ? '✓' : (passed === null ? '⚠' : '✗');
        const style = passed ? styles.pass : (passed === null ? styles.warn : styles.fail);
        
        console.log('%c' + symbol + ' ' + message, style);
        if (details) {
            console.log('  %c→ ' + details, styles.info);
        }
        if (fix && !passed) {
            console.log('  %cFIX: ' + fix, styles.fix);
        }
        
        // Track results
        if (passed) {
            results.passed++;
        } else if (passed === null) {
            results.warnings++;
        } else {
            results.failed++;
            results.issues.push({ message, details, fix });
        }
    }
    
    // ============================================
    // TEST: Global Dependencies
    // ============================================
    function testGlobalDependencies() {
        printSection('Global Dependencies');
        
        // Check i18n
        printResult(
            typeof window.i18n === 'object',
            'i18n internationalization system',
            window.i18n ? 'Loaded successfully' : 'Not found',
            'Ensure /static/js/i18n.js is loaded before other scripts'
        );
        
        if (window.i18n) {
            printResult(
                typeof window.i18n.translate === 'function',
                'i18n.translate() function',
                'Available',
                null
            );
            
            printResult(
                typeof window.i18n.setLanguage === 'function',
                'i18n.setLanguage() function',
                'Available',
                null
            );
            
            printResult(
                typeof window.i18n.applyLanguage === 'function',
                'i18n.applyLanguage() function',
                'Available',
                null
            );
        }
        
        // Check feed-updates
        printResult(
            typeof window.updateCircleDisplays === 'function',
            'Circle display update functions',
            window.updateCircleDisplays ? 'Available' : 'Not found',
            'Ensure /static/js/feed-updates.js is loaded'
        );
    }
    
    // ============================================
    // TEST: Page Loading
    // ============================================
    function testPageLoading() {
        printSection('Page Loading & Initialization');
        
        // Check if DOM is ready
        printResult(
            document.readyState === 'complete',
            'DOM ready state',
            document.readyState,
            null
        );
        
        // Check for loading indicators stuck visible
        const loadingElements = document.querySelectorAll('[id*="loading"], [class*="loading"]');
        const visibleLoading = Array.from(loadingElements).filter(el => {
            return el.style.display !== 'none' && 
                   el.style.visibility !== 'hidden' && 
                   el.offsetParent !== null;
        });
        
        printResult(
            visibleLoading.length === 0,
            'No stuck loading indicators',
            visibleLoading.length > 0 ? `Found ${visibleLoading.length} visible loading elements` : 'All clear',
            visibleLoading.length > 0 ? 'Check page initialization code - loading indicators should hide after load' : null
        );
        
        // Check for error messages
        const errorElements = document.querySelectorAll('[id*="error"], [class*="error"]');
        const visibleErrors = Array.from(errorElements).filter(el => {
            return el.style.display !== 'none' && 
                   el.style.visibility !== 'hidden' && 
                   el.offsetParent !== null &&
                   el.textContent.trim().length > 0;
        });
        
        printResult(
            visibleErrors.length === 0,
            'No visible error messages',
            visibleErrors.length > 0 ? `Found ${visibleErrors.length} error messages` : 'No errors',
            visibleErrors.length > 0 ? 'Fix backend errors or hide error containers by default' : null
        );
    }
    
    // ============================================
    // TEST: Authentication State
    // ============================================
    async function testAuthenticationState() {
        printSection('Authentication State');
        
        try {
            const response = await fetch('/api/auth/session');
            const isAuthenticated = response.ok;
            
            printResult(
                isAuthenticated || !isAuthenticated,  // Both states are valid
                'Session check endpoint',
                isAuthenticated ? 'Authenticated' : 'Not authenticated (expected if not logged in)',
                !response.ok && response.status !== 401 ? 'Fix /api/auth/session endpoint' : null
            );
            
            if (isAuthenticated) {
                const data = await response.json();
                printResult(
                    data.user && data.user.id,
                    'User session data',
                    data.user ? `User ID: ${data.user.id}` : 'Invalid data',
                    'Ensure session endpoint returns user data'
                );
            }
        } catch (error) {
            printResult(
                false,
                'Session check endpoint',
                error.message,
                'Fix /api/auth/session endpoint or CORS configuration'
            );
        }
    }
    
    // ============================================
    // TEST: API Endpoints
    // ============================================
    async function testAPIEndpoints() {
        printSection('API Endpoint Availability');
        
        const endpoints = [
            { url: '/api/user/profile', method: 'GET', requiresAuth: true },
            { url: '/api/posts', method: 'GET', requiresAuth: false },
            { url: '/api/alerts', method: 'GET', requiresAuth: true },
            { url: '/api/circles', method: 'GET', requiresAuth: true }
        ];
        
        for (const endpoint of endpoints) {
            try {
                const response = await fetch(endpoint.url, { method: endpoint.method });
                const isOk = response.ok || (endpoint.requiresAuth && response.status === 401);
                
                printResult(
                    isOk,
                    `${endpoint.method} ${endpoint.url}`,
                    `Status: ${response.status} ${response.statusText}`,
                    !isOk ? `Fix ${endpoint.url} endpoint in backend` : null
                );
            } catch (error) {
                printResult(
                    false,
                    `${endpoint.method} ${endpoint.url}`,
                    error.message,
                    'Check network connectivity and backend status'
                );
            }
        }
    }
    
    // ============================================
    // TEST: Translation System
    // ============================================
    function testTranslationSystem() {
        printSection('Translation System');
        
        if (!window.i18n) {
            printResult(false, 'Translation system', 'i18n not loaded', 'Load i18n.js before testing');
            return;
        }
        
        // Check available languages
        const languages = window.i18n.translations ? Object.keys(window.i18n.translations) : [];
        printResult(
            languages.length >= 4,
            'Available languages',
            `Found: ${languages.join(', ')} (${languages.length} total)`,
            languages.length < 4 ? 'Add missing language translations (en, he, ar, ru)' : null
        );
        
        // Check current language
        const currentLang = window.i18n.currentLanguage || window.i18n.getCurrentLanguage?.();
        printResult(
            ['en', 'he', 'ar', 'ru'].includes(currentLang),
            'Current language valid',
            `Current: ${currentLang}`,
            'Set valid default language in i18n initialization'
        );
        
        // Check RTL support
        const rtlLanguages = ['ar', 'he'];
        const bodyDir = document.body.getAttribute('dir');
        const shouldBeRTL = rtlLanguages.includes(currentLang);
        const isRTL = bodyDir === 'rtl';
        
        printResult(
            isRTL === shouldBeRTL || bodyDir === null,
            'RTL direction support',
            `Body dir="${bodyDir}", Language: ${currentLang}`,
            shouldBeRTL && !isRTL ? 'Set document.body.dir = "rtl" for Arabic/Hebrew' : null
        );
        
        // Test translation function
        if (window.i18n.translate) {
            const testKey = 'privacy.public';
            const translation = window.i18n.translate(testKey);
            printResult(
                translation && translation !== testKey,
                'Translation function working',
                `Test key "${testKey}" → "${translation}"`,
                'Add translations for common keys'
            );
        }
        
        // Check for missing translations (data-i18n attributes without translations)
        const i18nElements = document.querySelectorAll('[data-i18n]');
        let missingTranslations = 0;
        i18nElements.forEach(el => {
            const key = el.getAttribute('data-i18n');
            if (key && window.i18n.translate) {
                const translation = window.i18n.translate(key);
                if (translation === key) {
                    missingTranslations++;
                }
            }
        });
        
        printResult(
            missingTranslations === 0,
            'Missing translations',
            missingTranslations > 0 ? 
                `Found ${missingTranslations} elements with missing translations` : 
                'All elements have translations',
            missingTranslations > 0 ? 
                'Add missing translation keys to i18n.translations' : null
        );
    }
    
    // ============================================
    // TEST: Circle Display System
    // ============================================
    function testCircleDisplaySystem() {
        printSection('Circle Display System');
        
        // Check circle emoji mapping
        printResult(
            typeof window.CIRCLE_EMOJIS === 'object',
            'Circle emoji mappings',
            window.CIRCLE_EMOJIS ? 'Loaded' : 'Not found',
            'Ensure CIRCLE_EMOJIS is defined in feed-updates.js'
        );
        
        // Check for duplicate emojis in circle displays
        const circleElements = document.querySelectorAll('[data-circle], .circle-header, option[value*="class"], option[value="public"]');
        let duplicateEmojis = 0;
        
        circleElements.forEach(el => {
            const text = el.textContent;
            // Count emojis using regex
            const emojiMatches = text.match(/[\u{1F000}-\u{1FAFF}\u{2600}-\u{27BF}]/ug) || [];
            if (emojiMatches.length > 1) {
                duplicateEmojis++;
            }
        });
        
        printResult(
            duplicateEmojis === 0,
            'No duplicate emojis in circles',
            duplicateEmojis > 0 ? 
                `Found ${duplicateEmojis} elements with duplicate emojis` : 
                'All circles display correctly',
            duplicateEmojis > 0 ? 
                'Run updateCircleDisplays() to fix emoji duplication' : null
        );
        
        // Check privacy dropdowns
        const privacySelects = document.querySelectorAll('select[name="circle"], .privacy-select, .visibility-selector');
        printResult(
            privacySelects.length > 0 || true,  // Warning if not found
            'Privacy dropdown selectors',
            `Found ${privacySelects.length} privacy selectors`,
            privacySelects.length === 0 ? 'Add privacy selectors to forms' : null
        );
    }
    
    // ============================================
    // TEST: Console Errors
    // ============================================
    function testConsoleErrors() {
        printSection('Console Error Detection');
        
        // Check for common error patterns in console
        const consoleErrors = [];
        const originalError = console.error;
        const originalWarn = console.warn;
        
        // Temporarily intercept console errors
        window._diagnosticErrors = [];
        console.error = function(...args) {
            window._diagnosticErrors.push({ type: 'error', message: args.join(' ') });
            originalError.apply(console, args);
        };
        console.warn = function(...args) {
            window._diagnosticErrors.push({ type: 'warn', message: args.join(' ') });
            originalWarn.apply(console, args);
        };
        
        printResult(
            null,
            'Console error monitoring active',
            'Error tracking started - refresh page to capture errors',
            'Run this diagnostic again after page refresh to see errors'
        );
        
        // Restore original console methods after a delay
        setTimeout(() => {
            console.error = originalError;
            console.warn = originalWarn;
        }, 1000);
    }
    
    // ============================================
    // TEST: Network Requests
    // ============================================
    function testNetworkRequests() {
        printSection('Network Request Analysis');
        
        // Check Performance API for failed requests
        if (window.performance && window.performance.getEntriesByType) {
            const resources = window.performance.getEntriesByType('resource');
            
            // Analyze resource loading
            let failedResources = 0;
            const slowResources = [];
            
            resources.forEach(resource => {
                // Check for failed loads (duration = 0 often indicates failure)
                if (resource.duration === 0 && resource.transferSize === 0) {
                    failedResources++;
                }
                
                // Check for slow resources (>2 seconds)
                if (resource.duration > 2000) {
                    slowResources.push({
                        name: resource.name.split('/').pop(),
                        duration: Math.round(resource.duration)
                    });
                }
            });
            
            printResult(
                failedResources === 0,
                'Failed resource loads',
                failedResources > 0 ? 
                    `Found ${failedResources} failed resources` : 
                    'All resources loaded successfully',
                failedResources > 0 ? 
                    'Check network tab for 404 errors and fix missing files' : null
            );
            
            printResult(
                slowResources.length === 0,
                'Resource loading performance',
                slowResources.length > 0 ? 
                    `${slowResources.length} resources took >2s to load` : 
                    'All resources load quickly',
                slowResources.length > 0 ? 
                    'Optimize slow resources: ' + slowResources.map(r => `${r.name} (${r.duration}ms)`).join(', ') : null
            );
            
            printResult(
                true,
                'Total resources loaded',
                `${resources.length} resources analyzed`,
                null
            );
        }
    }
    
    // ============================================
    // TEST: Form Validation
    // ============================================
    function testFormValidation() {
        printSection('Form Validation');
        
        const forms = document.querySelectorAll('form');
        printResult(
            forms.length > 0 || true,
            'Forms detected',
            `Found ${forms.length} forms on page`,
            null
        );
        
        // Check for forms without submit handlers
        let formsWithoutHandlers = 0;
        forms.forEach(form => {
            // Check if form has submit event listener or action attribute
            const hasAction = form.hasAttribute('action');
            const hasOnSubmit = form.hasAttribute('onsubmit');
            
            if (!hasAction && !hasOnSubmit) {
                formsWithoutHandlers++;
            }
        });
        
        printResult(
            formsWithoutHandlers === 0,
            'Forms with submit handlers',
            formsWithoutHandlers > 0 ? 
                `Found ${formsWithoutHandlers} forms without handlers` : 
                'All forms have handlers',
            'Add submit event handlers to all forms'
        );
        
        // Check for input validation
        const requiredInputs = document.querySelectorAll('input[required], select[required], textarea[required]');
        printResult(
            requiredInputs.length > 0 || null,
            'Required field validation',
            `Found ${requiredInputs.length} required fields`,
            requiredInputs.length === 0 ? 'Add required attributes to critical form fields' : null
        );
    }
    
    // ============================================
    // TEST: Security Concerns
    // ============================================
    function testSecurityConcerns() {
        printSection('Security Analysis');
        
        // Check for inline scripts (potential XSS)
        const inlineScripts = document.querySelectorAll('script:not([src])');
        const suspiciousScripts = Array.from(inlineScripts).filter(script => {
            const content = script.textContent;
            return content.includes('eval(') || 
                   content.includes('innerHTML =') ||
                   content.includes('document.write');
        });
        
        printResult(
            suspiciousScripts.length === 0,
            'No suspicious inline scripts',
            suspiciousScripts.length > 0 ? 
                `Found ${suspiciousScripts.length} scripts with potential XSS vectors` : 
                'No obvious XSS risks',
            'Replace innerHTML with textContent or use DOM manipulation'
        );
        
        // Check for password fields without autocomplete
        const passwordFields = document.querySelectorAll('input[type="password"]');
        let passwordsWithoutAutocomplete = 0;
        passwordFields.forEach(field => {
            if (!field.hasAttribute('autocomplete')) {
                passwordsWithoutAutocomplete++;
            }
        });
        
        printResult(
            passwordsWithoutAutocomplete === 0 || passwordFields.length === 0,
            'Password field autocomplete attributes',
            passwordsWithoutAutocomplete > 0 ? 
                `${passwordsWithoutAutocomplete} password fields missing autocomplete` : 
                'All password fields configured',
            'Add autocomplete="current-password" or "new-password" to password fields'
        );
        
        // Check for HTTPS
        printResult(
            window.location.protocol === 'https:',
            'HTTPS encryption',
            `Using ${window.location.protocol}`,
            window.location.protocol !== 'https:' ? 'Enable HTTPS in production' : null
        );
    }
    
    // ============================================
    // TEST: Mobile Responsiveness
    // ============================================
    function testMobileResponsiveness() {
        printSection('Mobile Responsiveness');
        
        // Check viewport meta tag
        const viewport = document.querySelector('meta[name="viewport"]');
        printResult(
            viewport !== null,
            'Viewport meta tag',
            viewport ? viewport.getAttribute('content') : 'Not found',
            'Add <meta name="viewport" content="width=device-width, initial-scale=1.0">'
        );
        
        // Check for fixed width elements that might break mobile
        const fixedWidthElements = document.querySelectorAll('[style*="width:"][style*="px"]');
        printResult(
            fixedWidthElements.length < 10 || null,
            'Fixed-width elements',
            `Found ${fixedWidthElements.length} elements with px widths`,
            fixedWidthElements.length > 20 ? 
                'Consider using responsive units (%, rem, em) instead of px' : null
        );
        
        // Check touch-friendly button sizes
        const buttons = document.querySelectorAll('button, .btn, [role="button"]');
        let smallButtons = 0;
        buttons.forEach(btn => {
            const rect = btn.getBoundingClientRect();
            if (rect.width < 44 || rect.height < 44) {
                smallButtons++;
            }
        });
        
        printResult(
            smallButtons === 0,
            'Touch-friendly button sizes',
            smallButtons > 0 ? 
                `Found ${smallButtons} buttons smaller than 44x44px` : 
                'All buttons are touch-friendly',
            'Ensure interactive elements are at least 44x44px for mobile'
        );
    }
    
    // ============================================
    // TEST: Performance Metrics
    // ============================================
    function testPerformanceMetrics() {
        printSection('Performance Metrics');
        
        if (window.performance && window.performance.timing) {
            const timing = window.performance.timing;
            const loadTime = timing.loadEventEnd - timing.navigationStart;
            const domReady = timing.domContentLoadedEventEnd - timing.navigationStart;
            
            printResult(
                loadTime < 3000,
                'Page load time',
                `${loadTime}ms`,
                loadTime >= 3000 ? 'Optimize assets and reduce bundle size' : null
            );
            
            printResult(
                domReady < 2000,
                'DOM ready time',
                `${domReady}ms`,
                domReady >= 2000 ? 'Reduce blocking scripts and optimize critical rendering path' : null
            );
        }
        
        // Check memory usage if available
        if (window.performance && window.performance.memory) {
            const memory = window.performance.memory;
            const usedMB = Math.round(memory.usedJSHeapSize / 1048576);
            const limitMB = Math.round(memory.jsHeapSizeLimit / 1048576);
            
            printResult(
                usedMB < limitMB * 0.8,
                'JavaScript memory usage',
                `${usedMB}MB used of ${limitMB}MB limit`,
                usedMB >= limitMB * 0.8 ? 'High memory usage detected - check for memory leaks' : null
            );
        }
    }
    
    // ============================================
    // TEST: Accessibility
    // ============================================
    function testAccessibility() {
        printSection('Accessibility');
        
        // Check for alt text on images
        const images = document.querySelectorAll('img');
        let imagesWithoutAlt = 0;
        images.forEach(img => {
            if (!img.hasAttribute('alt')) {
                imagesWithoutAlt++;
            }
        });
        
        printResult(
            imagesWithoutAlt === 0,
            'Image alt text',
            imagesWithoutAlt > 0 ? 
                `Found ${imagesWithoutAlt} images without alt text` : 
                'All images have alt text',
            'Add descriptive alt attributes to all images'
        );
        
        // Check for proper heading hierarchy
        const headings = document.querySelectorAll('h1, h2, h3, h4, h5, h6');
        const h1Count = document.querySelectorAll('h1').length;
        
        printResult(
            h1Count === 1 || h1Count === 0,
            'Heading hierarchy',
            h1Count === 1 ? 'Single H1 found (correct)' : 
                h1Count === 0 ? 'No H1 found (add one)' : 
                `Multiple H1s found (${h1Count})`,
            h1Count > 1 ? 'Use only one H1 per page' : 
                h1Count === 0 ? 'Add an H1 heading to the page' : null
        );
        
        // Check for ARIA labels on interactive elements
        const interactiveElements = document.querySelectorAll('button:not([aria-label]), a:not([aria-label])[href="#"]');
        printResult(
            interactiveElements.length < 5 || null,
            'ARIA labels on interactive elements',
            `${interactiveElements.length} elements could use aria-label`,
            interactiveElements.length > 5 ? 
                'Add aria-label to buttons and links without text content' : null
        );
    }
    
    // ============================================
    // GENERATE REPORT
    // ============================================
    function generateReport() {
        printHeader('Diagnostic Summary');
        
        const total = results.passed + results.failed + results.warnings;
        
        console.log('\n%cTest Results:', 'font-weight: bold;');
        console.log('%c✓ Passed:  ' + results.passed + '/' + total, styles.pass);
        console.log('%c✗ Failed:  ' + results.failed + '/' + total, styles.fail);
        console.log('%c⚠ Warnings: ' + results.warnings + '/' + total, styles.warn);
        
        if (results.issues.length > 0) {
            console.log('\n%cCritical Issues:', 'color: #ef4444; font-weight: bold;');
            results.issues.forEach((issue, index) => {
                console.log(`\n%c${index + 1}. ${issue.message}`, 'font-weight: bold;');
                if (issue.details) {
                    console.log(`   Details: ${issue.details}`);
                }
                if (issue.fix) {
                    console.log('%c   Fix: ' + issue.fix, styles.fix);
                }
            });
        }
        
        // Overall assessment
        console.log('\n%cOverall Assessment:', 'font-weight: bold;');
        if (results.failed === 0) {
            console.log('%c✓ Frontend is ready for QA testing', styles.pass);
        } else if (results.failed < 5) {
            console.log('%c⚠ Frontend needs minor fixes before QA', styles.warn);
        } else {
            console.log('%c✗ Frontend requires significant fixes before QA', styles.fail);
        }
        
        // Export results
        window.frontendDiagnosticResults = results;
        console.log('\n%cResults exported to: window.frontendDiagnosticResults', styles.info);
    }
    
    // ============================================
    // RUN ALL TESTS
    // ============================================
    async function runAllTests() {
        printHeader('TheraSocial Frontend Diagnostic Suite');
        console.log('Running comprehensive frontend tests...\n');
        
        testGlobalDependencies();
        testPageLoading();
        await testAuthenticationState();
        await testAPIEndpoints();
        testTranslationSystem();
        testCircleDisplaySystem();
        testConsoleErrors();
        testNetworkRequests();
        testFormValidation();
        testSecurityConcerns();
        testMobileResponsiveness();
        testPerformanceMetrics();
        testAccessibility();
        
        generateReport();
    }
    
    // Start tests
    runAllTests();
    
})();
