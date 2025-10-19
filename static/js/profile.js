// Profile Page JavaScript with Enhanced Fields and Modern Styling
// Add this to your existing profile page or create a new profile.html

// Profile HTML Structure (add to profile.html)
const profileHTML = `
<div class="profile-container">
    <style>
        .profile-container {
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
        }
        
        .profile-header {
            text-align: center;
            margin-bottom: 40px;
            position: relative;
        }
        
        .profile-avatar {
            width: 120px;
            height: 120px;
            border-radius: 60px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto 20px;
            font-size: 48px;
            color: white;
            box-shadow: 0 10px 30px rgba(102, 126, 234, 0.3);
        }
        
        .profile-name {
            font-size: 2em;
            color: #2d3436;
            margin-bottom: 10px;
            font-weight: 600;
        }
        
        .profile-sections {
            display: grid;
            gap: 25px;
        }
        
        .profile-section {
            background: white;
            border-radius: 16px;
            padding: 0;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.07);
            transition: all 0.3s ease;
            overflow: hidden;
        }
        
        .profile-section:hover {
            box-shadow: 0 8px 16px rgba(0, 0, 0, 0.12);
            transform: translateY(-2px);
        }
        
        .section-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px 25px;
            font-size: 1.1em;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .section-icon {
            font-size: 1.2em;
        }
        
        .section-content {
            padding: 25px;
        }
        
        .profile-field {
            position: relative;
            margin-bottom: 20px;
        }
        
        .profile-input,
        .profile-textarea {
            width: 100%;
            padding: 12px 15px;
            border: 2px solid #e1e8ed;
            border-radius: 10px;
            font-size: 16px;
            transition: all 0.3s ease;
            background: #f8f9fa;
            font-family: inherit;
        }
        
        .profile-textarea {
            min-height: 100px;
            resize: vertical;
        }
        
        .profile-input:focus,
        .profile-textarea:focus {
            outline: none;
            border-color: #667eea;
            background: white;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        
        .profile-label {
            position: absolute;
            left: 15px;
            top: -10px;
            background: white;
            padding: 0 8px;
            color: #667eea;
            font-size: 14px;
            font-weight: 500;
            z-index: 1;
        }
        
        .character-count {
            position: absolute;
            right: 15px;
            bottom: -20px;
            font-size: 12px;
            color: #8898aa;
        }
        
        .profile-actions {
            display: flex;
            gap: 15px;
            justify-content: center;
            margin-top: 40px;
        }
        
        .btn-save,
        .btn-cancel {
            padding: 12px 40px;
            border: none;
            border-radius: 25px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        
        .btn-save {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
        }
        
        .btn-save:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(102, 126, 234, 0.5);
        }
        
        .btn-cancel {
            background: white;
            color: #667eea;
            border: 2px solid #667eea;
        }
        
        .btn-cancel:hover {
            background: #f8f9fa;
        }
        
        .interest-tags {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-top: 10px;
        }
        
        .interest-tag {
            padding: 6px 15px;
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            color: white;
            border-radius: 20px;
            font-size: 14px;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .interest-tag:hover {
            transform: scale(1.05);
        }
        
        .profile-completion {
            background: #f8f9fa;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 30px;
        }
        
        .completion-bar {
            width: 100%;
            height: 10px;
            background: #e1e8ed;
            border-radius: 5px;
            overflow: hidden;
            margin: 10px 0;
        }
        
        .completion-progress {
            height: 100%;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            transition: width 0.5s ease;
        }
        
        .completion-text {
            text-align: center;
            color: #667eea;
            font-weight: 600;
        }
        
        @media (max-width: 768px) {
            .profile-container {
                padding: 15px;
            }
            
            .profile-actions {
                flex-direction: column;
            }
            
            .btn-save,
            .btn-cancel {
                width: 100%;
            }
        }
    </style>
    
    <div class="profile-header">
        <div class="profile-avatar" id="profileAvatar">👤</div>
        <div class="profile-name" id="profileName">Loading...</div>
    </div>
    
    <div class="profile-completion">
        <div class="completion-text">Profile Completion: <span id="completionPercent">0%</span></div>
        <div class="completion-bar">
            <div class="completion-progress" id="completionBar" style="width: 0%"></div>
        </div>
    </div>
    
    <div class="profile-sections">
        <div class="profile-section">
            <div class="section-header">
                <span class="section-icon">📝</span>
                <span>About Me</span>
            </div>
            <div class="section-content">
                <div class="profile-field">
                    <label class="profile-label">Bio</label>
                    <textarea class="profile-textarea" id="bio" placeholder="Tell us about yourself..." maxlength="500"></textarea>
                    <span class="character-count"><span id="bioCount">0</span> / 500</span>
                </div>
            </div>
        </div>
        
        <div class="profile-section">
            <div class="section-header">
                <span class="section-icon">💼</span>
                <span>Professional</span>
            </div>
            <div class="section-content">
                <div class="profile-field">
                    <label class="profile-label">Occupation</label>
                    <input type="text" class="profile-input" id="occupation" placeholder="What do you do?">
                </div>
            </div>
        </div>
        
        <div class="profile-section">
            <div class="section-header">
                <span class="section-icon">🎯</span>
                <span>Goals & Aspirations</span>
            </div>
            <div class="section-content">
                <div class="profile-field">
                    <label class="profile-label">My Goals</label>
                    <textarea class="profile-textarea" id="goals" placeholder="What are your personal or professional goals?" maxlength="300"></textarea>
                    <span class="character-count"><span id="goalsCount">0</span> / 300</span>
                </div>
            </div>
        </div>
        
        <div class="profile-section">
            <div class="section-header">
                <span class="section-icon">💫</span>
                <span>Interests & Hobbies</span>
            </div>
            <div class="section-content">
                <div class="profile-field">
                    <label class="profile-label">Interests</label>
                    <textarea class="profile-textarea" id="interests" placeholder="What are you interested in?" maxlength="300"></textarea>
                    <span class="character-count"><span id="interestsCount">0</span> / 300</span>
                </div>
                
                <div class="profile-field" style="margin-top: 30px;">
                    <label class="profile-label">Favorite Hobbies</label>
                    <textarea class="profile-textarea" id="favorite_hobbies" placeholder="What do you love to do in your free time?" maxlength="300"></textarea>
                    <span class="character-count"><span id="hobbiesCount">0</span> / 300</span>
                </div>
            </div>
        </div>
    </div>
    
    <div class="profile-actions">
        <button class="btn-save" onclick="saveProfile()">Save Changes</button>
        <button class="btn-cancel" onclick="loadProfile()">Cancel</button>
    </div>
</div>
`;

// Profile JavaScript Functions
let profileData = {};

async function loadProfile() {
    try {
        const response = await fetch('/api/profile', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (response.ok) {
            profileData = await response.json();
            
            // Populate fields
            document.getElementById('bio').value = profileData.bio || '';
            document.getElementById('interests').value = profileData.interests || '';
            document.getElementById('occupation').value = profileData.occupation || '';
            document.getElementById('goals').value = profileData.goals || '';
            document.getElementById('favorite_hobbies').value = profileData.favorite_hobbies || '';
            
            // Update character counts
            updateCharacterCount('bio', 500);
            updateCharacterCount('goals', 300);
            updateCharacterCount('interests', 300);
            updateCharacterCount('favorite_hobbies', 300);
            
            // Update profile completion
            updateProfileCompletion();
            
            // Get user name (you may need to fetch this from your user endpoint)
            const userResponse = await fetch('/api/user/profile');
            if (userResponse.ok) {
                const userData = await userResponse.json();
                document.getElementById('profileName').textContent = userData.username || 'User';
                
                // Set avatar based on first letter
                const firstLetter = (userData.username || 'U')[0].toUpperCase();
                document.getElementById('profileAvatar').textContent = firstLetter;
            }
        }
    } catch (error) {
        console.error('Error loading profile:', error);
    }
}

async function saveProfile() {
    const profileData = {
        bio: document.getElementById('bio').value,
        interests: document.getElementById('interests').value,
        occupation: document.getElementById('occupation').value,
        goals: document.getElementById('goals').value,
        favorite_hobbies: document.getElementById('favorite_hobbies').value
    };
    
    try {
        const response = await fetch('/api/profile', {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(profileData)
        });
        
        if (response.ok) {
            showNotification('Profile updated successfully!', 'success');
            updateProfileCompletion();
        } else {
            showNotification('Error updating profile', 'error');
        }
    } catch (error) {
        console.error('Error saving profile:', error);
        showNotification('Error saving profile', 'error');
    }
}

function updateCharacterCount(fieldId, maxLength) {
    const field = document.getElementById(fieldId);
    const countElement = document.getElementById(fieldId + 'Count');
    
    if (!field || !countElement) return;
    
    const updateCount = () => {
        const length = field.value.length;
        countElement.textContent = length;
        
        // Change color as approaching limit
        if (length > maxLength * 0.9) {
            countElement.style.color = '#f5576c';
        } else if (length > maxLength * 0.7) {
            countElement.style.color = '#ffa500';
        } else {
            countElement.style.color = '#8898aa';
        }
    };
    
    field.addEventListener('input', updateCount);
    updateCount();
}

function updateProfileCompletion() {
    const fields = ['bio', 'interests', 'occupation', 'goals', 'favorite_hobbies'];
    let filledFields = 0;
    
    fields.forEach(fieldId => {
        const field = document.getElementById(fieldId);
        if (field && field.value.trim().length > 0) {
            filledFields++;
        }
    });
    
    const percentage = Math.round((filledFields / fields.length) * 100);
    
    document.getElementById('completionPercent').textContent = percentage + '%';
    document.getElementById('completionBar').style.width = percentage + '%';
}

function showNotification(message, type) {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = 'notification ' + type;
    notification.textContent = message;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 15px 25px;
        background: ${type === 'success' ? 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' : '#f5576c'};
        color: white;
        border-radius: 10px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        z-index: 1000;
        animation: slideIn 0.3s ease;
    `;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.remove();
    }, 3000);
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    // Check if we're on the profile page
    if (document.getElementById('profileContainer')) {
        document.getElementById('profileContainer').innerHTML = profileHTML;
        loadProfile();
    }
});
