// Social Parameters Save/Load System with i18n support and numeric ratings
// COMPLETE FIXED VERSION - Includes language selector and all fixes

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

// ESSENTIAL 5 PARAMETER CATEGORIES ONLY - ratings 1-4
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
                'parameters.title': 'Daily Parameters',
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
'privacy.class_b': 'Class B (Close Friends)',
'privacy.class_a': 'Class A (Family)',
'privacy.private': 'Private',
                'error.loading': 'Error loading parameters'
            });
        }

        // Hebrew translations
        if (!window.i18n.translations.he['parameters.mood']) {
            Object.assign(window.i18n.translations.he, {
                'parameters.title': 'פרמטרים יומיים',
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
'privacy.class_b': 'מחלקה ב\' (חברים קרובים)',
'privacy.class_a': 'מחלקה א\' (משפחה)',
'privacy.private': 'פרטי',
                'error.loading': 'שגיאה בטעינת פרמטרים'
            });
        }

        // Arabic translations
        if (!window.i18n.translations.ar['parameters.mood']) {
            Object.assign(window.i18n.translations.ar, {
                'parameters.title': 'المعاملات اليومية',
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
'privacy.class_b': 'الفئة ب (الأصدقاء المقربون)',
'privacy.class_a': 'الفئة أ (العائلة)',
'privacy.private': 'خاص',
                'error.loading': 'خطأ في تحميل المعاملات'
            });
        }

        // Russian translations
        if (!window.i18n.translations.ru['parameters.mood']) {
            Object.assign(window.i18n.translations.ru, {
                'parameters.title': 'Ежедневные параметры',
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
'privacy.class_b': 'Класс Б (Близкие друзья)',
'privacy.class_a': 'Класс А (Семья)',
'privacy.private': 'Приватный',
                'error.loading': 'Ошибка загрузки параметров'
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

    // Set default privacy to private for all parameters
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
                <h1 data-i18n="parameters.title">Daily Parameters</h1>
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
                    <span class="parameter-description" data-i18n="${category.descriptionKey}">${category.descriptionKey}</span>
                </div>
                <div class="privacy-selector">
                  <select class="privacy-select"
        data-category="${category.id}"
        onchange="updatePrivacy('${category.id}', this.value)">
    <option value="private" ${privacy === 'private' ? 'selected' : ''}>
        🔒 Private
    </option>
    <option value="class_a" ${privacy === 'class_a' ? 'selected' : ''}>
        👨‍👩‍👧‍👦 Class A (Family)
    </option>
    <option value="class_b" ${privacy === 'class_b' ? 'selected' : ''}>
        👥 Class B (Friends)
    </option>
    <option value="public" ${privacy === 'public' ? 'selected' : ''}>
        🌍 Public
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

    // Setup language selector
    setupLanguageSelector();

    // Initialize calendar
    updateCalendar();


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
}

// Setup language selector
function setupLanguageSelector() {
    const selector = document.getElementById('languageSelector');
    if (!selector) return;

    // Get current language, defaulting to 'en' if nothing is set
    let currentLang = window.i18n?.getCurrentLanguage?.() || localStorage.getItem('userLanguage');

    // If no language is set anywhere, default to English
    if (!currentLang || currentLang === '') {
        currentLang = 'en';
        localStorage.setItem('userLanguage', 'en');
    }

    // Set the selector value
    selector.value = currentLang;

    // Force a re-render of the selector to ensure it displays properly
    setTimeout(() => {
        if (!selector.value || selector.value === '') {
            selector.value = 'en';
        }
        // Trigger a change event to update display
        selector.dispatchEvent(new Event('change', { bubbles: false }));
    }, 10);

    // Handle language change
    selector.addEventListener('change', function() {
        const newLang = this.value;

        // Save to localStorage
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

        // Send to server to save preference
        if (window.fetch) {
            fetch('/api/user/language', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ language: newLang })
            }).catch(err => console.error('Failed to save language preference:', err));
        }
    });

    // Set initial RTL direction based on current language
    const rtlLanguages = ['ar', 'he'];
    if (rtlLanguages.includes(currentLang)) {
        document.body.setAttribute('dir', 'rtl');
    } else {
        document.body.setAttribute('dir', 'ltr');
    }
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

    // Add day headers
    const dayHeaders = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
    dayHeaders.forEach(day => {
        const header = document.createElement('div');
        header.className = 'calendar-header';
        header.textContent = day;
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
        mood_privacy: window.selectedPrivacy.mood || 'public',
        energy_privacy: window.selectedPrivacy.energy || 'public',
        sleep_quality_privacy: window.selectedPrivacy.sleep_quality || 'public',
        physical_activity_privacy: window.selectedPrivacy.physical_activity || 'public',
        anxiety_privacy: window.selectedPrivacy.anxiety || 'public',
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
                const privacyValue = result.data[privacyKey] || result.data[param + '_privacy'] || 'public';

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
    mood_privacy: result.data.mood_privacy || 'public',
    energy_privacy: result.data.energy_privacy || 'public',
    sleep_quality_privacy: result.data.sleep_quality_privacy || 'public',
    physical_activity_privacy: result.data.physical_activity_privacy || 'public',
    anxiety_privacy: result.data.anxiety_privacy || 'public',
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

// Update translations dynamically
function updateTranslations() {
    if (!window.i18n) return;

    // Re-add translations in case language changed
    addParameterTranslations();

    // Update all translatable elements
    document.querySelectorAll('[data-i18n]').forEach(element => {
        const key = element.getAttribute('data-i18n');
        if (key) {
            element.textContent = pt(key);
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

console.log('Parameters-social.js loaded - FIXED VERSION with calendar display and no auto-loading');