#!/usr/bin/env python
"""
Complete app.py for Social Social Platform
With Flask-Migrate and SQLAlchemy 2.0 style queries
Auto-migrates on startup for seamless deployment
"""

import os
import sys
import json
import uuid
import redis
import logging
from datetime import datetime, timedelta
from functools import wraps

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
    'pool_size': 10,
    'pool_recycle': 3600,
    'pool_pre_ping': True,
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
migrate = Migrate(app, db, render_as_batch=True)  # render_as_batch for SQLite compatibility
CORS(app, supports_credentials=True)
Session(app)

# Setup logging
logging.basicConfig(
    level=logging.INFO if is_production else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('thera_social')

# Initialize Redis client (optional, for caching)
try:
    redis_client = redis.from_url(REDIS_URL) if REDIS_URL else None
    if redis_client:
        redis_client.ping()
        logger.info("Redis connected successfully")
except Exception as e:
    redis_client = None
    logger.warning(f"Redis not available: {e}")


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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = db.Column(db.DateTime)

    # Relationships
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

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }


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
    circle_id = db.Column(db.Integer, db.ForeignKey('circles.id'))
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
    circle_type = db.Column(db.String(50))  # 'general', 'close_friends', 'family'
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
    date = db.Column(db.Date, index=True)
    mood = db.Column(db.String(100))
    sleep_hours = db.Column(db.Float)
    exercise = db.Column(db.String(100))
    anxiety = db.Column(db.String(100))
    energy = db.Column(db.String(100))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'date', name='_user_date_uc'),
    )


class Alert(db.Model):
    __tablename__ = 'alerts'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    title = db.Column(db.String(200))
    content = db.Column(db.Text)  # FIXED: Changed from 'message' to 'content'
    type = db.Column(db.String(50))  # 'info', 'warning', 'success', 'error'
    is_read = db.Column(db.Boolean, default=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'message': self.content,  # Return as 'message' for backward compatibility
            'type': self.type,
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
                logger.info("Database schema created successfully")
                create_admin_user()
            else:
                logger.info(f"Found {len(tables)} existing tables")

                # Fix all schema issues
                fix_all_schema_issues()

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

        except Exception as e:
            logger.error(f"Database initialization error: {e}")
            # Try to create tables as fallback
            try:
                db.create_all()
                logger.info("Created database tables as fallback")
                create_admin_user()
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
                        # SQLite doesn't support RENAME COLUMN in older versions
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

            # 2. Fix profiles table - add missing columns
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

            # 3. Ensure activities table exists
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

            # 4. Ensure comments table exists
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

            # 5. Ensure reactions table exists
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

            logger.info("✓ All schema fixes complete")

    except Exception as e:
        logger.error(f"Error in fix_all_schema_issues: {e}")
        # Don't fail the entire initialization for schema fixes
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
                type='success'
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
    return render_template('circles.html')


@app.route('/messages')
@login_required
def messages_page():
    """Messages page"""
    return render_template('messages.html')


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

        # Validation
        if not username or not email or not password:
            return jsonify({'error': 'All fields are required'}), 400

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
            email=email
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
            title='Welcome to Social Social!',
            content='Your account has been created successfully. Start by updating your profile.',
            type='success'
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

        return jsonify({
            'success': True,
            'user': user.to_dict()
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

        return jsonify({
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

        db.session.commit()
        return jsonify({'success': True, 'message': 'Profile updated'})


@app.route('/api/users/search')
@login_required
def search_users():
    """Search for users"""
    query = request.args.get('q', '')
    if len(query) < 2:
        return jsonify([])

    # SQLAlchemy 2.0 style
    stmt = select(User).filter(
        or_(
            User.username.ilike(f'%{query}%'),
            User.email.ilike(f'%{query}%')
        ),
        User.id != session.get('user_id'),
        User.is_active == True
    ).limit(20)

    users = db.session.execute(stmt).scalars().all()

    results = [{
        'id': u.id,
        'username': u.username,
        'email': u.email
    } for u in users]

    return jsonify(results)


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
        ).order_by(desc(Alert.created_at)).limit(10)

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
            # Get all messages - SQLAlchemy 2.0 style
            sent_stmt = select(Message).filter_by(sender_id=user_id).order_by(desc(Message.created_at)).limit(50)
            sent = db.session.execute(sent_stmt).scalars().all()

            received_stmt = select(Message).filter_by(recipient_id=user_id).order_by(desc(Message.created_at)).limit(50)
            received = db.session.execute(received_stmt).scalars().all()

            def format_message(msg):
                sender = db.session.get(User, msg.sender_id)
                recipient = db.session.get(User, msg.recipient_id)
                if sender and recipient:
                    return {
                        'id': msg.id,
                        'sender': {'id': sender.id, 'username': sender.username},
                        'recipient': {'id': recipient.id, 'username': recipient.username},
                        'content': msg.content,
                        'is_read': msg.is_read,
                        'created_at': msg.created_at.isoformat()
                    }
                return None

            return jsonify({
                'sent': [m for msg in sent if (m := format_message(msg))],
                'received': [m for msg in received if (m := format_message(msg))]
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

            # Create alert for recipient
            sender = db.session.get(User, user_id)
            alert = Alert(
                user_id=recipient_id,
                title=f'New message from {sender.username}',
                content=content[:100] + '...' if len(content) > 100 else content,
                type='info'
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


@app.route('/api/messages/<int:message_id>/read', methods=['PUT'])
@login_required
def mark_message_read(message_id):
    """Mark message as read"""
    try:
        user_id = session.get('user_id')
        message = db.session.get(Message, message_id)

        if not message:
            return jsonify({'error': 'Message not found'}), 404

        if message.recipient_id != user_id:
            return jsonify({'error': 'Unauthorized'}), 403

        message.is_read = True
        db.session.commit()

        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Mark message error: {str(e)}")
        return jsonify({'error': 'Failed to mark message'}), 500


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
            partner = db.session.get(User, partner_id)
            if partner:
                # Get last message - SQLAlchemy 2.0 style
                last_msg_stmt = select(Message).filter(
                    or_(
                        and_(Message.sender_id == user_id, Message.recipient_id == partner_id),
                        and_(Message.sender_id == partner_id, Message.recipient_id == user_id)
                    )
                ).order_by(desc(Message.created_at))

                last_message = db.session.execute(last_msg_stmt).scalar_one_or_none()

                # Count unread messages from this partner
                unread_stmt = select(func.count(Message.id)).filter_by(
                    sender_id=partner_id,
                    recipient_id=user_id,
                    is_read=False
                )
                unread_count = db.session.execute(unread_stmt).scalar() or 0

                conversations.append({
                    'user': {'id': partner.id, 'username': partner.username},
                    'last_message': {
                        'content': last_message.content if last_message else None,
                        'created_at': last_message.created_at.isoformat() if last_message else None,
                        'is_own': last_message.sender_id == user_id if last_message else False
                    },
                    'unread_count': unread_count,
                    'timestamp': last_message.created_at.isoformat() if last_message else None
                })

        # Sort by last message time
        conversations.sort(
            key=lambda x: x['timestamp'] if x['timestamp'] else '',
            reverse=True
        )

        return jsonify(conversations)

    except Exception as e:
        logger.error(f"Get conversations error: {str(e)}")
        return jsonify({'error': 'Failed to get conversations'}), 500


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
            # Get all circles - SQLAlchemy 2.0 style
            general_stmt = select(Circle).filter_by(user_id=user_id, circle_type='general')
            general = db.session.execute(general_stmt).scalars().all()

            close_friends_stmt = select(Circle).filter_by(user_id=user_id, circle_type='close_friends')
            close_friends = db.session.execute(close_friends_stmt).scalars().all()

            family_stmt = select(Circle).filter_by(user_id=user_id, circle_type='family')
            family = db.session.execute(family_stmt).scalars().all()

            def get_user_info(circle):
                user = db.session.get(User, circle.circle_user_id)
                if user:
                    return {
                        'id': user.id,
                        'username': user.username,
                        'email': user.email
                    }
                return None

            return jsonify({
                'general': [info for c in general if (info := get_user_info(c))],
                'close_friends': [info for c in close_friends if (info := get_user_info(c))],
                'family': [info for c in family if (info := get_user_info(c))]
            })

        except Exception as e:
            logger.error(f"Get circles error: {str(e)}")
            return jsonify({'error': 'Failed to get circles'}), 500

    elif request.method == 'POST':
        try:
            data = request.json
            circle_user_id = data.get('user_id')
            circle_type = data.get('circle_type')

            if circle_type not in ['general', 'close_friends', 'family']:
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
        circle_user_id = data.get('user_id')
        circle_type = data.get('circle_type')

        # SQLAlchemy 2.0 style
        circle_stmt = select(Circle).filter_by(
            user_id=user_id,
            circle_user_id=circle_user_id,
            circle_type=circle_type
        )
        circle = db.session.execute(circle_stmt).scalar_one_or_none()

        if circle:
            db.session.delete(circle)
            db.session.commit()
            return jsonify({'success': True})

        return jsonify({'error': 'Not found'}), 404

    except Exception as e:
        logger.error(f"Remove from circle error: {str(e)}")
        return jsonify({'error': 'Failed to remove from circle'}), 500


# =====================
# FEED & POSTS ROUTES
# =====================

@app.route('/api/feed', methods=['GET'])
@login_required
def get_feed():
    """Get user feed"""
    try:
        user_id = session['user_id']

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

        return jsonify({'posts': feed})

    except Exception as e:
        logger.error(f"Feed error: {str(e)}")
        return jsonify({'posts': []})


@app.route('/api/posts', methods=['POST'])
@login_required
def create_post():
    """Create a new post"""
    try:
        data = request.json
        content = sanitize_input(data.get('content', ''))

        if not content:
            return jsonify({'error': 'Content required'}), 400

        # Check content moderation
        moderation = content_moderator.check_content(content)
        if not moderation['safe']:
            return jsonify({'error': moderation.get('message', 'Content not allowed')}), 400

        post = Post(
            user_id=session['user_id'],
            content=content
        )
        db.session.add(post)

        # Update activity
        today = datetime.utcnow().date()
        activity_stmt = select(Activity).filter_by(
            user_id=session['user_id'],
            activity_date=today
        )
        activity = db.session.execute(activity_stmt).scalar_one_or_none()

        if not activity:
            activity = Activity(user_id=session['user_id'], activity_date=today)
            db.session.add(activity)

        activity.post_count = (activity.post_count or 0) + 1

        db.session.commit()

        return jsonify({'success': True, 'post_id': post.id})

    except Exception as e:
        logger.error(f"Post creation error: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Failed to create post'}), 500


# =====================
# PARAMETERS ROUTES (Therapy Companion)
# =====================

@app.route('/api/parameters', methods=['GET'])
@login_required
def get_parameters():
    """Get current parameters"""
    user_id = session['user_id']
    today = datetime.now().date()

    # SQLAlchemy 2.0 style
    params_stmt = select(SavedParameters).filter_by(
        user_id=user_id,
        date=today
    )
    params = db.session.execute(params_stmt).scalar_one_or_none()

    if params:
        return jsonify({
            'mood': params.mood or '',
            'sleep_hours': params.sleep_hours or 0,
            'exercise': params.exercise or '',
            'anxiety': params.anxiety or '',
            'energy': params.energy or '',
            'notes': params.notes or ''
        })

    return jsonify({
        'mood': '',
        'sleep_hours': 0,
        'exercise': '',
        'anxiety': '',
        'energy': '',
        'notes': ''
    })


@app.route('/api/parameters/save', methods=['POST'])
@login_required
def save_parameters():
    """Save daily parameters"""
    try:
        user_id = session.get('user_id')
        data = request.json

        date_str = data.get('date', str(datetime.now().date()))
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()

        # Check if parameters exist - SQLAlchemy 2.0 style
        params_stmt = select(SavedParameters).filter_by(
            user_id=user_id,
            date=date_obj
        )
        params = db.session.execute(params_stmt).scalar_one_or_none()

        if not params:
            params = SavedParameters(user_id=user_id, date=date_obj)
            db.session.add(params)

        # Save parameters
        params.mood = sanitize_input(data.get('mood', ''))
        params.sleep_hours = float(data.get('sleep_hours', 0))
        params.exercise = sanitize_input(data.get('exercise', ''))
        params.anxiety = sanitize_input(data.get('anxiety', ''))
        params.energy = sanitize_input(data.get('energy', ''))
        params.notes = sanitize_input(data.get('notes', ''))

        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Parameters saved for {date_str}'
        })

    except IntegrityError:
        db.session.rollback()
        return jsonify({'error': 'Failed to save parameters'}), 500
    except Exception as e:
        logger.error(f"Save parameters error: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Failed to save parameters'}), 500


@app.route('/api/parameters/load/<date>')
@login_required
def load_parameters(date):
    """Load parameters for specific date"""
    try:
        user_id = session.get('user_id')

        try:
            date_obj = datetime.strptime(date, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Invalid date format'}), 400

        # SQLAlchemy 2.0 style
        params_stmt = select(SavedParameters).filter_by(
            user_id=user_id,
            date=date_obj
        )
        params = db.session.execute(params_stmt).scalar_one_or_none()

        if params:
            return jsonify({
                'success': True,
                'data': {
                    'mood': params.mood or '',
                    'sleep_hours': params.sleep_hours or 0,
                    'sleep_display': f"{params.sleep_hours} Hours" if params.sleep_hours else "0 Hours",
                    'exercise': params.exercise or '',
                    'anxiety': params.anxiety or '',
                    'energy': params.energy or '',
                    'notes': params.notes or ''
                }
            })
        else:
            return jsonify({
                'success': False,
                'message': 'No saved parameters for this date'
            })

    except Exception as e:
        logger.error(f"Load parameters error: {str(e)}")
        return jsonify({'error': 'Failed to load parameters'}), 500


@app.route('/api/parameters/dates')
@login_required
def get_parameter_dates():
    """Get dates with saved parameters"""
    try:
        user_id = session.get('user_id')
        # SQLAlchemy 2.0 style
        params_stmt = select(SavedParameters).filter_by(user_id=user_id)
        params = db.session.execute(params_stmt).scalars().all()
        dates = [p.date.strftime('%Y-%m-%d') for p in params]
        return jsonify({'dates': dates})
    except Exception as e:
        logger.error(f"Get parameter dates error: {str(e)}")
        return jsonify({'dates': []})


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
    db.create_all()
    print("Database initialized.")


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