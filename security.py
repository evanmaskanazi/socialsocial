"""
Security module for Thera Social
Handles encryption, sanitization, and security measures
"""
import os
import re
import html
import secrets
import hashlib
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import base64
import bleach

class SecurityManager:
    """Manages security features and encryption"""
    
    def __init__(self, app, redis_client):
        self.app = app
        self.redis = redis_client
        self.cipher_suite = self._init_cipher()
        self.allowed_tags = ['b', 'i', 'u', 'br', 'p', 'strong', 'em']
        self.allowed_attributes = {}
        
    def _init_cipher(self):
        """Initialize encryption cipher"""
        encryption_key = os.environ.get('ENCRYPTION_KEY')
        
        if not encryption_key:
            # Generate a key from password
            password = os.environ.get('ENCRYPTION_PASSWORD', 'default-password').encode()
            salt = os.environ.get('ENCRYPTION_SALT', 'default-salt').encode()
            
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
                backend=default_backend()
            )
            
            key = base64.urlsafe_b64encode(kdf.derive(password))
        else:
            key = encryption_key.encode() if isinstance(encryption_key, str) else encryption_key
        
        return Fernet(key)
    
    def validate_request(self, request):
        """Validate incoming request for security threats"""
        # Check for suspicious patterns
        suspicious_patterns = [
            r'<script',
            r'javascript:',
            r'onerror=',
            r'onclick=',
            r'onload=',
            r'eval\(',
            r'alert\(',
            r'document\.cookie',
            r'window\.location'
        ]
        
        # Check all request data
        data_to_check = []
        
        if request.json:
            data_to_check.extend(self._flatten_dict(request.json))
        
        if request.form:
            data_to_check.extend(request.form.values())
        
        if request.args:
            data_to_check.extend(request.args.values())
        
        for data in data_to_check:
            if isinstance(data, str):
                for pattern in suspicious_patterns:
                    if re.search(pattern, data, re.IGNORECASE):
                        self._log_security_event('suspicious_request', {
                            'pattern': pattern,
                            'ip': request.remote_addr
                        })
                        return False
        
        # Check request size
        if request.content_length and request.content_length > 10 * 1024 * 1024:  # 10MB
            return False
        
        return True
    
    def _flatten_dict(self, d, parent_key='', sep='_'):
        """Flatten nested dictionary"""
        items = []
        for k, v in d.items():
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, f"{parent_key}{sep}{k}" if parent_key else k, sep=sep))
            elif isinstance(v, list):
                for item in v:
                    if isinstance(item, dict):
                        items.extend(self._flatten_dict(item, f"{parent_key}{sep}{k}" if parent_key else k, sep=sep))
                    else:
                        items.append(item)
            else:
                items.append(v)
        return items
    
    def get_security_headers(self):
        """Get security headers for response"""
        return {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'",
            'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
            'Referrer-Policy': 'strict-origin-when-cross-origin'
        }
    
    def handle_privacy_violation(self, user_id, report_id):
        """Handle privacy violation with severe penalties"""
        from models import db, Penalty, User, Report
        
        user = User.query.get(user_id)
        report = Report.query.get(report_id)
        
        if not user or not report:
            return
        
        # Create penalty
        penalty = Penalty(
            user_id=user_id,
            report_id=report_id,
            penalty_type='privacy_violation',
            reason='Violation of user anonymity and privacy',
            amount=10000,  # Default fine
            start_date=datetime.utcnow(),
            end_date=datetime.utcnow() + timedelta(days=30),  # 30 day suspension
            is_active=True
        )
        
        db.session.add(penalty)
        
        # Deactivate user
        user.is_active = False
        
        # Update report
        report.status = 'resolved'
        report.resolution = 'User penalized for privacy violation'
        report.resolved_at = datetime.utcnow()
        
        db.session.commit()
        
        # Log event
        self._log_security_event('privacy_violation_penalty', {
            'user_id': user_id,
            'report_id': report_id,
            'penalty_amount': 10000
        })
        
        # Invalidate all user sessions
        from app import auth_manager
        auth_manager.invalidate_session(user_id)
    
    def _log_security_event(self, event_type, details):
        """Log security event"""
        event_key = f"security_event:{event_type}:{datetime.utcnow().isoformat()}"
        self.redis.setex(event_key, 2592000, str(details))  # 30 days
        
        # Also log to application logger
        if hasattr(self.app, 'logger'):
            self.app.logger.warning(f"Security Event: {event_type}", extra=details)
    
    def check_rate_limit(self, identifier, action, limit=60, window=60):
        """Check rate limit for action"""
        key = f"rate_limit:{action}:{identifier}"
        current = self.redis.incr(key)
        
        if current == 1:
            self.redis.expire(key, window)
        
        return current <= limit
    
    def detect_anomaly(self, user_id, action, metadata=None):
        """Detect anomalous user behavior"""
        # Track user actions
        action_key = f"user_actions:{user_id}:{action}"
        count = self.redis.incr(action_key)
        
        if count == 1:
            self.redis.expire(action_key, 3600)  # 1 hour window
        
        # Define thresholds for different actions
        thresholds = {
            'login_attempt': 10,
            'password_reset': 3,
            'profile_update': 20,
            'message_send': 100,
            'post_create': 50,
            'report_submit': 5
        }
        
        threshold = thresholds.get(action, 50)
        
        if count > threshold:
            self._log_security_event('anomaly_detected', {
                'user_id': user_id,
                'action': action,
                'count': count,
                'threshold': threshold,
                'metadata': metadata
            })
            return True
        
        return False
    
    def validate_input_length(self, data, field_limits):
        """Validate input field lengths"""
        for field, limit in field_limits.items():
            if field in data and len(str(data[field])) > limit:
                return False, f"{field} exceeds maximum length of {limit}"
        
        return True, None
    
    def generate_secure_filename(self, original_filename):
        """Generate secure filename for uploads"""
        # Remove path components
        filename = os.path.basename(original_filename)
        
        # Remove non-alphanumeric characters except dots and hyphens
        filename = re.sub(r'[^a-zA-Z0-9.\-_]', '', filename)
        
        # Add random prefix
        prefix = secrets.token_hex(8)
        
        return f"{prefix}_{filename}"
    
    def scan_for_malware_patterns(self, content):
        """Scan content for potential malware patterns"""
        malware_patterns = [
            r'<iframe',
            r'<embed',
            r'<object',
            r'\.exe',
            r'\.dll',
            r'\.bat',
            r'\.cmd',
            r'\.scr',
            r'\.vbs',
            r'\.js',
            r'base64,',
            r'data:text/html'
        ]
        
        for pattern in malware_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return True
        
        return False
    
    def generate_csrf_token(self, session_id):
        """Generate CSRF token for session"""
        token = secrets.token_urlsafe(32)
        csrf_key = f"csrf:{session_id}"
        
        self.redis.setex(csrf_key, 3600, token)  # 1 hour expiry
        
        return token
    
    def validate_csrf_token(self, session_id, token):
        """Validate CSRF token"""
        csrf_key = f"csrf:{session_id}"
        stored_token = self.redis.get(csrf_key)
        
        if stored_token and stored_token.decode('utf-8') == token:
            return True
        
        return False


# Standalone encryption functions
def encrypt_field(data):
    """Encrypt sensitive field data"""
    if not data:
        return None
    
    key = os.environ.get('ENCRYPTION_KEY', 'default-encryption-key')
    
    # Create cipher
    if len(key) < 32:
        key = hashlib.sha256(key.encode()).digest()
    
    key_b64 = base64.urlsafe_b64encode(key)
    cipher = Fernet(key_b64)
    
    # Encrypt data
    encrypted = cipher.encrypt(data.encode() if isinstance(data, str) else data)
    
    return encrypted.decode() if isinstance(encrypted, bytes) else encrypted


def decrypt_field(encrypted_data):
    """Decrypt sensitive field data"""
    if not encrypted_data:
        return None
    
    key = os.environ.get('ENCRYPTION_KEY', 'default-encryption-key')
    
    # Create cipher
    if len(key) < 32:
        key = hashlib.sha256(key.encode()).digest()
    
    key_b64 = base64.urlsafe_b64encode(key)
    cipher = Fernet(key_b64)
    
    # Decrypt data
    try:
        decrypted = cipher.decrypt(encrypted_data.encode() if isinstance(encrypted_data, str) else encrypted_data)
        return decrypted.decode() if isinstance(decrypted, bytes) else decrypted
    except Exception:
        return None


def sanitize_input(text):
    """Sanitize user input to prevent XSS"""
    if not text:
        return text
    
    # Remove any HTML tags except allowed ones
    cleaned = bleach.clean(
        text,
        tags=['b', 'i', 'u', 'br', 'p', 'strong', 'em'],
        attributes={},
        strip=True
    )
    
    # Additional sanitization
    cleaned = html.escape(cleaned)
    
    # Unescape allowed tags
    allowed_tags = ['b', 'i', 'u', 'br', 'p', 'strong', 'em']
    for tag in allowed_tags:
        cleaned = cleaned.replace(f'&lt;{tag}&gt;', f'<{tag}>')
        cleaned = cleaned.replace(f'&lt;/{tag}&gt;', f'</{tag}>')
    
    return cleaned


def validate_email(email):
    """Validate email format"""
    if not email:
        return False
    
    # Basic email regex
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if not re.match(pattern, email):
        return False
    
    # Additional checks
    if len(email) > 254:  # Max email length
        return False
    
    # Check for suspicious patterns
    suspicious = [
        'script',
        'javascript',
        'onclick',
        '../',
        'file://',
        'data:'
    ]
    
    email_lower = email.lower()
    for pattern in suspicious:
        if pattern in email_lower:
            return False
    
    return True


def validate_url(url):
    """Validate URL format and safety"""
    if not url:
        return False
    
    # URL regex
    pattern = r'^https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(/.*)?$'
    
    if not re.match(pattern, url):
        return False
    
    # Check for dangerous URLs
    dangerous_patterns = [
        'javascript:',
        'data:',
        'vbscript:',
        'file://',
        'about:',
        'chrome:',
        '127.0.0.1',
        'localhost'
    ]
    
    url_lower = url.lower()
    for pattern in dangerous_patterns:
        if pattern in url_lower:
            return False
    
    return True


def hash_data(data):
    """Hash data using SHA-256"""
    if isinstance(data, str):
        data = data.encode()
    
    return hashlib.sha256(data).hexdigest()


def generate_anonymous_id(prefix='USER'):
    """Generate anonymous identifier"""
    random_part = secrets.token_hex(6).upper()
    timestamp_part = hex(int(datetime.utcnow().timestamp()))[2:].upper()
    
    return f"{prefix}_{timestamp_part}_{random_part}"


class ContentModerator:
    """Content moderation for safety"""
    
    def __init__(self):
        self.harmful_patterns = [
            r'\bsuicid[e|al]\b',
            r'\bself[- ]?harm\b',
            r'\bkill[- ]?(myself|yourself)\b',
            r'\bcut[- ]?(myself|yourself)\b',
            r'\boverdos[e|ing]\b',
            r'\bend[- ]?(my|your)[- ]?life\b'
        ]
        
        self.support_keywords = [
            'help', 'support', 'crisis', 'emergency',
            'therapist', 'counselor', 'hotline'
        ]
    
    def check_content(self, text):
        """Check content for concerning patterns"""
        if not text:
            return {'safe': True}
        
        text_lower = text.lower()
        concerns = []
        
        # Check for harmful patterns
        for pattern in self.harmful_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                concerns.append('harmful_content')
                break
        
        # Check if seeking help
        seeking_help = any(keyword in text_lower for keyword in self.support_keywords)
        
        if concerns and not seeking_help:
            return {
                'safe': False,
                'concerns': concerns,
                'action': 'alert_support'
            }
        
        return {'safe': True}
    
    def get_support_resources(self):
        """Get mental health support resources"""
        return {
            'crisis_lines': [
                {'name': 'National Suicide Prevention Lifeline', 'number': '988'},
                {'name': 'Crisis Text Line', 'number': 'Text HOME to 741741'},
                {'name': 'International Association for Suicide Prevention', 'url': 'https://www.iasp.info'}
            ],
            'message': 'If you are in crisis, please reach out for help. You are not alone.'
        }


class IPSecurityManager:
    """Manage IP-based security"""
    
    def __init__(self, redis_client):
        self.redis = redis_client
    
    def is_ip_blocked(self, ip_address):
        """Check if IP is blocked"""
        block_key = f"blocked_ip:{ip_address}"
        return self.redis.exists(block_key)
    
    def block_ip(self, ip_address, duration=3600, reason='suspicious_activity'):
        """Block IP address"""
        block_key = f"blocked_ip:{ip_address}"
        self.redis.setex(block_key, duration, reason)
    
    def track_ip_activity(self, ip_address, action):
        """Track IP activity"""
        key = f"ip_activity:{ip_address}:{action}"
        count = self.redis.incr(key)
        
        if count == 1:
            self.redis.expire(key, 3600)  # 1 hour window
        
        # Auto-block if too many suspicious actions
        if count > 100:
            self.block_ip(ip_address, 86400, 'excessive_activity')
            return False
        
        return True
    
    def get_ip_reputation(self, ip_address):
        """Get IP reputation score"""
        # Check various factors
        factors = {
            'failed_logins': f"failed_login:{ip_address}",
            'reports': f"ip_reports:{ip_address}",
            'violations': f"ip_violations:{ip_address}"
        }
        
        score = 100  # Start with perfect score
        
        for factor, key in factors.items():
            count = self.redis.get(key)
            if count:
                score -= int(count) * 10
        
        return max(0, score)
