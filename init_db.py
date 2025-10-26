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
        
        # Migrate parameters table if needed
        migrate_parameters_table(db)
        
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

def migrate_parameters_table(db):
    """Migrate parameters table from text to numeric values (5 categories)"""
    from sqlalchemy import text
    
    print("Checking parameters table for migration...")
    
    try:
        # Check current schema
        result = db.session.execute(text("PRAGMA table_info(parameters)"))
        columns = {row[1]: row[2] for row in result}
        
        needs_migration = False
        
        # Add physical_activity column if we have old exercise column
        if 'exercise' in columns and 'physical_activity' not in columns:
            needs_migration = True
            try:
                db.session.execute(text(
                    'ALTER TABLE parameters ADD COLUMN physical_activity INTEGER CHECK (physical_activity >= 1 AND physical_activity <= 4)'
                ))
                db.session.commit()
                print("✓ Added physical_activity column")
            except Exception as e:
                print(f"  Note: physical_activity column might already exist")
                db.session.rollback()
        
        # Add sleep_quality column if it doesn't exist
        if 'sleep_quality' not in columns:
            needs_migration = True
            try:
                db.session.execute(text(
                    'ALTER TABLE parameters ADD COLUMN sleep_quality INTEGER CHECK (sleep_quality >= 1 AND sleep_quality <= 4)'
                ))
                db.session.commit()
                print("✓ Added sleep_quality column")
            except Exception as e:
                print(f"  Note: sleep_quality column might already exist")
                db.session.rollback()
        
        # Ensure energy column exists (single column for combined physical/mental)
        if 'energy' not in columns:
            needs_migration = True
            try:
                db.session.execute(text(
                    'ALTER TABLE parameters ADD COLUMN energy INTEGER CHECK (energy >= 1 AND energy <= 4)'
                ))
                db.session.commit()
                print("✓ Added energy column")
            except Exception as e:
                print(f"  Note: energy column might already exist")
                db.session.rollback()
        
        # Migrate existing data from text to numeric
        if needs_migration or columns.get('mood') == 'TEXT':
            print("Migrating parameter values from text to numeric...")
            
            # Migrate mood values
            db.session.execute(text('''
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
            '''))
            
            # Copy exercise to physical_activity and convert to numeric
            if 'exercise' in columns and 'physical_activity' in columns:
                db.session.execute(text('''
                    UPDATE parameters 
                    SET physical_activity = CASE 
                        WHEN exercise IN ('none', '1', 'no') THEN 1
                        WHEN exercise IN ('light', '2', 'mild') THEN 2
                        WHEN exercise IN ('moderate', '3', 'medium') THEN 3
                        WHEN exercise IN ('intense', 'high', '4', 'heavy') THEN 4
                        WHEN CAST(exercise AS INTEGER) BETWEEN 1 AND 4 THEN CAST(exercise AS INTEGER)
                        ELSE NULL
                    END
                    WHERE exercise IS NOT NULL AND physical_activity IS NULL
                '''))
            
            # Migrate anxiety values
            db.session.execute(text('''
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
            '''))
            
            # Migrate energy values (single column for physical and mental combined)
            db.session.execute(text('''
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
            '''))
            
            # Convert sleep_hours to sleep_quality if needed
            if 'sleep_hours' in columns and 'sleep_quality' in columns:
                db.session.execute(text('''
                    UPDATE parameters 
                    SET sleep_quality = CASE 
                        WHEN sleep_hours <= 4 THEN 1
                        WHEN sleep_hours > 4 AND sleep_hours <= 6 THEN 2
                        WHEN sleep_hours > 6 AND sleep_hours <= 8 THEN 3
                        WHEN sleep_hours > 8 THEN 4
                        ELSE NULL
                    END
                    WHERE sleep_hours IS NOT NULL AND sleep_quality IS NULL
                '''))
            
            # If there were separate physical_energy and mental_energy columns, consolidate them
            if 'physical_energy' in columns and 'mental_energy' in columns:
                print("Consolidating physical_energy and mental_energy into single energy column...")
                db.session.execute(text('''
                    UPDATE parameters 
                    SET energy = ROUND((COALESCE(physical_energy, 0) + COALESCE(mental_energy, 0)) / 2.0)
                    WHERE energy IS NULL AND (physical_energy IS NOT NULL OR mental_energy IS NOT NULL)
                '''))
            
            db.session.commit()
            print("✓ Parameter values migrated to numeric format")
        else:
            print("✓ Parameters table is up to date")
            
    except Exception as e:
        print(f"Warning: Could not check/migrate parameters table: {str(e)}")
        db.session.rollback()

if __name__ == '__main__':
    # Add parent directory to path
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    from app import app, db
    initialize_database()

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    from app import app, db
    initialize_database()
