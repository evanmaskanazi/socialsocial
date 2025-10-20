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
    preferred_language = db.Column(db.String(5), default='en')
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
            'preferred_language': self.preferred_language or 'en',
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
                create_test_users()

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
            email=email,
            preferred_language='en'
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


@app.route('/api/user/language', methods=['GET', 'POST'])
@login_required
def user_language():
    """Get or update user's preferred language"""
    user_id = session.get('user_id')
    user = db.session.get(User, user_id)

    if not user:
        return jsonify({'error': 'User not found'}), 404

    if request.method == 'GET':
        return jsonify({
            'preferred_language': user.preferred_language or 'en'
        })

    elif request.method == 'POST':
        try:
            data = request.json
            language = data.get('preferred_language', 'en')

            # Validate language
            if language not in ['en', 'he', 'ar', 'ru']:
                return jsonify({'error': 'Unsupported language'}), 400

            user.preferred_language = language
            user.updated_at = datetime.utcnow()
            db.session.commit()

            logger.info(f"User {user.username} changed language to {language}")

            return jsonify({
                'success': True,
                'preferred_language': user.preferred_language
            })
        except Exception as e:
            logger.error(f"Language update error: {str(e)}")
            db.session.rollback()
            return jsonify({'error': 'Failed to update language'}), 500



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

        # Update user's preferred language if provided
        if 'preferred_language' in data:
            user = db.session.get(User, user_id)
            if user and data['preferred_language'] in ['en', 'he', 'ar', 'ru']:
                user.preferred_language = data['preferred_language']

        db.session.commit()
        return jsonify({'success': True, 'message': 'Profile updated'})


@app.route('/api/users/search')
@login_required
def search_users():
    """Search for users by username or email"""
    try:
        query = request.args.get('q', '').strip().lower()

        if not query or len(query) < 2:
            return jsonify({'users': []})

        # Get current user to exclude from results
        current_user_id = session['user_id']

        # Search for users by username (case-insensitive)
        users = User.query.filter(
            User.id != current_user_id,
            User.username.ilike(f'%{query}%')
        ).limit(10).all()

        # Format results
        results = []
        for user in users:
            # Get user's profile if it exists
            profile = Profile.query.filter_by(user_id=user.id).first()

            results.append({
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'bio': profile.bio if profile else None,
                'avatar_url': profile.avatar_url if profile else None
            })

        return jsonify({'users': results})

    except Exception as e:
        logger.error(f"User search error: {e}")
        return jsonify({'users': []})


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
                title=f'New message from {sender_name}',
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


@app.route('/api/feed/dates')
@login_required
def get_feed_saved_dates():
    """Get all dates that have feed entries with visibility info"""
    try:
        user_id = session['user_id']

        # Get all posts grouped by date and circle
        posts = db.session.query(
            db.func.date(Post.created_at).label('date'),
            Post.circle_id
        ).filter_by(
            user_id=user_id
        ).group_by(
            db.func.date(Post.created_at),
            Post.circle_id
        ).all()

        # Organize by date with visibility info
        dates_with_visibility = {}
        circle_to_visibility = {
            1: 'general',
            2: 'close_friends',
            3: 'family',
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
        logger.error(f"Get feed dates error: {e}")
        return jsonify({'dates': {}})


@app.route('/api/posts', methods=['POST'])
@login_required
def save_feed_entry():
    """Save/update feed entry for a specific date and visibility"""
    try:
        data = request.get_json()
        user_id = session['user_id']

        # Get the date and visibility from request
        post_date = data.get('date', datetime.utcnow().strftime('%Y-%m-%d'))
        content = data.get('content', '').strip()
        visibility = data.get('visibility', 'general')  # general, close_friends, family, private

        if not content:
            return jsonify({'error': 'Content is required'}), 400

        # Map visibility to circle_id (you may need to adjust based on your circles table)
        circle_map = {
            'general': 1,
            'close_friends': 2,
            'family': 3,
            'private': None
        }
        circle_id = circle_map.get(visibility)

        # Check if there's already a post for this date and visibility
        existing_post = Post.query.filter_by(
            user_id=user_id,
            circle_id=circle_id
        ).filter(
            db.func.date(Post.created_at) == post_date
        ).first()

        if existing_post:
            # Update existing post
            existing_post.content = content
            existing_post.updated_at = datetime.utcnow()
            message = f'Feed updated for {visibility.replace("_", " ")} on {post_date}'
        else:
            # Create new post
            new_post = Post(
                user_id=user_id,
                content=content,
                circle_id=circle_id,
                created_at=datetime.strptime(post_date, '%Y-%m-%d'),
                updated_at=datetime.utcnow(),
                is_published=True
            )
            db.session.add(new_post)
            message = f'Feed saved for {visibility.replace("_", " ")} on {post_date}'

        db.session.commit()
        return jsonify({'success': True, 'message': message})

    except Exception as e:
        logger.error(f"Feed save error: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to save feed'}), 500


@app.route('/api/feed/<date_str>')
@login_required
def load_feed_by_date(date_str):
    """Load feed entry for a specific date and visibility"""
    try:
        user_id = session['user_id']
        visibility = request.args.get('visibility', 'general')

        # Map visibility to circle_id
        circle_map = {
            'general': 1,
            'close_friends': 2,
            'family': 3,
            'private': None
        }
        circle_id = circle_map.get(visibility)

        # Get the post for this date and visibility
        post = Post.query.filter_by(
            user_id=user_id,
            circle_id=circle_id
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
    #data time

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