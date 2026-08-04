"""
Security module for Thera Social  -  Version A26 (B175)

A26 changes (all additive or widening; nothing that validated before stops validating):
  1. validate_username is Unicode-aware. A25 accepted only ^[a-zA-Z0-9_]{3,20}$, which
     made a Hebrew/Arabic/Cyrillic username impossible. The 3-20 length policy is
     unchanged. Invisible, direction-flipping and compatibility look-alike characters
     are rejected so one account cannot render identically to another.
  2. normalize_username() + derive_username_from_email(). The latter fixes a real signup
     blocker: the raw email local part was used as the default username, so anyone whose
     address contained a dot ("john.doe@...") failed registration outright.
  3. ContentModerator no longer blocks the words hate/violence/abuse. check_content gates
     PRIVATE MESSAGES, so on a mental-health platform that stopped members telling their
     support person "I'm a survivor of abuse". Prohibited patterns are now second-person
     attacks ("kill yourself"); first-person disclosures ("kill myself") are delivered
     with support resources attached.
  4. crisis/harmful regexes fixed - [e|al] and [e|ing] were character classes, not
     alternations, so "suicidal" and "overdosing" were never detected at all.
  5. verify_password and validate_csrf_token use constant-time comparison.
  6. sanitize_input returns '' for non-string input instead of raising.

Security module for Thera Social
Handles encryption, sanitization, and security measures
Complete version with all features and fixes
"""
import os
import re
import html
import unicodedata
import secrets
import hashlib
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import base64
import bleach
import jwt
from functools import wraps
from flask import session, jsonify, request
import logging

logger = logging.getLogger(__name__)

class SecurityManager:
    """Enhanced security manager for the application"""
    
    def __init__(self, app=None, redis_client=None):
        self.app = app
        self.redis = redis_client
        self.secret_key = None
        self.encryption_key = None
        self.cipher_suite = None
        self.allowed_tags = ['b', 'i', 'u', 'br', 'p', 'strong', 'em']
        self.allowed_attributes = {}
        
        if app:
            self.init_app(app, redis_client)
    
    def init_app(self, app, redis_client=None):
        """Initialize security with Flask app"""
        self.app = app
        self.redis = redis_client
        self.secret_key = app.config.get('SECRET_KEY', 'dev-key-change-in-production')
        self.cipher_suite = self._init_cipher()
        
        # Generate encryption key from secret
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'stable_salt',  # In production, use a proper salt management
            iterations=100000,
            backend=default_backend()
        )
        key = base64.urlsafe_b64encode(kdf.derive(self.secret_key.encode()))
        self.encryption_key = key
        self.fernet = Fernet(key)
    
    def _init_cipher(self):
        """Initialize encryption cipher"""
        encryption_key = os.environ.get('ENCRYPTION_KEY')
        
        if encryption_key and len(encryption_key) == 44:
            # Valid Fernet key provided
            try:
                if isinstance(encryption_key, str):
                    key = encryption_key.encode()
                else:
                    key = encryption_key
                return Fernet(key)
            except Exception:
                pass
        
        # Fall back to deriving a key
        password = encryption_key or os.environ.get('ENCRYPTION_PASSWORD', 'default-password')
        if isinstance(password, str):
            password = password.encode()
        
        salt = os.environ.get('ENCRYPTION_SALT', 'default-salt')
        if isinstance(salt, str):
            salt = salt.encode()
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        
        key = base64.urlsafe_b64encode(kdf.derive(password))
        return Fernet(key)
    
    def validate_request(self, request):
        """Validate incoming request for security threats"""
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
        
        data_to_check = []
        
        try:
            if request.is_json and request.json:
                data_to_check.extend(self._flatten_dict(request.json))
        except:
            pass 
        
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
        
        penalty = Penalty(
            user_id=user_id,
            report_id=report_id,
            penalty_type='privacy_violation',
            reason='Violation of user anonymity and privacy',
            amount=10000,
            start_date=datetime.utcnow(),
            end_date=datetime.utcnow() + timedelta(days=30),
            is_active=True
        )
        
        db.session.add(penalty)
        user.is_active = False
        
        report.status = 'resolved'
        report.resolution = 'User penalized for privacy violation'
        report.resolved_at = datetime.utcnow()
        
        db.session.commit()
        
        self._log_security_event('privacy_violation_penalty', {
            'user_id': user_id,
            'report_id': report_id,
            'penalty_amount': 10000
        })
        
        from app import auth_manager
        auth_manager.invalidate_session(user_id)
    
    def _log_security_event(self, event_type, details):
        """Log security event"""
        if self.redis:
            event_key = f"security_event:{event_type}:{datetime.utcnow().isoformat()}"
            self.redis.setex(event_key, 2592000, str(details))
        
        if hasattr(self.app, 'logger'):
            self.app.logger.warning(f"Security Event: {event_type}", extra=details)
        else:
            logger.warning(f"Security Event: {event_type}", extra=details)
    
    def check_rate_limit(self, identifier, action, limit=60, window=60):
        """Check rate limit for action"""
        if not self.redis:
            return True
            
        key = f"rate_limit:{action}:{identifier}"
        current = self.redis.incr(key)
        
        if current == 1:
            self.redis.expire(key, window)
        
        return current <= limit
    
    def detect_anomaly(self, user_id, action, metadata=None):
        """Detect anomalous user behavior"""
        if not self.redis:
            return False
            
        action_key = f"user_actions:{user_id}:{action}"
        count = self.redis.incr(action_key)
        
        if count == 1:
            self.redis.expire(action_key, 3600)
        
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
        filename = os.path.basename(original_filename)
        filename = re.sub(r'[^a-zA-Z0-9.\-_]', '', filename)
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
    
    def generate_csrf_token(self, session_id=None):
        """Generate CSRF token for session"""
        if session_id and self.redis:
            token = secrets.token_urlsafe(32)
            csrf_key = f"csrf:{session_id}"
            self.redis.setex(csrf_key, 3600, token)
            return token
        else:
            # Fallback to session-based CSRF
            if 'csrf_token' not in session:
                session['csrf_token'] = secrets.token_hex(32)
            return session['csrf_token']
    
    def validate_csrf_token(self, session_id, token):
        """Validate CSRF token"""
        if session_id and self.redis:
            csrf_key = f"csrf:{session_id}"
            stored_token = self.redis.get(csrf_key)
            
            # A26: constant-time comparison (see verify_password).
            try:
                if stored_token and token and secrets.compare_digest(
                        stored_token if isinstance(stored_token, bytes) else str(stored_token).encode('utf-8'),
                        str(token).encode('utf-8')):
                    return True
            except (TypeError, UnicodeError):
                return False
        else:
            # Fallback to session-based CSRF
            expected = session.get('csrf_token')
            if not expected or not token:
                return False
            try:
                # compare_digest raises TypeError on non-ASCII str; compare bytes.
                return secrets.compare_digest(str(expected).encode('utf-8'), str(token).encode('utf-8'))
            except (TypeError, UnicodeError):
                return False
        
        return False

# Initialize global instance
security_manager = SecurityManager()

def init_security(app, redis_client=None):
    """Initialize security with Flask app"""
    security_manager.init_app(app, redis_client)
    return security_manager

# Standalone encryption functions
def get_fernet_cipher():
    """Get a Fernet cipher using the configured key"""
    encryption_key = os.environ.get('ENCRYPTION_KEY')
    
    # Check if it's a valid 44-char Fernet key
    if encryption_key and len(encryption_key) == 44:
        try:
            if isinstance(encryption_key, str):
                key = encryption_key.encode()
            else:
                key = encryption_key
            return Fernet(key)
        except Exception:
            pass
    
    # Fall back to deriving a key from password
    password = encryption_key or os.environ.get('ENCRYPTION_PASSWORD', 'default-encryption-key')
    if isinstance(password, str):
        password = password.encode()
    
    salt = os.environ.get('ENCRYPTION_SALT', 'default-salt')
    if isinstance(salt, str):
        salt = salt.encode()
    
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
        backend=default_backend()
    )
    
    key = base64.urlsafe_b64encode(kdf.derive(password))
    return Fernet(key)

def encrypt_field(data):
    """Encrypt sensitive field data"""
    if not data:
        return None
    
    try:
        cipher = get_fernet_cipher()
        
        # Ensure data is bytes
        if isinstance(data, str):
            data_bytes = data.encode('utf-8')
        else:
            data_bytes = data
        
        # Encrypt
        encrypted = cipher.encrypt(data_bytes)
        
        # Return as string for database storage
        if isinstance(encrypted, bytes):
            return encrypted.decode('utf-8')
        return encrypted
        
    except Exception as e:
        logger.error(f"Encryption error: {e}")
        return None

def decrypt_field(encrypted_data):
    """Decrypt sensitive field data"""
    if not encrypted_data:
        return None
    
    try:
        cipher = get_fernet_cipher()
        
        # Ensure encrypted_data is bytes
        if isinstance(encrypted_data, str):
            encrypted_bytes = encrypted_data.encode('utf-8')
        else:
            encrypted_bytes = encrypted_data
        
        # Decrypt
        decrypted = cipher.decrypt(encrypted_bytes)
        
        # Return as string
        if isinstance(decrypted, bytes):
            return decrypted.decode('utf-8')
        return decrypted
        
    except Exception as e:
        logger.error(f"Decryption error: {e}")
        return None

def sanitize_input(text):
    """
    Sanitize user input to prevent XSS attacks.
    FIXED: Removed double-escaping issue that was breaking HTML sanitization.
    """
    if not text:
        return text
    
    # A26: bleach.clean() raises TypeError on a non-string (e.g. a JSON number or
    # list arriving in a field the caller expected to be text). Return it untouched
    # so a malformed payload produces a validation error, not a 500.
    if not isinstance(text, str):
        return ''
    
    # Use bleach to clean and allow only safe tags
    # This is sufficient for XSS protection
    # NOTE (A26): bleach preserves non-ASCII text, so Hebrew/Arabic/Cyrillic
    # usernames and message bodies pass through unchanged. It does escape & and <.
    cleaned = bleach.clean(
        text,
        tags=['b', 'i', 'u', 'br', 'p', 'strong', 'em'],
        attributes={},
        strip=True
    )
    
    return cleaned

def validate_email(email):
    """Validate email format"""
    if not email:
        return False
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if not re.match(pattern, email):
        return False
    
    if len(email) > 254:
        return False
    
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

# =====================================================================
# A26: Unicode-aware username validation.
#
# A25 accepted only ^[a-zA-Z0-9_]{3,20}$, which made a Hebrew (or Arabic,
# or Cyrillic) username impossible. This is a strict WIDENING: every name
# A25 accepted is still accepted, and the length policy (3-20) is unchanged.
#
# Added: letters in ANY script, combining marks (Hebrew niqqud, Arabic
# harakat, Devanagari matras), hyphen, apostrophe and single inner spaces.
# Still rejected: leading/trailing/doubled separators, and any invisible or
# direction-flipping character - those let one account impersonate another
# on screen, which matters in an app where alerts read "<username>'s mood...".
# =====================================================================

USERNAME_MIN_LENGTH = 3
USERNAME_MAX_LENGTH = 20

# Legacy A25 rule, kept verbatim so nothing that used to validate stops doing so.
_LEGACY_USERNAME_RE = re.compile(r'^[a-zA-Z0-9_]{3,20}$')

# Separators allowed INSIDE a name only, never doubled.
_USERNAME_SEPARATORS = frozenset("-'\u2019 ")

# Categories that must never appear: control characters, bidi overrides and
# zero-width joiners, surrogates, private-use and unassigned code points.
_USERNAME_FORBIDDEN_CATEGORIES = ('Cc', 'Cf', 'Cs', 'Co', 'Cn')

# Code points that ARE letters (category Lo/Lm, so str.isalnum() is True) but
# render as nothing. Without this, "admin" and "admin<U+3164>" are two different,
# visually identical accounts.
_USERNAME_INVISIBLE_LETTERS = frozenset(
    '\u115f'   # HANGUL CHOSEONG FILLER
    '\u1160'   # HANGUL JUNGSEONG FILLER
    '\u3164'   # HANGUL FILLER
    '\uffa0'   # HALFWIDTH HANGUL FILLER
    '\u17b4'   # KHMER VOWEL INHERENT AQ
    '\u17b5'   # KHMER VOWEL INHERENT AA
    '\u2065'   # unassigned in some UCD versions
    '\u180e'   # MONGOLIAN VOWEL SEPARATOR
)


# Ranges that are invisible or direction-flipping but are NOT category Cc/Cf/Cn.
# The gap that matters: variation selectors, the combining grapheme joiner and the
# Mongolian free-variation selectors are category Mn (a "mark"), so a marks-aware
# rule admits them - and "admin" + U+FE0F renders identically to "admin".
_USERNAME_IGNORABLE_RANGES = (
    (0x00AD, 0x00AD),      # SOFT HYPHEN
    (0x034F, 0x034F),      # COMBINING GRAPHEME JOINER
    (0x061C, 0x061C),      # ARABIC LETTER MARK
    (0x115F, 0x1160),      # HANGUL fillers
    (0x17B4, 0x17B5),      # KHMER inherent vowels
    (0x180B, 0x180F),      # MONGOLIAN free variation selectors
    (0x200B, 0x200F),      # zero-width space/joiners, LRM/RLM
    (0x202A, 0x202E),      # bidi embedding/override
    (0x2060, 0x206F),      # word joiner, invisible operators, bidi formatting
    (0x3164, 0x3164),      # HANGUL FILLER
    (0xFE00, 0xFE0F),      # VARIATION SELECTOR 1-16
    (0xFEFF, 0xFEFF),      # ZERO WIDTH NO-BREAK SPACE
    (0xFFA0, 0xFFA0),      # HALFWIDTH HANGUL FILLER
    (0xFFF0, 0xFFF8),      # unassigned/interlinear
    (0x1D173, 0x1D17A),    # musical formatting
    (0xE0000, 0xE0FFF),    # tags + VARIATION SELECTOR SUPPLEMENT
)

# Character categories a username may be built from. Deliberately excludes No and Nl
# (superscripts, circled digits, Roman numerals) - they are "numeric" to str.isalnum()
# but are decorative look-alikes, not name characters.
_USERNAME_LETTER_CATEGORIES = frozenset(('Lu', 'Ll', 'Lt', 'Lm', 'Lo'))
_USERNAME_DIGIT_CATEGORIES = frozenset(('Nd',))
_USERNAME_MARK_CATEGORIES = frozenset(('Mn', 'Mc', 'Me'))


def _is_username_ignorable(ch):
    """True for characters that render as nothing or flip text direction."""
    cp = ord(ch)
    for low, high in _USERNAME_IGNORABLE_RANGES:
        if low <= cp <= high:
            return True
    return ch in _USERNAME_INVISIBLE_LETTERS


# Compatibility-decomposable code points that are nonetheless ORDINARY LETTERS in a
# living script. THAI SARA AM is one of the most common Thai vowels; the Croatian and
# Dutch digraphs and Armenian ech-yiwn are real letters people have in their names;
# the Hangul Compatibility Jamo block is how Korean jamo are normally typed.
_USERNAME_COMPAT_LETTERS = frozenset(
    '\u0e33'                      # THAI CHARACTER SARA AM
    '\u0eb3'                      # LAO VOWEL SIGN AM
    '\u0587'                      # ARMENIAN SMALL LIGATURE ECH YIWN
    '\u0132\u0133'                # LATIN IJ / ij  (Dutch)
    '\u01c4\u01c5\u01c6'          # DZ with caron  (Croatian)
    '\u01c7\u01c8\u01c9'          # LJ
    '\u01ca\u01cb\u01cc'          # NJ
    '\u01f1\u01f2\u01f3'          # DZ
) | frozenset(chr(c) for c in range(0x3131, 0x3164))   # Hangul Compatibility Jamo


def _is_username_confusable(ch):
    """True for compatibility-decomposable look-alikes.

    NFC (unlike NFKC) does not fold these, so fullwidth "\uff41", math-bold and
    circled forms would otherwise pass as distinct-but-identical-looking names.
    Verified against Hebrew, Arabic, Devanagari, Tamil, Greek, Cyrillic, CJK,
    Hangul and accented Latin: no legitimate name character is affected.
    """
    if ch in _USERNAME_COMPAT_LETTERS:
        return False
    return unicodedata.decomposition(ch).startswith('<')


def _is_username_word_char(ch):
    """Letter (any script), decimal digit, underscore, or a combining mark.

    Python's re \\w excludes combining marks, which would reject exactly the names
    this change exists to support (Hebrew niqqud, Arabic harakat, Devanagari
    matras) and anything typed on macOS/iOS, whose input methods emit NFD text.
    """
    if ch == '_':
        return True
    if _is_username_ignorable(ch) or _is_username_confusable(ch):
        return False
    category = unicodedata.category(ch)
    return (category in _USERNAME_LETTER_CATEGORIES
            or category in _USERNAME_DIGIT_CATEGORIES
            or category in _USERNAME_MARK_CATEGORIES)


def _is_username_start_char(ch):
    """A name must BEGIN with something with a body of its own - not a mark.

    Without this, '\u0301abc' validates and renders as floating diacritics.
    """
    return _is_username_word_char(ch) and not unicodedata.category(ch).startswith('M')


def normalize_username(username):
    """NFC-normalise and strip. Callers should STORE this value.

    Storing the normalised form is what stops "jose\\u0301" and "jos\\u00e9"
    becoming two rows that render identically.
    """
    if not username or not isinstance(username, str):
        return ''
    return unicodedata.normalize('NFC', username).strip()


def validate_username(username):
    """Validate username format (A26: any script, 3-20 characters)."""
    try:
        if not username or not isinstance(username, str):
            return False
        # Length is checked on the RAW string too: callers may store the raw
        # value, and NFD text can be far longer than its NFC form.
        if len(username) > USERNAME_MAX_LENGTH * 8:
            return False
        candidate = normalize_username(username)
        if not candidate:
            return False
        if not (USERNAME_MIN_LENGTH <= len(candidate) <= USERNAME_MAX_LENGTH):
            return False
        # Applies to both rules below - the one deliberate narrowing vs A25.
        if any(unicodedata.category(ch) in _USERNAME_FORBIDDEN_CATEGORIES for ch in candidate):
            return False
        if any(_is_username_ignorable(ch) for ch in candidate):
            return False
        # Legacy ASCII rule first - cheapest, and guarantees the superset.
        if _LEGACY_USERNAME_RE.match(candidate):
            return True
        # Unicode rule: must contain something visible, must start and end on a
        # word character, and may not contain doubled separators.
        if not any(unicodedata.category(ch)[0] in ('L', 'N') for ch in candidate):
            return False
        if not _is_username_start_char(candidate[0]) or not _is_username_word_char(candidate[-1]):
            return False
        previous_was_separator = False
        for ch in candidate:
            if _is_username_word_char(ch):
                previous_was_separator = False
            elif ch in _USERNAME_SEPARATORS:
                if previous_was_separator:
                    return False
                previous_was_separator = True
            else:
                return False
        return True
    except Exception as exc:      # never let a validation edge case 500 a request
        logger.warning(f"validate_username error: {exc}")
        return False


# Marker so callers can detect this capability instead of duplicating the rule.
validate_username.a26_unicode_aware = True


def derive_username_from_email(email):
    """Build a VALID username from an email local part, or '' if impossible.

    A25 used the raw local part, so anyone whose address contained a dot or a
    plus - "john.doe@...", the majority of real addresses - failed registration
    with "Invalid username format" and had to invent a name before they could
    sign up. Dots/plus/hyphens become underscores, the result is padded to the
    3-character minimum and trimmed to the 20-character maximum.
    """
    try:
        if not email or not isinstance(email, str) or '@' not in email:
            return ''
        local = normalize_username(email.split('@')[0])
        if not local:
            return ''
        # Map anything not allowed onto an underscore, then collapse runs.
        mapped = ''.join(ch if _is_username_word_char(ch) else '_' for ch in local)
        mapped = re.sub(r'_{2,}', '_', mapped).strip('_')
        # Drop any leading combining marks so the result starts on a real glyph.
        while mapped and not _is_username_start_char(mapped[0]):
            mapped = mapped[1:]
        if not mapped:
            return ''
        mapped = mapped[:USERNAME_MAX_LENGTH]
        while len(mapped) < USERNAME_MIN_LENGTH:
            mapped += '0'
        return mapped if validate_username(mapped) else ''
    except Exception as exc:
        logger.warning(f"derive_username_from_email error: {exc}")
        return ''

def validate_password_strength(password):
    """Check password strength"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    
    if not re.search(r'\d', password):
        return False, "Password must contain at least one number"
    
    return True, "Password is strong"

def validate_url(url):
    """Validate URL format and safety"""
    if not url:
        return False
    
    pattern = r'^https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(/.*)?$'
    
    if not re.match(pattern, url):
        return False
    
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

def generate_token(length=32):
    """Generate a secure random token"""
    return secrets.token_hex(length)

def hash_password(password):
    """Hash password using PBKDF2"""
    salt = secrets.token_bytes(32)
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
        backend=default_backend()
    )
    key = kdf.derive(password.encode())
    return base64.b64encode(salt + key).decode('utf-8')

def verify_password(password, password_hash):
    """Verify password against hash"""
    try:
        decoded = base64.b64decode(password_hash.encode())
        salt = decoded[:32]
        stored_key = decoded[32:]
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        new_key = kdf.derive(password.encode())
        
        # A26: constant-time comparison. A plain `==` on bytes short-circuits on the
        # first differing byte, which leaks how much of the hash a guess got right.
        return secrets.compare_digest(new_key, stored_key)
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False

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

def generate_jwt_token(user_id, expiry_hours=24):
    """Generate JWT token for user authentication"""
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(hours=expiry_hours),
        'iat': datetime.utcnow()
    }
    
    secret_key = security_manager.secret_key or os.environ.get('SECRET_KEY', 'default-key')
    
    token = jwt.encode(
        payload,
        secret_key,
        algorithm='HS256'
    )
    
    return token

def verify_jwt_token(token):
    """Verify and decode JWT token"""
    try:
        secret_key = security_manager.secret_key or os.environ.get('SECRET_KEY', 'default-key')
        
        payload = jwt.decode(
            token,
            secret_key,
            algorithms=['HS256']
        )
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def login_required(f):
    """Decorator to require login for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator to require admin privileges"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        
        if not session.get('is_admin', False):
            return jsonify({'error': 'Admin privileges required'}), 403
        
        return f(*args, **kwargs)
    return decorated_function

def secure_filename(filename):
    """Sanitize filename for safe storage"""
    # Remove any path components
    filename = filename.replace('/', '').replace('\\', '')
    
    # Remove special characters except dots and underscores
    filename = re.sub(r'[^a-zA-Z0-9._-]', '', filename)
    
    # Limit length
    name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
    if ext:
        return f"{name[:50]}.{ext[:10]}"
    return filename[:60]

class RateLimiter:
    """Simple rate limiter for API endpoints"""
    
    def __init__(self):
        self.attempts = {}
    
    def check_rate_limit(self, identifier, max_attempts=5, window_minutes=15):
        """Check if rate limit is exceeded"""
        now = datetime.utcnow()
        window_start = now - timedelta(minutes=window_minutes)
        
        # Clean old attempts
        if identifier in self.attempts:
            self.attempts[identifier] = [
                attempt for attempt in self.attempts[identifier]
                if attempt > window_start
            ]
        else:
            self.attempts[identifier] = []
        
        # Check limit
        if len(self.attempts[identifier]) >= max_attempts:
            return False
        
        # Add current attempt
        self.attempts[identifier].append(now)
        return True
    
    def reset(self, identifier):
        """Reset rate limit for identifier"""
        if identifier in self.attempts:
            del self.attempts[identifier]

# Global rate limiter instance
rate_limiter = RateLimiter()

def rate_limit(max_attempts=5, window_minutes=15):
    """Decorator for rate limiting routes"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            identifier = request.remote_addr
            
            if not rate_limiter.check_rate_limit(identifier, max_attempts, window_minutes):
                return jsonify({'error': 'Rate limit exceeded. Please try again later.'}), 429
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

class ContentModerator:
    """Content moderation for user-generated content"""
    
    def __init__(self):
        # A26 FIX: A25 read r'\b(?:hate|violence|abuse)\b' here, and check_content()
        # gates PRIVATE MESSAGES (app.py). On a mental health platform that meant a
        # member could not tell their support person "I'm a survivor of abuse" or
        # "I'm dealing with domestic violence" - exactly the disclosures this product
        # exists to carry. Those words are gone.
        #
        # What belongs here is harm DIRECTED AT another person. The distinction that
        # matters is grammatical: second person ("kill yourself") is an attack and is
        # refused; first person ("kill myself") is a disclosure and must be delivered
        # so the person's support network can actually respond to it.
        self.prohibited_patterns = [
            r'\bkill[- ]?yourself\b',
            r'\bcut[- ]?yourself\b',
            r'\bharm[- ]?yourself\b',
            r'\bend[- ]?your[- ]?life\b',
            r'\bgo\s+(?:die|kill\s+yourself)\b',
            r'\byou\s+(?:should|deserve\s+to|ought\s+to)\s+(?:die|overdose|kill\s+yourself)\b',
        ]

        # Patterns that might indicate self-harm or crisis (first person only)
        self.crisis_patterns = [
            r'\b(?:suicide|self.?harm|kill.?myself)\b',
            r'\b(?:end.?it.?all|no.?point.?living)\b',
        ]

        # First person only - see the note above. These raise a support signal; they
        # never block delivery. A25 wrote [e|al] and [e|ing], which are character
        # classes rather than alternations, so "suicidal" and "overdosing" - the most
        # common phrasings - were never detected at all.
        self.harmful_patterns = [
            r'\bsuicid(?:e|al)\b',
            r'\bself[- ]?harm\b',
            r'\bkill[- ]?myself\b',
            r'\bcut[- ]?myself\b',
            r'\boverdos(?:e|ing)\b',
            r'\bend[- ]?my[- ]?life\b',
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
        
        # Check for crisis content
        for pattern in self.crisis_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return {
                    'safe': False,
                    'type': 'crisis',
                    'message': 'If you are in crisis, please reach out for help. Crisis hotline: 988'
                }
        
        # Check for harmful content
        for pattern in self.harmful_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                concerns.append('harmful_content')
                break
        
        # Check for prohibited content
        for pattern in self.prohibited_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return {
                    'safe': False,
                    'type': 'prohibited',
                    'message': 'Content contains prohibited terms'
                }
        
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

# Global content moderator instance
content_moderator = ContentModerator()

class IPSecurityManager:
    """Manage IP-based security"""
    
    def __init__(self, redis_client):
        self.redis = redis_client
    
    def is_ip_blocked(self, ip_address):
        """Check if IP is blocked"""
        if not self.redis:
            return False
        block_key = f"blocked_ip:{ip_address}"
        return self.redis.exists(block_key)
    
    def block_ip(self, ip_address, duration=3600, reason='suspicious_activity'):
        """Block IP address"""
        if not self.redis:
            return
        block_key = f"blocked_ip:{ip_address}"
        self.redis.setex(block_key, duration, reason)
    
    def track_ip_activity(self, ip_address, action):
        """Track IP activity"""
        if not self.redis:
            return True
            
        key = f"ip_activity:{ip_address}:{action}"
        count = self.redis.incr(key)
        
        if count == 1:
            self.redis.expire(key, 3600)
        
        if count > 100:
            self.block_ip(ip_address, 86400, 'excessive_activity')
            return False
        
        return True
    
    def get_ip_reputation(self, ip_address):
        """Get IP reputation score"""
        if not self.redis:
            return 100
            
        factors = {
            'failed_logins': f"failed_login:{ip_address}",
            'reports': f"ip_reports:{ip_address}",
            'violations': f"ip_violations:{ip_address}"
        }
        
        score = 100
        
        for factor, key in factors.items():
            count = self.redis.get(key)
            if count:
                score -= int(count) * 10
        
        return max(0, score)

# Export all functions and classes
__all__ = [
    'SecurityManager',
    'security_manager',
    'init_security',
    'get_fernet_cipher',
    'encrypt_field',
    'decrypt_field',
    'sanitize_input',
    'validate_email',
    'validate_username',
    'validate_password_strength',
    'validate_url',
    'generate_token',
    'hash_password',
    'verify_password',
    'hash_data',
    'generate_anonymous_id',
    'generate_jwt_token',
    'verify_jwt_token',
    'login_required',
    'admin_required',
    'secure_filename',
    'RateLimiter',
    'rate_limiter',
    'rate_limit',
    'ContentModerator',
    'content_moderator',
    'IPSecurityManager'
]
