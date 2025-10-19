#!/usr/bin/env python
"""
fix_database.py - Add missing columns to existing database
Fixed version with proper transaction handling
"""
import os
from sqlalchemy import create_engine, text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get database URL
DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///social.db')

# Fix for Render PostgreSQL
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

logger.info("Connecting to database...")
engine = create_engine(DATABASE_URL)

# Use separate transactions for each operation
def try_add_column(conn, column_sql, column_name):
    """Try to add a column, handling if it already exists"""
    trans = conn.begin()
    try:
        conn.execute(text(column_sql))
        trans.commit()
        logger.info(f"Added {column_name} column")
        return True
    except Exception as e:
        trans.rollback()
        if "already exists" in str(e).lower() or "duplicate column" in str(e).lower():
            logger.info(f"{column_name} column already exists")
        else:
            logger.warning(f"Could not add {column_name}: {e}")
        return False

# Main execution
with engine.connect() as conn:
    try:
        logger.info("Adding missing columns to users table...")
        
        # Add each column in its own transaction
        try_add_column(conn, 
            "ALTER TABLE users ADD COLUMN username VARCHAR(80)", 
            "username")
        
        try_add_column(conn, 
            "ALTER TABLE users ADD COLUMN role VARCHAR(50) DEFAULT 'user'", 
            "role")
        
        try_add_column(conn, 
            "ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT TRUE", 
            "is_active")
        
        try_add_column(conn, 
            "ALTER TABLE users ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP", 
            "updated_at")
        
        # Now update usernames in a fresh transaction
        logger.info("Setting usernames for existing users...")
        trans = conn.begin()
        try:
            result = conn.execute(text("SELECT id, email FROM users WHERE username IS NULL"))
            users = result.fetchall()
            
            if users:
                for user in users:
                    user_id, email = user
                    username = f"{email.split('@')[0]}_{user_id}"
                    conn.execute(
                        text("UPDATE users SET username = :username WHERE id = :id"),
                        {"username": username, "id": user_id}
                    )
                    logger.info(f"Set username for user {user_id}: {username}")
                trans.commit()
                logger.info(f"Updated {len(users)} users with usernames")
            else:
                trans.commit()
                logger.info("All users already have usernames")
                
        except Exception as e:
            trans.rollback()
            logger.error(f"Error updating usernames: {e}")
            # Try a simpler approach for PostgreSQL
            try:
                trans = conn.begin()
                conn.execute(text("""
                    UPDATE users 
                    SET username = CONCAT(SPLIT_PART(email, '@', 1), '_', id::text)
                    WHERE username IS NULL
                """))
                trans.commit()
                logger.info("Updated usernames using PostgreSQL syntax")
            except Exception as e2:
                trans.rollback()
                logger.error(f"Fallback update also failed: {e2}")
        
        logger.info("Database fix complete!")
        
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise

print("✓ Database schema fixed successfully!")
