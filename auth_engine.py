import streamlit as st
from supabase import create_client, Client
import logging

# --- CONFIGURATION ---
logger = logging.getLogger(__name__)

# Initialize Supabase Client
# We let this fail loudly if secrets are missing so we know why the app isn't working
url = st.secrets["supabase"]["url"]
key = st.secrets["supabase"]["key"]
supabase = create_client(url, key)

# --- AUTHENTICATION FUNCTIONS ---

def verify_user(email, password):
    """
    Attempts to sign in the user.
    Returns the User object (dict) if successful, None if failed.
    """
    if not supabase:
        return None
    
    try:
        # Supabase Python SDK v2 syntax
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
        logger.warning(f"Login failed for {email}: {e}")
        # Print to console for debugging in cloud logs
        print(f"Login Error: {e}")
    
    return None

def create_user(email, password):
    """
    Registers a new user.
    Returns the User object if successful, None if failed.
    """
    if not supabase:
        return None

    try:
        response = supabase.auth.sign_up({
            "email": email,
            "password": password
        })
        
        if response.user:
            return {
                "id": response.user.id,
                "email": response.user.email
            }
    except Exception as e:
        logger.error(f"Signup failed for {email}: {e}")
        raise e 
    
    return None

def send_password_reset(email):
    """
    Sends a password reset email via Supabase.
    Returns: (bool success, str message)
    """
    if not supabase:
        return False, "Supabase not connected"
        
    try:
        # Ensure we redirect back to the app's recovery page
        base_url = st.secrets.get("general", {}).get("BASE_URL", "https://verbapost.streamlit.app")
        redirect_to = f"{base_url}/?type=recovery"
        
        supabase.auth.reset_password_email(email, options={"redirect_to": redirect_to})
        return True, "Success"
    except Exception as e:
        logger.error(f"Reset email failed: {e}")
        return False, str(e)

def update_user_password(new_password):
    """
    Updates the password for the currently logged-in user.
    """
    if not supabase:
        return False

    try:
        supabase.auth.update_user({"password": new_password})
        return True
    except Exception as e:
        logger.error(f"Password update failed: {e}")
        return False

def get_current_user():
    """
    Checks if a valid session exists.
    """
    if not supabase:
        return None
    try:
        session = supabase.auth.get_session()
        if session and session.user:
            return session.user
    except:
        pass
    return None