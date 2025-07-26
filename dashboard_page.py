import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import datetime as dt
import sqlite3
# import smtplib
# from email.mime.text import MIMEText
# from email.mime.multipart import MIMEMultipart
# from datetime import datetime
# import gspread



# def send_email_to_fta(receiver_email, fta_name):
#     sender_email = st.secrets["secrets"]["address"]
#     app_password = st.secrets["secrets"]["app_password"]
    
#     subject = "Thank you for submitting your FTA Form"
#     body = f"""
#     Dear {fta_name},

#     Thank you for completing the FTA form. We have received your submission.

#     Best regards,
#     TSP A-Team
#     """

#     # Create message
#     message = MIMEMultipart()
#     message["From"] = sender_email
#     message["To"] = receiver_email
#     message["Subject"] = subject
#     message.attach(MIMEText(body, "plain"))

#     # Send email
#     try:
#         server = smtplib.SMTP("smtp.gmail.com", 587)
#         server.starttls()
#         server.login(sender_email, app_password)
#         server.sendmail(sender_email, receiver_email, message.as_string())
#         server.quit()
#         print(f"Email sent to {receiver_email}")
#     except Exception as e:
#         print(f"Failed to send email to {receiver_email}: {e}")

# # === CONFIG ===
# GSHEET_URL = st.secrets["secrets"]["gsheet_url"]
# SENDER_EMAIL = st.secrets["secrets"]["address"]
# APP_PASSWORD = st.secrets["secrets"]["app_password"]

# # === Connect to Google Sheet ===
# @st.cache_resource
# def get_gspread_client():
#     scopes = [
#         "https://www.googleapis.com/auth/spreadsheets",
#         "https://www.googleapis.com/auth/drive",
#     ]
#     return gspread.service_account_from_dict(st.secrets["google_service_account"], scopes=scopes)

# gc = get_gspread_client()
# spreadsheet = gc.open_by_url(GSHEET_URL)

# # Get or create the 'email_logs' worksheet
# def get_or_create_log_sheet():
#     try:
#         return spreadsheet.worksheet("email_logs")
#     except gspread.exceptions.WorksheetNotFound:
#         return spreadsheet.add_worksheet(title="email_logs", rows="1000", cols="10")

# log_sheet = get_or_create_log_sheet()

# # Ensure headers exist
# if not log_sheet.get_all_values():
#     log_sheet.append_row([
#         "Timestamp", "FTA Name", "Email Address", "Subject", "Sender Email", "Status", "Error Message"
#     ])

# # === Log email activity ===
# def log_email_to_sheet(name, receiver_email, subject, sender_email, status, error_msg=None):
#     now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
#     row = [
#         now,
#         name,
#         receiver_email,
#         subject,
#         sender_email,
#         status,
#         error_msg or ""
#     ]
#     log_sheet.append_row(row, value_input_option="USER_ENTERED")

# # === Email sending function ===
# def send_email_to_fta(receiver_email, fta_name):
#     subject = f"Thank you for submitting your FTA Form"

#     message = MIMEText(f"""
#     Dear {fta_name},

#     Thank you for completing the FTA form. We have received your submission.

#     Best regards,
#     TSP A-Team
#     """)
#     message['From'] = SENDER_EMAIL
#     message['To'] = receiver_email
#     message['Subject'] = subject

#     try:
#         server = smtplib.SMTP("smtp.gmail.com", 587)
#         server.starttls()
#         server.login(SENDER_EMAIL, APP_PASSWORD)
#         server.sendmail(SENDER_EMAIL, receiver_email, message.as_string())
#         server.quit()
#         log_email_to_sheet(fta_name, receiver_email, subject, SENDER_EMAIL, "Success")
#     except Exception as e:
#         log_email_to_sheet(fta_name, receiver_email, subject, SENDER_EMAIL, "Failed", str(e))


# Utility function to safely get the first existing column
def get_first_existing_column(df, options):
    for col in options:
        if col in df.columns:
            return col
    return None

def show_dashboard_page(go_to):

    # --- Load from session_state ---
    if "fta_data" not in st.session_state:
        st.error("FTA data not loaded. Please reload the application from the start.")
        st.stop()

    fta_raw_df = st.session_state.get("fta_data")

    if fta_raw_df is None or fta_raw_df.empty:
        st.warning("FTA data not loaded.")
        st.stop()

    # === Normalize columns ===
    fta_raw_df.columns = fta_raw_df.columns.str.strip().str.lower()

    # Example column names: 'name', 'email'
    # for _, row in fta_raw_df.iterrows():
    #     fta_name = row.get("Full Name", "FTA")
    #     email = row.get("Email address")
    
    #     if email:
    #         send_email_to_fta(email, fta_name)

    # === Get column names for new or old versions ===
    member_col = get_first_existing_column(
        fta_raw_df, ["membership_interest", "would you like to be a member of tsp?"]
    )
    mg_col = get_first_existing_column(
        fta_raw_df, [
            "consent",
            "i consent that the my data provided in this form can be used by the standpoint church as deemed appropriate.",
            "m&g consent"
        ]
    )
    gender_col = get_first_existing_column(fta_raw_df, ["gender"])
    invited_by_col = get_first_existing_column(
        fta_raw_df, ["invited_by", "who invited you to tsp?"]
    )
    timestamp_col = get_first_existing_column(fta_raw_df, ["timestamp"])


    # Parse timestamp and month if column exists
    if timestamp_col:
        fta_raw_df[timestamp_col] = pd.to_datetime(fta_raw_df[timestamp_col], errors="coerce")
        fta_raw_df["month"] = fta_raw_df[timestamp_col].dt.strftime("%b")
        monthly_counts = fta_raw_df["month"].value_counts().sort_index()
    else:
        monthly_counts = pd.Series()

    # ---------- DASHBOARD FILTER UI ----------
    header, col_start, col_end, col_search = st.columns([3, 1, 1, 1.5])
    with header:
        st.markdown("### Welcome to the A-Team Dashboard")

    # ▶️ NEW / CHANGED: provide default dates bounded by data
    DB_PATH = "fta.db"
    with sqlite3.connect(DB_PATH) as conn:
        all_feedback = pd.read_sql_query("SELECT * FROM fta_feedback", conn)
    
    if not all_feedback.empty:
        all_feedback["submitted_at"] = pd.to_datetime(all_feedback["submitted_at"], errors="coerce")

    min_date = fta_raw_df[timestamp_col].min().date() if timestamp_col else dt.date.today()
    max_date = all_feedback["submitted_at"].max().date() if not all_feedback["submitted_at"].isna().all() else dt.date.today()


    with col_start:
        start_date = st.date_input("Start Date",
                                   value=min_date,
                                   min_value=min_date,
                                   max_value=max_date)

    with col_end:
        end_date = st.date_input("End Date",
                                 value=max_date,
                                 min_value=min_date,
                                 max_value=max_date)

    with col_search:
        st.text_input("Search")

    # ▶️ NEW: safely guard against inverted ranges
    if start_date > end_date:
        st.error("Start date cannot be after end date.")
        st.stop()

    # ▶️ NEW:  Filter dataframe by the chosen date range
    if timestamp_col:
        mask = (
            (fta_raw_df[timestamp_col].dt.date >= start_date) &
            (fta_raw_df[timestamp_col].dt.date <= end_date)
        )
        df = fta_raw_df.loc[mask].copy()
    else:
        df = fta_raw_df.copy()  
    
    # === Prepare Metrics ===
    total_invitees = len(df)

    if member_col:
        # converted = df[member_col].astype(str).str.lower().eq("yes").sum()
        member_intent = df[member_col].value_counts().to_dict()
    else:
        # converted = 0
        member_intent = {}


    # st.write(all_feedback)
    feedback_timestamp_col = "submitted_at"

    # Step 1: Coerce column to datetime (this handles bad formats gracefully)
    all_feedback[feedback_timestamp_col] = pd.to_datetime(
        all_feedback[feedback_timestamp_col], errors="coerce"
    )

    # Step 2: Drop or warn if all values failed conversion (optional)
    if all_feedback[feedback_timestamp_col].isna().all():
        st.error(f"All values in '{feedback_timestamp_col}' failed to convert to datetime.")
        st.stop()

    if feedback_timestamp_col:
        mask = (
            (all_feedback[feedback_timestamp_col].dt.date >= start_date) &
            (all_feedback[feedback_timestamp_col].dt.date <= end_date)
        )
        df_feedback = all_feedback.loc[mask].copy()
    else:
        df_feedback = all_feedback.copy() 

    mg_confirmation = "call_type"

    if mg_confirmation:
        converted = df_feedback[df_feedback[mg_confirmation] == "M&G Confirmation"]["fta_id"].drop_duplicates().count()
    else:
        converted = 0

    conversion_rate = round((converted / total_invitees) * 100) if total_invitees else 0

    mg_data = df[mg_col].value_counts().to_dict() if mg_col else {}
    gender = df[gender_col].value_counts().to_dict() if gender_col else {}
    member = df[member_col].value_counts().to_dict() if member_col else {}
    invited_by = df[invited_by_col].value_counts().to_dict()

    # ▶️ NEW: recompute monthly counts after filtering
    if timestamp_col:
        df["month"] = df[timestamp_col].dt.strftime("%b")
        monthly_counts = df["month"].value_counts().sort_index()
    else:
        monthly_counts = pd.Series(dtype=int)

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
            <div class="card-icon">No of Invitees <span>🧑‍🤝‍🧑</span></div>
            <div class="card-value">{total_invitees}</div>
        </div>
        <div class="card card-yellow">
            <div class="card-icon">No of Converted <span>✔️</span></div>
            <div class="card-value">{converted}</div>
        </div>
        <div class="card card-red">
            <div class="card-icon">Conversion Rate <span>📊</span></div>
            <div class="card-value">{conversion_rate}%</div>
        </div>
    </div>
    """

    st.markdown(card_style, unsafe_allow_html=True)
    st.markdown(card_html, unsafe_allow_html=True)


    st.markdown("---")

    # Define a broad palette of distinct, visually pleasant colors
    color_palette = ["#FEE440", "#8B0000", "#B0B0B0"]

    def assign_ordered_colors(data_dict, color_list):
        # Sort categories by value (descending)
        sorted_items = sorted(data_dict.items(), key=lambda x: x[1], reverse=True)
        # Assign colors in order
        return {k: color_list[i % len(color_list)] for i, (k, _) in enumerate(sorted_items)}

    mg_colors = assign_ordered_colors(mg_data, color_palette)
    gender_colors = assign_ordered_colors(gender, color_palette)
    member_colors = assign_ordered_colors(member, color_palette)

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

    # Layout
    donut1, donut2, donut3 = st.columns(3)

    with donut1:
        if member_intent:
            styled_donut_with_legend("Like to be a Member?", member_intent, member_colors)
        else:
            st.info("Membership intent data not available.")

    with donut2:
        if gender:
            styled_donut_with_legend("Invitees by Gender", gender, gender_colors)
        else:
            st.info("Gender data not available.")

    with donut3:
        if mg_data:
            styled_donut_with_legend("Invitees by Data Use Consent", mg_data, mg_colors)
        else:
            st.info("Data use Consent data not available.")

#--------------------------------------------------------------------
# BOTTOM PAGE
#--------------------------------------------------------------------
    bottom1, bottom2 = st.columns([2, 1])
    with bottom1:
        if not monthly_counts.empty:
            fig4 = px.line(x=monthly_counts.index, y=monthly_counts.values, markers=True)
            fig4.update_layout(title_text="Invitees by Month", xaxis_title="Month", yaxis_title="Number of FTA")
            st.plotly_chart(fig4, use_container_width=True)
        else:
            st.info("Monthly invitee data not available.")

    with bottom2:
        if invited_by:
            labels = list(invited_by.keys())
            values = list(invited_by.values())

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
                title_text="Who Invited You to TSP?",
                xaxis_title="Number of FTA",
                yaxis_title=""
            )

            st.plotly_chart(fig5, use_container_width=True)
        else:
            st.info("Invitation source data not available.")
