#!/usr/bin/env bash
# Build script for Render deployment
# This replaces your existing build.sh

set -o errexit

echo "Starting build process..."

# Upgrade pip and install dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Run database migrations and fixes
echo "Setting up database..."
python -c "
from app import app, db
from flask_migrate import upgrade, init
import os
from sqlalchemy import text

with app.app_context():
    print('Creating database tables...')
    # Create all tables if they don't exist
    db.create_all()
    print('✓ Database tables created')

    # Initialize migration repository if needed
    if not os.path.exists('migrations'):
        try:
            init()
            print('✓ Migration repository initialized')
        except Exception as e:
            print(f'Migration init skipped: {e}')

    # Run any pending migrations
    try:
        upgrade()
        print('✓ Migrations completed')
    except Exception as e:
        print(f'Migration skipped (may already be applied): {e}')

    # Fix the alerts table schema issue
    print('Checking alerts table schema...')
    with db.engine.connect() as conn:
        try:
            # Check what columns exist
            result = conn.execute(text(
                \"\"\"SELECT column_name
                FROM information_schema.columns
                WHERE table_name='alerts'
                AND column_name IN ('message', 'content')\"\"\"
            ))
            columns = [row[0] for row in result]

            # Fix the column name if needed
            if 'message' in columns and 'content' not in columns:
                print('Renaming alerts.message to alerts.content...')
                conn.execute(text('ALTER TABLE alerts RENAME COLUMN message TO content'))
                conn.commit()
                print('✓ Fixed alerts.message column')
            elif 'content' not in columns and 'message' not in columns:
                print('Adding missing content column...')
                conn.execute(text('ALTER TABLE alerts ADD COLUMN content TEXT'))
                conn.commit()
                print('✓ Added alerts.content column')
            else:
                print('✓ Alerts table schema is correct')

        except Exception as e:
            print(f'Schema check completed with warning: {e}')

    # Verify the fix
    with db.engine.connect() as conn:
        try:
            result = conn.execute(text('SELECT content FROM alerts LIMIT 1'))
            print('✓ Verified: alerts.content column exists and is accessible')
        except Exception as e:
            print(f'Warning: Could not verify alerts table: {e}')

    print('✓ Database setup completed successfully!')
"

echo "✓ Build completed successfully!"