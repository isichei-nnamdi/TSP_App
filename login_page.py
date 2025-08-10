import streamlit as st
from db_session import get_session
from models import User, ATeamMember
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash, check_password_hash


def authenticate_user(email, password, session):
    user = session.query(User).filter_by(email=email).first()
    if user and check_password_hash(user.password, password):
        return True
    return False


# def add_user(email, password, role, session):
#     try:
#         hashed_password = generate_password_hash(password)
#         new_user = User(email=email, password=hashed_password, role=role)
#         session.add(new_user)
#         session.commit()
#         return True
#     except IntegrityError:
#         session.rollback()
#         return False
def add_user(email, password, role, session):
    try:
        hashed_password = generate_password_hash(password)
        new_user = User(email=email, password=hashed_password, role=role)
        session.add(new_user)

        # ✅ If user is an A-Team member, add them to the a_team_members table
        if role == "A-Team":
            exists = session.query(ATeamMember).filter_by(email=email).first()
            if not exists:
                # Extract full name from email if not provided
                full_name = email.split("@")[0].replace(".", " ").title()
                session.add(ATeamMember(email=email, full_name=full_name))

        session.commit()
        return True
    except IntegrityError:
        session.rollback()
        return False


def reset_password(email, new_password, session):
    user = session.query(User).filter_by(email=email).first()
    if user:
        user.password = generate_password_hash(new_password)
        session.commit()
        return True
    return False


def get_user_role(email, session):
    user = session.query(User).filter_by(email=email).first()
    return user.role if user else None


def show_login_page(go_to):
    session = get_session()

    # Load domain & admin config from secrets
    # approved_domains = st.secrets["secrets"]["approved_domains"]
    # admin_emails = st.secrets["secrets"]["admin_emails"]

    approved_domains = ["tspchurch.com"]
    admin_emails = ["dorcas@tspchurch.com", "admin@tspchurch.com"]

    # === LAYOUT ===
    left_col, right_col = st.columns([1, 1.5])

    # === LEFT: Login Form ===
    with left_col:
        st.image("assets/tsp-logo.png", width=120)
        st.markdown("### FTA Welcome Flow")

        tab1, tab2, tab3 = st.tabs(["Login", "Register", "Forgot Password"])

        # --- LOGIN TAB ---
        with tab1:
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_pass")
            if st.button("Login"):
                if "@" not in email:
                    st.error("Invalid email format.")
                else:
                    domain = email.split("@")[-1]
                    if domain not in approved_domains:
                        st.error("Unauthorized domain. Please use an approved email address.")
                    elif authenticate_user(email, password, session):
                        st.session_state["email"] = email
                        st.session_state["role"] = get_user_role(email, session)
                        st.success("Login successful. Redirecting...")
                        go_to("dashboard")
                    else:
                        st.error("Invalid email or password.")

        # --- REGISTER TAB ---
        with tab2:
            new_email = st.text_input("New Email", key="reg_email")
            new_password = st.text_input("New Password", type="password", key="reg_pass")
            role = st.selectbox("Role", ["A-Team", "Admin"])
            if st.button("Register"):
                if "@" not in new_email:
                    st.error("Invalid email format.")
                else:
                    domain = new_email.split("@")[-1]
                    if role == "Admin" and new_email not in admin_emails:
                        st.error("This email is not authorized to register as Admin.")
                    elif domain not in approved_domains:
                        st.error("Unauthorized domain. Use an approved email address.")
                    elif add_user(new_email, new_password, role, session):
                        st.success("User registered successfully.")
                    else:
                        st.error("Email already exists.")

        # --- RESET TAB ---
        with tab3:
            reset_email = st.text_input("Email", key="reset_email")
            new_pass = st.text_input("New Password", type="password", key="reset_pass")
            if st.button("Reset Password"):
                if reset_email.strip():
                    if reset_password(reset_email, new_pass, session):
                        st.success("Password reset successfully.")
                    else:
                        st.error("Email not found.")
                else:
                    st.error("Please provide a valid email address.")

    # === RIGHT: Motivational Section ===
    with right_col:
        st.markdown(
            """
            <div style='
                background-color: #FEE440;
                height: 100vh;
                display: flex;
                justify-content: center;
                align-items: center;
                text-align: center;
                padding: 2rem;
                border-radius: 10px;'>
                <div>
                    <h2>“We are the light of the world”</h2>
                    <p style='font-size: 18px; margin-top: 1rem;'>Your role in the A-Team is making eternal impact.</p>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )