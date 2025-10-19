#!/usr/bin/env python
"""
fix_database.py - Add missing columns to existing database
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

with engine.connect() as conn:
    try:
        # Add missing columns one by one (PostgreSQL safe)
        logger.info("Adding missing columns to users table...")
        
        # Add username column if missing
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN username VARCHAR(80)"))
            conn.commit()
            logger.info("Added username column")
        except:
            logger.info("Username column already exists")
        
        # Add role column if missing
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR(50) DEFAULT 'user'"))
            conn.commit()
            logger.info("Added role column")
        except:
            logger.info("Role column already exists")
        
        # Add is_active column if missing
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT TRUE"))
            conn.commit()
            logger.info("Added is_active column")
        except:
            logger.info("is_active column already exists")
        
        # Add updated_at column if missing
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"))
            conn.commit()
            logger.info("Added updated_at column")
        except:
            logger.info("updated_at column already exists")
        
        # Generate usernames from emails for existing users
        logger.info("Setting usernames for existing users...")
        result = conn.execute(text("SELECT id, email FROM users WHERE username IS NULL"))
        users = result.fetchall()
        
        for user in users:
            user_id, email = user
            username = f"{email.split('@')[0]}_{user_id}"
            conn.execute(
                text("UPDATE users SET username = :username WHERE id = :id"),
                {"username": username, "id": user_id}
            )
        conn.commit()
        
        logger.info("Database fix complete!")
        
    except Exception as e:
        logger.error(f"Error: {e}")
        raise

print("✓ Database schema fixed successfully!")
