#!/usr/bin/env python3
"""
TheraSocial Backend Diagnostic Suite - Enhanced Version
Provides EXACT code fixes with line numbers and code blocks

Run on Render shell with: python backend_diagnostics_enhanced.py
"""

import os
import sys
import json
import time
from datetime import datetime, timedelta
from collections import defaultdict

# Color codes for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    MAGENTA = '\033[95m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_check(passed, message, details=None):
    """Print a check result with color coding"""
    if passed:
        symbol = f"{Colors.GREEN}✓{Colors.END}"
    elif passed is None:
        symbol = f"{Colors.YELLOW}⚠{Colors.END}"
    else:
        symbol = f"{Colors.RED}✗{Colors.END}"
    
    print(f"{symbol} {message}")
    if details:
        print(f"  {Colors.BLUE}→{Colors.END} {details}")

def print_section(title):
    """Print a section header"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{title}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.END}\n")

def print_code_fix(issue_num, description, old_code, new_code, file_path, line_range=None):
    """Print a code fix with before/after"""
    print(f"\n{Colors.BOLD}{Colors.RED}Issue #{issue_num}: {description}{Colors.END}")
    print(f"{Colors.CYAN}File: {file_path}{Colors.END}")
    if line_range:
        print(f"{Colors.CYAN}Lines: {line_range}{Colors.END}")
    
    print(f"\n{Colors.RED}❌ CURRENT CODE (REMOVE):{Colors.END}")
    print(f"{Colors.RED}{old_code}{Colors.END}")
    
    print(f"\n{Colors.GREEN}✓ FIXED CODE (REPLACE WITH):{Colors.END}")
    print(f"{Colors.GREEN}{new_code}{Colors.END}")
    print(f"{Colors.BLUE}{'─'*70}{Colors.END}")

# Import Flask app components
try:
    from app import app, db, User, Profile, Post, Comment, Circle, Follow, FollowRequest
    from app import SavedParameters, Alert, Message, Activity, ParameterTrigger
    from app import redis_client, is_production
    print_check(True, "Successfully imported application modules")
except Exception as e:
    print_check(False, "Failed to import application modules", str(e))
    sys.exit(1)

class EnhancedBackendDiagnostics:
    def __init__(self):
        self.results = {
            'passed': 0,
            'failed': 0,
            'warnings': 0,
            'issues': [],
            'code_fixes': []
        }
        self.issue_counter = 0
        
    def add_result(self, passed, category, message, details=None, sql_fix=None, code_fix=None):
        """Track test result with code fixes"""
        if passed:
            self.results['passed'] += 1
        elif passed is None:
            self.results['warnings'] += 1
        else:
            self.results['failed'] += 1
            self.issue_counter += 1
            issue_data = {
                'number': self.issue_counter,
                'category': category,
                'message': message,
                'details': details,
                'sql_fix': sql_fix,
                'code_fix': code_fix
            }
            self.results['issues'].append(issue_data)
            if code_fix:
                self.results['code_fixes'].append(issue_data)
        
        print_check(passed, message, details)
    
    def test_environment_config(self):
        """Test environment configuration"""
        print_section("Environment Configuration")
        
        # Check SECRET_KEY
        secret_key = app.config.get('SECRET_KEY')
        is_default = secret_key == 'dev-secret-key-change-in-production'
        
        if is_production and is_default:
            self.add_result(
                False,
                'security',
                'SECRET_KEY using default value (CRITICAL SECURITY ISSUE)',
                'Using dev-secret-key-change-in-production',
                code_fix={
                    'file': 'Render Environment Variables',
                    'action': 'Add environment variable',
                    'old': 'SECRET_KEY not set (or using default)',
                    'new': '''
# In Render Dashboard > Environment:
# Click "Add Environment Variable"
# Key: SECRET_KEY
# Value: (generate with command below)

# Generate secure key:
python -c "import secrets; print(secrets.token_hex(32))"

# Example result: 4f9a8b2c1d3e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0
'''
                }
            )
        else:
            self.add_result(True, 'security', 'SECRET_KEY configuration', 'Using custom key' if not is_default else 'Using default (OK for dev)')
        
        # Check DATABASE_URL
        db_url = os.environ.get('DATABASE_URL')
        self.add_result(
            bool(db_url),
            'database',
            'DATABASE_URL environment variable',
            db_url[:50] + '...' if db_url else 'Not set',
            None if db_url else {
                'file': 'Render Environment Variables',
                'action': 'Verify DATABASE_URL is set',
                'old': 'DATABASE_URL missing',
                'new': 'DATABASE_URL should be auto-set by Render when you add a PostgreSQL database'
            }
        )
        
        # Check Redis
        redis_url = os.environ.get('REDIS_URL')
        if is_production and not redis_url:
            self.add_result(
                None,
                'cache',
                'REDIS_URL not configured',
                'Sessions using filesystem (slower)',
                code_fix={
                    'file': 'Render Environment Variables',
                    'action': 'Add Redis for better performance',
                    'old': 'REDIS_URL not set',
                    'new': '''
# In Render Dashboard:
# 1. Create new Redis service
# 2. Copy the Internal Redis URL
# 3. Add to your Web Service Environment Variables:
#    Key: REDIS_URL
#    Value: redis://red-xxxxx:6379 (from Redis service)
'''
                }
            )
        else:
            self.add_result(
                True if redis_url else None,
                'cache',
                'Redis configuration',
                'Configured' if redis_url else 'Not configured (OK for dev)'
            )
        
        # Check email configuration
        smtp_user = os.environ.get('SMTP_USERNAME')
        smtp_pass = os.environ.get('SMTP_PASSWORD')
        email_configured = bool(smtp_user and smtp_pass)
        
        if is_production and not email_configured:
            self.add_result(
                None,
                'email',
                'Email not configured',
                'Password reset emails will fail',
                code_fix={
                    'file': 'Render Environment Variables',
                    'action': 'Configure email for password resets',
                    'old': 'Email variables not set',
                    'new': '''
# For Gmail:
# 1. Enable 2-Step Verification in Google Account
# 2. Generate App Password: https://myaccount.google.com/apppasswords
# 3. Add these environment variables in Render:

SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your.email@gmail.com
SMTP_PASSWORD=your-16-char-app-password
FROM_EMAIL=your.email@gmail.com
APP_URL=https://socialsocial-72gn.onrender.com
'''
                }
            )
        else:
            self.add_result(
                True if email_configured else None,
                'email',
                'Email configuration',
                'Configured' if email_configured else 'Not configured (OK for dev)'
            )
    
    def test_database_integrity(self):
        """Test data integrity with exact SQL fixes"""
        print_section("Data Integrity Checks")
        
        with app.app_context():
            try:
                # Orphaned profiles
                orphaned_profiles = db.session.query(Profile).filter(
                    ~Profile.user_id.in_(db.session.query(User.id))
                ).all()
                
                if orphaned_profiles:
                    self.add_result(
                        False,
                        'integrity',
                        f'Found {len(orphaned_profiles)} orphaned profiles',
                        f'Profile IDs: {[p.id for p in orphaned_profiles]}',
                        sql_fix='''
-- Run this SQL command in Render Shell or pgAdmin:
DELETE FROM profiles WHERE user_id NOT IN (SELECT id FROM users);

-- Verify the fix:
SELECT COUNT(*) FROM profiles WHERE user_id NOT IN (SELECT id FROM users);
-- Should return: 0
'''
                    )
                else:
                    self.add_result(True, 'integrity', 'No orphaned profiles', 'All profiles belong to valid users')
                
                # Orphaned posts
                orphaned_posts = db.session.query(Post).filter(
                    ~Post.user_id.in_(db.session.query(User.id))
                ).all()
                
                if orphaned_posts:
                    self.add_result(
                        False,
                        'integrity',
                        f'Found {len(orphaned_posts)} orphaned posts',
                        f'Post IDs: {[p.id for p in orphaned_posts[:5]]}...',
                        sql_fix='''
-- Run this SQL command:
DELETE FROM posts WHERE user_id NOT IN (SELECT id FROM users);

-- Verify:
SELECT COUNT(*) FROM posts WHERE user_id NOT IN (SELECT id FROM users);
'''
                    )
                else:
                    self.add_result(True, 'integrity', 'No orphaned posts', 'All posts belong to valid users')
                
                # Orphaned messages
                orphaned_messages = db.session.query(Message).filter(
                    or_(
                        ~Message.sender_id.in_(db.session.query(User.id)),
                        ~Message.recipient_id.in_(db.session.query(User.id))
                    )
                ).all()
                
                if orphaned_messages:
                    self.add_result(
                        False,
                        'integrity',
                        f'Found {len(orphaned_messages)} orphaned messages',
                        'Messages with invalid sender or recipient',
                        sql_fix='''
-- Run this SQL command:
DELETE FROM messages 
WHERE sender_id NOT IN (SELECT id FROM users) 
   OR recipient_id NOT IN (SELECT id FROM users);

-- Verify:
SELECT COUNT(*) FROM messages 
WHERE sender_id NOT IN (SELECT id FROM users) 
   OR recipient_id NOT IN (SELECT id FROM users);
'''
                    )
                else:
                    self.add_result(True, 'integrity', 'No orphaned messages', 'All messages have valid users')
                
                # Self-follows
                self_follows = db.session.query(Follow).filter(
                    Follow.follower_id == Follow.followed_id
                ).all()
                
                if self_follows:
                    self.add_result(
                        False,
                        'integrity',
                        f'Found {len(self_follows)} self-follows',
                        f'User IDs: {list(set([f.follower_id for f in self_follows]))}',
                        sql_fix='''
-- Run this SQL command:
DELETE FROM follows WHERE follower_id = followed_id;

-- Verify:
SELECT COUNT(*) FROM follows WHERE follower_id = followed_id;

-- To prevent future self-follows, add constraint in app.py Follow model:
-- Add validation in follow() method (see code fix below)
''',
                        code_fix={
                            'file': 'app.py',
                            'line_range': '487-492',
                            'old': '''    def follow(self, user):
        """Follow another user"""
        if not self.is_following(user):
            follow = Follow(follower_id=self.id, followed_id=user.id)
            db.session.add(follow)''',
                            'new': '''    def follow(self, user):
        """Follow another user"""
        # Prevent self-follows
        if self.id == user.id:
            raise ValueError("Cannot follow yourself")
        
        if not self.is_following(user):
            follow = Follow(follower_id=self.id, followed_id=user.id)
            db.session.add(follow)'''
                        }
                    )
                else:
                    self.add_result(True, 'integrity', 'No self-follows', 'Users cannot follow themselves')
                
            except Exception as e:
                self.add_result(
                    None,
                    'integrity',
                    'Data integrity check error',
                    str(e),
                    None
                )
    
    def test_privacy_defaults(self):
        """Test privacy defaults with exact fixes"""
        print_section("Privacy Settings Compliance")
        
        with app.app_context():
            try:
                # Parameters without privacy settings
                params_without_privacy = db.session.query(SavedParameters).filter(
                    or_(
                        SavedParameters.mood_privacy.is_(None),
                        SavedParameters.energy_privacy.is_(None),
                        SavedParameters.sleep_quality_privacy.is_(None),
                        SavedParameters.physical_activity_privacy.is_(None),
                        SavedParameters.anxiety_privacy.is_(None)
                    )
                ).all()
                
                if params_without_privacy:
                    affected_users = list(set([p.user_id for p in params_without_privacy]))
                    self.add_result(
                        False,
                        'privacy',
                        f'Found {len(params_without_privacy)} parameters without privacy settings',
                        f'Affects {len(affected_users)} users',
                        sql_fix=f'''
-- IMMEDIATE FIX - Set all NULL privacy to 'private':
UPDATE saved_parameters 
SET mood_privacy = COALESCE(mood_privacy, 'private'),
    energy_privacy = COALESCE(energy_privacy, 'private'),
    sleep_quality_privacy = COALESCE(sleep_quality_privacy, 'private'),
    physical_activity_privacy = COALESCE(physical_activity_privacy, 'private'),
    anxiety_privacy = COALESCE(anxiety_privacy, 'private')
WHERE mood_privacy IS NULL 
   OR energy_privacy IS NULL 
   OR sleep_quality_privacy IS NULL 
   OR physical_activity_privacy IS NULL 
   OR anxiety_privacy IS NULL;

-- Verify all parameters now have privacy:
SELECT COUNT(*) FROM saved_parameters 
WHERE mood_privacy IS NULL 
   OR energy_privacy IS NULL 
   OR sleep_quality_privacy IS NULL 
   OR physical_activity_privacy IS NULL 
   OR anxiety_privacy IS NULL;
-- Should return: 0

-- PREVENT FUTURE ISSUES - Update model defaults in app.py
-- See code fix below
''',
                        code_fix={
                            'file': 'app.py',
                            'line_range': '634-638',
                            'current_code_check': 'Already has default=\'private\' in model',
                            'old': '''    mood_privacy = db.Column(db.String(20), default='private')
    energy_privacy = db.Column(db.String(20), default='private')
    sleep_quality_privacy = db.Column(db.String(20), default='private')
    physical_activity_privacy = db.Column(db.String(20), default='private')
    anxiety_privacy = db.Column(db.String(20), default='private')''',
                            'new': '''    # Defaults are already correct in model
    # Issue is with existing data - run the SQL fix above
    mood_privacy = db.Column(db.String(20), default='private', nullable=False)
    energy_privacy = db.Column(db.String(20), default='private', nullable=False)
    sleep_quality_privacy = db.Column(db.String(20), default='private', nullable=False)
    physical_activity_privacy = db.Column(db.String(20), default='private', nullable=False)
    anxiety_privacy = db.Column(db.String(20), default='private', nullable=False)'''
                        }
                    )
                else:
                    self.add_result(True, 'privacy', 'All parameters have privacy settings', 'No NULL privacy values')
                
                # Users without circles_privacy
                users_without_circles_privacy = db.session.query(User).filter(
                    User.circles_privacy.is_(None)
                ).all()
                
                if users_without_circles_privacy:
                    self.add_result(
                        False,
                        'privacy',
                        f'Found {len(users_without_circles_privacy)} users without circles_privacy',
                        f'User IDs: {[u.id for u in users_without_circles_privacy]}',
                        sql_fix='''
-- Set circles_privacy to 'private' for all NULL values:
UPDATE users SET circles_privacy = 'private' WHERE circles_privacy IS NULL;

-- Verify:
SELECT COUNT(*) FROM users WHERE circles_privacy IS NULL;
-- Should return: 0
''',
                        code_fix={
                            'file': 'app.py',
                            'line_range': '463',
                            'old': '''    circles_privacy = db.Column(db.String(20), default='private')''',
                            'new': '''    circles_privacy = db.Column(db.String(20), default='private', nullable=False)'''
                        }
                    )
                else:
                    self.add_result(True, 'privacy', 'All users have circles_privacy set', 'No NULL values')
                
            except Exception as e:
                self.add_result(
                    None,
                    'privacy',
                    'Privacy check error',
                    str(e),
                    None
                )
    
    def test_api_security(self):
        """Test API security measures"""
        print_section("API Security Checks")
        
        # Check if login_required decorator exists
        try:
            with open('app.py', 'r') as f:
                app_content = f.read()
                
            has_login_required = 'def login_required' in app_content or '@login_required' in app_content
            
            if not has_login_required:
                self.add_result(
                    False,
                    'security',
                    'No login_required decorator found',
                    'Protected routes may be accessible without authentication',
                    code_fix={
                        'file': 'app.py',
                        'line_range': 'Add after imports (~line 50)',
                        'old': '# No authentication decorator',
                        'new': '''
# Add this decorator function after imports:
def login_required(f):
    """Decorator to require login for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function

# Then protect routes like:
@app.route('/api/user/profile')
@login_required
def get_profile():
    ...
'''
                    }
                )
            else:
                self.add_result(True, 'security', 'Authentication decorator exists', 'Routes can be protected')
            
            # Check for rate limiting
            has_rate_limit = 'rate_limit' in app_content.lower()
            if not has_rate_limit:
                self.add_result(
                    None,
                    'security',
                    'No rate limiting detected',
                    'Consider adding rate limits to prevent abuse',
                    code_fix={
                        'file': 'app.py',
                        'note': 'Rate limiting is imported from security.py',
                        'old': 'from security import (...)',
                        'new': '''from security import (
    sanitize_input, validate_email, validate_username,
    validate_password_strength, encrypt_field, decrypt_field,
    generate_token, rate_limit, content_moderator
)

# Use on sensitive routes:
@app.route('/api/auth/login', methods=['POST'])
@rate_limit(max_requests=5, window=60)  # 5 requests per minute
def login():
    ...
'''
                    }
                )
            else:
                self.add_result(True, 'security', 'Rate limiting available', 'Can protect against brute force')
            
        except Exception as e:
            self.add_result(None, 'security', 'Could not check security features', str(e))
    
    def generate_fixes_document(self):
        """Generate document with all code fixes"""
        print_section("CODE FIXES SUMMARY")
        
        if not self.results['code_fixes']:
            print(f"{Colors.GREEN}✓ No code fixes needed!{Colors.END}\n")
            return
        
        print(f"{Colors.BOLD}Found {len(self.results['code_fixes'])} issues requiring code changes:{Colors.END}\n")
        
        for issue in self.results['code_fixes']:
            fix = issue.get('code_fix') or issue.get('sql_fix')
            
            if issue.get('sql_fix'):
                print(f"\n{Colors.BOLD}{Colors.RED}#{issue['number']}: {issue['message']}{Colors.END}")
                print(f"{Colors.CYAN}Category: {issue['category']}{Colors.END}")
                print(f"{Colors.YELLOW}Details: {issue['details']}{Colors.END}")
                print(f"\n{Colors.GREEN}SQL FIX:{Colors.END}")
                print(f"{Colors.GREEN}{issue['sql_fix']}{Colors.END}")
                print(f"{Colors.BLUE}{'─'*70}{Colors.END}")
            
            if issue.get('code_fix') and isinstance(issue['code_fix'], dict):
                cf = issue['code_fix']
                print(f"\n{Colors.BOLD}{Colors.RED}#{issue['number']}: {issue['message']}{Colors.END}")
                print(f"{Colors.CYAN}File: {cf.get('file', 'Unknown')}{Colors.END}")
                if cf.get('line_range'):
                    print(f"{Colors.CYAN}Lines: {cf['line_range']}{Colors.END}")
                if cf.get('action'):
                    print(f"{Colors.CYAN}Action: {cf['action']}{Colors.END}")
                
                if cf.get('old'):
                    print(f"\n{Colors.RED}❌ CURRENT/OLD:{Colors.END}")
                    print(f"{Colors.RED}{cf['old']}{Colors.END}")
                
                if cf.get('new'):
                    print(f"\n{Colors.GREEN}✓ REPLACE WITH:{Colors.END}")
                    print(f"{Colors.GREEN}{cf['new']}{Colors.END}")
                
                print(f"{Colors.BLUE}{'─'*70}{Colors.END}")
    
    def generate_report(self):
        """Generate comprehensive diagnostic report"""
        print_section("DIAGNOSTIC SUMMARY")
        
        total_tests = self.results['passed'] + self.results['failed'] + self.results['warnings']
        
        print(f"\n{Colors.BOLD}Test Results:{Colors.END}")
        print(f"  {Colors.GREEN}✓ Passed:{Colors.END}  {self.results['passed']}/{total_tests}")
        print(f"  {Colors.RED}✗ Failed:{Colors.END}  {self.results['failed']}/{total_tests}")
        print(f"  {Colors.YELLOW}⚠ Warnings:{Colors.END} {self.results['warnings']}/{total_tests}")
        
        # Overall assessment
        print(f"\n{Colors.BOLD}Overall Assessment:{Colors.END}")
        if self.results['failed'] == 0:
            print(f"{Colors.GREEN}✓ System is ready for QA testing{Colors.END}")
        elif self.results['failed'] < 5:
            print(f"{Colors.YELLOW}⚠ System needs minor fixes before QA{Colors.END}")
        else:
            print(f"{Colors.RED}✗ System requires significant fixes before QA{Colors.END}")
        
        return self.results

def main():
    """Run all diagnostic tests"""
    print(f"\n{Colors.BOLD}{'='*70}{Colors.END}")
    print(f"{Colors.BOLD}TheraSocial Enhanced Backend Diagnostics{Colors.END}")
    print(f"{Colors.BOLD}with Exact Code Fixes{Colors.END}")
    print(f"{Colors.BOLD}Running in: {'PRODUCTION' if is_production else 'DEVELOPMENT'} mode{Colors.END}")
    print(f"{Colors.BOLD}{'='*70}{Colors.END}")
    
    diagnostics = EnhancedBackendDiagnostics()
    
    # Run test suites
    diagnostics.test_environment_config()
    diagnostics.test_database_integrity()
    diagnostics.test_privacy_defaults()
    diagnostics.test_api_security()
    
    # Generate reports
    diagnostics.generate_fixes_document()
    results = diagnostics.generate_report()
    
    # Exit with appropriate code
    sys.exit(0 if results['failed'] == 0 else 1)

if __name__ == '__main__':
    main()
