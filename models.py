"""
Database models for Thera Social
"""
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

db = SQLAlchemy()
migrate = Migrate()

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    anonymous_id = db.Column(db.String(50), unique=True, nullable=False, index=True)
    email_encrypted = db.Column(db.String(500), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    display_name = db.Column(db.String(100), nullable=False)
    bio_encrypted = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    is_verified = db.Column(db.Boolean, default=False)
    last_login = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    posts = db.relationship('Post', backref='author', lazy='dynamic', cascade='all, delete-orphan')
    parameters = db.relationship('Parameter', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    circles = db.relationship('Circle', backref='owner', lazy='dynamic', cascade='all, delete-orphan')
    sent_messages = db.relationship('PrivateMessage', foreign_keys='PrivateMessage.sender_id', backref='sender', lazy='dynamic')
    received_messages = db.relationship('PrivateMessage', foreign_keys='PrivateMessage.recipient_id', backref='recipient', lazy='dynamic')
    alerts = db.relationship('Alert', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    reports_made = db.relationship('Report', foreign_keys='Report.reporter_id', backref='reporter', lazy='dynamic')
    reports_received = db.relationship('Report', foreign_keys='Report.reported_user_id', backref='reported_user', lazy='dynamic')
    penalties = db.relationship('Penalty', backref='user', lazy='dynamic')
    
    # Following relationships
    following = db.relationship(
        'Follow',
        foreign_keys='Follow.follower_id',
        backref='follower',
        lazy='dynamic',
        cascade='all, delete-orphan'
    )
    
    followers = db.relationship(
        'Follow',
        foreign_keys='Follow.followed_id',
        backref='followed',
        lazy='dynamic',
        cascade='all, delete-orphan'
    )

class Follow(db.Model):
    __tablename__ = 'follows'
    
    id = db.Column(db.Integer, primary_key=True)
    follower_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    followed_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('follower_id', 'followed_id'),)

class Circle(db.Model):
    __tablename__ = 'circles'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    circle_type = db.Column(db.String(20), nullable=False)  # family, close_friends, general
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    members = db.relationship('CircleMember', backref='circle', lazy='dynamic', cascade='all, delete-orphan')

class CircleMember(db.Model):
    __tablename__ = 'circle_members'
    
    id = db.Column(db.Integer, primary_key=True)
    circle_id = db.Column(db.Integer, db.ForeignKey('circles.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('circle_id', 'user_id'),)

class Post(db.Model):
    __tablename__ = 'posts'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content_encrypted = db.Column(db.Text, nullable=False)
    visibility = db.Column(db.String(20), default='general')  # family, close_friends, general, private
    circle_id = db.Column(db.Integer, db.ForeignKey('circles.id'))
    is_deleted = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Parameter(db.Model):
    __tablename__ = 'parameters'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    
    # 5 parameter fields - all integers 1-4
    mood = db.Column(db.Integer, db.CheckConstraint('mood >= 1 AND mood <= 4'))
    energy = db.Column(db.Integer, db.CheckConstraint('energy >= 1 AND energy <= 4'))
    sleep_quality = db.Column(db.Integer, db.CheckConstraint('sleep_quality >= 1 AND sleep_quality <= 4'))
    physical_activity = db.Column(db.Integer, db.CheckConstraint('physical_activity >= 1 AND physical_activity <= 4'))
    anxiety = db.Column(db.Integer, db.CheckConstraint('anxiety >= 1 AND anxiety <= 4'))
    
    # Notes field
    notes = db.Column(db.Text)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    user = db.relationship('User', backref=db.backref('parameters', lazy='dynamic'))
    
    # Ensure unique date per user
    __table_args__ = (
        db.UniqueConstraint('user_id', 'date', name='unique_user_date'),
    )
    
    def to_dict(self):
        """Convert parameter to dictionary for API responses"""
        return {
            'id': self.id,
            'date': self.date.isoformat() if self.date else None,
            'mood': self.mood,
            'energy': self.energy,
            'sleep_quality': self.sleep_quality,
            'physical_activity': self.physical_activity,
            'anxiety': self.anxiety,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class ParameterValue(db.Model):
    __tablename__ = 'parameter_values'
    
    id = db.Column(db.Integer, primary_key=True)
    parameter_id = db.Column(db.Integer, db.ForeignKey('parameters.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    value = db.Column(db.Float, nullable=False)
    notes_encrypted = db.Column(db.Text)
    recorded_at = db.Column(db.DateTime, default=datetime.utcnow)

class Trend(db.Model):
    __tablename__ = 'trends'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    parameter_id = db.Column(db.Integer, db.ForeignKey('parameters.id'), nullable=False)
    trend_type = db.Column(db.String(20))  # increasing, decreasing, stable, volatile
    confidence = db.Column(db.Float)
    change_percent = db.Column(db.Float)
    period_days = db.Column(db.Integer)
    detected_at = db.Column(db.DateTime, default=datetime.utcnow)

class Alert(db.Model):
    __tablename__ = 'alerts'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    alert_type = db.Column(db.String(50), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    message_encrypted = db.Column(db.Text)
    priority = db.Column(db.String(20), default='low')  # low, medium, high, critical
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class PrivateMessage(db.Model):
    __tablename__ = 'private_messages'
    
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content_encrypted = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    is_deleted_sender = db.Column(db.Boolean, default=False)
    is_deleted_recipient = db.Column(db.Boolean, default=False)
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)

class Report(db.Model):
    __tablename__ = 'reports'
    
    id = db.Column(db.Integer, primary_key=True)
    reporter_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    reported_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    violation_type = db.Column(db.String(50), nullable=False)  # privacy_violation, harassment, spam, etc.
    description_encrypted = db.Column(db.Text, nullable=False)
    evidence = db.Column(db.JSON)
    status = db.Column(db.String(20), default='pending')  # pending, investigating, resolved, dismissed
    resolution = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolved_at = db.Column(db.DateTime)

class Penalty(db.Model):
    __tablename__ = 'penalties'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    report_id = db.Column(db.Integer, db.ForeignKey('reports.id'))
    penalty_type = db.Column(db.String(50), nullable=False)  # warning, suspension, ban, fine
    reason = db.Column(db.Text, nullable=False)
    amount = db.Column(db.Float)  # For fines
    start_date = db.Column(db.DateTime, default=datetime.utcnow)
    end_date = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
