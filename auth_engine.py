import streamlit as st
from supabase import create_client, Client
import logging

# --- CONFIGURATION ---
logger = logging.getLogger(__name__)

def _get_supabase():
    """Safely retrieves the Supabase client."""
    try:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
        return create_client(url, key)
    except Exception as e:
        logger.error(f"Supabase Config Error: {e}")
        return None

# --- AUTH FUNCTIONS CALLED BY UI_LOGIN.PY ---

def sign_in(email, password):
    """
    Logs the user in via Supabase Auth.
    Matches ui_login.py call: user, error = auth_engine.sign_in(email, password)
    """
    client = _get_supabase()
    if not client: return None, "Configuration Error"

    try:
        res = client.auth.sign_in_with_password({"email": email, "password": password})
        if res.user:
            return res.user, None
    except Exception as e:
        # Clean up error message
        msg = str(e)
        if "Invalid login credentials" in msg: return None, "Incorrect email or password."
        return None, msg
    return None, "Unknown Error"

def sign_up(email, password, data=None):
    """
    Registers a new user.
    Matches ui_login.py call: user, error = auth_engine.sign_up(email, pass, data)
    """
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
    """
    Sends the recovery email.
    Matches ui_login.py call: success, msg = auth_engine.send_password_reset(email)
    """
    client = _get_supabase()
    if not client: return False, "Config Error"

    try:
        # This sends the magic link
        client.auth.reset_password_email(email)
        return True, "Sent"
    except Exception as e:
        return False, str(e)

def update_user_password(new_password):
    """
    Updates password for the currently logged-in user (Recovery Mode).
    """
    client = _get_supabase()
    if not client: return False, "Config Error"

    try:
        client.auth.update_user({"password": new_password})
        return True, "Updated"
    except Exception as e:
        return False, str(e)

def verify_otp(email, token):
    """
    Optional: If using 6-digit codes instead of links.
    """
    client = _get_supabase()
    if not client: return None, "Config Error"
    
    try:
        res = client.auth.verify_otp({"email": email, "token": token, "type": "recovery"})
        return res.session, None
    except Exception as e:
        return None, str(e)