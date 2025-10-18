"""
Configuration for Thera Social
"""
import os
import logging
from datetime import timedelta

class Config:
    # Basic Flask config
    SECRET_KEY = os.environ.get('SECRET_KEY') or os.urandom(32)
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'postgresql://localhost/thera_social').replace('postgres://', 'postgresql://')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,
        'pool_recycle': 3600,
        'pool_pre_ping': True,
    }
    
    # Redis
    REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379')
    
    # Security
    ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY', os.urandom(32))
    JWT_SECRET = os.environ.get('JWT_SECRET', os.urandom(32))
    JWT_EXPIRATION = timedelta(hours=24)
    
    # Session
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Strict'
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    
    # Rate limiting
    RATELIMIT_STORAGE_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379')
    
    # Privacy settings
    ANONYMITY_VIOLATION_FINE = 10000  # Default fine amount
    MAX_REPORT_AGE_DAYS = 90
    
    # Content moderation
    CONCERNING_KEYWORDS = ['suicide', 'self-harm', 'depression', 'anxiety', 'panic']
    
    # Email (optional)
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    
def configure_logging():
    """Configure structured logging"""
    logger = logging.getLogger('thera_social')
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO if os.environ.get('PRODUCTION') else logging.DEBUG)
    return logger
