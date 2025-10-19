#!/usr/bin/env python
"""Initialize migrations for the first time"""

import os
import sys
from flask_migrate import init, migrate, upgrade
from app import app, db

def setup_migrations():
    """Initialize Flask-Migrate"""
    with app.app_context():
        # Initialize migration repository
        if not os.path.exists('migrations'):
            init()
            print("✓ Initialized migration repository")
        
        # Create initial migration
        migrate(message='Initial migration with all models')
        print("✓ Created initial migration")
        
        # Apply migration
        upgrade()
        print("✓ Applied migrations to database")
        
        # Fix any schema issues
        from app import initialize_database
        initialize_database()
        print("✓ Fixed any remaining schema issues")

if __name__ == '__main__':
    setup_migrations()
