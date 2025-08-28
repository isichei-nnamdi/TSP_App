import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import datetime as dt
import os
from datetime import datetime
from sqlalchemy import select
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from models import Feedback


def get_first_existing_column(df, options):
    for col in options:
        if col in df.columns:
            return col
    return None

def show_dashboard_page(go_to):
    if "fta_data" not in st.session_state:
        st.error("FTA data not loaded. Please reload the application from the start.")
        st.stop()

    fta_raw_df = st.session_state.get("fta_data")
    # st.write(fta_raw_df)
    if fta_raw_df is None or fta_raw_df.empty:
        st.warning("FTA data not loaded.")
        st.stop()

    fta_raw_df.columns = fta_raw_df.columns.str.strip().str.lower()

    member_col = get_first_existing_column(
        fta_raw_df, ["membership_interest", "would you like to be a member of tsp?"])
    mg_col = get_first_existing_column(
        fta_raw_df, ["consent", "i consent that the my data provided in this form can be used by the standpoint church as deemed appropriate.", "m&g consent"])
    gender_col = get_first_existing_column(fta_raw_df, ["gender"])
    invited_by_col = get_first_existing_column(
        fta_raw_df, ["invited_by", "who invited you to tsp?"])
    timestamp_col = get_first_existing_column(fta_raw_df, ["timestamp"])

    if timestamp_col:
        fta_raw_df[timestamp_col] = pd.to_datetime(fta_raw_df[timestamp_col], errors="coerce")
        fta_raw_df["month"] = fta_raw_df[timestamp_col].dt.strftime("%b")
        monthly_counts = fta_raw_df["month"].value_counts().sort_index()
    else:
        monthly_counts = pd.Series()

    header, col_start, col_end, col_search = st.columns([3, 1, 1, 1.5])
    with header:
        st.markdown("### Welcome to the A-Team Dashboard")
    
    
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

    
    # Read with Pandas
    with engine.connect() as conn:
        all_feedback = pd.read_sql(select(Feedback), session.bind)

    # Clean up column names
    all_feedback.columns = all_feedback.columns.str.strip().str.lower()

    if not all_feedback.empty:
        # Clean up column names
        all_feedback.columns = all_feedback.columns.str.strip().str.lower()
        all_feedback["submitted_at"] = pd.to_datetime(all_feedback["submitted_at"], errors="coerce")

    min_date_str = "01/01/2025"
    min_date = datetime.strptime(min_date_str, "%m/%d/%Y").date()
    # min_date = fta_raw_df[timestamp_col].min().date() if timestamp_col else dt.date.today()
    max_date = dt.date.today()

    with col_start:
        start_date = st.date_input("Start Date", value=min_date, min_value=min_date, max_value=max_date)
    with col_end:
        end_date = st.date_input("End Date", value=max_date, min_value=min_date, max_value=max_date)
    with col_search:
        st.text_input("Search")

    if start_date > end_date:
        st.error("Start date cannot be after end date.")
        st.stop()

    if timestamp_col:
        mask = (fta_raw_df[timestamp_col].dt.date >= start_date) & (fta_raw_df[timestamp_col].dt.date <= end_date)
        df = fta_raw_df.loc[mask].copy()
    else:
        df = fta_raw_df.copy()

    total_invitees = len(df)
    member_intent = df[member_col].value_counts().to_dict() if member_col else {}

    all_feedback["submitted_at"] = pd.to_datetime(all_feedback["submitted_at"], errors="coerce")
    if all_feedback["submitted_at"].isna().all():
        st.error("All values in 'submitted_at' failed to convert to datetime.")
        st.stop()

    if "submitted_at" in all_feedback:
        mask = (all_feedback["submitted_at"].dt.date >= start_date) & (all_feedback["submitted_at"].dt.date <= end_date)
        df_feedback = all_feedback.loc[mask].copy()
    else:
        df_feedback = all_feedback.copy()

    mg_attended = "call_type"
    converted = df_feedback[df_feedback[mg_attended] == "M&G Attended"]["fta_id"].drop_duplicates().count() if mg_attended else 0
    conversion_rate = round((converted / total_invitees) * 100) if total_invitees else 0

    mg_data = df[mg_col].value_counts().to_dict() if mg_col else {}
    gender = df[gender_col].value_counts().to_dict() if gender_col else {}
    member = df[member_col].value_counts().to_dict() if member_col else {}
    invited_by = df[invited_by_col].value_counts().to_dict()

    if timestamp_col:
        df["month"] = df[timestamp_col].dt.strftime("%b")
        monthly_counts = df["month"].value_counts().sort_index()
    else:
        monthly_counts = pd.Series(dtype=int)
    
    
    st.markdown("""
        <style>
        .card-container {{ 
                display: flex; 
                justify-content: space-between; 
                gap: 20px;
                }}
                
        .card {{
                flex: 1; 
                padding: 20px; 
                border-radius: 12px; 
                color: white; 
                font-family: Arial; 
                box-shadow: 2px 2px 12px rgba(0,0,0,0.1); 
                }}
        .card-red {{ 
                background-color: #a00000; 
                }}
        .card-yellow {{ 
                background-color: #ffe640; color: black; 
                }}
        .card-icon {{ 
                display: flex; 
                justify-content: space-between; 
                align-items: center; 
                font-size: 14px; 
                font-weight: 500; 
                }}
        .card-value {{ font-size: 32px; font-weight: bold; margin-top: 5px; }}
        </style>
        <div class="card-container">
            <div class="card card-red"><div class="card-icon">No of Invitees <span>🢑</span></div><div class="card-value">{}</div></div>
            <div class="card card-yellow"><div class="card-icon">No of Converted <span>✔️</span></div><div class="card-value">{}</div></div>
            <div class="card card-red"><div class="card-icon">Conversion Rate <span>📊</span></div><div class="card-value">{}%</div></div>
        </div>
    """.format(total_invitees, converted, conversion_rate), unsafe_allow_html=True)

    st.markdown("---")

    color_palette = ["#FEE440", "#8B0000", "#B0B0B0", "#321F1F", "#CD0BC9"]

    def assign_colors(data_dict, color_list):
        sorted_items = sorted(data_dict.items(), key=lambda x: x[1], reverse=True)
        return {k: color_list[i % len(color_list)] for i, (k, _) in enumerate(sorted_items)}
    
    def donut_chart(title, data_dict, color_dict):
        labels, values = list(data_dict.keys()), list(data_dict.values())
        total = sum(values)
    
        # Donut chart
        fig = go.Figure([go.Pie(
            labels=labels,
            values=values,
            hole=0.75,
            marker=dict(colors=[color_dict[k] for k in labels]),
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
    
        # Layout with chart on left and styled legend on right
        col_chart, col_legend = st.columns([2, 1])
        with col_chart:
            st.plotly_chart(fig, use_container_width=True)
        with col_legend:
            st.write(" ")  # some spacing
            st.write(" ")
            st.write(" ")
            st.write(" ")
            st.write(" ")
            for label in labels:
                val = data_dict[label]
                pct = int((val / total) * 100)
                color = color_dict[label]
    
                st.markdown(f"""
                <div style="margin-bottom: 12px;">
                    <div style="font-size:14px; margin-bottom:2px;">
                        <strong>{label}</strong> {val} ({pct}%)
                    </div>
                    <div style="background-color:#e0e0e0; border-radius: 10px; height: 8px; width: 100%;">
                        <div style="background-color:{color}; width:{pct}%; height:8px; border-radius:10px;"></div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
    
    # Example usage in 3 columns
    donut1, donut2, donut3 = st.columns(3)
    with donut1:
        donut_chart("Like to be a Member?", member_intent, assign_colors(member_intent, color_palette))
    with donut2:
        donut_chart("Invitees by Gender", gender, assign_colors(gender, color_palette))
    with donut3:
        donut_chart("Invitees by Data Use Consent", mg_data, assign_colors(mg_data, color_palette))

    # bottom1, bottom2 = st.columns([2, 1])
    # with bottom1:
    #     if not monthly_counts.empty:
    #         fig4 = px.line(x=monthly_counts.index, y=monthly_counts.values, markers=True)
    #         fig4.update_layout(title_text="Invitees by Month", xaxis_title="Month", yaxis_title="Number of FTA")
    #         st.plotly_chart(fig4, use_container_width=True)
    #     else:
    #         st.info("Monthly invitee data not available.")
    # Ensure months are in chronological order
    month_order = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    monthly_counts = monthly_counts.reindex(month_order).dropna()
    
    bottom1, bottom2 = st.columns([2, 1])
    with bottom1:
        if not monthly_counts.empty:
            fig4 = px.line(
                x=monthly_counts.index, 
                y=monthly_counts.values, 
                markers=True
            )
            fig4.update_traces(line=dict(color='#800020'))  # Set oxblood color
            fig4.update_layout(
                title_text="Invitees by Month",
                xaxis_title="Month",
                yaxis_title="Number of FTA"
            )
            st.plotly_chart(fig4, use_container_width=True)
        else:
            st.info("Monthly invitee data not available.")

    with bottom2:
        if invited_by:
            fig5 = go.Figure(go.Bar(x=list(invited_by.values()), y=list(invited_by.keys()), orientation="h", marker_color="#8B0000", text=list(invited_by.values()), textposition='outside'))
            fig5.update_layout(title_text="Who Invited You to TSP?", xaxis_title="Number of FTA")
            st.plotly_chart(fig5, use_container_width=True)
        else:
            st.info("Invitation source data not available.")
