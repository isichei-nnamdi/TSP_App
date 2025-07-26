import os
import sqlite3

DB_PATH = "fta.db"

def reset_database():
    # Delete the existing database file, if it exists
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print("✅ Existing database removed.")

    # Reinitialize the tables
    with sqlite3.connect(DB_PATH, timeout=10) as conn:
        c = conn.cursor()

        # A-Team members table
        c.execute('''
            CREATE TABLE IF NOT EXISTS a_team_members (
                email TEXT PRIMARY KEY,
                full_name TEXT
            )
        ''')

        # FTA Assignments
        c.execute('''
            CREATE TABLE IF NOT EXISTS fta_assignments (
                fta_id TEXT PRIMARY KEY,
                full_name TEXT,
                assigned_to TEXT,
                assigned_at TEXT
            )
        ''')

        # Assignment Tracker
        c.execute('''
            CREATE TABLE IF NOT EXISTS assignment_tracker (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                last_assigned_index INTEGER
            )
        ''')

        # Feedback Table
        c.execute('''
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fta_id TEXT,
                response TEXT,
                feedback_by TEXT,
                feedback_at TEXT
            )
        ''')

        # Email Logs Table
        c.execute('''
            CREATE TABLE IF NOT EXISTS email_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fta_id TEXT,
                assigned_to TEXT,
                email_subject TEXT,
                sender TEXT,
                sent_at TEXT
            )
        ''')

        # Initialize tracker row
        c.execute('INSERT OR IGNORE INTO assignment_tracker (id, last_assigned_index) VALUES (1, -1)')

        conn.commit()

    print("✅ Database reset and all tables reinitialized successfully.")

if __name__ == "__main__":
    reset_database()
