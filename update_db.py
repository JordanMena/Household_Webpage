import sqlite3
import os

# Path to the database file
db_path = os.path.join('home_page', 'site.db')

def update_db():
    if not os.path.exists(db_path):
        print(f"Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if the column already exists
        cursor.execute("PRAGMA table_info(tag)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if 'color' not in columns:
            print("Adding 'color' column to 'tag' table...")
            cursor.execute("ALTER TABLE tag ADD COLUMN color TEXT NOT NULL DEFAULT 'primary'")
            
            # Update existing special tags
            print("Updating default colors for 'meat' and 'vegetarian'...")
            cursor.execute("UPDATE tag SET color = 'danger' WHERE name = 'meat'")
            cursor.execute("UPDATE tag SET color = 'success' WHERE name = 'vegetarian'")
            
            conn.commit()
            print("Database updated successfully.")
        else:
            print("'color' column already exists.")
            
    except sqlite3.Error as e:
        print(f"An error occurred: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    update_db()
