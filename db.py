import streamlit as st
import sqlite3
import bcrypt
from datetime import datetime
import pandas as pd
from email_utils import send_email_to_fta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


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

def create_email_log_table():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS email_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fta_id TEXT,  -- <-- This was missing!
                timestamp TEXT,
                fta_name TEXT,
                email TEXT,
                subject TEXT,
                status TEXT,
                error_message TEXT
            )
        ''')
        conn.commit()

# def create_email_log_table():
#     with sqlite3.connect(DB_PATH) as conn:
#         cursor = conn.cursor()
#         cursor.execute('''
#             CREATE TABLE IF NOT EXISTS email_logs (
#                 id INTEGER PRIMARY KEY AUTOINCREMENT,
#                 timestamp TEXT,
#                 fta_name TEXT,
#                 email TEXT,
#                 subject TEXT,
#                 status TEXT,
#                 error_message TEXT
#             )
#         ''')
#         conn.commit()


sender_email = st.secrets["secrets"]["address"]
app_password = st.secrets["secrets"]["app_password"]

def send_email(receiver_email, fta_name):
    subject = "Welcome to the FTA Team"
    body = f"Dear {fta_name},\n\nThank you for joining the team!"

    message = MIMEText(body)
    message["Subject"] = subject
    message["From"] = sender_email
    message["To"] = receiver_email

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

def log_email_sent(fta_id, email, fta_name, subject, status="sent", error_message=None):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO email_logs (timestamp, fta_id, fta_name, email, subject, status, error_message)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (timestamp, fta_id, fta_name, email, subject, status, error_message))
        conn.commit()
        
# def log_email_sent(fta_id, email, name, subject):
#     timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#     with sqlite3.connect(DB_PATH) as conn:
#         conn.execute("""
#             CREATE TABLE IF NOT EXISTS email_logs (
#                 fta_id TEXT,
#                 email TEXT,
#                 name TEXT,
#                 subject TEXT,
#                 timestamp TEXT
#             )
#         """)
#         conn.execute("""
#             INSERT INTO email_logs (fta_id, email, name, subject, timestamp)
#             VALUES (?, ?, ?, ?, ?)
#         """, (fta_id, email, name, subject, timestamp))

def email_already_sent(fta_id):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        result = cursor.execute(
            "SELECT 1 FROM email_logs WHERE fta_id = ? AND status = 'sent' LIMIT 1",
            (fta_id,)
        ).fetchone()
        return result is not None

# def email_already_sent(fta_id):
#     with sqlite3.connect(DB_PATH) as conn:
#         result = conn.execute("SELECT 1 FROM email_logs WHERE fta_id = ?", (fta_id,))
#         return result.fetchone() is not None

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

        # if email and not email_already_sent(fta_id):
        #     sent, subject = send_email(email, name)
        #     if sent:
        #         log_email_sent(fta_id, email, name, subject)
        if email and not email_already_sent(fta_id):
            sent, subject = send_email(email, name)
            if sent:
                log_email_sent(fta_id, email, name, subject, "sent")
            else:
                log_email_sent(fta_id, email, name, subject, "failed", "Send error")

    # Store in main table
    with sqlite3.connect(DB_PATH) as conn:
        df.to_sql("fta_responses", conn, if_exists="replace", index=False)

    try:
        assign_new_ftas(df)
    except Exception as e:
        print(f"[Assignment Error] {e}")
        return pd.DataFrame() 

    return df
    
# def sync_and_assign_fta_responses(gsheet_url):
#     try:
#         df = pd.read_csv(gsheet_url)
#         df.columns = df.columns.str.strip()
#         df = df.drop_duplicates(subset=["FTA ID"])
#     except Exception as e:
#         print(f"[Sync Error] Failed to fetch sheet: {e}")
#         return pd.DataFrame()

#     with sqlite3.connect(DB_PATH) as conn:
#         df.to_sql("fta_responses", conn, if_exists="replace", index=False)

#     try:
#         assign_new_ftas(df)
#     except Exception as e:
#         print(f"[Assignment Error] {e}")
#         return pd.DataFrame()  # or return df if you still want to display the raw data

#     return df

# def sync_and_assign_fta_responses(gsheet_url):
#     try:
#         # Load from Google Sheets
#         client = gspread.service_account_from_dict(st.secrets["secrets"])
#         sheet = client.open_by_url(gsheet_url)
#         ws = sheet.worksheet("Form Responses 1")
#         data = ws.get_all_records()
#         df = pd.DataFrame(data)
#         df.columns = df.columns.str.strip()

#         # Ensure 'email_sent' column exists
#         if 'email_sent' not in df.columns:
#             ws.update_cell(1, len(df.columns) + 1, "email_sent")
#             df['email_sent'] = ""

#         # Email log worksheet
#         try:
#             email_log_ws = sheet.worksheet("email_logs")
#         except gspread.exceptions.WorksheetNotFound:
#             email_log_ws = sheet.add_worksheet("email_logs", rows=1000, cols=5)
#             email_log_ws.append_row(["timestamp", "fta_name", "email", "subject", "sender"])

#         # Loop through rows to send email if not already sent
#         for idx, row in df.iterrows():
#             if not row.get("email_sent"):
#                 fta_name = row.get("Full Name") or "FTA"
#                 email = row.get("Email address")
#                 if email:
#                     subject = "Thank you for fellowshing with us at TSP today"
#                     sender = st.secrets["secrets"]["address"]  # or your configured sender

#                     # Send the email
#                     send_email_to_fta(email, fta_name, subject, sender)

#                     # Mark email as sent in original sheet
#                     ws.update_cell(idx + 2, df.columns.get_loc("email_sent") + 1, "Yes")

#                     # Log the email
#                     email_log_ws.append_row([
#                         datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
#                         fta_name,
#                         email,
#                         subject,
#                         sender
#                     ])

#         # Continue with syncing to local DB
#         df = df.drop_duplicates(subset=["FTA ID"])
#     except Exception as e:
#         print(f"[Sync Error] Failed to fetch sheet or send emails: {e}")
#         return pd.DataFrame()

#     with sqlite3.connect(DB_PATH) as conn:
#         df.to_sql("fta_responses", conn, if_exists="replace", index=False)

#     try:
#         assign_new_ftas(df)
#     except Exception as e:
#         print(f"[Assignment Error] {e}")
#         return pd.DataFrame()

#     return df

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
