#!/usr/bin/env python
"""
Check and reset user passwords
Run in Render shell: python fix_password.py
"""

import os
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Database setup
DATABASE_URL = os.environ.get('DATABASE_URL', '')
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)


def check_password(email, password):
    """Check if password matches for a user"""
    print("\n" + "="*80)
    print(f"CHECKING PASSWORD FOR: {email}")
    print("="*80)
    
    session = Session()
    try:
        result = session.execute(text("""
            SELECT id, username, email, password_hash
            FROM users 
            WHERE email = :email
        """), {'email': email})
        
        user = result.fetchone()
        
        if not user:
            print(f"❌ User not found: {email}")
            return False
        
        print(f"✅ User found: {user[1]} (ID: {user[0]})")
        print(f"   Testing password: {password}")
        
        # Check if password matches
        password_hash = user[3]
        matches = check_password_hash(password_hash, password)
        
        if matches:
            print(f"✅ Password is CORRECT!")
            return True
        else:
            print(f"❌ Password is INCORRECT!")
            print(f"   Password hash starts with: {password_hash[:30]}...")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        session.close()


def reset_password(email, new_password, confirm=False):
    """Reset password for a user"""
    print("\n" + "="*80)
    print(f"RESETTING PASSWORD FOR: {email}")
    print("="*80)
    
    if not confirm:
        print("❌ Must pass confirm=True to reset password")
        print("   This is a safety check to prevent accidental resets")
        return False
    
    session = Session()
    try:
        # Check if user exists
        result = session.execute(text("""
            SELECT id, username, email
            FROM users 
            WHERE email = :email
        """), {'email': email})
        
        user = result.fetchone()
        
        if not user:
            print(f"❌ User not found: {email}")
            return False
        
        print(f"✅ User found: {user[1]} (ID: {user[0]})")
        print(f"   Generating new password hash for: {new_password}")
        
        # Generate new password hash
        new_hash = generate_password_hash(new_password)
        
        print(f"   New hash starts with: {new_hash[:30]}...")
        
        # Update password
        session.execute(text("""
            UPDATE users 
            SET password_hash = :password_hash,
                updated_at = NOW()
            WHERE email = :email
        """), {
            'email': email,
            'password_hash': new_hash
        })
        
        session.commit()
        
        print(f"✅ Password reset successfully!")
        print(f"   New password: {new_password}")
        
        # Verify the password works
        print("\n   Verifying new password...")
        if check_password_hash(new_hash, new_password):
            print("   ✅ New password verified!")
            return True
        else:
            print("   ❌ New password verification failed!")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        session.rollback()
        return False
    finally:
        session.close()


def show_password_info(email):
    """Show password hash information (for debugging)"""
    print("\n" + "="*80)
    print(f"PASSWORD INFO FOR: {email}")
    print("="*80)
    
    session = Session()
    try:
        result = session.execute(text("""
            SELECT id, username, email, password_hash, updated_at
            FROM users 
            WHERE email = :email
        """), {'email': email})
        
        user = result.fetchone()
        
        if not user:
            print(f"❌ User not found: {email}")
            return
        
        print(f"User ID: {user[0]}")
        print(f"Username: {user[1]}")
        print(f"Email: {user[2]}")
        print(f"Password Hash: {user[3][:50]}...")
        print(f"Hash Length: {len(user[3])}")
        print(f"Hash Algorithm: {'bcrypt' if user[3].startswith('$2b$') else 'unknown'}")
        print(f"Last Updated: {user[4]}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        session.close()


def diagnose_login_issue(email, password):
    """Complete diagnosis of why login might be failing"""
    print("\n" + "🔍"*40)
    print("DIAGNOSING LOGIN ISSUE")
    print("🔍"*40)
    
    # 1. Check if user exists
    session = Session()
    try:
        result = session.execute(text("""
            SELECT id, username, email, password_hash, is_active, last_login
            FROM users 
            WHERE email = :email
        """), {'email': email})
        
        user = result.fetchone()
        
        if not user:
            print(f"\n❌ PROBLEM: User does not exist: {email}")
            return
        
        print(f"\n✅ User exists: {user[1]} (ID: {user[0]})")
        print(f"   Email: {user[2]}")
        print(f"   Active: {user[4]}")
        print(f"   Last Login: {user[5]}")
        
        # 2. Check if user is active
        if not user[4]:
            print(f"\n❌ PROBLEM: User is inactive!")
            return
        
        print(f"\n✅ User is active")
        
        # 3. Check password
        print(f"\n🔍 Checking password...")
        password_hash = user[3]
        
        print(f"   Password hash: {password_hash[:50]}...")
        print(f"   Hash length: {len(password_hash)}")
        print(f"   Algorithm: {'bcrypt' if password_hash.startswith('$2b$') else 'unknown'}")
        
        matches = check_password_hash(password_hash, password)
        
        if matches:
            print(f"\n✅ Password is CORRECT!")
            print(f"\n🎉 LOGIN SHOULD WORK!")
            print(f"   If login still fails, the issue is in the application code,")
            print(f"   not in the database.")
        else:
            print(f"\n❌ PROBLEM: Password is INCORRECT!")
            print(f"   The password hash in the database does not match '{password}'")
            print(f"\n💡 SOLUTION: Reset the password using:")
            print(f"   python fix_password.py --reset {email} --password {password}")
        
    except Exception as e:
        print(f"\n❌ Error during diagnosis: {e}")
    finally:
        session.close()


# Main execution
if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Check and fix user passwords')
    parser.add_argument('--check', type=str, help='Check password for email')
    parser.add_argument('--password', type=str, help='Password to check/set')
    parser.add_argument('--reset', type=str, help='Reset password for email')
    parser.add_argument('--confirm', action='store_true', help='Confirm password reset')
    parser.add_argument('--info', type=str, help='Show password info for email')
    parser.add_argument('--diagnose', type=str, help='Diagnose login issue for email')
    
    args = parser.parse_args()
    
    if args.diagnose:
        if not args.password:
            print("❌ Must provide --password with --diagnose")
        else:
            diagnose_login_issue(args.diagnose, args.password)
    
    elif args.check:
        if not args.password:
            print("❌ Must provide --password with --check")
        else:
            check_password(args.check, args.password)
    
    elif args.reset:
        if not args.password:
            print("❌ Must provide --password with --reset")
        elif not args.confirm:
            print("❌ Must provide --confirm flag to reset password")
            print("   Example: python fix_password.py --reset email@example.com --password newpass123 --confirm")
        else:
            reset_password(args.reset, args.password, confirm=True)
    
    elif args.info:
        show_password_info(args.info)
    
    else:
        # Default: diagnose the known problem user
        print("🔍 Running default diagnosis for emaskanazi@gmail.com")
        diagnose_login_issue('emaskanazi@gmail.com', 'password123')
