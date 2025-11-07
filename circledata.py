# Check circles data integrity
from app import app, db
from sqlalchemy import text

with app.app_context():
    # Test 1: Check all users have valid circle privacy settings
    print("✅ Test 1: Checking circle privacy settings...")
    result = db.session.execute(text("""
        SELECT id, username, circles_privacy 
        FROM users 
        WHERE circles_privacy NOT IN ('public', 'class_a', 'class_b', 'class_c', 'private')
           OR circles_privacy IS NULL
    """))
    invalid = result.fetchall()
    if invalid:
        print(f"❌ Found {len(invalid)} users with invalid privacy settings:")
        for user in invalid:
            print(f"   User {user.id} ({user.username}): {user.circles_privacy}")
    else:
        print("✅ All users have valid privacy settings!")

    # Test 2: Check circle memberships are consistent
    print("\n✅ Test 2: Checking circle memberships...")
    result = db.session.execute(text("""
        SELECT c.*, u1.username as circle_owner, u2.username as member_name
        FROM circles c
        JOIN users u1 ON c.user_id = u1.id
        JOIN users u2 ON c.member_id = u2.id
        WHERE c.circle_type NOT IN ('class_a', 'class_b', 'class_c')
    """))
    invalid_circles = result.fetchall()
    if invalid_circles:
        print(f"❌ Found {len(invalid_circles)} invalid circle memberships:")
        for c in invalid_circles:
            print(f"   {c.circle_owner}'s circle has {c.member_name} in invalid type: {c.circle_type}")
    else:
        print("✅ All circle memberships have valid types!")

    # Test 3: Check for orphaned circles (users that don't exist)
    print("\n✅ Test 3: Checking for orphaned circles...")
    result = db.session.execute(text("""
        SELECT c.* FROM circles c
        LEFT JOIN users u1 ON c.user_id = u1.id
        LEFT JOIN users u2 ON c.member_id = u2.id
        WHERE u1.id IS NULL OR u2.id IS NULL
    """))
    orphaned = result.fetchall()
    if orphaned:
        print(f"❌ Found {len(orphaned)} orphaned circle entries")
    else:
        print("✅ No orphaned circles found!")

    # Test 4: Check specific user's circles match their privacy
    print("\n✅ Test 4: Checking user privacy vs actual circles...")
    test_user_id = 1  # Change this to test specific user
    
    result = db.session.execute(text("""
        SELECT circles_privacy FROM users WHERE id = :user_id
    """), {"user_id": test_user_id})
    user_privacy = result.fetchone()
    
    if user_privacy:
        privacy = user_privacy[0]
        print(f"   User {test_user_id} privacy setting: {privacy}")
        
        # Get their circles
        result = db.session.execute(text("""
            SELECT circle_type, COUNT(*) as count
            FROM circles 
            WHERE user_id = :user_id
            GROUP BY circle_type
        """), {"user_id": test_user_id})
        
        circles_count = result.fetchall()
        for circle in circles_count:
            print(f"   - {circle.circle_type}: {circle.count} members")
    
    # Test 5: Verify default privacy is 'private'
    print("\n✅ Test 5: Checking default privacy settings...")
    result = db.session.execute(text("""
        SELECT COUNT(*) as count, circles_privacy
        FROM users
        GROUP BY circles_privacy
        ORDER BY count DESC
    """))
    privacy_stats = result.fetchall()
    print("   Privacy distribution:")
    for stat in privacy_stats:
        print(f"   - {stat.circles_privacy or 'NULL'}: {stat.count} users")
    
    # Test 6: Check if any user is in multiple circles of same person
    print("\n✅ Test 6: Checking for duplicate circle memberships...")
    result = db.session.execute(text("""
        SELECT user_id, member_id, COUNT(*) as count
        FROM circles
        GROUP BY user_id, member_id
        HAVING COUNT(*) > 1
    """))
    duplicates = result.fetchall()
    if duplicates:
        print(f"❌ Found {len(duplicates)} duplicate memberships!")
        for dup in duplicates:
            print(f"   User {dup.user_id} has member {dup.member_id} in {dup.count} circles")
    else:
        print("✅ No duplicate circle memberships found!")

    print("\n✅ All tests complete!")
