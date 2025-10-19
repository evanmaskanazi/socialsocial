#!/usr/bin/env python
"""
create_sample_users.py - Create 12 sample users for testing circles
"""
import os
from sqlalchemy import create_engine, text
from werkzeug.security import generate_password_hash
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Sample users data
SAMPLE_USERS = [
    {'username': 'alice_wonder', 'email': 'alice@example.com', 'name': 'Alice Wonder'},
    {'username': 'bob_builder', 'email': 'bob@example.com', 'name': 'Bob Builder'},
    {'username': 'charlie_day', 'email': 'charlie@example.com', 'name': 'Charlie Day'},
    {'username': 'diana_prince', 'email': 'diana@example.com', 'name': 'Diana Prince'},
    {'username': 'edward_snow', 'email': 'edward@example.com', 'name': 'Edward Snow'},
    {'username': 'fiona_green', 'email': 'fiona@example.com', 'name': 'Fiona Green'},
    {'username': 'george_lucas', 'email': 'george@example.com', 'name': 'George Lucas'},
    {'username': 'helen_troy', 'email': 'helen@example.com', 'name': 'Helen Troy'},
    {'username': 'ivan_terrible', 'email': 'ivan@example.com', 'name': 'Ivan Terrible'},
    {'username': 'julia_roberts', 'email': 'julia@example.com', 'name': 'Julia Roberts'},
    {'username': 'kevin_hart', 'email': 'kevin@example.com', 'name': 'Kevin Hart'},
    {'username': 'lisa_simpson', 'email': 'lisa@example.com', 'name': 'Lisa Simpson'}
]

# Get database URL
DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///social.db')

# Fix for Render PostgreSQL
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

logger.info("Connecting to database...")
engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    created_count = 0
    skipped_count = 0
    
    # Default password for all sample users
    default_password = generate_password_hash('password123')
    
    for user_data in SAMPLE_USERS:
        trans = conn.begin()
        try:
            # Check if user already exists
            result = conn.execute(
                text("SELECT id FROM users WHERE email = :email OR username = :username"),
                {"email": user_data['email'], "username": user_data['username']}
            )
            
            if result.fetchone():
                logger.info(f"User {user_data['username']} already exists, skipping...")
                skipped_count += 1
                trans.rollback()
                continue
            
            # Insert new user
            result = conn.execute(text("""
                INSERT INTO users (username, email, password_hash, role, is_active, created_at, updated_at)
                VALUES (:username, :email, :password_hash, 'user', TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                RETURNING id
            """), {
                "username": user_data['username'],
                "email": user_data['email'],
                "password_hash": default_password
            })
            
            user_id = result.scalar()
            
            # Create profile for the user
            conn.execute(text("""
                INSERT INTO profiles (user_id, bio, interests, occupation, goals, favorite_hobbies, created_at, updated_at)
                VALUES (:user_id, :bio, :interests, :occupation, :goals, :hobbies, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """), {
                "user_id": user_id,
                "bio": f"Hi, I'm {user_data['name']}! I'm here to connect and share experiences.",
                "interests": "Technology, Travel, Music, Books, Photography",
                "occupation": "Professional",
                "goals": "Connect with interesting people and build meaningful relationships",
                "hobbies": "Reading, Hiking, Cooking, Gaming, Art"
            })
            
            trans.commit()
            created_count += 1
            logger.info(f"Created user: {user_data['username']} (ID: {user_id})")
            
        except Exception as e:
            trans.rollback()
            logger.error(f"Failed to create user {user_data['username']}: {e}")
    
    # Summary
    print(f"""
    ========================================
    Sample Users Creation Complete!
    ========================================
    Created: {created_count} new users
    Skipped: {skipped_count} existing users
    
    All sample users have password: password123
    
    You can now login and add these users to your circles:
    - General Circle
    - Close Friends
    - Family
    ========================================
    """)
    
    # Show all users in the system
    print("Current users in the system:")
    result = conn.execute(text("SELECT id, username, email FROM users ORDER BY id"))
    for row in result:
        print(f"  ID: {row[0]}, Username: {row[1]}, Email: {row[2]}")
