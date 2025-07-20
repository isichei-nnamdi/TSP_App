import sqlite3

DB_PATH = "fta.db"

def init_assignment_tables():
    with sqlite3.connect(DB_PATH, timeout=10) as conn:
        c = conn.cursor()
        # Create the A-Team members table
        c.execute('''
            CREATE TABLE IF NOT EXISTS a_team_members (
                email TEXT PRIMARY KEY,
                full_name TEXT
            )
        ''')
        # Create the assignments table
        c.execute('''
            CREATE TABLE IF NOT EXISTS fta_assignments (
                fta_id TEXT PRIMARY KEY,
                full_name TEXT,
                assigned_to TEXT,
                assigned_at TEXT
            )
        ''')
        # Create the assignment_tracker table
        c.execute('''
            CREATE TABLE IF NOT EXISTS assignment_tracker (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                last_assigned_index INTEGER
            )
        ''')
        # Ensure a default row exists
        c.execute('INSERT OR IGNORE INTO assignment_tracker (id, last_assigned_index) VALUES (1, -1)')
        conn.commit()
    print("Tables initialized successfully.")

if __name__ == "__main__":
    init_assignment_tables()