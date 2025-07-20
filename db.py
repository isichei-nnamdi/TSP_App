import sqlite3
import bcrypt
from datetime import datetime
import pandas as pd

DB_PATH = "fta.db"

# ======================= USER MANAGEMENT =======================

def create_users_table():
    with sqlite3.connect(DB_PATH, timeout=10) as conn:
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE,
                password_hash TEXT,
                role TEXT DEFAULT 'A-Team'
            )
        ''')
        conn.commit()

def add_user(email, password, role='A-Team'):
    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
    try:
        with sqlite3.connect(DB_PATH, timeout=10) as conn:
            c = conn.cursor()
            c.execute('INSERT INTO users (email, password_hash, role) VALUES (?, ?, ?)',
                      (email, password_hash, role))
            if role == "A-Team":
                c.execute("INSERT OR IGNORE INTO a_team_members (email, full_name) VALUES (?, ?)", (email, email))
            conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False

def authenticate_user(email, password):
    with sqlite3.connect(DB_PATH, timeout=10) as conn:
        c = conn.cursor()
        c.execute('SELECT password_hash FROM users WHERE email = ?', (email,))
        result = c.fetchone()
    if result:
        return bcrypt.checkpw(password.encode(), result[0])
    return False

def get_user_role(email):
    with sqlite3.connect(DB_PATH, timeout=10) as conn:
        c = conn.cursor()
        c.execute('SELECT role FROM users WHERE email = ?', (email,))
        result = c.fetchone()
    return result[0] if result else None

def reset_password(email, new_password):
    password_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt())
    with sqlite3.connect(DB_PATH, timeout=10) as conn:
        c = conn.cursor()
        c.execute('UPDATE users SET password_hash = ? WHERE email = ?', (password_hash, email))
        conn.commit()

# ======================= A-TEAM AND ASSIGNMENT =======================
def init_assignment_tables():
    with sqlite3.connect(DB_PATH, timeout=10) as conn:
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS a_team_members (
                email TEXT PRIMARY KEY,
                full_name TEXT
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS fta_assignments (
                fta_id TEXT PRIMARY KEY,
                full_name TEXT,
                assigned_to TEXT,
                assigned_at TEXT
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS assignment_tracker (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                last_assigned_index INTEGER
            )
        ''')
        # Ensure a default row exists
        c.execute('INSERT OR IGNORE INTO assignment_tracker (id, last_assigned_index) VALUES (1, -1)')
        conn.commit()


def add_a_team_member(email, full_name):
    with sqlite3.connect(DB_PATH, timeout=10) as conn:
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO a_team_members (email, full_name) VALUES (?, ?)", (email, full_name))
        conn.commit()

def get_all_a_team_members():
    with sqlite3.connect(DB_PATH, timeout=10) as conn:
        df = pd.read_sql_query("SELECT * FROM a_team_members", conn)
    return df

def get_existing_assignments():
    with sqlite3.connect(DB_PATH, timeout=10) as conn:
        df = pd.read_sql_query("SELECT * FROM fta_assignments", conn)
    return df

def sync_and_assign_fta_responses(gsheet_url):
    try:
        df = pd.read_csv(gsheet_url)
        df.columns = df.columns.str.strip()
        df = df.drop_duplicates(subset=["FTA ID"])
    except Exception as e:
        print(f"[Sync Error] Failed to fetch sheet: {e}")
        return pd.DataFrame()

    with sqlite3.connect(DB_PATH) as conn:
        df.to_sql("fta_responses", conn, if_exists="replace", index=False)

    try:
        assign_new_ftas(df)
    except Exception as e:
        print(f"[Assignment Error] {e}")
        return pd.DataFrame()  # or return df if you still want to display the raw data

    return df

def assign_new_ftas(fta_df):
    fta_df.columns = fta_df.columns.str.strip()

    if "FTA ID" not in fta_df.columns:
        raise ValueError("Missing 'FTA ID' column in FTA form data.")

    assigned_df = get_existing_assignments()
    already_assigned_ids = set(assigned_df['fta_id'])

    unassigned_ftas = fta_df[~fta_df['FTA ID'].isin(already_assigned_ids)].copy()
    if unassigned_ftas.empty:
        return assigned_df  # nothing new

    members_df = get_all_a_team_members()
    member_count = len(members_df)
    if member_count == 0:
        raise Exception("No A-Team members available for assignment.")

    # Get last assigned index
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT last_assigned_index FROM assignment_tracker WHERE id = 1")
        result = c.fetchone()
        last_index = result[0] if result else -1

    assignments = []
    current_index = (last_index + 1) % member_count

    for _, row in unassigned_ftas.iterrows():
        assigned_to = members_df.iloc[current_index]["email"]
        assignments.append((
            row["FTA ID"],
            row["Full Name"],
            assigned_to,
            datetime.now().isoformat()
        ))
        current_index = (current_index + 1) % member_count

    # Save new assignments
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        try:
            c.executemany(
                "INSERT INTO fta_assignments (fta_id, full_name, assigned_to, assigned_at) VALUES (?, ?, ?, ?)",
                assignments
            )
            # Update tracker
            c.execute("UPDATE assignment_tracker SET last_assigned_index = ?", ((current_index - 1) % member_count,))
            conn.commit()
        except sqlite3.IntegrityError:
            pass

    return get_existing_assignments()


def create_feedback_table():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS fta_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT,
                fta_id TEXT,
                call_type TEXT,
                call_success TEXT,
                feedback_1 TEXT,
                met_date TEXT,
                mg_date TEXT,
                department TEXT,
                general_feedback TEXT,
                submitted_at TEXT
            )
        ''')
