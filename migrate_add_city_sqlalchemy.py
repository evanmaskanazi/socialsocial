#!/usr/bin/env python3
"""
One-time migration script to add selected_city column to users table.

Usage:
    python migrate_add_city.py

This script will:
1. Connect to your Render PostgreSQL database
2. Check if selected_city column already exists
3. Add the column if it doesn't exist
4. Verify the migration was successful
5. Show sample data

Safe to run multiple times (idempotent).
"""

import os
import sys
import psycopg2
from psycopg2 import sql

def get_database_url():
    """Get DATABASE_URL from environment or prompt user"""
    # Try to get from environment first (Render automatically sets this)
    db_url = os.environ.get('DATABASE_URL')
    
    if db_url:
        print(f"✓ Found DATABASE_URL in environment")
        return db_url
    
    # If not in environment, prompt user
    print("\nDATABASE_URL not found in environment.")
    print("Please paste your Render PostgreSQL connection string:")
    print("(Format: postgresql://user:password@host:port/database)")
    print()
    db_url = input("DATABASE_URL: ").strip()
    
    if not db_url:
        print("❌ Error: DATABASE_URL is required")
        sys.exit(1)
    
    return db_url

def check_column_exists(cursor, table_name, column_name):
    """Check if a column exists in a table"""
    cursor.execute("""
        SELECT EXISTS (
            SELECT 1 
            FROM information_schema.columns 
            WHERE table_name = %s 
            AND column_name = %s
        );
    """, (table_name, column_name))
    
    return cursor.fetchone()[0]

def show_table_structure(cursor, table_name):
    """Display the table structure"""
    cursor.execute("""
        SELECT column_name, data_type, character_maximum_length, column_default
        FROM information_schema.columns
        WHERE table_name = %s
        ORDER BY ordinal_position;
    """, (table_name,))
    
    columns = cursor.fetchall()
    
    print(f"\n📋 Structure of '{table_name}' table:")
    print("=" * 80)
    print(f"{'Column Name':<25} {'Data Type':<20} {'Max Length':<12} {'Default':<20}")
    print("-" * 80)
    
    for col in columns:
        col_name, data_type, max_length, default = col
        max_len_str = str(max_length) if max_length else 'N/A'
        default_str = str(default)[:18] if default else 'None'
        print(f"{col_name:<25} {data_type:<20} {max_len_str:<12} {default_str:<20}")
    
    print("=" * 80)

def show_sample_data(cursor):
    """Show sample data from users table"""
    cursor.execute("""
        SELECT id, username, selected_city 
        FROM users 
        LIMIT 5;
    """)
    
    rows = cursor.fetchall()
    
    print(f"\n📊 Sample data (first 5 users):")
    print("=" * 80)
    print(f"{'ID':<6} {'Username':<30} {'Selected City':<40}")
    print("-" * 80)
    
    if rows:
        for row in rows:
            user_id, username, city = row
            city_str = city if city else 'NULL'
            print(f"{user_id:<6} {username:<30} {city_str:<40}")
    else:
        print("(No users found in database)")
    
    print("=" * 80)

def main():
    print("=" * 80)
    print("  MIGRATION SCRIPT: Add selected_city column to users table")
    print("=" * 80)
    print()
    
    # Get database URL
    database_url = get_database_url()
    
    # Connect to database
    print("\n🔌 Connecting to database...")
    try:
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        print("✓ Connected successfully")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        sys.exit(1)
    
    try:
        # Check if column already exists
        print("\n🔍 Checking if 'selected_city' column exists...")
        column_exists = check_column_exists(cursor, 'users', 'selected_city')
        
        if column_exists:
            print("✓ Column 'selected_city' already exists - no migration needed")
            print("   (Safe to run this script multiple times)")
        else:
            print("⚠ Column 'selected_city' does NOT exist - will add it now")
            
            # Add the column
            print("\n📝 Running migration: ALTER TABLE users ADD COLUMN...")
            cursor.execute("""
                ALTER TABLE users 
                ADD COLUMN selected_city VARCHAR(100) 
                DEFAULT 'Jerusalem, Israel';
            """)
            
            # Commit the change
            conn.commit()
            print("✅ Migration successful! Column 'selected_city' has been added")
            print("   Default value: 'Jerusalem, Israel'")
        
        # Show table structure
        show_table_structure(cursor, 'users')
        
        # Show sample data
        show_sample_data(cursor)
        
        # Count total users
        cursor.execute("SELECT COUNT(*) FROM users;")
        total_users = cursor.fetchone()[0]
        print(f"\n📈 Total users in database: {total_users}")
        
        if not column_exists:
            print(f"   All {total_users} existing users now have selected_city = 'Jerusalem, Israel'")
        
        print("\n" + "=" * 80)
        print("✅ MIGRATION COMPLETE!")
        print("=" * 80)
        print("\nNext steps:")
        print("1. Deploy the new app.py with selected_city column defined in User model")
        print("2. Your application should now work without 500 errors")
        print("3. You can safely delete this migration script after deployment")
        print()
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        conn.rollback()
        sys.exit(1)
    
    finally:
        # Clean up
        cursor.close()
        conn.close()
        print("🔌 Database connection closed")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠ Migration cancelled by user")
        sys.exit(1)
