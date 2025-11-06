import psycopg2, os
conn = psycopg2.connect(os.environ['DATABASE_URL'])
cursor = conn.cursor()

owner_username = 'emaskanazi_1'
member_username = 'diana'
circle_type = 'public'  # LOWERCASE! And it's stored directly in circles table

print(f"=== Test: Remove '{member_username}' from '{circle_type}' ===\n")

# Get owner ID
cursor.execute("SELECT id FROM users WHERE username = %s", (owner_username,))
owner_id = cursor.fetchone()[0]
print(f"Owner ID: {owner_id}")

# Get member ID
cursor.execute("SELECT id FROM users WHERE username = %s", (member_username,))
member_id = cursor.fetchone()[0]
print(f"Member ID: {member_id}")

# Find the membership row in circles table
cursor.execute("""
    SELECT id FROM circles
    WHERE circle_user_id = %s 
    AND user_id = %s 
    AND circle_type = %s
""", (owner_id, member_id, circle_type))

circle_row = cursor.fetchone()
if not circle_row:
    print(f"\n✗ '{member_username}' is NOT in {circle_type}")
    
    # Show what circles they ARE in
    cursor.execute("""
        SELECT circle_type FROM circles 
        WHERE circle_user_id = %s AND user_id = %s
    """, (owner_id, member_id))
    existing = cursor.fetchall()
    if existing:
        print(f"   But they ARE in: {[r[0] for r in existing]}")
else:
    circle_row_id = circle_row[0]
    print(f"\n✓ Found membership (circle row id: {circle_row_id})")
    
    # Delete
    cursor.execute("DELETE FROM circles WHERE id = %s", (circle_row_id,))
    print(f"✓ Would delete '{member_username}' from {circle_type}")
    conn.rollback()  # Don't commit - just test

cursor.close()
conn.close()
