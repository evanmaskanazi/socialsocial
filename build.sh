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

    # Use begin() for proper transaction handling
    with db.engine.begin() as conn:
        # CRITICAL FIX: Make ALL problematic columns nullable
        problematic_columns = [
            'anonymous_id', 'email_encrypted', 'username_encrypted',
            'display_name', 'encrypted_username', 'encrypted_email'
        ]

        for col in problematic_columns:
            try:
                result = conn.execute(text(f'''
                    SELECT column_name, is_nullable
                    FROM information_schema.columns
                    WHERE table_name=\\'users\\' AND column_name=\\'{col}\\'
                '''))
                row = result.fetchone()
                if row and row[1] == 'NO':
                    logger.info(f'Making {col} nullable...')
                    conn.execute(text(f'ALTER TABLE users ALTER COLUMN {col} DROP NOT NULL'))
                    logger.info(f'✓ Fixed {col} to be nullable')
            except Exception as e:
                pass  # Column doesn't exist, that's fine

        # Fix alerts table
        try:
            result = conn.execute(text(
                '''SELECT column_name FROM information_schema.columns
                WHERE table_name=\\'alerts\\' AND column_name IN (\\'message\\', \\'content\\')'''
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
                '''SELECT column_name FROM information_schema.columns WHERE table_name=\\'profiles\\''''
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

        # Fix circles table - make name column nullable
        try:
            result = conn.execute(text(
                '''SELECT column_name, is_nullable
                FROM information_schema.columns
                WHERE table_name=\\'circles\\' AND column_name=\\'name\\''''
            ))
            row = result.fetchone()
            if row and row[1] == 'NO':
                logger.info('Making circles.name nullable...')
                conn.execute(text('ALTER TABLE circles ALTER COLUMN name DROP NOT NULL'))
                logger.info('✓ Fixed circles.name to be nullable')
        except Exception as e:
            logger.warning(f'Circles name fix: {e}')

        # Ensure activities table exists
        try:
            result = conn.execute(text(
                '''SELECT table_name FROM information_schema.tables WHERE table_name=\\'activities\\''''
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
    try:
        from app import init_database
        init_database()
        logger.info('✓ Database initialized with test users')
    except Exception as e:
        logger.error(f'Test user creation error: {e}')
"

echo "=== Build completed successfully! ==="