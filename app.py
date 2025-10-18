"""
Thera Social Backend - Main Application
A social-therapeutic platform with anonymous sharing and tracking
"""
import os
import logging
import traceback
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, request, jsonify, g, session, send_from_directory
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.middleware.proxy_fix import ProxyFix
import redis
import uuid

# Import custom modules
from models import db, migrate, User, Follow, Circle, CircleMember, Post, Parameter, ParameterValue, Trend, Alert, PrivateMessage, Report, Penalty
from config import Config, configure_logging
from security import SecurityManager, sanitize_input, validate_email, encrypt_field, decrypt_field
from auth import AuthManager, require_auth, generate_token, verify_token
from social import SocialManager
from tracking import TrackingManager
from messaging import MessagingManager

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# Initialize extensions
db.init_app(app)
migrate.init_app(app, db)
CORS(app, supports_credentials=True)

# Initialize Redis
redis_client = redis.from_url(os.environ.get('REDIS_URL', 'redis://localhost:6379'))

# Initialize rate limiter
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["5000 per day", "1000 per hour"],
    storage_uri="memory://"
)

# Configure logging
logger = configure_logging()

# Initialize managers
security_manager = SecurityManager(app, redis_client)
auth_manager = AuthManager(app, db, redis_client)
social_manager = SocialManager(db, redis_client)
tracking_manager = TrackingManager(db, redis_client)
messaging_manager = MessagingManager(db, redis_client, security_manager)

# ============= REQUEST HANDLERS =============

@app.before_request
def before_request():
    """Initialize request context"""
    g.request_id = str(uuid.uuid4())
    g.request_start_time = datetime.utcnow()
    
    # Security checks
    if not security_manager.validate_request(request):
        return jsonify({'error': 'Invalid request'}), 400
    
    # Log request
    logger.info('request_started', extra={
        'request_id': g.request_id,
        'method': request.method,
        'path': request.path,
        'ip': request.remote_addr
    })

@app.after_request
def after_request(response):
    """Post-request processing"""
    if hasattr(g, 'request_start_time'):
        duration = (datetime.utcnow() - g.request_start_time).total_seconds()
        logger.info('request_completed', extra={
            'request_id': g.request_id,
            'duration': duration,
            'status': response.status_code
        })
    
    # Security headers
    response.headers.update(security_manager.get_security_headers())
    response.headers['X-Request-ID'] = g.request_id
    
    return response

@app.errorhandler(Exception)
def handle_error(error):
    """Global error handler"""
    logger.error('unhandled_exception', extra={
        'request_id': g.request_id,
        'error': str(error),
        'traceback': traceback.format_exc()
    })
    
    if isinstance(error, ValueError):
        return jsonify({'error': str(error)}), 400
    
    return jsonify({'error': 'Internal server error'}), 500

# ============= AUTHENTICATION ENDPOINTS =============

@app.route('/api/auth/register', methods=['POST'])
@limiter.limit("10 per hour")
def register():
    """Register new user with anonymity"""
    try:
        data = request.json
        
        # Validate required fields
        email = sanitize_input(data.get('email', ''))
        password = data.get('password', '')
        display_name = sanitize_input(data.get('display_name', ''))
        
        if not all([email, password]):
            return jsonify({'error': 'Email and password required'}), 400
        
        if not validate_email(email):
            return jsonify({'error': 'Invalid email format'}), 400
        
        # Check password strength
        if len(password) < 12:
            return jsonify({'error': 'Password must be at least 12 characters'}), 400
        
        # Check if email exists
        if User.query.filter_by(email_encrypted=encrypt_field(email)).first():
            return jsonify({'error': 'Email already registered'}), 400
        
        # Generate anonymous ID
        anonymous_id = f"USER_{uuid.uuid4().hex[:12].upper()}"
        
        # Create user
        user = User(
            anonymous_id=anonymous_id,
            email_encrypted=encrypt_field(email),
            display_name=display_name or f"Anonymous_{uuid.uuid4().hex[:8]}",
            password_hash=auth_manager.hash_password(password)
        )
        
        db.session.add(user)
        db.session.flush()
        
        # Create default circles
        for circle_type in ['family', 'close_friends', 'general']:
            circle = Circle(
                user_id=user.id,
                circle_type=circle_type,
                name=circle_type.replace('_', ' ').title()
            )
            db.session.add(circle)
        
        # Create default tracking parameters
        default_params = ['mood', 'sleep', 'exercise', 'anxiety', 'energy']
        for param_name in default_params:
            param = Parameter(
                user_id=user.id,
                name=param_name,
                parameter_type='scale',
                min_value=1,
                max_value=10
            )
            db.session.add(param)
        
        db.session.commit()
        
        # Generate token
        token = generate_token(user.id, user.anonymous_id)
        
        logger.info('user_registered', extra={
            'request_id': g.request_id,
            'user_id': user.id,
            'anonymous_id': anonymous_id
        })
        
        return jsonify({
            'success': True,
            'token': token,
            'user': {
                'id': user.anonymous_id,
                'display_name': user.display_name
            }
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error('registration_error', extra={
            'request_id': g.request_id,
            'error': str(e)
        })
        return jsonify({'error': 'Registration failed'}), 500

@app.route('/api/auth/login', methods=['POST'])
@limiter.limit("20 per minute")
def login():
    """User login with anonymity preservation"""
    try:
        data = request.json
        email = data.get('email', '')
        password = data.get('password', '')
        
        if not all([email, password]):
            return jsonify({'error': 'Email and password required'}), 400
        
        # Find user by encrypted email
        user = User.query.filter_by(
            email_encrypted=encrypt_field(email),
            is_active=True
        ).first()
        
        if not user or not auth_manager.verify_password(password, user.password_hash):
            logger.warning('login_failed', extra={
                'request_id': g.request_id,
                'email': email
            })
            return jsonify({'error': 'Invalid credentials'}), 401
        
        # Check for penalties
        active_penalty = user.penalties.filter_by(is_active=True).first()
        if active_penalty:
            return jsonify({
                'error': 'Account suspended',
                'reason': active_penalty.reason,
                'until': active_penalty.end_date.isoformat() if active_penalty.end_date else 'Permanent'
            }), 403
        
        # Update last login
        user.last_login = datetime.utcnow()
        db.session.commit()
        
        # Generate token
        token = generate_token(user.id, user.anonymous_id)
        
        # Create session
        session_id = auth_manager.create_session(user.id)
        
        logger.info('login_success', extra={
            'request_id': g.request_id,
            'user_id': user.id
        })
        
        response = jsonify({
            'success': True,
            'token': token,
            'user': {
                'id': user.anonymous_id,
                'display_name': user.display_name
            }
        })
        
        response.set_cookie(
            'session_token',
            session_id,
            max_age=86400,
            secure=True,
            httponly=True,
            samesite='Strict'
        )
        
        return response
        
    except Exception as e:
        logger.error('login_error', extra={
            'request_id': g.request_id,
            'error': str(e)
        })
        return jsonify({'error': 'Login failed'}), 500

@app.route('/api/auth/logout', methods=['POST'])
@require_auth()
def logout():
    """User logout"""
    try:
        user = request.current_user
        auth_manager.invalidate_session(user.id)
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============= PROFILE ENDPOINTS =============

@app.route('/api/profile', methods=['GET'])
@require_auth()
def get_profile():
    """Get user profile with anonymity"""
    user = request.current_user
    
    return jsonify({
        'profile': {
            'id': user.anonymous_id,
            'display_name': user.display_name,
            'bio': decrypt_field(user.bio_encrypted) if user.bio_encrypted else None,
            'joined': user.created_at.isoformat(),
            'stats': {
                'followers': user.followers.count(),
                'following': user.following.count(),
                'posts': user.posts.count()
            }
        }
    })

@app.route('/api/profile', methods=['PUT'])
@require_auth()
def update_profile():
    """Update profile maintaining anonymity"""
    try:
        user = request.current_user
        data = request.json
        
        if 'display_name' in data:
            user.display_name = sanitize_input(data['display_name'])
        
        if 'bio' in data:
            bio = sanitize_input(data['bio'])
            if len(bio) > 500:
                return jsonify({'error': 'Bio must be under 500 characters'}), 400
            user.bio_encrypted = encrypt_field(bio)
        
        db.session.commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ============= SOCIAL ENDPOINTS =============

@app.route('/api/follow/<anonymous_id>', methods=['POST'])
@require_auth()
def follow_user(anonymous_id):
    """Follow another user"""
    try:
        user = request.current_user
        target = User.query.filter_by(anonymous_id=anonymous_id).first()
        
        if not target:
            return jsonify({'error': 'User not found'}), 404
        
        if target.id == user.id:
            return jsonify({'error': 'Cannot follow yourself'}), 400
        
        result = social_manager.follow_user(user.id, target.id)
        
        if result:
            # Create alert for followed user
            tracking_manager.create_alert(
                target.id,
                'new_follower',
                f'{user.display_name} started following you',
                'low'
            )
        
        return jsonify({'success': result})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/unfollow/<anonymous_id>', methods=['DELETE'])
@require_auth()
def unfollow_user(anonymous_id):
    """Unfollow a user"""
    try:
        user = request.current_user
        target = User.query.filter_by(anonymous_id=anonymous_id).first()
        
        if not target:
            return jsonify({'error': 'User not found'}), 404
        
        result = social_manager.unfollow_user(user.id, target.id)
        
        return jsonify({'success': result})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/circles', methods=['GET'])
@require_auth()
def get_circles():
    """Get user's circles"""
    user = request.current_user
    circles = social_manager.get_user_circles(user.id)
    
    return jsonify({'circles': circles})

@app.route('/api/circles/<int:circle_id>/members', methods=['POST'])
@require_auth()
def add_to_circle(circle_id):
    """Add user to circle"""
    try:
        user = request.current_user
        data = request.json
        target_id = data.get('user_id')
        
        # Verify circle ownership
        circle = Circle.query.filter_by(id=circle_id, user_id=user.id).first()
        if not circle:
            return jsonify({'error': 'Circle not found'}), 404
        
        # Find target user
        target = User.query.filter_by(anonymous_id=target_id).first()
        if not target:
            return jsonify({'error': 'User not found'}), 404
        
        # Check if following
        if not Follow.query.filter_by(follower_id=user.id, followed_id=target.id).first():
            return jsonify({'error': 'Must follow user first'}), 400
        
        result = social_manager.add_to_circle(circle_id, target.id)
        
        return jsonify({'success': result})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============= SHARING ENDPOINTS =============

@app.route('/api/posts', methods=['POST'])
@require_auth()
def create_post():
    """Share feelings or updates"""
    try:
        user = request.current_user
        data = request.json
        
        content = sanitize_input(data.get('content', ''))
        visibility = data.get('visibility', 'general')
        circle_id = data.get('circle_id')
        
        if not content:
            return jsonify({'error': 'Content required'}), 400
        
        if len(content) > 1000:
            return jsonify({'error': 'Content too long'}), 400
        
        post = Post(
            user_id=user.id,
            content_encrypted=encrypt_field(content),
            visibility=visibility,
            circle_id=circle_id
        )
        
        db.session.add(post)
        db.session.commit()
        
        # Check for concerning patterns
        tracking_manager.analyze_content(user.id, content)
        
        return jsonify({
            'success': True,
            'post_id': post.id
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.route('/api/feed', methods=['GET'])
@require_auth()
def get_feed():
    """Get personalized feed"""
    try:
        user = request.current_user
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 50)
        
        feed = social_manager.get_user_feed(user.id, page, per_page)
        
        return jsonify({
            'posts': feed['posts'],
            'pagination': feed['pagination']
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============= TRACKING ENDPOINTS =============

@app.route('/api/parameters', methods=['GET'])
@require_auth()
def get_parameters():
    """Get user's tracking parameters"""
    user = request.current_user
    params = tracking_manager.get_user_parameters(user.id)
    
    return jsonify({'parameters': params})

@app.route('/api/parameters/values', methods=['POST'])
@require_auth()
def track_parameter():
    """Track parameter value"""
    try:
        user = request.current_user
        data = request.json
        
        parameter_id = data.get('parameter_id')
        value = data.get('value')
        notes = sanitize_input(data.get('notes', ''))
        
        if not all([parameter_id, value is not None]):
            return jsonify({'error': 'Parameter ID and value required'}), 400
        
        # Verify parameter ownership
        param = Parameter.query.filter_by(id=parameter_id, user_id=user.id).first()
        if not param:
            return jsonify({'error': 'Parameter not found'}), 404
        
        # Record value
        result = tracking_manager.record_value(user.id, parameter_id, value, notes)
        
        # Analyze trends
        trends = tracking_manager.analyze_trends(user.id, parameter_id)
        
        # Alert followers if significant change
        if trends and abs(trends.get('change_percent', 0)) > 20:
            social_manager.alert_followers(user.id, param.name, trends)
        
        return jsonify({
            'success': True,
            'value_id': result['id'],
            'trends': trends
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/parameters/<int:param_id>/history', methods=['GET'])
@require_auth()
def get_parameter_history(param_id):
    """Get parameter history"""
    try:
        user = request.current_user
        days = request.args.get('days', 30, type=int)
        
        history = tracking_manager.get_parameter_history(user.id, param_id, days)
        
        return jsonify({
            'history': history['values'],
            'statistics': history['stats']
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/parameters/insights', methods=['GET'])
@require_auth()
def get_insights():
    """Get tracking insights"""
    try:
        user = request.current_user
        days = request.args.get('days', 30, type=int)
        
        insights = tracking_manager.get_insights(user.id, days)
        
        return jsonify({'insights': insights})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/alerts', methods=['GET'])
@require_auth()
def get_alerts():
    """Get user alerts"""
    user = request.current_user
    page = request.args.get('page', 1, type=int)
    
    alerts = tracking_manager.get_user_alerts(user.id, page)
    
    return jsonify({
        'alerts': alerts['alerts'],
        'unread_count': alerts['unread_count']
    })

# ============= MESSAGING ENDPOINTS =============

@app.route('/api/messages', methods=['POST'])
@require_auth()
def send_message():
    """Send private message"""
    try:
        user = request.current_user
        data = request.json
        
        recipient_id = data.get('recipient_id')
        content = sanitize_input(data.get('content', ''))
        
        if not all([recipient_id, content]):
            return jsonify({'error': 'Recipient and content required'}), 400
        
        # Find recipient
        recipient = User.query.filter_by(anonymous_id=recipient_id).first()
        if not recipient:
            return jsonify({'error': 'Recipient not found'}), 404
        
        # Check if can message (must be following each other)
        if not social_manager.can_message(user.id, recipient.id):
            return jsonify({'error': 'Must be mutual followers to message'}), 403
        
        message_id = messaging_manager.send_message(user.id, recipient.id, content)
        
        return jsonify({
            'success': True,
            'message_id': message_id
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/messages/<anonymous_id>', methods=['GET'])
@require_auth()
def get_conversation(anonymous_id):
    """Get conversation with user"""
    try:
        user = request.current_user
        page = request.args.get('page', 1, type=int)
        
        # Find other user
        other_user = User.query.filter_by(anonymous_id=anonymous_id).first()
        if not other_user:
            return jsonify({'error': 'User not found'}), 404
        
        messages = messaging_manager.get_conversation(user.id, other_user.id, page)
        
        return jsonify({
            'messages': messages['messages'],
            'pagination': messages['pagination']
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/messages/conversations', methods=['GET'])
@require_auth()
def get_conversations():
    """Get list of conversations"""
    try:
        user = request.current_user
        page = request.args.get('page', 1, type=int)
        
        conversations = messaging_manager.get_conversations_list(user.id, page)
        
        return jsonify(conversations)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============= PRIVACY & SAFETY ENDPOINTS =============

@app.route('/api/report', methods=['POST'])
@require_auth()
def report_violation():
    """Report privacy violation or inappropriate behavior"""
    try:
        user = request.current_user
        data = request.json
        
        reported_user_id = data.get('user_id')
        violation_type = data.get('type')
        description = sanitize_input(data.get('description', ''))
        evidence = data.get('evidence', [])
        
        if not all([reported_user_id, violation_type, description]):
            return jsonify({'error': 'All fields required'}), 400
        
        # Find reported user
        reported_user = User.query.filter_by(anonymous_id=reported_user_id).first()
        if not reported_user:
            return jsonify({'error': 'User not found'}), 404
        
        # Create report
        report = Report(
            reporter_id=user.id,
            reported_user_id=reported_user.id,
            violation_type=violation_type,
            description_encrypted=encrypt_field(description),
            evidence=evidence,
            status='pending'
        )
        
        db.session.add(report)
        db.session.commit()
        
        # Log for audit
        logger.warning('violation_reported', extra={
            'request_id': g.request_id,
            'reporter_id': user.id,
            'reported_id': reported_user.id,
            'type': violation_type
        })
        
        # If privacy violation, immediate action
        if violation_type == 'privacy_violation':
            security_manager.handle_privacy_violation(reported_user.id, report.id)
        
        return jsonify({
            'success': True,
            'report_id': report.id,
            'message': 'Report submitted for review'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

# ============= FRONTEND SERVING =============

@app.route('/')
def index():
    """Serve the main application"""
    return send_from_directory('static', 'index.html')

@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files"""
    return send_from_directory('static', filename)

# ============= HEALTH CHECK =============

@app.route('/api/health', methods=['GET'])
def health_check():
    """System health check"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'version': '1.0.0'
    })

# ============= MAIN ENTRY =============

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        from init_db import initialize_database
        initialize_database()
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=not os.environ.get('PRODUCTION'))
