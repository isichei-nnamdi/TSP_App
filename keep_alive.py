import requests
import datetime
import os

# Replace this URL with your Streamlit app URL
APP_URL = "https://ateamconnect.streamlit.app/"

# Use a safe, absolute path for logging
LOG_FILE = r"C:\Users\hp\Documents\Datafied Files\TSP App\TSP_App\keep_alive_log.txt"

def ping_app():
    try:
        response = requests.get(APP_URL, timeout=10)
        if response.status_code == 200:
            log_message = f"[{datetime.datetime.now()}] App is awake! ✅"
        else:
            log_message = f"[{datetime.datetime.now()}] Warning: App returned status {response.status_code}"
    except Exception as e:
        log_message = f"[{datetime.datetime.now()}] Error pinging app: {e}"

    print(log_message)
    with open(LOG_FILE, "a", encoding="utf-8") as log:
        log.write(log_message + "\n")

if __name__ == "__main__":
    ping_app()