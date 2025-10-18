"""
Authentication module for Thera Social
Handles user authentication, sessions, and token management
"""
import os
import secrets
import hashlib
import jwt
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, g
from werkzeug.security import generate_password_hash, check_password_hash
import redis

class AuthManager:
    """Manages authentication and sessions"""
    
    def __init__(self, app, db, redis_client):
        self.app = app
        self.db = db
        self.redis = redis_client
        self.jwt_secret = os.environ.get('JWT_SECRET', secrets.token_urlsafe(32))
        self.session_timeout = 86400  # 24 hours
        
    def hash_password(self, password):
        """Hash password using werkzeug with pbkdf2"""
        return generate_password_hash(
            password,
            method='pbkdf2:sha256',
            salt_length=16
        )
    
    def verify_password(self, password, password_hash):
        """Verify password against hash"""
        return check_password_hash(password_hash, password)
    
    def create_session(self, user_id):
        """Create user session in Redis"""
        session_id = secrets.token_urlsafe(32)
        session_key = f"session:{session_id}"
        
        session_data = {
            'user_id': user_id,
            'created_at': datetime.utcnow().isoformat(),
            'last_activity': datetime.utcnow().isoformat()
        }
        
        # Store session in Redis
        self.redis.hset(session_key, mapping=session_data)
        self.redis.expire(session_key, self.session_timeout)
        
        # Track active sessions for user
        user_sessions_key = f"user_sessions:{user_id}"
        self.redis.sadd(user_sessions_key, session_id)
        self.redis.expire(user_sessions_key, self.session_timeout)
        
        return session_id
    
    def get_session(self, session_id):
        """Get session from Redis"""
        session_key = f"session:{session_id}"
        session_data = self.redis.hgetall(session_key)
        
        if not session_data:
            return None
        
        # Update last activity
        self.redis.hset(session_key, 'last_activity', datetime.utcnow().isoformat())
        self.redis.expire(session_key, self.session_timeout)
        
        return {
            'user_id': int(session_data.get(b'user_id', 0)),
            'created_at': session_data.get(b'created_at', b'').decode('utf-8'),
            'last_activity': session_data.get(b'last_activity', b'').decode('utf-8')
        }
    
    def invalidate_session(self, user_id):
        """Invalidate all sessions for user"""
        user_sessions_key = f"user_sessions:{user_id}"
        session_ids = self.redis.smembers(user_sessions_key)
        
        for session_id in session_ids:
            session_key = f"session:{session_id.decode('utf-8')}"
            self.redis.delete(session_key)
        
        self.redis.delete(user_sessions_key)
    
    def validate_session(self, session_id):
        """Validate session and return user_id"""
        session = self.get_session(session_id)
        if not session:
            return None
        
        # Check if session expired
        last_activity = datetime.fromisoformat(session['last_activity'])
        if (datetime.utcnow() - last_activity).total_seconds() > self.session_timeout:
            self.redis.delete(f"session:{session_id}")
            return None
        
        return session['user_id']
    
    def generate_reset_token(self, user_id):
        """Generate password reset token"""
        token = secrets.token_urlsafe(32)
        reset_key = f"password_reset:{token}"
        
        self.redis.setex(
            reset_key,
            3600,  # 1 hour expiry
            user_id
        )
        
        return token
    
    def validate_reset_token(self, token):
        """Validate password reset token"""
        reset_key = f"password_reset:{token}"
        user_id = self.redis.get(reset_key)
        
        if user_id:
            self.redis.delete(reset_key)
            return int(user_id)
        
        return None
    
    def generate_verification_token(self, user_id):
        """Generate email verification token"""
        token = secrets.token_urlsafe(32)
        verify_key = f"email_verify:{token}"
        
        self.redis.setex(
            verify_key,
            86400,  # 24 hour expiry
            user_id
        )
        
        return token
    
    def verify_email_token(self, token):
        """Verify email verification token"""
        verify_key = f"email_verify:{token}"
        user_id = self.redis.get(verify_key)
        
        if user_id:
            self.redis.delete(verify_key)
            return int(user_id)
        
        return None
    
    def track_failed_login(self, identifier):
        """Track failed login attempts"""
        key = f"failed_login:{identifier}"
        attempts = self.redis.incr(key)
        
        if attempts == 1:
            self.redis.expire(key, 900)  # 15 minutes
        
        return attempts
    
    def is_locked_out(self, identifier):
        """Check if account is locked due to failed attempts"""
        key = f"failed_login:{identifier}"
        attempts = self.redis.get(key)
        
        if attempts and int(attempts) >= 5:
            return True
        
        return False
    
    def clear_failed_attempts(self, identifier):
        """Clear failed login attempts"""
        key = f"failed_login:{identifier}"
        self.redis.delete(key)


def generate_token(user_id, anonymous_id):
    """Generate JWT token for user"""
    payload = {
        'user_id': user_id,
        'anonymous_id': anonymous_id,
        'iat': datetime.utcnow(),
        'exp': datetime.utcnow() + timedelta(hours=24)
    }
    
    token = jwt.encode(
        payload,
        os.environ.get('JWT_SECRET', 'default-secret-key'),
        algorithm='HS256'
    )
    
    return token


def verify_token(token):
    """Verify JWT token"""
    try:
        payload = jwt.decode(
            token,
            os.environ.get('JWT_SECRET', 'default-secret-key'),
            algorithms=['HS256']
        )
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def require_auth(optional=False):
    """Decorator for routes requiring authentication"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Check for Authorization header
            auth_header = request.headers.get('Authorization')
            
            if not auth_header:
                # Check for session cookie
                session_token = request.cookies.get('session_token')
                if session_token:
                    from app import auth_manager
                    user_id = auth_manager.validate_session(session_token)
                    
                    if user_id:
                        from models import User
                        user = User.query.get(user_id)
                        if user and user.is_active:
                            request.current_user = user
                            g.user_id = user.id
                            return f(*args, **kwargs)
                
                if optional:
                    request.current_user = None
                    g.user_id = None
                    return f(*args, **kwargs)
                
                return jsonify({'error': 'Authentication required'}), 401
            
            # Extract token
            try:
                token = auth_header.split(' ')[1]
            except IndexError:
                if optional:
                    request.current_user = None
                    g.user_id = None
                    return f(*args, **kwargs)
                return jsonify({'error': 'Invalid authorization header'}), 401
            
            # Verify token
            payload = verify_token(token)
            if not payload:
                if optional:
                    request.current_user = None
                    g.user_id = None
                    return f(*args, **kwargs)
                return jsonify({'error': 'Invalid or expired token'}), 401
            
            # Get user
            from models import User
            user = User.query.get(payload['user_id'])
            
            if not user or not user.is_active:
                if optional:
                    request.current_user = None
                    g.user_id = None
                    return f(*args, **kwargs)
                return jsonify({'error': 'User not found or inactive'}), 401
            
            # Check for active penalties
            active_penalty = user.penalties.filter_by(is_active=True).first()
            if active_penalty:
                return jsonify({
                    'error': 'Account suspended',
                    'reason': active_penalty.reason,
                    'until': active_penalty.end_date.isoformat() if active_penalty.end_date else 'Permanent'
                }), 403
            
            # Set current user
            request.current_user = user
            g.user_id = user.id
            
            return f(*args, **kwargs)
            
        return decorated_function
    return decorator


def require_admin():
    """Decorator for admin-only routes"""
    def decorator(f):
        @wraps(f)
        @require_auth()
        def decorated_function(*args, **kwargs):
            user = request.current_user
            
            # Check if user is admin (you might want to add an is_admin field to User model)
            if not getattr(user, 'is_admin', False):
                return jsonify({'error': 'Admin access required'}), 403
            
            return f(*args, **kwargs)
            
        return decorated_function
    return decorator


class TwoFactorAuth:
    """Two-factor authentication manager"""
    
    def __init__(self, redis_client):
        self.redis = redis_client
        
    def generate_otp(self, user_id):
        """Generate OTP for user"""
        import random
        
        otp = str(random.randint(100000, 999999))
        otp_key = f"otp:{user_id}"
        
        # Store OTP with 5 minute expiry
        self.redis.setex(otp_key, 300, otp)
        
        return otp
    
    def verify_otp(self, user_id, otp):
        """Verify OTP"""
        otp_key = f"otp:{user_id}"
        stored_otp = self.redis.get(otp_key)
        
        if stored_otp and stored_otp.decode('utf-8') == otp:
            self.redis.delete(otp_key)
            return True
        
        return False
    
    def generate_backup_codes(self, user_id, count=10):
        """Generate backup codes for 2FA"""
        codes = []
        
        for _ in range(count):
            code = secrets.token_hex(4).upper()
            codes.append(code)
            
            # Hash and store backup code
            code_hash = hashlib.sha256(code.encode()).hexdigest()
            backup_key = f"backup_code:{user_id}:{code_hash}"
            self.redis.setex(backup_key, 31536000, '1')  # 1 year expiry
        
        return codes
    
    def verify_backup_code(self, user_id, code):
        """Verify and consume backup code"""
        code_hash = hashlib.sha256(code.encode()).hexdigest()
        backup_key = f"backup_code:{user_id}:{code_hash}"
        
        if self.redis.get(backup_key):
            self.redis.delete(backup_key)
            return True
        
        return False


class PermissionManager:
    """Manage user permissions and roles"""
    
    PERMISSIONS = {
        'user': [
            'read_own_profile',
            'write_own_profile',
            'read_posts',
            'write_posts',
            'follow_users',
            'send_messages'
        ],
        'moderator': [
            'review_reports',
            'warn_users',
            'delete_posts',
            'view_user_details'
        ],
        'admin': [
            'manage_users',
            'manage_penalties',
            'view_analytics',
            'system_settings'
        ]
    }
    
    @classmethod
    def check_permission(cls, user, permission):
        """Check if user has specific permission"""
        user_role = getattr(user, 'role', 'user')
        
        if user_role == 'admin':
            return True  # Admins have all permissions
        
        if user_role == 'moderator':
            allowed = cls.PERMISSIONS['moderator'] + cls.PERMISSIONS['user']
            return permission in allowed
        
        return permission in cls.PERMISSIONS.get(user_role, [])
    
    @classmethod
    def require_permission(cls, permission):
        """Decorator to require specific permission"""
        def decorator(f):
            @wraps(f)
            @require_auth()
            def decorated_function(*args, **kwargs):
                user = request.current_user
                
                if not cls.check_permission(user, permission):
                    return jsonify({'error': f'Permission denied: {permission}'}), 403
                
                return f(*args, **kwargs)
                
            return decorated_function
        return decorator


class AuditLogger:
    """Log authentication and security events"""
    
    def __init__(self, db, logger):
        self.db = db
        self.logger = logger
    
    def log_login(self, user_id, ip_address, success=True):
        """Log login attempt"""
        self.logger.info('login_attempt', extra={
            'user_id': user_id,
            'ip_address': ip_address,
            'success': success,
            'timestamp': datetime.utcnow().isoformat()
        })
    
    def log_logout(self, user_id):
        """Log logout"""
        self.logger.info('logout', extra={
            'user_id': user_id,
            'timestamp': datetime.utcnow().isoformat()
        })
    
    def log_password_change(self, user_id):
        """Log password change"""
        self.logger.info('password_changed', extra={
            'user_id': user_id,
            'timestamp': datetime.utcnow().isoformat()
        })
    
    def log_permission_denied(self, user_id, resource, action):
        """Log permission denied event"""
        self.logger.warning('permission_denied', extra={
            'user_id': user_id,
            'resource': resource,
            'action': action,
            'timestamp': datetime.utcnow().isoformat()
        })
    
    def log_suspicious_activity(self, user_id, activity_type, details):
        """Log suspicious activity"""
        self.logger.warning('suspicious_activity', extra={
            'user_id': user_id,
            'activity_type': activity_type,
            'details': details,
            'timestamp': datetime.utcnow().isoformat()
        })
