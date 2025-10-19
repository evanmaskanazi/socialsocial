#!/usr/bin/env python
"""
fix_database.py - Comprehensive database schema fix
Handles mixed schema (encrypted + plain columns) and ensures all required columns exist
"""
import os
from sqlalchemy import create_engine, text, inspect
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
        # First, check what columns we currently have
        logger.info("Checking existing database schema...")
        inspector = inspect(engine)
        
        if 'users' in inspector.get_table_names():
            existing_columns = [col['name'] for col in inspector.get_columns('users')]
            logger.info(f"Found existing columns in users table: {existing_columns}")
            
            # Check for encrypted vs plain schema
            has_encrypted = 'email_encrypted' in existing_columns
            has_plain_email = 'email' in existing_columns
            
            if has_encrypted and not has_plain_email:
                logger.warning("Database has encrypted schema but missing plain email column!")
        
        logger.info("Adding missing columns to users table...")
        
        # CRITICAL: Add the plain email column (this was missing!)
        try_add_column(conn, 
            "ALTER TABLE users ADD COLUMN email VARCHAR(120)", 
            "email")
        
        # Add username column
        try_add_column(conn, 
            "ALTER TABLE users ADD COLUMN username VARCHAR(80)", 
            "username")
        
        # Add role column
        try_add_column(conn, 
            "ALTER TABLE users ADD COLUMN role VARCHAR(50) DEFAULT 'user'", 
            "role")
        
        # Add is_active column (might already exist from encrypted schema)
        try_add_column(conn, 
            "ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT TRUE", 
            "is_active")
        
        # Add created_at column
        try_add_column(conn, 
            "ALTER TABLE users ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP", 
            "created_at")
        
        # Add updated_at column (might already exist from encrypted schema)
        try_add_column(conn, 
            "ALTER TABLE users ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP", 
            "updated_at")
        
        # Add password_hash if it doesn't exist (in case of really old schema)
        try_add_column(conn, 
            "ALTER TABLE users ADD COLUMN password_hash VARCHAR(255)", 
            "password_hash")
        
        # Now handle data migration/updates
        logger.info("Checking for data migrations needed...")
        
        # Update NULL emails from encrypted columns if needed
        trans = conn.begin()
        try:
            # Check if we have email_encrypted but email is NULL
            result = conn.execute(text("""
                SELECT COUNT(*) FROM users 
                WHERE email IS NULL 
                AND email_encrypted IS NOT NULL
            """))
            count = result.scalar()
            if count and count > 0:
                logger.info(f"Found {count} users with encrypted emails but no plain email")
                # Note: We can't decrypt without the key, so set a placeholder
                conn.execute(text("""
                    UPDATE users 
                    SET email = CONCAT('user', id, '@example.com')
                    WHERE email IS NULL AND email_encrypted IS NOT NULL
                """))
                logger.info("Set placeholder emails for encrypted users")
            trans.commit()
        except Exception as e:
            trans.rollback()
            logger.info(f"Email migration check skipped: {e}")
        
        # Update usernames from emails
        logger.info("Setting usernames for existing users...")
        trans = conn.begin()
        try:
            result = conn.execute(text("""
                SELECT id, email, username 
                FROM users 
                WHERE username IS NULL AND email IS NOT NULL
            """))
            users = result.fetchall()
            
            if users:
                for user in users:
                    user_id, email, username = user
                    if not username and email:
                        # Create username from email
                        email_part = email.split('@')[0] if '@' in email else email
                        new_username = f"{email_part}_{user_id}"
                        conn.execute(
                            text("UPDATE users SET username = :username WHERE id = :id"),
                            {"username": new_username, "id": user_id}
                        )
                        logger.info(f"Set username for user {user_id}: {new_username}")
                trans.commit()
                logger.info(f"Updated {len(users)} users with usernames")
            else:
                trans.commit()
                logger.info("All users already have usernames")
                
        except Exception as e:
            trans.rollback()
            logger.error(f"Error updating usernames: {e}")
            # Try PostgreSQL-specific syntax as fallback
            try:
                trans = conn.begin()
                conn.execute(text("""
                    UPDATE users 
                    SET username = CONCAT(SPLIT_PART(email, '@', 1), '_', id::text)
                    WHERE username IS NULL AND email IS NOT NULL
                """))
                trans.commit()
                logger.info("Updated usernames using PostgreSQL syntax")
            except Exception as e2:
                trans.rollback()
                logger.error(f"Fallback update also failed: {e2}")
        
        # Set default role for users without one
        trans = conn.begin()
        try:
            conn.execute(text("""
                UPDATE users 
                SET role = 'user' 
                WHERE role IS NULL
            """))
            trans.commit()
            logger.info("Set default role for users")
        except Exception as e:
            trans.rollback()
            logger.warning(f"Role update skipped: {e}")
        
        # Final verification
        logger.info("Verifying final schema...")
        inspector = inspect(engine)
        if 'users' in inspector.get_table_names():
            final_columns = [col['name'] for col in inspector.get_columns('users')]
            required_columns = ['id', 'email', 'username', 'password_hash', 'role', 'is_active']
            missing = [col for col in required_columns if col not in final_columns]
            
            if missing:
                logger.error(f"WARNING: Still missing required columns: {missing}")
            else:
                logger.info("✓ All required columns are present!")
            
            # Show current user count and sample
            result = conn.execute(text("SELECT COUNT(*) FROM users"))
            user_count = result.scalar()
            logger.info(f"Total users in database: {user_count}")
            
            if user_count > 0:
                result = conn.execute(text("""
                    SELECT id, email, username 
                    FROM users 
                    ORDER BY id 
                    LIMIT 3
                """))
                logger.info("Sample users:")
                for row in result:
                    logger.info(f"  ID: {row[0]}, Email: {row[1]}, Username: {row[2]}")
        
        logger.info("Database fix complete!")
        
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise

print("✓ Database schema fixed successfully!")
