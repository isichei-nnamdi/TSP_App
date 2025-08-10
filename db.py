import streamlit as st
import bcrypt
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


