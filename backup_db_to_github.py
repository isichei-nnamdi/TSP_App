import os
import shutil
import subprocess
from datetime import datetime

# --- CONFIGURE THESE PATHS ---
# Path to your live/persistent SQLite database file
DB_SOURCE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "database", "fta.db")

# Path to your local repo (should be the root folder of your project)
REPO_PATH = os.path.dirname(os.path.abspath(__file__))

# Path to where the DB should be backed up in your repo
DB_DEST = os.path.join(REPO_PATH, "database", "fta.db")

def backup_database():
    # Step 1: Copy the database file to the repo folder
    if not os.path.exists(DB_SOURCE):
        print(f"Database file not found at {DB_SOURCE}")
        return

    shutil.copy2(DB_SOURCE, DB_DEST)
    print(f"Copied database from {DB_SOURCE} to {DB_DEST}")

    # Step 2: Commit and push changes to GitHub
    os.chdir(REPO_PATH)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        subprocess.run(["git", "add", "database/fta.db"], check=True)
        subprocess.run(["git", "commit", "-m", f"Backup DB at {timestamp}"], check=True)
        subprocess.run(["git", "push"], check=True)
        print("Database backup committed and pushed to GitHub.")
    except subprocess.CalledProcessError as e:
        print("Git command failed:", e)

if __name__ == "__main__":
    backup_database()