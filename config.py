"""
Configuration for Thera Social
FIX 4: Mandatory security environment variables
"""
import os
import sys
import logging
from datetime import timedelta


class ConfigurationError(Exception):
    """Raised when required configuration is missing"""
    pass


def require_env(name, production_only=False):
    """
    Get a required environment variable.
    Raises ConfigurationError if missing in production.
    In development, generates a warning and returns a temporary value.
    """
    value = os.environ.get(name)
    is_production = os.environ.get('PRODUCTION', '').lower() in ('true', '1', 'yes')
    
    if value:
        return value
    
    if is_production or not production_only:
        if is_production:
            # In production, missing required vars are fatal
            raise ConfigurationError(
                f"FATAL: Required environment variable '{name}' is not set. "
                f"Please set this in your deployment configuration."
            )
        else:
            # In development, warn but allow temporary value
            logging.warning(
                f"⚠️  Environment variable '{name}' not set. "
                f"Using temporary value for development. "
                f"DO NOT use this in production!"
            )
            # Generate a temporary but consistent dev value
            import hashlib
            return hashlib.sha256(f"dev-{name}-temporary".encode()).hexdigest()[:32]
    
    return None


class Config:
    """Application configuration with security-first defaults"""
    
    # Determine environment
    IS_PRODUCTION = os.environ.get('PRODUCTION', '').lower() in ('true', '1', 'yes')
    
    # FIX 4: Required security secrets - MUST be set in production
    # These will raise ConfigurationError if missing in production
    @staticmethod
    def get_secret_key():
        return require_env('SECRET_KEY', production_only=False)
    
    @staticmethod  
    def get_jwt_secret():
        return require_env('JWT_SECRET', production_only=False)
    
    @staticmethod
    def get_encryption_key():
        return require_env('ENCRYPTION_KEY', production_only=False)
    
    # Basic Flask config - lazy loaded to catch missing vars early
    @property
    def SECRET_KEY(self):
        return self.get_secret_key()
    
    # Database
    @staticmethod
    def get_database_url():
        url = os.environ.get('DATABASE_URL', '')
        if not url:
            if Config.IS_PRODUCTION:
                raise ConfigurationError(
                    "FATAL: DATABASE_URL environment variable is not set."
                )
            return 'postgresql://localhost/thera_social'
        # Fix Heroku/Render postgres:// to postgresql://
        return url.replace('postgres://', 'postgresql://')
    
    SQLALCHEMY_DATABASE_URI = property(lambda self: self.get_database_url())
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,
        'pool_recycle': 3600,
        'pool_pre_ping': True,
    }
    
    # Redis
    REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379')
    
    # Security - lazy properties to catch errors early
    @property
    def ENCRYPTION_KEY(self):
        return self.get_encryption_key()
    
    @property
    def JWT_SECRET(self):
        return self.get_jwt_secret()
    
    JWT_EXPIRATION = timedelta(hours=24)
    
    # Session security
    SESSION_COOKIE_SECURE = True  # Always True - use HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'  # Changed from Strict for OAuth compatibility
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    
    # CSRF protection
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600  # 1 hour
    
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
    MAIL_USE_TLS = True
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@therasocial.com')


def validate_config():
    """
    Validate all required configuration at startup.
    Call this early in application initialization.
    """
    errors = []
    warnings = []
    
    is_production = os.environ.get('PRODUCTION', '').lower() in ('true', '1', 'yes')
    
    # Check required secrets
    required_secrets = ['SECRET_KEY', 'JWT_SECRET', 'ENCRYPTION_KEY']
    for secret in required_secrets:
        value = os.environ.get(secret)
        if not value:
            if is_production:
                errors.append(f"Missing required secret: {secret}")
            else:
                warnings.append(f"Missing secret '{secret}' - using temporary dev value")
    
    # Check database
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        if is_production:
            errors.append("Missing required: DATABASE_URL")
        else:
            warnings.append("DATABASE_URL not set - using localhost")
    
    # Check Redis
    redis_url = os.environ.get('REDIS_URL')
    if not redis_url:
        warnings.append("REDIS_URL not set - using localhost:6379")
    
    # Print warnings
    for warning in warnings:
        logging.warning(f"⚠️  Config: {warning}")
    
    # Fail on errors in production
    if errors:
        for error in errors:
            logging.error(f"❌ Config Error: {error}")
        raise ConfigurationError(
            f"Configuration validation failed with {len(errors)} error(s). "
            f"Please set the required environment variables."
        )
    
    if is_production:
        logging.info("✅ Configuration validated successfully for production")
    else:
        logging.info("✅ Configuration validated for development mode")


def configure_logging():
    """Configure structured logging"""
    log_level = logging.INFO if os.environ.get('PRODUCTION') else logging.DEBUG
    
    # Create logger
    logger = logging.getLogger('thera_social')
    logger.setLevel(log_level)
    
    # Console handler with formatting
    handler = logging.StreamHandler()
    handler.setLevel(log_level)
    
    # Use JSON-like format in production for log aggregation
    if os.environ.get('PRODUCTION'):
        formatter = logging.Formatter(
            '{"time":"%(asctime)s", "level":"%(levelname)s", "name":"%(name)s", "message":"%(message)s"}'
        )
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger


# Validate configuration on import in production
if os.environ.get('PRODUCTION', '').lower() in ('true', '1', 'yes'):
    try:
        validate_config()
    except ConfigurationError as e:
        print(f"\n{'='*60}")
        print("CONFIGURATION ERROR - APPLICATION CANNOT START")
        print('='*60)
        print(str(e))
        print('='*60)
        print("\nRequired environment variables:")
        print("  - SECRET_KEY: Flask session secret")
        print("  - JWT_SECRET: JWT token signing key")
        print("  - ENCRYPTION_KEY: Data encryption key")
        print("  - DATABASE_URL: PostgreSQL connection string")
        print("\nOptional but recommended:")
        print("  - REDIS_URL: Redis connection string")
        print('='*60 + "\n")
        sys.exit(1)
