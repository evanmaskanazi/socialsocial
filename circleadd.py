import psycopg2, os
conn = psycopg2.connect(os.environ['DATABASE_URL'])
cursor = conn.cursor()

# Your account
owner_username = 'emaskanazi_1'
member_username = 'fiona'  # User to add
circle_type = 'public'

print(f"=== Test: Add '{member_username}' to '{circle_type}' ===")

# Step 1: Get owner user_id
cursor.execute("SELECT id FROM users WHERE username = %s", (owner_username,))
owner = cursor.fetchone()
if not owner:
    print(f"✗ Owner not found")
    exit()
owner_id = owner[0]
print(f"Owner ID: {owner_id}")

# Step 2: Get member user_id
cursor.execute("SELECT id FROM users WHERE username = %s", (member_username,))
member = cursor.fetchone()
if not member:
    print(f"✗ User '{member_username}' not found in database")
    exit()
member_id = member[0]
print(f"Member ID: {member_id}")

# Step 3: Find circle
cursor.execute("""
    SELECT id FROM circles 
    WHERE circle_user_id = %s AND circle_type = %s
""", (owner_id, circle_type))

circle = cursor.fetchone()
if not circle:
    print(f"✗ Circle not found")
    exit()
circle_id = circle[0]
print(f"Circle ID: {circle_id}")

# Step 4: Check if already member
cursor.execute("""
    SELECT * FROM circle_members 
    WHERE circle_id = %s AND user_id = %s
""", (circle_id, member_id))

if cursor.fetchone():
    print(f"✗ '{member_username}' is ALREADY in this circle")
else:
    # Step 5: Add
    cursor.execute("""
        INSERT INTO circle_members (circle_id, user_id, added_at)
        VALUES (%s, %s, NOW())
        RETURNING id
    """, (circle_id, member_id))
    
    new_id = cursor.fetchone()[0]
    print(f"✓ Would add '{member_username}' (new circle_member id: {new_id})")
    conn.rollback()  # DON'T commit

cursor.close()
conn.close()
