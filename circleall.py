import psycopg2, os
conn = psycopg2.connect(os.environ['DATABASE_URL'])
cursor = conn.cursor()

owner_username = 'emaskanazi_1'
member_username = 'diana'  # From your screenshot
circle_type = 'public'

print(f"=== Full Cycle Test: Remove and Re-add '{member_username}' ===\n")

# Get IDs
cursor.execute("SELECT id FROM users WHERE username = %s", (owner_username,))
owner_id = cursor.fetchone()[0]

cursor.execute("SELECT id FROM users WHERE username = %s", (member_username,))
member_id = cursor.fetchone()[0]

cursor.execute("""
    SELECT id FROM circles 
    WHERE circle_user_id = %s AND circle_type = %s
""", (owner_id, circle_type))
circle_id = cursor.fetchone()[0]

print(f"Owner: {owner_username} (ID: {owner_id})")
print(f"Member: {member_username} (ID: {member_id})")
print(f"Circle: {circle_type} (ID: {circle_id})\n")

# Check initial state
cursor.execute("""
    SELECT * FROM circle_members 
    WHERE circle_id = %s AND user_id = %s
""", (circle_id, member_id))

is_member = cursor.fetchone() is not None
print(f"1. Initial state: '{member_username}' {'IS' if is_member else 'is NOT'} in circle")

# Step 1: Remove (if present)
if is_member:
    cursor.execute("""
        DELETE FROM circle_members 
        WHERE circle_id = %s AND user_id = %s
    """, (circle_id, member_id))
    print(f"2. Removed: {cursor.rowcount} row deleted")

# Step 2: Re-add
cursor.execute("""
    INSERT INTO circle_members (circle_id, user_id, added_at)
    VALUES (%s, %s, NOW())
    RETURNING id, added_at
""", (circle_id, member_id))

result = cursor.fetchone()
print(f"3. Re-added: circle_member ID {result[0]}, added at {result[1]}")

print("\n✓ Full cycle successful!")
conn.rollback()  # Don't commit - just test

cursor.close()
conn.close()
