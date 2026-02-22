// Complete Trigger Management System for TheraSocial
// triggers.js - Full Implementation
// Version Lang - Replaced all hardcoded English strings with i18n translation keys

class TriggerManager {
    constructor() {
        this.triggers = [];
        this.followedUsers = [];
        this.initialized = false;
    }

    // Translation helper with fallback
    t(key, fallback) {
        return (window.i18n && window.i18n.translate) ? (window.i18n.translate(key) || fallback) : (fallback || key);
    }

    async init() {
        if (this.initialized) return;

        try {
            await this.loadFollowedUsers();
            await this.loadTriggers();
            this.render();
            this.initialized = true;
        } catch (error) {
            console.error('Error initializing trigger manager:', error);
        }
    }

    async loadFollowedUsers() {
        try {
            // Get list of users being followed
            const response = await fetch('/api/users/following', {
                credentials: 'include'
            });

            if (response.ok) {
                const data = await response.json();
                this.followedUsers = data.users || [];
            } else {
                // If endpoint doesn't exist yet, try alternate approach
                this.followedUsers = [];
            }
        } catch (error) {
            console.error('Error loading followed users:', error);
            this.followedUsers = [];
        }
    }

    async loadTriggers() {
        try {
            const response = await fetch('/api/triggers', {
                credentials: 'include'
            });

            if (response.ok) {
                const data = await response.json();
                this.triggers = data.triggers || [];
            } else {
                this.triggers = [];
            }
        } catch (error) {
            console.error('Error loading triggers:', error);
            this.triggers = [];
        }
    }

    render() {
        const container = document.getElementById('triggers-container');
        if (!container) return;

        container.innerHTML = `
            <div class="triggers-section">
                <div class="section-header">
                    <h2>${this.t('triggers.care_title', 'Care Triggers')}</h2>
                    <p class="section-subtitle">${this.t('triggers.care_subtitle', 'Get notified when people you care about need support')}</p>
                </div>

                <div class="add-trigger-form">
                    <h3>${this.t('triggers.add_new', 'Add New Trigger')}</h3>

                    <div class="form-row">
                        <div class="form-group">
                            <label for="trigger-user">${this.t('triggers.person_to_watch', 'Person to watch:')}</label>
                            <select id="trigger-user" class="form-select">
                                <option value="">${this.t('triggers.select_person', 'Select a person...')}</option>
                                ${this.followedUsers.map(user => `
                                    <option value="${user.id}">${user.display_name || user.username}</option>
                                `).join('')}
                            </select>
                        </div>

                        <div class="form-group">
                            <label for="trigger-parameter">${this.t('triggers.parameter_label', 'Parameter:')}</label>
                            <select id="trigger-parameter" class="form-select">
                                <option value="mood">\u{1F60A} ${this.t('triggers.param_mood', 'Mood')}</option>
                                <option value="energy">\u{26A1} ${this.t('triggers.param_energy', 'Energy')}</option>
                                <option value="sleep_quality">\u{1F634} ${this.t('triggers.param_sleep', 'Sleep Quality')}</option>
                                <option value="physical_activity">\u{1F3C3} ${this.t('triggers.param_activity', 'Physical Activity')}</option>
                                <option value="anxiety">\u{1F630} ${this.t('triggers.param_anxiety', 'Anxiety')}</option>
                            </select>
                        </div>
                    </div>

                    <div class="form-row">
                        <div class="form-group">
                            <label for="trigger-condition">${this.t('triggers.alert_when', 'Alert when value:')}</label>
                            <div class="condition-group">
                                <select id="trigger-condition" class="form-select">
                                    <option value="below">${this.t('triggers.falls_below', 'Falls below')}</option>
                                    <option value="equals">${this.t('triggers.equals_exactly', 'Equals exactly')}</option>
                                    <option value="above">${this.t('triggers.goes_above', 'Goes above')}</option>
                                </select>
                                <select id="trigger-value" class="form-select">
                                    <option value="1">${this.t('triggers.value_low', '1 (Low)')}</option>
                                    <option value="2">${this.t('triggers.value_med_low', '2 (Medium-Low)')}</option>
                                    <option value="3">${this.t('triggers.value_med_high', '3 (Medium-High)')}</option>
                                    <option value="4">${this.t('triggers.value_high', '4 (High)')}</option>
                                </select>
                            </div>
                        </div>
                    </div>

                    <div class="form-row">
                        <div class="form-group full-width">
                            <label class="checkbox-label">
                                <input type="checkbox" id="trigger-consecutive" onchange="triggerManager.toggleConsecutiveDays()">
                                <span>${this.t('triggers.also_alert_no_checkin', 'Also alert if no check-in for')}</span>
                                <input type="number" id="trigger-days" min="1" max="30" value="3" disabled class="inline-input">
                                <span>${this.t('triggers.consecutive_days', 'consecutive days')}</span>
                            </label>
                        </div>
                    </div>

                    <button class="btn-primary" onclick="triggerManager.addTrigger()">
                        <span>\u{2795}</span> ${this.t('triggers.add_btn', 'Add Trigger')}
                    </button>
                </div>

                <div class="existing-triggers">
                    <h3>${this.t('triggers.active_count', 'Active Triggers')} (${this.triggers.length})</h3>
                    ${this.renderTriggerList()}
                </div>
            </div>
        `;
    }

        renderTriggerList() {
        if (this.triggers.length === 0) {
            return `
                <div class="no-triggers">
                    <p>📭 ${this.t('triggers.no_active', 'No active triggers yet')}</p>
                    <p class="hint">${this.t('triggers.no_active_hint', 'Add triggers above to get notified when someone needs support')}</p>
                </div>
            `;
        }

        return `
            <div class="trigger-list">
                ${this.triggers.map(trigger => this.renderTriggerItem(trigger)).join('')}
            </div>
        `;
    }

    renderTriggerItem(trigger) {
        const parameterNames = {
            mood: this.t('triggers.param_mood', 'Mood'),
            energy: this.t('triggers.param_energy', 'Energy'),
            sleep_quality: this.t('triggers.param_sleep', 'Sleep Quality'),
            physical_activity: this.t('triggers.param_activity', 'Physical Activity'),
            anxiety: this.t('triggers.param_anxiety', 'Anxiety')
        };

        const parameterEmoji = {
            mood: '\u{1F60A}',
            energy: '\u{26A1}',
            sleep_quality: '\u{1F634}',
            physical_activity: '\u{1F3C3}',
            anxiety: '\u{1F630}'
        };

        const conditionText = {
            below: this.t('triggers.drops_below', 'drops below'),
            above: this.t('triggers.goes_above_text', 'goes above'),
            equals: this.t('triggers.equals_text', 'equals')
        };

        return `
            <div class="trigger-item" data-trigger-id="${trigger.id}">
                <div class="trigger-icon">
                    ${parameterEmoji[trigger.parameter] || '\u{1F4CA}'}
                </div>
                <div class="trigger-info">
                    <div class="trigger-main">
                        <strong>${trigger.watched_user}</strong>'s
                        <span class="parameter-name">${parameterNames[trigger.parameter] || trigger.parameter.replace(/_/g, ' ')}</span>
                        ${conditionText[trigger.condition]}
                        <span class="trigger-value-badge">${trigger.value}</span>
                    </div>
                    ${trigger.consecutive_days ? `
                        <div class="trigger-secondary">
                            ${this.t('triggers.no_checkin_for', 'Or no check-in for {days} days').replace('{days}', trigger.consecutive_days)}
                        </div>
                    ` : ''}
                </div>
                <button class="btn-delete" onclick="triggerManager.deleteTrigger(${trigger.id})" title="${this.t('triggers.delete_title', 'Delete trigger')}">
                    \u{1F5D1}\u{FE0F}
                </button>
            </div>
        `;
    }

        toggleConsecutiveDays() {
        const checkbox = document.getElementById('trigger-consecutive');
        const daysInput = document.getElementById('trigger-days');

        if (checkbox && daysInput) {
            daysInput.disabled = !checkbox.checked;
            if (checkbox.checked) {
                daysInput.focus();
            }
        }
    }

    async addTrigger() {
        // Get form values
        const watchedId = document.getElementById('trigger-user').value;
        const parameterName = document.getElementById('trigger-parameter').value;
        const condition = document.getElementById('trigger-condition').value;
        const value = parseInt(document.getElementById('trigger-value').value);
        const consecutiveCheckbox = document.getElementById('trigger-consecutive');
        const consecutiveDays = consecutiveCheckbox.checked ?
            parseInt(document.getElementById('trigger-days').value) : null;

        // Validate
        if (!watchedId) {
            this.showMessage(this.t('triggers.select_person_error', 'Please select a person to watch'), 'error');
            return;
        }

        const data = {
            watched_id: watchedId,
            parameter_name: parameterName,
            condition: condition,
            value: value,
            consecutive_days: consecutiveDays
        };

        try {
            const response = await fetch('/api/triggers', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'include',
                body: JSON.stringify(data)
            });

            if (response.ok) {
                await this.loadTriggers();
                this.render();
                this.showMessage(this.t('triggers.added_success', 'Trigger added successfully!'), 'success');

                // Reset form
                document.getElementById('trigger-user').value = '';
                document.getElementById('trigger-consecutive').checked = false;
                document.getElementById('trigger-days').disabled = true;
            } else {
                const error = await response.json();
                this.showMessage(error.error || this.t('triggers.add_failed', 'Failed to add trigger'), 'error');
            }
        } catch (error) {
            console.error('Error adding trigger:', error);
            this.showMessage(this.t('triggers.add_failed_retry', 'Failed to add trigger. Please try again.'), 'error');
        }
    }

    async deleteTrigger(triggerId) {
        if (!confirm(this.t('triggers.confirm_delete', 'Are you sure you want to delete this trigger?'))) {
            return;
        }

        try {
            const response = await fetch(`/api/triggers/${triggerId}`, {
                method: 'DELETE',
                credentials: 'include'
            });

            if (response.ok) {
                // Animate removal
                const triggerElement = document.querySelector(`[data-trigger-id="${triggerId}"]`);
                if (triggerElement) {
                    triggerElement.style.animation = 'fadeOut 0.3s ease';
                    setTimeout(() => {
                        this.loadTriggers().then(() => this.render());
                    }, 300);
                }

                this.showMessage(this.t('triggers.deleted', 'Trigger deleted'), 'success');
            } else {
                this.showMessage(this.t('triggers.delete_failed', 'Failed to delete trigger'), 'error');
            }
        } catch (error) {
            console.error('Error deleting trigger:', error);
            this.showMessage(this.t('triggers.delete_failed', 'Failed to delete trigger'), 'error');
        }
    }

    showMessage(message, type = 'info') {
        // Use global showSuccess/showError if available
        if (type === 'success' && typeof showSuccess === 'function') {
            showSuccess(message);
        } else if (type === 'error' && typeof showError === 'function') {
            showError(message);
        } else {
            // Fallback to console
            console.log(`${type.toUpperCase()}: ${message}`);
        }
    }

    // Method to manually refresh triggers
    async refresh() {
        await this.loadTriggers();
        this.render();
    }
}

// Create global instance
let triggerManager;

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    triggerManager = new TriggerManager();

    // Auto-initialize if container exists
    if (document.getElementById('triggers-container')) {
        triggerManager.init();
    }
});

// Auto-refresh triggers every 60 seconds
setInterval(() => {
    if (triggerManager && triggerManager.initialized) {
        triggerManager.refresh();
    }
}, 60000);