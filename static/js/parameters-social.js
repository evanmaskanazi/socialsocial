// Social Parameters Save/Load System with i18n support and numeric ratings

// Translation function helper - renamed from 't' to 'pt' to avoid conflicts
const pt = (key) => window.i18n ? window.i18n.translate(key) : key;

// State management
let currentDate = new Date();
let selectedDate = new Date();
let savedDates = [];
let selectedRatings = {};

// Parameter categories - 5 total categories with descriptions
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

// Add translations for new parameters
const addParameterTranslations = () => {
    if (window.i18n && window.i18n.translations) {
        // English translations
        if (!window.i18n.translations.en['parameters.mood']) {
            Object.assign(window.i18n.translations.en, {
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
                'parameters.saved': 'Parameters saved successfully!',
                'parameters.loaded': 'Parameters loaded for',
                'parameters.cleared': 'Form cleared',
                'parameters.no_saved': 'No saved parameters for this date',
                'parameters.today_label': 'Today',
                'error.saving': 'Error saving parameters',
                'error.loading': 'Error loading parameters'
            });
        }

        // Hebrew translations
        if (!window.i18n.translations.he['parameters.mood']) {
            Object.assign(window.i18n.translations.he, {
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
                'parameters.saved': 'הפרמטרים נשמרו בהצלחה!',
                'parameters.loaded': 'פרמטרים נטענו עבור',
                'parameters.cleared': 'הטופס נוקה',
                'parameters.no_saved': 'אין פרמטרים שמורים לתאריך זה',
                'parameters.today_label': 'היום',
                'error.saving': 'שגיאה בשמירת פרמטרים',
                'error.loading': 'שגיאה בטעינת פרמטרים'
            });
        }

        // Arabic translations
        if (!window.i18n.translations.ar['parameters.mood']) {
            Object.assign(window.i18n.translations.ar, {
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
                'parameters.saved': 'تم حفظ المعاملات بنجاح!',
                'parameters.loaded': 'تم تحميل المعاملات لـ',
                'parameters.cleared': 'تم مسح النموذج',
                'parameters.no_saved': 'لا توجد معاملات محفوظة لهذا التاريخ',
                'parameters.today_label': 'اليوم',
                'error.saving': 'خطأ في حفظ المعاملات',
                'error.loading': 'خطأ في تحميل المعاملات'
            });
        }

        // Russian translations
        if (!window.i18n.translations.ru['parameters.mood']) {
            Object.assign(window.i18n.translations.ru, {
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
                'parameters.saved': 'Параметры успешно сохранены!',
                'parameters.loaded': 'Параметры загружены для',
                'parameters.cleared': 'Форма очищена',
                'parameters.no_saved': 'Нет сохраненных параметров для этой даты',
                'parameters.today_label': 'Сегодня',
                'error.saving': 'Ошибка сохранения параметров',
                'error.loading': 'Ошибка загрузки параметров'
            });
        }

        // Also add month translations if missing
        const months = ['january', 'february', 'march', 'april', 'may', 'june',
                       'july', 'august', 'september', 'october', 'november', 'december'];

        months.forEach((month, index) => {
            const key = `month.${month}`;
            if (!window.i18n.translations.en[key]) {
                window.i18n.translations.en[key] = month.charAt(0).toUpperCase() + month.slice(1);
            }
        });

        // Add day translations if missing
        const days = ['sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat'];
        const dayTranslations = {
            en: ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'],
            he: ['א', 'ב', 'ג', 'ד', 'ה', 'ו', 'ש'],
            ar: ['الأحد', 'الإثنين', 'الثلاثاء', 'الأربعاء', 'الخميس', 'الجمعة', 'السبت'],
            ru: ['Вс', 'Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб']
        };

        Object.keys(dayTranslations).forEach(lang => {
            days.forEach((day, index) => {
                const key = `day.${day}`;
                if (!window.i18n.translations[lang][key]) {
                    window.i18n.translations[lang][key] = dayTranslations[lang][index];
                }
            });
        });
    }
};

// Initialize parameters page
function initializeParameters() {
    addParameterTranslations();
    const container = document.getElementById('parametersContainer');
    if (container) {
        container.innerHTML = generateParametersHTML();
        initializeCalendar();
    }
}

// Generate the HTML structure with embedded styles (like original approach)
function generateParametersHTML() {
    return `
        <div class="parameters-container">
            <style>
                .parameters-container {
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 20px;
                }

                .calendar-section {
                    background: white;
                    border-radius: 15px;
                    padding: 20px;
                    margin-bottom: 30px;
                    box-shadow: 0 4px 10px rgba(0,0,0,0.1);
                }

                .calendar-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 20px;
                    padding-bottom: 15px;
                    border-bottom: 2px solid #f0f0f0;
                }

                .calendar-title {
                    font-size: 1.5em;
                    color: #2d3436;
                    font-weight: 600;
                }

                .calendar-navigation {
                    display: flex;
                    gap: 10px;
                }

                .calendar-nav-btn {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    border: none;
                    padding: 8px 15px;
                    border-radius: 8px;
                    cursor: pointer;
                    transition: all 0.3s;
                }

                .calendar-nav-btn:hover {
                    transform: scale(1.05);
                }

                #currentMonth {
                    min-width: 150px;
                    text-align: center;
                    font-weight: 600;
                }

                .calendar-grid {
                    display: grid;
                    grid-template-columns: repeat(7, 1fr);
                    gap: 5px;
                }

                .calendar-day {
                    aspect-ratio: 1;
                    border: 1px solid #e1e8ed;
                    border-radius: 8px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    cursor: pointer;
                    transition: all 0.3s;
                    position: relative;
                }

                .calendar-day:hover {
                    background: #f8f9fa;
                }

                .calendar-day.selected {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                }

                .calendar-day.has-data::after {
                    content: '•';
                    position: absolute;
                    bottom: 5px;
                    color: #4caf50;
                    font-size: 20px;
                }

                .day-label {
                    font-weight: 600;
                    color: #667eea;
                    text-align: center;
                    padding: 10px;
                }

                .parameters-form {
                    background: white;
                    border-radius: 15px;
                    padding: 25px;
                    box-shadow: 0 4px 10px rgba(0,0,0,0.1);
                }

                .selected-date-display {
                    text-align: center;
                    padding: 15px;
                    background: #f8f9fa;
                    border-radius: 10px;
                    margin-bottom: 20px;
                    color: #667eea;
                    font-weight: 600;
                }

                /* Rating styles similar to daily check-in */
                .rating-category {
                    margin-bottom: 20px;
                }

                .category-header {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    margin-bottom: 5px;
                }

                .category-emoji {
                    font-size: 20px;
                }

                .category-name {
                    font-weight: 600;
                    color: #333;
                }

                .category-description {
                    color: #666;
                    font-size: 0.9em;
                    margin-left: 28px;
                    margin-bottom: 10px;
                }

                .rating-scale {
                    display: flex;
                    gap: 10px;
                }

                .rating-button {
                    flex: 1;
                    padding: 12px;
                    border: 2px solid #e1e8ed;
                    background: white;
                    border-radius: 8px;
                    cursor: pointer;
                    transition: all 0.3s;
                    text-align: center;
                }

                .rating-button:hover {
                    border-color: #667eea;
                    background: #f8f9fa;
                }

                .rating-button.selected {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    border-color: transparent;
                }

                .rating-value {
                    font-size: 1.2em;
                    font-weight: 600;
                }

                .notes-textarea {
                    width: 100%;
                    padding: 12px;
                    border: 2px solid #e1e8ed;
                    border-radius: 10px;
                    font-size: 16px;
                    min-height: 100px;
                    resize: vertical;
                    transition: all 0.3s;
                }

                .notes-textarea:focus {
                    outline: none;
                    border-color: #667eea;
                }

                .parameter-actions {
                    display: flex;
                    gap: 15px;
                    justify-content: center;
                    margin-top: 30px;
                }

                .btn-primary,
                .btn-secondary {
                    padding: 12px 30px;
                    border: none;
                    border-radius: 25px;
                    font-size: 16px;
                    font-weight: 600;
                    cursor: pointer;
                    transition: all 0.3s;
                }

                .btn-primary {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                }

                .btn-primary:hover {
                    transform: scale(1.05);
                    box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
                }

                .btn-secondary {
                    background: white;
                    color: #667eea;
                    border: 2px solid #667eea;
                }

                .btn-secondary:hover {
                    background: #f8f9fa;
                }

                /* Message Container */
                #messageContainer {
                    position: fixed;
                    top: 20px;
                    left: 50%;
                    transform: translateX(-50%);
                    z-index: 10000;
                    max-width: 90%;
                }

                .message {
                    padding: 15px 25px;
                    border-radius: 10px;
                    margin-bottom: 10px;
                    animation: slideDown 0.5s ease;
                    box-shadow: 0 4px 15px rgba(0,0,0,0.1);
                }

                .message.success {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                }

                .message.error {
                    background: #f5576c;
                    color: white;
                }

                .message.info {
                    background: #4facfe;
                    color: white;
                }

                /* Flashy positive message style */
                .message.flashy {
                    background: linear-gradient(270deg, #ff6b6b, #ffd93d, #6bcf7f, #4ecdc4, #667eea, #a561e8);
                    background-size: 1200% 100%;
                    animation: gradientShift 3s ease infinite, pulse 1s ease infinite;
                    padding: 25px 40px;
                    font-size: 1.3rem;
                    font-weight: 700;
                    text-align: center;
                    border-radius: 20px;
                    box-shadow: 0 10px 40px rgba(102, 126, 234, 0.4);
                    min-width: 500px;
                }

                .flashy-content {
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    gap: 15px;
                }

                .flashy-icon {
                    font-size: 2rem;
                    animation: spin 2s linear infinite;
                }

                @keyframes gradientShift {
                    0% { background-position: 0% 50%; }
                    50% { background-position: 100% 50%; }
                    100% { background-position: 0% 50%; }
                }

                @keyframes pulse {
                    0%, 100% { transform: scale(1); }
                    50% { transform: scale(1.05); }
                }

                @keyframes spin {
                    from { transform: rotate(0deg); }
                    to { transform: rotate(360deg); }
                }

                @keyframes slideDown {
                    from { opacity: 0; transform: translateY(-20px); }
                    to { opacity: 1; transform: translateY(0); }
                }

                @keyframes slideIn {
                    from { opacity: 0; transform: translateX(-50%) translateY(-20px); }
                    to { opacity: 1; transform: translateX(-50%) translateY(0); }
                }

                @keyframes fadeOut {
                    from { opacity: 1; transform: translateY(0); }
                    to { opacity: 0; transform: translateY(-20px); }
                }

                @media (max-width: 768px) {
                    .flashy-text {
                        font-size: 1.2rem;
                    }
                    .flashy-icon {
                        font-size: 1.5rem;
                    }
                    .message.flashy {
                        min-width: 90%;
                    }
                }
            </style>

            <!-- Message Container -->
            <div id="messageContainer"></div>

            <div class="calendar-section">
            <div class="calendar-header">
                <div class="calendar-title" data-i18n="parameters.select_date">${pt('parameters.select_date')}</div>
                <div class="calendar-navigation">
                    <button class="calendar-nav-btn" onclick="previousMonth()">←</button>
                    <span id="currentMonth">January 2025</span>
                    <button class="calendar-nav-btn" onclick="nextMonth()">→</button>
                </div>
            </div>

            <div class="calendar-grid" id="calendarGrid">
                <!-- Days of week headers -->
                <div class="day-label" data-i18n="day.sun">${pt('day.sun')}</div>
                <div class="day-label" data-i18n="day.mon">${pt('day.mon')}</div>
                <div class="day-label" data-i18n="day.tue">${pt('day.tue')}</div>
                <div class="day-label" data-i18n="day.wed">${pt('day.wed')}</div>
                <div class="day-label" data-i18n="day.thu">${pt('day.thu')}</div>
                <div class="day-label" data-i18n="day.fri">${pt('day.fri')}</div>
                <div class="day-label" data-i18n="day.sat">${pt('day.sat')}</div>
                <!-- Calendar days will be inserted here -->
            </div>
        </div>

        <!-- Parameters Form -->
        <div class="parameters-form">
            <div id="selectedDateDisplay" class="selected-date-display">
                ${pt('parameters.today_label')}
            </div>

            <!-- Rating Categories -->
            <div id="ratingCategories">
                <!-- Categories will be generated dynamically -->
            </div>

            <!-- Notes Section -->
            <div class="notes-section">
                <label class="notes-label" data-i18n="parameters.notes">${pt('parameters.notes')}</label>
                <textarea
                    id="notesInput"
                    class="notes-textarea"
                    placeholder="${pt('parameters.notes_placeholder')}"
                    data-i18n-placeholder="parameters.notes_placeholder"
                ></textarea>
            </div>

            <!-- Action Buttons -->
            <div class="parameter-actions">
                <button class="btn-primary" onclick="saveParameters()" data-i18n="parameters.save">
                    ${pt('parameters.save')}
                </button>
                <button class="btn-secondary" onclick="loadParameters()" data-i18n="parameters.load">
                    ${pt('parameters.load')}
                </button>
                <button class="btn-secondary" onclick="clearParameters()" data-i18n="parameters.clear">
                    ${pt('parameters.clear')}
                </button>
            </div>
        </div>
        </div> <!-- Close parameters-container -->
    `;
}

// Initialize calendar and load saved dates
async function initializeCalendar() {
    await loadSavedDates();
    renderCalendar();
    renderRatingCategories();
    updateSelectedDateDisplay();
}

// Load saved dates from server
async function loadSavedDates() {
    try {
        const response = await fetch('/api/parameters/dates');
        if (response.ok) {
            const data = await response.json();
            savedDates = data.dates || [];
        }
    } catch (error) {
        console.error('Error loading saved dates:', error);
    }
}

// Render the calendar
function renderCalendar() {
    const year = currentDate.getFullYear();
    const month = currentDate.getMonth();

    // Update month display
    const monthNames = [
        pt('month.january'), pt('month.february'), pt('month.march'),
        pt('month.april'), pt('month.may'), pt('month.june'),
        pt('month.july'), pt('month.august'), pt('month.september'),
        pt('month.october'), pt('month.november'), pt('month.december')
    ];

    const monthDisplay = document.getElementById('currentMonth');
    if (monthDisplay) {
        monthDisplay.textContent = `${monthNames[month]} ${year}`;
    }

    // Get first day of month and number of days
    const firstDay = new Date(year, month, 1).getDay();
    const daysInMonth = new Date(year, month + 1, 0).getDate();

    // Build calendar grid
    const grid = document.getElementById('calendarGrid');
    if (!grid) return;

    // Keep the day labels
    const dayLabels = grid.querySelectorAll('.day-label');
    const dayLabelsHTML = Array.from(dayLabels).map(label => label.outerHTML).join('');

    grid.innerHTML = dayLabelsHTML;

    // Add empty cells for days before month starts
    for (let i = 0; i < firstDay; i++) {
        const emptyCell = document.createElement('div');
        grid.appendChild(emptyCell);
    }

    // Add days of month
    for (let day = 1; day <= daysInMonth; day++) {
        const dayCell = document.createElement('div');
        dayCell.className = 'calendar-day';
        dayCell.textContent = day;

        const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;

        // Check if this date has saved data
        if (savedDates.includes(dateStr)) {
            dayCell.classList.add('has-data');
        }

        // Check if this is the selected date
        if (selectedDate.getDate() === day &&
            selectedDate.getMonth() === month &&
            selectedDate.getFullYear() === year) {
            dayCell.classList.add('selected');
        }

        dayCell.onclick = () => selectDate(year, month, day);
        grid.appendChild(dayCell);
    }
}

// Render rating categories
function renderRatingCategories() {
    const container = document.getElementById('ratingCategories');
    if (!container) return;

    container.innerHTML = '';

    PARAMETER_CATEGORIES.forEach(category => {
        const categoryDiv = document.createElement('div');
        categoryDiv.className = 'rating-category';

        // Category header
        const headerDiv = document.createElement('div');
        headerDiv.className = 'category-header';

        const emojiSpan = document.createElement('span');
        emojiSpan.className = 'category-emoji';
        emojiSpan.textContent = category.emoji;

        const nameSpan = document.createElement('span');
        nameSpan.className = 'category-name';
        nameSpan.setAttribute('data-i18n', category.nameKey);
        nameSpan.textContent = pt(category.nameKey);

        headerDiv.appendChild(emojiSpan);
        headerDiv.appendChild(nameSpan);

        // Category description
        const descDiv = document.createElement('div');
        descDiv.className = 'category-description';
        descDiv.setAttribute('data-i18n', category.descriptionKey);
        descDiv.textContent = pt(category.descriptionKey);

        // Rating scale
        const scaleDiv = document.createElement('div');
        scaleDiv.className = 'rating-scale';

        for (let i = category.min; i <= category.max; i++) {
            const button = document.createElement('button');
            button.type = 'button';
            button.className = 'rating-button';
            button.dataset.category = category.id;
            button.dataset.value = i;
            button.onclick = () => selectRating(category.id, i);

            const valueSpan = document.createElement('span');
            valueSpan.className = 'rating-value';
            valueSpan.textContent = i;

            button.appendChild(valueSpan);
            scaleDiv.appendChild(button);
        }

        categoryDiv.appendChild(headerDiv);
        categoryDiv.appendChild(descDiv);
        categoryDiv.appendChild(scaleDiv);

        container.appendChild(categoryDiv);
    });
}

// Select a rating
function selectRating(categoryId, value) {
    selectedRatings[categoryId] = value;

    // Update button states
    document.querySelectorAll(`.rating-button[data-category="${categoryId}"]`).forEach(btn => {
        btn.classList.remove('selected');
        if (parseInt(btn.dataset.value) === value) {
            btn.classList.add('selected');
        }
    });
}

// Select a date
function selectDate(year, month, day) {
    selectedDate = new Date(year, month, day);
    renderCalendar();
    updateSelectedDateDisplay();

    // Clear current selections
    clearParameters(false);

    // Load parameters for this date
    loadParameters(false);
}

// Update selected date display
function updateSelectedDateDisplay() {
    const display = document.getElementById('selectedDateDisplay');
    if (!display) return;

    const dateStr = selectedDate.toLocaleDateString();
    const today = new Date();
    const isToday = selectedDate.toDateString() === today.toDateString();

    display.textContent = isToday ? `${pt('parameters.today_label')} (${dateStr})` : dateStr;
}

// Navigate months
function previousMonth() {
    currentDate.setMonth(currentDate.getMonth() - 1);
    renderCalendar();
}

function nextMonth() {
    currentDate.setMonth(currentDate.getMonth() + 1);
    renderCalendar();
}

// Save parameters
async function saveParameters() {
    const dateStr = selectedDate.toISOString().split('T')[0];

    const parameters = {
        date: dateStr,
        mood: selectedRatings.mood || null,
        energy: selectedRatings.energy || null,
        sleep_quality: selectedRatings.sleep_quality || null,
        physical_activity: selectedRatings.physical_activity || null,
        anxiety: selectedRatings.anxiety || null,
        notes: document.getElementById('notesInput').value || ''
    };

    try {
        const response = await fetch('/api/parameters/save', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(parameters)
        });

        if (response.ok) {
            const result = await response.json();

            // Show flashy positive message and scroll to top
            showMessage(getRandomPositiveMessage(), 'success', 10000, true);

            // Reload saved dates to update calendar
            await loadSavedDates();
            renderCalendar();
        } else {
            showMessage(pt('error.saving'), 'error', 5000, false);
        }
    } catch (error) {
        console.error('Error saving parameters:', error);
        showMessage(pt('error.saving'), 'error', 5000, false);
    }
}

// Load parameters
async function loadParameters(showMsg = true) {
    const dateStr = selectedDate.toISOString().split('T')[0];

    try {
        const response = await fetch(`/api/parameters/load/${dateStr}`);
        const result = await response.json();

        if (result.success && result.data) {
            const data = result.data;

            // Load ratings
            selectedRatings = {};
            PARAMETER_CATEGORIES.forEach(category => {
                const value = data[category.id];
                if (value) {
                    selectedRatings[category.id] = parseInt(value);
                    selectRating(category.id, parseInt(value));
                }
            });

            // Load notes
            const notesInput = document.getElementById('notesInput');
            if (notesInput) {
                notesInput.value = data.notes || '';
            }

            if (showMsg) {
                showMessage(`${pt('parameters.loaded')} ${dateStr}`, 'success', 5000, false);
            }
        } else if (showMsg) {
            showMessage(result.message || pt('parameters.no_saved'), 'info', 5000, false);
        }
    } catch (error) {
        console.error('Error loading parameters:', error);
        if (showMsg) {
            showMessage(pt('error.loading'), 'error', 5000, false);
        }
    }
}

// Clear parameters
function clearParameters(showMsg = true) {
    selectedRatings = {};

    // Clear all selections
    document.querySelectorAll('.rating-button').forEach(button => {
        button.classList.remove('selected');
    });

    // Clear notes
    const notesInput = document.getElementById('notesInput');
    if (notesInput) {
        notesInput.value = '';
    }

    if (showMsg) {
        showMessage(pt('parameters.cleared'), 'info', 3000, false);
    }
}

// Update translations when language changes
function updateTranslations() {
    // Re-render rating categories with new translations
    renderRatingCategories();

    // Update month display
    renderCalendar();

    // Update date display
    updateSelectedDateDisplay();

    // Restore selected ratings
    Object.keys(selectedRatings).forEach(categoryId => {
        selectRating(categoryId, selectedRatings[categoryId]);
    });
}

// Get random positive message in current language
function getRandomPositiveMessage() {
    const messages = {
        'en': [
            "Amazing work! You're tracking your wellness journey beautifully! 💪",
            "Fantastic job! Your dedication to self-awareness is inspiring! ⭐",
            "Wonderful! Every parameter logged is a step towards understanding yourself better! 🌈",
            "Brilliant! You're building valuable insights about your wellbeing! 🎯",
            "Outstanding! Your consistency in tracking is your superpower! 🦸",
            "Excellent! You're creating a meaningful record of your progress! 📈",
            "Superb! Your commitment to self-care shines through! ✨",
            "Marvelous! You're taking charge of your wellness journey! 🌟",
            "Spectacular! Keep up this amazing self-awareness practice! 🚀",
            "Phenomenal! You're writing your wellness story, one day at a time! 📖"
        ],
        'he': [
            "עבודה מדהימה! אתה עוקב אחר מסע הבריאות שלך בצורה יפהפייה! 💪",
            "עבודה פנטסטית! המסירות שלך למודעות עצמית מעוררת השראה! ⭐",
            "נפלא! כל פרמטר שנרשם הוא צעד להבנה טובה יותר של עצמך! 🌈",
            "מבריק! אתה בונה תובנות חשובות על הרווחה שלך! 🎯",
            "יוצא מן הכלל! העקביות שלך במעקב היא כוח העל שלך! 🦸",
            "מצוין! אתה יוצר תיעוד משמעותי של ההתקדמות שלך! 📈",
            "נהדר! המחויבות שלך לטיפול עצמי זוהרת! ✨",
            "מדהים! אתה לוקח אחריות על מסע הבריאות שלך! 🌟",
            "מרהיב! המשך בתרגול המדהים הזה של מודעות עצמית! 🚀",
            "פנומנלי! אתה כותב את סיפור הבריאות שלך, יום אחר יום! 📖"
        ],
        'ar': [
            "عمل رائع! أنت تتابع رحلتك الصحية بشكل جميل! 💪",
            "عمل رائع! إخلاصك للوعي الذاتي ملهم! ⭐",
            "رائع! كل معامل مسجل هو خطوة نحو فهم نفسك بشكل أفضل! 🌈",
            "ممتاز! أنت تبني رؤى قيمة حول رفاهيتك! 🎯",
            "متميز! ثباتك في التتبع هو قوتك الخارقة! 🦸",
            "ممتاز! أنت تخلق سجلاً ذا معنى لتقدمك! 📈",
            "رائع! التزامك بالعناية الذاتية يتألق! ✨",
            "مذهل! أنت تتولى مسؤولية رحلتك الصحية! 🌟",
            "مذهل! استمر في هذه الممارسة المذهلة للوعي الذاتي! 🚀",
            "استثنائي! أنت تكتب قصة عافيتك، يومًا بعد يوم! 📖"
        ],
        'ru': [
            "Потрясающая работа! Вы прекрасно отслеживаете свой путь к здоровью! 💪",
            "Фантастическая работа! Ваша преданность самосознанию вдохновляет! ⭐",
            "Замечательно! Каждый записанный параметр - это шаг к лучшему пониманию себя! 🌈",
            "Блестяще! Вы создаете ценные инсайты о своем благополучии! 🎯",
            "Выдающийся результат! Ваша последовательность в отслеживании - это ваша суперсила! 🦸",
            "Превосходно! Вы создаете значимую запись своего прогресса! 📈",
            "Великолепно! Ваша приверженность заботе о себе сияет! ✨",
            "Чудесно! Вы берете ответственность за свой путь к здоровью! 🌟",
            "Впечатляюще! Продолжайте эту удивительную практику самосознания! 🚀",
            "Феноменально! Вы пишете свою историю благополучия, день за днем! 📖"
        ]
    };

    const lang = window.i18n ? window.i18n.getCurrentLanguage() : 'en';
    const langMessages = messages[lang] || messages['en'];
    return langMessages[Math.floor(Math.random() * langMessages.length)];
}

// Show message with optional flashy style
function showMessage(text, type = 'success', duration = 5000, isFlashy = false) {
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

        // Scroll to top to see the message
        window.scrollTo({ top: 0, behavior: 'smooth' });
    } else {
        messageDiv.textContent = text;
    }

    container.appendChild(messageDiv);

    setTimeout(() => {
        messageDiv.style.animation = 'fadeOut 0.5s ease-out';
        setTimeout(() => messageDiv.remove(), 500);
    }, duration);
}

// Initialize when DOM is ready (backup initialization)
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