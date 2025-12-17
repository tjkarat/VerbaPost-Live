import streamlit as st
from supabase import create_client, Client
import logging
import os

# --- CONFIGURATION ---
logger = logging.getLogger(__name__)

def _get_supabase():
    """
    Safely retrieves the Supabase client.
    Prioritizes Environment Variables (Production), falls back to Secrets (QA).
    """
    try:
        # 1. Try Environment Variables (GCP Production)
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")

        # 2. Fallback to Streamlit Secrets (QA / Local)
        if not url and hasattr(st, "secrets") and "supabase" in st.secrets:
            url = st.secrets["supabase"]["url"]
        
        if not key and hasattr(st, "secrets") and "supabase" in st.secrets:
            key = st.secrets["supabase"]["key"]

        if not url or not key:
            logger.error("Supabase credentials missing from both Env Vars and Secrets.")
            return None

        return create_client(url, key)
    except Exception as e:
        logger.error(f"Supabase Config Error: {e}")
        return None

# --- AUTH FUNCTIONS ---

def sign_in(email, password):
    client = _get_supabase()
    if not client: return None, "Configuration Error: API Keys Missing"

    try:
        res = client.auth.sign_in_with_password({"email": email, "password": password})
        if res.user:
            return res.user, None
    except Exception as e:
        msg = str(e)
        if "Invalid login credentials" in msg: return None, "Incorrect email or password."
        return None, msg
    return None, "Unknown Error"

def sign_up(email, password, data=None):
    client = _get_supabase()
    if not client: return None, "Configuration Error"

    try:
        options = {"data": data} if data else {}
        res = client.auth.sign_up({"email": email, "password": password, "options": options})
        if res.user:
            return res.user, None
    except Exception as e:
        return None, str(e)
    return None, "Signup Failed"

def send_password_reset(email):
    client = _get_supabase()
    if not client: return False, "Configuration Error"

    try:
        client.auth.reset_password_email(email)
        return True, "Sent"
    except Exception as e:
        return False, str(e)

def update_user_password(new_password):
    client = _get_supabase()
    if not client: return False, "Configuration Error"

    try:
        client.auth.update_user({"password": new_password})
        return True, "Updated"
    except Exception as e:
        return False, str(e)

def verify_otp(email, token):
    client = _get_supabase()
    if not client: return None, "Configuration Error"
    
    try:
        res = client.auth.verify_otp({"email": email, "token": token, "type": "recovery"})
        return res.session, None
    except Exception as e:
        return None, str(e)