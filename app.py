#!/usr/bin/env python
"""
Complete app.py for Social Social Platform
With Flask-Migrate and SQLAlchemy 2.0 style queries
Auto-migrates on startup for seamless deployment
"""

import os
import sys
import traceback
import json
import uuid
import redis
import logging
from datetime import datetime, timedelta
from functools import wraps
import time
from collections import defaultdict

# Cache busting timestamp - updates on every app restart
CACHE_BUST_VERSION = str(int(time.time()))

from flask import (
    Flask, request, jsonify, session,
    render_template, send_from_directory, redirect, url_for
)
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from flask_session import Session
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy import select, and_, or_, desc, func, inspect, text
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content

import mimetypes

# Add MIME type for CSS files
mimetypes.add_type('text/css', '.css')
mimetypes.add_type('text/javascript', '.js')

# Import security functions
from security import (
    sanitize_input, validate_email, validate_username,
    validate_password_strength, encrypt_field, decrypt_field,
    generate_token, rate_limit, content_moderator
)

# Initialize Flask app
app = Flask(__name__, static_folder='static', template_folder='templates')

# =====================
# CONFIGURATION
# =====================

# Environment detection - using modern Flask approach
is_production = os.environ.get('FLASK_DEBUG', 'False').lower() == 'false'
app.config['DEBUG'] = not is_production

# Secret key configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
if is_production and app.config['SECRET_KEY'] == 'dev-secret-key-change-in-production':
    print("WARNING: Using default SECRET_KEY in production!")

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///social.db')

# Fix for Render PostgreSQL URL
if app.config['SQLALCHEMY_DATABASE_URI'].startswith('postgres://'):
    app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace(
        'postgres://', 'postgresql://', 1
    )

# SQLAlchemy configuration
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_size': 20,  # Increased from 10
    'max_overflow': 30,  # Allow temporary overflow connections
    'pool_recycle': 3600,
    'pool_pre_ping': True,
    'pool_timeout': 30,  # Wait up to 30 seconds for connection
}

# Session configuration
app.config['SESSION_TYPE'] = 'redis' if os.environ.get('REDIS_URL') else 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)
app.config['SESSION_COOKIE_SECURE'] = is_production
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_NAME'] = 'thera_session'
app.config['SESSION_KEY_PREFIX'] = 'thera_social:'
app.config['SESSION_USE_SIGNER'] = True

# Redis configuration for sessions
REDIS_URL = os.environ.get('REDIS_URL')
if REDIS_URL:
    app.config['SESSION_REDIS'] = redis.from_url(REDIS_URL)

# Initialize extensions
db = SQLAlchemy(app)
migrate = Migrate(app, db, render_as_batch=True)  # render_as_batch for SQLite

CORS(app, supports_credentials=True)
Session(app)

# =====================
# RATE LIMITING
# =====================

# Simple in-memory rate limiter (use Redis in production for distributed systems)
rate_limit_store = defaultdict(list)


def check_rate_limit(user_id, max_requests=100, window=60):
    """
    Check if user has exceeded rate limit
    max_requests: maximum requests allowed
    window: time window in seconds
    """
    now = time.time()
    user_requests = rate_limit_store[user_id]

    # Remove old requests outside window
    user_requests[:] = [req_time for req_time in user_requests if now - req_time < window]

    if len(user_requests) >= max_requests:
        return False, len(user_requests)

    user_requests.append(now)
    return True, len(user_requests)


def rate_limit_endpoint(max_requests=100, window=60):
    """
    Decorator for rate limiting endpoints
    Usage: @rate_limit_endpoint(max_requests=60, window=60)
    """

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_id = session.get('user_id')
            if user_id:
                allowed, count = check_rate_limit(user_id, max_requests, window)
                if not allowed:
                    return jsonify({'error': 'Rate limit exceeded', 'retry_after': window}), 429
            return f(*args, **kwargs)

        return decorated_function

    return decorator


# Setup logging
logging.basicConfig(
    level=logging.INFO if is_production else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('thera_social')

# Email configuration for password reset
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask_mail import Mail, Message

# Flask-Mail configuration for SendGrid
app.config['MAIL_SERVER'] = os.environ.get('SMTP_SERVER', 'smtp.sendgrid.net')
app.config['MAIL_PORT'] = int(os.environ.get('SMTP_PORT', 587))
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = os.environ.get('SMTP_USERNAME', 'apikey')
app.config['MAIL_PASSWORD'] = os.environ.get('SMTP_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('FROM_EMAIL', 'evanmax@outlook.com')

# Initialize Flask-Mail
mail = Mail(app)


def get_email_translations(language='en'):
    """Get email translations based on language"""
    translations = {
        'en': {
            'subject': 'TheraSocial - Password Reset Request',
            'hello': 'Hello',
            'request_text': 'You requested to reset your password for TheraSocial.',
            'click_button': 'Click the button below to reset your password:',
            'button_text': 'Reset Password',
            'copy_link': 'Or copy and paste this link into your browser:',
            'expire_text': 'This link will expire in 1 hour.',
            'ignore_text': 'If you did not request this reset, please ignore this email.',
            'regards': 'Best regards',
            'team': 'TheraSocial Team'
        },
        'he': {
            'subject': 'TheraSocial - בקשת איפוס סיסמה',
            'hello': 'שלום',
            'request_text': 'ביקשת לאפס את הסיסמה שלך עבור TheraSocial.',
            'click_button': 'לחץ על הכפתור למטה כדי לאפס את הסיסמה:',
            'button_text': 'איפוס סיסמה',
            'copy_link': 'או העתק והדבק את הקישור הזה בדפדפן שלך:',
            'expire_text': 'קישור זה יפוג תוך שעה.',
            'ignore_text': 'אם לא ביקשת איפוס זה, אנא התעלם מאימייל זה.',
            'regards': 'בברכה',
            'team': 'צוות TheraSocial'
        },
        'ar': {
            'subject': 'TheraSocial - طلب إعادة تعيين كلمة المرور',
            'hello': 'مرحبا',
            'request_text': 'لقد طلبت إعادة تعيين كلمة المرور الخاصة بك لـ TheraSocial.',
            'click_button': 'انقر على الزر أدناه لإعادة تعيين كلمة المرور:',
            'button_text': 'إعادة تعيين كلمة المرور',
            'copy_link': 'أو انسخ والصق هذا الرابط في المتصفح:',
            'expire_text': 'ستنتهي صلاحية هذا الرابط خلال ساعة واحدة.',
            'ignore_text': 'إذا لم تطلب إعادة التعيين، يرجى تجاهل هذا البريد.',
            'regards': 'مع أطيب التحيات',
            'team': 'فريق TheraSocial'
        },
        'ru': {
            'subject': 'TheraSocial - Запрос на сброс пароля',
            'hello': 'Здравствуйте',
            'request_text': 'Вы запросили сброс пароля для TheraSocial.',
            'click_button': 'Нажмите кнопку ниже, чтобы сбросить пароль:',
            'button_text': 'Сбросить пароль',
            'copy_link': 'Или скопируйте эту ссылку в ваш браузер:',
            'expire_text': 'Эта ссылка истечет через 1 час.',
            'ignore_text': 'Если вы не запрашивали сброс, проигнорируйте это письмо.',
            'regards': 'С наилучшими пожеланиями',
            'team': 'Команда TheraSocial'
        }
    }
    return translations.get(language, translations['en'])


def send_password_reset_email(user_email, reset_token, user_language='en'):
    """Send password reset email in user's preferred language using Flask-Mail"""
    try:
        t = get_email_translations(user_language)
        reset_link = f"{os.environ.get('APP_URL', 'http://localhost:5000')}?reset_token={reset_token}"

        is_rtl = user_language in ['he', 'ar']
        text_dir = 'rtl' if is_rtl else 'ltr'
        text_align = 'right' if is_rtl else 'left'

        html_content = f"""
        <html>
        <body style="font-family: Arial; direction: {text_dir}; text-align: {text_align};">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #667eea;">{t['subject'].replace('TheraSocial - ', '')}</h2>
                <p>{t['hello']},</p>
                <p>{t['request_text']}</p>
                <p>{t['click_button']}</p>
                <p style="text-align: center; margin: 30px 0;">
                    <a href="{reset_link}" style="background: #667eea; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block;">
                        {t['button_text']}
                    </a>
                </p>
                <p>{t['copy_link']}</p>
                <p style="word-break: break-all; color: #667eea;">{reset_link}</p>
                <p style="color: #666;">{t['expire_text']}</p>
                <p style="color: #666;">{t['ignore_text']}</p>
                <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
                <p style="color: #999;">
                    {t['regards']},<br>{t['team']}
                </p>
            </div>
        </body>
        </html>
        """

        text_content = f"""
        {t['hello']},
        {t['request_text']}
        {t['click_button']}
        {reset_link}
        {t['expire_text']}
        {t['ignore_text']}
        {t['regards']},
        {t['team']}
        """

        try:
            message = Mail(
                from_email=Email(app.config['MAIL_DEFAULT_SENDER']),
                to_emails=To(user_email),
                subject=t['subject'],
                plain_text_content=Content("text/plain", text_content),
                html_content=Content("text/html", html_content)
            )

            sg = SendGridAPIClient(app.config['MAIL_PASSWORD'])
            response = sg.send(message)
            logging.info(f'Password reset email sent to {user_email}')
        except Exception as e:
            logging.error(f'Failed to send password reset email: {str(e)}')
            raise

        mail.send(msg)
        logger.info(f"Password reset email sent to {user_email} in {user_language}")
        return True

    except Exception as e:
        logger.error(f"Failed to send password reset email: {e}")
        return False


def send_magic_link_email(user_email, magic_token, user_language='en'):
    """Send magic link login email using Flask-Mail"""
    try:
        translations = {
            'en': {
                'subject': 'TheraSocial - Magic Link Sign In',
                'hello': 'Hello',
                'request_text': 'Click the link below to sign in to TheraSocial:',
                'button_text': 'Sign In',
                'expire_text': 'This link will expire in 5 years or until a new one is generated',
                'ignore_text': 'If you did not request this, please ignore this email.'
            },
            'he': {
                'subject': 'TheraSocial - התחברות בקישור קסם',
                'hello': 'שלום',
                'request_text': 'לחץ על הקישור למטה כדי להתחבר:',
                'button_text': 'התחבר',
                'expire_text': 'קישור זה יפוג תוקפו בעוד 5 שנים או עד שייווצר קישור חדש',
                'ignore_text': 'אם לא ביקשת זאת, התעלם מאימייל זה.'
            },
            'ar': {
                'subject': 'TheraSocial - تسجيل الدخول بالرابط السحري',
                'hello': 'مرحبا',
                'request_text': 'انقر على الرابط أدناه لتسجيل الدخول:',
                'button_text': 'تسجيل الدخول',
                'expire_text': 'سينتهي هذا الرابط خلال 5 سنوات أو حتى يتم إنشاء رابط جديد',
                'ignore_text': 'إذا لم تطلب هذا، تجاهل هذا البريد.'
            },
            'ru': {
                'subject': 'TheraSocial - Вход по волшебной ссылке',
                'hello': 'Здравствуйте',
                'request_text': 'Нажмите на ссылку ниже для входа:',
                'button_text': 'Войти',
                'expire_text': 'Эта ссылка истечет через 5 лет или пока не будет создана новая.',
                'ignore_text': 'Если вы не запрашивали это, проигнорируйте.'
            }
        }

        t = translations.get(user_language, translations['en'])
        magic_link = f"{os.environ.get('APP_URL', 'http://localhost:5000')}?magic_token={magic_token}"

        html_content = f"""<html><body>
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2>{t['subject']}</h2>
                <p>{t['hello']},</p>
                <p>{t['request_text']}</p>
                <a href="{magic_link}" style="background: #667eea; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; display: inline-block;">
                    {t['button_text']}
                </a>
                <p>{t['expire_text']}</p>
                <p>{t['ignore_text']}</p>
            </div>
        </body></html>"""

        try:
            message = Mail(
                from_email=Email(app.config['MAIL_DEFAULT_SENDER']),
                to_emails=To(user_email),
                subject=t['subject'],
                html_content=Content("text/html", html_content)
            )

            sg = SendGridAPIClient(app.config['MAIL_PASSWORD'])
            response = sg.send(message)
            logging.info(f'Magic link email sent to {user_email}')
        except Exception as e:
            logging.error(f'Failed to send magic link email: {str(e)}')
            raise

        mail.send(msg)
        logger.info(f"Magic link email sent to {user_email} in {user_language}")
        return True

    except Exception as e:
        logger.error(f"Failed to send magic link email: {e}")
        return False


def ensure_saved_parameters_schema():
    """Ensure saved_parameters table has all required columns - runs on startup"""
    # Guard: Skip if already run in this process
    if hasattr(ensure_saved_parameters_schema, '_completed'):
        return

    try:
        with app.app_context():
            # Check if table exists
            inspector = inspect(db.engine)
            if 'saved_parameters' not in inspector.get_table_names():
                logger.info("saved_parameters table doesn't exist yet, will be created by migrations")
                return

            # Get existing columns
            existing_columns = {col['name'] for col in inspector.get_columns('saved_parameters')}
            logger.debug(f"Existing columns in saved_parameters: {existing_columns}")  # Changed to debug

            # Check if we're using PostgreSQL or SQLite
            is_postgres = 'postgresql' in str(db.engine.url)

            # Define required columns with their types
            required_columns = {
                'sleep_quality': 'INTEGER',
                'physical_activity': 'INTEGER',
                'anxiety': 'INTEGER',
                'updated_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'
            }

            # Privacy columns (will be added if missing, with private default)
            privacy_columns = {
                'mood_privacy': 'VARCHAR(20) DEFAULT \'private\'',
                'energy_privacy': 'VARCHAR(20) DEFAULT \'private\'',
                'sleep_quality_privacy': 'VARCHAR(20) DEFAULT \'private\'',
                'physical_activity_privacy': 'VARCHAR(20) DEFAULT \'private\'',
                'anxiety_privacy': 'VARCHAR(20) DEFAULT \'private\''
            }

            # Combine all required columns
            all_required = {**required_columns, **privacy_columns}

            # Add missing columns
            missing_columns = set(all_required.keys()) - existing_columns

            if missing_columns:
                logger.info(f"Adding missing columns to saved_parameters: {missing_columns}")

                with db.engine.connect() as connection:
                    for column_name in missing_columns:
                        column_type = all_required[column_name]

                        if is_postgres:
                            # PostgreSQL syntax with IF NOT EXISTS
                            alter_query = text(
                                f"ALTER TABLE saved_parameters ADD COLUMN IF NOT EXISTS {column_name} {column_type}")
                        else:
                            # SQLite syntax (no IF NOT EXISTS)
                            alter_query = text(
                                f"ALTER TABLE saved_parameters ADD COLUMN {column_name} {column_type}")

                        try:
                            connection.execute(alter_query)
                            connection.commit()
                            logger.info(f"Added column: {column_name}")
                        except Exception as e:
                            # Column might already exist in SQLite (which doesn't support IF NOT EXISTS)
                            logger.debug(f"Column {column_name} might already exist: {e}")

                logger.info("Successfully added all missing columns to saved_parameters")
            else:
                logger.debug("All required columns exist in saved_parameters")  # Changed to debug

        # Mark as completed for this process
        ensure_saved_parameters_schema._completed = True

    except Exception as e:
        logger.error(f"Error ensuring saved_parameters schema: {str(e)}")
        # Don't raise - allow app to start even if this fails


# Initialize Redis client (optional, for caching)
try:
    redis_client = redis.from_url(REDIS_URL) if REDIS_URL else None
    if redis_client:
        redis_client.ping()
        logger.info("Redis connected successfully")
except Exception as e:
    redis_client = None
    logger.warning(f"Redis not available: {e}")


def parse_date_as_local(date_string):
    """Parse date string as local date without timezone conversion"""
    from datetime import datetime
    try:
        # This ensures the date is treated as-is without timezone shifts
        return datetime.strptime(date_string, '%Y-%m-%d').date()
    except ValueError:
        # Fallback for other formats
        return datetime.fromisoformat(date_string.split('T')[0]).date()


def get_db():
    """Get a direct database connection for raw SQL queries"""
    import psycopg2
    from psycopg2.extras import RealDictCursor

    # Get the database URI from SQLAlchemy config
    db_uri = app.config['SQLALCHEMY_DATABASE_URI']

    # For PostgreSQL (Render uses PostgreSQL)
    if db_uri.startswith('postgresql://') or db_uri.startswith('postgres://'):
        # Fix postgres:// to postgresql:// if needed
        if db_uri.startswith('postgres://'):
            db_uri = db_uri.replace('postgres://', 'postgresql://', 1)

        try:
            conn = psycopg2.connect(db_uri, cursor_factory=RealDictCursor)
            return conn
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            raise

    # For SQLite (local development)
    elif db_uri.startswith('sqlite:///'):
        import sqlite3
        db_path = db_uri.replace('sqlite:///', '')
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn

    else:
        raise ValueError(f"Unsupported database type: {db_uri}")

def auto_migrate_database():
    """Automatically update database schema on startup"""
    logger.info("Starting auto_migrate_database...")
    with app.app_context():
        try:
            # Create all tables first
            db.create_all()

            # Now add missing columns
            from sqlalchemy import inspect, text
            inspector = inspect(db.engine)

            with db.engine.connect() as conn:
                # Check if we're using PostgreSQL or SQLite
                is_postgres = 'postgresql' in str(db.engine.url)

                # Update users table
                if 'users' in inspector.get_table_names():
                    columns = [col['name'] for col in inspector.get_columns('users')]

                    if 'has_completed_onboarding' not in columns:
                        if is_postgres:
                            conn.execute(
                                text("ALTER TABLE users ADD COLUMN has_completed_onboarding BOOLEAN DEFAULT FALSE"))
                        else:
                            conn.execute(
                                text("ALTER TABLE users ADD COLUMN has_completed_onboarding INTEGER DEFAULT 0"))
                        conn.commit()

                    if 'onboarding_dismissed' not in columns:
                        if is_postgres:
                            conn.execute(
                                text("ALTER TABLE users ADD COLUMN onboarding_dismissed BOOLEAN DEFAULT FALSE"))
                        else:
                            conn.execute(text("ALTER TABLE users ADD COLUMN onboarding_dismissed INTEGER DEFAULT 0"))
                        conn.commit()

                    if 'shareable_link_token' not in columns:
                        conn.execute(text("ALTER TABLE users ADD COLUMN shareable_link_token VARCHAR(100)"))
                        conn.commit()

                # Update parameters/saved_parameters table
                params_table = 'saved_parameters' if 'saved_parameters' in inspector.get_table_names() else 'parameters'
                if params_table in inspector.get_table_names():
                    columns = [col['name'] for col in inspector.get_columns(params_table)]

                    privacy_columns = ['mood_privacy', 'energy_privacy', 'sleep_quality_privacy',
                                       'physical_activity_privacy', 'anxiety_privacy']

                    for col in privacy_columns:
                        if col not in columns:
                            conn.execute(
                                text(f"ALTER TABLE {params_table} ADD COLUMN {col} VARCHAR(20) DEFAULT 'public'"))
                            conn.commit()

                # Create password_reset_tokens table if it doesn't exist
                if 'password_reset_tokens' not in inspector.get_table_names():
                    logger.info("Creating password_reset_tokens table...")
                    if is_postgres:
                        conn.execute(text("""
                            CREATE TABLE password_reset_tokens (
                                id SERIAL PRIMARY KEY,
                                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                                token VARCHAR(100) UNIQUE NOT NULL,
                                expires_at TIMESTAMP NOT NULL,
                                used BOOLEAN DEFAULT FALSE,
                                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                            )
                        """))
                    else:
                        conn.execute(text("""
                            CREATE TABLE password_reset_tokens (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                user_id INTEGER NOT NULL,
                                token VARCHAR(100) UNIQUE NOT NULL,
                                expires_at TIMESTAMP NOT NULL,
                                used INTEGER DEFAULT 0,
                                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                            )
                        """))
                    conn.commit()
                    logger.info("✓ Created password_reset_tokens table")

                # Create magic_login_tokens table
                if 'magic_login_tokens' not in inspector.get_table_names():
                    logger.info("Creating magic_login_tokens table...")
                    if is_postgres:
                        conn.execute(text("""
                            CREATE TABLE magic_login_tokens (
                                id SERIAL PRIMARY KEY,
                                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                                token VARCHAR(100) UNIQUE NOT NULL,
                                expires_at TIMESTAMP NOT NULL,
                                used BOOLEAN DEFAULT FALSE,
                                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                            )
                        """))
                    else:
                        conn.execute(text("""
                            CREATE TABLE magic_login_tokens (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                user_id INTEGER NOT NULL,
                                token VARCHAR(100) UNIQUE NOT NULL,
                                expires_at TIMESTAMP NOT NULL,
                                used INTEGER DEFAULT 0,
                                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                            )
                        """))
                    conn.commit()
                    logger.info("✓ Created magic_login_tokens table")

                # Create user_consents table
                if 'user_consents' not in inspector.get_table_names():
                    logger.info("Creating user_consents table...")
                    if is_postgres:
                        conn.execute(text("""
                            CREATE TABLE user_consents (
                                id SERIAL PRIMARY KEY,
                                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                                email_updates BOOLEAN DEFAULT FALSE,
                                privacy_accepted BOOLEAN DEFAULT FALSE,
                                research_data BOOLEAN DEFAULT FALSE,
                                team_declaration BOOLEAN DEFAULT FALSE,
                                responsible_use BOOLEAN DEFAULT FALSE,
                                waiver_claims BOOLEAN DEFAULT FALSE,
                                consent_language VARCHAR(5) DEFAULT 'en',
                                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                            )
                        """))
                    else:
                        conn.execute(text("""
                            CREATE TABLE user_consents (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                user_id INTEGER NOT NULL,
                                email_updates INTEGER DEFAULT 0,
                                privacy_accepted INTEGER DEFAULT 0,
                                research_data INTEGER DEFAULT 0,
                                team_declaration INTEGER DEFAULT 0,
                                responsible_use INTEGER DEFAULT 0,
                                waiver_claims INTEGER DEFAULT 0,
                                consent_language VARCHAR(5) DEFAULT 'en',
                                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
                            )
                        """))
                    conn.commit()
                    logger.info("✓ Created user_consents table")

                # Add follow_note column to follows table
                if 'follows' in inspector.get_table_names():
                    columns = [col['name'] for col in inspector.get_columns('follows')]
                    if 'follow_note' not in columns:
                        logger.info("Adding follow_note column to follows table...")
                        conn.execute(text("ALTER TABLE follows ADD COLUMN follow_note VARCHAR(300)"))
                        conn.commit()
                        logger.info("✓ Added follow_note column to follows table")

                # Create or update parameter_triggers table
                if 'parameter_triggers' not in inspector.get_table_names():
                    logger.info("Creating parameter_triggers table...")
                    if is_postgres:
                        conn.execute(text("""
                            CREATE TABLE parameter_triggers (
                                id SERIAL PRIMARY KEY,
                                watcher_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                                watched_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                                mood_alert BOOLEAN DEFAULT FALSE,
                                energy_alert BOOLEAN DEFAULT FALSE,
                                sleep_alert BOOLEAN DEFAULT FALSE,
                                physical_alert BOOLEAN DEFAULT FALSE,
                                anxiety_alert BOOLEAN DEFAULT FALSE,
                                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                UNIQUE(watcher_id, watched_id)
                            )
                        """))
                    else:
                        conn.execute(text("""
                            CREATE TABLE parameter_triggers (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                watcher_id INTEGER NOT NULL,
                                watched_id INTEGER NOT NULL,
                                mood_alert INTEGER DEFAULT 0,
                                energy_alert INTEGER DEFAULT 0,
                                sleep_alert INTEGER DEFAULT 0,
                                physical_alert INTEGER DEFAULT 0,
                                anxiety_alert INTEGER DEFAULT 0,
                                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                FOREIGN KEY(watcher_id) REFERENCES users(id) ON DELETE CASCADE,
                                FOREIGN KEY(watched_id) REFERENCES users(id) ON DELETE CASCADE,
                                UNIQUE(watcher_id, watched_id)
                            )
                        """))
                    conn.commit()
                    logger.info("✓ Created parameter_triggers table")
                else:
                    # Table exists, check for missing columns
                    columns = [col['name'] for col in inspector.get_columns('parameter_triggers')]

                    alert_columns = ['mood_alert', 'energy_alert', 'sleep_alert',
                                     'physical_alert', 'anxiety_alert']

                    for col in alert_columns:
                        if col not in columns:
                            logger.info(f"Adding {col} column to parameter_triggers table...")
                            if is_postgres:
                                conn.execute(
                                    text(f"ALTER TABLE parameter_triggers ADD COLUMN {col} BOOLEAN DEFAULT FALSE"))
                            else:
                                conn.execute(text(f"ALTER TABLE parameter_triggers ADD COLUMN {col} INTEGER DEFAULT 0"))
                            conn.commit()
                            logger.info(f"✓ Added {col} column to parameter_triggers table")

                # Auto-migration: Remove posts circle_id foreign key constraint
                if 'posts' in inspector.get_table_names():
                    try:
                        # Check if the constraint exists (PostgreSQL only)
                        if is_postgres:
                            result = conn.execute(text("""
                                SELECT constraint_name 
                                FROM information_schema.table_constraints 
                                WHERE table_name = 'posts' 
                                AND constraint_name = 'posts_circle_id_fkey'
                            """))

                            if result.fetchone():
                                logger.info("Removing posts_circle_id_fkey constraint...")
                                conn.execute(text('ALTER TABLE posts DROP CONSTRAINT posts_circle_id_fkey'))
                                conn.commit()
                                logger.info("✓ Removed posts_circle_id_fkey constraint")
                    except Exception as e:
                        logger.warning(f"Posts constraint removal skipped: {e}")

                    # Clean up posts with invalid circle_id
                    try:
                        result = conn.execute(text("""
                            UPDATE posts 
                            SET circle_id = NULL 
                            WHERE circle_id IS NOT NULL 
                            AND circle_id NOT IN (SELECT id FROM circles)
                        """))
                        conn.commit()
                        rows_updated = result.rowcount
                        if rows_updated > 0:
                            logger.info(f"✓ Cleaned up {rows_updated} posts with invalid circle_id")
                    except Exception as e:
                        logger.warning(f"Posts cleanup skipped: {e}")

                    # Migrate old posts to use visibility field instead of circle_id
                    try:
                        result = conn.execute(text("""
                            UPDATE posts 
                            SET visibility = CASE 
                                WHEN circle_id = 1 THEN 'general'
                                WHEN circle_id = 2 THEN 'close_friends'
                                WHEN circle_id = 3 THEN 'family'
                                ELSE 'private'
                            END
                            WHERE visibility IS NULL OR visibility = ''
                        """))
                        conn.commit()
                        rows_updated = result.rowcount
                        if rows_updated > 0:
                            logger.info(f"✓ Migrated {rows_updated} posts to use visibility field")
                    except Exception as e:
                        logger.warning(f"Posts visibility migration skipped: {e}")

                logger.info("Database auto-migration completed successfully")

        except Exception as e:
            logger.warning(f"Auto-migration error (may be normal if columns exist): {e}")


# Call auto-migration on startup
auto_migrate_database()


# =====================
# DATABASE MODELS
# =====================
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), default='user')
    is_active = db.Column(db.Boolean, default=True)
    preferred_language = db.Column(db.String(5), default='en')
    selected_city = db.Column(db.String(100), default='Jerusalem, Israel')
    # ADD THESE THREE NEW FIELDS:
    has_completed_onboarding = db.Column(db.Boolean, default=False)
    onboarding_dismissed = db.Column(db.Boolean, default=False)
    shareable_link_token = db.Column(db.String(100), unique=True)
    circles_privacy = db.Column(db.String(20), default='private')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = db.Column(db.DateTime)

    # Keep ALL existing relationships
    profile = db.relationship('Profile', backref='user', uselist=False, cascade='all, delete-orphan')
    sent_messages = db.relationship('Message', foreign_keys='Message.sender_id', backref='sender',
                                    cascade='all, delete-orphan')
    received_messages = db.relationship('Message', foreign_keys='Message.recipient_id', backref='recipient',
                                        cascade='all, delete-orphan')
    circles = db.relationship('Circle', foreign_keys='Circle.user_id', backref='owner', cascade='all, delete-orphan')
    saved_parameters = db.relationship('SavedParameters', backref='user', cascade='all, delete-orphan')
    posts = db.relationship('Post', backref='author', cascade='all, delete-orphan')
    alerts = db.relationship('Alert', backref='user', cascade='all, delete-orphan')
    activities = db.relationship('Activity', backref='user', cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    # KEEP THESE METHODS - THEY'RE ESSENTIAL!
    def follow(self, user, note=None):
        """Follow another user with optional note"""
        if not self.is_following(user):
            follow = Follow(follower_id=self.id, followed_id=user.id, follow_note=note)
            db.session.add(follow)

    def unfollow(self, user):
        """Unfollow a user"""
        follow = Follow.query.filter_by(
            follower_id=self.id,
            followed_id=user.id
        ).first()
        if follow:
            db.session.delete(follow)

    def is_following(self, user):
        """Check if following a user"""
        return Follow.query.filter_by(
            follower_id=self.id,
            followed_id=user.id
        ).first() is not None

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'is_active': self.is_active,
            'preferred_language': self.preferred_language or 'en',
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            # ADD THESE TO to_dict():
            'has_completed_onboarding': self.has_completed_onboarding,
            'shareable_link_token': self.shareable_link_token,
            'circles_privacy': self.circles_privacy or 'private'
        }


class PasswordResetToken(db.Model):
    __tablename__ = 'password_reset_tokens'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    token = db.Column(db.String(100), unique=True, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='reset_tokens')


class MagicLoginToken(db.Model):
    __tablename__ = 'magic_login_tokens'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    token = db.Column(db.String(100), unique=True, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_relation = db.relationship('User', backref='magic_tokens')


class UserConsent(db.Model):
    __tablename__ = 'user_consents'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    email_updates = db.Column(db.Boolean, default=False)
    privacy_accepted = db.Column(db.Boolean, default=False)
    research_data = db.Column(db.Boolean, default=False)
    team_declaration = db.Column(db.Boolean, default=False)
    responsible_use = db.Column(db.Boolean, default=False)
    waiver_claims = db.Column(db.Boolean, default=False)
    consent_language = db.Column(db.String(5), default='en')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_relation = db.relationship('User', backref='consent', uselist=False)


class ParameterTrigger(db.Model):
    __tablename__ = 'parameter_triggers'
    id = db.Column(db.Integer, primary_key=True)
    watcher_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    watched_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # New style columns (what you actually use)
    mood_alert = db.Column(db.Boolean, default=False)
    energy_alert = db.Column(db.Boolean, default=False)
    sleep_alert = db.Column(db.Boolean, default=False)
    physical_alert = db.Column(db.Boolean, default=False)
    anxiety_alert = db.Column(db.Boolean, default=False)

    # Old style columns (keep for compatibility with existing DB)
    parameter_name = db.Column(db.String(50), nullable=True)
    trigger_condition = db.Column(db.String(50), nullable=True)
    trigger_value = db.Column(db.Float, nullable=True)
    consecutive_days = db.Column(db.Integer, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    last_triggered = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    watcher = db.relationship('User', foreign_keys=[watcher_id], backref='watching_triggers')
    watched = db.relationship('User', foreign_keys=[watched_id], backref='watched_by_triggers')

    __table_args__ = (db.UniqueConstraint('watcher_id', 'watched_id', name='unique_trigger'),)


class Profile(db.Model):
    __tablename__ = 'profiles'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True)
    bio = db.Column(db.Text)
    interests = db.Column(db.Text)
    occupation = db.Column(db.String(200))
    goals = db.Column(db.Text)
    favorite_hobbies = db.Column(db.Text)
    avatar_url = db.Column(db.String(500))
    mood_status = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Post(db.Model):
    __tablename__ = 'posts'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    content = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(500))
    likes = db.Column(db.Integer, default=0)
    circle_id = db.Column(db.Integer, nullable=True)
    visibility = db.Column(db.String(50), default='general')
    is_published = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    comments = db.relationship('Comment', backref='post', cascade='all, delete-orphan')
    reactions = db.relationship('Reaction', backref='post', cascade='all, delete-orphan')


class Comment(db.Model):
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    author = db.relationship('User', backref='comments')


class Reaction(db.Model):
    __tablename__ = 'reactions'
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    type = db.Column(db.String(20), nullable=False)  # like, love, support, etc.
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('post_id', 'user_id', name='unique_post_reaction'),
    )


class Circle(db.Model):
    __tablename__ = 'circles'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    circle_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    circle_type = db.Column(db.String(50))  # 'public', 'class_b', 'class_a'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    circle_user = db.relationship('User', foreign_keys=[circle_user_id])

    __table_args__ = (
        db.UniqueConstraint('user_id', 'circle_user_id', 'circle_type', name='_user_circle_uc'),
    )


class Message(db.Model):
    __tablename__ = 'messages'
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    recipient_id = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    content = db.Column(db.Text)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)


class SavedParameters(db.Model):
    __tablename__ = 'saved_parameters'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    date = db.Column(db.String(10), index=True)  # String date like '2025-11-03'
    mood = db.Column(db.Integer)
    energy = db.Column(db.Integer)
    sleep_quality = db.Column(db.Integer)
    physical_activity = db.Column(db.Integer)
    anxiety = db.Column(db.Integer)
    mood_privacy = db.Column(db.String(20), default='private')
    energy_privacy = db.Column(db.String(20), default='private')
    sleep_quality_privacy = db.Column(db.String(20), default='private')
    physical_activity_privacy = db.Column(db.String(20), default='private')
    anxiety_privacy = db.Column(db.String(20), default='private')
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)
    # REMOVED: privacy = db.Column(db.JSON)  # This line should be removed/commented

    __table_args__ = (db.UniqueConstraint('user_id', 'date', name='_user_date_uc'),)

    def to_dict(self, viewer_id=None, privacy_level=None):
        base_dict = {
            'id': self.id,
            'date': self.date,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

        if viewer_id == self.user_id:
            base_dict.update({
                'mood': self.mood,
                'energy': self.energy,
                'sleep_quality': self.sleep_quality,
                'physical_activity': self.physical_activity,
                'anxiety': self.anxiety,
                'mood_privacy': self.mood_privacy,
                'energy_privacy': self.energy_privacy,
                'sleep_quality_privacy': self.sleep_quality_privacy,
                'physical_activity_privacy': self.physical_activity_privacy,
                'anxiety_privacy': self.anxiety_privacy,
                'notes': self.notes
            })
        else:
            for param in ['mood', 'energy', 'sleep_quality', 'physical_activity', 'anxiety']:
                param_privacy = getattr(self, f"{param}_privacy", 'public')
                # Only show if public, or if viewer has proper access level (NOT private)
                if param_privacy == 'public' or \
                        (param_privacy == 'class_b' and privacy_level in ['class_b', 'class_a']) or \
                        (param_privacy == 'class_a' and privacy_level == 'class_a'):
                    # Note: 'private' params are excluded - only owner can see
                    base_dict[param] = getattr(self, param)

        return base_dict


class Alert(db.Model):
    __tablename__ = 'alerts'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    title = db.Column(db.String(200))
    content = db.Column(db.Text)  # FIXED: Changed from 'message' to 'content'
    alert_type = db.Column(db.String(50))  # 'info', 'warning', 'success', 'error'
    is_read = db.Column(db.Boolean, default=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'message': self.content,  # Return as 'message' for backward compatibility
            'type': self.alert_type,  # Map alert_type to type for API compatibility
            'is_read': self.is_read,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Activity(db.Model):
    """Store activity feed data by date for calendar functionality"""
    __tablename__ = 'activities'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    activity_date = db.Column(db.Date, nullable=False)
    post_count = db.Column(db.Integer, default=0)
    comment_count = db.Column(db.Integer, default=0)
    message_count = db.Column(db.Integer, default=0)
    mood_entries = db.Column(db.JSON, default=list)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'activity_date', name='unique_user_activity_date'),
    )


class Follow(db.Model):
    __tablename__ = 'follows'
    id = db.Column(db.Integer, primary_key=True)
    follower_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    followed_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    follow_note = db.Column(db.String(300))  # New field for follow notes
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    follower = db.relationship('User', foreign_keys=[follower_id], backref='following')
    followed = db.relationship('User', foreign_keys=[followed_id], backref='followers')

    __table_args__ = (db.UniqueConstraint('follower_id', 'followed_id', name='unique_follow'),)


class FollowRequest(db.Model):
    __tablename__ = 'follow_requests'
    id = db.Column(db.Integer, primary_key=True)
    requester_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    target_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    privacy_level = db.Column(db.String(20), default='public')
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    responded_at = db.Column(db.DateTime)

    requester = db.relationship('User', foreign_keys=[requester_id], backref='sent_follow_requests')
    target = db.relationship('User', foreign_keys=[target_id], backref='received_follow_requests')

    __table_args__ = (db.UniqueConstraint('requester_id', 'target_id', name='unique_follow_request'),)


class NotificationSettings(db.Model):
    __tablename__ = 'notification_settings'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    follow_requests = db.Column(db.Boolean, default=True)
    parameter_triggers = db.Column(db.Boolean, default=True)
    daily_reminder = db.Column(db.Boolean, default=False)
    weekly_summary = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('notification_settings', uselist=False))


def ensure_database_schema():
    """Automatically ensure all required columns exist"""
    # Guard: Skip if already run in this process
    if hasattr(ensure_database_schema, '_completed'):
        return

    try:
        with db.engine.connect() as conn:
            # Check if we're using PostgreSQL or SQLite
            is_postgres = 'postgresql' in str(db.engine.url)

            if is_postgres:
                # PostgreSQL - Check and add visibility column to posts table
                result = conn.execute(text("""
                    SELECT column_name
                    FROM information_schema.columns 
                    WHERE table_name = 'posts' 
                    AND table_schema = 'public'
                """))
                columns = [row[0] for row in result]

                if 'visibility' not in columns:
                    logger.info("Adding visibility column to posts table...")
                    conn.execute(text("ALTER TABLE posts ADD COLUMN visibility VARCHAR(50) DEFAULT 'general'"))
                    conn.commit()
                    logger.info("Visibility column added successfully")

                # PostgreSQL - Check and add circles_privacy column to users table
                result = conn.execute(text("""
                    SELECT column_name
                    FROM information_schema.columns 
                    WHERE table_name = 'users' 
                    AND table_schema = 'public'
                """))
                user_columns = [row[0] for row in result]

                if 'circles_privacy' not in user_columns:
                    logger.info("Adding circles_privacy column to users table...")
                    conn.execute(text("ALTER TABLE users ADD COLUMN circles_privacy VARCHAR(20) DEFAULT 'private'"))
                    conn.commit()
                    logger.info("circles_privacy column added successfully")
                else:
                    logger.debug("✓ circles_privacy column already exists")  # Changed to debug

            else:
                # SQLite - Check and add visibility column to posts table
                result = conn.execute(text("PRAGMA table_info(posts)"))
                columns = [row[1] for row in result]

                if 'visibility' not in columns:
                    logger.info("Adding visibility column to posts table...")
                    conn.execute(text("ALTER TABLE posts ADD COLUMN visibility VARCHAR(50) DEFAULT 'general'"))
                    conn.commit()
                    logger.info("Visibility column added successfully")

                # SQLite - Check and add circles_privacy column to users table
                result = conn.execute(text("PRAGMA table_info(users)"))
                user_columns = [row[1] for row in result]

                if 'circles_privacy' not in user_columns:
                    logger.info("Adding circles_privacy column to users table...")
                    conn.execute(text("ALTER TABLE users ADD COLUMN circles_privacy VARCHAR(20) DEFAULT 'private'"))
                    conn.commit()
                    logger.info("circles_privacy column added successfully")
                else:
                    logger.debug("✓ circles_privacy column already exists")  # Changed to debug

        # Mark as completed for this process
        ensure_database_schema._completed = True

    except Exception as e:
        logger.error(f"Database schema check error: {str(e)}")


# =====================
# DATABASE INITIALIZATION
# =====================

def init_database():
    """Initialize database with migrations and fixes"""
    with app.app_context():
        try:
            # Check if database exists and has tables
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()

            if not tables:
                logger.info("No tables found, creating database schema...")
                db.create_all()
                ensure_database_schema()
                ensure_saved_parameters_schema()  # ← ADDED
                logger.info("Database schema created successfully")
                create_admin_user()
                create_test_users()
                create_test_follows()
                create_parameters_table()
            else:
                logger.info(f"Found {len(tables)} existing tables")

                # Fix all schema issues
                fix_all_schema_issues()
                ensure_database_schema()
                ensure_saved_parameters_schema()  # ← ADDED
                create_test_users()
                create_test_follows()
                create_parameters_table()

                # Only try migrations if migrations folder exists
                if os.path.exists('migrations'):
                    try:
                        from flask_migrate import upgrade
                        logger.info("Checking for pending migrations...")
                        upgrade()
                        logger.info("Database migrations applied successfully")
                    except Exception as e:
                        logger.warning(f"Migration error (non-critical): {e}")
                        logger.info("Using existing database schema")
                else:
                    logger.info("No migrations folder found, using existing schema")

            # Verify database connection
            db.session.execute(select(func.count()).select_from(User))
            db.session.commit()
            logger.info("Database connection verified")

            # Run one-time cleanup of stale trigger alerts
            try:
                removed = cleanup_all_stale_trigger_alerts()
                logger.info(f"Startup cleanup: Removed {removed} stale trigger alerts")
            except Exception as cleanup_err:
                logger.warning(f"Cleanup warning (non-critical): {cleanup_err}")

        except Exception as e:
            logger.error(f"Database initialization error: {e}")
            # Try to create tables as fallback
            try:
                db.create_all()
                logger.info("Created database tables as fallback")
                ensure_saved_parameters_schema()  # ← ADDED
                create_admin_user()
                create_test_users()
                create_test_follows()
                create_parameters_table()
            except Exception as e2:
                logger.error(f"Failed to create tables: {e2}")
                if not is_production:
                    raise


def fix_all_schema_issues():
    """Fix all known database schema issues"""
    try:
        with db.engine.connect() as conn:
            # Check if we're using PostgreSQL or SQLite
            is_postgres = 'postgresql' in str(db.engine.url)

            # 1. Fix alerts table (message -> content)
            try:
                if is_postgres:
                    result = conn.execute(text(
                        """SELECT column_name 
                        FROM information_schema.columns 
                        WHERE table_name='alerts' 
                        AND column_name IN ('message', 'content')"""
                    ))
                    columns = [row[0] for row in result]

                    if 'message' in columns and 'content' not in columns:
                        logger.info("Renaming alerts.message to alerts.content...")
                        conn.execute(text("ALTER TABLE alerts RENAME COLUMN message TO content"))
                        conn.commit()
                        logger.info("✓ Fixed alerts.message column")
                    elif 'content' not in columns and 'message' not in columns:
                        logger.info("Adding missing content column...")
                        conn.execute(text("ALTER TABLE alerts ADD COLUMN content TEXT"))
                        conn.commit()
                        logger.info("✓ Added alerts.content column")
                    else:
                        logger.info("✓ Alerts table schema is correct")
                else:
                    # SQLite handling
                    result = conn.execute(text("PRAGMA table_info(alerts)"))
                    columns = [row[1] for row in result]

                    if 'message' in columns and 'content' not in columns:
                        logger.info("Migrating alerts table for SQLite...")
                        conn.execute(text("""
                            CREATE TABLE alerts_new (
                                id INTEGER PRIMARY KEY,
                                user_id INTEGER,
                                title VARCHAR(200),
                                content TEXT,
                                type VARCHAR(50),
                                is_read BOOLEAN DEFAULT 0,
                                created_at DATETIME,
                                FOREIGN KEY(user_id) REFERENCES users(id)
                            )
                        """))
                        conn.execute(text("""
                            INSERT INTO alerts_new (id, user_id, title, content, type, is_read, created_at)
                            SELECT id, user_id, title, message, type, is_read, created_at FROM alerts
                        """))
                        conn.execute(text("DROP TABLE alerts"))
                        conn.execute(text("ALTER TABLE alerts_new RENAME TO alerts"))
                        conn.commit()
                        logger.info("✓ Migrated alerts table schema")
            except Exception as e:
                logger.warning(f"Could not fix alerts table: {e}")

            # 2. Fix circles table - ensure circle_user_id exists
            try:
                if is_postgres:
                    result = conn.execute(text(
                        """SELECT column_name 
                        FROM information_schema.columns 
                        WHERE table_name='circles'"""
                    ))
                    existing_columns = [row[0] for row in result]

                    if existing_columns:  # Table exists
                        if 'circle_user_id' not in existing_columns:
                            logger.info("Adding missing circle_user_id column to circles table...")
                            conn.execute(text("""
                                ALTER TABLE circles 
                                ADD COLUMN circle_user_id INTEGER 
                                REFERENCES users(id) ON DELETE CASCADE
                            """))
                            conn.commit()
                            logger.info("✓ Added circle_user_id column to circles table")
                        else:
                            logger.info("✓ Circles table has circle_user_id column")
                else:
                    # SQLite
                    result = conn.execute(text("PRAGMA table_info(circles)"))
                    existing_columns = [row[1] for row in result]

                    if existing_columns and 'circle_user_id' not in existing_columns:
                        logger.info("Recreating circles table for SQLite with circle_user_id...")
                        conn.execute(text("""
                            CREATE TABLE circles_new (
                                id INTEGER PRIMARY KEY,
                                user_id INTEGER NOT NULL,
                                circle_user_id INTEGER NOT NULL,
                                circle_type VARCHAR(50),
                                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                                UNIQUE(user_id, circle_user_id, circle_type),
                                FOREIGN KEY(user_id) REFERENCES users(id),
                                FOREIGN KEY(circle_user_id) REFERENCES users(id)
                            )
                        """))
                        conn.execute(text("""
                            INSERT INTO circles_new (id, user_id, circle_type, created_at)
                            SELECT id, user_id, circle_type, created_at FROM circles
                        """))
                        conn.execute(text("DROP TABLE circles"))
                        conn.execute(text("ALTER TABLE circles_new RENAME TO circles"))
                        conn.commit()
                        logger.info("✓ Recreated circles table with circle_user_id")

            except Exception as e:
                logger.warning(f"Could not fix circles table: {e}")

            # 3. Fix profiles table - add missing columns
            try:
                if is_postgres:
                    result = conn.execute(text(
                        """SELECT column_name 
                        FROM information_schema.columns 
                        WHERE table_name='profiles'"""
                    ))
                    existing_columns = [row[0] for row in result]
                else:
                    # SQLite
                    result = conn.execute(text("PRAGMA table_info(profiles)"))
                    existing_columns = [row[1] for row in result]

                # Define all columns that should exist in profiles table
                required_columns = [
                    ('mood_status', 'VARCHAR(50)'),
                    ('avatar_url', 'VARCHAR(500)'),
                    ('interests', 'TEXT'),
                    ('occupation', 'VARCHAR(200)'),
                    ('goals', 'TEXT'),
                    ('favorite_hobbies', 'TEXT')
                ]

                for col_name, col_type in required_columns:
                    if col_name not in existing_columns:
                        logger.info(f"Adding profiles.{col_name} column...")
                        conn.execute(text(f"ALTER TABLE profiles ADD COLUMN {col_name} {col_type}"))
                        conn.commit()
                        logger.info(f"✓ Added profiles.{col_name} column")

            except Exception as e:
                logger.warning(f"Could not fix profiles table: {e}")

            # 4. Ensure activities table exists
            try:
                if is_postgres:
                    result = conn.execute(text(
                        """SELECT table_name 
                        FROM information_schema.tables 
                        WHERE table_name='activities'"""
                    ))
                    table_exists = result.fetchone() is not None
                else:
                    # SQLite
                    result = conn.execute(text(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name='activities'"
                    ))
                    table_exists = result.fetchone() is not None

                if not table_exists:
                    logger.info("Creating activities table...")
                    if is_postgres:
                        conn.execute(text("""
                            CREATE TABLE activities (
                                id SERIAL PRIMARY KEY,
                                user_id INTEGER NOT NULL REFERENCES users(id),
                                activity_date DATE NOT NULL,
                                post_count INTEGER DEFAULT 0,
                                comment_count INTEGER DEFAULT 0,
                                message_count INTEGER DEFAULT 0,
                                mood_entries JSON,
                                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                UNIQUE(user_id, activity_date)
                            )
                        """))
                    else:
                        # SQLite version
                        conn.execute(text("""
                            CREATE TABLE activities (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                user_id INTEGER NOT NULL,
                                activity_date DATE NOT NULL,
                                post_count INTEGER DEFAULT 0,
                                comment_count INTEGER DEFAULT 0,
                                message_count INTEGER DEFAULT 0,
                                mood_entries TEXT,
                                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                UNIQUE(user_id, activity_date),
                                FOREIGN KEY(user_id) REFERENCES users(id)
                            )
                        """))
                    conn.commit()
                    logger.info("✓ Created activities table")
                else:
                    logger.info("✓ Activities table already exists")

            except Exception as e:
                logger.warning(f"Could not create activities table: {e}")

            # 5. Ensure comments table exists
            try:
                if is_postgres:
                    result = conn.execute(text(
                        """SELECT table_name 
                        FROM information_schema.tables 
                        WHERE table_name='comments'"""
                    ))
                    table_exists = result.fetchone() is not None
                else:
                    result = conn.execute(text(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name='comments'"
                    ))
                    table_exists = result.fetchone() is not None

                if not table_exists:
                    logger.info("Creating comments table...")
                    if is_postgres:
                        conn.execute(text("""
                            CREATE TABLE comments (
                                id SERIAL PRIMARY KEY,
                                post_id INTEGER NOT NULL REFERENCES posts(id),
                                user_id INTEGER NOT NULL REFERENCES users(id),
                                content TEXT NOT NULL,
                                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                            )
                        """))
                    else:
                        conn.execute(text("""
                            CREATE TABLE comments (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                post_id INTEGER NOT NULL,
                                user_id INTEGER NOT NULL,
                                content TEXT NOT NULL,
                                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                FOREIGN KEY(post_id) REFERENCES posts(id),
                                FOREIGN KEY(user_id) REFERENCES users(id)
                            )
                        """))
                    conn.commit()
                    logger.info("✓ Created comments table")

            except Exception as e:
                logger.warning(f"Could not create comments table: {e}")

            # 6. Ensure reactions table exists
            try:
                if is_postgres:
                    result = conn.execute(text(
                        """SELECT table_name 
                        FROM information_schema.tables 
                        WHERE table_name='reactions'"""
                    ))
                    table_exists = result.fetchone() is not None
                else:
                    result = conn.execute(text(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name='reactions'"
                    ))
                    table_exists = result.fetchone() is not None

                if not table_exists:
                    logger.info("Creating reactions table...")
                    if is_postgres:
                        conn.execute(text("""
                            CREATE TABLE reactions (
                                id SERIAL PRIMARY KEY,
                                post_id INTEGER NOT NULL REFERENCES posts(id),
                                user_id INTEGER NOT NULL REFERENCES users(id),
                                type VARCHAR(20) NOT NULL,
                                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                UNIQUE(post_id, user_id)
                            )
                        """))
                    else:
                        conn.execute(text("""
                            CREATE TABLE reactions (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                post_id INTEGER NOT NULL,
                                user_id INTEGER NOT NULL,
                                type VARCHAR(20) NOT NULL,
                                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                UNIQUE(post_id, user_id),
                                FOREIGN KEY(post_id) REFERENCES posts(id),
                                FOREIGN KEY(user_id) REFERENCES users(id)
                            )
                        """))
                    conn.commit()
                    logger.info("✓ Created reactions table")

            except Exception as e:
                logger.warning(f"Could not create reactions table: {e}")

            # 7. CRITICAL FIX: Handle posts table with encrypted columns
            try:
                if is_postgres:
                    # Check what columns exist
                    result = conn.execute(text(
                        """SELECT column_name, is_nullable
                        FROM information_schema.columns 
                        WHERE table_name='posts'"""
                    ))
                    column_info = {row[0]: row[1] for row in result}

                    # If encrypted columns exist and are NOT NULL, make them nullable
                    encrypted_cols = ['content_encrypted', 'image_url_encrypted']
                    for col in encrypted_cols:
                        if col in column_info and column_info[col] == 'NO':
                            logger.info(f"Making {col} nullable...")
                            conn.execute(text(f"ALTER TABLE posts ALTER COLUMN {col} DROP NOT NULL"))
                            conn.commit()
                            logger.info(f"✓ Made {col} nullable")

                    # Add missing plain columns
                    required_columns = [
                        ('content', 'TEXT'),
                        ('image_url', 'VARCHAR(500)'),
                        ('likes', 'INTEGER DEFAULT 0'),
                        ('circle_id', 'INTEGER'),
                        ('is_published', 'BOOLEAN DEFAULT TRUE'),
                        ('updated_at', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
                    ]

                    for col_name, col_type in required_columns:
                        if col_name not in column_info:
                            logger.info(f"Adding {col_name} column to posts...")
                            conn.execute(text(f"ALTER TABLE posts ADD COLUMN {col_name} {col_type}"))
                            conn.commit()
                            logger.info(f"✓ Added {col_name} column")
                else:
                    # SQLite - check and add columns
                    result = conn.execute(text("PRAGMA table_info(posts)"))
                    existing_columns = [row[1] for row in result]

                    required_columns = [
                        ('content', 'TEXT'),
                        ('image_url', 'VARCHAR(500)'),
                        ('likes', 'INTEGER DEFAULT 0'),
                        ('circle_id', 'INTEGER'),
                        ('is_published', 'BOOLEAN DEFAULT 1'),
                        ('updated_at', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
                    ]

                    for col_name, col_type in required_columns:
                        if col_name not in existing_columns:
                            logger.info(f"Adding {col_name} column to posts...")
                            conn.execute(text(f"ALTER TABLE posts ADD COLUMN {col_name} {col_type}"))
                            conn.commit()
                            logger.info(f"✓ Added {col_name} column")

            except Exception as e:
                logger.warning(f"Could not fix posts table: {e}")

            # 8. Fix alerts table - ensure type column exists
            try:
                if is_postgres:
                    result = conn.execute(text(
                        """SELECT column_name 
                        FROM information_schema.columns 
                        WHERE table_name='alerts'"""
                    ))
                    existing_columns = [row[0] for row in result]

                    if existing_columns and 'type' not in existing_columns:
                        logger.info("Adding missing type column to alerts table...")
                        conn.execute(text("ALTER TABLE alerts ADD COLUMN type VARCHAR(50) DEFAULT 'info'"))
                        conn.commit()
                        logger.info("✓ Added type column to alerts table")
                else:
                    # SQLite
                    result = conn.execute(text("PRAGMA table_info(alerts)"))
                    existing_columns = [row[1] for row in result]

                    if existing_columns and 'type' not in existing_columns:
                        logger.info("Adding type column to alerts table...")
                        conn.execute(text("ALTER TABLE alerts ADD COLUMN type VARCHAR(50) DEFAULT 'info'"))
                        conn.commit()
                        logger.info("✓ Added type column to alerts table")

            except Exception as e:
                logger.warning(f"Could not add type column to alerts table: {e}")

            # 9. Add preferred_language column to users table
            try:
                if is_postgres:
                    result = conn.execute(text(
                        """SELECT column_name 
                        FROM information_schema.columns 
                        WHERE table_name='users'"""
                    ))
                    existing_columns = [row[0] for row in result]

                    if existing_columns and 'preferred_language' not in existing_columns:
                        logger.info("Adding missing preferred_language column to users table...")
                        conn.execute(text("ALTER TABLE users ADD COLUMN preferred_language VARCHAR(5) DEFAULT 'en'"))
                        conn.commit()
                        logger.info("✓ Added preferred_language column to users table")
                    elif 'preferred_language' in existing_columns:
                        logger.info("✓ Users table already has preferred_language column")
                else:
                    # SQLite
                    result = conn.execute(text("PRAGMA table_info(users)"))
                    existing_columns = [row[1] for row in result]

                    if existing_columns and 'preferred_language' not in existing_columns:
                        logger.info("Adding preferred_language column to users table...")
                        conn.execute(text("ALTER TABLE users ADD COLUMN preferred_language VARCHAR(5) DEFAULT 'en'"))
                        conn.commit()
                        logger.info("✓ Added preferred_language column to users table")
                    elif 'preferred_language' in existing_columns:
                        logger.info("✓ Users table already has preferred_language column")

            except Exception as e:
                logger.warning(f"Could not add preferred_language column to users table: {e}")

            try:
                if is_postgres:
                    result = conn.execute(text(
                        """SELECT column_name 
                        FROM information_schema.columns 
                        WHERE table_name='users'"""
                    ))
                    existing_columns = [row[0] for row in result]

                    if existing_columns and 'selected_city' not in existing_columns:
                        logger.info("Adding missing selected_city column to users table...")
                        conn.execute(
                            text("ALTER TABLE users ADD COLUMN selected_city VARCHAR(100) DEFAULT 'Jerusalem, Israel'"))
                        conn.commit()
                        logger.info("✓ Added selected_city column to users table")
                    elif 'selected_city' in existing_columns:
                        logger.info("✓ Users table already has selected_city column")
                else:
                    # SQLite
                    result = conn.execute(text("PRAGMA table_info(users)"))
                    existing_columns = [row[1] for row in result]

                    if existing_columns and 'selected_city' not in existing_columns:
                        logger.info("Adding selected_city column to users table...")
                        conn.execute(
                            text("ALTER TABLE users ADD COLUMN selected_city VARCHAR(100) DEFAULT 'Jerusalem, Israel'"))
                        conn.commit()
                        logger.info("✓ Added selected_city column to users table")
                    elif 'selected_city' in existing_columns:
                        logger.info("✓ Users table already has selected_city column")

            except Exception as e:
                logger.warning(f"Could not add selected_city column to users table: {e}")

            logger.info("✓ All schema fixes complete")

    except Exception as e:
        logger.error(f"Error in fix_all_schema_issues: {e}")
        # Don't fail the entire initialization for schema fixes
        pass


def create_test_users():
    """Create 12 test users for the social app"""
    try:
        logger.info("Checking for test users...")

        test_users = [
            {'username': 'alice', 'email': 'alice@example.com', 'password': 'password123',
             'bio': 'Love hiking and photography', 'interests': 'Photography, Hiking, Travel',
             'occupation': 'Photographer', 'goals': 'Travel to 50 countries', 'hobbies': 'Reading, Yoga'},

            {'username': 'bob', 'email': 'bob@example.com', 'password': 'password123',
             'bio': 'Software developer and gamer', 'interests': 'Gaming, Programming, Tech',
             'occupation': 'Software Engineer', 'goals': 'Build a successful startup', 'hobbies': 'Gaming, Coding'},

            {'username': 'charlie', 'email': 'charlie@example.com', 'password': 'password123',
             'bio': 'Chef and food enthusiast', 'interests': 'Cooking, Food, Wine',
             'occupation': 'Chef', 'goals': 'Open my own restaurant', 'hobbies': 'Cooking, Wine tasting'},

            {'username': 'diana', 'email': 'diana@example.com', 'password': 'password123',
             'bio': 'Artist and creative soul', 'interests': 'Art, Music, Dance',
             'occupation': 'Graphic Designer', 'goals': 'Have an art exhibition', 'hobbies': 'Painting, Dancing'},

            {'username': 'edward', 'email': 'edward@example.com', 'password': 'password123',
             'bio': 'Fitness coach and athlete', 'interests': 'Fitness, Sports, Nutrition',
             'occupation': 'Personal Trainer', 'goals': 'Complete an Ironman', 'hobbies': 'Running, Swimming'},

            {'username': 'fiona', 'email': 'fiona@example.com', 'password': 'password123',
             'bio': 'Teacher and bookworm', 'interests': 'Education, Literature, History',
             'occupation': 'High School Teacher', 'goals': 'Write a novel', 'hobbies': 'Reading, Writing'},

            {'username': 'george', 'email': 'george@example.com', 'password': 'password123',
             'bio': 'Musician and composer', 'interests': 'Music, Guitar, Jazz',
             'occupation': 'Music Teacher', 'goals': 'Record an album', 'hobbies': 'Guitar, Piano'},

            {'username': 'helen', 'email': 'helen@example.com', 'password': 'password123',
             'bio': 'Entrepreneur and innovator', 'interests': 'Business, Marketing, Innovation',
             'occupation': 'Marketing Manager', 'goals': 'Launch a successful product',
             'hobbies': 'Networking, Reading'},

            {'username': 'ivan', 'email': 'ivan@example.com', 'password': 'password123',
             'bio': 'Doctor and health advocate', 'interests': 'Medicine, Health, Research',
             'occupation': 'Physician', 'goals': 'Contribute to medical research', 'hobbies': 'Tennis, Chess'},

            {'username': 'julia', 'email': 'julia@example.com', 'password': 'password123',
             'bio': 'Environmental scientist', 'interests': 'Environment, Science, Sustainability',
             'occupation': 'Environmental Consultant', 'goals': 'Make a positive environmental impact',
             'hobbies': 'Gardening, Hiking'},

            {'username': 'kevin', 'email': 'kevin@example.com', 'password': 'password123',
             'bio': 'Film director and storyteller', 'interests': 'Film, Cinema, Storytelling',
             'occupation': 'Video Producer', 'goals': 'Direct a feature film', 'hobbies': 'Photography, Film'},

            {'username': 'laura', 'email': 'laura@example.com', 'password': 'password123',
             'bio': 'Psychologist and mindfulness coach', 'interests': 'Psychology, Mindfulness, Wellness',
             'occupation': 'Clinical Psychologist', 'goals': 'Help 1000 people improve their mental health',
             'hobbies': 'Meditation, Yoga'}
        ]

        created_count = 0
        for user_data in test_users:
            # Check if user exists
            existing_user = User.query.filter_by(email=user_data['email']).first()
            if not existing_user:
                # Create user
                user = User(
                    username=user_data['username'],
                    email=user_data['email']
                )
                user.set_password(user_data['password'])
                db.session.add(user)
                db.session.flush()  # Get the user ID

                # Create profile
                profile = Profile(
                    user_id=user.id,
                    bio=user_data['bio'],
                    interests=user_data['interests'],
                    occupation=user_data['occupation'],
                    goals=user_data['goals'],
                    favorite_hobbies=user_data['hobbies']
                )
                db.session.add(profile)
                created_count += 1
                logger.info(f"Created test user: {user_data['username']}")

        if created_count > 0:
            db.session.commit()
            logger.info(f"✓ Created {created_count} test users")
        else:
            logger.info("✓ Test users already exist")

    except Exception as e:
        logger.error(f"Error creating test users: {e}")
        db.session.rollback()


def create_test_follows():
    """Create follow relationships between test users and main user"""
    try:
        logger.info("Setting up test follow relationships...")

        # Get the main user (emaskanazi_1)
        main_user = User.query.filter_by(username='emaskanazi_1').first()
        if not main_user:
            logger.info("Main user emaskanazi_1 not found, skipping test follows")
            return

        # Get test users
        test_usernames = ['alice', 'bob', 'charlie', 'diana', 'edward', 'fiona',
                          'george', 'helen', 'ivan', 'julia', 'kevin', 'laura']

        test_users = User.query.filter(User.username.in_(test_usernames)).all()

        if not test_users:
            logger.info("No test users found, skipping test follows")
            return

        # Count existing follows
        existing_follows = Follow.query.filter_by(followed_id=main_user.id).count()

        if existing_follows >= len(test_users):
            logger.info(f"✓ Test follows already exist ({existing_follows} followers)")
            return

        # Create follows: each test user follows the main user
        created_count = 0
        for test_user in test_users:
            # Check if follow already exists
            existing = Follow.query.filter_by(
                follower_id=test_user.id,
                followed_id=main_user.id
            ).first()

            if not existing:
                follow = Follow(
                    follower_id=test_user.id,
                    followed_id=main_user.id
                )
                db.session.add(follow)
                created_count += 1

        # Also make main user follow some test users back
        for test_user in test_users[:6]:  # Follow back half of them
            existing = Follow.query.filter_by(
                follower_id=main_user.id,
                followed_id=test_user.id
            ).first()

            if not existing:
                follow = Follow(
                    follower_id=main_user.id,
                    followed_id=test_user.id
                )
                db.session.add(follow)

        db.session.commit()
        logger.info(f"✓ Created {created_count} new follow relationships")

        # Verify
        follower_count = Follow.query.filter_by(followed_id=main_user.id).count()
        following_count = Follow.query.filter_by(follower_id=main_user.id).count()
        logger.info(f"Main user now has {follower_count} followers and is following {following_count} users")

    except Exception as e:
        logger.error(f"Error creating test follows: {e}")
        db.session.rollback()


def create_parameters_table():
    """Create parameters table if it doesn't exist with correct schema"""
    try:
        logger.info("Checking parameters table...")

        conn = get_db()
        cursor = conn.cursor()

        # Check if parameters table exists and has correct columns
        try:
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'parameters'
                ORDER BY ordinal_position
            """)
            columns = [row['column_name'] for row in cursor.fetchall()]

            # Check if we have the mood/energy columns (our actual schema)
            required_columns = ['date', 'mood', 'energy', 'sleep_quality', 'user_id']

            if columns and all(col in columns for col in required_columns):
                logger.info("✓ Parameters table exists with correct schema")
                cursor.close()
                conn.close()
                return
            elif columns:
                # Table exists but has wrong schema
                logger.info(f"Parameters table has wrong columns: {columns}")
                logger.info("Attempting to drop and recreate parameters table...")

                # Try to drop with timeout
                cursor.execute("SET statement_timeout = '5s'")  # 5 second timeout
                try:
                    cursor.execute("DROP TABLE IF EXISTS parameters CASCADE")
                    conn.commit()
                    logger.info("Old parameters table dropped successfully")
                except Exception as drop_error:
                    logger.error(f"Failed to drop parameters table: {drop_error}")
                    # Try to rename instead of drop
                    try:
                        cursor.execute("ALTER TABLE parameters RENAME TO parameters_old")
                        conn.commit()
                        logger.info("Renamed old parameters table to parameters_old")
                    except:
                        logger.error("Could not drop or rename old table, continuing anyway...")
                        cursor.close()
                        conn.close()
                        return  # Give up, don't block startup

        except Exception as e:
            logger.info(f"Parameters table check: {e}")
            # Table doesn't exist, continue to create it

        # Create the new parameters table with correct schema
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS parameters (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                date DATE NOT NULL,
                mood INTEGER CHECK (mood >= 1 AND mood <= 4),
                energy INTEGER CHECK (energy >= 1 AND energy <= 4),
                sleep_quality INTEGER CHECK (sleep_quality >= 1 AND sleep_quality <= 4),
                physical_activity INTEGER CHECK (physical_activity >= 1 AND physical_activity <= 4),
                anxiety INTEGER CHECK (anxiety >= 1 AND anxiety <= 4),
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, date)
            )
        ''')

        conn.commit()
        logger.info("✓ Parameters table created with correct schema")

        cursor.close()
        conn.close()

    except Exception as e:
        logger.error(f"Error in create_parameters_table: {e}")
        # Don't crash the app startup over this
        try:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
        except:
            pass


def create_admin_user():
    """Create default admin user if it doesn't exist"""
    try:
        admin_email = os.environ.get('ADMIN_EMAIL', 'admin@example.com')
        admin_password = os.environ.get('ADMIN_PASSWORD', 'admin123')

        # Check if admin exists - SQLAlchemy 2.0 style
        stmt = select(User).filter_by(email=admin_email)
        admin = db.session.execute(stmt).scalar_one_or_none()

        if not admin:
            admin = User(
                username='admin',
                email=admin_email,
                role='admin',
                is_active=True
            )
            admin.set_password(admin_password)
            db.session.add(admin)
            db.session.flush()

            # Create admin profile
            profile = Profile(user_id=admin.id)
            db.session.add(profile)

            # Create welcome alert
            alert = Alert(
                user_id=admin.id,
                title='Welcome Admin!',
                content='Your admin account has been created.',
                alert_type='success'
            )
            db.session.add(alert)

            db.session.commit()
            logger.info(f"Admin user created: {admin_email}")
        else:
            logger.info("Admin user already exists")

    except Exception as e:
        logger.error(f"Error creating admin user: {e}")
        db.session.rollback()


# =====================
# DECORATORS
# =====================

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required'}), 401

        # Verify user still exists and is active
        user = db.session.get(User, session['user_id'])
        if not user or not user.is_active:
            session.clear()
            return jsonify({'error': 'Invalid session'}), 401

        return f(*args, **kwargs)

    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required'}), 401

        user = db.session.get(User, session['user_id'])
        if not user or user.role != 'admin':
            return jsonify({'error': 'Admin privileges required'}), 403

        return f(*args, **kwargs)

    return decorated_function


# =====================
# REQUEST HANDLERS
# =====================

@app.before_request
def before_request():
    """Log request details"""
    request.request_id = str(uuid.uuid4())
    if not request.path.startswith('/static'):
        logger.info(f"Request started: {request.method} {request.path}")


@app.after_request
def after_request(response):
    """Log response details and set security headers"""
    if not request.path.startswith('/static'):
        logger.info(f"Request completed: {response.status_code}")

    # Security headers
    if is_production:
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'

    return response


# =====================
# BASIC ROUTES
# =====================

@app.route('/')
def index():
    """Main landing page"""
    return render_template('index.html')


@app.route('/favicon.ico')
def favicon():
    """Serve favicon - handle missing file gracefully"""
    try:
        return send_from_directory(os.path.join(app.root_path, 'static'),
                                   'favicon.ico', mimetype='image/vnd.microsoft.icon')
    except:
        return '', 204


@app.route('/about')
def about_page():
    """About page"""
    return render_template('about.html')


@app.route('/support')
def support_page():
    """Support page"""
    return render_template('support.html')


@app.route('/profile')
@login_required
def profile_page():
    """Profile page"""
    return render_template('profile.html')


@app.route('/circles')
@login_required
def circles_page():
    """Circles page"""
    return render_template('circles.html', cache_bust=CACHE_BUST_VERSION)


@app.route('/messages')
@login_required
def messages_page():
    """Messages page"""
    return render_template('messages.html')


@app.route('/parameters')
@login_required
def parameters_page():
    return render_template('parameters.html')


@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    status = {'status': 'healthy', 'timestamp': datetime.utcnow().isoformat()}

    try:
        # Check database
        db.session.execute(text('SELECT 1'))
        status['database'] = 'OK'
    except Exception as e:
        status['database'] = f'Error: {str(e)}'
        status['status'] = 'unhealthy'

    # Check Redis if configured
    try:
        if redis_client:
            redis_client.ping()
            status['redis'] = 'OK'
        else:
            status['redis'] = 'Not configured'
    except Exception as e:
        status['redis'] = f'Error: {str(e)}'

    return jsonify(status), 200 if status['status'] == 'healthy' else 503


# =====================
# AUTHENTICATION ROUTES
# =====================

@app.route('/api/auth/register', methods=['POST'])
@rate_limit(max_attempts=5, window_minutes=15)
def register():
    """Register new user"""
    try:
        data = request.json

        # Validate input
        username = sanitize_input(data.get('username', '').strip())
        email = sanitize_input(data.get('email', '').strip().lower())
        password = data.get('password', '')

        # Default username to email local part if not provided
        if not username and email:
            username = email.split('@')[0]
            # Sanitize the generated username too
            username = sanitize_input(username)

        # Validation - now password and email are required, username will have a default
        if not email or not password:
            return jsonify({'error': 'Email and password are required'}), 400

        # Check username after defaulting
        if not username:
            return jsonify({'error': 'Username could not be generated from email'}), 400

        if not validate_email(email):
            return jsonify({'error': 'Invalid email format'}), 400

        if not validate_username(username):
            return jsonify({'error': 'Invalid username format'}), 400

        valid, msg = validate_password_strength(password)
        if not valid:
            return jsonify({'error': msg}), 400

        # Check if user exists - SQLAlchemy 2.0 style
        existing_email = db.session.execute(
            select(User).filter_by(email=email)
        ).scalar_one_or_none()

        if existing_email:
            return jsonify({'error': 'Email already registered'}), 400

        existing_username = db.session.execute(
            select(User).filter_by(username=username)
        ).scalar_one_or_none()

        if existing_username:
            return jsonify({'error': 'Username already taken'}), 400

        # Create user
        user = User(
            username=username,
            email=email,
            preferred_language=data.get('preferred_language', 'en')
        )
        user.set_password(password)
        db.session.add(user)
        db.session.flush()

        # Create profile
        profile = Profile(user_id=user.id)
        db.session.add(profile)

        # Create welcome alert
        alert = Alert(
            user_id=user.id,
            title='alerts.welcome_title',
            content='alerts.welcome_message',
            alert_type='success'
        )
        db.session.add(alert)

        db.session.commit()

        # Log user in
        session['user_id'] = user.id
        session['username'] = user.username
        session.permanent = True

        logger.info(f"User registered: {username}")

        return jsonify({
            'success': True,
            'user': user.to_dict()
        }), 200

    except IntegrityError as e:
        logger.error(f"Registration integrity error: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Username or email already exists'}), 400
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Registration failed'}), 500


@app.route('/api/auth/login', methods=['POST'])
@rate_limit(max_attempts=10, window_minutes=15)
def login():
    """User login"""
    try:
        data = request.json
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')

        if not email or not password:
            return jsonify({'error': 'Email and password required'}), 400

        # Find user - SQLAlchemy 2.0 style
        user = db.session.execute(
            select(User).filter_by(email=email)
        ).scalar_one_or_none()

        if not user or not user.check_password(password):
            return jsonify({'error': 'Invalid credentials'}), 401

        if not user.is_active:
            return jsonify({'error': 'Account deactivated'}), 403

        # Update last login
        user.last_login = datetime.utcnow()
        db.session.commit()

        # Create session
        session['user_id'] = user.id
        session['username'] = user.username
        session['role'] = user.role
        session.permanent = True

        logger.info(f"Login successful: {user.username}")

        # Prepare user data with language preference
        user_data = user.to_dict()
        user_data['preferred_language'] = user.preferred_language or 'en'

        return jsonify({
            'success': True,
            'user': user_data
        }), 200

    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return jsonify({'error': 'Login failed'}), 500


@app.route('/api/auth/logout', methods=['POST'])
def logout():
    """User logout"""
    user_id = session.get('user_id')
    session.clear()
    logger.info(f"User logged out: {user_id}")
    return jsonify({'success': True}), 200


@app.route('/api/onboarding/status', methods=['GET'])
@login_required
def get_onboarding_status():
    user = User.query.get(session['user_id'])
    return jsonify({
        'needs_onboarding': not user.has_completed_onboarding and not user.onboarding_dismissed,
        'has_completed': user.has_completed_onboarding,
        'was_dismissed': user.onboarding_dismissed
    })


@app.route('/api/onboarding/complete', methods=['POST'])
@login_required
def complete_onboarding():
    user = User.query.get(session['user_id'])
    user.has_completed_onboarding = True
    db.session.commit()
    return jsonify({'message': 'Onboarding completed'}), 200


@app.route('/api/onboarding/dismiss', methods=['POST'])
@login_required
def dismiss_onboarding():
    user = User.query.get(session['user_id'])
    user.onboarding_dismissed = True
    db.session.commit()
    return jsonify({'message': 'Onboarding dismissed'}), 200


@app.route('/api/auth/session', methods=['GET'])
def check_session():
    """Check if user is logged in"""
    if 'user_id' in session:
        user = db.session.get(User, session['user_id'])
        if user and user.is_active:
            return jsonify({
                'authenticated': True,
                'user': user.to_dict()
            })

    return jsonify({'authenticated': False}), 401


# =====================
# USER & PROFILE ROUTES
# =====================

@app.route('/api/user/profile', methods=['GET'])
@login_required
def get_current_user():
    """Get current user info"""
    user = db.session.get(User, session['user_id'])
    if not user:
        return jsonify({'error': 'User not found'}), 404

    return jsonify(user.to_dict())


@app.route('/api/user/language', methods=['POST'])
def update_user_language():
    """
    Update user's language preference
    Works both for authenticated and unauthenticated users
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'message': 'No data provided'
            }), 400

        # FIXED: Accept both 'language' and 'preferred_language' for compatibility
        language = data.get('preferred_language') or data.get('language', 'en')

        # Validate language code
        valid_languages = ['en', 'he', 'ar', 'ru']
        if language not in valid_languages:
            return jsonify({
                'success': False,
                'message': 'Invalid language code'
            }), 400

        # If user is authenticated, save to database
        if 'user_id' in session:
            user_id = session['user_id']

            try:
                user = db.session.get(User, user_id)
                if user:
                    # FIXED: Use correct column name 'preferred_language'
                    user.preferred_language = language
                    db.session.commit()

                    logger.info(f"Updated language for user {user_id} to {language}")
                    return jsonify({
                        'success': True,
                        'message': 'Language preference saved',
                        'language': language  # Return the saved language
                    }), 200
                else:
                    return jsonify({
                        'success': False,
                        'message': 'User not found'
                    }), 404

            except Exception as e:
                db.session.rollback()
                logger.error(f"Error updating language preference: {e}")
                return jsonify({
                    'success': False,
                    'message': 'Database error'
                }), 500
        else:
            # For unauthenticated users, store in session
            session['preferred_language'] = language  # FIXED: Consistent naming

            logger.info(f"Stored language {language} in session (unauthenticated)")
            return jsonify({
                'success': True,
                'message': 'Language preference saved in session',
                'language': language
            }), 200

    except Exception as e:
        logger.error(f"Error in update_user_language: {e}")
        return jsonify({
            'success': False,
            'message': 'Server error'
        }), 500


@app.route('/api/user/update-city', methods=['POST'])
@login_required
def update_user_city():
    """Update user's selected city"""
    try:
        data = request.json
        selected_city = data.get('selected_city')

        if not selected_city:
            return jsonify({'error': 'City required'}), 400

        user = db.session.get(User, session['user_id'])
        if not user:
            return jsonify({'error': 'User not found'}), 404

        user.selected_city = selected_city
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'City updated successfully'
        }), 200

    except Exception as e:
        logger.error(f"Error updating city: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to update city'}), 500


@app.route('/api/user/change-password', methods=['POST'])
@login_required
def change_password():
    """Change user password"""
    try:
        data = request.json
        current_password = data.get('current_password')
        new_password = data.get('new_password')

        if not current_password or not new_password:
            return jsonify({'error': 'Current and new passwords required'}), 400

        user = db.session.get(User, session['user_id'])
        if not user:
            return jsonify({'error': 'User not found'}), 404

        # Verify current password
        if not user.check_password(current_password):
            return jsonify({'error': 'Current password is incorrect'}), 401

        # Validate new password
        if len(new_password) < 12:
            return jsonify({'error': 'Password must be at least 12 characters long'}), 400

        # Check complexity
        import re
        has_upper = bool(re.search(r'[A-Z]', new_password))
        has_lower = bool(re.search(r'[a-z]', new_password))
        has_digit = bool(re.search(r'[0-9]', new_password))
        has_special = bool(re.search(r'[!@#$%^&*(),.?":{}|<>]', new_password))

        if not (has_upper and has_lower and has_digit and has_special):
            return jsonify({'error': 'Password must contain uppercase, lowercase, number, and special character'}), 400

        # Update password
        user.set_password(new_password)
        db.session.commit()

        logger.info(f"Password changed for user {user.id}")

        return jsonify({
            'success': True,
            'message': 'Password updated successfully'
        }), 200

    except Exception as e:
        logger.error(f"Error changing password: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to change password'}), 500


@app.route('/api/auth/request-magic-link', methods=['POST'])
@rate_limit(max_attempts=5, window_minutes=15)
def request_magic_link():
    """Request magic link for email-only login"""
    try:
        data = request.json
        email = data.get('email', '').strip().lower()
        language = data.get('language', 'en')

        if not email:
            return jsonify({'error': 'Email required'}), 400

        user = db.session.execute(
            select(User).filter_by(email=email)
        ).scalar_one_or_none()

        if not user:
            import secrets
            # Extract username from email (part before @)
            email_username = email.split('@')[0]

            # Check if this username is taken
            existing = db.session.execute(
                select(User).filter_by(username=email_username)
            ).scalar_one_or_none()

            # If taken, add random suffix
            if existing:
                temp_username = f"{email_username}_{secrets.token_hex(4)}"
            else:
                temp_username = email_username

            user = User(
                username=temp_username,
                email=email,
                preferred_language=language
            )
            user.set_password(secrets.token_urlsafe(32))
            db.session.add(user)
            db.session.flush()

            profile = Profile(user_id=user.id)
            db.session.add(profile)

        import secrets
        magic_token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(days=1825)

        token_record = MagicLoginToken(
            user_id=user.id,
            token=magic_token,
            expires_at=expires_at
        )
        db.session.add(token_record)
        db.session.commit()

        user_language = user.preferred_language or language
        send_magic_link_email(user.email, magic_token, user_language)

        return jsonify({'success': True, 'message': 'Magic link sent'}), 200

    except Exception as e:
        logger.error(f"Magic link error: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to send magic link'}), 500


@app.route('/api/auth/verify-magic-link', methods=['POST'])
def verify_magic_link():
    """Verify magic link and log user in"""
    try:
        data = request.json
        magic_token = data.get('token', '')

        if not magic_token:
            return jsonify({'error': 'Token required'}), 400

        token_record = db.session.execute(
            select(MagicLoginToken).filter_by(
                token=magic_token
                # Removed: used=False check - allow unlimited use
            )
        ).scalar_one_or_none()

        if not token_record or token_record.expires_at < datetime.utcnow():
            return jsonify({'error': 'Invalid or expired token'}), 400

        # DO NOT mark as used - allow unlimited clicks until new token generated
        # token_record.used = True  # COMMENTED OUT
        user = db.session.get(User, token_record.user_id)

        # Check if username needs confirmation (not if it's from email)
        email_prefix = user.email.split('@')[0]
        needs_username = False  # Don't force username change if it matches email

        consent = db.session.execute(
            select(UserConsent).filter_by(user_id=user.id)
        ).scalar_one_or_none()
        needs_consent = consent is None

        user.last_login = datetime.utcnow()
        db.session.commit()

        session['user_id'] = user.id
        session['username'] = user.username
        session['role'] = user.role
        session.permanent = True

        return jsonify({
            'success': True,
            'needs_username': needs_username,
            'needs_consent': needs_consent,
            'user': user.to_dict(),
            'suggested_username': email_prefix  # Send suggestion to frontend
        }), 200

    except Exception as e:
        logger.error(f"Magic link verification error: {e}")
        return jsonify({'error': 'Verification failed'}), 500


@app.route('/api/auth/set-username', methods=['POST'])
@login_required
def set_username():
    """Set username for magic link users (optional)"""
    try:
        data = request.json
        new_username = data.get('username', '').strip()
        skip_username = data.get('skip', False)

        user = db.session.get(User, session['user_id'])

        # If skipping, keep the email-based username
        if skip_username:
            # Username already set from email, just return success
            return jsonify({'success': True, 'username': user.username}), 200

        if not new_username:
            # If blank, use email prefix
            new_username = user.email.split('@')[0]

        # Validate username
        if not validate_username(new_username):
            return jsonify({'error': 'Invalid username format'}), 400

        # Check if username taken (excluding current user)
        existing = db.session.execute(
            select(User).filter(
                User.username == new_username,
                User.id != user.id
            )
        ).scalar_one_or_none()

        if existing:
            return jsonify({'error': 'Username already taken'}), 400

        user.username = new_username
        session['username'] = new_username
        db.session.commit()

        return jsonify({'success': True, 'username': new_username}), 200

    except Exception as e:
        logger.error(f"Set username error: {e}")
        return jsonify({'error': 'Failed to set username'}), 500


@app.route('/api/auth/save-consent', methods=['POST'])
@login_required
def save_consent():
    """Save user consent preferences with optional username"""
    try:
        data = request.json

        # Handle username if provided with consent
        username = data.get('username', '').strip()
        if username:
            user = db.session.get(User, session['user_id'])

            # If blank, use email prefix
            if not username:
                username = user.email.split('@')[0]

            # Check if username is available
            existing = db.session.execute(
                select(User).filter(
                    User.username == username,
                    User.id != user.id
                )
            ).scalar_one_or_none()

            if not existing:
                user.username = username
                session['username'] = username

        # Check if consent already exists
        consent = db.session.execute(
            select(UserConsent).filter_by(user_id=session['user_id'])
        ).scalar_one_or_none()

        if not consent:
            consent = UserConsent(user_id=session['user_id'])
            db.session.add(consent)

        # Update consent fields
        consent.email_updates = data.get('email_updates', False)
        consent.privacy_accepted = data.get('privacy_accepted', False)
        consent.research_data = data.get('research_data', False)
        consent.team_declaration = data.get('team_declaration', False)
        consent.responsible_use = data.get('responsible_use', False)
        consent.waiver_claims = data.get('waiver_claims', False)
        consent.consent_language = data.get('language', 'en')

        # All required consents must be true
        required = ['privacy_accepted', 'team_declaration', 'responsible_use', 'waiver_claims']
        all_accepted = all(data.get(field, False) for field in required)

        if not all_accepted:
            return jsonify({'error': 'All required consents must be accepted'}), 400

        db.session.commit()
        return jsonify({'success': True}), 200

    except Exception as e:
        logger.error(f"Save consent error: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to save consent'}), 500


@app.route('/api/user/delete-account', methods=['POST'])
@login_required
def delete_account():
    """Delete user account and all associated data"""
    try:
        user_id = session['user_id']
        user = db.session.get(User, user_id)

        if not user:
            return jsonify({'error': 'User not found'}), 404

        # Log the deletion
        logger.info(f"Deleting account for user {user.id} ({user.username})")

        # Delete user (cascade will handle related data)
        db.session.delete(user)
        db.session.commit()

        # Clear session
        session.clear()

        return jsonify({
            'success': True,
            'message': 'Account deleted successfully'
        }), 200

    except Exception as e:
        logger.error(f"Error deleting account: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to delete account'}), 500


@app.route('/api/auth/forgot-password', methods=['POST'])
@rate_limit(max_attempts=5, window_minutes=60)
def forgot_password():
    """Request password reset with language support"""
    try:
        data = request.json
        email = data.get('email', '').strip().lower()
        language = data.get('language', 'en')

        if not email:
            return jsonify({'error': 'Email required'}), 400

        user = db.session.execute(
            select(User).filter_by(email=email)
        ).scalar_one_or_none()

        if not user:
            logger.info(f"Password reset requested for non-existent email: {email}")
            return jsonify({
                'success': True,
                'message': 'If an account exists with that email, a reset link has been sent'
            }), 200

        import secrets
        reset_token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(hours=1)

        token_record = PasswordResetToken(
            user_id=user.id,
            token=reset_token,
            expires_at=expires_at
        )
        db.session.add(token_record)
        db.session.commit()

        user_language = user.preferred_language or language
        email_sent = send_password_reset_email(user.email, reset_token, user_language)

        return jsonify({
            'success': True,
            'message': 'If an account exists with that email, a reset link has been sent'
        }), 200

    except Exception as e:
        logger.error(f"Forgot password error: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to process request'}), 500


@app.route('/api/auth/reset-password', methods=['POST'])
def reset_password():
    """Reset password using token"""
    try:
        data = request.json
        token = data.get('token')
        new_password = data.get('new_password')

        if not token or not new_password:
            return jsonify({'error': 'Token and new password required'}), 400

        # Find token
        token_record = db.session.execute(
            select(PasswordResetToken).filter_by(token=token, used=False)
        ).scalar_one_or_none()

        if not token_record:
            return jsonify({'error': 'Invalid or expired reset token'}), 400

        # Check if token expired
        if datetime.utcnow() > token_record.expires_at:
            return jsonify({'error': 'Reset token has expired'}), 400

        # Validate new password
        if len(new_password) < 12:
            return jsonify({'error': 'Password must be at least 12 characters long'}), 400

        # Check complexity
        import re
        has_upper = bool(re.search(r'[A-Z]', new_password))
        has_lower = bool(re.search(r'[a-z]', new_password))
        has_digit = bool(re.search(r'[0-9]', new_password))
        has_special = bool(re.search(r'[!@#$%^&*(),.?":{}|<>]', new_password))

        if not (has_upper and has_lower and has_digit and has_special):
            return jsonify({'error': 'Password must contain uppercase, lowercase, number, and special character'}), 400

        # Get user and update password
        user = db.session.get(User, token_record.user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        user.set_password(new_password)
        token_record.used = True
        db.session.commit()

        logger.info(f"Password reset successful for user {user.id}")

        return jsonify({
            'success': True,
            'message': 'Password reset successfully'
        }), 200

    except Exception as e:
        logger.error(f"Reset password error: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to reset password'}), 500


@app.route('/api/user/language', methods=['GET'])
def get_user_language():
    """Get user's language preference"""
    try:
        # Check if user is authenticated
        if 'user_id' in session:
            user_id = session['user_id']
            user = db.session.get(User, user_id)

            # FIXED: Use correct column name 'preferred_language'
            if user and hasattr(user, 'preferred_language') and user.preferred_language:
                return jsonify({
                    'success': True,
                    'language': user.preferred_language
                }), 200

        # Check session for unauthenticated users
        # FIXED: Check both old and new session keys for backwards compatibility
        session_lang = session.get('preferred_language') or session.get('language')
        if session_lang:
            return jsonify({
                'success': True,
                'language': session_lang
            }), 200

        # Default to English
        return jsonify({
            'success': True,
            'language': 'en'
        }), 200

    except Exception as e:
        logger.error(f"Error getting language preference: {e}")
        return jsonify({
            'success': True,  # Don't fail hard on language errors
            'language': 'en'
        }), 200


@app.route('/api/admin/migrate-language', methods=['POST'])
def migrate_language_column():
    """
    Migration endpoint to copy 'language' to 'preferred_language' if needed
    Only accessible to admins or in development
    """
    # Add authentication check here if needed

    try:
        # Check if old 'language' column exists
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        user_columns = [col['name'] for col in inspector.get_columns('user')]

        if 'language' in user_columns:
            # Migrate data from 'language' to 'preferred_language'
            users = User.query.filter(User.language.isnot(None)).all()
            count = 0
            for user in users:
                if hasattr(user, 'language') and user.language:
                    user.preferred_language = user.language
                    count += 1

            db.session.commit()
            return jsonify({
                'success': True,
                'message': f'Migrated {count} users'
            }), 200
        else:
            return jsonify({
                'success': True,
                'message': 'No migration needed - language column does not exist'
            }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Migration error: {e}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@app.route('/api/profile', methods=['GET', 'PUT'])
@login_required
def profile():
    """Get or update user profile"""
    user_id = session.get('user_id')

    if request.method == 'GET':
        profile = db.session.execute(
            select(Profile).filter_by(user_id=user_id)
        ).scalar_one_or_none()

        if not profile:
            profile = Profile(user_id=user_id)
            db.session.add(profile)
            db.session.commit()

        # FIXED: Get username from User table to return in response
        user = db.session.execute(
            select(User).filter_by(id=user_id)
        ).scalar_one_or_none()

        return jsonify({
            'username': user.username if user else '',  # FIXED: Added username field
            'bio': profile.bio or '',
            'interests': profile.interests or '',
            'occupation': profile.occupation or '',
            'goals': profile.goals or '',
            'favorite_hobbies': profile.favorite_hobbies or '',
            'mood_status': profile.mood_status or '',
            'avatar_url': profile.avatar_url or ''
        })

    elif request.method == 'PUT':
        data = request.json
        profile = db.session.execute(
            select(Profile).filter_by(user_id=user_id)
        ).scalar_one_or_none()

        if not profile:
            profile = Profile(user_id=user_id)
            db.session.add(profile)

        # Update fields
        if 'bio' in data:
            profile.bio = sanitize_input(data.get('bio', ''))[:1000]
        if 'interests' in data:
            profile.interests = sanitize_input(data.get('interests', ''))
        if 'occupation' in data:
            profile.occupation = sanitize_input(data.get('occupation', ''))
        if 'goals' in data:
            profile.goals = sanitize_input(data.get('goals', ''))
        if 'favorite_hobbies' in data:
            profile.favorite_hobbies = sanitize_input(data.get('favorite_hobbies', ''))
        if 'mood_status' in data:
            profile.mood_status = sanitize_input(data.get('mood_status', ''))[:50]
        if 'avatar_url' in data:
            profile.avatar_url = data.get('avatar_url', '')[:500]

        profile.updated_at = datetime.utcnow()

        # Update user's preferred language if provided
        if 'preferred_language' in data:
            user = db.session.get(User, user_id)
            if user and data['preferred_language'] in ['en', 'he', 'ar', 'ru']:
                user.preferred_language = data['preferred_language']

        db.session.commit()
        return jsonify({'success': True, 'message': 'Profile updated'})


@app.route('/api/users/<int:user_id>/profile', methods=['GET'])
@login_required
def get_user_profile(user_id):
    """Get another user's profile"""
    try:
        current_user_id = session.get('user_id')

        # Check if following this user
        is_following = Follow.query.filter_by(
            follower_id=current_user_id,
            followed_id=user_id
        ).first() is not None

        if not is_following and user_id != current_user_id:
            return jsonify({'error': 'Must be following user to view profile'}), 403

        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        # Get profile data if it exists
        profile = user.profile if user.profile else None

        return jsonify({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'city': user.selected_city or '',
            'bio': profile.bio if profile else '',
            'avatar_url': profile.avatar_url if profile else '',
            'occupation': profile.occupation if profile else '',
            'interests': profile.interests if profile else '',
            'goals': profile.goals if profile else '',
            'favorite_hobbies': profile.favorite_hobbies if profile else '',
            'created_at': user.created_at.isoformat() if user.created_at else None
        })
    except Exception as e:
        logger.error(f"Error loading user profile {user_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/users/<int:user_id>/posts', methods=['GET'])
@login_required
def get_user_posts(user_id):
    """Get another user's feed posts with circle-based visibility"""
    try:
        current_user_id = session.get('user_id')

        # Check if following this user
        is_following = Follow.query.filter_by(
            follower_id=current_user_id,
            followed_id=user_id
        ).first() is not None

        if not is_following and user_id != current_user_id:
            return jsonify({'error': 'Must be following user to view posts'}), 403

        # If viewing own posts, return all
        if user_id == current_user_id:
            posts = Post.query.filter_by(user_id=user_id).order_by(Post.created_at.desc()).all()

            # Calculate likes and comments for each post
            posts_data = []
            for post in posts:
                # Count likes from Reaction table
                likes_count = db.session.execute(
                    select(func.count(Reaction.id)).filter_by(post_id=post.id, type='like')
                ).scalar() or 0

                # Count comments
                comments_count = db.session.execute(
                    select(func.count(Comment.id)).filter_by(post_id=post.id)
                ).scalar() or 0

                # Check if current user liked this post
                user_liked = db.session.execute(
                    select(Reaction).filter_by(
                        post_id=post.id,
                        user_id=current_user_id,
                        type='like'
                    )
                ).scalar_one_or_none() is not None

                posts_data.append({
                    'id': post.id,
                    'content': post.content,
                    'created_at': post.created_at.isoformat() if post.created_at else None,
                    'likes_count': likes_count,
                    'comments_count': comments_count,
                    'user_liked': user_liked,
                    'circle_id': post.circle_id,
                    'visibility': post.visibility
                })

            return jsonify({'posts': posts_data})

        # Check circle membership for viewing other users' posts
        membership = Circle.query.filter_by(
            user_id=user_id,
            circle_user_id=current_user_id
        ).first()

        # Determine which circle IDs current user can see (hierarchical)
        visible_circle_ids = [1]  # Everyone can see general/public (circle_id=1)
        if membership:
            if membership.circle_type in ['class_a', 'family']:
                # Class A members can see public (1), class_b (2), and class_a (3)
                visible_circle_ids = [1, 2, 3]
            elif membership.circle_type in ['class_b', 'close_friends']:
                # Class B members can see public (1) and class_b (2)
                visible_circle_ids = [1, 2]

        # Get posts filtered by visible circles
        posts = Post.query.filter(
            Post.user_id == user_id,
            Post.circle_id.in_(visible_circle_ids)
        ).order_by(Post.created_at.desc()).all()

        # Calculate likes and comments for each post
        posts_data = []
        for post in posts:
            # Count likes from Reaction table
            likes_count = db.session.execute(
                select(func.count(Reaction.id)).filter_by(post_id=post.id, type='like')
            ).scalar() or 0

            # Count comments
            comments_count = db.session.execute(
                select(func.count(Comment.id)).filter_by(post_id=post.id)
            ).scalar() or 0

            # Check if current user liked this post
            user_liked = db.session.execute(
                select(Reaction).filter_by(
                    post_id=post.id,
                    user_id=current_user_id,
                    type='like'
                )
            ).scalar_one_or_none() is not None

            posts_data.append({
                'id': post.id,
                'content': post.content,
                'created_at': post.created_at.isoformat() if post.created_at else None,
                'likes_count': likes_count,
                'comments_count': comments_count,
                'user_liked': user_liked,
                'circle_id': post.circle_id,
                'visibility': post.visibility
            })

        return jsonify({'posts': posts_data})

    except Exception as e:
        logger.error(f"Error getting user posts: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/users/<int:user_id>/circles', methods=['GET'])
@login_required
def get_user_circles(user_id):
    """Get another user's circles (read-only) - returns members in each circle"""
    try:
        current_user_id = session.get('user_id')

        # Check if following this user
        is_following = Follow.query.filter_by(
            follower_id=current_user_id,
            followed_id=user_id
        ).first() is not None

        if not is_following and user_id != current_user_id:
            return jsonify({'error': 'Must be following user to view circles'}), 403

        # Initialize viewer_circle_type
        viewer_circle_type = None
        user_privacy_level = None

        # Check circles privacy settings if viewing another user's circles
        if user_id != current_user_id:
            target_user = db.session.get(User, user_id)
            if not target_user:
                return jsonify({'error': 'User not found'}), 404

            privacy_level = target_user.circles_privacy or 'private'
            user_privacy_level = privacy_level  # Store for return

            # Check viewer's circle membership with target user
            viewer_circle = db.session.execute(
                select(Circle).filter_by(
                    user_id=user_id,
                    circle_user_id=current_user_id
                )
            ).scalars().first()

            if viewer_circle:
                type_mapping_check = {
                    'general': 'public',
                    'close_friends': 'class_b',
                    'family': 'class_a',
                    'public': 'public',
                    'class_b': 'class_b',
                    'class_a': 'class_a'
                }
                viewer_circle_type = type_mapping_check.get(viewer_circle.circle_type, 'public')

            # Apply privacy filtering - return with user_privacy field
            if privacy_level == 'private':
                return jsonify({
                    'private': True,
                    'message': 'Circles set to private',
                    'public': [],
                    'class_b': [],
                    'class_a': [],
                    'can_view': {'public': False, 'class_b': False, 'class_a': False},
                    'viewer_circle_type': viewer_circle_type,
                    'user_privacy': privacy_level  # ADDED
                })

            if privacy_level == 'class_a' and viewer_circle_type != 'class_a':
                return jsonify({
                    'private': True,
                    'message': 'Circles set to private',
                    'public': [],
                    'class_b': [],
                    'class_a': [],
                    'can_view': {'public': False, 'class_b': False, 'class_a': False},
                    'viewer_circle_type': viewer_circle_type,
                    'user_privacy': privacy_level  # ADDED
                })

            if privacy_level == 'class_b' and viewer_circle_type not in ['class_a', 'class_b']:
                return jsonify({
                    'private': True,
                    'message': 'Circles set to private',
                    'public': [],
                    'class_b': [],
                    'class_a': [],
                    'can_view': {'public': False, 'class_b': False, 'class_a': False},
                    'viewer_circle_type': viewer_circle_type,
                    'user_privacy': privacy_level  # ADDED
                })

        # Get all circles for this user
        circles_stmt = select(Circle).filter_by(user_id=user_id)
        circles = db.session.execute(circles_stmt).scalars().all()

        # Organize by circle type
        result = {
            'public': [],
            'class_b': [],
            'class_a': []
        }

        type_mapping = {
            'public': 'public',
            'general': 'public',
            'class_b': 'class_b',
            'close_friends': 'class_b',
            'class_a': 'class_a',
            'family': 'class_a'
        }

        for circle in circles:
            # Get the user info for the circle member
            member_user = db.session.get(User, circle.circle_user_id)
            if member_user:
                user_info = {
                    'id': member_user.id,
                    'username': member_user.username,
                    'email': member_user.email
                }

                # Map to normalized circle type
                circle_type = type_mapping.get(circle.circle_type, circle.circle_type)
                if circle_type in result:
                    result[circle_type].append(user_info)

        # Add permission flags for frontend
        can_view = {
            'public': True,
            'class_b': True,
            'class_a': True
        }

        result['can_view'] = can_view
        result['viewer_circle_type'] = viewer_circle_type
        result['user_privacy'] = user_privacy_level  # ADDED

        return jsonify(result)

    except Exception as e:
        logger.error(f"Get user circles error: {str(e)}")
        return jsonify({'error': 'Failed to get circles'}), 500


@app.route('/api/users/<int:user_id>/parameters', methods=['GET'])
@login_required
def get_user_parameters(user_id):
    """Get another user's wellness parameters with circle-based privacy"""
    try:
        current_user_id = session.get('user_id')

        # Check if following this user
        is_following = Follow.query.filter_by(
            follower_id=current_user_id,
            followed_id=user_id
        ).first() is not None

        if not is_following and user_id != current_user_id:
            return jsonify({'error': 'Must be following user to view parameters'}), 403

        # Get date range from query params (REQUIRED)
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        if not start_date or not end_date:
            return jsonify({'error': 'start_date and end_date are required'}), 400

        # Parse dates
        try:
            start = parse_date_as_local(start_date)
            end = parse_date_as_local(end_date)
        except ValueError:
            return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400

        # Check what circle the current user is in for the target user
        circle_level = 'public'  # Default to public
        if current_user_id != user_id:
            circle_stmt = select(Circle).filter_by(
                user_id=user_id,
                circle_user_id=current_user_id
            )
            circle = db.session.execute(circle_stmt).scalar_one_or_none()

            if circle:
                # Map circle types to privacy levels
                type_mapping = {
                    'public': 'public',
                    'general': 'public',
                    'class_b': 'class_b',
                    'close_friends': 'class_b',
                    'class_a': 'class_a',
                    'family': 'class_a'
                }
                circle_level = type_mapping.get(circle.circle_type, 'public')
        else:
            # User viewing their own parameters - full access
            circle_level = 'class_a'

        # Get parameters with privacy settings
        query = text("""
            SELECT p.date, p.mood, p.energy, p.sleep_quality, 
                   p.physical_activity, p.anxiety, p.notes,
                   p.mood_privacy, p.energy_privacy, p.sleep_quality_privacy,
                   p.physical_activity_privacy, p.anxiety_privacy
            FROM saved_parameters p
            WHERE p.user_id = :user_id
              AND p.date >= :start_date 
              AND p.date <= :end_date
            ORDER BY p.date ASC
        """)

        result_proxy = db.session.execute(
            query,
            {
                'user_id': user_id,
                'start_date': start.isoformat(),
                'end_date': end.isoformat()
            }
        )

        parameters = result_proxy.fetchall()

        # Build result array with privacy filtering
        result = []
        for row in parameters:
            param_dict = {
                'date': row[0].isoformat() if hasattr(row[0], 'isoformat') else str(row[0])
            }

            # Check privacy for each parameter
            # mood
            mood_privacy = row[7] or 'public'
            if check_param_visibility(mood_privacy, circle_level):
                param_dict['mood'] = row[1]
            else:
                param_dict['mood'] = None

            # energy
            energy_privacy = row[8] or 'public'
            if check_param_visibility(energy_privacy, circle_level):
                param_dict['energy'] = row[2]
            else:
                param_dict['energy'] = None

            # sleep_quality
            sleep_privacy = row[9] or 'public'
            if check_param_visibility(sleep_privacy, circle_level):
                param_dict['sleep_quality'] = row[3]
            else:
                param_dict['sleep_quality'] = None

            # physical_activity
            activity_privacy = row[10] or 'public'
            if check_param_visibility(activity_privacy, circle_level):
                param_dict['physical_activity'] = row[4]
            else:
                param_dict['physical_activity'] = None

            # anxiety
            anxiety_privacy = row[11] or 'public'
            if check_param_visibility(anxiety_privacy, circle_level):
                param_dict['anxiety'] = row[5]
            else:
                param_dict['anxiety'] = None

            # Notes are always private unless user is in class_a
            if circle_level == 'class_a':
                param_dict['notes'] = row[6]
            else:
                param_dict['notes'] = None

            result.append(param_dict)

        return jsonify(result), 200

    except Exception as e:
        app.logger.error(f"Error loading user parameters: {str(e)}")
        return jsonify({'error': 'Failed to load parameters'}), 500


def check_param_visibility(param_privacy, viewer_circle_level):
    """Helper function to check if a parameter should be visible based on privacy and viewer's circle"""
    if param_privacy == 'public':
        return True
    elif param_privacy == 'class_b':
        return viewer_circle_level in ['class_b', 'class_a']
    elif param_privacy == 'class_a':
        return viewer_circle_level == 'class_a'
    return False


@app.route('/api/debug/parameters/<int:user_id>')
@login_required
def debug_parameters(user_id):
    """Temporary debug endpoint - DELETE after fixing"""
    try:
        # Get ALL parameters for this user (no date filter)
        query = text("""
            SELECT date, mood, energy, sleep_quality, 
                   physical_activity, anxiety, notes, user_id
            FROM saved_parameters
            WHERE user_id = :user_id
            ORDER BY date DESC
            LIMIT 10
        """)

        result = db.session.execute(query, {'user_id': user_id})
        rows = result.fetchall()

        parameters = []
        for row in rows:
            parameters.append({
                'date': str(row[0]),  # Convert to string to see exact format
                'date_type': type(row[0]).__name__,
                'mood': row[1],
                'energy': row[2],
                'sleep_quality': row[3],
                'physical_activity': row[4],
                'anxiety': row[5],
                'notes': row[6],
                'user_id': row[7]
            })

        return jsonify({
            'count': len(parameters),
            'data': parameters
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/users/search')
@login_required
def search_users():
    """Search for users by username or email"""
    try:
        # Get and validate query
        query = request.args.get('q', '').strip().lower()
        logger.info(f"🔍 Search request: query='{query}'")

        if not query or len(query) < 2:
            logger.info(f"❌ Query too short: length={len(query)}")
            return jsonify({'users': []})

        # Get current user
        current_user_id = session.get('user_id')
        if not current_user_id:
            logger.error("❌ No user_id in session")
            return jsonify({'error': 'Not authenticated'}), 401

        logger.info(f"👤 Current user: {current_user_id}")

        # Perform search
        logger.info(f"🔎 Searching: username ILIKE '%{query}%' WHERE id != {current_user_id}")

        users = User.query.filter(
            User.id != current_user_id,
            User.username.ilike(f'%{query}%')
        ).limit(10).all()

        logger.info(f"✓ Found {len(users)} user(s): {[u.username for u in users]}")

        # Format results with profile data
        results = []
        for user in users:
            try:
                profile = Profile.query.filter_by(user_id=user.id).first()

                user_data = {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'display_name': user.username,
                    'bio': profile.bio if profile else None,
                    'occupation': profile.occupation if profile else None,
                    'interests': profile.interests if profile else None,
                    'avatar_url': profile.avatar_url if profile else None
                }

                results.append(user_data)
                logger.debug(f"  - Formatted user {user.id}: {user.username}")

            except Exception as profile_error:
                # Include user even if profile loading fails
                logger.warning(f"⚠️  Profile error for user {user.id}: {profile_error}")
                results.append({
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'display_name': user.username,
                    'bio': None,
                    'occupation': None,
                    'interests': None,
                    'avatar_url': None
                })

        logger.info(f"📤 Returning {len(results)} result(s)")
        return jsonify({'users': results})

    except Exception as e:
        logger.error(f"❌ Search failed: {type(e).__name__}: {e}", exc_info=True)
        logger.error(f"   Query: '{request.args.get('q', '')}'")
        logger.error(f"   Session: {dict(session)}")
        return jsonify({'users': [], 'error': 'Search failed'}), 500


# =====================
# ALERTS ROUTES
# =====================

@app.route('/api/alerts', methods=['GET'])
@login_required
def get_alerts():
    """Get user alerts"""
    try:
        user_id = session['user_id']

        # SQLAlchemy 2.0 style
        alerts_stmt = select(Alert).filter_by(
            user_id=user_id,
            is_read=False
        ).order_by(desc(Alert.created_at)).limit(50)

        alerts = db.session.execute(alerts_stmt).scalars().all()

        return jsonify({
            'alerts': [alert.to_dict() for alert in alerts],
            'unread_count': len(alerts)
        })

    except Exception as e:
        logger.error(f"Get alerts error: {str(e)}")
        return jsonify({'error': 'Failed to get alerts'}), 500


@app.route('/api/alerts/<int:alert_id>/read', methods=['PUT'])
@login_required
def mark_alert_read(alert_id):
    """Mark alert as read"""
    try:
        alert = db.session.get(Alert, alert_id)
        if alert and alert.user_id == session['user_id']:
            alert.is_read = True
            db.session.commit()
            return jsonify({'success': True})
        return jsonify({'error': 'Alert not found'}), 404
    except Exception as e:
        logger.error(f"Mark alert error: {str(e)}")
        return jsonify({'error': 'Failed to mark alert'}), 500


# =====================
# MESSAGES ROUTES
# =====================

@app.route('/api/messages', methods=['GET', 'POST'])
@login_required
def messages():
    """Get or send messages"""
    user_id = session.get('user_id')

    if request.method == 'GET':
        try:
            recipient_id = request.args.get('recipient_id', type=int)

            if recipient_id:
                # Get messages for specific conversation
                messages_stmt = select(Message).filter(
                    or_(
                        and_(Message.sender_id == user_id, Message.recipient_id == recipient_id),
                        and_(Message.sender_id == recipient_id, Message.recipient_id == user_id)
                    )
                ).order_by(Message.created_at)  # Chronological order for conversation view

                messages = db.session.execute(messages_stmt).scalars().all()

                def format_message(msg):
                    try:
                        sender = db.session.get(User, msg.sender_id)
                        recipient = db.session.get(User, msg.recipient_id)

                        # Ensure both users exist and have usernames
                        if not sender or not recipient:
                            logger.warning(f"Missing user data for message {msg.id}")
                            return None

                        return {
                            'id': msg.id,
                            'sender': {
                                'id': sender.id if sender else msg.sender_id,
                                'username': sender.username if sender else 'Unknown User'
                            },
                            'recipient': {
                                'id': recipient.id if recipient else msg.recipient_id,
                                'username': recipient.username if recipient else 'Unknown User'
                            },
                            'content': msg.content or '',
                            'is_read': msg.is_read,
                            'created_at': msg.created_at.isoformat() if msg.created_at else datetime.utcnow().isoformat()
                        }
                    except Exception as e:
                        logger.error(f"Error formatting message {msg.id}: {str(e)}")
                        return None

                formatted_messages = [m for msg in messages if (m := format_message(msg)) is not None]
                return jsonify({'messages': formatted_messages})

            else:
                # Get all messages for overview
                sent_stmt = select(Message).filter_by(sender_id=user_id).order_by(desc(Message.created_at)).limit(50)
                sent = db.session.execute(sent_stmt).scalars().all()

                received_stmt = select(Message).filter_by(recipient_id=user_id).order_by(
                    desc(Message.created_at)).limit(50)
                received = db.session.execute(received_stmt).scalars().all()

                def format_message(msg):
                    try:
                        sender = db.session.get(User, msg.sender_id)
                        recipient = db.session.get(User, msg.recipient_id)

                        if not sender or not recipient:
                            logger.warning(f"Missing user data for message {msg.id}")
                            return None

                        return {
                            'id': msg.id,
                            'sender': {
                                'id': sender.id if sender else msg.sender_id,
                                'username': sender.username if sender else 'Unknown User'
                            },
                            'recipient': {
                                'id': recipient.id if recipient else msg.recipient_id,
                                'username': recipient.username if recipient else 'Unknown User'
                            },
                            'content': msg.content or '',
                            'is_read': msg.is_read,
                            'created_at': msg.created_at.isoformat() if msg.created_at else datetime.utcnow().isoformat()
                        }
                    except Exception as e:
                        logger.error(f"Error formatting message {msg.id}: {str(e)}")
                        return None

                return jsonify({
                    'sent': [m for msg in sent if (m := format_message(msg)) is not None],
                    'received': [m for msg in received if (m := format_message(msg)) is not None]
                })

        except Exception as e:
            logger.error(f"Get messages error: {str(e)}")
            return jsonify({'error': 'Failed to get messages'}), 500

    elif request.method == 'POST':
        try:
            data = request.json
            recipient_id = data.get('recipient_id')
            content = data.get('content', '').strip()

            if not recipient_id or not content:
                return jsonify({'error': 'Missing recipient or content'}), 400

            # Check if recipient exists
            recipient = db.session.get(User, recipient_id)
            if not recipient:
                return jsonify({'error': 'Recipient not found'}), 404

            # Check content
            moderation = content_moderator.check_content(content)
            if not moderation['safe']:
                return jsonify({'error': moderation.get('message', 'Content not allowed')}), 400

            # Create message
            message = Message(
                sender_id=user_id,
                recipient_id=recipient_id,
                content=sanitize_input(content)
            )
            db.session.add(message)

            # Create alert for recipient - FIX 7: Safe sender name retrieval
            try:
                sender = db.session.get(User, user_id)
                sender_name = sender.username if sender and sender.username else 'Someone'
            except Exception as e:
                logger.error(f"Error getting sender username: {str(e)}")
                sender_name = 'Someone'

            alert = Alert(
                user_id=recipient_id,
                title=json.dumps({
                    'key': 'alerts.new_message_from',
                    'params': {'username': sender_name}
                }),
                content=content[:100] + '...' if len(content) > 100 else content,
                alert_type='info'
            )
            db.session.add(alert)

            # Update activity for today
            today = datetime.utcnow().date()
            activity_stmt = select(Activity).filter_by(user_id=user_id, activity_date=today)
            activity = db.session.execute(activity_stmt).scalar_one_or_none()

            if not activity:
                activity = Activity(user_id=user_id, activity_date=today)
                db.session.add(activity)

            activity.message_count = (activity.message_count or 0) + 1

            db.session.commit()

            return jsonify({'success': True, 'message_id': message.id})

        except Exception as e:
            logger.error(f"Send message error: {str(e)}")
            db.session.rollback()
            return jsonify({'error': 'Failed to send message'}), 500


@app.route('/api/messages/read/<int:recipient_id>', methods=['POST'])
@login_required
def mark_messages_read(recipient_id):
    """Mark all messages from a recipient as read"""
    try:
        user_id = session.get('user_id')

        # Mark all unread messages from this sender as read
        unread_messages = Message.query.filter_by(
            sender_id=recipient_id,
            recipient_id=user_id,
            is_read=False
        ).all()

        for message in unread_messages:
            message.is_read = True

        db.session.commit()

        return jsonify({'success': True, 'marked_count': len(unread_messages)})
    except Exception as e:
        logger.error(f"Mark messages error: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Failed to mark messages'}), 500


@app.route('/api/messages/conversations')
@login_required
def get_conversations():
    """Get conversation list with improved functionality"""
    try:
        user_id = session['user_id']

        # Get unique conversation partners - SQLAlchemy 2.0 style
        sent_stmt = select(Message.recipient_id).filter_by(sender_id=user_id).distinct()
        sent_partners = db.session.execute(sent_stmt).scalars().all()

        received_stmt = select(Message.sender_id).filter_by(recipient_id=user_id).distinct()
        received_partners = db.session.execute(received_stmt).scalars().all()

        # Combine and deduplicate
        partner_ids = set(sent_partners + received_partners)

        conversations = []
        for partner_id in partner_ids:
            try:
                partner = db.session.get(User, partner_id)

                # Skip if partner doesn't exist or has no username
                if not partner or not partner.username:
                    logger.warning(f"Skipping conversation with invalid partner {partner_id}")
                    continue

                # Get last message - SQLAlchemy 2.0 style
                last_msg_stmt = select(Message).filter(
                    or_(
                        and_(Message.sender_id == user_id, Message.recipient_id == partner_id),
                        and_(Message.sender_id == partner_id, Message.recipient_id == user_id)
                    )
                ).order_by(desc(Message.created_at))

                last_message = db.session.execute(last_msg_stmt).scalars().first()

                # Count unread messages from this partner
                unread_stmt = select(func.count(Message.id)).filter_by(
                    sender_id=partner_id,
                    recipient_id=user_id,
                    is_read=False
                )
                unread_count = db.session.execute(unread_stmt).scalar() or 0

                # Ensure all fields have safe fallback values
                conversations.append({
                    'user': {
                        'id': partner.id,
                        'username': partner.username or 'Unknown User'
                    },
                    'last_message': {
                        'content': last_message.content if last_message and last_message.content else '',
                        'created_at': last_message.created_at.isoformat() if last_message and last_message.created_at else None,
                        'is_own': last_message.sender_id == user_id if last_message else False
                    },
                    'unread_count': unread_count,
                    'timestamp': last_message.created_at.isoformat() if last_message and last_message.created_at else None
                })
            except Exception as e:
                logger.error(f"Error processing conversation with partner {partner_id}: {str(e)}")
                continue

        # Sort by last message time
        conversations.sort(
            key=lambda x: x['timestamp'] if x['timestamp'] else '',
            reverse=True
        )

        # ✅ FIXED: Wrap in object for frontend consistency
        return jsonify({'conversations': conversations})

    except Exception as e:
        logger.error(f"Get conversations error: {str(e)}")
        return jsonify({'conversations': []})  # Return empty array on error instead of error object


# =====================
# CIRCLES ROUTES
# =====================
@app.route('/api/circles', methods=['GET', 'POST'])
@login_required
def circles():
    """Manage user circles"""
    user_id = session.get('user_id')

    if request.method == 'GET':
        try:
            # NEW: Support viewing another user's circles
            viewing_user_id = request.args.get('user_id', type=int)

            # If no user_id specified, show logged-in user's circles
            target_user_id = viewing_user_id if viewing_user_id else user_id
            is_viewing_own = (target_user_id == user_id)

            # Get target user
            target_user = db.session.get(User, target_user_id)
            if not target_user:
                return jsonify({'error': 'User not found'}), 404

            circles_privacy = getattr(target_user, 'circles_privacy', 'public')

            logger.info(
                f"User {user_id} viewing circles of user {target_user_id} (privacy: {circles_privacy}, is_own: {is_viewing_own})")

            # If viewing someone else's circles, check follow status
            if not is_viewing_own:
                is_following = db.session.execute(
                    select(Follow).filter_by(
                        follower_id=user_id,
                        followed_id=target_user_id
                    )
                ).scalar_one_or_none()

                if not is_following:
                    return jsonify({'error': 'Must be following user to view circles'}), 403

                # If circles are private AND viewing someone else's, return empty
                if circles_privacy == 'private':
                    return jsonify({
                        'public': [],
                        'class_b': [],
                        'class_a': [],
                        'private': True
                    })

                # Determine viewer's circle level for this user
                viewer_circle_stmt = select(Circle).filter(
                    Circle.user_id == target_user_id,
                    Circle.circle_user_id == user_id
                )
                viewer_circle = db.session.execute(viewer_circle_stmt).scalar_one_or_none()

                if viewer_circle:
                    # Map to standardized circle type
                    type_mapping = {
                        'public': 'public',
                        'general': 'public',
                        'class_b': 'class_b',
                        'close_friends': 'class_b',
                        'class_a': 'class_a',
                        'family': 'class_a'
                    }
                    viewer_circle_level = type_mapping.get(viewer_circle.circle_type, 'public')
                else:
                    # Not in any circle, default to public
                    viewer_circle_level = 'public'

                logger.info(f"Viewer {user_id} is in '{viewer_circle_level}' circle for user {target_user_id}")
            else:
                viewer_circle_level = None  # Not used when viewing own

            # Get all circles - SQLAlchemy 2.0 style
            # Filter out circles with NULL circle_user_id to prevent SAWarning
            # Support both old and new naming conventions
            public_stmt = select(Circle).filter(
                Circle.user_id == target_user_id,
                Circle.circle_user_id.isnot(None),
                or_(Circle.circle_type == 'public', Circle.circle_type == 'general')
            )
            public = db.session.execute(public_stmt).scalars().all()

            class_b_stmt = select(Circle).filter(
                Circle.user_id == target_user_id,
                Circle.circle_user_id.isnot(None),
                or_(Circle.circle_type == 'class_b', Circle.circle_type == 'close_friends')
            )
            class_b = db.session.execute(class_b_stmt).scalars().all()

            class_a_stmt = select(Circle).filter(
                Circle.user_id == target_user_id,
                Circle.circle_user_id.isnot(None),
                or_(Circle.circle_type == 'class_a', Circle.circle_type == 'family')
            )
            class_a = db.session.execute(class_a_stmt).scalars().all()

            def get_user_info(circle):
                """Safely get user info, handling None/NULL circle_user_id"""
                if not circle.circle_user_id:
                    logger.warning(f"Circle {circle.id} has NULL circle_user_id for user {target_user_id}")
                    return None

                user = db.session.get(User, circle.circle_user_id)
                if user:
                    return {
                        'id': user.id,
                        'username': user.username,
                        'email': user.email,
                        'display_name': user.username
                    }
                logger.warning(f"User {circle.circle_user_id} not found for circle {circle.id}")
                return None

            # Apply privacy filtering based on circles_privacy AND viewer's circle level
            result = {
                'public': [],
                'class_b': [],
                'class_a': []
            }

            if is_viewing_own:
                # ✅ OWNER ALWAYS SEES ALL THEIR CIRCLES (regardless of privacy setting)
                result['public'] = [info for c in public if (info := get_user_info(c))]
                result['class_b'] = [info for c in class_b if (info := get_user_info(c))]
                result['class_a'] = [info for c in class_a if (info := get_user_info(c))]
            else:
                # ✅ VIEWING SOMEONE ELSE'S CIRCLES - Apply privacy rules

                if circles_privacy == 'private':
                    # Nobody sees anything (already returned earlier, but just in case)
                    result['private'] = True

                elif circles_privacy == 'public':
                    # Everyone sees all circles
                    result['public'] = [info for c in public if (info := get_user_info(c))]
                    result['class_b'] = [info for c in class_b if (info := get_user_info(c))]
                    result['class_a'] = [info for c in class_a if (info := get_user_info(c))]

                elif circles_privacy == 'class_b':
                    # Only Class B and Class A members can see
                    if viewer_circle_level in ['class_b', 'class_a']:
                        result['class_b'] = [info for c in class_b if (info := get_user_info(c))]
                        result['class_a'] = [info for c in class_a if (info := get_user_info(c))]
                        result['public'] = [info for c in public if (info := get_user_info(c))]
                    else:
                        # viewer is only in public circle, can't see anything
                        result['private'] = True

                elif circles_privacy == 'class_a':
                    # Only Class A members can see
                    if viewer_circle_level == 'class_a':
                        result['class_a'] = [info for c in class_a if (info := get_user_info(c))]
                        result['public'] = [info for c in public if (info := get_user_info(c))]
                        result['class_b'] = [info for c in class_b if (info := get_user_info(c))]
                    else:
                        # viewer is not in class_a, can't see anything
                        result['private'] = True

            return jsonify(result)

        except Exception as e:
            logger.error(f"Get circles error: {str(e)}")
            return jsonify({'error': 'Failed to get circles'}), 500

    elif request.method == 'POST':
        try:
            data = request.json
            circle_user_id = data.get('user_id')
            circle_type = data.get('circle_type')

            valid_types = ['public', 'class_b', 'class_a', 'general', 'close_friends', 'family']
            # Map old names to new names
            type_mapping = {
                'general': 'public',
                'close_friends': 'class_b',
                'family': 'class_a',
                'public': 'public',
                'class_b': 'class_b',
                'class_a': 'class_a'
            }
            circle_type = type_mapping.get(circle_type, circle_type)

            if circle_type not in ['public', 'class_b', 'class_a']:
                return jsonify({'error': 'Invalid circle type'}), 400

            # Check if user exists
            if not db.session.get(User, circle_user_id):
                return jsonify({'error': 'User not found'}), 404

            # Check if already in circle - SQLAlchemy 2.0 style
            existing_stmt = select(Circle).filter_by(
                user_id=user_id,
                circle_user_id=circle_user_id,
                circle_type=circle_type
            )
            existing = db.session.execute(existing_stmt).scalar_one_or_none()

            if existing:
                return jsonify({'error': 'User already in this circle'}), 400

            circle = Circle(
                user_id=user_id,
                circle_user_id=circle_user_id,
                circle_type=circle_type
            )
            db.session.add(circle)
            db.session.commit()

            logger.info(f"Added user {circle_user_id} to {circle_type} circle for user {user_id}")
            return jsonify({'success': True, 'message': 'User added to circle'})

        except Exception as e:
            logger.error(f"Add to circle error: {str(e)}")
            db.session.rollback()
            return jsonify({'error': 'Failed to add to circle'}), 500


@app.route('/api/circles/remove', methods=['DELETE'])
@login_required
def remove_from_circle():
    """Remove user from circle"""
    try:
        user_id = session.get('user_id')
        data = request.json

        # Validate data exists
        if not data:
            logger.error("No data provided to remove_from_circle")
            return jsonify({'error': 'No data provided'}), 400

        circle_user_id = data.get('user_id')
        circle_type = data.get('circle_type')

        # Validate required fields
        if not circle_user_id or not circle_type:
            logger.error(f"Missing required fields: user_id={circle_user_id}, circle_type={circle_type}")
            return jsonify({'error': 'Missing required fields'}), 400

        logger.info(f"Removing user {circle_user_id} from circle {circle_type} for user {user_id}")

        # Map old names to new names AND create list of possible matches
        type_mapping = {
            'general': ['public', 'general'],  # Check both new and old
            'public': ['public', 'general'],
            'close_friends': ['class_b', 'close_friends'],
            'class_b': ['class_b', 'close_friends'],
            'family': ['class_a', 'family'],
            'class_a': ['class_a', 'family'],
            'private': ['private']  # Private only has one name
        }

        # Get list of possible type names to check
        possible_types = type_mapping.get(circle_type, [circle_type])

        logger.info(f"Checking for circle types: {possible_types}")

        # Use SQLAlchemy to delete - check for ANY of the possible type names
        stmt = select(Circle).filter(
            Circle.user_id == user_id,
            Circle.circle_user_id == circle_user_id,
            Circle.circle_type.in_(possible_types)  # Check BOTH old and new names
        )
        circle = db.session.execute(stmt).scalar_one_or_none()

        if circle:
            db.session.delete(circle)
            db.session.commit()
            logger.info(f"Successfully removed user {circle_user_id} from circle {circle.circle_type}")
            return jsonify({'success': True})
        else:
            logger.warning(f"No circle membership found for types {possible_types}")
            return jsonify({'error': 'Not found'}), 404

    except Exception as e:
        logger.error(f"Remove from circle error: {str(e)}", exc_info=True)
        db.session.rollback()
        return jsonify({'error': 'Failed to remove from circle'}), 500


def migrate_circle_names():
    """Migrate old circle names to new ones in the database"""
    try:
        # Map old names to new names
        name_mapping = {
            'general': 'public',
            'close_friends': 'class_b',
            'family': 'class_a'
        }

        migrated_count = 0

        # Get all circles with old names and update them
        for old_name, new_name in name_mapping.items():
            stmt = select(Circle).filter_by(circle_type=old_name)
            old_circles = db.session.execute(stmt).scalars().all()

            for circle in old_circles:
                logger.info(f"Migrating circle {circle.id} from '{old_name}' to '{new_name}'")
                circle.circle_type = new_name
                migrated_count += 1

        if migrated_count > 0:
            db.session.commit()
            app.logger.info(f"Circle names migration completed: {migrated_count} circles updated")
        else:
            app.logger.info("Circle names check completed - no migration needed")

    except Exception as e:
        app.logger.error(f"Error checking circle names: {e}")
        db.session.rollback()


@app.route('/api/circles/membership/<int:check_user_id>', methods=['GET'])
@login_required
def check_circle_membership(check_user_id):
    """Check what circle the current user is in for another user"""
    try:
        current_user_id = session.get('user_id')

        # Check if current user is in any of check_user's circles
        circle_stmt = select(Circle).filter_by(
            user_id=check_user_id,
            circle_user_id=current_user_id
        )
        circle = db.session.execute(circle_stmt).scalar_one_or_none()

        if circle:
            # Map old types to new if needed
            type_mapping = {
                'general': 'public',
                'close_friends': 'class_b',
                'family': 'class_a'
            }
            circle_type = type_mapping.get(circle.circle_type, circle.circle_type)
            return jsonify({'circle': circle_type})

        return jsonify({'circle': None})

    except Exception as e:
        logger.error(f"Check circle membership error: {str(e)}")
        return jsonify({'error': 'Failed to check membership'}), 500


def get_my_circles():
    """Get all circles with proper member information"""
    try:
        user_id = session.get('user_id')

        # Check if requesting user's own circles or someone else's
        target_user_id = request.args.get('user_id', user_id, type=int)

        # Initialize viewer_circle_type for later use
        viewer_circle_type = None

        # If viewing someone else's circles, check their privacy settings
        if target_user_id != user_id:
            target_user = db.session.get(User, target_user_id)
            if not target_user:
                return jsonify({'error': 'User not found'}), 404

            privacy_level = target_user.circles_privacy or 'private'

            # Check viewer's circle membership with target user FIRST (before any privacy checks)
            viewer_circle = db.session.execute(
                select(Circle).filter_by(
                    user_id=target_user_id,
                    circle_user_id=user_id
                )
            ).scalars().first()

            if viewer_circle:
                type_mapping = {
                    'general': 'public',
                    'close_friends': 'class_b',
                    'family': 'class_a',
                    'public': 'public',
                    'class_b': 'class_b',
                    'class_a': 'class_a'
                }
                viewer_circle_type = type_mapping.get(viewer_circle.circle_type, 'public')

            # Apply privacy filtering with consistent response format
            if privacy_level == 'private':
                return jsonify({
                    'private': True,
                    'message': 'Circles set to private',
                    'public': [],
                    'class_b': [],
                    'class_a': [],
                    'viewer_circle_type': viewer_circle_type,
                    'viewing_user_id': target_user_id
                })

            if privacy_level == 'class_a' and viewer_circle_type != 'class_a':
                return jsonify({
                    'private': True,
                    'message': 'Circles set to private',
                    'public': [],
                    'class_b': [],
                    'class_a': [],
                    'viewer_circle_type': viewer_circle_type,
                    'viewing_user_id': target_user_id
                })

            if privacy_level == 'class_b' and viewer_circle_type not in ['class_a', 'class_b']:
                return jsonify({
                    'private': True,
                    'message': 'Circles set to private',
                    'public': [],
                    'class_b': [],
                    'class_a': [],
                    'viewer_circle_type': viewer_circle_type,
                    'viewing_user_id': target_user_id
                })

            # For public or allowed viewers, continue with circles
            circles_stmt = select(Circle).filter_by(user_id=target_user_id)
        else:
            # User viewing own circles - no restrictions
            circles_stmt = select(Circle).filter_by(user_id=user_id)

        circles = db.session.execute(circles_stmt).scalars().all()

        result = {
            'public': [],
            'class_b': [],
            'class_a': []
        }

        type_mapping = {
            'general': 'public',
            'close_friends': 'class_b',
            'family': 'class_a',
            'public': 'public',
            'class_b': 'class_b',
            'class_a': 'class_a'
        }

        for circle in circles:
            user = db.session.get(User, circle.circle_user_id)
            if user:
                user_info = {
                    'user_id': user.id,
                    'username': user.username
                }
                circle_type = type_mapping.get(circle.circle_type, circle.circle_type)
                if circle_type in result:
                    result[circle_type].append(user_info)

        # If viewing another user's circles, include the viewer's circle type
        if target_user_id != user_id:
            result['viewer_circle_type'] = viewer_circle_type
            result['viewing_user_id'] = target_user_id

        return jsonify(result)

    except Exception as e:
        logger.error(f"Get my circles error: {str(e)}")
        return jsonify({'error': 'Failed to get circles'}), 500


@app.route('/api/circles/privacy', methods=['GET'])
@login_required
def get_circles_privacy():
    """Get user's circles privacy setting - supports querying other users"""
    try:
        current_user_id = session.get('user_id')
        # Allow checking another user's privacy setting via query parameter
        target_user_id = request.args.get('user_id', current_user_id, type=int)

        user = db.session.get(User, target_user_id)

        if not user:
            return jsonify({'error': 'User not found'}), 404

        return jsonify({
            'privacy': user.circles_privacy or 'private',
            'circles_privacy': user.circles_privacy or 'private'  # Keep both for backwards compatibility
        })
    except Exception as e:
        logger.error(f"Get circles privacy error: {str(e)}")
        return jsonify({'error': 'Failed to get circles privacy'}), 500


@app.route('/api/circles/privacy', methods=['POST'])
@login_required
def update_circles_privacy():
    """Update user's circles privacy setting"""
    try:
        user_id = session.get('user_id')
        data = request.get_json()

        # Accept either 'privacy_level', 'privacy', or 'circles_privacy' from frontend
        privacy_level = data.get('privacy_level') or data.get('privacy') or data.get('circles_privacy')

        # Validate privacy level
        if not privacy_level or privacy_level not in ['public', 'class_b', 'class_a', 'private']:
            logger.error(f"Invalid privacy level received: {privacy_level}, data: {data}")
            return jsonify({'error': 'Invalid privacy level'}), 400
        user = db.session.get(User, user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        user.circles_privacy = privacy_level
        db.session.commit()

        return jsonify({
            'message': 'Privacy updated successfully',
            'circles_privacy': privacy_level
        })

    except Exception as e:
        logger.error(f"Update circles privacy error: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Failed to update privacy'}), 500


# =====================
# FEED & POSTS ROUTES
# =====================

@app.route('/api/feed', methods=['GET'])
@login_required
@rate_limit_endpoint(max_requests=60, window=60)  # 60 requests per minute
def get_feed():
    """Get user feed with caching"""
    try:
        user_id = session['user_id']
        page = request.args.get('page', 1, type=int)

        # Try cache first
        cache_key = f'feed:{user_id}:{page}'
        if REDIS_URL:
            try:
                r = redis.from_url(REDIS_URL)
                cached_feed = r.get(cache_key)
                if cached_feed:
                    logger.debug(f'Cache hit for feed:{user_id}:{page}')
                    return jsonify(json.loads(cached_feed))
            except Exception as e:
                logger.warning(f'Cache read failed: {e}')

        # Get users in circles - SQLAlchemy 2.0 style
        circles_stmt = select(Circle).filter_by(user_id=user_id)
        circle_users = db.session.execute(circles_stmt).scalars().all()
        circle_user_ids = [c.circle_user_id for c in circle_users]
        circle_user_ids.append(user_id)  # Include own posts

        # Get posts - SQLAlchemy 2.0 style
        posts_stmt = select(Post).filter(
            Post.user_id.in_(circle_user_ids),
            Post.is_published == True
        ).order_by(desc(Post.created_at)).limit(50)

        posts = db.session.execute(posts_stmt).scalars().all()

        feed = []
        for post in posts:
            # Count reactions
            reactions_count = db.session.execute(
                select(func.count(Reaction.id)).filter_by(post_id=post.id)
            ).scalar() or 0

            # Count comments
            comments_count = db.session.execute(
                select(func.count(Comment.id)).filter_by(post_id=post.id)
            ).scalar() or 0

            feed.append({
                'id': post.id,
                'content': post.content,
                'author': post.author.username,
                'author_id': post.author.id,
                'likes': post.likes,
                'reactions_count': reactions_count,
                'comments_count': comments_count,
                'created_at': post.created_at.isoformat()
            })

        result = {'posts': feed}

        # Cache result for 5 minutes
        if REDIS_URL:
            try:
                r = redis.from_url(REDIS_URL)
                r.setex(cache_key, 300, json.dumps(result))
                logger.debug(f'Cached feed:{user_id}:{page}')
            except Exception as e:
                logger.warning(f'Cache write failed: {e}')

        return jsonify(result)

    except Exception as e:
        logger.error(f"Feed error: {str(e)}")
        return jsonify({'posts': []})


# Add these new endpoints right here, after get_feed() function ends


@app.route('/api/feed/hierarchical', methods=['GET'])
@login_required
def get_hierarchical_feed():
    """Get feed posts with visibility hierarchy applied"""
    try:
        user_id = session.get('user_id')
        page = request.args.get('page', 1, type=int)
        per_page = 20

        # Get all posts the user can see
        visible_posts = []

        # 1. User's own posts (all visible)
        own_posts = Post.query.filter_by(user_id=user_id, is_published=True).all()
        visible_posts.extend(own_posts)

        # 2. Check circles user belongs to for other users' posts
        # Get circles where current user is a member
        circles_in = db.session.execute(
            select(Circle).filter_by(circle_user_id=user_id)
        ).scalars().all()

        for circle in circles_in:
            # Get posts from this circle owner
            owner_posts = Post.query.filter_by(
                user_id=circle.user_id,
                is_published=True
            ).all()

            for post in owner_posts:
                # Apply hierarchy rules
                if post.visibility == 'public':
                    # Public posts visible to all circle members
                    if post not in visible_posts:
                        visible_posts.append(post)
                elif post.visibility == 'class_b':
                    # Class B posts visible to Class B and Class A members
                    if circle.circle_type in ['class_b', 'class_a']:
                        if post not in visible_posts:
                            visible_posts.append(post)
                elif post.visibility == 'class_a':
                    # Class A posts only visible to Class A members
                    if circle.circle_type == 'class_a':
                        if post not in visible_posts:
                            visible_posts.append(post)

        # Sort by created_at descending
        visible_posts.sort(key=lambda x: x.created_at, reverse=True)

        # Paginate
        start = (page - 1) * per_page
        end = start + per_page
        paginated_posts = visible_posts[start:end]

        # Format response
        posts_data = []
        for post in paginated_posts:
            author = db.session.get(User, post.user_id)
            posts_data.append({
                'id': post.id,
                'author': {
                    'id': author.id,
                    'username': author.username
                } if author else None,
                'content': post.content,
                'visibility': post.visibility,
                'created_at': post.created_at.isoformat(),
                'likes': post.likes,
                'comments_count': len(post.comments)
            })

        return jsonify({
            'posts': posts_data,
            'has_more': len(visible_posts) > end
        })

    except Exception as e:
        logger.error(f"Hierarchical feed error: {str(e)}")
        return jsonify({'error': 'Failed to load feed'}), 500


@app.route('/api/parameters/hierarchical/<int:view_user_id>', methods=['GET'])
@login_required
def get_hierarchical_parameters(view_user_id):
    """Get parameters with visibility hierarchy applied"""
    try:
        current_user_id = session.get('user_id')

        # If viewing own parameters, return all
        if view_user_id == current_user_id:
            params = SavedParameters.query.filter_by(user_id=view_user_id).all()
            return jsonify({
                'parameters': [p.to_dict(viewer_id=current_user_id) for p in params]
            })

        # Check what circle current user is in for the viewed user
        circle = Circle.query.filter_by(
            user_id=view_user_id,
            circle_user_id=current_user_id
        ).first()

        if not circle:
            # Not in any circle - can only see public
            privacy_level = 'public'
        else:
            privacy_level = circle.circle_type

        # Get parameters and apply visibility rules
        params = SavedParameters.query.filter_by(user_id=view_user_id).all()
        visible_params = []

        for param in params:
            param_dict = param.to_dict(viewer_id=current_user_id, privacy_level=privacy_level)
            visible_params.append(param_dict)

        return jsonify({'parameters': visible_params})

    except Exception as e:
        logger.error(f"Hierarchical parameters error: {str(e)}")
        return jsonify({'error': 'Failed to load parameters'}), 500


@app.route('/api/feed/dates')
@login_required
def get_feed_saved_dates():
    """Get all dates with feed entries, organized by visibility level"""
    try:
        user_id = session['user_id']

        # Get all posts for this user
        posts = Post.query.filter_by(user_id=user_id).all()

        # Organize dates by circle_id
        dates_by_circle = {
            1: [],  # public/general
            2: [],  # close_friends/class_b
            3: [],  # family/class_a
            None: []  # private
        }

        for post in posts:
            date_str = post.created_at.strftime('%Y-%m-%d')
            if post.circle_id not in dates_by_circle:
                dates_by_circle[post.circle_id] = []
            if date_str not in dates_by_circle[post.circle_id]:
                dates_by_circle[post.circle_id].append(date_str)

        # Map circle_ids to visibility names
        visibility_dates = {
            'general': dates_by_circle[1],
            'close_friends': dates_by_circle[2],
            'family': dates_by_circle[3],
            'private': dates_by_circle[None]
        }

        # For backward compatibility, also return combined dates
        all_dates = set()
        for dates in dates_by_circle.values():
            all_dates.update(dates)

        # FIX: Return BOTH combined dates AND dates separated by visibility
        return jsonify({
            'dates': {date: True for date in all_dates},
            'dates_by_visibility': visibility_dates  # ← NEW: Needed for frontend
        })

    except Exception as e:
        logger.error(f"Error fetching feed dates: {e}")
        return jsonify({'dates': {}, 'dates_by_visibility': {}})


@app.route('/api/users/<int:user_id>/feed/dates')
@login_required
def get_user_feed_dates(user_id):
    """Get dates that have feed entries for a specific user with circle-based visibility"""
    try:
        current_user_id = session.get('user_id')

        # If viewing own dates, use the standard endpoint logic
        if user_id == current_user_id:
            posts = db.session.query(
                db.func.date(Post.created_at).label('date'),
                Post.circle_id
            ).filter_by(
                user_id=user_id
            ).group_by(
                db.func.date(Post.created_at),
                Post.circle_id
            ).all()

            dates_with_visibility = {}
            circle_to_visibility = {
                1: 'public',  # was 'general'
                2: 'class_b',  # was 'close_friends'
                3: 'class_a',  # was 'family'
                None: 'private'
            }

            for post in posts:
                date_str = post.date.strftime('%Y-%m-%d')
                if date_str not in dates_with_visibility:
                    dates_with_visibility[date_str] = []

                visibility = circle_to_visibility.get(post.circle_id, 'general')
                dates_with_visibility[date_str].append(visibility)

            return jsonify({'dates': dates_with_visibility})

        # Check circle membership
        # Check circle membership
        membership = Circle.query.filter_by(
            user_id=user_id,
            circle_user_id=current_user_id
        ).first()

        # Determine which circle IDs current user can see (hierarchical)
        visible_circle_ids = [1]  # Everyone can see general/public (circle_id=1)
        if membership:
            if membership.circle_type == 'class_a' or membership.circle_type == 'family':
                # Class A members can see public (1), class_b (2), and class_a (3)
                visible_circle_ids = [1, 2, 3]
            elif membership.circle_type == 'class_b' or membership.circle_type == 'close_friends':
                # Class B members can see public (1) and class_b (2)
                visible_circle_ids = [1, 2]

        # Get posts filtered by visible circles
        posts = db.session.query(
            db.func.date(Post.created_at).label('date'),
            Post.circle_id
        ).filter(
            Post.user_id == user_id,
            Post.circle_id.in_(visible_circle_ids)
        ).group_by(
            db.func.date(Post.created_at),
            Post.circle_id
        ).all()

        dates_with_visibility = {}
        circle_to_visibility = {
            1: 'public',  # was 'general'
            2: 'class_b',  # was 'close_friends'
            3: 'class_a',  # was 'family'
            None: 'private'
        }

        for post in posts:
            date_str = post.date.strftime('%Y-%m-%d')
            if date_str not in dates_with_visibility:
                dates_with_visibility[date_str] = []

            visibility = circle_to_visibility.get(post.circle_id, 'general')
            dates_with_visibility[date_str].append(visibility)

        return jsonify({'dates': dates_with_visibility})

    except Exception as e:
        logger.error(f"Error getting user feed dates: {e}")
        return jsonify({'dates': {}})


@app.route('/api/users/<int:user_id>/feed/<date>')
@login_required
def get_user_feed_by_date(user_id, date):
    """Get a specific user's feed posts for a date with circle-based visibility"""
    try:
        current_user_id = session.get('user_id')

        # Parse the date
        from datetime import datetime, timedelta
        feed_date = datetime.fromisoformat(date).date()

        # Get start and end of the day
        start_datetime = datetime.combine(feed_date, datetime.min.time())
        end_datetime = datetime.combine(feed_date, datetime.max.time())

        # If viewing own posts, return all for that date
        # If viewing own posts, return all for that date
        if user_id == current_user_id:
            posts = Post.query.filter(
                Post.user_id == user_id,
                Post.created_at >= start_datetime,
                Post.created_at <= end_datetime
            ).order_by(Post.created_at.desc()).all()

            circle_to_visibility = {
                1: 'public',  # was 'general'
                2: 'class_b',  # was 'close_friends'
                3: 'class_a',  # was 'family'
                None: 'private'
            }

            # Calculate likes and comments for each post
            posts_data = []
            for post in posts:
                # Count likes from Reaction table
                likes_count = db.session.execute(
                    select(func.count(Reaction.id)).filter_by(post_id=post.id, type='like')
                ).scalar() or 0

                # Count comments
                comments_count = db.session.execute(
                    select(func.count(Comment.id)).filter_by(post_id=post.id)
                ).scalar() or 0

                # Check if current user liked this post
                user_liked = db.session.execute(
                    select(Reaction).filter_by(
                        post_id=post.id,
                        user_id=current_user_id,
                        type='like'
                    )
                ).scalar_one_or_none() is not None

                posts_data.append({
                    'id': post.id,
                    'content': post.content,
                    'created_at': post.created_at.isoformat() if post.created_at else None,
                    'circle_id': post.circle_id,
                    'likes_count': likes_count,
                    'comments_count': comments_count,
                    'user_liked': user_liked,
                    'visibility': post.visibility
                })

            return jsonify({'posts': posts_data})

        # Check if following this user
        is_following = Follow.query.filter_by(
            follower_id=current_user_id,
            followed_id=user_id
        ).first() is not None

        if not is_following:
            return jsonify({'error': 'Must be following user to view posts'}), 403

        # Check circle membership
        membership = Circle.query.filter_by(
            user_id=user_id,
            circle_user_id=current_user_id
        ).first()

        # Determine which circle IDs current user can see
        # Determine which circle IDs current user can see (hierarchical)
        visible_circle_ids = [1]  # Everyone can see general/public (circle_id=1)
        if membership:
            if membership.circle_type in ['class_a', 'family']:
                # Class A members can see public (1), class_b (2), and class_a (3)
                visible_circle_ids = [1, 2, 3]
            elif membership.circle_type in ['class_b', 'close_friends']:
                # Class B members can see public (1) and class_b (2)
                visible_circle_ids = [1, 2]

        # Get posts filtered by visible circles for that date
        posts = Post.query.filter(
            Post.user_id == user_id,
            Post.circle_id.in_(visible_circle_ids),
            Post.created_at >= start_datetime,
            Post.created_at <= end_datetime
        ).order_by(Post.created_at.desc()).all()

        if not posts:
            return jsonify({'error': 'This update is not available to you based on your circle membership'}), 403

        circle_to_visibility = {
            1: 'public',  # was 'general'
            2: 'class_b',  # was 'close_friends'
            3: 'class_a',  # was 'family'
            None: 'private'
        }

        # Calculate likes and comments for each post
        posts_data = []
        for post in posts:
            # Count likes from Reaction table
            likes_count = db.session.execute(
                select(func.count(Reaction.id)).filter_by(post_id=post.id, type='like')
            ).scalar() or 0

            # Count comments
            comments_count = db.session.execute(
                select(func.count(Comment.id)).filter_by(post_id=post.id)
            ).scalar() or 0

            # Check if current user liked this post
            user_liked = db.session.execute(
                select(Reaction).filter_by(
                    post_id=post.id,
                    user_id=current_user_id,
                    type='like'
                )
            ).scalar_one_or_none() is not None

            posts_data.append({
                'id': post.id,
                'content': post.content,
                'created_at': post.created_at.isoformat() if post.created_at else None,
                'circle_id': post.circle_id,
                'likes_count': likes_count,
                'comments_count': comments_count,
                'user_liked': user_liked,
                'visibility': post.visibility
            })

        return jsonify({'posts': posts_data})

    except Exception as e:
        logger.error(f"Error getting user feed by date: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/posts', methods=['POST'])
@login_required
def save_feed_entry():
    """Save/update feed entry for a specific date and visibility with STRICT permissions"""
    try:
        data = request.get_json()
        user_id = session['user_id']

        # Get the date and visibility from request
        post_date = data.get('date', datetime.utcnow().strftime('%Y-%m-%d'))
        content = data.get('content', '').strip()
        visibility = data.get('visibility', 'general')  # general, close_friends, family, private

        if not content:
            return jsonify({'error': 'Content is required'}), 400

        # REMOVED: Map visibility to circle_id - no longer needed
        # We now use visibility field directly instead of circle_id

        # Delete any existing posts for this date first
        Post.query.filter_by(user_id=user_id).filter(
            db.func.date(Post.created_at) == post_date
        ).delete()

        # Create a SINGLE post with visibility field
        new_post = Post(
            user_id=user_id,
            content=content,
            circle_id=None,  # CHANGED: Always None, use visibility instead
            visibility=visibility,  # ADDED: Store visibility directly
            created_at=datetime.strptime(post_date, '%Y-%m-%d'),
            updated_at=datetime.utcnow(),
            is_published=True
        )
        db.session.add(new_post)

        db.session.commit()
        visibility_display = visibility.replace("_", " ").title()
        return jsonify({'success': True, 'message': f'Feed saved for {visibility_display} on {post_date}'})

    except Exception as e:
        logger.error(f"Feed save error: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to save feed'}), 500


@app.route('/api/posts/<int:post_id>/like', methods=['POST'])
@login_required
def like_post(post_id):
    """Toggle like on a post"""
    try:
        user_id = session.get('user_id')

        # Check if post exists and user has access
        post = db.session.get(Post, post_id)
        if not post:
            return jsonify({'error': 'Post not found'}), 404

        # Check if user already liked this post
        existing_reaction = db.session.execute(
            select(Reaction).filter_by(
                post_id=post_id,
                user_id=user_id,
                type='like'
            )
        ).scalar_one_or_none()

        if existing_reaction:
            # Unlike - remove the reaction
            db.session.delete(existing_reaction)
            db.session.commit()

            # Get updated count
            likes_count = db.session.execute(
                select(func.count(Reaction.id)).filter_by(
                    post_id=post_id,
                    type='like'
                )
            ).scalar()

            return jsonify({
                'success': True,
                'liked': False,
                'likes_count': likes_count
            }), 200
        else:
            # Like - add the reaction
            new_reaction = Reaction(
                post_id=post_id,
                user_id=user_id,
                type='like'
            )
            db.session.add(new_reaction)
            db.session.commit()

            # Get updated count
            likes_count = db.session.execute(
                select(func.count(Reaction.id)).filter_by(
                    post_id=post_id,
                    type='like'
                )
            ).scalar()

            return jsonify({
                'success': True,
                'liked': True,
                'likes_count': likes_count
            }), 200

    except Exception as e:
        logger.error(f"Error toggling like: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to toggle like'}), 500


@app.route('/api/posts/<int:post_id>/comments', methods=['GET'])
@login_required
def get_post_comments(post_id):
    """Get all comments for a post"""
    try:
        # Check if post exists
        post = db.session.get(Post, post_id)
        if not post:
            return jsonify({'error': 'Post not found'}), 404

        # Get comments with author information
        comments = db.session.execute(
            select(Comment).filter_by(post_id=post_id).order_by(Comment.created_at.asc())
        ).scalars().all()

        comments_data = []
        for comment in comments:
            author = db.session.get(User, comment.user_id)
            comments_data.append({
                'id': comment.id,
                'content': comment.content,
                'created_at': comment.created_at.isoformat(),
                'author': {
                    'id': author.id,
                    'username': author.username
                }
            })

        return jsonify({'comments': comments_data}), 200

    except Exception as e:
        logger.error(f"Error getting comments: {e}")
        return jsonify({'error': 'Failed to load comments'}), 500


@app.route('/api/posts/<int:post_id>/comments', methods=['POST'])
@login_required
def add_comment(post_id):
    """Add a comment to a post"""
    try:
        user_id = session.get('user_id')
        data = request.json
        content = data.get('content', '').strip()

        if not content:
            return jsonify({'error': 'Comment content required'}), 400

        # Check if post exists
        post = db.session.get(Post, post_id)
        if not post:
            return jsonify({'error': 'Post not found'}), 404

        # Create new comment
        new_comment = Comment(
            post_id=post_id,
            user_id=user_id,
            content=sanitize_input(content)
        )
        db.session.add(new_comment)
        db.session.commit()

        # Get author information
        author = db.session.get(User, user_id)

        # Get updated comment count
        comments_count = db.session.execute(
            select(func.count(Comment.id)).filter_by(post_id=post_id)
        ).scalar()

        return jsonify({
            'success': True,
            'comment': {
                'id': new_comment.id,
                'content': new_comment.content,
                'created_at': new_comment.created_at.isoformat(),
                'author': {
                    'id': author.id,
                    'username': author.username
                }
            },
            'comments_count': comments_count
        }), 201

    except Exception as e:
        logger.error(f"Error adding comment: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to add comment'}), 500

@app.route('/api/feed/<date_str>')
@login_required
def load_feed_by_date(date_str):
    """Load feed entry for a specific date and visibility with STRICT matching"""
    try:
        user_id = session['user_id']
        visibility = request.args.get('visibility', 'general')

        # Get the post for this date that matches the requested visibility
        post = Post.query.filter_by(
            user_id=user_id,
            visibility=visibility  # Match by visibility field, not circle_id
        ).filter(
            db.func.date(Post.created_at) == date_str
        ).first()

        if post:
            return jsonify({
                'content': post.content,
                'date': date_str,
                'visibility': visibility,
                'updated_at': post.updated_at.isoformat() if post.updated_at else None
            })
        else:
            return jsonify({
                'content': '',
                'date': date_str,
                'visibility': visibility,
                'message': f'No {visibility.replace("_", " ")} feed entry for this date'
            })

    except Exception as e:
        logger.error(f"Load feed error: {e}")
        return jsonify({'error': 'Failed to load feed'}), 500


# =====================
# PARAMETERS ROUTES (Therapy Companion)
# =====================
# app.py - Fix for /api/parameters GET endpoint
# Location: Replace lines 3189-3235 in app.py

@app.route('/api/parameters', methods=['GET'])
@login_required
def get_parameters():
    """Get parameters for a specific date"""
    try:
        user_id = session.get('user_id')
        date_str = request.args.get('date')

        if not date_str:
            date_str = datetime.now().strftime('%Y-%m-%d')

        params = SavedParameters.query.filter_by(
            user_id=user_id,
            date=date_str
        ).first()

        if params:
            return jsonify({
                'success': True,
                'data': {
                    'parameters': {
                        'mood': int(params.mood) if params.mood else 0,
                        'energy': int(params.energy) if params.energy else 0,
                        'sleep_quality': int(params.sleep_quality) if params.sleep_quality else 0,
                        'physical_activity': int(params.physical_activity) if params.physical_activity else 0,
                        'anxiety': int(params.anxiety) if params.anxiety else 0
                    },
                    # ADD ALL PRIVACY SETTINGS HERE
                    'mood_privacy': params.mood_privacy or 'public',
                    'energy_privacy': params.energy_privacy or 'public',
                    'sleep_quality_privacy': params.sleep_quality_privacy or 'public',
                    'physical_activity_privacy': params.physical_activity_privacy or 'public',
                    'anxiety_privacy': params.anxiety_privacy or 'public',
                    'notes': params.notes or ''
                }
            })
        else:
            return jsonify({
                'success': True,
                'data': {
                    'parameters': {
                        'mood': 0,
                        'energy': 0,
                        'sleep_quality': 0,
                        'physical_activity': 0,
                        'anxiety': 0
                    },
                    # ADD DEFAULT PRIVACY SETTINGS
                    'mood_privacy': 'public',
                    'energy_privacy': 'public',
                    'sleep_quality_privacy': 'public',
                    'physical_activity_privacy': 'public',
                    'anxiety_privacy': 'public',
                    'notes': ''
                }
            })

    except Exception as e:
        logger.error(f"Get parameters error: {str(e)}")
        return jsonify({'error': 'Failed to get parameters'}), 500


@app.route('/api/parameters', methods=['POST'])
@login_required
def save_parameters():
    """Save user parameters with privacy settings"""
    try:
        data = request.get_json()
        user_id = session.get('user_id')
        date_str = data.get('date')

        if not date_str:
            return jsonify({'error': 'Date is required'}), 400

            # Parse the date as local date without timezone conversion
        try:
            param_date = parse_date_as_local(date_str)
            date_str = param_date.isoformat()  # Ensure consistent YYYY-MM-DD format
        except ValueError:
            return jsonify({'error': 'Invalid date format'}), 400

        # Find or create parameter entry
        # Find or create parameter entry
        params = SavedParameters.query.filter_by(
            user_id=user_id,
            date=date_str
        ).first()

        if not params:
            params = SavedParameters(
                user_id=user_id,
                date=date_str
            )

        # Update values - ENSURE INTEGER CONVERSION
        for field in ['mood', 'energy', 'sleep_quality', 'physical_activity', 'anxiety']:
            if field in data:
                value = data[field]
                if value is not None:
                    try:
                        # Convert to integer
                        int_value = int(value)
                        if 1 <= int_value <= 4:
                            setattr(params, field, int_value)
                    except (ValueError, TypeError):
                        pass  # Skip invalid values

            # Handle privacy settings
            privacy_field = f"{field}_privacy"
            if privacy_field in data:
                privacy_value = data[privacy_field]
                if privacy_value in ['public', 'class_a', 'class_b', 'private']:
                    setattr(params, privacy_field, privacy_value)

        if 'notes' in data:
            params.notes = data['notes']

        params.updated_at = datetime.utcnow()
        db.session.add(params)
        db.session.commit()

        # Check triggers
        process_parameter_triggers(user_id, params)

        # Cleanup stale trigger alerts based on new privacy settings
        cleanup_stale_trigger_alerts_for_user(user_id)

        import random
        encouragements = [
            "Great job tracking your wellness today! 🌟",
            "Your consistency is inspiring! Keep it up! 💪",
            "Every check-in is a step forward! 🚀",
            "Thank you for taking care of yourself! ❤️",
            "Your commitment to wellness is admirable! 🌈"
        ]

        # Return consistent format
        return jsonify({
            'success': True,
            'message': 'Parameters saved successfully',
            'encouragement': random.choice(encouragements),
            'data': {
                'parameters': {
                    'mood': int(params.mood) if params.mood else 0,
                    'energy': int(params.energy) if params.energy else 0,
                    'sleep_quality': int(params.sleep_quality) if params.sleep_quality else 0,
                    'physical_activity': int(params.physical_activity) if params.physical_activity else 0,
                    'anxiety': int(params.anxiety) if params.anxiety else 0
                },
                'notes': params.notes or ''
            }
        }), 200

    except Exception as e:
        logger.error(f"Error saving parameters: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Failed to save parameters'}), 500


def process_parameter_triggers(user_id, params):
    """Check triggers when parameters are saved - checks for N consecutive days based on trigger settings"""
    try:
        # Find all triggers where someone is watching this user
        triggers = ParameterTrigger.query.filter_by(watched_id=user_id).all()

        for trigger in triggers:
            # Skip if no consecutive_days is set (shouldn't happen, but safety check)
            if not trigger.consecutive_days or trigger.consecutive_days < 1:
                continue

            # Get last 30 days of parameters to check for consecutive patterns
            thirty_days_ago = datetime.now().date() - timedelta(days=30)
            all_params = SavedParameters.query.filter(
                SavedParameters.user_id == user_id,
                SavedParameters.date >= thirty_days_ago
            ).order_by(SavedParameters.date.desc()).all()

            # Need at least as many days as the trigger requires
            if len(all_params) < trigger.consecutive_days:
                continue

            watched_user = User.query.get(user_id)

            # Define parameters to check with their trigger conditions
            param_checks = []
            if trigger.mood_alert:
                param_checks.append(('mood', 'mood', lambda x: x <= 2, 2))
            if trigger.energy_alert:
                param_checks.append(('energy', 'energy', lambda x: x <= 2, 2))
            if trigger.sleep_alert:
                param_checks.append(('sleep_quality', 'sleep quality', lambda x: x <= 2, 2))
            if trigger.physical_alert:
                param_checks.append(('physical_activity', 'physical activity', lambda x: x <= 2, 2))
            if trigger.anxiety_alert:
                param_checks.append(('anxiety', 'anxiety', lambda x: x >= 3, 3))

            for param_attr, param_name, condition_func, threshold in param_checks:
                # Look for N consecutive days (where N = trigger.consecutive_days)
                consecutive_count = 0
                consecutive_dates = []
                last_date = None

                for param_entry in all_params:
                    param_value = getattr(param_entry, param_attr, None)

                    if param_value is not None and condition_func(param_value):
                        # Check if consecutive
                        if last_date is None or (last_date - param_entry.date).days == 1:
                            consecutive_count += 1
                            consecutive_dates.append(param_entry.date)
                            last_date = param_entry.date

                            # If we found the required consecutive days, create alert
                            if consecutive_count >= trigger.consecutive_days:
                                # Check if we've already alerted for this pattern
                                # Look for recent similar alerts (within last 7 days)
                                recent_alert = Alert.query.filter(
                                    Alert.user_id == trigger.watcher_id,
                                    Alert.alert_type == 'trigger',
                                    Alert.content.like(f"%{watched_user.username}%{param_name}%consecutive%"),
                                    Alert.created_at >= datetime.now() - timedelta(days=7)
                                ).first()

                                if not recent_alert:
                                    alert = Alert(
                                        user_id=trigger.watcher_id,
                                        title=f"Wellness Alert for {watched_user.username}",
                                        content=f"{watched_user.username}'s {param_name} has been at concerning levels for {consecutive_count} consecutive days (ending {consecutive_dates[0].strftime('%b %d')})",
                                        alert_type='trigger'
                                    )
                                    db.session.add(alert)
                                    db.session.commit()
                                break  # Only alert once per parameter type
                        else:
                            # Reset if not consecutive
                            consecutive_count = 1
                            consecutive_dates = [param_entry.date]
                            last_date = param_entry.date
                    else:
                        # Reset if condition not met
                        consecutive_count = 0
                        consecutive_dates = []
                        last_date = None

    except Exception as e:
        logger.error(f"Error processing parameter triggers: {str(e)}")
        db.session.rollback()


def cleanup_stale_trigger_alerts_for_user(affected_user_id):
    """
    Automatically clean up trigger alerts that are no longer valid due to privacy changes.
    This runs whenever parameters are saved to ensure alerts respect current privacy settings.

    Args:
        affected_user_id: The user whose parameters were just updated
    """
    try:
        # Helper function to check privacy permissions
        def can_see_parameter(param_privacy, watcher_circle):
            """Check if watcher can see this parameter based on privacy and circle level"""
            if param_privacy == 'private':
                return False
            elif param_privacy == 'class_a':
                return watcher_circle == 'class_a'
            elif param_privacy == 'class_b':
                return watcher_circle in ['class_b', 'class_a']
            elif param_privacy == 'public':
                return True
            return False

        # Get the user who was just updated
        affected_user = User.query.get(affected_user_id)
        if not affected_user:
            return

        # Find all watchers who have triggers for this user
        triggers = ParameterTrigger.query.filter_by(watched_id=affected_user_id).all()

        for trigger in triggers:
            watcher_id = trigger.watcher_id

            # Get watcher's circle level
            watcher_circle = get_watcher_circle_level(affected_user_id, watcher_id)

            if not watcher_circle:
                # Watcher not in any circle - remove all their alerts for this user
                alerts_to_remove = Alert.query.filter(
                    Alert.user_id == watcher_id,
                    Alert.alert_type == 'trigger',
                    Alert.content.like(f"%{affected_user.username}%")
                ).all()

                for alert in alerts_to_remove:
                    db.session.delete(alert)
                    logger.info(
                        f"Removed alert {alert.id}: watcher {watcher_id} not in any circle of user {affected_user_id}")
                continue

            # Get current privacy settings for this user
            recent_param = SavedParameters.query.filter_by(
                user_id=affected_user_id
            ).order_by(SavedParameters.updated_at.desc()).first()

            if not recent_param:
                continue

            # Check each parameter type's privacy
            param_keywords = {
                'mood': 'mood_privacy',
                'anxiety': 'anxiety_privacy',
                'sleep_quality': 'sleep_quality_privacy',
                'sleep quality': 'sleep_quality_privacy',
                'physical_activity': 'physical_activity_privacy',
                'physical activity': 'physical_activity_privacy',
                'energy': 'energy_privacy'
            }

            # Get all trigger alerts for this watcher about this user
            watcher_alerts = Alert.query.filter(
                Alert.user_id == watcher_id,
                Alert.alert_type == 'trigger',
                Alert.content.like(f"%{affected_user.username}%")
            ).all()

            for alert in watcher_alerts:
                content = alert.content or ""

                # Find which parameter this alert is about
                privacy_attr = None
                for keyword, privacy_field in param_keywords.items():
                    if keyword in content.lower():
                        privacy_attr = privacy_field
                        break

                if not privacy_attr:
                    continue

                # Get current privacy setting for this parameter
                param_privacy = getattr(recent_param, privacy_attr, 'private')

                # Check if watcher should still see this alert
                if not can_see_parameter(param_privacy, watcher_circle):
                    db.session.delete(alert)
                    logger.info(
                        f"Auto-cleanup: Removed alert {alert.id} for watcher {watcher_id} - {param_privacy} vs {watcher_circle}")

        db.session.commit()
        logger.info(f"Auto-cleanup completed for user {affected_user_id}")

    except Exception as e:
        logger.error(f"Error in automatic cleanup: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        db.session.rollback()


def cleanup_all_stale_trigger_alerts():
    """
    One-time cleanup function to remove all existing stale trigger alerts.
    This should run on app startup after deployment to clean up historical alerts.
    """
    try:
        logger.info("Starting global trigger alerts cleanup...")

        # Helper function to check privacy permissions
        def can_see_parameter(param_privacy, watcher_circle):
            """Check if watcher can see this parameter based on privacy and circle level"""
            if param_privacy == 'private':
                return False
            elif param_privacy == 'class_a':
                return watcher_circle == 'class_a'
            elif param_privacy == 'class_b':
                return watcher_circle in ['class_b', 'class_a']
            elif param_privacy == 'public':
                return True
            return False

        # Get all trigger alerts
        all_trigger_alerts = Alert.query.filter_by(alert_type='trigger').all()

        total_checked = len(all_trigger_alerts)
        removed_count = 0
        kept_count = 0

        param_keywords = {
            'mood': 'mood_privacy',
            'anxiety': 'anxiety_privacy',
            'sleep_quality': 'sleep_quality_privacy',
            'sleep quality': 'sleep_quality_privacy',
            'physical_activity': 'physical_activity_privacy',
            'physical activity': 'physical_activity_privacy',
            'energy': 'energy_privacy'
        }

        for alert in all_trigger_alerts:
            watcher_id = alert.user_id
            content = alert.content or ""

            # Parse username from content
            if "'s " not in content:
                kept_count += 1
                continue

            username = content.split("'s ")[0]
            watched_user = User.query.filter_by(username=username).first()

            if not watched_user:
                kept_count += 1
                continue

            watched_id = watched_user.id

            # Get watcher's circle level
            watcher_circle = get_watcher_circle_level(watched_id, watcher_id)

            if not watcher_circle:
                # Watcher not in any circle - remove alert
                db.session.delete(alert)
                removed_count += 1
                logger.info(f"Global cleanup: Removed alert {alert.id} - watcher {watcher_id} not in circles")
                continue

            # Find which parameter this alert is about
            privacy_attr = None
            for keyword, privacy_field in param_keywords.items():
                if keyword in content.lower():
                    privacy_attr = privacy_field
                    break

            if not privacy_attr:
                kept_count += 1
                continue

            # Get current privacy settings
            recent_param = SavedParameters.query.filter_by(
                user_id=watched_id
            ).order_by(SavedParameters.updated_at.desc()).first()

            if not recent_param:
                kept_count += 1
                continue

            param_privacy = getattr(recent_param, privacy_attr, 'private')

            # Check if watcher should see this alert
            if not can_see_parameter(param_privacy, watcher_circle):
                db.session.delete(alert)
                removed_count += 1
                logger.info(
                    f"Global cleanup: Removed alert {alert.id} - privacy violation ({param_privacy} vs {watcher_circle})")
            else:
                kept_count += 1

        db.session.commit()

        logger.info(f"Global cleanup completed: Checked {total_checked}, Removed {removed_count}, Kept {kept_count}")
        return removed_count

    except Exception as e:
        logger.error(f"Error in global cleanup: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        db.session.rollback()
        return 0


@app.route('/api/parameters/dates', methods=['GET'])
@login_required
def get_parameter_dates():
    """Get all dates that have saved parameters for the current user"""
    try:
        user_id = session.get('user_id')

        # Get all parameter dates for this user using SQLAlchemy ORM
        params = SavedParameters.query.filter_by(user_id=user_id).all()

        # Extract just the dates
        dates = [param.date.strftime('%Y-%m-%d') if hasattr(param.date, 'strftime') else str(param.date)
                 for param in params if param.date]

        return jsonify({
            'success': True,
            'dates': dates
        })

    except Exception as e:
        logger.error(f"Get parameter dates error: {str(e)}")
        return jsonify({
            'success': False,
            'dates': []
        })


@app.route('/api/parameters/insights')
@login_required
def get_insights():
    """Get parameter insights"""
    try:
        user_id = session['user_id']

        # Get last 30 days - SQLAlchemy 2.0 style
        thirty_days_ago = datetime.now().date() - timedelta(days=30)
        params_stmt = select(SavedParameters).filter(
            SavedParameters.user_id == user_id,
            SavedParameters.date >= thirty_days_ago
        )
        params = db.session.execute(params_stmt).scalars().all()

        if not params:
            return jsonify({'message': 'No data available for insights'})

        # Calculate insights
        avg_sleep = sum(p.sleep_hours for p in params if p.sleep_hours) / len(params) if params else 0
        moods = [p.mood for p in params if p.mood]

        return jsonify({
            'average_sleep': round(avg_sleep, 1),
            'total_entries': len(params),
            'most_common_mood': max(moods, key=moods.count) if moods else 'N/A',
            'streak': calculate_streak(params)
        })

    except Exception as e:
        logger.error(f"Get insights error: {str(e)}")
        return jsonify({'message': 'Failed to get insights'})


@app.route('/api/parameters/triggers/<int:user_id>', methods=['GET'])
@login_required
def get_parameter_triggers(user_id):
    """Get trigger settings for a user being watched"""
    try:
        watcher_id = session.get('user_id')
        trigger = db.session.execute(
            select(ParameterTrigger).filter_by(
                watcher_id=watcher_id,
                watched_id=user_id
            )
        ).scalar_one_or_none()

        if trigger:
            return jsonify({
                'mood_alert': trigger.mood_alert,
                'energy_alert': trigger.energy_alert,
                'sleep_alert': trigger.sleep_alert,
                'physical_alert': trigger.physical_alert,
                'anxiety_alert': trigger.anxiety_alert
            })
        else:
            return jsonify({
                'mood_alert': False,
                'energy_alert': False,
                'sleep_alert': False,
                'physical_alert': False,
                'anxiety_alert': False
            })

    except Exception as e:
        logger.error(f"Get triggers error: {e}")
        return jsonify({'error': 'Failed to get triggers'}), 500


@app.route('/api/parameters/triggers/<int:user_id>', methods=['POST'])
@login_required
def set_parameter_triggers(user_id):
    """Set trigger alerts for a user being watched"""
    try:
        watcher_id = session.get('user_id')
        data = request.json

        follow = db.session.execute(
            select(Follow).filter_by(
                follower_id=watcher_id,
                followed_id=user_id
            )
        ).scalar_one_or_none()

        if not follow:
            return jsonify({'error': 'You must be following this user'}), 400

        trigger = db.session.execute(
            select(ParameterTrigger).filter_by(
                watcher_id=watcher_id,
                watched_id=user_id
            )
        ).scalar_one_or_none()

        if not trigger:
            trigger = ParameterTrigger(
                watcher_id=watcher_id,
                watched_id=user_id
            )
            db.session.add(trigger)

        trigger.mood_alert = data.get('mood_alert', False)
        trigger.energy_alert = data.get('energy_alert', False)
        trigger.sleep_alert = data.get('sleep_alert', False)
        trigger.physical_alert = data.get('physical_alert', False)
        trigger.anxiety_alert = data.get('anxiety_alert', False)

        db.session.commit()
        return jsonify({'success': True})

    except Exception as e:
        logger.error(f"Set triggers error: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to set triggers'}), 500


def get_watcher_circle_level(watched_id, watcher_id):
    """
    Get the circle level that the watcher belongs to for the watched user.

    Args:
        watched_id: User ID of the person being watched
        watcher_id: User ID of the person watching

    Returns:
        str: 'class_a', 'class_b', 'public', or None if not in any circle
    """
    # Check if watcher is in any of watched user's circles
    circle = db.session.execute(
        select(Circle).filter_by(
            user_id=watched_id,
            circle_user_id=watcher_id
        )
    ).scalar_one_or_none()

    if circle:
        return circle.circle_type

    # Not in any circle
    return None


@app.route('/api/parameters/check-triggers', methods=['GET'])
@login_required
def check_parameter_triggers():
    """Check for parameter alerts - respects privacy settings"""
    try:
        watcher_id = session.get('user_id')
        triggers = db.session.execute(
            select(ParameterTrigger).filter_by(watcher_id=watcher_id)
        ).scalars().all()

        alerts = []
        alerts_created = 0
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)

        # Helper function to convert values to numbers (for OLD schema)
        def to_number(val):
            if val is None:
                return None
            if isinstance(val, (int, float)):
                return float(val)
            if isinstance(val, str):
                if val.lower() in ['private', 'hidden', 'none']:
                    return None
                try:
                    return float(val)
                except ValueError:
                    return None
            return None

        # ✅ NEW: Helper to check if parameter is visible to watcher
        def can_see_parameter(param_privacy, watcher_circle):
            """Check if watcher can see this parameter based on privacy and circle level"""
            if param_privacy == 'private':
                return False  # Private params never trigger alerts
            elif param_privacy == 'class_a':
                return watcher_circle == 'class_a'
            elif param_privacy == 'class_b':
                return watcher_circle in ['class_b', 'class_a']
            elif param_privacy == 'public':
                return True  # Public params trigger for everyone
            return False

        for trigger in triggers:
            # Skip if no consecutive_days setting
            if not trigger.consecutive_days or trigger.consecutive_days < 1:
                continue

            # ✅ NEW: Get watcher's circle level for this watched user
            watcher_circle = get_watcher_circle_level(trigger.watched_id, watcher_id)
            if not watcher_circle:
                # Watcher is not in any circle for this user - skip
                continue

            parameters = db.session.execute(
                select(SavedParameters).filter(
                    SavedParameters.user_id == trigger.watched_id,
                    SavedParameters.date >= thirty_days_ago
                ).order_by(SavedParameters.date.asc())
            ).scalars().all()

            # Need at least as many days as the trigger requires
            if len(parameters) < trigger.consecutive_days:
                continue

            watched_user = db.session.get(User, trigger.watched_id)
            if not watched_user:
                continue

            # ===== DETERMINE WHICH SCHEMA THIS TRIGGER USES =====
            has_new_schema = any([
                trigger.mood_alert,
                trigger.energy_alert,
                trigger.sleep_alert,
                trigger.physical_alert,
                trigger.anxiety_alert
            ])

            has_old_schema = trigger.parameter_name is not None

            # ===== NEW SCHEMA CODE (WITH PRIVACY CHECK) =====
            if has_new_schema:
                # Helper function to check consecutive days - FINDS ALL OCCURRENCES
                # ✅ MODIFIED: Now checks privacy for each parameter
                def check_consecutive_pattern(param_attr, privacy_attr, condition_func, alert_level_func):
                    found_patterns = []
                    consecutive_count = 0
                    consecutive_values = []
                    consecutive_dates = []
                    last_date = None

                    for param in parameters:
                        param_value = getattr(param, param_attr, None)
                        param_privacy = getattr(param, privacy_attr, 'private')

                        # ✅ NEW: Check if watcher can see this parameter
                        if not can_see_parameter(param_privacy, watcher_circle):
                            # Reset streak if we hit a private parameter
                            consecutive_count = 0
                            consecutive_values = []
                            consecutive_dates = []
                            last_date = None
                            continue

                        if param_value is not None and condition_func(param_value):
                            # Check if consecutive
                            if last_date is None or (param.date - last_date).days == 1:
                                consecutive_count += 1
                                consecutive_values.append(param_value)
                                consecutive_dates.append(param.date)
                                last_date = param.date

                                # Check if we hit the required consecutive days
                                if consecutive_count >= trigger.consecutive_days:
                                    pattern = {
                                        'level': alert_level_func(consecutive_values[-trigger.consecutive_days:]),
                                        'user': watched_user.username,
                                        'parameter': param_attr,
                                        'dates': [d.isoformat() for d in consecutive_dates[-trigger.consecutive_days:]],
                                        'values': consecutive_values[-trigger.consecutive_days:],
                                        'consecutive_days': consecutive_count
                                    }
                                    found_patterns.append(pattern)
                                    # Reset to find more patterns
                                    consecutive_count = 0
                                    consecutive_values = []
                                    consecutive_dates = []
                                    last_date = None
                            else:
                                # Reset if not consecutive
                                consecutive_count = 1
                                consecutive_values = [param_value]
                                consecutive_dates = [param.date]
                                last_date = param.date
                        else:
                            # Reset if condition not met
                            consecutive_count = 0
                            consecutive_values = []
                            consecutive_dates = []
                            last_date = None

                    return found_patterns

                # Check mood triggers (lower is worse)
                if trigger.mood_alert:
                    def mood_condition(val):
                        return val <= 2

                    def mood_level(vals):
                        avg = sum(vals) / len(vals)
                        if avg == 1:
                            return 'critical'
                        elif avg <= 1.5:
                            return 'high'
                        else:
                            return 'warning'

                    # ✅ MODIFIED: Pass privacy_attr parameter
                    results = check_consecutive_pattern('mood', 'mood_privacy', mood_condition, mood_level)
                    alerts.extend(results)

                # Check energy triggers (lower is worse)
                if trigger.energy_alert:
                    def energy_condition(val):
                        return val <= 2

                    def energy_level(vals):
                        avg = sum(vals) / len(vals)
                        if avg == 1:
                            return 'critical'
                        elif avg <= 1.5:
                            return 'high'
                        else:
                            return 'warning'

                    # ✅ MODIFIED: Pass privacy_attr parameter
                    results = check_consecutive_pattern('energy', 'energy_privacy', energy_condition,
                                                        energy_level)
                    alerts.extend(results)

                # Check sleep quality triggers (lower is worse)
                if trigger.sleep_alert:
                    def sleep_condition(val):
                        return val <= 2

                    def sleep_level(vals):
                        avg = sum(vals) / len(vals)
                        if avg == 1:
                            return 'critical'
                        elif avg <= 1.5:
                            return 'high'
                        else:
                            return 'warning'

                    # ✅ MODIFIED: Pass privacy_attr parameter
                    results = check_consecutive_pattern('sleep_quality', 'sleep_quality_privacy', sleep_condition,
                                                        sleep_level)
                    alerts.extend(results)

                # Check physical activity triggers (lower is worse)
                if trigger.physical_alert:
                    def physical_condition(val):
                        return val <= 2

                    def physical_level(vals):
                        avg = sum(vals) / len(vals)
                        if avg == 1:
                            return 'critical'
                        elif avg <= 1.5:
                            return 'high'
                        else:
                            return 'warning'

                    # ✅ MODIFIED: Pass privacy_attr parameter
                    results = check_consecutive_pattern('physical_activity', 'physical_activity_privacy',
                                                        physical_condition, physical_level)
                    alerts.extend(results)

                # Check anxiety triggers (higher is worse)
                if trigger.anxiety_alert:
                    def anxiety_condition(val):
                        return val >= 3

                    def anxiety_level(vals):
                        avg = sum(vals) / len(vals)
                        if avg == 4:
                            return 'critical'
                        elif avg >= 3.5:
                            return 'high'
                        else:
                            return 'warning'

                    # ✅ MODIFIED: Pass privacy_attr parameter
                    results = check_consecutive_pattern('anxiety', 'anxiety_privacy', anxiety_condition, anxiety_level)
                    alerts.extend(results)

            # ===== OLD SCHEMA CODE (WITH PRIVACY CHECK) =====
            elif has_old_schema:
                param_name = trigger.parameter_name
                condition = trigger.trigger_condition
                threshold = trigger.trigger_value

                # Map parameter name to model attribute
                param_mapping = {
                    'mood': ('mood', 'mood_privacy'),
                    'anxiety': ('anxiety', 'anxiety_privacy'),
                    'sleep_quality': ('sleep_quality', 'sleep_quality_privacy'),
                    'physical_activity': ('physical_activity', 'physical_activity_privacy'),
                    'energy': ('energy', 'energy_privacy')
                }

                if param_name not in param_mapping:
                    continue

                param_attr, privacy_attr = param_mapping[param_name]

                # Create condition function
                if condition == 'less_than':
                    def condition_func(val, t=threshold):
                        num = to_number(val)
                        return num is not None and num < t

                    condition_text = f"less than {threshold}"
                elif condition == 'greater_than':
                    def condition_func(val, t=threshold):
                        num = to_number(val)
                        return num is not None and num > t

                    condition_text = f"greater than {threshold}"
                elif condition == 'equals':
                    def condition_func(val, t=threshold):
                        num = to_number(val)
                        return num is not None and num == t

                    condition_text = f"equal to {threshold}"
                else:
                    continue

                # Find ALL consecutive patterns (WITH PRIVACY CHECK)
                consecutive_count = 0
                last_date = None
                streak_start = None

                for param in parameters:
                    param_value = getattr(param, param_attr, None)
                    param_privacy = getattr(param, privacy_attr, 'private')

                    # ✅ NEW: Check if watcher can see this parameter
                    if not can_see_parameter(param_privacy, watcher_circle):
                        # Reset streak if we hit a private parameter
                        consecutive_count = 0
                        last_date = None
                        streak_start = None
                        continue

                    if condition_func(param_value):
                        # Condition met
                        if last_date is None or (param.date - last_date).days == 1:
                            if consecutive_count == 0:
                                streak_start = param.date
                            consecutive_count += 1
                            last_date = param.date

                            # Check if we completed a pattern
                            if consecutive_count == trigger.consecutive_days:
                                # Add to alerts list for OLD schema format
                                alert_data = {
                                    'user': watched_user.username,
                                    'parameter': param_name,
                                    'consecutive_days': consecutive_count,
                                    'end_date': param.date,
                                    'condition_text': condition_text,
                                    'is_old_schema': True  # Flag for later processing
                                }
                                alerts.append(alert_data)

                                # Reset to find more patterns
                                consecutive_count = 0
                                last_date = None
                                streak_start = None
                        else:
                            # Not consecutive
                            consecutive_count = 1
                            streak_start = param.date
                            last_date = param.date
                    else:
                        # Condition not met
                        consecutive_count = 0
                        last_date = None
                        streak_start = None

        # ===== CREATE ALERT OBJECTS =====
        for alert_data in alerts:
            # Check if OLD schema alert
            if alert_data.get('is_old_schema'):
                # OLD schema format
                end_date_str = alert_data['end_date'].strftime('%b %d')

                # Check if we've already created this alert recently
                existing = Alert.query.filter(
                    Alert.user_id == watcher_id,
                    Alert.alert_type == 'trigger',
                    Alert.content.like(f"%{alert_data['user']}%{alert_data['parameter']}%ending {end_date_str}%"),
                    Alert.created_at >= datetime.utcnow() - timedelta(days=7)
                ).first()

                if not existing:
                    alert = Alert(
                        user_id=watcher_id,
                        title=f"Wellness Alert for {alert_data['user']}",
                        content=f"{alert_data['user']}'s {alert_data['parameter']} has been {alert_data['condition_text']} for {alert_data['consecutive_days']} consecutive days (ending {end_date_str})",
                        alert_type='trigger'
                    )
                    db.session.add(alert)
                    alerts_created += 1
            else:
                # NEW schema format (existing code)
                existing = Alert.query.filter(
                    Alert.user_id == watcher_id,
                    Alert.alert_type == 'trigger',
                    Alert.content.like(f"%{alert_data['user']}%{alert_data['parameter']}%"),
                    Alert.created_at >= datetime.utcnow() - timedelta(days=7)
                ).first()

                if not existing:
                    alert = Alert(
                        user_id=watcher_id,
                        title=f"Parameter Alert: {alert_data['user']}",
                        content=f"{alert_data['user']}'s {alert_data['parameter']} has been concerning for {alert_data['consecutive_days']} consecutive days",
                        alert_type='trigger'
                    )
                    db.session.add(alert)
                    alerts_created += 1

        db.session.commit()

        return jsonify({
            'success': True,
            'alerts': alerts,
            'count': alerts_created
        })

    except Exception as e:
        logger.error(f"Check triggers error: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e),
            'alerts': [],
            'count': 0
        })


# ==========================================
# PART 4: Automatic Cleanup Endpoint
# ==========================================
# Add this endpoint to app.py to handle retroactive cleanup automatically
# Insert anywhere after the get_watcher_circle_level() function

@app.route('/api/admin/cleanup-trigger-privacy', methods=['POST'])
@login_required
def cleanup_trigger_privacy():
    """
    Retroactively clean up trigger alerts that violate privacy settings.
    This should be run once after deploying the privacy fix.

    Only the logged-in user's alerts are cleaned up (not admin-only).
    """
    try:
        user_id = session.get('user_id')

        # Helper function (copy from main fix)
        def can_see_parameter(param_privacy, watcher_circle):
            """Check if watcher can see this parameter based on privacy and circle level"""
            if param_privacy == 'private':
                return False
            elif param_privacy == 'class_a':
                return watcher_circle == 'class_a'
            elif param_privacy == 'class_b':
                return watcher_circle in ['class_b', 'class_a']
            elif param_privacy == 'public':
                return True
            return False

        # Get all trigger alerts for this user
        trigger_alerts = Alert.query.filter_by(
            user_id=user_id,
            alert_type='trigger'
        ).all()

        total_checked = len(trigger_alerts)
        removed_count = 0
        kept_count = 0

        for alert in trigger_alerts:
            watcher_id = alert.user_id

            # Parse alert content to find watched user and parameter
            # Format: "username's parameter_name has been..."
            content = alert.content or ""

            if "'s " not in content:
                kept_count += 1
                continue

            username = content.split("'s ")[0]

            # Find watched user
            watched_user = User.query.filter_by(username=username).first()
            if not watched_user:
                kept_count += 1
                continue

            watched_id = watched_user.id

            # Get watcher's circle level using the helper function
            watcher_circle = get_watcher_circle_level(watched_id, watcher_id)

            if not watcher_circle:
                # Watcher not in any circle - should not have this alert
                db.session.delete(alert)
                removed_count += 1
                logger.info(f"Removed alert {alert.id}: watcher not in any circle")
                continue

            # Extract parameter name from content
            param_keywords = {
                'mood': 'mood_privacy',
                'anxiety': 'anxiety_privacy',
                'sleep_quality': 'sleep_quality_privacy',
                'sleep quality': 'sleep_quality_privacy',
                'physical_activity': 'physical_activity_privacy',
                'physical activity': 'physical_activity_privacy',
                'energy': 'energy_privacy'
            }

            privacy_attr = None
            for keyword, privacy_field in param_keywords.items():
                if keyword in content.lower():
                    privacy_attr = privacy_field
                    break

            if not privacy_attr:
                # Can't determine parameter - keep alert to be safe
                kept_count += 1
                continue

            # Get the most recent parameter entry for this user to check privacy
            recent_param = SavedParameters.query.filter_by(
                user_id=watched_id
            ).order_by(SavedParameters.updated_at.desc()).first()

            if not recent_param:
                kept_count += 1
                continue

            param_privacy = getattr(recent_param, privacy_attr, 'private')

            # Check if watcher should see this parameter
            if not can_see_parameter(param_privacy, watcher_circle):
                db.session.delete(alert)
                removed_count += 1
                logger.info(f"Removed alert {alert.id}: privacy violation ({param_privacy} vs {watcher_circle})")
            else:
                kept_count += 1

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Privacy cleanup completed',
            'total_checked': total_checked,
            'removed': removed_count,
            'kept': kept_count
        })

    except Exception as e:
        logger.error(f"Cleanup error: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ==========================================
# ALTERNATIVE: Admin-Only Global Cleanup
# ==========================================
# If you want an admin endpoint that cleans up ALL users' alerts at once:

@app.route('/api/admin/cleanup-all-trigger-privacy', methods=['POST'])
@login_required
def cleanup_all_trigger_privacy():
    """
    Clean up ALL trigger alerts across all users that violate privacy.
    Requires admin privileges.
    """
    try:
        # Check if user is admin (you'll need to add admin flag to User model)
        user_id = session.get('user_id')
        current_user = db.session.get(User, user_id)

        # For now, skip admin check - remove this in production!
        # if not current_user.is_admin:
        #     return jsonify({'error': 'Admin access required'}), 403

        def can_see_parameter(param_privacy, watcher_circle):
            if param_privacy == 'private':
                return False
            elif param_privacy == 'class_a':
                return watcher_circle == 'class_a'
            elif param_privacy == 'class_b':
                return watcher_circle in ['class_b', 'class_a']
            elif param_privacy == 'public':
                return True
            return False

        # Get ALL trigger alerts
        trigger_alerts = Alert.query.filter_by(alert_type='trigger').all()

        total_checked = len(trigger_alerts)
        removed_count = 0
        kept_count = 0
        removed_by_user = {}  # Track removals per user

        for alert in trigger_alerts:
            watcher_id = alert.user_id
            content = alert.content or ""

            if "'s " not in content:
                kept_count += 1
                continue

            username = content.split("'s ")[0]
            watched_user = User.query.filter_by(username=username).first()

            if not watched_user:
                kept_count += 1
                continue

            watched_id = watched_user.id
            watcher_circle = get_watcher_circle_level(watched_id, watcher_id)

            if not watcher_circle:
                db.session.delete(alert)
                removed_count += 1
                removed_by_user[watcher_id] = removed_by_user.get(watcher_id, 0) + 1
                continue

            param_keywords = {
                'mood': 'mood_privacy',
                'anxiety': 'anxiety_privacy',
                'sleep_quality': 'sleep_quality_privacy',
                'sleep quality': 'sleep_quality_privacy',
                'physical_activity': 'physical_activity_privacy',
                'physical activity': 'physical_activity_privacy',
                'energy': 'energy_privacy'
            }

            privacy_attr = None
            for keyword, privacy_field in param_keywords.items():
                if keyword in content.lower():
                    privacy_attr = privacy_field
                    break

            if not privacy_attr:
                kept_count += 1
                continue

            recent_param = SavedParameters.query.filter_by(
                user_id=watched_id
            ).order_by(SavedParameters.updated_at.desc()).first()

            if not recent_param:
                kept_count += 1
                continue

            param_privacy = getattr(recent_param, privacy_attr, 'private')

            if not can_see_parameter(param_privacy, watcher_circle):
                db.session.delete(alert)
                removed_count += 1
                removed_by_user[watcher_id] = removed_by_user.get(watcher_id, 0) + 1
            else:
                kept_count += 1

        db.session.commit()

        # Build user breakdown
        user_breakdown = []
        for uid, count in removed_by_user.items():
            user = db.session.get(User, uid)
            if user:
                user_breakdown.append({
                    'username': user.username,
                    'removed': count
                })

        return jsonify({
            'success': True,
            'message': 'Global privacy cleanup completed',
            'total_checked': total_checked,
            'removed': removed_count,
            'kept': kept_count,
            'affected_users': len(removed_by_user),
            'breakdown': user_breakdown
        })

    except Exception as e:
        logger.error(f"Global cleanup error: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def calculate_streak(params):
    """Calculate consecutive days streak"""
    if not params:
        return 0

    dates = sorted([p.date for p in params], reverse=True)
    streak = 1
    today = datetime.now().date()

    # Check if most recent date is today or yesterday
    if dates[0] < today - timedelta(days=1):
        return 0

    for i in range(1, len(dates)):
        if (dates[i - 1] - dates[i]).days == 1:
            streak += 1
        else:
            break

    return streak


# =====================
# ACTIVITY ROUTES (Calendar Feature)
# =====================

@app.route('/api/activity/<date_str>')
@login_required
def get_activity(date_str):
    """Get activity data for specific date"""
    try:
        user_id = session['user_id']

        # Parse date
        try:
            activity_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Invalid date format'}), 400

        # Get activity record
        activity_stmt = select(Activity).filter_by(
            user_id=user_id,
            activity_date=activity_date
        )
        activity = db.session.execute(activity_stmt).scalar_one_or_none()

        if not activity:
            return jsonify({
                'date': date_str,
                'post_count': 0,
                'comment_count': 0,
                'message_count': 0,
                'mood_entries': []
            })

        return jsonify({
            'date': date_str,
            'post_count': activity.post_count or 0,
            'comment_count': activity.comment_count or 0,
            'message_count': activity.message_count or 0,
            'mood_entries': activity.mood_entries or []
        })

    except Exception as e:
        logger.error(f"Get activity error: {str(e)}")
        return jsonify({'error': 'Failed to get activity'}), 500


@app.route('/api/activity/<date_str>', methods=['POST'])
@login_required
def update_activity(date_str):
    """Update activity data for specific date"""
    try:
        user_id = session['user_id']
        data = request.json

        # Parse date
        try:
            activity_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Invalid date format'}), 400

        # Get or create activity
        activity_stmt = select(Activity).filter_by(
            user_id=user_id,
            activity_date=activity_date
        )
        activity = db.session.execute(activity_stmt).scalar_one_or_none()

        if not activity:
            activity = Activity(
                user_id=user_id,
                activity_date=activity_date
            )
            db.session.add(activity)

        # Update fields
        if 'mood_entry' in data:
            mood_entries = activity.mood_entries or []
            mood_entries.append({
                'mood': data['mood_entry'].get('mood'),
                'note': data['mood_entry'].get('note'),
                'timestamp': datetime.utcnow().isoformat()
            })
            activity.mood_entries = mood_entries

        if 'post_count' in data:
            activity.post_count = data['post_count']
        if 'comment_count' in data:
            activity.comment_count = data['comment_count']
        if 'message_count' in data:
            activity.message_count = data['message_count']

        activity.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify({'success': True, 'message': 'Activity updated'})

    except Exception as e:
        logger.error(f"Update activity error: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Failed to update activity'}), 500


@app.route('/api/activity/dates')
@login_required
def get_activity_dates():
    """Get dates with activity data"""
    try:
        user_id = session['user_id']
        # SQLAlchemy 2.0 style
        activities_stmt = select(Activity).filter_by(user_id=user_id)
        activities = db.session.execute(activities_stmt).scalars().all()
        dates = [a.activity_date.strftime('%Y-%m-%d') for a in activities]
        return jsonify({'dates': dates})
    except Exception as e:
        logger.error(f"Get activity dates error: {str(e)}")
        return jsonify({'dates': []})


# =====================
# ADMIN ROUTES
# =====================

@app.route('/api/admin/users')
@admin_required
def admin_get_users():
    """Get all users (admin only)"""
    try:
        # SQLAlchemy 2.0 style
        users_stmt = select(User).order_by(desc(User.created_at))
        users = db.session.execute(users_stmt).scalars().all()

        return jsonify([{
            'id': u.id,
            'username': u.username,
            'email': u.email,
            'role': u.role,
            'is_active': u.is_active,
            'created_at': u.created_at.isoformat()
        } for u in users])

    except Exception as e:
        logger.error(f"Admin get users error: {str(e)}")
        return jsonify({'error': 'Failed to get users'}), 500


@app.route('/api/admin/stats')
@admin_required
def admin_stats():
    """Get platform statistics"""
    try:
        # SQLAlchemy 2.0 style
        total_users = db.session.execute(select(func.count(User.id))).scalar() or 0
        total_posts = db.session.execute(select(func.count(Post.id))).scalar() or 0
        total_messages = db.session.execute(select(func.count(Message.id))).scalar() or 0

        # Active users today
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        active_stmt = select(func.count(User.id)).filter(
            User.last_login >= today_start
        )
        active_users_today = db.session.execute(active_stmt).scalar() or 0

        return jsonify({
            'total_users': total_users,
            'total_posts': total_posts,
            'total_messages': total_messages,
            'active_users_today': active_users_today
        })

    except Exception as e:
        logger.error(f"Admin stats error: {str(e)}")
        return jsonify({'error': 'Failed to get stats'}), 500


# =====================
# SAMPLE DATA ROUTE
# =====================

@app.route('/api/setup/sample-users', methods=['POST'])
def create_sample_users():
    """Create sample users for testing"""
    if is_production:
        return jsonify({'error': 'Not available in production'}), 403

    try:
        sample_users = [
            {'username': 'alice_wonder', 'email': 'alice@example.com', 'name': 'Alice Wonder'},
            {'username': 'bob_builder', 'email': 'bob@example.com', 'name': 'Bob Builder'},
            {'username': 'charlie_day', 'email': 'charlie@example.com', 'name': 'Charlie Day'},
            {'username': 'diana_prince', 'email': 'diana@example.com', 'name': 'Diana Prince'},
            {'username': 'edward_snow', 'email': 'edward@example.com', 'name': 'Edward Snow'},
            {'username': 'fiona_green', 'email': 'fiona@example.com', 'name': 'Fiona Green'}
        ]

        created = []
        for user_data in sample_users:
            # Check if exists - SQLAlchemy 2.0 style
            existing_stmt = select(User).filter_by(email=user_data['email'])
            if db.session.execute(existing_stmt).scalar_one_or_none():
                continue

            user = User(
                username=user_data['username'],
                email=user_data['email']
            )
            user.set_password('password123')
            db.session.add(user)
            db.session.flush()

            # Create profile
            profile = Profile(
                user_id=user.id,
                bio=f"Hi, I'm {user_data['name']}!",
                interests='Reading, Travel, Technology',
                occupation='Professional',
                goals='Connect with interesting people',
                favorite_hobbies='Hiking, Photography, Cooking'
            )
            db.session.add(profile)
            created.append(user_data['username'])

        db.session.commit()

        return jsonify({
            'success': True,
            'created': created,
            'message': f'Created {len(created)} sample users with default password: password123'
        })

    except Exception as e:
        logger.error(f"Create sample users error: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Failed to create sample users'}), 500


# =====================
# CITY/TIMEZONE ROUTES
# =====================

@app.route('/api/user/city', methods=['GET', 'POST'])
@login_required
def user_city():
    """Get or update user's selected city"""
    user_id = session.get('user_id')
    user = db.session.get(User, user_id)

    if not user:
        return jsonify({'error': 'User not found'}), 404

    if request.method == 'GET':
        return jsonify({
            'selected_city': user.selected_city or 'Jerusalem, Israel'
        })

    elif request.method == 'POST':
        try:
            data = request.json
            city = data.get('selected_city')

            # List of valid cities
            valid_cities = [
                'Jerusalem, Israel', 'Tokyo, Japan', 'Delhi, India', 'Shanghai, China',
                'Mexico City, Mexico', 'São Paulo, Brazil', 'Cairo, Egypt',
                'Dhaka, Bangladesh', 'Beijing, China', 'Mumbai, India',
                'Osaka, Japan', 'Karachi, Pakistan', 'Chongqing, China',
                'Kinshasa, DR Congo', 'New York City, USA', 'Istanbul, Turkey',
                'London, United Kingdom', 'Paris, France', 'Buenos Aires, Argentina',
                'Moscow, Russia', 'Seoul, South Korea', 'Hong Kong, China',
                'Dubai, UAE', 'Sydney, Australia', 'Singapore, Singapore',
                'Los Angeles, USA', 'Chicago, USA', 'Melbourne, Australia',
                'Berlin, Germany', 'Madrid, Spain', 'Rome, Italy',
                'Bangkok, Thailand', 'Jakarta, Indonesia', 'Tehran, Iran',
                'Lagos, Nigeria', 'Rio de Janeiro, Brazil', 'Vancouver, Canada',
                'Amsterdam, Netherlands', 'Washington, USA', 'Houston, USA'
            ]

            if city not in valid_cities:
                return jsonify({'error': 'Invalid city'}), 400

            user.selected_city = city
            user.updated_at = datetime.utcnow()
            db.session.commit()

            return jsonify({
                'success': True,
                'selected_city': user.selected_city
            })
        except Exception as e:
            logger.error(f"City update error: {str(e)}")
            db.session.rollback()
            return jsonify({'error': 'Failed to update city'}), 500


# =====================
# FOLLOWING/FOLLOWERS ROUTES
# =====================
@app.route('/api/follow/<int:user_id>', methods=['POST'])
@login_required
def follow_user(user_id):
    """Follow another user with optional note and trigger"""
    try:
        current_user_id = session.get('user_id')
        current_user = db.session.get(User, current_user_id)
        user_to_follow = db.session.get(User, user_id)

        # Use get_json(silent=True) to handle missing JSON body
        data = request.get_json(silent=True) or {}
        # Support both 'note' and 'follow_note' keys for compatibility
        follow_note = (data.get('note') or data.get('follow_note') or '').strip()[:300] if data else ''
        follow_trigger = data.get('trigger', False) if data else False

        if not user_to_follow:
            return jsonify({'error': 'User not found'}), 404

        if current_user_id == user_id:
            return jsonify({'error': 'Cannot follow yourself'}), 400

        # Check if already following
        existing = Follow.query.filter_by(
            follower_id=current_user_id,
            followed_id=user_id
        ).first()

        if existing:
            # Update existing follow with note
            if hasattr(existing, 'follow_note'):
                existing.follow_note = follow_note
            # Add trigger support if your Follow model has this field
            if hasattr(existing, 'follow_trigger'):
                existing.follow_trigger = follow_trigger
            db.session.commit()
            return jsonify({'success': True, 'message': 'Follow updated'}), 200

        # Create new follow
        current_user.follow(user_to_follow, note=follow_note)

        # Update the newly created follow record with note if model supports it
        follow = Follow.query.filter_by(
            follower_id=current_user_id,
            followed_id=user_id
        ).first()

        if follow:
            if hasattr(follow, 'follow_note'):
                follow.follow_note = follow_note
            if hasattr(follow, 'follow_trigger'):
                follow.follow_trigger = follow_trigger

        db.session.commit()

        # Create alert for followed user
        alert_content = 'You have a new follower!'
        if follow_note:
            alert_content += f' They said: "{follow_note}"'
        if follow_trigger:
            alert_content += ' (Following your parameters)'

        alert = Alert(
            user_id=user_id,
            title=f'{current_user.username} started following you',
            content=alert_content,
            alert_type='info'
        )
        db.session.add(alert)

        if follow_note:
            message = Message(
                sender_id=current_user_id,
                recipient_id=user_id,
                content=f"Follow note: {follow_note}"
            )
            db.session.add(message)

        db.session.commit()
        return jsonify({'success': True, 'message': 'User followed'})

    except Exception as e:
        logger.error(f"Follow error: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        db.session.rollback()
        return jsonify({'error': 'Failed to follow user'}), 500


@app.route('/api/unfollow/<int:user_id>', methods=['POST'])
@login_required
def unfollow_user(user_id):
    """Unfollow a user"""
    try:
        current_user_id = session.get('user_id')
        current_user = db.session.get(User, current_user_id)
        user_to_unfollow = db.session.get(User, user_id)

        if not user_to_unfollow:
            return jsonify({'error': 'User not found'}), 404

        current_user.unfollow(user_to_unfollow)
        db.session.commit()

        return jsonify({'success': True, 'message': 'User unfollowed'})

    except Exception as e:
        logger.error(f"Unfollow error: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Failed to unfollow user'}), 500


@app.route('/api/following')
@login_required
@rate_limit_endpoint(max_requests=60, window=60)  # 60 requests per minute
def get_following():
    """Get list of users the current user is following with pagination"""
    try:
        user_id = session.get('user_id')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)

        # Limit per_page to prevent abuse
        per_page = min(per_page, 100)

        # Get total count for pagination
        total = db.session.execute(
            select(func.count()).select_from(Follow).filter_by(follower_id=user_id)
        ).scalar()

        # Get follows directly from Follow model with pagination
        follows_query = select(Follow).filter_by(follower_id=user_id).limit(per_page).offset((page - 1) * per_page)
        follows = db.session.execute(follows_query).scalars().all()

        following = []
        for follow in follows:
            followed_user = db.session.get(User, follow.followed_id)
            if followed_user:
                following.append({
                    'id': followed_user.id,
                    'username': followed_user.username,
                    'email': followed_user.email,
                    'note': follow.follow_note,  # ADD THIS FIELD
                    'selected_city': followed_user.selected_city,
                    'created_at': follow.created_at.isoformat()
                })

        return jsonify({
            'following': following,
            'page': page,
            'per_page': per_page,
            'total': total,
            'pages': (total + per_page - 1) // per_page
        })

    except Exception as e:
        logger.error(f"Get following error: {str(e)}")
        return jsonify({'error': 'Failed to get following'}), 500


@app.route('/api/parameters/user/<int:user_id>', methods=['GET'])
@login_required
def get_user_parameters_for_triggers(user_id):
    """Get parameters for viewing in trigger modal"""
    try:
        viewer_id = session.get('user_id')

        # Check if following
        if viewer_id != user_id:
            follow = Follow.query.filter_by(
                follower_id=viewer_id,
                followed_id=user_id
            ).first()
            if not follow:
                return jsonify({'error': 'Not authorized'}), 403

        # Get last 30 days
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)

        parameters = SavedParameters.query.filter(
            SavedParameters.user_id == user_id,
            SavedParameters.date >= thirty_days_ago
        ).order_by(SavedParameters.date.desc()).all()

        result = {'parameters': []}
        for param in parameters:
            # Add each parameter as separate entry
            for param_name in ['mood', 'energy', 'sleep_quality', 'physical_activity', 'anxiety']:
                value = getattr(param, param_name, None)
                if value:
                    result['parameters'].append({
                        'date': param.date.isoformat() if hasattr(param.date, 'isoformat') else str(param.date),
                        'parameter_name': param_name,
                        'value': value
                    })

        return jsonify(result), 200

    except Exception as e:
        logger.error(f"Error getting user parameters: {e}")
        return jsonify({'error': 'Failed to load parameters'}), 500


@app.route('/api/followers')
@login_required
@rate_limit_endpoint(max_requests=60, window=60)  # 60 requests per minute
def get_followers():
    """Get list of users following the current user with pagination"""
    try:
        user_id = session.get('user_id')
        user = db.session.get(User, user_id)
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)

        # Limit per_page to prevent abuse
        per_page = min(per_page, 100)

        # Get total count
        total = db.session.execute(
            select(func.count()).select_from(Follow).filter_by(followed_id=user_id)
        ).scalar()

        # Get followers with pagination
        follows_query = select(Follow).filter_by(followed_id=user_id).limit(per_page).offset((page - 1) * per_page)
        follows = db.session.execute(follows_query).scalars().all()

        followers = []
        for follow in follows:
            follower_user = db.session.get(User, follow.follower_id)
            if follower_user:
                followers.append({
                    'id': follower_user.id,
                    'username': follower_user.username,
                    'email': follower_user.email,
                    'selected_city': follower_user.selected_city,
                    'created_at': follow.created_at.isoformat(),
                    'is_following_back': user.is_following(follower_user)
                })

        return jsonify({
            'followers': followers,
            'page': page,
            'per_page': per_page,
            'total': total,
            'pages': (total + per_page - 1) // per_page
        })

    except Exception as e:
        logger.error(f"Get followers error: {str(e)}")
        return jsonify({'error': 'Failed to get followers'}), 500


@app.route('/api/recommendations')
@login_required
def get_recommendations():
    """Get follow recommendations prioritizing same city, then common connections"""
    try:
        user_id = session.get('user_id')
        user = db.session.get(User, user_id)

        if not user:
            return jsonify({'recommendations': []}), 200

        recommendations = []
        seen_ids = set()

        # PRIORITY 1: Users in same city (only if user has selected a city)
        if user.selected_city:
            same_city_users = User.query.filter(
                User.selected_city == user.selected_city,
                User.id != user_id,
                User.is_active == True
            ).limit(15).all()

            for city_user in same_city_users:
                if not user.is_following(city_user) and city_user.id not in seen_ids:
                    seen_ids.add(city_user.id)
                    recommendations.append({
                        'id': city_user.id,
                        'username': city_user.username,
                        'email': city_user.email,
                        'selected_city': city_user.selected_city,
                        'reason': 'Same city'
                    })

        # PRIORITY 2: Friends of friends (only if not enough same-city users)
        if len(recommendations) < 20:
            # Get users from circles
            circle_users = db.session.execute(
                select(Circle.circle_user_id).filter_by(user_id=user_id)
            ).scalars().all()

            # Get friends of friends
            for circle_user_id in circle_users:
                if len(recommendations) >= 20:
                    break

                their_circles = db.session.execute(
                    select(Circle.circle_user_id).filter_by(
                        user_id=circle_user_id
                    ).filter(Circle.circle_user_id != user_id)
                ).scalars().all()

                for potential_id in their_circles[:5]:
                    if len(recommendations) >= 20:
                        break

                    if potential_id in seen_ids:
                        continue

                    potential_user = db.session.get(User, potential_id)
                    if potential_user and not user.is_following(potential_user):
                        seen_ids.add(potential_user.id)

                        # Check if also same city for enhanced reason
                        reason = 'Friend of friend'
                        if potential_user.selected_city == user.selected_city:
                            reason = 'Same city & friend of friend'

                        recommendations.append({
                            'id': potential_user.id,
                            'username': potential_user.username,
                            'email': potential_user.email,
                            'selected_city': potential_user.selected_city,
                            'reason': reason
                        })

        return jsonify({'recommendations': recommendations[:20]})

    except Exception as e:
        logger.error(f"Get recommendations error: {str(e)}")
        return jsonify({'error': 'Failed to get recommendations'}), 500


# ADD THESE TWO ENDPOINTS TO app.py AFTER LINE 4235
# (Right after the existing get_recommendations() function)

@app.route('/api/users/recommendations', methods=['GET'])
@login_required
def get_user_recommendations():
    """Get recommended users to INVITE to follow YOU (not people for you to follow)"""
    try:
        # Set query timeout to prevent hanging (PostgreSQL only)
        try:
            db.session.execute(text("SET LOCAL statement_timeout = '5000'"))
        except Exception:
            pass  # Ignore if not PostgreSQL

        user_id = session.get('user_id')
        current_user = db.session.get(User, user_id)

        if not current_user:
            return jsonify({
                'error': 'User not found',
                'recommendations': [],
                'count': 0
            }), 200

        # Get IDs of users who are ALREADY FOLLOWING ME (my current followers)
        # These should be EXCLUDED because they're already following me
        my_followers = []
        try:
            my_followers = db.session.execute(
                select(Follow.follower_id).filter_by(followed_id=user_id)
            ).scalars().all()
        except Exception as e:
            logger.warning(f"Followers query failed: {e}")

        # Get pending follow requests I RECEIVED
        # These should be EXCLUDED because they already want to follow me
        received_requests = []
        try:
            received_requests = db.session.execute(
                select(FollowRequest.requester_id).filter_by(
                    target_id=user_id,
                    status='pending'
                )
            ).scalars().all()
        except Exception as e:
            logger.warning(f"Received requests query failed: {e}")

        # Get pending follow requests I SENT
        # These should be EXCLUDED because I already invited them
        sent_requests = []
        try:
            sent_requests = db.session.execute(
                select(FollowRequest.target_id).filter_by(
                    requester_id=user_id,
                    status='pending'
                )
            ).scalars().all()
        except Exception as e:
            logger.warning(f"Sent requests query failed: {e}")

        # Exclude: myself, people already following me, people who sent me requests, and people I sent requests to
        exclude_ids = set(my_followers + received_requests + sent_requests + [user_id])

        logger.info(f"User {user_id} ({current_user.username}) invite recommendations - "
                    f"excluding {len(exclude_ids)} users: "
                    f"followers={len(my_followers)}, received_requests={len(received_requests)}, sent_requests={len(sent_requests)}")

        # Get users with similar location (potential people to invite)
        location_matches = []
        try:
            if hasattr(current_user, 'selected_city') and current_user.selected_city:
                location_matches = db.session.execute(
                    select(User).filter(
                        User.selected_city == current_user.selected_city,
                        ~User.id.in_(exclude_ids)
                    ).limit(10)
                ).scalars().all()
                logger.info(f"Found {len(location_matches)} location matches in "
                            f"{current_user.selected_city} for user {current_user.username}")
        except Exception as e:
            logger.warning(f"Location query failed: {e}")
            location_matches = []

        # Get recently active users (potential people to invite)
        recent_users = []
        try:
            recent_users = db.session.execute(
                select(User).filter(
                    ~User.id.in_(exclude_ids)
                ).order_by(User.created_at.desc()).limit(10)
            ).scalars().all()
            logger.info(f"Found {len(recent_users)} recent users for user {current_user.username}")
        except Exception as e:
            logger.warning(f"Recent users query failed: {e}")
            recent_users = []

        # Combine and deduplicate
        all_recommendations = []
        seen_ids = set()

        for user_list in [location_matches, recent_users]:
            for user in user_list:
                if user.id not in seen_ids:
                    seen_ids.add(user.id)
                    all_recommendations.append({
                        'id': user.id,
                        'username': user.username,
                        'location': getattr(user, 'selected_city', None)
                    })

        # Limit to 20 recommendations
        all_recommendations = all_recommendations[:20]

        logger.info(f"Returning {len(all_recommendations)} recommendations for user "
                    f"{current_user.username}: {[r['username'] for r in all_recommendations]}")

        return jsonify({
            'recommendations': all_recommendations,
            'count': len(all_recommendations)
        })

    except Exception as e:
        logger.error(f"Recommendations error: {str(e)}")
        return jsonify({
            'error': 'Failed to load recommendations',
            'recommendations': [],
            'count': 0
        }), 200


@app.route('/invite/<username>')
def public_invite_page(username):
    """Public invite page for a user - accessible without login"""
    try:
        # Find user by username
        user = db.session.execute(
            select(User).filter_by(username=username)
        ).scalar_one_or_none()

        if not user:
            return render_template('invite_not_found.html'), 404

        # Get user's public stats
        follower_count = db.session.execute(
            select(func.count(Follow.id)).filter_by(followed_id=user.id)
        ).scalar()

        following_count = db.session.execute(
            select(func.count(Follow.id)).filter_by(follower_id=user.id)
        ).scalar()

        # Check if current user is logged in
        current_user_id = session.get('user_id')
        is_logged_in = current_user_id is not None

        # Check follow status if logged in
        already_following = False
        pending_request = False

        if is_logged_in:
            # Check if already following
            follow_exists = db.session.execute(
                select(Follow).filter_by(
                    follower_id=current_user_id,
                    followed_id=user.id
                )
            ).scalar_one_or_none()

            already_following = follow_exists is not None

            # Check for pending request
            request_exists = db.session.execute(
                select(FollowRequest).filter_by(
                    requester_id=current_user_id,
                    target_id=user.id,
                    status='pending'
                )
            ).scalar_one_or_none()

            pending_request = request_exists is not None

        return render_template('invite.html',
                               invite_user=user,
                               follower_count=follower_count,
                               following_count=following_count,
                               is_logged_in=is_logged_in,
                               already_following=already_following,
                               pending_request=pending_request
                               )

    except Exception as e:
        logger.error(f"Invite page error: {str(e)}")
        return render_template('invite_error.html'), 500


@app.route('/api/user/<int:user_id>/feed/<date_str>')
@login_required
def get_user_feed(user_id, date_str):
    """Get another user's feed for a specific date (read-only with circle permissions)"""
    try:
        current_user_id = session.get('user_id')
        current_user = db.session.get(User, current_user_id)

        # Check if following or is self
        target_user = db.session.get(User, user_id)
        if not target_user:
            return jsonify({'error': 'User not found'}), 404

        if user_id != current_user_id and not current_user.is_following(target_user):
            return jsonify({'error': 'You must follow this user to view their feed'}), 403

        post = Post.query.filter_by(user_id=user_id).filter(
            db.func.date(Post.created_at) == date_str
        ).first()

        if not post:
            return jsonify({'content': '', 'date': date_str})

        # Check circle permission if viewing another user's post
        if user_id != current_user_id:
            post_visibility = post.visibility if post.visibility else 'general'

            if post_visibility == 'family':
                # Must be in family circle
                in_circle = Circle.query.filter_by(
                    user_id=user_id,
                    circle_user_id=current_user_id,
                    circle_type='family'
                ).first() is not None

                if not in_circle:
                    return jsonify({'error': 'This post is only visible to family members'}), 403

            elif post_visibility == 'close_friends':
                # Must be in family OR close_friends circle
                in_circle = Circle.query.filter(
                    Circle.user_id == user_id,
                    Circle.circle_user_id == current_user_id,
                    Circle.circle_type.in_(['family', 'close_friends'])
                ).first() is not None

                if not in_circle:
                    return jsonify({'error': 'This post is only visible to close friends'}), 403

        return jsonify({
            'content': post.content,
            'date': date_str,
            'visibility': post.visibility if post.visibility else 'general',
            'updated_at': post.updated_at.isoformat() if post.updated_at else None
        })

    except Exception as e:
        logger.error(f"Get user feed error: {str(e)}")
        return jsonify({'error': 'Failed to get feed'}), 500


@app.route('/api/user/<int:user_id>/parameters/<date_str>')
@login_required
def get_user_parameters_by_date(user_id, date_str):
    """Get another user's parameters for a specific date (read-only)"""
    try:
        current_user_id = session.get('user_id')
        current_user = db.session.get(User, current_user_id)

        # Check if following or is self
        target_user = db.session.get(User, user_id)
        if not target_user:
            return jsonify({'error': 'User not found'}), 404

        if user_id != current_user_id and not current_user.is_following(target_user):
            return jsonify({'error': 'You must follow this user to view their parameters'}), 403

        params = SavedParameters.query.filter_by(
            user_id=user_id,
            date=date_str
        ).first()

        if params:
            return jsonify({
                'success': True,
                'data': {
                    'parameters': {
                        'mood': params.mood,
                        'energy': params.energy,
                        'sleep_quality': params.sleep_quality,
                        'physical_activity': params.physical_activity,
                        'anxiety': params.anxiety
                    },
                    'notes': params.notes or ''
                }
            })
        else:
            return jsonify({'success': False, 'message': 'No parameters for this date'})

    except Exception as e:
        logger.error(f"Get user parameters error: {str(e)}")
        return jsonify({'error': 'Failed to get parameters'}), 500


@app.route('/api/follow-requests', methods=['POST'])
@login_required
def create_follow_request():
    try:
        data = request.get_json()
        requester_id = session.get('user_id')
        target_id = data.get('target_id')

        if not target_id or requester_id == target_id:
            return jsonify({'error': 'Invalid target'}), 400

        existing = FollowRequest.query.filter_by(
            requester_id=requester_id,
            target_id=target_id
        ).first()

        if existing:
            if existing.status == 'pending':
                return jsonify({'error': 'Request already pending'}), 400
            existing.status = 'pending'
            existing.created_at = datetime.utcnow()
        else:
            existing = FollowRequest(
                requester_id=requester_id,
                target_id=target_id
            )
            db.session.add(existing)

        db.session.commit()

        # Create alert
        requester = db.session.get(User, requester_id)
        requester_username = requester.username if requester else "Someone"

        alert = Alert(
            user_id=target_id,
            title="invite.alert_title",
            content=f"{requester_username}|invite.alert_content",
            alert_type='follow_request'
        )
        db.session.add(alert)
        db.session.commit()

        return jsonify({'message': 'Follow request sent'}), 200

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Failed'}), 500


@app.route('/api/follow-requests/received', methods=['GET'])
@login_required
def get_received_follow_requests():
    user_id = session.get('user_id')
    requests = FollowRequest.query.filter_by(
        target_id=user_id,
        status='pending'
    ).all()

    return jsonify({
        'requests': [{
            'id': req.id,
            'requester_id': req.requester_id,
            'requester_name': req.requester.username,
            'created_at': req.created_at.isoformat()
        } for req in requests]
    })


@app.route('/api/follow-requests/<int:request_id>/respond', methods=['POST'])
@login_required
def respond_to_follow_request(request_id):
    try:
        data = request.get_json()
        user_id = session.get('user_id')
        action = data.get('action')
        privacy_level = data.get('privacy_level', 'public')

        follow_request = FollowRequest.query.get(request_id)

        if not follow_request or follow_request.target_id != user_id:
            return jsonify({'error': 'Not found'}), 404

        if follow_request.status != 'pending':
            return jsonify({'error': 'Already processed'}), 400

        if action == 'accept':
            follow_request.status = 'accepted'
            follow_request.privacy_level = privacy_level
            follow_request.responded_at = datetime.utcnow()

            follow = Follow(
                follower_id=follow_request.requester_id,
                followed_id=follow_request.target_id
            )
            db.session.add(follow)

        elif action == 'reject':
            follow_request.status = 'rejected'
            follow_request.responded_at = datetime.utcnow()

        db.session.commit()
        return jsonify({'message': f'Request {action}ed'}), 200

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Failed'}), 500


@app.route('/api/triggers', methods=['GET'])
@login_required
def get_triggers():
    user_id = session.get('user_id')
    triggers = ParameterTrigger.query.filter_by(
        watcher_id=user_id,
        is_active=True
    ).all()

    return jsonify({
        'triggers': [{
            'id': t.id,
            'watched_user': t.watched.username,
            'parameter': t.parameter_name,
            'condition': t.trigger_condition,
            'value': t.trigger_value,
            'consecutive_days': t.consecutive_days
        } for t in triggers]
    })


@app.route('/api/triggers', methods=['POST'])
@login_required
def create_trigger():
    try:
        data = request.get_json()
        trigger = ParameterTrigger(
            watcher_id=session.get('user_id'),
            watched_id=data.get('watched_id'),
            parameter_name=data.get('parameter_name'),
            trigger_condition=data.get('condition'),
            trigger_value=data.get('value'),
            consecutive_days=data.get('consecutive_days')
        )
        db.session.add(trigger)
        db.session.commit()
        return jsonify({'message': 'Trigger created'}), 201
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Failed'}), 500


@app.route('/api/triggers/<int:trigger_id>', methods=['DELETE'])
@login_required
def delete_trigger(trigger_id):
    trigger = ParameterTrigger.query.get(trigger_id)
    if trigger and trigger.watcher_id == session.get('user_id'):
        trigger.is_active = False
        db.session.commit()
        return jsonify({'message': 'Deleted'}), 200
    return jsonify({'error': 'Not found'}), 404


@app.route('/api/users/shareable-link', methods=['GET'])
@login_required
def get_shareable_link():
    user = User.query.get(session.get('user_id'))

    if not user.shareable_link_token:
        import uuid
        user.shareable_link_token = str(uuid.uuid4())
        db.session.commit()

    base_url = request.host_url.rstrip('/')
    shareable_link = f"{base_url}/profile/{user.shareable_link_token}"

    return jsonify({'link': shareable_link})


@app.route('/api/profile/<token>', methods=['GET'])
def get_profile_by_token(token):
    user = User.query.filter_by(shareable_link_token=token).first()
    if not user:
        return jsonify({'error': 'Not found'}), 404
    return jsonify({'display_name': user.username, 'id': user.id})


# =====================
# ERROR HANDLERS
# =====================

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Not found'}), 404
    return jsonify({'error': 'Page not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    db.session.rollback()
    logger.error(f"Internal error: {str(error)}")
    return jsonify({'error': 'Internal server error'}), 500


# =====================
# CLI COMMANDS
# =====================

@app.cli.command()
def init_db():
    """Initialize the database"""
    db.create_all()  # Let SQLAlchemy create from models.py

    # Only do migration for existing data
    with app.app_context():
        db_conn = get_db()
        try:
            migrate_parameters_data(db_conn)  # Use your migration function
        except:
            pass  # New installation, no migration needed

    print("Database initialized.")


def migrate_parameters_data(db):
    """Migrate existing text-based parameters to numeric values"""
    try:
        # Migrate mood from text to numeric
        db.execute('''
            UPDATE parameters 
            SET mood = CASE 
                WHEN mood = 'very_bad' OR mood = '1' THEN 1
                WHEN mood = 'bad' OR mood = '2' THEN 2
                WHEN mood IN ('ok', 'neutral', '3', 'moderate') THEN 3
                WHEN mood IN ('good', '4', 'excellent') THEN 4
                WHEN CAST(mood AS INTEGER) BETWEEN 1 AND 4 THEN CAST(mood AS INTEGER)
                ELSE NULL
            END
            WHERE mood IS NOT NULL AND typeof(mood) = 'text'
        ''')

        # Migrate exercise to physical_activity
        db.execute('''
            UPDATE parameters 
            SET physical_activity = CASE 
                WHEN exercise IN ('none', '1', 'no') THEN 1
                WHEN exercise IN ('light', '2', 'mild') THEN 2
                WHEN exercise IN ('moderate', '3', 'medium') THEN 3
                WHEN exercise IN ('intense', 'high', '4', 'heavy') THEN 4
                WHEN CAST(exercise AS INTEGER) BETWEEN 1 AND 4 THEN CAST(exercise AS INTEGER)
                ELSE exercise
            END
            WHERE exercise IS NOT NULL
        ''')

        # Migrate anxiety from text to numeric
        db.execute('''
            UPDATE parameters 
            SET anxiety = CASE 
                WHEN anxiety IN ('none', '1', 'no') THEN 1
                WHEN anxiety IN ('low', 'mild', '2') THEN 2
                WHEN anxiety IN ('moderate', '3', 'medium') THEN 3
                WHEN anxiety IN ('high', 'severe', '4') THEN 4
                WHEN CAST(anxiety AS INTEGER) BETWEEN 1 AND 4 THEN CAST(anxiety AS INTEGER)
                ELSE NULL
            END
            WHERE anxiety IS NOT NULL AND typeof(anxiety) = 'text'
        ''')

        # Handle old energy column - ensure it's numeric
        db.execute('''
            UPDATE parameters 
            SET energy = CASE 
                WHEN energy IN ('very_low', '1') THEN 1
                WHEN energy IN ('low', '2') THEN 2
                WHEN energy IN ('moderate', '3', 'medium', 'ok') THEN 3
                WHEN energy IN ('high', '4', 'good') THEN 4
                WHEN CAST(energy AS INTEGER) BETWEEN 1 AND 4 THEN CAST(energy AS INTEGER)
                ELSE NULL
            END
            WHERE energy IS NOT NULL AND typeof(energy) = 'text'
        ''')

        # Convert sleep_hours to sleep_quality if needed
        cursor = db.execute("PRAGMA table_info(parameters)")
        columns = [row[1] for row in cursor.fetchall()]

        if 'sleep_hours' in columns:
            db.execute('''
                UPDATE parameters 
                SET sleep_quality = CASE 
                    WHEN sleep_hours <= 4 THEN 1
                    WHEN sleep_hours > 4 AND sleep_hours <= 6 THEN 2
                    WHEN sleep_hours > 6 AND sleep_hours <= 8 THEN 3
                    WHEN sleep_hours > 8 THEN 4
                    ELSE NULL
                END
                WHERE sleep_hours IS NOT NULL AND sleep_quality IS NULL
            ''')

        db.commit()
        print("Parameters data migration completed successfully")
    except Exception as e:
        print(f"Error during migration: {e}")


@app.cli.command()
def fix_alerts():
    """Fix alerts table schema"""
    fix_alerts_table()
    print("Alerts table fixed.")


# =====================
# MAIN INITIALIZATION
# =====================

if __name__ == '__main__':
    # Initialize database
    init_database()
    migrate_circle_names()
    # data time

    # Get port from environment
    port = int(os.environ.get('PORT', 5000))

    # Run application
    logger.info(f"Starting Social Social Platform on port {port}")
    logger.info(f"Production mode: {is_production}")

    app.run(
        host='0.0.0.0',
        port=port,
        debug=not is_production
    )
else:
    # For production servers (gunicorn, etc.)
    init_database()