import psycopg2, os
conn = psycopg2.connect(os.environ['DATABASE_URL'])
cursor = conn.cursor()

# Your account
owner_username = 'emaskanazi_1'  # Your account
member_username = 'bob'  # User to remove
circle_type = 'public'  # From screenshot: public, class_b, class_a

print(f"=== Test: Remove '{member_username}' from '{circle_type}' ===")

# Step 1: Get owner user_id
cursor.execute("SELECT id FROM users WHERE username = %s", (owner_username,))
owner = cursor.fetchone()
if not owner:
    print(f"✗ Owner '{owner_username}' not found")
    exit()
owner_id = owner[0]
print(f"Owner ID: {owner_id}")

# Step 2: Get member user_id
cursor.execute("SELECT id FROM users WHERE username = %s", (member_username,))
member = cursor.fetchone()
if not member:
    print(f"✗ Member '{member_username}' not found")
    exit()
member_id = member[0]
print(f"Member ID: {member_id}")

# Step 3: Find the circle
cursor.execute("""
    SELECT id, name FROM circles 
    WHERE circle_user_id = %s AND circle_type = %s
""", (owner_id, circle_type))

circle = cursor.fetchone()
if not circle:
    print(f"✗ Circle '{circle_type}' not found for owner")
    exit()

circle_id = circle[0]
print(f"Circle ID: {circle_id}, Name: {circle[1]}")

# Step 4: Check if member is in circle
cursor.execute("""
    SELECT * FROM circle_members 
    WHERE circle_id = %s AND user_id = %s
""", (circle_id, member_id))

if not cursor.fetchone():
    print(f"✗ '{member_username}' is NOT in this circle")
else:
    # Step 5: Remove
    cursor.execute("""
        DELETE FROM circle_members 
        WHERE circle_id = %s AND user_id = %s
    """, (circle_id, member_id))
    
    print(f"✓ Would remove '{member_username}' (deleted {cursor.rowcount} row)")
    conn.rollback()  # DON'T commit - just test

cursor.close()
conn.close()
