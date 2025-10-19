#!/usr/bin/env bash
# Build script for Render deployment
# Handles database migrations and schema fixes automatically

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
    # Create all tables first
    db.create_all()
    logger.info('✓ Ensured all tables exist')

    with db.engine.connect() as conn:
        # Fix alerts table
        try:
            result = conn.execute(text(
                \"\"\"SELECT column_name FROM information_schema.columns
                WHERE table_name='alerts' AND column_name IN ('message', 'content')\"\"\"
            ))
            columns = [row[0] for row in result]

            if 'message' in columns and 'content' not in columns:
                conn.execute(text('ALTER TABLE alerts RENAME COLUMN message TO content'))
                conn.commit()
                logger.info('✓ Fixed alerts.message column')
            elif 'content' not in columns:
                conn.execute(text('ALTER TABLE alerts ADD COLUMN content TEXT'))
                conn.commit()
                logger.info('✓ Added alerts.content column')
        except Exception as e:
            logger.warning(f'Alerts fix skipped: {e}')

        # Fix profiles table - add missing columns
        try:
            result = conn.execute(text(
                \"\"\"SELECT column_name FROM information_schema.columns WHERE table_name='profiles'\"\"\"
            ))
            existing = [row[0] for row in result]

            columns_to_add = [
                ('mood_status', 'VARCHAR(50)'),
                ('avatar_url', 'VARCHAR(500)')
            ]

            for col_name, col_type in columns_to_add:
                if col_name not in existing:
                    conn.execute(text(f'ALTER TABLE profiles ADD COLUMN {col_name} {col_type}'))
                    conn.commit()
                    logger.info(f'✓ Added profiles.{col_name} column')
        except Exception as e:
            logger.warning(f'Profiles fix skipped: {e}')

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
                conn.commit()
                logger.info('✓ Created activities table')
        except Exception as e:
            logger.warning(f'Activities table skipped: {e}')

    # Initialize database
    try:
        from app import init_database
        init_database()
        logger.info('✓ Database initialized')
    except Exception as e:
        logger.warning(f'Init skipped: {e}')

    logger.info('✓ Schema fixes complete!')
"

echo "=== Build completed successfully! ==="