import streamlit as st
from login_page import show_login_page
from dashboard_page import show_dashboard_page
from fta_page import show_fta_page
from team_page import show_team_page
from fta_tracking import show_feedback_tracking_page
from db import (
    create_users_table,
    init_assignment_tables,
    sync_and_assign_fta_responses,
    get_existing_assignments,
    create_feedback_table,
    create_email_log_table,
)
# st.set_page_config(page_title="FTA Login", layout="wide", initial_sidebar_state="collapsed")
st.set_page_config(page_title="FTA Management", layout="wide")

# === CONFIG ===
GSHEET_URL = st.secrets["secrets"]["gsheet_url"]

# === Load session data once ===
if "fta_data" not in st.session_state:
    st.session_state["fta_data"] = sync_and_assign_fta_responses(GSHEET_URL)

if "fta_assignments" not in st.session_state:
    st.session_state["fta_assignments"] = get_existing_assignments()

# === Setup DB (create tables if not exist) ===
create_users_table()
create_feedback_table()
create_email_log_table()
init_assignment_tables()

# === Sync once per session ===
if "assigned_synced" not in st.session_state:
    sync_and_assign_fta_responses(GSHEET_URL)
    st.session_state["assigned_synced"] = True

# === Navigation Helper ===
def go_to(page):
    st.session_state.page = page
    st.rerun()

# === Page State ===
if "page" not in st.session_state:
    st.session_state.page = "login"

# === Sidebar Navigation (after login) ===
if "email" in st.session_state:
    st.sidebar.image("assets/tsp-logo.png", width=100)
    st.sidebar.markdown("### FTA Welcome Flow")
    st.sidebar.markdown(f"Logged in as: **{st.session_state['email']}**")

    # st.sidebar.markdown("#### 📊 Dashboard")
    if st.sidebar.button("Go to Dashboard"):
        go_to("dashboard")

    if st.session_state.get("role") == "A-Team":
        # st.sidebar.markdown("#### 🧍 FTAs")
        if st.sidebar.button("Go to FTAs"):
            go_to("fta")
        elif st.sidebar.button("FTA Tracking"):
            go_to("fta_tracking")

    if st.session_state.get("role") == "Admin":
        # st.sidebar.markdown("#### 👥 A-Team Management")
        if st.sidebar.button("Manage A-Team"):
            go_to("team")

    if st.sidebar.button("🚪 Logout"):
        st.session_state.clear()
        go_to("login")

# === Routing Logic ===
if st.session_state.page == "login":
    show_login_page(go_to)

elif st.session_state.page == "dashboard":
    if "email" not in st.session_state:
        st.warning("Please log in first.")
        go_to("login")
    else:
        show_dashboard_page(go_to)

elif st.session_state.page == "fta":
    if st.session_state.get("role") != "A-Team":
        st.error("You are not authorized to access the FTA page.")
        st.stop()
    show_fta_page(go_to)

elif st.session_state.page == "fta_tracking":
    if st.session_state.get("role") != "A-Team":
        st.error("You are not authorized to access the FTA page.")
        st.stop()
    show_feedback_tracking_page(go_to)

elif st.session_state.page == "team":
    if st.session_state.get("role") != "Admin":
        st.error("You are not authorized to access the A-Team Management page.")
        st.stop()
    show_team_page(go_to)
