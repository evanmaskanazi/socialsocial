import psycopg2, os
conn = psycopg2.connect(os.environ['DATABASE_URL'])
cursor = conn.cursor()

owner_username = 'emaskanazi_1'

print(f"=== Current circles for '{owner_username}' ===\n")

# Get owner ID
cursor.execute("SELECT id FROM users WHERE username = %s", (owner_username,))
owner = cursor.fetchone()
if not owner:
    print("✗ Owner not found")
    exit()
owner_id = owner[0]

# Get all circles and their members
cursor.execute("""
    SELECT c.circle_type, c.name, u.username
    FROM circles c
    LEFT JOIN circle_members cm ON c.id = cm.circle_id
    LEFT JOIN users u ON cm.user_id = u.id
    WHERE c.circle_user_id = %s
    ORDER BY c.circle_type, u.username
""", (owner_id,))

current_circle = None
members = []

for row in cursor.fetchall():
    circle_type, circle_name, username = row
    
    if current_circle != circle_type:
        if current_circle:
            print(f"  Members: {', '.join(members) if members else 'None'}\n")
        current_circle = circle_type
        members = []
        print(f"{circle_type.upper()} ({circle_name}):")
    
    if username:
        members.append(username)

if members:
    print(f"  Members: {', '.join(members)}\n")

cursor.close()
conn.close()
