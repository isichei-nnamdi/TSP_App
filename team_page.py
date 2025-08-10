import streamlit as st
import pandas as pd
# import sqlite3
import plotly.graph_objects as go
from datetime import datetime
from db import get_all_a_team_members, add_a_team_member, get_email_logs, clear_email_logs, delete_failed_email_logs
from reset_db import reset_database
import os
from sqlalchemy import select
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import FtaAssignments, ATeamMember, Feedback
from sqlalchemy import func
from db_session import get_session


# ---------------------------------------------------------------------
#  TEAM PAGE  ── Filters: Date range  +  A‑Team member  +  Reset button
# ---------------------------------------------------------------------
def show_team_page(go_to):
    # ---------------------------------------------------------------
    # 1) LOAD DATA SAFELY FROM SESSION_STATE
    # ---------------------------------------------------------------
    if st.session_state.get("role") != "Admin":
        st.error("You are not authorized to view this page.")
        st.stop()

    

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
    session = Session()
    
    # # Read the file in binary mode
    # with open(DB_PATH, "rb") as f:
    #     db_bytes = f.read()
    
    # # Provide download button in the app
    # st.download_button(
    #     label="Download SQLite Database",
    #     data=db_bytes,
    #     file_name="fta.db",
    #     mime="application/octet-stream"
    # )
    
    st.markdown("### 👥 A-Team Management")

    col1, col2 = st.columns(2)
    with col1:
        st.write(" ")
        st.write(" ")
        # === Add new member ===
        with st.expander("➕ Add New A-Team Member"):
            email = st.text_input("Email")
            full_name = st.text_input("Full Name")
            create_login = st.checkbox("Also create login account with default password")
            if st.button("Add Member"):
                if email and full_name:
                    add_a_team_member(email, full_name)
                    if create_login:
                        from db import add_user
                        add_user(email, "password1234", role="A-Team")
                    st.success("Member added successfully!")
                    st.rerun()
                else:
                    st.warning("Please enter both email and full name.")

        # === Load members
        members_df = get_all_a_team_members()

        # === Load FTA count
        fta_count = (
            session.query(
                FtaAssignments.assigned_to.label("email"),
                func.count(FtaAssignments.id).label("fta_count")
            )
            .group_by(FtaAssignments.assigned_to)
            .all()
        )
        fta_counts = pd.DataFrame(fta_count, columns=["email", "fta_count"])
        assignments_df = pd.read_sql(select(FtaAssignments), session.bind)

        # Merge carefully
        members_df = pd.merge(members_df, fta_counts, on="email", how="left")
        members_df["fta_count"] = members_df["fta_count"].fillna(0).astype(int)

    with col2:
        # === Search/Filter ===
        search = st.text_input("🔍 Search by email or name", placeholder="🔍 Search by email or name", label_visibility="hidden").lower()
        filtered_df = members_df[members_df.apply(
            lambda row: search in row["email"].lower() or search in row["full_name"].lower(), axis=1
        )] if search else members_df

    # --- Load members and assignments ---
    assignments_df = pd.read_sql(select(FtaAssignments), session.bind)
    all_feedback = pd.read_sql(select(Feedback), session.bind)

    
    if all_feedback.empty:
        print("✅ No feedback has been submitted yet.")
        contacted_ids = []
    else:
        all_feedback["submitted_at"] = pd.to_datetime(all_feedback["submitted_at"], errors="coerce")
        all_feedback["Feedback_id"] = all_feedback["fta_id"] + " - " + all_feedback["call_type"]
        contacted_ids = all_feedback["fta_id"].unique()


    st.markdown("---")

    st.markdown("##### Summary of Assigned & Contacted Calls")

    col1, col2, col3, col4 = st.columns([2, 1, 1, 1.5])
    with col1:
        st.write("")
    with col2:
        # Ensure assigned_at column is datetime
        # Store as string
        min_date_str = "01/01/2025"
        
        assignments_df["assigned_at"] = pd.to_datetime(assignments_df["assigned_at"], errors="coerce")
        # Convert to date object if needed
        min_date = datetime.strptime(min_date_str, "%m/%d/%Y").date()
        # min_date = assignments_df["assigned_at"].min().date() if not assignments_df["assigned_at"].isna().all() else datetime.today().date()
        max_date = datetime.today().date() # all_feedback["submitted_at"].max().date() if not all_feedback["submitted_at"].isna().all() else
        start_date = st.date_input("Start Date",
                                value=min_date,
                                min_value=min_date,
                                max_value=max_date,
                                key="start_date")
    with col3:
        end_date = st.date_input("End Date",
                                value=max_date,
                                min_value=min_date,
                                max_value=max_date,
                                key="end_date")
    with col4:
        selected_member = st.selectbox(
        label="Filter by A-Team Member",
        options=["All"] + assignments_df["assigned_to"].dropna().drop_duplicates().tolist()
    )

    # Filter by date
    filtered_df = assignments_df[
        (assignments_df["assigned_at"].dt.date >= start_date) &
        (assignments_df["assigned_at"].dt.date <= end_date)
    ]

    # Filter by selected A-Team member
    if selected_member != "All":
        filtered_df = filtered_df[filtered_df["assigned_to"] == selected_member]


    # --- Compute assignment summary ---
    summary_data = []

    for _, member in members_df.iterrows():
        email = member["email"]
        if member.get("name"):
            full_name = member["name"]
        else:
            full_name = email.split("@")[0].split(".")[0].capitalize()
      

        # Get all assignments for the current member
        member_ftas = filtered_df[filtered_df["assigned_to"] == email]
        total = len(member_ftas)
        contacted = member_ftas["fta_id"].isin(contacted_ids).sum()
        not_contacted = total - contacted

        summary_data.append({
            "Email": email,
            "Name": full_name,
            "Total Assigned": total,
            "Contacted": contacted,
            "Not Contacted": not_contacted
        })

    # --- Convert to DataFrame and show ---
    expected_cols = ["Email", "Name", "Total Assigned", "Contacted", "Not Contacted"]
    summary_df = pd.DataFrame(summary_data)

    # Ensure DataFrame has the expected columns
    for col in expected_cols:
        if col not in summary_df.columns:
            summary_df[col] = 0

    # Compute totals safely
    total_assigned = summary_df["Total Assigned"].sum()
    total_contacted = summary_df["Contacted"].sum()
    total_not_contacted = summary_df["Not Contacted"].sum()

    # Define styles
    card_style = """
        <style>
        .card-container {
            display: flex;
            justify-content: space-between;
            gap: 20px;
        }
        .card {
            flex: 1;
            padding: 20px;
            border-radius: 12px;
            color: white;
            font-family: Arial, sans-serif;
            box-shadow: 2px 2px 12px rgba(0,0,0,0.1);
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            min-height: 120px;
        }
        .card-red {
            background-color: #a00000;
        }
        .card-yellow {
            background-color: #ffe640;
            color: black;
        }
        .card-icon {
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 14px;
            font-weight: 500;
        }
        .card-value {
            font-size: 32px;
            font-weight: bold;
            margin-top: 5px;
        }
        </style>
    """

    card_html = f"""
    <div class="card-container">
        <div class="card card-red">
            <div class="card-icon">Assigned FTAs<span>📅</span></div>
            <div class="card-value">{total_assigned}</div>
        </div>
        <div class="card card-yellow">
            <div class="card-icon">Contacted FTAs<span>✆✉</span></div>
            <div class="card-value">{total_contacted}</div>
        </div>
        <div class="card card-red">
            <div class="card-icon">Not Contacted FTAs<span>👎</span></div>
            <div class="card-value">{total_not_contacted}</div>
        </div>
    </div>
    """

    st.markdown(card_style, unsafe_allow_html=True)
    st.markdown(card_html, unsafe_allow_html=True)

    st.write("")
    st.write("")

    if selected_member == "All":
        st.dataframe(summary_df, use_container_width=True)
    else:
        st.dataframe(summary_df[summary_df["Email"] == selected_member], use_container_width=True)
    st.markdown("---")


    # === Display Feedback Table ===
    st.markdown("##### 📝 All Feedback from A-Team Members")
    try:
        col1, col2, col3, col4 = st.columns([2, 1, 1, 1.5])
        with col1:
            st.write("")
        with col2:
            # Store as string
            min_date_str = "01/01/2025"
            min_date = datetime.strptime(min_date_str, "%m/%d/%Y").date()
            # min_date = all_feedback["submitted_at"].min().date() if not all_feedback["submitted_at"].isna().all() else datetime.today().date()
            max_date = datetime.today().date() # all_feedback["submitted_at"].max().date() if not all_feedback["submitted_at"].isna().all() else
            start_date = st.date_input("Start Date",
                                    value=min_date,
                                    min_value=min_date,
                                    max_value=max_date)
        with col3:
            end_date = st.date_input("End Date",
                                    value=max_date,
                                    min_value=min_date,
                                    max_value=max_date)
        with col4:
            selected_member = st.selectbox(
            label="Filter by A-Team Member",
            options=["All"] + all_feedback["email"].dropna().drop_duplicates().tolist()
        )
    
        # Filter by date
        filtered_df = all_feedback[
            (all_feedback["submitted_at"].dt.date >= start_date) &
            (all_feedback["submitted_at"].dt.date <= end_date)
        ]
    
        # Filter by selected A-Team member
        if selected_member != "All":
            filtered_df = filtered_df[filtered_df["email"] == selected_member]
    
        calltype, callsuccess, feedback = st.columns(3)
        with calltype:
            call_type = filtered_df["call_type"].value_counts().to_dict()
    
            if call_type:
                labels = list(call_type.keys())
                values = list(call_type.values())
    
                fig5 = go.Figure(go.Bar(
                    x=values,
                    y=labels,
                    orientation="h",
                    marker_color="#8B0000",
                    text=values,
                    textposition='outside',
                    textfont=dict(color="#8B0000")
                ))
    
                fig5.update_layout(
                    title_text="Call Type",
                    xaxis_title="Number of Calls",
                    yaxis_title=""
                )
    
                st.plotly_chart(fig5, use_container_width=True)
            else:
                st.info("No type of calls recorded yet.")
        
        with callsuccess:
            call_success = filtered_df["call_success"].value_counts().to_dict()
    
            if call_success:
                labels = list(call_success.keys())
                values = list(call_success.values())
    
                fig5 = go.Figure(go.Bar(
                    x=values,
                    y=labels,
                    orientation="h",
                    marker_color= "#ffe640", # "#8B0000",
                    text=values,
                    textposition='outside',
                    textfont=dict(color="#8B0000")
                ))
    
                fig5.update_layout(
                    title_text="Was your call successful?",
                    xaxis_title="Number of Calls",
                    yaxis_title=""
                )
    
                st.plotly_chart(fig5, use_container_width=True)
            else:
                st.info("No successful calls made yet.")
        
        with feedback:
            call_feedback = filtered_df["feedback_1"].value_counts().to_dict()
    
            if call_feedback:
                labels = list(call_feedback.keys())
                values = list(call_feedback.values())
    
                fig5 = go.Figure(go.Bar(
                    x=values,
                    y=labels,
                    orientation="h",
                    marker_color="#8B0000",
                    text=values,
                    textposition='outside',
                    textfont=dict(color="#8B0000")
                ))
    
                fig5.update_layout(
                    title_text="Call Feedback",
                    xaxis_title="Number of Calls",
                    yaxis_title=""
                )
    
                st.plotly_chart(fig5, use_container_width=True)
            else:
                st.info("No calls feedback recorded yet.")
                
        st.dataframe(filtered_df.sort_values("submitted_at", ascending=False), use_container_width=True)
    
        st.markdown("---")
    
        # === Allow deletion ===
        st.markdown("###### ❌ Delete Feedback from A-Team Members")
    
        # Ensure there's a primary key column for deletion (id), otherwise fallback
        if "id" not in all_feedback.columns:
            st.warning("Feedback table must include an 'id' column for proper deletion.")
        else:
            # Create display labels for multiselect
            all_feedback["display_label"] = all_feedback.apply(
                lambda row: f"{row['fta_id']} - {row['call_type']} - {row['submitted_at'].strftime('%Y-%m-%d %H:%M') if pd.notnull(row['submitted_at']) else 'N/A'}",
                axis=1
            )
    
            # Build options as a dictionary: display_label -> id
            delete_options = {row["display_label"]: row["id"] for _, row in all_feedback.iterrows()}
    
            selected_labels = st.multiselect(
                "Select Feedback to Delete:",
                options=list(delete_options.keys())
            )
    
            # if st.button("Delete Selected Feedback"):
            #     if selected_labels:
            #         selected_ids = [delete_options[label] for label in selected_labels]
            #         with sqlite3.connect(DB_PATH) as conn:
            #             cursor = conn.cursor()
            #             cursor.executemany("DELETE FROM fta_feedback WHERE id = ?", [(fid,) for fid in selected_ids])
            #             conn.commit()
            #         st.success(f"Deleted {len(selected_ids)} feedback record(s).")
            #         st.rerun()
            #     else:
            #         st.warning("No feedback selected.")

            if st.button("Delete Selected Feedback"):
                if selected_labels:
                    selected_ids = [delete_options[label] for label in selected_labels]
                    
                    with get_session() as session:
                        session.query(Feedback).filter(Feedback.id.in_(selected_ids)).delete(synchronize_session=False)
                        session.commit()
                    
                    st.success(f"Deleted {len(selected_ids)} feedback record(s).")
                    st.rerun()
                else:
                    st.warning("No feedback selected.")
    
    
    
        st.markdown("##### 🔥 Delete Assigned FTAs")
    
        # === Load A-Team members for selection ===
        # with sqlite3.connect(DB_PATH) as conn:
        #     a_team_df = pd.read_sql_query("SELECT email, full_name FROM a_team_members", conn)
        with get_session() as session:
            a_team_data = session.query(ATeamMember.email, ATeamMember.full_name).all()
            a_team_df = pd.DataFrame(a_team_data, columns=["email", "full_name"])
    
        if a_team_df.empty:
            st.warning("No A-Team members available.")
            st.stop()
    
        selected_member = st.selectbox("Select A-Team Member", options=a_team_df["email"])
    
        # === Load assignments for that member ===
        # with sqlite3.connect(DB_PATH) as conn:
        #     query = "SELECT * FROM fta_assignments WHERE assigned_to = ?"
        #     member_assignments = pd.read_sql_query(query, conn, params=(selected_member,))

        with get_session() as session:
            assignments = (
                session.query(FtaAssignments)
                .filter(FtaAssignments.assigned_to == selected_member)
                .all()
            )
            member_assignments = pd.DataFrame(
                [a.__dict__ for a in assignments],
                columns=[col.name for col in FtaAssignments.__table__.columns]
            )
            # Remove SQLAlchemy internal state column
            if "_sa_instance_state" in member_assignments.columns:
                member_assignments.drop(columns=["_sa_instance_state"], inplace=True)

        if not member_assignments.empty:
            st.write(f"Assigned FTAs for {selected_member}")
            st.dataframe(member_assignments, use_container_width=True)

           
            selected_ftas = st.multiselect(
                "Select FTAs to delete:",
                options=member_assignments["fta_id"],
                format_func=lambda x: f"{x} - {member_assignments[member_assignments['fta_id'] == x]['name'].values[0]}"
            )
    
            # if st.button("Delete Selected FTAs"):
            #     with sqlite3.connect(DB_PATH) as conn:
            #         cursor = conn.cursor()
            #         for fta_id in selected_ftas:
            #             cursor.execute("DELETE FROM fta_assignments WHERE fta_id = ?", (fta_id,))
            #         conn.commit()
            #     st.success(f"{len(selected_ftas)} FTA(s) deleted.")
            #     st.rerun()


            if st.button("Delete Selected FTAs"):
                with get_session() as session:
                    for fta_id in selected_ftas:
                        session.query(FtaAssignments).filter(FtaAssignments.fta_id == fta_id).delete()
                    session.commit()

                st.success(f"{len(selected_ftas)} FTA(s) deleted.")
                st.rerun()

        else:
            st.info(f"No FTAs assigned to {selected_member}.")
        
    
        st.markdown("##### 🔁 Reassign FTAs from One A-Team Member to Another")
        # with sqlite3.connect(DB_PATH) as conn:
        #     fta_options = pd.read_sql_query("SELECT fta_id, full_name, assigned_to FROM fta_assignments", conn)
        #     members_df = pd.read_sql_query("SELECT email FROM a_team_members", conn)
        with get_session() as session:
            # Query FTA assignments
            fta_data = session.query(
                FtaAssignments.fta_id,
                FtaAssignments.name,
                FtaAssignments.assigned_to
            ).all()
            fta_options = pd.DataFrame(fta_data, columns=["fta_id", "full_name", "assigned_to"])

            # Query A-Team members' emails
            members_data = session.query(ATeamMember.email).all()
            members_df = pd.DataFrame(members_data, columns=["email"])
    
        if not fta_options.empty and not members_df.empty:
            all_emails = members_df["email"].tolist()
    
            # === Select A-Team member to filter FTAs ===
            selected_source_member = st.selectbox("Select A-Team member to reassign from:", options=all_emails)
    
            # === Filter FTAs assigned to that member ===
            member_ftas = fta_options[fta_options["assigned_to"] == selected_source_member]
    
            if member_ftas.empty:
                st.info("No FTAs currently assigned to this member.")
            else:
                # === Multi-select FTAs to reassign ===
                selected_ftas = st.multiselect(
                    "Select FTAs to reassign:",
                    options=member_ftas["fta_id"],
                    format_func=lambda x: f"{x} - {member_ftas.loc[member_ftas['fta_id'] == x, 'full_name'].values[0]}"
                )
    
                # === Choose a different A-Team member to assign to ===
                assignable_members = [email for email in all_emails if email != selected_source_member]
                new_member = st.selectbox("Assign to:", options=assignable_members)
    
                # === Button to trigger reassignment ===
                if st.button("Reassign Selected FTAs"):
                    # if selected_ftas:
                    #     with sqlite3.connect(DB_PATH) as conn:
                    #         cursor = conn.cursor()
                    #         for fta_id in selected_ftas:
                    #             cursor.execute(
                    #                 "UPDATE fta_assignments SET assigned_to = ?, assigned_at = ? WHERE fta_id = ?",
                    #                 (new_member, datetime.now().isoformat(), fta_id)
                    #             )
                    #         conn.commit()
                    #     st.success(f"{len(selected_ftas)} FTA(s) reassigned from {selected_source_member} to {new_member}.")
                    #     st.rerun()
                    # else:
                    #     st.warning("Please select at least one FTA to reassign.")
                    if selected_ftas:
                        with get_session() as session:
                            for fta_id in selected_ftas:
                                assignment = session.query(FtaAssignments).filter_by(fta_id=fta_id).first()
                                if assignment:
                                    assignment.assigned_to = new_member
                                    assignment.assigned_at = datetime.now().isoformat()
                            session.commit()

                        st.success(f"{len(selected_ftas)} FTA(s) reassigned from {selected_source_member} to {new_member}.")
                        st.rerun()
                    else:
                        st.warning("Please select at least one FTA to reassign.")

        # --- Admin Dashboard Section ---
        st.subheader("📬 Email Logs")
    
        try:
            logs_df = get_email_logs()
        
            if logs_df.empty:
                st.info("No email logs found.")
            else:
                logs_df["timestamp"] = pd.to_datetime(logs_df["timestamp"])

                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write("")

                with col2:
                    with st.expander("🔍 Filter Logs"):
                        status_filter = st.multiselect("Status", logs_df["status"].unique())
                        date_range = st.date_input("Date range", [])
        
                filtered_df = logs_df.copy()
        
                if status_filter:
                    filtered_df = filtered_df[filtered_df["status"].isin(status_filter)]
        
                if len(date_range) == 2:
                    start, end = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
                    filtered_df = filtered_df[
                        (filtered_df["timestamp"] >= start) & (filtered_df["timestamp"] <= end)
                    ]
        
                total_emails = len(filtered_df)
                successful = (filtered_df["status"] == "sent").sum()
                failed = (filtered_df["status"] == "failed").sum()
        
                # Define styles
                card_style = """
                    <style>
                    .card-container {
                        display: flex;
                        justify-content: space-between;
                        gap: 20px;
                    }
                    .card {
                        flex: 1;
                        padding: 20px;
                        border-radius: 12px;
                        color: white;
                        font-family: Arial, sans-serif;
                        box-shadow: 2px 2px 12px rgba(0,0,0,0.1);
                        display: flex;
                        flex-direction: column;
                        justify-content: space-between;
                        min-height: 120px;
                    }
                    .card-red {
                        background-color: #a00000;
                    }
                    .card-yellow {
                        background-color: #ffe640;
                        color: black;
                    }
                    .card-icon {
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                        font-size: 14px;
                        font-weight: 500;
                    }
                    .card-value {
                        font-size: 32px;
                        font-weight: bold;
                        margin-top: 5px;
                    }
                    </style>
                """
        
                card_html = f"""
                <div class="card-container">
                    <div class="card card-red">
                        <div class="card-icon">Total Emails<span>📅</span></div>
                        <div class="card-value">{total_emails}</div>
                    </div>
                    <div class="card card-yellow">
                        <div class="card-icon">Successful<span>✆✉</span></div>
                        <div class="card-value">{successful}</div>
                    </div>
                    <div class="card card-red">
                        <div class="card-icon">Failed<span>👎</span></div>
                        <div class="card-value">{failed}</div>
                    </div>
                </div>
                """
        
                st.markdown(card_style, unsafe_allow_html=True)
                st.markdown(card_html, unsafe_allow_html=True)
                st.write("")
                st.write("")
                st.dataframe(filtered_df.sort_values("timestamp", ascending=False), use_container_width=True)

                col1, col2 = st.columns(2)
                with col1:
                    if st.button("🗑️ Delete all Failed Email Logs"):
                        delete_failed_email_logs()
                        st.success("All failed email logs deleted.")
                        st.rerun()
                with col2:
                    if st.button("🚨 Reset Email Logs"):
                        clear_email_logs()
                        st.success("All email logs cleared.")
                        st.rerun()
                        
        
        except Exception as e:
            st.error(f"Failed to load email logs: {e}")
    
    #     # Delete A-Team member
    #     st.subheader("Delete A-Team Member")

    #    # Fetch all members
    #     members = session.query(ATeamMember).all()

    #     if members:
    #         member_data = [
    #             {"Full Name": m.full_name, "Email": m.email}
    #             for m in members
    #         ]
    #         df_members = pd.DataFrame(member_data)
    #         st.dataframe(df_members)

    #         # build list for selection (you probably already have df_members)
    #         member_options = df_members["Email"].tolist()  # or build from session query

    #         selected_member_email = st.selectbox("Select member to delete", member_options)

    #         if st.button("Delete Selected Member"):
    #             # optionally strip whitespace
    #             email_to_delete = selected_member_email.strip()

    #             with get_session() as session:
    #                 session.query(ATeamMember).filter(ATeamMember.email == email_to_delete).delete(synchronize_session=False)
    #                 session.commit()

    #             st.success(f"Member '{email_to_delete}' deleted.")
    #             st.rerun()

    except Exception as e:
        st.warning("⚠️ No feedback data available at the moment.")
