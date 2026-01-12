import streamlit as st
import os
import logging

logger = logging.getLogger(__name__)

def validate_environment():
    """
    Checks if critical environment variables and modules are present.
    Returns True if healthy, False (and stops execution) if not.
    """
    # 1. Check Secrets / Env Vars
    # We only check DATABASE_URL strictly. Others (Stripe, Twilio) warn but don't crash.
    required_keys = ["DATABASE_URL"]
    missing = []
    
    # Logic to check both st.secrets and os.environ
    for key in required_keys:
        found = False
        # Check os.environ (Cloud Run)
        if os.environ.get(key):
            found = True
        # Check st.secrets (Local/Streamlit Cloud)
        elif hasattr(st, "secrets"):
            if key in st.secrets:
                found = True
            elif "general" in st.secrets and key in st.secrets["general"]:
                found = True
        
        if not found:
            missing.append(key)

    if missing:
        st.error(f"❌ CRITICAL ERROR: Missing Environment Variables: {', '.join(missing)}")
        st.info("Please update your .streamlit/secrets.toml or Cloud Run variables.")
        return False

    return True