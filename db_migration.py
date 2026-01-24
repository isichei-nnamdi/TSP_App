# db_migration.py
# Run this once to add the 'is_active' column to your existing database

import os
from sqlalchemy import create_engine, text

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "database", "fta.db")
DB_PATH = f"sqlite:///{DB_FILE}"

def add_active_status_column():
    """Add is_active column to a_team_members table if it doesn't exist"""
    engine = create_engine(DB_PATH)
    
    with engine.connect() as conn:
        # Check if column exists
        result = conn.execute(text("PRAGMA table_info(a_team_members)"))
        columns = [row[1] for row in result]
        
        if 'is_active' not in columns:
            # Add the column with default value TRUE
            conn.execute(text("""
                ALTER TABLE a_team_members 
                ADD COLUMN is_active BOOLEAN DEFAULT 1
            """))
            conn.commit()
            print("✅ Successfully added 'is_active' column to a_team_members table")
        else:
            print("ℹ️ Column 'is_active' already exists")

if __name__ == "__main__":
    add_active_status_column()