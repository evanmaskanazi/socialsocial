// Social Parameters Save/Load System


const parametersEnhancedHTML = `
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
        
        .calendar-grid {
            display: grid;
            grid-template-columns: repeat(7, 1fr);
            gap: 5px;
            margin-bottom: 20px;
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
        
        .parameter-group {
            margin-bottom: 25px;
        }
        
        .parameter-label {
            display: block;
            color: #2d3436;
            font-weight: 600;
            margin-bottom: 10px;
            font-size: 1.1em;
        }
        
        .parameter-input-wrapper {
            position: relative;
        }
        
        .parameter-input {
            width: 100%;
            padding: 12px;
            border: 2px solid #e1e8ed;
            border-radius: 10px;
            font-size: 16px;
            transition: all 0.3s;
        }
        
        .parameter-input:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        
        .sleep-input-group {
            display: flex;
            align-items: center;
            gap: 15px;
        }
        
        .sleep-number {
            width: 100px;
        }
        
        .sleep-display {
            font-size: 1.2em;
            color: #667eea;
            font-weight: 600;
        }
        
        .mood-options {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
            gap: 10px;
        }
        
        .mood-option {
            padding: 10px 20px;
            border: 2px solid #e1e8ed;
            border-radius: 10px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .mood-option:hover {
            border-color: #667eea;
            background: #f8f9fa;
        }
        
        .mood-option.selected {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border-color: transparent;
        }
        
        .parameter-textarea {
            width: 100%;
            padding: 12px;
            border: 2px solid #e1e8ed;
            border-radius: 10px;
            font-size: 16px;
            min-height: 100px;
            resize: vertical;
            font-family: inherit;
            transition: all 0.3s;
        }
        
        .parameter-textarea:focus {
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
        
        .load-date-display {
            text-align: center;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 10px;
            margin-bottom: 20px;
            color: #667eea;
            font-weight: 600;
        }
    </style>
    
    <div class="calendar-section">
        <div class="calendar-header">
            <div class="calendar-title">Select Date</div>
            <div class="calendar-navigation">
                <button class="calendar-nav-btn" onclick="previousMonth()">←</button>
                <span id="currentMonth" style="min-width: 150px; text-align: center; font-weight: 600;">January 2025</span>
                <button class="calendar-nav-btn" onclick="nextMonth()">→</button>
            </div>
        </div>
        
        <div class="calendar-grid" id="calendarGrid">
            <!-- Days of week -->
            <div class="day-label">Sun</div>
            <div class="day-label">Mon</div>
            <div class="day-label">Tue</div>
            <div class="day-label">Wed</div>
            <div class="day-label">Thu</div>
            <div class="day-label">Fri</div>
            <div class="day-label">Sat</div>
            <!-- Calendar days will be inserted here -->
        </div>
        
        <div class="load-date-display" id="loadDateDisplay">
            Current Date: <span id="selectedDateDisplay">Today</span>
        </div>
    </div>
    
    <div class="parameters-form">
        <h2 style="color: #667eea; margin-bottom: 25px; text-align: center;">Daily Parameters</h2>
        
        <div class="parameter-group">
            <label class="parameter-label">Mood</label>
            <div class="parameter-input-wrapper">
                <input type="text" class="parameter-input" id="moodInput" 
                       placeholder="How are you feeling? (e.g., Happy, Calm, Anxious, etc.)">
            </div>
            <div class="mood-options" style="margin-top: 10px;">
                <div class="mood-option" onclick="selectMood('Happy')">😊 Happy</div>
                <div class="mood-option" onclick="selectMood('Calm')">😌 Calm</div>
                <div class="mood-option" onclick="selectMood('Anxious')">😰 Anxious</div>
                <div class="mood-option" onclick="selectMood('Sad')">😢 Sad</div>
                <div class="mood-option" onclick="selectMood('Energetic')">🔥 Energetic</div>
                <div class="mood-option" onclick="selectMood('Tired')">😴 Tired</div>
            </div>
        </div>
        
        <div class="parameter-group">
            <label class="parameter-label">Sleep</label>
            <div class="sleep-input-group">
                <input type="number" class="parameter-input sleep-number" id="sleepHours" 
                       min="0" max="24" step="0.5" placeholder="0" onchange="updateSleepDisplay()">
                <span class="sleep-display" id="sleepDisplay">0 Hours</span>
            </div>
        </div>
        
        <div class="parameter-group">
            <label class="parameter-label">Exercise</label>
            <div class="parameter-input-wrapper">
                <input type="text" class="parameter-input" id="exerciseInput" 
                       placeholder="What exercise did you do? (e.g., Running, Yoga, Gym, Walking)">
            </div>
        </div>
        
        <div class="parameter-group">
            <label class="parameter-label">Anxiety Level</label>
            <div class="parameter-input-wrapper">
                <input type="text" class="parameter-input" id="anxietyInput" 
                       placeholder="Describe your anxiety level (e.g., None, Mild, Moderate, Severe)">
            </div>
        </div>
        
        <div class="parameter-group">
            <label class="parameter-label">Energy Level</label>
            <div class="parameter-input-wrapper">
                <input type="text" class="parameter-input" id="energyInput" 
                       placeholder="Describe your energy level (e.g., Very Low, Low, Normal, High, Very High)">
            </div>
        </div>
        
        <div class="parameter-group">
            <label class="parameter-label">Notes</label>
            <textarea class="parameter-textarea" id="notesInput" 
                      placeholder="Any additional notes or thoughts for today..."></textarea>
        </div>
        
        <div class="parameter-actions">
            <button class="btn-primary" onclick="saveParameters()">Save Parameters</button>
            <button class="btn-secondary" onclick="loadParameters()">Load Parameters</button>
            <button class="btn-secondary" onclick="clearParameters()">Clear</button>
        </div>
    </div>
</div>
`;

// Calendar and Parameters JavaScript
let currentDate = new Date();
let selectedDate = new Date();
let savedDates = [];

async function initializeCalendar() {
    await loadSavedDates();
    renderCalendar();
    updateSelectedDateDisplay();
}

async function loadSavedDates() {
    try {
        const response = await fetch('/api/parameters/dates');
        if (response.ok) {
            const data = await response.json();
            savedDates = data.dates;
        }
    } catch (error) {
        console.error('Error loading saved dates:', error);
    }
}

function renderCalendar() {
    const year = currentDate.getFullYear();
    const month = currentDate.getMonth();
    
    // Update month display
    const monthNames = ['January', 'February', 'March', 'April', 'May', 'June',
                        'July', 'August', 'September', 'October', 'November', 'December'];
    document.getElementById('currentMonth').textContent = `${monthNames[month]} ${year}`;
    
    // Get first day of month and number of days
    const firstDay = new Date(year, month, 1).getDay();
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    
    // Build calendar grid
    const grid = document.getElementById('calendarGrid');
    // Keep the day labels
    const dayLabels = grid.querySelectorAll('.day-label');
    grid.innerHTML = '';
    dayLabels.forEach(label => grid.appendChild(label));
    
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

function selectDate(year, month, day) {
    selectedDate = new Date(year, month, day);
    renderCalendar();
    updateSelectedDateDisplay();
}

function updateSelectedDateDisplay() {
    const dateStr = selectedDate.toLocaleDateString('en-US', {
        weekday: 'long',
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });
    
    const today = new Date();
    const isToday = selectedDate.toDateString() === today.toDateString();
    
    document.getElementById('selectedDateDisplay').textContent = 
        isToday ? `Today (${dateStr})` : dateStr;
}

function previousMonth() {
    currentDate.setMonth(currentDate.getMonth() - 1);
    renderCalendar();
}

function nextMonth() {
    currentDate.setMonth(currentDate.getMonth() + 1);
    renderCalendar();
}

function selectMood(mood) {
    document.getElementById('moodInput').value = mood;
    
    // Update visual selection
    document.querySelectorAll('.mood-option').forEach(option => {
        option.classList.remove('selected');
        if (option.textContent.includes(mood)) {
            option.classList.add('selected');
        }
    });
}

function updateSleepDisplay() {
    const hours = document.getElementById('sleepHours').value || 0;
    const hoursText = hours == 1 ? 'Hour' : 'Hours';
    document.getElementById('sleepDisplay').textContent = `${hours} ${hoursText}`;
}

async function saveParameters() {
    const dateStr = selectedDate.toISOString().split('T')[0];
    
    const parameters = {
        date: dateStr,
        mood: document.getElementById('moodInput').value,
        sleep_hours: parseFloat(document.getElementById('sleepHours').value) || 0,
        exercise: document.getElementById('exerciseInput').value,
        anxiety: document.getElementById('anxietyInput').value,
        energy: document.getElementById('energyInput').value,
        notes: document.getElementById('notesInput').value
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
            showNotification(result.message, 'success');
            
            // Reload saved dates to update calendar
            await loadSavedDates();
            renderCalendar();
        } else {
            showNotification('Error saving parameters', 'error');
        }
    } catch (error) {
        console.error('Error saving parameters:', error);
        showNotification('Error saving parameters', 'error');
    }
}

async function loadParameters() {
    const dateStr = selectedDate.toISOString().split('T')[0];
    
    try {
        const response = await fetch(`/api/parameters/load/${dateStr}`);
        const result = await response.json();
        
        if (result.success) {
            const data = result.data;
            
            // Load values into form
            document.getElementById('moodInput').value = data.mood;
            document.getElementById('sleepHours').value = data.sleep_hours;
            document.getElementById('exerciseInput').value = data.exercise;
            document.getElementById('anxietyInput').value = data.anxiety;
            document.getElementById('energyInput').value = data.energy;
            document.getElementById('notesInput').value = data.notes;
            
            // Update sleep display
            updateSleepDisplay();
            
            // Update mood selection
            if (data.mood) {
                selectMood(data.mood);
            }
            
            showNotification(`Loaded parameters from ${dateStr}`, 'success');
        } else {
            showNotification(result.message || 'No saved parameters for this date', 'info');
        }
    } catch (error) {
        console.error('Error loading parameters:', error);
        showNotification('Error loading parameters', 'error');
    }
}

function clearParameters() {
    document.getElementById('moodInput').value = '';
    document.getElementById('sleepHours').value = '';
    document.getElementById('exerciseInput').value = '';
    document.getElementById('anxietyInput').value = '';
    document.getElementById('energyInput').value = '';
    document.getElementById('notesInput').value = '';
    
    // Clear visual selections
    document.querySelectorAll('.mood-option').forEach(option => {
        option.classList.remove('selected');
    });
    
    updateSleepDisplay();
    showNotification('Parameters cleared', 'info');
}

function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    
    let background;
    switch(type) {
        case 'success':
            background = 'linear-gradient(135deg, #4caf50 0%, #45a049 100%)';
            break;
        case 'error':
            background = 'linear-gradient(135deg, #f44336 0%, #d32f2f 100%)';
            break;
        default:
            background = 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)';
    }
    
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 15px 25px;
        background: ${background};
        color: white;
        border-radius: 10px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        z-index: 10000;
        animation: slideIn 0.3s ease;
    `;
    notification.textContent = message;
    document.body.appendChild(notification);
    
    setTimeout(() => notification.remove(), 3000);
}

// Initialize when page loads
document.addEventListener('DOMContentLoaded', () => {
    // Check if we're on the parameters page
    if (document.getElementById('parametersContainer')) {
        document.getElementById('parametersContainer').innerHTML = parametersEnhancedHTML;
        initializeCalendar();
    }
});
