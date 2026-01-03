import os
import json
import datetime
import streamlit as st

LOG_DIR = "logs"

def _ensure_log_dir():
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)

def log_transition(action, details=None):
    """
    Logs user actions to a daily JSON log file.
    """
    _ensure_log_dir()
    
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    log_file = os.path.join(LOG_DIR, f"log_{today}.json")
    
    timestamp = datetime.datetime.now().isoformat()
    
    entry = {
        "timestamp": timestamp,
        "action": action,
        "details": details or {}
    }
    
    # Append to JSON list (inefficient for huge logs, but fine for local app)
    # If file doesn't exist, create list. If exists, load and append.
    
    current_logs = []
    if os.path.exists(log_file):
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                content = f.read()
                if content:
                    current_logs = json.loads(content)
        except Exception as e:
            print(f"Error reading log file: {e}")
            
    current_logs.append(entry)
    
    try:
        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(current_logs, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error writing log file: {e}")
