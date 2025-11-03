// Complete Onboarding Flow for TheraSocial
// onboarding.js - Full Implementation

class OnboardingFlow {
    constructor() {
        this.currentStep = 0;
        this.steps = [
            {
                title: "Welcome to TheraSocial!",
                content: "Let's take a quick tour of how to track your wellness journey and connect with others who care about you.",
                action: null
            },
            {
                title: "Daily Check-ins",
                content: "Track your mood, energy, sleep, activity, and anxiety levels daily with simple 1-4 ratings. It only takes a minute!",
                action: () => this.highlightElement('.parameter-category')
            },
            {
                title: "Privacy Settings",
                content: "You control who sees what! Choose Public, Class B (close friends), or Class A (family) for each parameter.",
                action: () => this.highlightElement('.privacy-selector')
            },
            {
                title: "Connect with Others",
                content: "Follow friends and family to support each other's wellness journey. You decide what they can see.",
                action: () => this.highlightElement('.follow-section')
            },
            {
                title: "Set Care Triggers",
                content: "Get notified when someone you care about might need support. Set custom alerts for any parameter.",
                action: () => this.highlightElement('.triggers-section')
            },
            {
                title: "You're Ready!",
                content: "That's all you need to know to get started. Remember, this is your safe space to track and share your wellness journey.",
                action: null
            }
        ];
        this.overlayElement = null;
    }

    async checkAndStart() {
        try {
            const response = await fetch('/api/onboarding/status', {
                credentials: 'include'
            });

            if (!response.ok) {
                console.log('User not authenticated for onboarding');
                return;
            }

            const data = await response.json();

            if (data.needs_onboarding) {
                // Small delay to let page load
                setTimeout(() => this.start(), 500);
            }
        } catch (error) {
            console.error('Error checking onboarding status:', error);
        }
    }

    start() {
        this.createOverlay();
        this.showStep(0);
    }

    createOverlay() {
        // Remove any existing overlay
        if (this.overlayElement) {
            this.overlayElement.remove();
        }

        const overlay = document.createElement('div');
        overlay.id = 'onboarding-overlay';
        overlay.innerHTML = `
            <div class="onboarding-backdrop"></div>
            <div class="onboarding-modal">
                <div class="onboarding-content">
                    <div class="onboarding-header">
                        <h2 id="onboarding-title"></h2>
                        <button class="onboarding-close" onclick="onboardingFlow.skip()">&times;</button>
                    </div>
                    <p id="onboarding-text"></p>
                    <div class="onboarding-actions">
                        <button id="onboarding-prev" class="btn-secondary" onclick="onboardingFlow.prevStep()">
                            Previous
                        </button>
                        <button id="onboarding-next" class="btn-primary" onclick="onboardingFlow.nextStep()">
                            Next
                        </button>
                    </div>
                    <div class="onboarding-progress">
                        <div id="progress-bar"></div>
                    </div>
                    <div class="onboarding-footer">
                        <label class="dont-show-again">
                            <input type="checkbox" id="dont-show-again">
                            <span>Don't show this tour again</span>
                        </label>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(overlay);
        this.overlayElement = overlay;
    }

    showStep(stepIndex) {
        if (stepIndex < 0 || stepIndex >= this.steps.length) return;

        this.currentStep = stepIndex;
        const step = this.steps[stepIndex];

        // Update content
        document.getElementById('onboarding-title').textContent = step.title;
        document.getElementById('onboarding-text').textContent = step.content;

        // Update buttons
        const prevBtn = document.getElementById('onboarding-prev');
        const nextBtn = document.getElementById('onboarding-next');

        if (prevBtn) {
            prevBtn.style.display = stepIndex === 0 ? 'none' : 'inline-block';
        }

        if (nextBtn) {
            nextBtn.textContent = stepIndex === this.steps.length - 1 ? 'Get Started' : 'Next';
        }

        // Update progress bar
        const progress = ((stepIndex + 1) / this.steps.length) * 100;
        const progressBar = document.getElementById('progress-bar');
        if (progressBar) {
            progressBar.style.width = `${progress}%`;
        }

        // Remove previous highlights
        document.querySelectorAll('.onboarding-highlight').forEach(el => {
            el.classList.remove('onboarding-highlight');
        });

        // Execute step action if any
        if (step.action) {
            setTimeout(() => step.action(), 100);
        }
    }

    nextStep() {
        if (this.currentStep < this.steps.length - 1) {
            this.showStep(this.currentStep + 1);
        } else {
            this.complete();
        }
    }

    prevStep() {
        if (this.currentStep > 0) {
            this.showStep(this.currentStep - 1);
        }
    }

    async skip() {
        const dontShowAgain = document.getElementById('dont-show-again');

        if (dontShowAgain && dontShowAgain.checked) {
            await this.dismissOnboarding();
        }

        this.close();
    }

    async complete() {
        const dontShowAgain = document.getElementById('dont-show-again');

        // Mark as completed
        try {
            await fetch('/api/onboarding/complete', {
                method: 'POST',
                credentials: 'include'
            });
        } catch (error) {
            console.error('Error marking onboarding complete:', error);
        }

        if (dontShowAgain && dontShowAgain.checked) {
            await this.dismissOnboarding();
        }

        this.close();

        // Show success message if function exists
        if (typeof showSuccess === 'function') {
            showSuccess('Welcome to TheraSocial! Start by logging your first daily check-in.');
        }
    }

    async dismissOnboarding() {
        try {
            await fetch('/api/onboarding/dismiss', {
                method: 'POST',
                credentials: 'include'
            });
        } catch (error) {
            console.error('Error dismissing onboarding:', error);
        }
    }

    close() {
        if (this.overlayElement) {
            // Add fade out animation
            this.overlayElement.style.animation = 'fadeOut 0.3s ease';
            setTimeout(() => {
                if (this.overlayElement) {
                    this.overlayElement.remove();
                    this.overlayElement = null;
                }
            }, 300);
        }
    }

    highlightElement(selector) {
        const element = document.querySelector(selector);
        if (element) {
            element.classList.add('onboarding-highlight');
            element.scrollIntoView({
                behavior: 'smooth',
                block: 'center'
            });
        }
    }
}

// Global instance
let onboardingFlow;

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    // Create instance
    onboardingFlow = new OnboardingFlow();

    // Check if onboarding needed
    onboardingFlow.checkAndStart();
});

// Add required styles dynamically
const onboardingStyles = document.createElement('style');
onboardingStyles.textContent = `
    @keyframes fadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
    }

    @keyframes fadeOut {
        from { opacity: 1; }
        to { opacity: 0; }
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

    @keyframes pulse {
        0%, 100% {
            box-shadow: 0 0 0 4px rgba(102, 126, 234, 0.3);
        }
        50% {
            box-shadow: 0 0 0 8px rgba(102, 126, 234, 0.1);
        }
    }

    #onboarding-overlay {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        z-index: 10000;
        animation: fadeIn 0.3s ease;
    }

    .onboarding-backdrop {
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0, 0, 0, 0.7);
    }

    .onboarding-modal {
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        background: white;
        border-radius: 16px;
        padding: 0;
        max-width: 500px;
        width: 90%;
        box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
        animation: slideIn 0.4s ease;
    }

    .onboarding-content {
        padding: 30px;
    }

    .onboarding-header {
        display: flex;
        justify-content: space-between;
        align-items: start;
        margin-bottom: 15px;
    }

    .onboarding-header h2 {
        color: #667eea;
        margin: 0;
        font-size: 24px;
    }

    .onboarding-close {
        background: none;
        border: none;
        font-size: 28px;
        color: #999;
        cursor: pointer;
        padding: 0;
        width: 30px;
        height: 30px;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    .onboarding-close:hover {
        color: #667eea;
    }

    #onboarding-text {
        color: #666;
        line-height: 1.6;
        margin-bottom: 25px;
        font-size: 16px;
    }

    .onboarding-actions {
        display: flex;
        gap: 10px;
        margin-bottom: 20px;
    }

    .onboarding-progress {
        height: 4px;
        background: #e1e8ed;
        border-radius: 2px;
        overflow: hidden;
        margin-bottom: 20px;
    }

    #progress-bar {
        height: 100%;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        transition: width 0.3s ease;
        width: 0;
    }

    .onboarding-footer {
        padding-top: 15px;
        border-top: 1px solid #e1e8ed;
    }

    .dont-show-again {
        display: flex;
        align-items: center;
        gap: 8px;
        color: #666;
        font-size: 14px;
        cursor: pointer;
    }

    .dont-show-again input[type="checkbox"] {
        cursor: pointer;
    }

    .onboarding-highlight {
        position: relative;
        z-index: 9999;
        animation: pulse 2s infinite;
    }

    .btn-primary, .btn-secondary {
        padding: 10px 24px;
        border: none;
        border-radius: 25px;
        font-size: 16px;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.3s ease;
    }

    .btn-primary {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
    }

    .btn-primary:hover {
        transform: scale(1.05);
        box-shadow: 0 5px 15px rgba(102, 126, 234, 0.3);
    }

    .btn-secondary {
        background: #f0f2f5;
        color: #333;
    }

    .btn-secondary:hover {
        background: #e1e4e8;
    }
`;

document.head.appendChild(onboardingStyles);