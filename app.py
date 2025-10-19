#!/usr/bin/env python
"""
Complete app.py for Social Social Platform
Updated with SQLAlchemy 2.0 style queries
"""

import os
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
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select, and_, or_, desc

# Import security functions
from security import (
    sanitize_input, validate_email, validate_username,
    validate_password_strength, encrypt_field, decrypt_field,
    generate_token, rate_limit, content_moderator
)

# Initialize Flask app
app = Flask(__name__, static_folder='static', template_folder='templates')

# Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///social.db')

# Fix for Render PostgreSQL URL
if app.config['SQLALCHEMY_DATABASE_URI'].startswith('postgres://'):
    app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace('postgres://',
                                                                                          'postgresql://', 1)

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

# Initialize extensions
db = SQLAlchemy(app)
CORS(app, supports_credentials=True)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('thera_social')

# Initialize Redis (optional, for session management)
try:
    redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379')
    redis_client = redis.from_url(redis_url, decode_responses=True)
except:
    redis_client = None
    logger.warning("Redis not available, using local sessions")


# =====================
# DATABASE MODELS
# =====================

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), default='user')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    profile = db.relationship('Profile', backref='user', uselist=False, cascade='all, delete-orphan')
    sent_messages = db.relationship('Message', foreign_keys='Message.sender_id', backref='sender')
    received_messages = db.relationship('Message', foreign_keys='Message.recipient_id', backref='recipient')
    circles = db.relationship('Circle', foreign_keys='Circle.user_id', backref='owner')
    saved_parameters = db.relationship('SavedParameters', backref='user', cascade='all, delete-orphan')


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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Post(db.Model):
    __tablename__ = 'posts'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    likes = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    author = db.relationship('User', backref='posts')


class Circle(db.Model):
    __tablename__ = 'circles'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    circle_user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    circle_type = db.Column(db.String(50))  # 'general', 'close_friends', 'family'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    circle_user = db.relationship('User', foreign_keys=[circle_user_id])


class Message(db.Model):
    __tablename__ = 'messages'
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    recipient_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    content = db.Column(db.Text)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class SavedParameters(db.Model):
    __tablename__ = 'saved_parameters'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    date = db.Column(db.Date)
    mood = db.Column(db.String(100))
    sleep_hours = db.Column(db.Float)
    exercise = db.Column(db.String(100))
    anxiety = db.Column(db.String(100))
    energy = db.Column(db.String(100))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Alert(db.Model):
    __tablename__ = 'alerts'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    title = db.Column(db.String(200))
    message = db.Column(db.Text)
    type = db.Column(db.String(50))  # 'info', 'warning', 'success', 'error'
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='alerts')


# =====================
# DECORATORS
# =====================

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required'}), 401
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
    logger.info(f"request_started", extra={
        'request_id': request.request_id,
        'method': request.method,
        'path': request.path,
        'remote_addr': request.remote_addr
    })


@app.after_request
def after_request(response):
    """Log response details"""
    logger.info(f"request_completed", extra={
        'request_id': getattr(request, 'request_id', 'unknown'),
        'status_code': response.status_code
    })
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
    """Serve favicon"""
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')


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
            password_hash=generate_password_hash(password)
        )
        db.session.add(user)
        db.session.flush()

        # Create profile
        profile = Profile(user_id=user.id)
        db.session.add(profile)

        db.session.commit()

        # Log user in
        session['user_id'] = user.id
        session['username'] = user.username
        session.permanent = True

        logger.info("user_registered", extra={'user_id': user.id})

        return jsonify({
            'success': True,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email
            }
        }), 200

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

        if not user or not check_password_hash(user.password_hash, password):
            return jsonify({'error': 'Invalid credentials'}), 401

        if not user.is_active:
            return jsonify({'error': 'Account deactivated'}), 403

        # Create session
        session['user_id'] = user.id
        session['username'] = user.username
        session['role'] = user.role
        session.permanent = True

        logger.info("login_success", extra={'user_id': user.id})

        return jsonify({
            'success': True,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'role': user.role
            }
        }), 200

    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return jsonify({'error': 'Login failed'}), 500


@app.route('/api/auth/logout', methods=['POST'])
def logout():
    """User logout"""
    user_id = session.get('user_id')
    session.clear()
    logger.info("logout", extra={'user_id': user_id})
    return jsonify({'success': True}), 200


@app.route('/api/auth/session', methods=['GET'])
def check_session():
    """Check if user is logged in"""
    if 'user_id' in session:
        user = db.session.get(User, session['user_id'])
        if user:
            return jsonify({
                'authenticated': True,
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'role': user.role
                }
            })

    return jsonify({'authenticated': False}), 401


# =====================
# USER ROUTES
# =====================

@app.route('/api/user/profile', methods=['GET'])
@login_required
def get_current_user():
    """Get current user info"""
    user = db.session.get(User, session['user_id'])
    return jsonify({
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'role': user.role
    })


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
            'favorite_hobbies': profile.favorite_hobbies or ''
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
        profile.bio = sanitize_input(data.get('bio', ''))
        profile.interests = sanitize_input(data.get('interests', ''))
        profile.occupation = sanitize_input(data.get('occupation', ''))
        profile.goals = sanitize_input(data.get('goals', ''))
        profile.favorite_hobbies = sanitize_input(data.get('favorite_hobbies', ''))
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
        )
    ).limit(10)
    
    users = db.session.execute(stmt).scalars().all()

    results = [{
        'id': u.id,
        'username': u.username,
        'email': u.email
    } for u in users if u.id != session.get('user_id')]

    return jsonify(results)


# =====================
# FEED ROUTES
# =====================

@app.route('/api/feed', methods=['GET'])
@login_required
def get_feed():
    """Get user feed"""
    try:
        # Get posts from user's circles
        user_id = session['user_id']

        # Get users in circles - SQLAlchemy 2.0 style
        circles_stmt = select(Circle).filter_by(user_id=user_id)
        circle_users = db.session.execute(circles_stmt).scalars().all()
        circle_user_ids = [c.circle_user_id for c in circle_users]
        circle_user_ids.append(user_id)  # Include own posts

        # Get posts - SQLAlchemy 2.0 style
        posts_stmt = select(Post).filter(
            Post.user_id.in_(circle_user_ids)
        ).order_by(desc(Post.created_at)).limit(50)
        
        posts = db.session.execute(posts_stmt).scalars().all()

        feed = []
        for post in posts:
            feed.append({
                'id': post.id,
                'content': post.content,
                'author': post.author.username,
                'likes': post.likes,
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
        db.session.commit()

        return jsonify({'success': True, 'post_id': post.id})

    except Exception as e:
        logger.error(f"Post creation error: {str(e)}")
        return jsonify({'error': 'Failed to create post'}), 500


# =====================
# CIRCLES ROUTES
# =====================

@app.route('/api/circles', methods=['GET', 'POST'])
@login_required
def circles():
    """Manage user circles"""
    user_id = session.get('user_id')

    if request.method == 'GET':
        # Get all circles for the user - SQLAlchemy 2.0 style
        general_stmt = select(Circle).filter_by(user_id=user_id, circle_type='general')
        general = db.session.execute(general_stmt).scalars().all()
        
        close_friends_stmt = select(Circle).filter_by(user_id=user_id, circle_type='close_friends')
        close_friends = db.session.execute(close_friends_stmt).scalars().all()
        
        family_stmt = select(Circle).filter_by(user_id=user_id, circle_type='family')
        family = db.session.execute(family_stmt).scalars().all()

        def get_user_info(circle):
            user = db.session.get(User, circle.circle_user_id)
            return {
                'id': user.id,
                'username': user.username,
                'email': user.email
            }

        return jsonify({
            'general': [get_user_info(c) for c in general],
            'close_friends': [get_user_info(c) for c in close_friends],
            'family': [get_user_info(c) for c in family]
        })

    elif request.method == 'POST':
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


@app.route('/api/circles/remove', methods=['DELETE'])
@login_required
def remove_from_circle():
    """Remove user from circle"""
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


# =====================
# MESSAGES ROUTES
# =====================

@app.route('/api/messages', methods=['GET', 'POST'])
@login_required
def messages():
    """Get or send messages"""
    user_id = session.get('user_id')

    if request.method == 'GET':
        # Get all messages for the user - SQLAlchemy 2.0 style
        sent_stmt = select(Message).filter_by(sender_id=user_id).order_by(desc(Message.created_at))
        sent = db.session.execute(sent_stmt).scalars().all()
        
        received_stmt = select(Message).filter_by(recipient_id=user_id).order_by(desc(Message.created_at))
        received = db.session.execute(received_stmt).scalars().all()

        def format_message(msg):
            sender = db.session.get(User, msg.sender_id)
            recipient = db.session.get(User, msg.recipient_id)
            return {
                'id': msg.id,
                'sender': {'id': sender.id, 'username': sender.username},
                'recipient': {'id': recipient.id, 'username': recipient.username},
                'content': msg.content,
                'is_read': msg.is_read,
                'created_at': msg.created_at.isoformat()
            }

        return jsonify({
            'sent': [format_message(m) for m in sent],
            'received': [format_message(m) for m in received]
        })

    elif request.method == 'POST':
        data = request.json
        recipient_id = data.get('recipient_id')
        content = data.get('content')

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

        message = Message(
            sender_id=user_id,
            recipient_id=recipient_id,
            content=sanitize_input(content)
        )
        db.session.add(message)
        db.session.commit()

        return jsonify({'success': True, 'message_id': message.id})


@app.route('/api/messages/<int:message_id>/read', methods=['PUT'])
@login_required
def mark_message_read(message_id):
    """Mark message as read"""
    user_id = session.get('user_id')
    message = db.session.get(Message, message_id)

    if not message:
        return jsonify({'error': 'Message not found'}), 404

    if message.recipient_id != user_id:
        return jsonify({'error': 'Unauthorized'}), 403

    message.is_read = True
    db.session.commit()

    return jsonify({'success': True})


@app.route('/api/messages/conversations')
@login_required
def get_conversations():
    """Get conversation list"""
    user_id = session['user_id']

    # Get unique conversation partners - SQLAlchemy 2.0 style
    sent_stmt = select(Message.recipient_id).filter_by(sender_id=user_id).distinct()
    sent = db.session.execute(sent_stmt).scalars().all()
    
    received_stmt = select(Message.sender_id).filter_by(recipient_id=user_id).distinct()
    received = db.session.execute(received_stmt).scalars().all()

    partner_ids = set()
    for partner_id in sent:
        partner_ids.add(partner_id)
    for partner_id in received:
        partner_ids.add(partner_id)

    conversations = []
    for partner_id in partner_ids:
        user = db.session.get(User, partner_id)
        if user:
            # Get last message - SQLAlchemy 2.0 style
            last_msg_stmt = select(Message).filter(
                or_(
                    and_(Message.sender_id == user_id, Message.recipient_id == partner_id),
                    and_(Message.sender_id == partner_id, Message.recipient_id == user_id)
                )
            ).order_by(desc(Message.created_at))
            
            last_message = db.session.execute(last_msg_stmt).scalar_one_or_none()

            conversations.append({
                'user': {'id': user.id, 'username': user.username},
                'last_message': last_message.content if last_message else None,
                'timestamp': last_message.created_at.isoformat() if last_message else None
            })

    return jsonify(conversations)


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
            'mood': params.mood,
            'sleep_hours': params.sleep_hours,
            'exercise': params.exercise,
            'anxiety': params.anxiety,
            'energy': params.energy,
            'notes': params.notes
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
    user_id = session.get('user_id')
    data = request.json

    date_str = data.get('date', str(datetime.now().date()))
    date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()

    # Check if parameters exist for this date - SQLAlchemy 2.0 style
    params_stmt = select(SavedParameters).filter_by(
        user_id=user_id,
        date=date_obj
    )
    params = db.session.execute(params_stmt).scalar_one_or_none()

    if not params:
        params = SavedParameters(user_id=user_id, date=date_obj)
        db.session.add(params)

    # Save with text values
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


@app.route('/api/parameters/load/<date>')
@login_required
def load_parameters(date):
    """Load parameters for specific date"""
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
                'sleep_hours': params.sleep_hours,
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


@app.route('/api/parameters/dates')
@login_required
def get_parameter_dates():
    """Get dates with saved parameters"""
    user_id = session.get('user_id')
    # SQLAlchemy 2.0 style
    params_stmt = select(SavedParameters).filter_by(user_id=user_id)
    params = db.session.execute(params_stmt).scalars().all()
    dates = [p.date.strftime('%Y-%m-%d') for p in params]
    return jsonify({'dates': dates})


@app.route('/api/parameters/insights')
@login_required
def get_insights():
    """Get parameter insights"""
    user_id = session['user_id']

    # Get last 30 days of parameters - SQLAlchemy 2.0 style
    thirty_days_ago = datetime.now().date() - timedelta(days=30)
    params_stmt = select(SavedParameters).filter(
        SavedParameters.user_id == user_id,
        SavedParameters.date >= thirty_days_ago
    )
    params = db.session.execute(params_stmt).scalars().all()

    if not params:
        return jsonify({'message': 'No data available for insights'})

    # Calculate insights
    avg_sleep = sum(p.sleep_hours for p in params) / len(params) if params else 0
    moods = [p.mood for p in params if p.mood]

    return jsonify({
        'average_sleep': round(avg_sleep, 1),
        'total_entries': len(params),
        'most_common_mood': max(moods, key=moods.count) if moods else 'N/A',
        'streak': calculate_streak(params)
    })


def calculate_streak(params):
    """Calculate consecutive days streak"""
    if not params:
        return 0

    dates = sorted([p.date for p in params], reverse=True)
    streak = 1

    for i in range(1, len(dates)):
        if (dates[i - 1] - dates[i]).days == 1:
            streak += 1
        else:
            break

    return streak


# =====================
# ALERTS ROUTES
# =====================

@app.route('/api/alerts', methods=['GET'])
@login_required
def get_alerts():
    """Get user alerts"""
    user_id = session['user_id']
    # SQLAlchemy 2.0 style
    alerts_stmt = select(Alert).filter_by(
        user_id=user_id, 
        is_read=False
    ).order_by(desc(Alert.created_at)).limit(10)
    
    alerts = db.session.execute(alerts_stmt).scalars().all()

    return jsonify([{
        'id': a.id,
        'title': a.title,
        'message': a.message,
        'type': a.type,
        'created_at': a.created_at.isoformat()
    } for a in alerts])


@app.route('/api/alerts/<int:alert_id>/read', methods=['PUT'])
@login_required
def mark_alert_read(alert_id):
    """Mark alert as read"""
    alert = db.session.get(Alert, alert_id)
    if alert and alert.user_id == session['user_id']:
        alert.is_read = True
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'error': 'Alert not found'}), 404


# =====================
# ADMIN ROUTES
# =====================

@app.route('/api/admin/users')
@admin_required
def admin_get_users():
    """Get all users (admin only)"""
    # SQLAlchemy 2.0 style
    users_stmt = select(User)
    users = db.session.execute(users_stmt).scalars().all()
    
    return jsonify([{
        'id': u.id,
        'username': u.username,
        'email': u.email,
        'role': u.role,
        'is_active': u.is_active,
        'created_at': u.created_at.isoformat()
    } for u in users])


@app.route('/api/admin/stats')
@admin_required
def admin_stats():
    """Get platform statistics"""
    # SQLAlchemy 2.0 style
    total_users = db.session.execute(select(db.func.count(User.id))).scalar()
    total_posts = db.session.execute(select(db.func.count(Post.id))).scalar()
    total_messages = db.session.execute(select(db.func.count(Message.id))).scalar()
    
    active_users_stmt = select(db.func.count(User.id)).filter(
        User.updated_at >= datetime.now().date()
    )
    active_users_today = db.session.execute(active_users_stmt).scalar()
    
    return jsonify({
        'total_users': total_users,
        'total_posts': total_posts,
        'total_messages': total_messages,
        'active_users_today': active_users_today
    })


# =====================
# SUPPORT ROUTES
# =====================

@app.route('/api/support/contact', methods=['POST'])
def contact_support():
    """Send message to support"""
    data = request.json

    # In production, this would send an email or create a ticket
    logger.info("support_contact", extra={
        'name': data.get('name'),
        'email': data.get('email'),
        'subject': data.get('subject'),
        'message': data.get('message')
    })

    return jsonify({'success': True, 'message': 'Support request received'})


# =====================
# UTILITY ROUTES
# =====================

@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    status = {}

    # Check database
    try:
        db.session.execute(select(1))
        status['database'] = 'OK'
    except Exception as e:
        status['database'] = str(e)

    # Check Redis
    try:
        if redis_client:
            redis_client.ping()
            status['redis'] = 'OK'
        else:
            status['redis'] = 'Not configured'
    except Exception as e:
        status['redis'] = str(e)

    return jsonify(status), 200 if all(v in ['OK', 'Not configured'] for v in status.values()) else 503


@app.route('/api/setup/sample-users', methods=['POST'])
def create_sample_users():
    """Create sample users for testing"""
    sample_users = [
        {'username': 'alice_wonder', 'email': 'alice@example.com', 'name': 'Alice Wonder'},
        {'username': 'bob_builder', 'email': 'bob@example.com', 'name': 'Bob Builder'},
        {'username': 'charlie_day', 'email': 'charlie@example.com', 'name': 'Charlie Day'},
        {'username': 'diana_prince', 'email': 'diana@example.com', 'name': 'Diana Prince'},
        {'username': 'edward_snow', 'email': 'edward@example.com', 'name': 'Edward Snow'},
        {'username': 'fiona_green', 'email': 'fiona@example.com', 'name': 'Fiona Green'},
        {'username': 'george_lucas', 'email': 'george@example.com', 'name': 'George Lucas'},
        {'username': 'helen_troy', 'email': 'helen@example.com', 'name': 'Helen Troy'},
        {'username': 'ivan_terrible', 'email': 'ivan@example.com', 'name': 'Ivan Terrible'},
        {'username': 'julia_roberts', 'email': 'julia@example.com', 'name': 'Julia Roberts'},
        {'username': 'kevin_hart', 'email': 'kevin@example.com', 'name': 'Kevin Hart'},
        {'username': 'lisa_simpson', 'email': 'lisa@example.com', 'name': 'Lisa Simpson'}
    ]

    created = []
    for user_data in sample_users:
        # Check if user already exists - SQLAlchemy 2.0 style
        existing_stmt = select(User).filter_by(email=user_data['email'])
        if db.session.execute(existing_stmt).scalar_one_or_none():
            continue

        user = User(
            username=user_data['username'],
            email=user_data['email'],
            password_hash=generate_password_hash('password123')
        )
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


# =====================
# ERROR HANDLERS
# =====================

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({'error': 'Not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    db.session.rollback()
    logger.error(f"Internal error: {str(error)}")
    return jsonify({'error': 'Internal server error'}), 500


# =====================
# MAIN
# =====================

if __name__ == '__main__':
    with app.app_context():
        db.create_all()

    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
