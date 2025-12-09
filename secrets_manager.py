import streamlit as st
import os

def get_secret(key_path):
    """
    Robust secret fetcher.
    1. Checks os.environ (Production)
    2. Checks st.secrets (QA / Local)
    3. Handles nested keys (e.g. "stripe.secret_key")
    """
    # 1. Try Environment Variable (Exact Match)
    # Convert "stripe.secret_key" -> "STRIPE_SECRET_KEY" for env var convention
    env_key = key_path.replace(".", "_").upper()
    val = os.environ.get(env_key)
    if val: return val

    # 2. Try Streamlit Secrets
    try:
        # A. Direct Lookup (e.g. [stripe] secret_key = "...")
        if "." in key_path:
            section, key = key_path.split(".", 1)
            if section in st.secrets:
                return st.secrets[section].get(key)
        
        # B. Flat Lookup (e.g. STRIPE_SECRET_KEY = "...")
        # We check both the original path and the uppercase env-style
        if key_path in st.secrets: return st.secrets[key_path]
        if env_key in st.secrets: return st.secrets[env_key]
            
    except Exception as e:
        # Fail silently in prod, but print in dev if needed
        print(f"Secret Lookup Error: {e}")
        return None
    
    return None
