# FTA Welcome Flow App - The Standpoint Church

This Streamlit web app allows the A-Team to:
- Manage and follow up First-Time Attendees (FTAs)
- Auto-assign FTAs to team members
- Track contacted and uncontacted FTAs
- Use Google Sheet as the data source

## 📁 Project Structure
- `fta_login.py`: Login and registration logic
- `pages/dashboard.py`: Dashboard overview after login
- `pages/ftas.py`: My FTAs (assigned to user)
- `pages/contacted.py`: FTAs already contacted
- `db.py`: Database models and logic
- `utils/utils.py`: Shared sidebar + auth checks
- `assets/`: Church logos, images, etc.

## 💾 How to Run

```bash
pip install -r requirements.txt
streamlit run fta_login.py