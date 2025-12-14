import streamlit as st
from supabase import create_client, Client
import logging

# --- CONFIGURATION ---
logger = logging.getLogger(__name__)

# Initialize Supabase Client
try:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    supabase = create_client(url, key)
except Exception as e:
    logger.error(f"Supabase Init Error: {e}")
    supabase = None

# --- AUTHENTICATION FUNCTIONS ---

def verify_user(email, password):
    """
    Attempts to sign in the user.
    """
    if not supabase: return None
    try:
        response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        if response.user:
            return {
                "id": response.user.id,
                "email": response.user.email,
                "aud": response.user.aud
            }
    except Exception as e:
        print(f"Login Error: {e}")
    return None

def create_user(email, password):
    """
    Registers a new user.
    """
    if not supabase: return None
    try:
        response = supabase.auth.sign_up({
            "email": email,
            "password": password
        })
        if response.user:
            return {"id": response.user.id, "email": response.user.email}
    except Exception as e:
        logger.error(f"Signup failed: {e}")
        raise e 
    return None

def send_password_reset(email):
    """
    Sends a password reset email (OTP) via Supabase.
    """
    if not supabase: return False, "Supabase disconnected"
    try:
        # We redirect to the recovery view, but the user will need the code
        base_url = st.secrets.get("general", {}).get("BASE_URL", "https://verbapost.streamlit.app")
        redirect_to = f"{base_url}/?type=recovery"
        
        supabase.auth.reset_password_email(email, options={"redirect_to": redirect_to})
        return True, "Success"
    except Exception as e:
        return False, str(e)

def verify_otp(email, token):
    """
    Verifies the OTP (6-digit code) or token from the email link.
    This establishes the session required to change the password.
    """
    if not supabase: return False, "System offline"
    try:
        res = supabase.auth.verify_otp({
            "email": email,
            "token": token,
            "type": "recovery"
        })
        if res.user:
            return True, "Verified"
    except Exception as e:
        return False, str(e)
    return False, "Invalid Code"

def update_user_password(new_password):
    """
    Updates the password for the currently verified session.
    """
    if not supabase: return False
    try:
        # Check if we actually have a session first
        session = supabase.auth.get_session()
        if not session:
            return False
            
        supabase.auth.update_user({"password": new_password})
        return True
    except Exception as e:
        logger.error(f"Password update failed: {e}")
        return False