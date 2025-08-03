import streamlit as st
# import sqlite3
import psycopg2
from psycopg2.extras import RealDictCursor
import bcrypt
from datetime import datetime
import pandas as pd
from email_utils import send_email_to_fta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


# --- Supabase PostgreSQL Connection Setup ---
# Replace with your actual Supabase DB credentials
DB_HOST = st.secrets["DB_HOST"]
DB_NAME = st.secrets["DB_NAME"]
DB_USER = st.secrets["DB_USER"]
DB_PASSWORD = st.secrets["DB_PASSWORD"]
DB_PORT = st.secrets.get("DB_PORT", 5432)  # default PostgreSQL port

# DB_PATH = "fta.db"

def create_connection():
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT,
            cursor_factory=RealDictCursor
        )
        return conn
    except Exception as e:
        st.error(f"Database connection error: {e}")
        return None

# # ======================= USER MANAGEMENT =======================
# # --- Function to get logs ---
# def get_email_logs():
#     with sqlite3.connect(DB_PATH) as conn:
#         df = pd.read_sql_query('''
#             SELECT fta_id, fta_name, email, subject, status, error_message, timestamp
#             FROM email_logs
#             ORDER BY timestamp DESC
#         ''', conn)
#     return df

# # --- Function to clear logs ---
# def clear_email_logs():
#     with sqlite3.connect(DB_PATH) as conn:
#         conn.execute("DELETE FROM email_logs")
#         conn.commit()

# # --- Function to delete failed emails logs ---
# def delete_failed_email_logs():
#     with sqlite3.connect(DB_PATH) as conn:
#         conn.execute("""
#             DELETE FROM email_logs
#             WHERE status IS NULL OR LOWER(status) IN ('failed', 'error')
#         """)
#         conn.commit()


# def create_users_table():
#     with sqlite3.connect(DB_PATH, timeout=10) as conn:
#         c = conn.cursor()
#         c.execute('''
#             CREATE TABLE IF NOT EXISTS users (
#                 id INTEGER PRIMARY KEY AUTOINCREMENT,
#                 email TEXT UNIQUE,
#                 password_hash TEXT,
#                 role TEXT DEFAULT 'A-Team'
#             )
#         ''')
#         conn.commit()
        

# def add_user(email, password, role='A-Team'):
#     password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
#     try:
#         with sqlite3.connect(DB_PATH, timeout=10) as conn:
#             c = conn.cursor()
#             c.execute('INSERT INTO users (email, password_hash, role) VALUES (?, ?, ?)',
#                       (email, password_hash, role))
#             if role == "A-Team":
#                 c.execute("INSERT OR IGNORE INTO a_team_members (email, full_name) VALUES (?, ?)", (email, email))
#             conn.commit()
#         return True
#     except sqlite3.IntegrityError:
#         return False

# def authenticate_user(email, password):
#     with sqlite3.connect(DB_PATH, timeout=10) as conn:
#         c = conn.cursor()
#         c.execute('SELECT password_hash FROM users WHERE email = ?', (email,))
#         result = c.fetchone()
#     if result:
#         return bcrypt.checkpw(password.encode(), result[0])
#     return False

# def get_user_role(email):
#     with sqlite3.connect(DB_PATH, timeout=10) as conn:
#         c = conn.cursor()
#         c.execute('SELECT role FROM users WHERE email = ?', (email,))
#         result = c.fetchone()
#     return result[0] if result else None

# def reset_password(email, new_password):
#     password_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt())
#     with sqlite3.connect(DB_PATH, timeout=10) as conn:
#         c = conn.cursor()
#         c.execute('UPDATE users SET password_hash = ? WHERE email = ?', (password_hash, email))
#         conn.commit()

# ======================= USER MANAGEMENT (PostgreSQL) =======================
# --- Function to get logs ---
def get_email_logs():
    conn = connect_db()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute('''
                SELECT fta_id, fta_name, email, subject, status, error_message, timestamp
                FROM email_logs
                ORDER BY timestamp DESC
            ''')
            rows = cur.fetchall()
            return pd.DataFrame(rows)
    finally:
        conn.close()

# --- Function to clear logs ---
def clear_email_logs():
    conn = connect_db()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM email_logs")
            conn.commit()
    finally:
        conn.close()

# --- Function to delete failed emails logs ---
def delete_failed_email_logs():
    conn = connect_db()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                DELETE FROM email_logs
                WHERE status IS NULL OR LOWER(status) IN ('failed', 'error')
            """)
            conn.commit()
    finally:
        conn.close()


def create_users_table():
    conn = connect_db()
    try:
        with conn.cursor() as cur:
            cur.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    email TEXT UNIQUE,
                    password_hash TEXT,
                    role TEXT DEFAULT 'A-Team'
                )
            ''')
            conn.commit()
    finally:
        conn.close()


def add_user(email, password, role='A-Team'):
    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    conn = connect_db()
    try:
        with conn.cursor() as cur:
            cur.execute('INSERT INTO users (email, password_hash, role) VALUES (%s, %s, %s)',
                        (email, password_hash, role))
            if role == "A-Team":
                cur.execute("INSERT INTO a_team_members (email, full_name) VALUES (%s, %s) ON CONFLICT (email) DO NOTHING", (email, email))
            conn.commit()
            return True
    except psycopg2.IntegrityError:
        conn.rollback()
        return False
    finally:
        conn.close()


def authenticate_user(email, password):
    conn = connect_db()
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT password_hash FROM users WHERE email = %s', (email,))
            result = cur.fetchone()
            if result:
                return bcrypt.checkpw(password.encode(), result[0].encode())
            return False
    finally:
        conn.close()


def get_user_role(email):
    conn = connect_db()
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT role FROM users WHERE email = %s', (email,))
            result = cur.fetchone()
            return result[0] if result else None
    finally:
        conn.close()


def reset_password(email, new_password):
    password_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
    conn = connect_db()
    try:
        with conn.cursor() as cur:
            cur.execute('UPDATE users SET password_hash = %s WHERE email = %s', (password_hash, email))
            conn.commit()
    finally:
        conn.close()


# # ======================= A-TEAM AND ASSIGNMENT =======================
# def init_assignment_tables():
#     with sqlite3.connect(DB_PATH, timeout=10) as conn:
#         c = conn.cursor()
#         c.execute('''
#             CREATE TABLE IF NOT EXISTS a_team_members (
#                 email TEXT PRIMARY KEY,
#                 full_name TEXT
#             )
#         ''')
#         c.execute('''
#             CREATE TABLE IF NOT EXISTS fta_assignments (
#                 fta_id TEXT PRIMARY KEY,
#                 full_name TEXT,
#                 assigned_to TEXT,
#                 assigned_at TEXT
#             )
#         ''')
#         c.execute('''
#             CREATE TABLE IF NOT EXISTS assignment_tracker (
#                 id INTEGER PRIMARY KEY CHECK (id = 1),
#                 last_assigned_index INTEGER
#             )
#         ''')
#         # Ensure a default row exists
#         c.execute('INSERT OR IGNORE INTO assignment_tracker (id, last_assigned_index) VALUES (1, -1)')
#         conn.commit()


# def add_a_team_member(email, full_name):
#     with sqlite3.connect(DB_PATH, timeout=10) as conn:
#         c = conn.cursor()
#         c.execute("INSERT OR IGNORE INTO a_team_members (email, full_name) VALUES (?, ?)", (email, full_name))
#         conn.commit()

# def get_all_a_team_members():
#     with sqlite3.connect(DB_PATH, timeout=10) as conn:
#         df = pd.read_sql_query("SELECT * FROM a_team_members", conn)
#     return df

# def get_existing_assignments():
#     with sqlite3.connect(DB_PATH, timeout=10) as conn:
#         df = pd.read_sql_query("SELECT * FROM fta_assignments", conn)
#     return df

# def create_email_log_table():
#     with sqlite3.connect(DB_PATH) as conn:
#         cursor = conn.cursor()
#         cursor.execute('''
#             CREATE TABLE IF NOT EXISTS email_logs (
#                 id INTEGER PRIMARY KEY AUTOINCREMENT,
#                 fta_id TEXT,  -- <-- This was missing!
#                 timestamp TEXT,
#                 fta_name TEXT,
#                 email TEXT,
#                 subject TEXT,
#                 status TEXT,
#                 error_message TEXT
#             )
#         ''')
#         conn.commit()

# ======================= A-TEAM AND ASSIGNMENT =======================
def init_assignment_tables():
    conn = get_connection()
    with conn:
        with conn.cursor() as c:
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
            c.execute('INSERT INTO assignment_tracker (id, last_assigned_index) VALUES (1, -1)
                       ON CONFLICT (id) DO NOTHING')

def add_a_team_member(email, full_name):
    conn = get_connection()
    with conn:
        with conn.cursor() as c:
            c.execute("""
                INSERT INTO a_team_members (email, full_name)
                VALUES (%s, %s)
                ON CONFLICT (email) DO NOTHING
            """, (email, full_name))

def get_all_a_team_members():
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM a_team_members", conn)
    conn.close()
    return df

def get_existing_assignments():
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM fta_assignments", conn)
    conn.close()
    return df

def create_email_log_table():
    conn = get_connection()
    with conn:
        with conn.cursor() as cursor:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS email_logs (
                    id SERIAL PRIMARY KEY,
                    fta_id TEXT,
                    timestamp TEXT,
                    fta_name TEXT,
                    email TEXT,
                    subject TEXT,
                    status TEXT,
                    error_message TEXT
                )
            ''')


sender_email = st.secrets["secrets"]["address"]
app_password = st.secrets["secrets"]["app_password"]

def send_email(receiver_email, fta_name):
    subject = "Welcome to The Standpoint Church – We're Glad You Came!"
    body = f"""
    <html>
      <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <p>Dear {fta_name},</p>
    
        <p>
          We’re truly honored that you chose to worship with us at <strong>The Standpoint Church</strong>.
          On behalf of our Senior Pastor, <strong>Dr. Phil Ransom-Bello</strong>, and the entire Standpoint family,
          we want to say a big <strong>THANK YOU</strong> for fellowshipping with us!
        </p>
    
        <p>
          We believe that your presence is not by chance but part of God’s divine orchestration,
          and we are excited about all that God has in store for you from here.
        </p>
    
        <p>
          Whether this was your first time or you’ve visited before, please know that you're
          <strong>seen, valued, and loved</strong>. Our prayer is that you find purpose, truth, and transformation
          as you continue to encounter God's Word in this house.
        </p>
    
        <p>
          We look forward to seeing you again, growing together, and walking this journey of faith alongside you.
        </p>
    
        <br>
    
        <p style="margin-top: 30px;">
          With love and honor,<br>
          <strong>The A-Team</strong><br>
          <em>For Dr. Phil Ransom-Bello</em><br>
          <em>Lead Pastor, The Standpoint Church</em>
        </p>
      </body>
    </html>
    """

    # message = MIMEText(body)
    # message["Subject"] = subject
    # message["From"] = sender_email
    # message["To"] = receiver_email
    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = sender_email
    message["To"] = receiver_email
    
    part = MIMEText(body, "html")
    message.attach(part)

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, app_password)
        server.sendmail(sender_email, receiver_email, message.as_string())
        server.quit()

        return True, subject
    except Exception as e:
        print(f"[Email Error] {e}")
        return False, None

# def log_email_sent(fta_id, email, fta_name, subject, status="sent", error_message=None):
#     timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#     with sqlite3.connect(DB_PATH) as conn:
#         cursor = conn.cursor()
#         cursor.execute('''
#             INSERT INTO email_logs (timestamp, fta_id, fta_name, email, subject, status, error_message)
#             VALUES (?, ?, ?, ?, ?, ?, ?)
#         ''', (timestamp, fta_id, fta_name, email, subject, status, error_message))
#         conn.commit()
        

# def email_already_sent(fta_id):
#     with sqlite3.connect(DB_PATH) as conn:
#         cursor = conn.cursor()
#         result = cursor.execute(
#             "SELECT 1 FROM email_logs WHERE fta_id = ? AND status = 'sent' LIMIT 1",
#             (fta_id,)
#         ).fetchone()
#         return result is not None

def log_email_sent(fta_id, email, fta_name, subject, status="sent", error_message=None):
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO email_logs (timestamp, fta_id, fta_name, email, subject, status, error_message)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    ''', (timestamp, fta_id, fta_name, email, subject, status, error_message))
    conn.commit()
    cursor.close()
    conn.close()


def email_already_sent(fta_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT 1 FROM email_logs WHERE fta_id = %s AND status = 'sent' LIMIT 1",
        (fta_id,)
    )
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result is not None


# def sync_and_assign_fta_responses(gsheet_url):
#     try:
#         df = pd.read_csv(gsheet_url)
#         df.columns = df.columns.str.strip()
#         df = df.drop_duplicates(subset=["FTA ID"])
#     except Exception as e:
#         print(f"[Sync Error] Failed to fetch sheet: {e}")
#         return pd.DataFrame()

#     # Email sending and logging logic
#     for _, row in df.iterrows():
#         fta_id = row.get("FTA ID")
#         name = row.get("Full Name", "FTA")
#         email = row.get("Email address")
    
#         if not fta_id:
#             print(f"[Skip] Missing FTA ID for row: {row}")
#             continue
    
#         if not email:
#             print(f"[Skip] Missing email for FTA ID {fta_id}")
#             continue
    
#         if email_already_sent(fta_id):
#             print(f"[Skip] Email already sent to FTA ID {fta_id}")
#             continue
    
#         sent, subject = send_email(email, name)
#         if sent:
#             log_email_sent(fta_id, email, name, subject, "sent")
#         else:
#             log_email_sent(fta_id, email, name, subject, "failed", "Send error")

#     # Store in main table
#     with sqlite3.connect(DB_PATH) as conn:
#         df.to_sql("fta_responses", conn, if_exists="replace", index=False)

#     try:
#         assign_new_ftas(df)
#     except Exception as e:
#         print(f"[Assignment Error] {e}")
#         return pd.DataFrame() 

#     return df
    

# def assign_new_ftas(fta_df):
#     fta_df.columns = fta_df.columns.str.strip()

#     if "FTA ID" not in fta_df.columns:
#         raise ValueError("Missing 'FTA ID' column in FTA form data.")

#     assigned_df = get_existing_assignments()
#     already_assigned_ids = set(assigned_df['fta_id'])

#     unassigned_ftas = fta_df[~fta_df['FTA ID'].isin(already_assigned_ids)].copy()
#     if unassigned_ftas.empty:
#         return assigned_df  # nothing new

#     members_df = get_all_a_team_members()
#     member_count = len(members_df)
#     if member_count == 0:
#         raise Exception("No A-Team members available for assignment.")

#     # Get last assigned index
#     with sqlite3.connect(DB_PATH) as conn:
#         c = conn.cursor()
#         c.execute("SELECT last_assigned_index FROM assignment_tracker WHERE id = 1")
#         result = c.fetchone()
#         last_index = result[0] if result else -1

#     assignments = []
#     current_index = (last_index + 1) % member_count

#     for _, row in unassigned_ftas.iterrows():
#         assigned_to = members_df.iloc[current_index]["email"]
#         assignments.append((
#             row["FTA ID"],
#             row["Full Name"],
#             assigned_to,
#             datetime.now().isoformat()
#         ))
#         current_index = (current_index + 1) % member_count

#     # Save new assignments
#     with sqlite3.connect(DB_PATH) as conn:
#         c = conn.cursor()
#         try:
#             c.executemany(
#                 "INSERT INTO fta_assignments (fta_id, full_name, assigned_to, assigned_at) VALUES (?, ?, ?, ?)",
#                 assignments
#             )
#             # Update tracker
#             c.execute("UPDATE assignment_tracker SET last_assigned_index = ?", ((current_index - 1) % member_count,))
#             conn.commit()
#         except sqlite3.IntegrityError:
#             pass

#     return get_existing_assignments()


# def create_feedback_table():
#     with sqlite3.connect(DB_PATH) as conn:
#         conn.execute('''
#             CREATE TABLE IF NOT EXISTS fta_feedback (
#                 id INTEGER PRIMARY KEY AUTOINCREMENT,
#                 email TEXT,
#                 fta_id TEXT,
#                 call_type TEXT,
#                 call_success TEXT,
#                 feedback_1 TEXT,
#                 met_date TEXT,
#                 mg_date TEXT,
#                 department TEXT,
#                 general_feedback TEXT,
#                 submitted_at TEXT
#             )
#         ''')

def sync_and_assign_fta_responses(gsheet_url):
    try:
        df = pd.read_csv(gsheet_url)
        df.columns = df.columns.str.strip()
        df = df.drop_duplicates(subset=["FTA ID"])
    except Exception as e:
        print(f"[Sync Error] Failed to fetch sheet: {e}")
        return pd.DataFrame()

    # Email sending and logging logic
    for _, row in df.iterrows():
        fta_id = row.get("FTA ID")
        name = row.get("Full Name", "FTA")
        email = row.get("Email address")

        if not fta_id:
            print(f"[Skip] Missing FTA ID for row: {row}")
            continue

        if not email:
            print(f"[Skip] Missing email for FTA ID {fta_id}")
            continue

        if email_already_sent(fta_id):
            print(f"[Skip] Email already sent to FTA ID {fta_id}")
            continue

        sent, subject = send_email(email, name)
        if sent:
            log_email_sent(fta_id, email, name, subject, "sent")
        else:
            log_email_sent(fta_id, email, name, subject, "failed", "Send error")

    # Store in main table
    with get_connection() as conn:
        df.to_sql("fta_responses", conn, if_exists="replace", index=False)

    try:
        assign_new_ftas(df)
    except Exception as e:
        print(f"[Assignment Error] {e}")
        return pd.DataFrame()

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
    with get_connection() as conn:
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
    with get_connection() as conn:
        c = conn.cursor()
        try:
            c.executemany(
                "INSERT INTO fta_assignments (fta_id, full_name, assigned_to, assigned_at) VALUES (%s, %s, %s, %s)",
                assignments
            )
            # Update tracker
            c.execute("UPDATE assignment_tracker SET last_assigned_index = %s", ((current_index - 1) % member_count,))
            conn.commit()
        except Exception as e:
            print(f"[DB Error] {e}")

    return get_existing_assignments()


def create_feedback_table():
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS fta_feedback (
                    id SERIAL PRIMARY KEY,
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
            conn.commit()
