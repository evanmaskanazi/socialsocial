"""
Database initialization for Thera Social
"""
import os
import sys
from datetime import datetime

def initialize_database():
    """Initialize database with required tables and default data"""
    from app import app, db
    from models import User, Circle, Parameter
    
    print("Initializing Thera Social database...")
    
    with app.app_context():
        # Create all tables
        db.create_all()
        print("✓ Database tables created")
        
        # Create indexes for performance
        from sqlalchemy import text
        
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_users_anonymous_id ON users(anonymous_id)",
            "CREATE INDEX IF NOT EXISTS idx_follows_follower ON follows(follower_id)",
            "CREATE INDEX IF NOT EXISTS idx_follows_followed ON follows(followed_id)",
            "CREATE INDEX IF NOT EXISTS idx_posts_user_created ON posts(user_id, created_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_messages_conversation ON private_messages(sender_id, recipient_id, sent_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_alerts_user_unread ON alerts(user_id, is_read, created_at DESC)",
            "CREATE INDEX IF NOT EXISTS idx_parameter_values_lookup ON parameter_values(parameter_id, recorded_at DESC)",
        ]
        
        for index in indexes:
            try:
                db.session.execute(text(index))
                db.session.commit()
            except Exception as e:
                print(f"Note: Index might already exist - {str(e)}")
                db.session.rollback()
        
        print("✓ Database indexes created")
        
        # Create system user for notifications (only if doesn't exist)
        try:
            from security import encrypt_field
            from auth import AuthManager
            
            system_user = User.query.filter_by(anonymous_id='SYSTEM').first()
            if not system_user:
                auth_manager = AuthManager(app, db, None)
                
                system_user = User(
                    anonymous_id='SYSTEM',
                    email_encrypted=encrypt_field('system@therasocial.internal'),
                    password_hash=auth_manager.hash_password(os.urandom(32).hex()),
                    display_name='System',
                    is_active=True,
                    is_verified=True
                )
                db.session.add(system_user)
                db.session.commit()
                print("✓ System user created")
            else:
                print("✓ System user already exists")
        except Exception as e:
            print(f"System user creation skipped: {str(e)}")
            db.session.rollback()
        
        print("✓ Database initialization complete!")

if __name__ == '__main__':
    # Add parent directory to path
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    from app import app, db
    initialize_database()
