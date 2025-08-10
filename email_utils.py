import streamlit as st
import smtplib
from email.message import EmailMessage

def send_email_to_fta(email, fta_name, subject, sender):
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = email
    msg.set_content(f"""
Hi {fta_name},

Thank you for submitting your form. We have received your details and our team will reach out shortly.

Best regards,  
The TSP Team
""")

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(sender, st.secrets["secrets"]["app_password"])
            smtp.send_message(msg)
    except Exception as e:
        print(f"Email failed to {email}: {e}")