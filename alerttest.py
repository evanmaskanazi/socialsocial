# In Render shell or local Python environment:
# python

from app import app, db, Alert, User, Follow, Message
import json

# Create test client
client = app.test_client()

with app.app_context():
    print("=" * 60)
    print("BACKEND DIAGNOSTIC - ALERT SYSTEM")
    print("=" * 60)
    
    # ===== CHECK USERS =====
    print("\n1️⃣ CHECKING USERS")
    print("-" * 60)
    
    all_users = User.query.all()
    print(f"Total users in database: {len(all_users)}")
    
    alice = User.query.filter_by(username='alice').first()
    if alice:
        print(f"✅ Alice found: ID={alice.id}, username='{alice.username}'")
    else:
        print("❌ Alice not found")
        print("\nAvailable users:")
        for user in all_users[:10]:  # Show first 10
            print(f"   - ID {user.id}: {user.username}")
    
    # ===== CHECK ALERTS =====
    print("\n2️⃣ CHECKING ALERTS FOR ALICE")
    print("-" * 60)
    
    if alice:
        all_alerts = Alert.query.filter_by(user_id=alice.id).order_by(Alert.created_at.desc()).all()
        print(f"Total alerts: {len(all_alerts)}")
        
        unread_alerts = Alert.query.filter_by(user_id=alice.id, is_read=False).all()
        print(f"Unread alerts: {len(unread_alerts)}")
        
        if all_alerts:
            print("\nAlert details:")
            for i, alert in enumerate(all_alerts[:5], 1):  # Show last 5
                print(f"\nAlert #{i}:")
                print(f"   ID: {alert.id}")
                print(f"   Title: {alert.title}")
                print(f"   Content: {alert.content[:100]}...")
                print(f"   Type: {alert.alert_type}")
                print(f"   Read: {alert.is_read}")
                print(f"   Created: {alert.created_at}")
        else:
            print("❌ No alerts found for Alice")
    
    # ===== CHECK FOLLOWS =====
    print("\n3️⃣ CHECKING WHO FOLLOWS ALICE")
    print("-" * 60)
    
    if alice:
        # People following Alice
        followers = Follow.query.filter_by(followed_id=alice.id).all()
        print(f"Alice has {len(followers)} follower(s):")
        
        for follow in followers:
            follower_user = User.query.get(follow.follower_id)
            if follower_user:
                print(f"   - {follower_user.username} (Follow ID: {follow.id}, Since: {follow.created_at})")
                if hasattr(follow, 'follow_note') and follow.follow_note:
                    print(f"     Note: {follow.follow_note}")
        
        # People Alice is following
        following = Follow.query.filter_by(follower_id=alice.id).all()
        print(f"\nAlice is following {len(following)} user(s):")
        
        for follow in following:
            followed_user = User.query.get(follow.followed_id)
            if followed_user:
                print(f"   - {followed_user.username} (Follow ID: {follow.id})")
    
    # ===== CHECK MESSAGES =====
    print("\n4️⃣ CHECKING MESSAGES FOR ALICE")
    print("-" * 60)
    
    if alice:
        received_messages = Message.query.filter_by(recipient_id=alice.id).order_by(Message.timestamp.desc()).limit(5).all()
        print(f"Recent messages received: {len(received_messages)}")
        
        for i, msg in enumerate(received_messages, 1):
            sender = User.query.get(msg.sender_id)
            print(f"\nMessage #{i}:")
            print(f"   From: {sender.username if sender else 'Unknown'}")
            print(f"   Content: {msg.content[:50]}...")
            print(f"   Time: {msg.timestamp}")
    
    # ===== TEST API ENDPOINT =====
    print("\n5️⃣ TESTING /api/alerts ENDPOINT")
    print("-" * 60)
    
    if alice:
        # Simulate being logged in as Alice
        with client.session_transaction() as sess:
            sess['user_id'] = alice.id
            sess['username'] = alice.username
        
        response = client.get('/api/alerts')
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = json.loads(response.data)
            print(f"API returned {len(data.get('alerts', []))} alerts")
            print(f"Unread count: {data.get('unread_count', 0)}")
            
            print("\nAlerts from API:")
            for i, alert in enumerate(data.get('alerts', []), 1):
                print(f"\nAlert #{i}:")
                print(f"   ID: {alert.get('id')}")
                print(f"   Title: {alert.get('title')}")
                print(f"   Message: {alert.get('message', 'N/A')[:100]}")
                print(f"   Type: {alert.get('type')}")
                print(f"   Read: {alert.get('is_read')}")
        else:
            print(f"❌ API returned error: {response.status_code}")
            print(f"Response: {response.data}")
    
    print("\n" + "=" * 60)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 60)
