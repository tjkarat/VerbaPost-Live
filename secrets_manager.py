import streamlit as st
import os

def get_secret(key_path):
    """
    1. Checks Environment Variables (GCP Priority) - Prevents crashing if secrets.toml is missing.
    2. Checks Streamlit secrets (Local Fallback) - Only runs if Env Var is missing.
    """
    
    # --- PRIORITY 1: ENVIRONMENT VARIABLES (GCP) ---
    # Convert "stripe.secret_key" -> "STRIPE_SECRET_KEY"
    env_key = key_path.replace(".", "_").upper()
    value = os.environ.get(env_key)
    
    if value:
        return value

    # --- PRIORITY 2: STREAMLIT SECRETS (LOCAL) ---
    # We wrap this in a try/except because simply accessing st.secrets 
    # when the file is missing causes a hard crash on some Streamlit versions.
    try:
        # Check Exact Match
        if key_path in st.secrets:
            return st.secrets[key_path]
            
        # Check Nested Match (e.g. "stripe.secret_key")
        if "." in key_path:
            section, key = key_path.split(".")
            if section in st.secrets:
                return st.secrets[section].get(key)
    except FileNotFoundError:
        return None
    except Exception:
        return None
        
    return None