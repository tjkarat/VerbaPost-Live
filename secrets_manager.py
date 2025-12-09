import streamlit as st
import os
import logging

# Configure logging to console
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_secret(key_name):
    """
    Smart Secret Fetcher.
    1. Checks os.environ (Production/GCP).
    2. Checks st.secrets top-level (QA).
    3. Checks st.secrets nested sections (QA).
    """
    # 1. Try Environment Variable (Production Priority)
    env_val = os.environ.get(key_name)
    if env_val:
        return env_val

    # 2. Try Streamlit Secrets (QA/Local)
    try:
        # A. Direct Lookup (e.g. "STRIPE_SECRET_KEY" or "stripe.secret_key")
        if key_name in st.secrets:
            return st.secrets[key_name]
            
        # B. Smart Section Mapping (The Fix for your Error Logs)
        # If looking for "SUPABASE_URL", check [supabase] url
        if key_name == "SUPABASE_URL":
            return st.secrets["supabase"]["url"]
            
        if key_name == "SUPABASE_KEY":
            return st.secrets["supabase"]["key"]
            
        if key_name == "RESEND_API_KEY":
            return st.secrets["email"]["password"]
            
        if key_name == "GEOCODIO_API_KEY":
            return st.secrets["geocodio"]["api_key"]

        # C. Dot Notation Lookup (e.g. "stripe.secret_key")
        if "." in key_name:
            section, key = key_name.split(".", 1)
            if section in st.secrets:
                return st.secrets[section].get(key)
                
    except Exception:
        pass # Fail silently, don't crash

    # If we get here, it's truly missing. 
    # Only log strictly required keys to reduce noise.
    if key_name not in ["GA_ID"]: 
        # logger.warning(f"⚠️ Secret '{key_name}' not found.")
        pass
        
    return None