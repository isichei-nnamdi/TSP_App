# import streamlit as st
# import bcrypt
# import pandas as pd
# from datetime import datetime
# from sqlalchemy import or_, func, select, text
# from sqlalchemy.exc import SQLAlchemyError
# from sqlalchemy.orm import Session

# from db_session import get_session  # ✅ single source of truth for sessions
# from models import (
#     User,
#     ATeamMember,
#     EmailLogs,
#     FtaResponses,
#     AssignmentTracker,
#     FtaAssignments,
#     Feedback,
# )

# from email.mime.text import MIMEText
# from email.mime.multipart import MIMEMultipart
# import smtplib
# import hashlib

# # =========================
# # CONFIG (from Streamlit)
# # =========================
# sender_email = st.secrets["secrets"]["address"]
# app_password = st.secrets["secrets"]["app_password"]

# # =========================
# # Helpers
# # =========================

# def _normalize_fta_id(fta_id):
#     """Ensure FTA_ID is stored and compared consistently (string, stripped)."""
#     if fta_id is None:
#         return None
#     return str(fta_id).strip()

# def hash_pii(value):
#     """Hash PII values using SHA-256 (store only hashed PII)."""
#     if pd.isna(value) or value is None:
#         return None
#     return hashlib.sha256(str(value).encode("utf-8")).hexdigest()

# # =========================
# # A-Team sync utilities
# # =========================

# def sync_a_team_members():
#     """Ensure all users with A-Team role exist in a_team_members table."""
#     with get_session() as session:
#         a_team_users = session.query(User).filter(User.role == "A-Team").all()
#         for user in a_team_users:
#             if not session.query(ATeamMember).filter_by(email=user.email).first():
#                 full_name = user.name or user.email.split("@")[0].split(".")[0].capitalize()
#                 session.add(ATeamMember(email=user.email, full_name=full_name))
#         session.commit()

# def add_user_to_a_team_if_needed(user: User, session: Session):
#     """Add a new A-Team user to a_team_members."""
#     if user.role == "A-Team":
#         if not session.query(ATeamMember).filter_by(email=user.email).first():
#             full_name = user.name or user.email.split("@")[0].split(".")[0].capitalize()
#             session.add(ATeamMember(email=user.email, full_name=full_name))

# # =========================
# # Auth
# # =========================

# def authenticate_user(email, password):
#     with get_session() as session:
#         user = session.query(User).filter_by(email=email).first()
#         if not user:
#             return False
#         stored = user.password_hash
#         if isinstance(stored, str):
#             stored = stored.encode()
#         return bcrypt.checkpw(password.encode(), stored)

# def get_user_role(email):
#     with get_session() as session:
#         user = session.query(User).filter_by(email=email).first()
#         return user.role if user else None

# def reset_password(email, new_password):
#     with get_session() as session:
#         user = session.query(User).filter_by(email=email).first()
#         if user:
#             user.password_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt())
#             session.commit()

# # =========================
# # Email sending (idempotent)
# # =========================

# def send_email(receiver_email, fta_name):
#     subject = "Welcome to The Standpoint Church – We're Glad You Came!"
#     body = f"""
#     <html>
#       <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
#         <p>Dear {fta_name},</p>
#         <p>
#           We’re truly honored that you chose to worship with us at <strong>The Standpoint Church</strong>.
#           On behalf of our Senior Pastor, <strong>Dr. Phil Ransom-Bello</strong>, and the entire Standpoint family,
#           we want to say a big <strong>THANK YOU</strong> for fellowshipping with us!
#         </p>
#         <p>
#           We believe that your presence is not by chance but part of God’s divine orchestration,
#           and we are excited about all that God has in store for you from here.
#         </p>
#         <p>
#           Whether this was your first time or you’ve visited before, please know that you're
#           <strong>seen, valued, and loved</strong>. Our prayer is that you find purpose, truth, and transformation
#           as you continue to encounter God's Word in this house.
#         </p>
#         <p>
#           We look forward to seeing you again, growing together, and walking this journey of faith alongside you.
#         </p>
#         <br>
#         <p style="margin-top: 30px;">
#           With love and honor,<br>
#           <strong>The A-Team</strong><br>
#           <em>For Dr. Phil Ransom-Bello</em><br>
#           <em>Lead Pastor, The Standpoint Church</em>
#         </p>
#       </body>
#     </html>
#     """
#     message = MIMEMultipart("alternative")
#     message["Subject"] = subject
#     message["From"] = sender_email
#     message["To"] = receiver_email
#     message.attach(MIMEText(body, "html"))

#     try:
#         server = smtplib.SMTP("smtp.gmail.com", 587)
#         server.starttls()
#         server.login(sender_email, app_password)
#         server.sendmail(sender_email, receiver_email, message.as_string())
#         server.quit()
#         return True, subject, None
#     except Exception as e:
#         return False, None, str(e)

# def log_email_sent(session: Session, fta_id, email, fta_name, subject, status="sent", error_message=None):
#     """Log an email attempt. Uses normalized FTA_ID and commits via passed session."""
#     log = EmailLogs(
#         fta_id=_normalize_fta_id(fta_id),
#         fta_name=fta_name,
#         email=email,
#         subject=subject,
#         status=status,
#         error_message=error_message,
#         timestamp=datetime.now(),  # store raw datetime; SQLAlchemy/SQLite will handle
#     )
#     session.add(log)

# def email_already_sent(session: Session, fta_id) -> bool:
#     """Return True if a successful 'sent' log exists for this FTA_ID (normalized)."""
#     nid = _normalize_fta_id(fta_id)
#     if nid is None:
#         return False
#     exists = (
#         session.query(EmailLogs)
#         .filter(
#             EmailLogs.fta_id == nid,
#             func.lower(EmailLogs.status) == "sent",
#         )
#         .first()
#     )
#     return exists is not None

# # =========================
# # Email logs management
# # =========================

# def get_email_logs():
#     with get_session() as session:
#         logs = session.query(EmailLogs).order_by(EmailLogs.timestamp.desc()).all()
#         rows = [{
#             "fta_id": log.fta_id,
#             "fta_name": log.fta_name,
#             "email": log.email,
#             "subject": log.subject,
#             "status": log.status,
#             "error_message": log.error_message,
#             "timestamp": log.timestamp,
#         } for log in logs]
#     return pd.DataFrame(rows)

# def clear_email_logs():
#     with get_session() as session:
#         session.query(EmailLogs).delete()
#         session.commit()

# def delete_failed_email_logs():
#     with get_session() as session:
#         session.query(EmailLogs).filter(
#             or_(
#                 EmailLogs.status == None,
#                 func.lower(EmailLogs.status).in_(["failed", "error"]),
#             )
#         ).delete(synchronize_session=False)
#         session.commit()

# def resend_failed_emails():
#     """Attempt to resend only failed emails that have not since been sent successfully."""
#     with get_session() as session:
#         failed_logs = (
#             session.query(EmailLogs)
#             .filter(func.lower(EmailLogs.status) == "failed")
#             .order_by(EmailLogs.timestamp.asc())
#             .all()
#         )

#         if not failed_logs:
#             st.info("✅ No failed email logs to resend.")
#             return

#         st.write(f"🔄 Attempting to resend {len(failed_logs)} failed emails...")

#         for flog in failed_logs:
#             # Skip if a successful send has already happened later for the same FTA_ID
#             if email_already_sent(session, flog.fta_id):
#                 continue

#             success, subject, err = send_email(flog.email, flog.fta_name)

#             # Update the same log row to avoid log explosion
#             if success:
#                 flog.status = "sent"
#                 flog.subject = subject
#                 flog.error_message = None
#             else:
#                 flog.status = "failed"
#                 flog.error_message = err or "Retry failed"
#             flog.timestamp = datetime.now()

#         session.commit()
#         st.success("✅ Resend attempt completed.")

# # =========================
# # A-Team members
# # =========================

# def get_all_a_team_members():
#     with get_session() as session:
#         members = session.query(User).filter(User.role == "A-Team").all()
#         rows = [{
#             "id": m.id,
#             "name": m.name,
#             "email": m.email,
#             "role": m.role,
#         } for m in members]
#     return pd.DataFrame(rows)

# def add_a_team_member(email, full_name):
#     with get_session() as session:
#         existing = session.query(User).filter_by(email=email).first()
#         if not existing:
#             member = User(email=email, name=full_name, role="A-Team")
#             session.add(member)
#             # keep a-team mirror table in sync
#             add_user_to_a_team_if_needed(member, session)
#             session.commit()

# # =========================
# # Assignment utilities
# # =========================

# def init_assignment_tracker():
#     with get_session() as session:
#         tracker = session.query(AssignmentTracker).filter_by(id=1).first()
#         if not tracker:
#             tracker = AssignmentTracker(id=1, last_assigned_index=-1)
#             session.add(tracker)
#             session.commit()

# def get_existing_assignments():
#     with get_session() as session:
#         assignments = session.query(FtaAssignments).all()
#         rows = [{
#             "fta_id": a.fta_id,
#             "name": a.name,
#             "assigned_to": a.assigned_to,
#             "assigned_at": a.assigned_at,
#         } for a in assignments]
#     return pd.DataFrame(rows)

# def assign_new_ftas(fta_df: pd.DataFrame):
#     """Round-robin assign only unassigned FTA IDs to A-Team members."""
#     fta_df = fta_df.copy()
#     fta_df.columns = fta_df.columns.str.strip()

#     if "FTA ID" not in fta_df.columns:
#         raise ValueError("Missing 'FTA ID' column in FTA data (Google Sheet).")

#     # Normalize to strings for consistent matching
#     fta_df["FTA ID"] = fta_df["FTA ID"].map(_normalize_fta_id)

#     # Existing assignments
#     try:
#         existing = get_existing_assignments()
#         assigned_ids = set(existing["fta_id"].astype(str)) if not existing.empty else set()
#     except Exception as e:
#         print(f"[Assign Info] No existing assignments found: {e}")
#         assigned_ids = set()

#     unassigned = fta_df[~fta_df["FTA ID"].isin(assigned_ids)].copy()
#     if unassigned.empty:
#         print("[Assign Info] No unassigned FTAs found.")
#         return get_existing_assignments()

#     with get_session() as session:
#         members = session.query(User).filter(User.role == "A-Team").all()
#         member_count = len(members)
#         if member_count == 0:
#             raise Exception("No A-Team members available for assignment.")

#         tracker = session.query(AssignmentTracker).filter_by(id=1).first()
#         last_index = tracker.last_assigned_index if tracker else -1
#         current_index = (last_index + 1) % member_count

#         to_add = []
#         for _, row in unassigned.iterrows():
#             assigned_to_user = members[current_index]
#             a = FtaAssignments(
#                 fta_id=_normalize_fta_id(row["FTA ID"]),
#                 name=row.get("Full Name", "Unknown"),
#                 assigned_to=assigned_to_user.email,
#                 assigned_by=assigned_to_user.id,
#                 assigned_at=datetime.now(),
#             )
#             to_add.append(a)
#             current_index = (current_index + 1) % member_count

#         try:
#             session.add_all(to_add)
#             if tracker:
#                 tracker.last_assigned_index = (current_index - 1) % member_count
#             else:
#                 session.add(AssignmentTracker(id=1, last_assigned_index=(current_index - 1) % member_count))
#             session.commit()
#             print(f"[Assign Success] Assigned {len(to_add)} new FTAs.")
#         except SQLAlchemyError as e:
#             session.rollback()
#             print(f"[DB Error] Assignment failed: {e}")

#     return get_existing_assignments()

# # =========================
# # Sync & email pipeline
# # =========================

# def sync_and_assign_fta_responses(gsheet_url):
#     """
#     Pulls CSV from Google Sheet, upserts FtaResponses,
#     idempotently sends welcome email once per FTA_ID, and assigns FTAs.
#     """
#     print("\n=== [SYNC START] ===")
#     # ---- fetch data
#     try:
#         df = pd.read_csv(gsheet_url)
#         df.columns = df.columns.str.strip()
#         print(f"[Sync Info] Pulled {len(df)} rows from Google Sheets.")
#         print(f"[Sync Info] Columns found: {list(df.columns)}")
#         # normalize FTA ID column name
#         for alias in ["fta_id", "Fta Id"]:
#             if alias in df.columns:
#                 df.rename(columns={alias: "FTA ID"}, inplace=True)
#         if "FTA ID" not in df.columns:
#             print("[Sync Error] 'FTA ID' column is missing in the sheet.")
#             return pd.DataFrame()
#         # normalize FTA_ID to string
#         df["FTA ID"] = df["FTA ID"].map(_normalize_fta_id)
#         # dedupe by FTA_ID
#         df = df.drop_duplicates(subset=["FTA ID"]).reset_index(drop=True)
#         if df.empty:
#             print("[Sync Info] No data available after deduplication.")
#             return pd.DataFrame()
#     except Exception as e:
#         print(f"[Sync Error] Failed to fetch sheet: {e}")
#         return pd.DataFrame()

#     # ---- upsert & email (single session, consistent commits)
#     with get_session() as session:
#         try:
#             for _, row in df.iterrows():
#                 fta_id = row.get("FTA ID")
#                 if not fta_id:
#                     print(f"[Skip] Missing FTA ID for row: {row.to_dict()}")
#                     continue

#                 name_raw = row.get("Full Name", "FTA")
#                 email_raw = row.get("Email address")
#                 if not email_raw:
#                     print(f"[Skip] Missing email for FTA ID {fta_id}")
#                     continue

#                 # Hash PII for storage
#                 hashed_email = hash_pii(email_raw)
#                 hashed_name = hash_pii(name_raw)
#                 hashed_phone = hash_pii(row.get("Phone number"))
#                 hashed_address = hash_pii(row.get("Home Address"))

#                 existing = session.query(FtaResponses).filter(FtaResponses.FTA_ID == fta_id).first()

#                 # parse dates robustly (no locale ambiguity)
#                 ts = pd.to_datetime(row.get("Timestamp"), errors="coerce") if row.get("Timestamp") else None
#                 mtg = pd.to_datetime(row.get("Meeting Date"), errors="coerce") if row.get("Meeting Date") else None

#                 if existing:
#                     # update existing
#                     existing.Timestamp = ts
#                     existing.Email_address = hashed_email
#                     existing.Full_Name = hashed_name
#                     existing.Phone_number = hashed_phone
#                     existing.Gender = row.get("Gender")
#                     existing.Home_Address = hashed_address
#                     existing.Service_Experience = int(row.get("Service Experience", 0) or 0)
#                     existing.Worship_Experience = int(row.get("Worship Experience", 0) or 0)
#                     existing.Word_Experience = float(row.get("Word Experience", 0.0) or 0.0)
#                     existing.General_Feedback = row.get("General Feedback")
#                     existing.Invited_By = row.get("Invited By")
#                     existing.Membership_Interest = row.get("Membership Interest")
#                     existing.Consent = row.get("Consent")
#                     existing.Meeting_Date = mtg
#                 else:
#                     # insert new
#                     new_response = FtaResponses(
#                         Timestamp=ts,
#                         Email_address=hashed_email,
#                         Full_Name=hashed_name,
#                         Phone_number=hashed_phone,
#                         Gender=row.get("Gender"),
#                         Home_Address=hashed_address,
#                         Service_Experience=int(row.get("Service Experience", 0) or 0),
#                         Worship_Experience=int(row.get("Worship Experience", 0) or 0),
#                         Word_Experience=float(row.get("Word Experience", 0.0) or 0.0),
#                         General_Feedback=row.get("General Feedback"),
#                         Invited_By=row.get("Invited By"),
#                         Membership_Interest=row.get("Membership Interest"),
#                         Consent=row.get("Consent"),
#                         Meeting_Date=mtg,
#                         FTA_ID=fta_id,
#                     )
#                     session.add(new_response)

#                 # ---- Idempotent email send: only if never successfully sent before
#                 if not email_already_sent(session, fta_id):
#                     success, subject, err = send_email(email_raw, name_raw)
#                     if success:
#                         log_email_sent(session, fta_id, email_raw, name_raw, subject, status="sent")
#                     else:
#                         # log failure but do NOT block commit/upsert
#                         log_email_sent(session, fta_id, email_raw, name_raw, subject or "No Subject", status="failed", error_message=err)

#             # OPTIONAL: checkpoint WAL so external tools see changes immediately
#             # session.execute(text("PRAGMA wal_checkpoint(FULL);"))
#             session.commit()
#             print("[Sync Success] Changes committed to database.")
#         except SQLAlchemyError as e:
#             session.rollback()
#             print(f"[DB Commit Error] {e}")

#     # ---- Assign after saving
#     try:
#         if not df.empty:
#             assign_new_ftas(df)
#             print("[Assignment] FTA assignments updated successfully.")
#     except Exception as e:
#         print(f"[Assignment Error] {e}")

#     print("=== [SYNC END] ===\n")
#     return df

# ___--------------------------------------------------------------------------------------------
import streamlit as st
import bcrypt
import os
import pandas as pd
from datetime import datetime
from sqlalchemy.orm import Session
from models import Feedback, EmailLogs, User
from sqlalchemy import or_, func
from sqlalchemy.exc import SQLAlchemyError
from db_session import SessionLocal
from email_utils import send_email_to_fta
import hashlib
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from models import FtaResponses, AssignmentTracker, FtaAssignments
from sqlalchemy.orm import Session
from db_session import get_session
from models import User, ATeamMember
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


# ============ CONFIG ============
sender_email = st.secrets["secrets"]["address"]
app_password = st.secrets["secrets"]["app_password"]


def sync_a_team_members():
    """Ensure all users with A-Team role exist in a_team_members table."""
    with get_session() as session:
        a_team_users = session.query(User).filter(User.role == "A-Team").all()
        for user in a_team_users:
            exists = session.query(ATeamMember).filter_by(email=user.email).first()
            if not exists:
                full_name = user.name or user.email.split("@")[0].split(".")[0].capitalize()
                session.add(ATeamMember(email=user.email, full_name=full_name))
        session.commit()

def add_user_to_a_team_if_needed(user: User, session: Session):
    """Add a new A-Team user to a_team_members."""
    if user.role == "A-Team":
        exists = session.query(ATeamMember).filter_by(email=user.email).first()
        if not exists:
            full_name = user.name or user.email.split("@")[0].split(".")[0].capitalize()
            session.add(ATeamMember(email=user.email, full_name=full_name))

def toggle_a_team_member_status(email, is_active):
    """
    Toggle the active status of an A-Team member
    
    Args:
        email: Email of the A-Team member
        is_active: Boolean - True to activate, False to deactivate
    """
    try:
        with get_session() as session:
            member = session.query(ATeamMember).filter_by(email=email).first()
            if member:
                member.is_active = is_active
                session.commit()
                session.flush()  # Ensure changes are written
                print(f"✅ Toggled {email} to is_active={is_active}")
                return True
            else:
                print(f"❌ Member {email} not found")
                return False
    except Exception as e:
        print(f"❌ Error toggling status: {e}")
        import traceback
        traceback.print_exc()
        return False

def get_active_a_team_members():
    """Get only active A-Team members"""
    with get_session() as session:
        members = session.query(ATeamMember).filter_by(is_active=True).all()
        return pd.DataFrame([{
            'email': m.email,
            'full_name': m.full_name,
            'is_active': m.is_active
        } for m in members])

def get_all_a_team_members_with_status():
    """Get all A-Team members with their active status"""
    # import pandas as pd
    with get_session() as session:
        members = session.query(ATeamMember).all()
        return pd.DataFrame([{
            'email': m.email,
            'full_name': m.full_name,
            'is_active': m.is_active if hasattr(m, 'is_active') else True
        } for m in members])


def toggle_a_team_member_status_direct(email, is_active):
    """
    Toggle the active status of an A-Team member using direct session
    
    Args:
        email: Email of the A-Team member
        is_active: Boolean - True to activate, False to deactivate
    """
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DB_FILE = os.path.join(BASE_DIR, "database", "fta.db")
    DB_PATH = f"sqlite:///{DB_FILE}"
    
    engine = create_engine(DB_PATH, connect_args={"check_same_thread": False})
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        member = session.query(ATeamMember).filter_by(email=email).first()
        
        if member:
            print(f"Found member: {member.email}, current status: {member.is_active}")
            member.is_active = is_active
            session.commit()
            print(f"Updated {email} to is_active={is_active}")
            
            # Verify the change
            session.refresh(member)
            print(f"Verified: {member.email} is now is_active={member.is_active}")
            
            return True
        else:
            print(f"Member {email} not found in database")
            return False
            
    except Exception as e:
        print(f"Error toggling status: {e}")
        import traceback
        traceback.print_exc()
        session.rollback()
        return False
    finally:
        session.close()


# Even simpler version using raw SQL
def toggle_a_team_member_status_sql(email, is_active):
    """
    Toggle using raw SQL - most reliable method
    """
    import sqlite3
    
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DB_FILE = os.path.join(BASE_DIR, "database", "fta.db")
    
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Check if member exists
        cursor.execute("SELECT email, is_active FROM a_team_members WHERE email = ?", (email,))
        result = cursor.fetchone()
        
        if result:
            print(f"Current status for {email}: {result[1]}")
            
            # Update the status
            cursor.execute(
                "UPDATE a_team_members SET is_active = ? WHERE email = ?",
                (1 if is_active else 0, email)
            )
            conn.commit()
            
            # Verify
            cursor.execute("SELECT is_active FROM a_team_members WHERE email = ?", (email,))
            new_status = cursor.fetchone()[0]
            print(f"New status for {email}: {new_status}")
            
            conn.close()
            return True
        else:
            print(f"Member {email} not found")
            conn.close()
            return False
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False
# ============ AUTH ============

def authenticate_user(email, password):
    db: Session = SessionLocal()
    user = db.query(User).filter_by(email=email).first()
    db.close()
    return user and bcrypt.checkpw(password.encode(), user.password_hash.encode() if isinstance(user.password_hash, str) else user.password_hash)

def get_user_role(email):
    db: Session = SessionLocal()
    user = db.query(User).filter_by(email=email).first()
    db.close()
    return user.role if user else None

def reset_password(email, new_password):
    db: Session = SessionLocal()
    user = db.query(User).filter_by(email=email).first()
    if user:
        user.password_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt())
        db.commit()
    db.close()


# ============ EMAIL ============

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
    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = sender_email
    message["To"] = receiver_email
    message.attach(MIMEText(body, "html"))

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
    db = SessionLocal()
    log = EmailLogs(
        fta_id=fta_id,
        fta_name=fta_name,
        email=email,
        subject=subject,
        status=status,
        error_message=error_message,
        timestamp=datetime.now()  # ✅ Correct: raw datetime object
    )
    db.add(log)
    db.commit()
    db.close()

def email_already_sent(fta_id):
    db: Session = SessionLocal()
    exists = db.query(EmailLogs).filter_by(fta_id=fta_id, status='sent').first()
    db.close()
    return exists is not None

# --- New function to resend failed emails ---
def resend_failed_emails():
    db = SessionLocal()
    failed_logs = db.query(EmailLogs).filter(EmailLogs.status == "failed").all()
    db.close()

    if not failed_logs:
        st.info("✅ No failed email logs to resend.")
        return

    st.write(f"🔄 Attempting to resend {len(failed_logs)} failed emails...")

    for log in failed_logs:
        success, subject = send_email(log.email, log.fta_name)

        # Capture new log with error message if failed
        if success:
            log_email_sent(log.fta_id, log.email, log.fta_name, subject, status="sent")
        else:
            log_email_sent(
                log.fta_id,
                log.email,
                log.fta_name,
                subject or "No Subject",
                status="failed",
                error_message="Retry failed"  # Will be overwritten by send_email's error message handling
            )

    st.success("✅ Resend attempt completed.")
    

def get_all_a_team_members():
    db = SessionLocal()
    members = db.query(User).filter(User.role == "A-Team").all()
    db.close()

    return pd.DataFrame([{
        "id": m.id,
        "name": m.name,
        "email": m.email
    } for m in members])

def add_a_team_member(email, full_name):
    db = SessionLocal()
    existing = db.query(User).filter(User.email == email).first()
    if not existing:
        new_member = User(email=email, name=full_name, role="A-Team")
        db.add(new_member)
        db.commit()
    db.close()

def get_email_logs():
    db = SessionLocal()
    logs = db.query(EmailLogs).order_by(EmailLogs.timestamp.desc()).all()
    db.close()

    return pd.DataFrame([{
        "fta_id": log.fta_id,
        "fta_name": log.fta_name,
        "email": log.email,
        "subject": log.subject,
        "status": log.status,
        "error_message": log.error_message,
        "timestamp": log.timestamp
    } for log in logs])


def clear_email_logs():
    db = SessionLocal()
    db.query(EmailLogs).delete()
    db.commit()
    db.close()


def delete_failed_email_logs():
    db = SessionLocal()
    db.query(EmailLogs).filter(
        or_(
            EmailLogs.status == None,
            func.lower(EmailLogs.status).in_(["failed", "error"])
        )
    ).delete(synchronize_session=False)
    db.commit()
    db.close()


def init_assignment_tracker():
    db = SessionLocal()
    tracker = db.query(AssignmentTracker).filter_by(id=1).first()
    if not tracker:
        tracker = AssignmentTracker(id=1, last_assigned_index=-1)
        db.add(tracker)
        db.commit()
    db.close()

def add_a_team_member(email, full_name):
    db = SessionLocal()
    existing = db.query(User).filter_by(email=email).first()
    if not existing:
        member = User(email=email, name=full_name, role="A-Team")
        db.add(member)
        db.commit()
    db.close()


def get_all_a_team_members():
    db = SessionLocal()
    members = db.query(User).filter(User.role == "A-Team").all()
    db.close()
    
    # Convert to DataFrame
    return pd.DataFrame([{
        "id": member.id,
        "name": member.name,
        "email": member.email,
        "role": member.role
    } for member in members])


def get_existing_assignments():
    db = SessionLocal()
    assignments = db.query(FtaAssignments).all()
    db.close()

    return pd.DataFrame([{
        "fta_id": a.fta_id,
        "name": a.name,
        "assigned_to": a.assigned_to,
        "assigned_at": a.assigned_at
    } for a in assignments])


def assign_new_ftas(fta_df):
    fta_df.columns = fta_df.columns.str.strip()

    # Ensure the FTA ID column exists in the sheet data
    if "FTA ID" not in fta_df.columns:
        raise ValueError("Missing 'FTA ID' column in FTA data (Google Sheet).")

    # Get existing assignments from DB (empty if none)
    try:
        existing_assignments = get_existing_assignments()
        assigned_ids = set(existing_assignments['fta_id']) if not existing_assignments.empty else set()
    except Exception as e:
        print(f"[Assign Info] No existing assignments found: {e}")
        assigned_ids = set()

    # Only assign FTAs that are not already assigned
    unassigned_ftas = fta_df[~fta_df['FTA ID'].isin(assigned_ids)].copy()
    if unassigned_ftas.empty:
        print("[Assign Info] No unassigned FTAs found.")
        return existing_assignments

    db = SessionLocal()

    # Get A-Team members
    members = db.query(User).filter(User.role == "A-Team").all()
    member_count = len(members)
    if member_count == 0:
        db.close()
        raise Exception("No A-Team members available for assignment.")

    # Get last assigned index for round-robin distribution
    tracker = db.query(AssignmentTracker).filter_by(id=1).first()
    last_index = tracker.last_assigned_index if tracker else -1

    assignments = []
    current_index = (last_index + 1) % member_count

    for _, row in unassigned_ftas.iterrows():
        assigned_to_user = members[current_index]
        assignment = FtaAssignments(
            fta_id=row["FTA ID"],
            name=row.get("Full Name", "Unknown"),
            assigned_to=assigned_to_user.email,
            assigned_by=assigned_to_user.id,
            assigned_at=datetime.now()
        )
        assignments.append(assignment)
        current_index = (current_index + 1) % member_count

    try:
        db.add_all(assignments)

        # Update tracker
        if tracker:
            tracker.last_assigned_index = (current_index - 1) % member_count
        else:
            tracker = AssignmentTracker(id=1, last_assigned_index=(current_index - 1) % member_count)
            db.add(tracker)

        db.commit()
        print(f"[Assign Success] Assigned {len(assignments)} new FTAs.")
    except SQLAlchemyError as e:
        db.rollback()
        print(f"[DB Error] Assignment failed: {e}")
    finally:
        db.close()

    return get_existing_assignments()


def hash_pii(value):
    """Hash PII values using SHA-256."""
    if pd.isna(value) or value is None:
        return None
    return hashlib.sha256(str(value).encode('utf-8')).hexdigest()

def sync_and_assign_fta_responses(gsheet_url):
    print("\n=== [SYNC START] ===")
    try:
        # Fetch data from Google Sheet
        df = pd.read_csv(gsheet_url)
        df.columns = df.columns.str.strip()

        print(f"[Sync Info] Pulled {len(df)} rows from Google Sheets.")
        print(f"[Sync Info] Columns found: {list(df.columns)}")

        # Normalize column names
        col_map = {
            "FTA ID": "FTA ID",
            "fta_id": "FTA ID",
            "Fta Id": "FTA ID"
        }
        df.rename(columns={k: v for k, v in col_map.items() if k in df.columns}, inplace=True)

        if "FTA ID" not in df.columns:
            print("[Sync Error] 'FTA ID' column is missing in the sheet.")
            return pd.DataFrame()

        # Drop duplicates
        df = df.drop_duplicates(subset=["FTA ID"]).reset_index(drop=True)

        if df.empty:
            print("[Sync Info] No data available after deduplication.")
            return pd.DataFrame()

    except Exception as e:
        print(f"[Sync Error] Failed to fetch sheet: {e}")
        return pd.DataFrame()

    # === DB Session ===
    db = SessionLocal()
    try:
        for _, row in df.iterrows():
            fta_id = row.get("FTA ID")
            name = row.get("Full Name", "FTA")
            email = row.get("Email address")

            if not fta_id:
                print(f"[Skip] Missing FTA ID for row: {row.to_dict()}")
                continue
            if not email:
                print(f"[Skip] Missing email for FTA ID {fta_id}")
                continue

            # Hash PII before storing
            hashed_email = hash_pii(email)
            hashed_name = hash_pii(name)
            hashed_phone = hash_pii(row.get("Phone number"))
            hashed_address = hash_pii(row.get("Home Address"))

            existing = db.query(FtaResponses).filter(FtaResponses.FTA_ID == fta_id).first()

            if existing:
                print(f"[Update] Updating existing FTA ID {fta_id}")
                existing.Timestamp = pd.to_datetime(row.get("Timestamp")) if row.get("Timestamp") else None
                existing.Email_address = hashed_email
                existing.Full_Name = hashed_name
                existing.Phone_number = hashed_phone
                existing.Gender = row.get("Gender")
                existing.Home_Address = hashed_address
                existing.Service_Experience = int(row.get("Service Experience", 0))
                existing.Worship_Experience = int(row.get("Worship Experience", 0))
                existing.Word_Experience = float(row.get("Word Experience", 0.0))
                existing.General_Feedback = row.get("General Feedback")
                existing.Invited_By = row.get("Invited By")
                existing.Membership_Interest = row.get("Membership Interest")
                existing.Consent = row.get("Consent")
                existing.Meeting_Date = pd.to_datetime(row.get("Meeting Date")) if row.get("Meeting Date") else None
            else:
                print(f"[Insert] Adding new FTA ID {fta_id}")
                new_response = FtaResponses(
                    Timestamp=pd.to_datetime(row.get("Timestamp")) if row.get("Timestamp") else None,
                    Email_address=hashed_email,
                    Full_Name=hashed_name,
                    Phone_number=hashed_phone,
                    Gender=row.get("Gender"),
                    Home_Address=hashed_address,
                    Service_Experience=int(row.get("Service Experience", 0)),
                    Worship_Experience=int(row.get("Worship Experience", 0)),
                    Word_Experience=float(row.get("Word Experience", 0.0)),
                    General_Feedback=row.get("General Feedback"),
                    Invited_By=row.get("Invited By"),
                    Membership_Interest=row.get("Membership Interest"),
                    Consent=row.get("Consent"),
                    Meeting_Date=pd.to_datetime(row.get("Meeting Date")) if row.get("Meeting Date") else None,
                    FTA_ID=fta_id
                )
                db.add(new_response)

                # Email sending logic (use unhashed values for actual sending)
                if not email_already_sent(fta_id):
                    sent, subject = send_email(email, name)
                    status = "sent" if sent else "failed"
                    log_email_sent(fta_id, email, name, subject, status, None if sent else "Send error")

        db.commit()
        print("[Sync Success] Changes committed to database.")

    except SQLAlchemyError as commit_err:
        db.rollback()
        print(f"[DB Commit Error] {commit_err}")
    finally:
        db.close()

    # === Assign FTAs AFTER saving, using the same Google Sheet data ===
    try:
        if not df.empty:
            assign_new_ftas(df)
            print("[Assignment] FTA assignments updated successfully.")
    except Exception as e:
        print(f"[Assignment Error] {e}")

    print("=== [SYNC END] ===\n")
    return df


def get_available_a_team_members():
    """
    Get only active A-Team members who are available for new assignments
    """
    with get_session() as session:
        active_members = session.query(ATeamMember).filter_by(is_active=True).all()
        return [member.email for member in active_members]

def assign_ftas_to_active_members(fta_list):
    """
    Distribute FTAs only among active A-Team members
    
    Args:
        fta_list: List of FTA records to assign
    
    Returns:
        Dictionary mapping FTA IDs to assigned member emails
    """
    with get_session() as session:
        # Get active members only
        active_members = session.query(ATeamMember).filter_by(is_active=True).all()
        
        if not active_members:
            raise ValueError("No active A-Team members available for assignment")
        
        # Get current assignment counts for active members only
        active_emails = [m.email for m in active_members]
        assignment_counts = (
            session.query(
                FtaAssignments.assigned_to,
                func.count(FtaAssignments.id).label('count')
            )
            .filter(FtaAssignments.assigned_to.in_(active_emails))
            .group_by(FtaAssignments.assigned_to)
            .all()
        )
        
        # Create count dictionary
        counts = {email: 0 for email in active_emails}
        for email, count in assignment_counts:
            counts[email] = count
        
        # Sort members by current assignment count (least assigned first)
        sorted_members = sorted(counts.items(), key=lambda x: x[1])
        
        # Distribute FTAs
        assignments = {}
        member_index = 0
        
        for fta in fta_list:
            assigned_email = sorted_members[member_index][0]
            assignments[fta['id']] = assigned_email
            
            # Update count for next iteration
            sorted_members[member_index] = (assigned_email, sorted_members[member_index][1] + 1)
            sorted_members.sort(key=lambda x: x[1])  # Re-sort after increment
            
            # Move to next member (round-robin style)
            member_index = (member_index + 1) % len(sorted_members)
        
        return assignments

# Example usage in your assignment workflow:
def process_fta_assignments(uploaded_ftas):
    """
    Process FTA assignments - only assigns to active members
    """
    try:
        assignments = assign_ftas_to_active_members(uploaded_ftas)
        
        with get_session() as session:
            for fta_id, email in assignments.items():
                assignment = FtaAssignments(
                    fta_id=fta_id,
                    assigned_to=email,
                    assigned_at=datetime.now()
                    # ... other fields
                )
                session.add(assignment)
            session.commit()
        
        return True, f"Successfully assigned {len(assignments)} FTAs to active members"
    
    except ValueError as e:
        return False, str(e)
    except Exception as e:
        return False, f"Assignment failed: {str(e)}"
