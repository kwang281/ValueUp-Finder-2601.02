import json
import os
import streamlit as st
import shutil

STATE_FILE = "session_state.json"

def save_state(exclude_keys=None):
    """
    Saves current session state to JSON with atomic write.
    """
    if exclude_keys is None:
        exclude_keys = ['api_key'] 
        
    state_to_save = {}
    for key, value in st.session_state.items():
        if key not in exclude_keys:
            # Skip widget keys
            if (key.startswith("star_") or 
                key.startswith("fav_btn_") or 
                key.startswith("FormSubmitter:") or
                key == "trend_reset"):
                continue

            try:
                json.dumps(value)
                state_to_save[key] = value
            except (TypeError, OverflowError):
                pass
                
    try:
        # Atomic Write: Write to temp, then replace
        temp_file = STATE_FILE + ".tmp"
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(state_to_save, f, ensure_ascii=False, indent=2)
        
        # Windows-safe replacement
        if os.path.exists(STATE_FILE):
             try:
                 os.remove(STATE_FILE)
             except OSError:
                 # If remove fails (locked?), wait and try once more or ignore
                 pass 
        
        shutil.move(temp_file, STATE_FILE)
        
    except Exception as e:
        print(f"Error saving state: {e}")
        st.error(f"설정 저장 실패: {e}")

def load_state():
    """
    Loads session state from JSON file if it exists.
    """
    if not os.path.exists(STATE_FILE):
        return
        
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            saved_state = json.load(f)
            
        for key, value in saved_state.items():
            if key not in st.session_state:
                st.session_state[key] = value
    except Exception as e:
        print(f"Error loading state: {e}")
        if 'is_shown_error' not in st.session_state:
             st.error(f"설정 파일 로드 실패: {e}")
             st.session_state['is_shown_error'] = True
