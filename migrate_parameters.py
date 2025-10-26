"""
Migration script to convert old text-based parameters to numeric format (1-4)
Run this script to update any existing parameters data
"""
import sqlite3
import json
from datetime import datetime

def migrate_parameters_to_numeric():
    """Convert text parameters to numeric 1-4 scale"""
    
    # Connect to database
    conn = sqlite3.connect('social.db')
    cursor = conn.cursor()
    
    # First, check if parameters table exists and its structure
    cursor.execute("""
        SELECT sql FROM sqlite_master 
        WHERE type='table' AND name='parameters'
    """)
    table_info = cursor.fetchone()
    
    if not table_info:
        print("Parameters table doesn't exist yet. Creating it...")
        
        # Create the parameters table with numeric columns
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS parameters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                date DATE NOT NULL,
                mood INTEGER CHECK(mood >= 1 AND mood <= 4),
                energy INTEGER CHECK(energy >= 1 AND energy <= 4),
                sleep_quality INTEGER CHECK(sleep_quality >= 1 AND sleep_quality <= 4),
                physical_activity INTEGER CHECK(physical_activity >= 1 AND physical_activity <= 4),
                anxiety INTEGER CHECK(anxiety >= 1 AND anxiety <= 4),
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                UNIQUE(user_id, date)
            )
        """)
        conn.commit()
        print("✅ Parameters table created with numeric columns")
        return
    
    print("Table structure:", table_info[0])
    
    # Check column types
    cursor.execute("PRAGMA table_info(parameters)")
    columns = cursor.fetchall()
    
    print("\nCurrent columns:")
    for col in columns:
        print(f"  {col[1]}: {col[2]}")
    
    # Check if we have any text data that needs conversion
    cursor.execute("""
        SELECT id, user_id, date, mood, energy, sleep_quality, 
               physical_activity, anxiety, notes
        FROM parameters
        LIMIT 10
    """)
    
    sample_data = cursor.fetchall()
    
    if not sample_data:
        print("\nNo parameters data found to migrate")
        conn.close()
        return
    
    print(f"\nFound {len(sample_data)} parameter records to check")
    
    # Text to numeric mapping for common entries
    text_to_numeric = {
        # Mood mappings
        'very bad': 1, 'terrible': 1, 'awful': 1, 'depressed': 1,
        'bad': 2, 'not good': 2, 'down': 2, 'sad': 2,
        'ok': 3, 'okay': 3, 'neutral': 3, 'fine': 3, 'good': 3,
        'very good': 4, 'great': 4, 'excellent': 4, 'happy': 4,
        
        # Energy mappings
        'very low': 1, 'exhausted': 1, 'no energy': 1,
        'low': 2, 'tired': 2, 'sluggish': 2,
        'moderate': 3, 'normal': 3, 'average': 3,
        'high': 4, 'energetic': 4, 'very high': 4,
        
        # Sleep quality mappings
        'very poor': 1, 'terrible': 1, 'awful': 1,
        'poor': 2, 'bad': 2, 'restless': 2,
        'fair': 3, 'ok': 3, 'decent': 3,
        'good': 4, 'great': 4, 'excellent': 4,
        
        # Physical activity mappings
        'none': 1, 'sedentary': 1, 'no activity': 1,
        'light': 2, 'minimal': 2, 'some': 2,
        'moderate': 3, 'regular': 3, 'active': 3,
        'intense': 4, 'very active': 4, 'high': 4,
        
        # Anxiety mappings
        'severe': 4, 'very high': 4, 'extreme': 4,
        'moderate': 3, 'high': 3, 'significant': 3,
        'mild': 2, 'low': 2, 'some': 2,
        'none': 1, 'minimal': 1, 'calm': 1,
    }
    
    # Process each record
    updates_needed = []
    
    for row in sample_data:
        id_, user_id, date, mood, energy, sleep_quality, physical_activity, anxiety, notes = row
        
        print(f"\nRecord {id_} for user {user_id} on {date}:")
        
        update_values = {}
        
        # Check each parameter
        params = {
            'mood': mood,
            'energy': energy,
            'sleep_quality': sleep_quality,
            'physical_activity': physical_activity,
            'anxiety': anxiety
        }
        
        for param_name, value in params.items():
            if value is None:
                print(f"  {param_name}: None (skipping)")
                continue
                
            # Check if it's already numeric
            if isinstance(value, int) and 1 <= value <= 4:
                print(f"  {param_name}: {value} ✅ (already numeric)")
                continue
            
            # Try to convert if it's a string
            if isinstance(value, str):
                # Try direct numeric conversion first
                try:
                    numeric_value = int(value)
                    if 1 <= numeric_value <= 4:
                        update_values[param_name] = numeric_value
                        print(f"  {param_name}: '{value}' → {numeric_value}")
                        continue
                except ValueError:
                    pass
                
                # Try text mapping
                lower_value = value.lower().strip()
                if lower_value in text_to_numeric:
                    numeric_value = text_to_numeric[lower_value]
                    update_values[param_name] = numeric_value
                    print(f"  {param_name}: '{value}' → {numeric_value} (mapped)")
                else:
                    # Default to middle value if can't convert
                    update_values[param_name] = 2
                    print(f"  {param_name}: '{value}' → 2 (default)")
        
        if update_values:
            updates_needed.append((id_, update_values))
    
    # Apply updates if needed
    if updates_needed:
        print(f"\n📝 Applying updates to {len(updates_needed)} records...")
        
        for id_, values in updates_needed:
            set_clause = ', '.join([f"{k} = ?" for k in values.keys()])
            query = f"UPDATE parameters SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = ?"
            cursor.execute(query, list(values.values()) + [id_])
        
        conn.commit()
        print(f"✅ Successfully updated {len(updates_needed)} records")
    else:
        print("\n✅ No updates needed - all parameters are already numeric")
    
    conn.close()

if __name__ == '__main__':
    print("=== Parameters Migration Script ===")
    print("Converting text-based parameters to numeric (1-4) format\n")
    
    try:
        migrate_parameters_to_numeric()
        print("\n✅ Migration completed successfully!")
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
