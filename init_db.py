"""
Database initialization for Thera Social
"""
import os
import sys
from datetime import datetime

def initialize_database():
    from app import app, db
    
    with app.app_context():
        db.create_all()  # SQLAlchemy creates from models
        
        # Run migration for existing data
        from app import migrate_parameters_data, get_db
        try:
            db_conn = get_db()
            migrate_parameters_data(db_conn)
        except Exception as e:
            print(f"Migration skipped or already done: {e}")
            pass
            
        print("✓ Database initialized")

if __name__ == '__main__':
    # Add parent directory to path
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    from app import app, db
    initialize_database()
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    from app import app, db
    initialize_database()
