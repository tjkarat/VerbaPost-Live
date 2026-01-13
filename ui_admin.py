import streamlit as st
import pandas as pd
import time
import base64
import os
import requests

# --- MODULE IMPORTS ---
try: import database
except ImportError: database = None
try: import letter_format
except ImportError: letter_format = None
try: import audit_engine
except ImportError: audit_engine = None
try: import secrets_manager
except ImportError: secrets_manager = None

def check_service_health():
    """Diagnoses connection to critical B2B services."""
    health_report = []

    # 1. DATABASE CHECK
    try:
        if database and database.get_db_session():
            health_report.append(("✅", "Database (Supabase)", "Connected"))
        else:
            health_report.append(("❌", "Database", "Connection Failed"))
    except Exception as e:
        health_report.append(("❌", "Database", f"Error: {str(e)}"))

    # 2. OPENAI CHECK (Transcription)
    api_key = secrets_manager.get_secret("openai.api_key") if secrets_manager else os.environ.get("OPENAI_API_KEY")
    if api_key:
        health_report.append(("✅", "OpenAI (Intelligence)", "Key Present"))
    else:
        health_report.append(("⚠️", "OpenAI", "Key Missing (Transcription will fail)"))

    # 3. TWILIO CHECK (Voice)
    sid = secrets_manager.get_secret("twilio.account_sid") if secrets_manager else os.environ.get("TWILIO_ACCOUNT_SID")
    if sid:
        health_report.append(("✅", "Twilio (Voice)", "Key Present"))
    else:
        health_report.append(("❌", "Twilio", "Key Missing (Calls will fail)"))

    return health_report

def render_admin_page():
    st.title("⚙️ Admin Console (B2B Mode)")
    
    tab_print, tab_logs, tab_health = st.tabs(["🖨️ Manual Print Queue", "📊 System Logs", "❤️ Health"])

    # --- TAB: PRINT QUEUE (Same as before) ---
    with tab_print:
        # ... (Keep the print logic I gave you previously) ...
        st.info("Load the previous print queue code here.")

    # --- TAB: LOGS (Same as before) ---
    with tab_logs:
         # ... (Keep the log logic I gave you previously) ...
         st.info("Load the previous log code here.")

    # --- TAB: HEALTH (RESTORED) ---
    with tab_health:
        st.subheader("System Diagnostics")
        if st.button("Run Health Check"):
            with st.spinner("Pinging services..."):
                results = check_service_health()
                for status, service, msg in results:
                    st.markdown(f"**{status} {service}**: {msg}")