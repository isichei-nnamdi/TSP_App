import streamlit as st
import pandas as pd
from datetime import datetime
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, func
from models import Feedback, FtaAssignments
import os
from sqlalchemy import create_engine


# Absolute path to the database file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "database", "fta.db")

# Create the database folder if it doesn’t exist
os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)

# SQLAlchemy connection string
DB_PATH = f"sqlite:///{DB_FILE}"
engine = create_engine(DB_PATH, connect_args={"check_same_thread": False})

# Create session factory
Session = sessionmaker(bind=engine)

# DB_PATH = os.path.join(os.path.dirname(__file__), 'fta.db')
# engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
# Session = sessionmaker(bind=engine)

def show_feedback_tracking_page(go_to):
    df_fta_response = st.session_state["fta_data"]
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        st.write("")
    with col2:
        st.title("🔣️ FTA Feedback Tracking")
    
        email = st.session_state.get("email")
        if not email:
            st.warning("You must be logged in to access this page.")
            return
    
        session = Session()
    
        # Fetch assigned FTAs for this user (case-insensitive match)
        assigned_ftas = (
            session.query(FtaAssignments.fta_id)
            .filter(func.lower(FtaAssignments.assigned_to) == email.lower())
            .all()
        )
        assigned_ftas = pd.DataFrame(assigned_ftas, columns=["fta_id"])
    
        if assigned_ftas.empty:
            st.info("You don't have any assigned FTAs.")
            return
    
        # Merge with response data to include phone numbers
        assigned_ftas = assigned_ftas.merge(
            df_fta_response[["fta_id", "phone", "full_name"]],
            on="fta_id",
            how="left"
        )
    
        # Fetch feedback history for this user
        feedback_records = session.query(Feedback.fta_id, Feedback.call_type).filter_by(email=email).all()
        feedback_df = pd.DataFrame(feedback_records, columns=["fta_id", "call_type"])
    
        call_type = st.selectbox("Type of Call", [
            "1st call", "2nd call", "3rd call", "M&G Attended", "After Effect Confirmation"
        ])
    
        # Filter out FTAs that already have this call_type feedback
        if not feedback_df.empty:
            contacted_ids = feedback_df[feedback_df["call_type"] == call_type]["fta_id"].unique().tolist()
            available_ftas = assigned_ftas[~assigned_ftas["fta_id"].isin(contacted_ids)]
        else:
            available_ftas = assigned_ftas
    
        if available_ftas.empty:
            st.info(f"✅ All FTAs have already received '{call_type}' feedback.")
            st.stop()
    
        selected_fta = st.selectbox("Select FTA ID", options=available_ftas["fta_id"].tolist())
        phone_options = available_ftas[available_ftas["fta_id"] == selected_fta]["phone"].dropna().tolist()
        name_options = available_ftas[available_ftas["fta_id"] == selected_fta]["full_name"].dropna().tolist()
        st.selectbox("FTA Name", name_options)
        phone_selected_fta = st.selectbox("FTA Phone Number", options=phone_options if phone_options else ["No phone available"])
    
        call_success, feedback_1, met_date, mg_date, department = None, None, None, None, None
        general_feedback = ""
    
        if call_type == "1st call":
            call_success = st.selectbox("Was the call successful?", [
                "Yes", "Yes, but not reachable", "Yes, but switched off",
                "Yes, but didn't pick", "Yes, sent TSP communique", "Yes, sent a message"
            ])
            feedback_1 = st.selectbox("Feedback of 1st call", [
                "Close", "Just visiting", "Out of town", "Prayer request",
                "Transport needed", "Would love to join", "Hope to visit again",
                "Others (Please specify)"
            ])
            general_feedback = st.text_area("General Feedback on 1st call")
    
        elif call_type == "2nd call":
            met_date = st.date_input("Date you met your FTA")
            general_feedback = st.text_area("General Feedback on 2nd call")
    
        elif call_type == "3rd call":
            general_feedback = st.text_area("General Feedback on 3rd call")
    
        elif call_type == "M&G Attended":
            mg_date = st.date_input("Date for M&G")
            general_feedback = st.text_area("General Feedback on M&G Attended")
    
        elif call_type == "After Effect Confirmation":
            department = st.selectbox("Department handed over to", [
                "Audacity - Minister Gift", "Envagelism - Pastor Paul", "Warm Heart - Phillipa",
                "Prayer - Pastor Paul", "Audio-visual & Photography - Lori",
                "Giants & Pillars - Sarah Ozobu", "Social Media - Jeminine",
                "Refinery - Pastor Chibuzor", "Media Projection - Joshua", "Potters - Solomon",
                "Greeters - Rosemary", "Lawyers Club - Barrister Ahmed",
                "Help Desk - Pastor Yemi", "Glamour House - Barrister Amaka",
                "Couples Commiunity - Pastor Victor", "Ladies Community - Dorcas Smith",
                "Gents Community - Peter Obasi", "Medical Community - Doctor Jane",
                "Traffic - Mr. Emmanuel", "Transport - Francis Ozobu"
            ])
            general_feedback = st.text_area("General Feedback on Department Handover")
    
        if st.button("Submit Feedback"):
            feedback = Feedback(
                email=email,
                fta_id=selected_fta,
                call_type=call_type,
                call_success=call_success,
                feedback_1=feedback_1,
                met_date=met_date if met_date else None,
                mg_date=mg_date if mg_date else None,
                # met_date=met_date.isoformat() if met_date else None,
                # mg_date=mg_date.isoformat() if mg_date else None,
                department=department,
                general_feedback=general_feedback,
                submitted_at=datetime.now()
            )
            session.add(feedback)
            session.commit()
    
            st.success("✅ Feedback submitted successfully!")
            st.rerun()
    
    
        st.markdown("---")
        st.subheader("📜 Contact History")
    
        all_feedback = session.query(Feedback).filter_by(email=email).all()
        if all_feedback:
            df_history = pd.DataFrame([f.__dict__ for f in all_feedback])
            df_history.drop("_sa_instance_state", axis=1, inplace=True)
            st.dataframe(df_history.sort_values("submitted_at", ascending=False), use_container_width=True)
        else:
            st.info("No feedback history yet.")

    with col3:
        st.write("")
