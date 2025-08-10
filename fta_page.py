import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
import os

# --------------------------------
# === Database Path ===
# --------------------------------
# Absolute path to the database file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "database", "fta.db")

# Create the database folder if it doesn’t exist
os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)

# SQLAlchemy connection string
DB_PATH = f"sqlite:///{DB_FILE}"



def show_fta_page(go_to):
    # -----------------------------------------
    # === Validate Required Data in Session ===
    # -----------------------------------------
    if "fta_data" not in st.session_state or "fta_assignments" not in st.session_state:
        st.error("FTA data not available. Please return to the dashboard first.")
        st.stop()

    # --------------------------------
    # === Load Session Data ===
    # --------------------------------
    df_fta_response = st.session_state["fta_data"]
    assignments_df = st.session_state["fta_assignments"]
    user_email = st.session_state.get("email", "unknown")

    # Extract name before '@' and title-case it
    username = user_email.split("@")[0].title()

    # Get current hour
    current_hour = datetime.now().hour

    # Determine time-based greeting
    if 5 <= current_hour < 12:
        greeting = "Good morning"
    elif 12 <= current_hour < 17:
        greeting = "Good afternoon"
    elif 17 <= current_hour < 21:
        greeting = "Good evening"
    else:
        greeting = "Hello"

    # ------------------------------------------------
    # === Helper Function to Show Filtered Tables ===
    # ------------------------------------------------
    def show_table(title, df):
        if not df.empty:
            st.markdown(f"### {title}")
            st.dataframe(df.sort_values("assigned_at", ascending=False), use_container_width=True)
        else:
            st.info(f"No entries in: {title}")
                
    # ----------------------------------------------------
    # === Normalize and Rename Columns in FTA Response ===
    # ----------------------------------------------------
    if not df_fta_response.empty and len(df_fta_response.columns) > 0:
        df_fta_response.columns = df_fta_response.columns.astype(str).str.strip().str.lower()
        df_fta_response.rename(columns={
            "timestamp": "timestamp",
            "email address": "email",
            "full name": "full_name",
            "phone number": "phone",
            "gender": "gender",
            "home address": "location",
            "how was your overall service experience?": "service_experience",
            "amazing how will you rate your worship experience": "worship_experience",
            "how will you rate your word experience": "word_experience",
            "any general feedback for us? (e.g how can we improve)": "general_feedback",
            "who invited you to tsp?": "invited_by",
            "would you like to be a member of tsp?": "membership_interest",
            "i consent that the my data provided in this form can be used by the standpoint church as deemed appropriate.": "consent",
            "select the most convenient date for your one-on-one meeting with pastor phil.": "meeting_date",
            "fta id": "fta_id"
        }, inplace=True)
    else:
        st.warning("No data available to process or column headers are missing.")


    # -----------------------------------------
    # === Data Cleaning and Type Conversion ===
    # -----------------------------------------
    df_fta_response["fta_id"] = df_fta_response["fta_id"].astype(str).str.strip()
    df_fta_response["phone"] = df_fta_response["phone"].astype(str).str.strip()
    df_fta_response["timestamp"] = pd.to_datetime(df_fta_response["timestamp"], errors="coerce")
    assignments_df.columns = assignments_df.columns.str.strip().str.lower()
    assignments_df["fta_id"] = assignments_df["fta_id"].astype(str).str.strip()
    assignments_df["assigned_at"] = pd.to_datetime(assignments_df["assigned_at"], errors="coerce")

    # ------------------------------------------------
    # === Get Only FTAs Assigned to Logged-in User ===
    # ------------------------------------------------
    user_ftas = assignments_df[assignments_df["assigned_to"] == user_email]
    user_fta_ids = user_ftas["fta_id"].unique()

    # -------------------------------------------
    # === Join Responses with Assignment Info ===
    # -------------------------------------------
    enriched_ftas = pd.merge(
        df_fta_response[df_fta_response["fta_id"].isin(user_fta_ids)],
        user_ftas[["fta_id", "assigned_at"]],
        on="fta_id", how="left"
    )

    # ---------------------------------------
    # === Load Feedback Data from SQLite ===
    # ---------------------------------------
    # with sqlite3.connect(DB_PATH) as conn:
    #     feedback_df = pd.read_sql_query("SELECT * FROM fta_feedback WHERE email = ?", conn, params=(user_email,))
    from db_session import get_session
    from models import Feedback

    with get_session() as session:
        feedback_records = (
            session.query(Feedback)
            .filter(Feedback.email == user_email)
            .all()
        )

    # Convert to DataFrame
    # feedback_df = pd.DataFrame([record.__dict__ for record in feedback_records]).drop(columns=["_sa_instance_state"])
    # Extract only table columns into a DataFrame
    columns = Feedback.__table__.columns.keys()
    feedback_df = pd.DataFrame([{col: getattr(record, col) for col in columns} for record in feedback_records])

    if not feedback_df.empty:
        feedback_df["submitted_at"] = pd.to_datetime(
            feedback_df["submitted_at"], errors="coerce"
        )
    if not feedback_df.empty:
        feedback_df["fta_id"] = feedback_df["fta_id"].astype(str).str.strip()

    # ---------------------------------------------
    # === Set Default Date Range for Filtering ===
    # ---------------------------------------------
    min_date_str = "01/01/2025"
    min_date = datetime.strptime(min_date_str, "%m/%d/%Y").date()
    # min_date = enriched_ftas["timestamp"].min().date() if not enriched_ftas["timestamp"].isna().all() else datetime.today().date()
    max_date = datetime.today().date()
    
    # --------------------------------------------
    # === UI Filters: Date Range and Call Type ===
    # --------------------------------------------
    whitespace, startdate, enddate, calltype = st.columns([2, 1, 1, 1.5])
    with whitespace:
        # Display greeting message
        colored_word = f"<span style='color:#a00000'>{greeting}</span>"
        colored_fta = f"<span style='color:#A89410'>FTA dashboard</span>" #A89410 #FEE440
        # color = "#a00000"  # Deep red or any HEX color
        greeting_html = f"""
        <h5>Hello {username}, <br> {colored_word} and welcome to your {colored_fta} 🤗</h5>
        """
        st.markdown(greeting_html, unsafe_allow_html=True)
        # st.markdown(f"##### Hello {username}, {greeting} and welcome to your FTA dashboard 🤗")
    with startdate:
        start_date = st.date_input("Start date", 
                                   value=min_date, 
                                   min_value=min_date, 
                                   max_value=max_date
                                   )
    with enddate:
        end_date = st.date_input("End date", 
                                 value=max_date, 
                                 min_value=min_date, 
                                 max_value=max_date
                                 )
    with calltype:
        if not feedback_df.empty:
            call_type_filter = st.selectbox(
            label="Filter by Call Type",
            options=["All"] + feedback_df["call_type"].dropna().unique().tolist()
        )

    # ----------------------------------
    # === Apply Date Filter to FTAs ===
    # ----------------------------------
    filtered_ftas = enriched_ftas[
        (enriched_ftas["timestamp"].dt.date >= pd.to_datetime(start_date).date()) &
        (enriched_ftas["timestamp"].dt.date <= pd.to_datetime(end_date).date())
    ]

    # ----------------------------------------
    # === Apply Call Type Filter if Needed ===
    # ----------------------------------------
    if not feedback_df.empty:
        if call_type_filter != "All":
            feedback_df = feedback_df[feedback_df["call_type"] == call_type_filter]

    # --------------------------------
    # === Compute Contact Status ===
    # --------------------------------
    if not feedback_df.empty:
        contacted_ids = feedback_df["fta_id"].unique()
        today = datetime.now()
    
    if not feedback_df.empty:
        new_ftas = filtered_ftas[
            (~filtered_ftas["fta_id"].isin(contacted_ids)) &
            ((today - filtered_ftas["assigned_at"]).dt.days <= 2)
        ]
        not_contacted_ftas = filtered_ftas[
            (~filtered_ftas["fta_id"].isin(contacted_ids)) &
            ((today - filtered_ftas["assigned_at"]).dt.days > 2)
        ]
        contacted_ftas = filtered_ftas[filtered_ftas["fta_id"].isin(contacted_ids)]

    
    # ----------------------------------
    # === Apply Date Filter to FTAs ===
    # ----------------------------------
    filtered_user_ftas = user_ftas[
        (user_ftas["assigned_at"].dt.date >= pd.to_datetime(start_date).date()) &
        (user_ftas["assigned_at"].dt.date <= pd.to_datetime(end_date).date())
    ]
    if not feedback_df.empty:
        filtered_feedback_df = feedback_df[
            (feedback_df["submitted_at"].dt.date >= pd.to_datetime(start_date).date()) &
            (feedback_df["submitted_at"].dt.date <= pd.to_datetime(end_date).date())
        ]

    # --------------------------------
    # === Summary Metrics ===
    # --------------------------------
    no_assigned_fta = len(filtered_user_ftas)
    if feedback_df.empty:
        no_of_contacted_fta = 0
    else:
        no_of_contacted_fta = len(filtered_feedback_df["fta_id"].unique())
    no_of_not_contacted_fta = 0 if (no_assigned_fta - no_of_contacted_fta) < 0 else no_assigned_fta - no_of_contacted_fta

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
            <div class="card-icon">FTAs Assigned<span>🧑‍🤝‍🧑</span></div>
            <div class="card-value">{no_assigned_fta}</div>
        </div>
        <div class="card card-yellow">
            <div class="card-icon">Contacted<span>✔️</span></div>
            <div class="card-value">{no_of_contacted_fta}</div>
        </div>
        <div class="card card-red">
            <div class="card-icon">FTAs Not Contacted<span>📊</span></div>
            <div class="card-value">{no_of_not_contacted_fta}</div>
        </div>
    </div>
    """

    st.markdown(card_style, unsafe_allow_html=True)
    st.markdown(card_html, unsafe_allow_html=True)

    st.write("")
    st.write("")
    # --------------------------------
    # === Feedback Charts Section ===
    # --------------------------------
    st.markdown("### Feedback Analysis")

    # Define a broad palette of distinct, visually pleasant colors
    color_palette = ["#FEE440", "#8B0000", "#B0B0B0", "#321F1F", "#CD0BC9"]

    def assign_ordered_colors(data_dict, color_list):
        # Sort categories by value (descending)
        sorted_items = sorted(data_dict.items(), key=lambda x: x[1], reverse=True)
        # Assign colors in order
        return {k: color_list[i % len(color_list)] for i, (k, _) in enumerate(sorted_items)}

    if feedback_df.empty:
        st.warning("No feedback available yet!")
    else:
        calltype_data = filtered_feedback_df["call_type"].value_counts().to_dict() if "call_type" else {}
        call_success_data = filtered_feedback_df["call_success"].value_counts().to_dict()

        calltype_colors = assign_ordered_colors(calltype_data, color_palette)

        # Function to build styled donut with legend
        def styled_donut_with_legend(title, data_dict, color_dict):
            labels = list(data_dict.keys())
            values = list(data_dict.values())
            total = sum(values)

            fig = go.Figure(data=[go.Pie(
                labels=labels,
                values=values,
                hole=0.75,
                marker=dict(colors=[color_dict[label] for label in labels]),
                textinfo='none',
                sort=False
            )])

            fig.update_layout(
                margin=dict(t=30, b=20, l=0, r=0),
                title=dict(text=title, x=0.1, font=dict(size=16)),
                showlegend=False,
                height=300,
                width=300,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
            )

            # Layout: Chart on left, legend on right
            chart_col, legend_col = st.columns([2, 1])
            with chart_col:
                st.plotly_chart(fig, use_container_width=True)

            with legend_col:
                st.write(" ")
                st.write(" ")
                st.write(" ")
                st.write(" ")
                st.write(" ")
                st.write(" ")
                for label in labels:
                    val = data_dict[label]
                    percent = int((val / total) * 100)
                    color = color_dict[label]

                    st.markdown(f"""
                    <div style="margin-bottom: 10px;">
                        <div style="font-size:15px;"><strong>{label}</strong> {val} ({percent}%)</div>
                        <div style="background-color:#e0e0e0; border-radius: 10px; height: 10px; width: 100%;">
                            <div style="background-color:{color}; width:{percent}%; height:10px; border-radius:10px;"></div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

        chart_col1, chart_col2 = st.columns(2)
        if feedback_df.empty:
            show_table("Newly Assigned FTAs", new_ftas)
            st.info("No feedback records to chart yet.")
        else:
            with chart_col1:
                if calltype_data:
                    styled_donut_with_legend("Call Type", calltype_data, calltype_colors)
                else:
                    st.info("Call type data not available.")

            with chart_col2:
                if call_success_data:
                    labels = list(call_success_data.keys())
                    values = list(call_success_data.values())

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
                        title=dict(
                            text="Was the call successful?",
                            x=0.0,  # aligns title to the left (optional)
                            font=dict(size=16),
                            pad=dict(t=0, b=0)  # remove padding above/below title
                        ),
                        xaxis_title="Number of FTA",
                        yaxis_title="",
                        margin=dict(t=20, b=100, l=10, r=10)  # tighten top and bottom margin
                    )

                    st.plotly_chart(fig5, use_container_width=True)
                else:
                    st.info("Call success data not available.")

    
        # ------------------------------------
        # === Display Filtered FTA Tables ===
        # ------------------------------------
        show_table("Newly Assigned FTAs", new_ftas)
        show_table("FTAs Not Yet Contacted", not_contacted_ftas)
        show_table("Contacted FTAs", contacted_ftas)
