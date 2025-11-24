import streamlit as st
import pandas as pd
from datetime import datetime

# --- SAFE IMPORTS (CRITICAL FIX) ---
# This prevents the app from crashing if a module is missing
try: import database
except ImportError: database = None

try: import ai_engine
except ImportError: ai_engine = None

try: import letter_format
except ImportError: letter_format = None

try: import mailer
except ImportError: mailer = None

try: import payment_engine
except ImportError: payment_engine = None

try: import analytics
except ImportError: analytics = None

def show_admin():
    st.title("🔐 Admin Console")
    
    tab1, tab2, tab3 = st.tabs(["📊 Overview", "👥 Users", "⚙️ Settings"])
    
    with tab1:
        st.subheader("System Status")
        c1, c2, c3 = st.columns(3)
        c1.metric("AI Engine", "Active" if ai_engine else "Offline")
        c2.metric("Mailer", "Active" if mailer else "Offline")
        c3.metric("Database", "Connected" if database else "Offline")
        
        if analytics:
            analytics.show_analytics()
        else:
            st.warning("Analytics module not found")

    with tab2:
        st.subheader("User Management")
        st.info("User table will appear here once database is connected.")

    with tab3:
        st.subheader("Configuration")
        st.json(st.secrets.get("public_config", {"status": "No public config"}))