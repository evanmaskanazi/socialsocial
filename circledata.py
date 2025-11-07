# Fixed script for your database schema
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

    # Test 2: Check circle memberships are consistent (FIXED FOR YOUR SCHEMA)
    print("\n✅ Test 2: Checking circle memberships...")
    result = db.session.execute(text("""
        SELECT c.*, u1.username as circle_owner, u2.username as member_name
        FROM circles c
        JOIN users u1 ON c.user_id = u1.id
        JOIN users u2 ON c.circle_user_id = u2.id
        WHERE c.circle_type NOT IN ('class_a', 'class_b', 'class_c')
    """))
    invalid_circles = result.fetchall()
    if invalid_circles:
        print(f"❌ Found {len(invalid_circles)} invalid circle memberships:")
        for c in invalid_circles:
            print(f"   {c.circle_owner}'s circle has {c.member_name} in invalid type: {c.circle_type}")
    else:
        print("✅ All circle memberships have valid types!")

    # Test 3: Check for orphaned circles (FIXED)
    print("\n✅ Test 3: Checking for orphaned circles...")
    result = db.session.execute(text("""
        SELECT c.* FROM circles c
        LEFT JOIN users u1 ON c.user_id = u1.id
        LEFT JOIN users u2 ON c.circle_user_id = u2.id
        WHERE u1.id IS NULL OR u2.id IS NULL
    """))
    orphaned = result.fetchall()
    if orphaned:
        print(f"❌ Found {len(orphaned)} orphaned circle entries")
    else:
        print("✅ No orphaned circles found!")

    # Test 4: Check specific user's circles
    print("\n✅ Test 4: Checking user 1's circles...")
    result = db.session.execute(text("""
        SELECT circle_type, COUNT(*) as count
        FROM circles 
        WHERE user_id = 1
        GROUP BY circle_type
    """))
    circles_count = result.fetchall()
    for circle in circles_count:
        print(f"   - {circle.circle_type}: {circle.count} members")

    # Test 5: Check privacy distribution
    print("\n✅ Test 5: Privacy distribution...")
    result = db.session.execute(text("""
        SELECT COUNT(*) as count, circles_privacy
        FROM users
        GROUP BY circles_privacy
        ORDER BY count DESC
    """))
    privacy_stats = result.fetchall()
    for stat in privacy_stats:
        print(f"   - {stat.circles_privacy or 'NULL'}: {stat.count} users")

    print("\n✅ All tests complete!")
```

## 2. Why You Still Get the JavaScript Error

Looking at your logs and HTML files, the problem is clear - your site is **NOT loading the fixed version** of circles-messages.js. 

From your logs:
```
GET /static/js/circles-messages.js HTTP/1.1" 200
```

Notice it's loading WITHOUT any version parameter, yet in your browser it shows:
```
circles-messages.js:1 Uncaught SyntaxError: Identifier 'currentRecipient' has already been declared
