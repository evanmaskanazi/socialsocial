#!/usr/bin/env bash
# Build script for Render deployment
set -o errexit
echo "=== Starting Render build process ==="

# Upgrade pip and install dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Fix all database schema issues
echo "Fixing database schema..."
python -c "
from app import app, db
from sqlalchemy import text
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('build_script')

with app.app_context():
    db.create_all()
    logger.info('✓ Ensured all tables exist')

    # Use begin() instead of connect() for proper transaction handling
    with db.engine.begin() as conn:
        # CRITICAL FIX: Make anonymous_id nullable
        try:
            result = conn.execute(text(
                \"\"\"SELECT column_name, is_nullable
                FROM information_schema.columns
                WHERE table_name='users' AND column_name='anonymous_id'\"\"\"
            ))
            row = result.fetchone()
            if row:
                col_name, is_nullable = row[0], row[1]
                if is_nullable == 'NO':
                    logger.info('Found anonymous_id column with NOT NULL constraint, fixing...')
                    conn.execute(text('ALTER TABLE users ALTER COLUMN anonymous_id DROP NOT NULL'))
                    logger.info('✓ Fixed anonymous_id to be nullable')
                else:
                    logger.info('✓ anonymous_id column already nullable')
            else:
                logger.info('✓ No anonymous_id column found (good!)')
        except Exception as e:
            logger.error(f'Anonymous_id fix FAILED: {e}')
            raise  # Don't continue if this fails

        # Fix alerts table
        try:
            result = conn.execute(text(
                \"\"\"SELECT column_name FROM information_schema.columns
                WHERE table_name='alerts' AND column_name IN ('message', 'content')\"\"\"
            ))
            columns = [row[0] for row in result]
            if 'message' in columns and 'content' not in columns:
                conn.execute(text('ALTER TABLE alerts RENAME COLUMN message TO content'))
                logger.info('✓ Fixed alerts.message column')
            elif 'content' not in columns and 'message' not in columns:
                conn.execute(text('ALTER TABLE alerts ADD COLUMN content TEXT'))
                logger.info('✓ Added alerts.content column')
        except Exception as e:
            logger.warning(f'Alerts fix: {e}')

        # Fix profiles table
        try:
            result = conn.execute(text(
                \"\"\"SELECT column_name FROM information_schema.columns WHERE table_name='profiles'\"\"\"
            ))
            existing = [row[0] for row in result]
            columns_to_add = [
                ('mood_status', 'VARCHAR(50)'),
                ('avatar_url', 'VARCHAR(500)'),
                ('interests', 'TEXT'),
                ('occupation', 'VARCHAR(200)'),
                ('goals', 'TEXT'),
                ('favorite_hobbies', 'TEXT')
            ]
            for col_name, col_type in columns_to_add:
                if col_name not in existing:
                    conn.execute(text(f'ALTER TABLE profiles ADD COLUMN {col_name} {col_type}'))
                    logger.info(f'✓ Added profiles.{col_name} column')
        except Exception as e:
            logger.warning(f'Profiles fix: {e}')

        # Ensure activities table exists
        try:
            result = conn.execute(text(
                \"\"\"SELECT table_name FROM information_schema.tables WHERE table_name='activities'\"\"\"
            ))
            if not result.fetchone():
                conn.execute(text('''
                    CREATE TABLE activities (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER REFERENCES users(id),
                        activity_date DATE NOT NULL,
                        post_count INTEGER DEFAULT 0,
                        comment_count INTEGER DEFAULT 0,
                        message_count INTEGER DEFAULT 0,
                        mood_entries JSON,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(user_id, activity_date)
                    )
                '''))
                logger.info('✓ Created activities table')
        except Exception as e:
            logger.warning(f'Activities: {e}')

    logger.info('✓ All schema fixes committed!')

    # NOW initialize database and create test users
    # This runs AFTER the schema is fixed and committed
    try:
        from app import init_database
        init_database()
        logger.info('✓ Database initialized with test users')
    except Exception as e:
        logger.error(f'Test user creation error: {e}')
        # Don't fail build if test users can't be created
        # They'll be created when app starts
"

echo "=== Build completed successfully! ==="