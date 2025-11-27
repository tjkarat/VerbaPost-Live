import streamlit as st
import os

def get_secret(key_path):
    """
    1. Checks Streamlit secrets (Exact Match) -> Good for 'SUPABASE_URL'
    2. Checks Streamlit secrets (Nested Match) -> Good for 'stripe.secret_key'
    3. Checks Environment Variables (Flattened) -> Good for GCP
    """
    # A. Streamlit: Try Exact Match (e.g. "SUPABASE_URL")
    try:
        if key_path in st.secrets:
            return st.secrets[key_path]
    except:
        pass

    # B. Streamlit: Try Nested Match (e.g. "stripe.secret_key")
    try:
        if "." in key_path:
            section, key = key_path.split(".")
            if section in st.secrets:
                return st.secrets[section].get(key)
    except:
        pass

    # C. GCP: Try Environment Variable (e.g. "STRIPE_SECRET_KEY")
    # We replace dots with underscores and uppercase everything
    env_key = key_path.replace(".", "_").upper()
    return os.environ.get(env_key)
