import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

DB_PATH = "fta.db"

def hash_value(value):
    if value is None:
        return None
    return hashlib.sha256(value.encode('utf-8')).hexdigest() 


def show_feedback_tracking_page(go_to):
    df_fta_response = st.session_state["fta_data"]
    st.title("🗣️ FTA Feedback Tracking")

    email = st.session_state.get("email")
    if not email:
        st.warning("You must be logged in to access this page.")
        return

    with sqlite3.connect(DB_PATH) as conn:
        assigned_ftas = pd.read_sql_query("SELECT fta_id FROM fta_assignments WHERE assigned_to = ?", conn, params=(email,))

    if assigned_ftas.empty:
        st.info("You don't have any assigned FTAs.")

    else:
        # --- Fetch feedback history ---
        with sqlite3.connect(DB_PATH) as conn:
            feedback_df = pd.read_sql_query("SELECT fta_id, call_type FROM fta_feedback WHERE email = ?", conn, params=(email,))

        # --- Select Call Type ---
        call_type = st.selectbox("Type of Call", [
            "1st call", "2nd call", "3rd call", "M&G Attended", "After Effect Confirmation"
        ])

        # --- Filter FTAs: exclude those with feedback for this call_type ---
        if not feedback_df.empty:
            contacted_ids = feedback_df[feedback_df["call_type"] == call_type]["fta_id"].unique().tolist()
            available_ftas = assigned_ftas[~assigned_ftas["fta_id"].isin(contacted_ids)]
        else:
            available_ftas = assigned_ftas

        if available_ftas.empty:
            st.info(f"✅ All FTAs have already received '{call_type}' feedback.")
            st.stop()

        selected_fta = st.selectbox("Select FTA ID", options=available_ftas["fta_id"].tolist())
        phone_selected_fta = st.selectbox("FTA Phone Number", options=df_fta_response[df_fta_response["fta_id"]==selected_fta]["phone"])

        # --- Conditional Fields ---
        call_success = None
        feedback_1 = None
        met_date = None
        mg_date = None
        department = None
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

        # --- Submit Feedback ---
        if st.button("Submit Feedback"):
            submitted_at = datetime.now().isoformat()
            
            with sqlite3.connect(DB_PATH) as conn:
                conn.execute('''
                    INSERT INTO fta_feedback (
                        email, fta_id, call_type, call_success, feedback_1, 
                        met_date, mg_date, department, general_feedback, submitted_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    email, selected_fta, call_type, call_success, feedback_1,
                    met_date.isoformat() if met_date else None,
                    mg_date.isoformat() if mg_date else None,
                    department, general_feedback, submitted_at
                ))
                conn.commit()

            st.success("✅ Feedback submitted successfully!")
            st.rerun()


    
    # === Contact History ===
    st.markdown("---")
    st.subheader("📜 Contact History")
    with sqlite3.connect(DB_PATH) as conn:
        feedback_df = pd.read_sql_query("SELECT * FROM fta_feedback WHERE email = ?", conn, params=(email,))

    if not feedback_df.empty:
        st.dataframe(feedback_df.sort_values("submitted_at", ascending=False), use_container_width=True)
    else:
        st.info("No feedback history yet.")
