import streamlit as st
from supabase import create_client
import logging

logger = logging.getLogger(__name__)

# Try to get secrets manager
try: import secrets_manager
except ImportError: secrets_manager = None

# Singleton Client
_supabase_client = None

def get_client():
    """
    Lazy loader for Supabase Client.
    Prioritizes secrets_manager (Env Vars) over st.secrets (TOML).
    """
    global _supabase_client
    if _supabase_client: return _supabase_client
    
    try:
        url = None
        key = None
        
        # 1. Try Secrets Manager
        if secrets_manager:
            url = secrets_manager.get_secret("supabase.url")
            key = secrets_manager.get_secret("supabase.key")
            
        # 2. Fallback to Streamlit Secrets
        if not url and "supabase" in st.secrets:
            url = st.secrets["supabase"]["url"]
        if not key and "supabase" in st.secrets:
            key = st.secrets["supabase"]["key"]
            
        if url and key:
            _supabase_client = create_client(url, key)
            return _supabase_client
        else:
            logger.error("Supabase URL or Key missing.")
            return None
    except Exception as e:
        logger.error(f"Supabase Init Error: {e}")
        return None

# --- OAUTH VERIFICATION (NEW) ---

def verify_oauth_token(access_token):
    """
    Uses the access token from the URL hash to verify the user
    and fetch their profile from Supabase.
    Returns: (user_email, error_message)
    """
    client = get_client()
    if not client: return None, "Supabase Client Missing"

    try:
        # Verify token by fetching the user object
        user_response = client.auth.get_user(access_token)
        
        if user_response and user_response.user:
            return user_response.user.email, None
        else:
            return None, "Invalid Token or User not found"
    except Exception as e:
        logger.error(f"Token Verification Failed: {e}")
        return None, str(e)

# --- STANDARD AUTH FLOWS (Existing) ---

def sign_up(email, password, data=None):
    """
    Creates a new user.
    """
    client = get_client()
    if not client: return None, "Client Missing"
    try:
        options = {"data": data} if data else {}
        res = client.auth.sign_up({"email": email, "password": password, "options": options})
        return res.user, None
    except Exception as e:
        return None, str(e)

def sign_in(email, password):
    """
    Logs in an existing user.
    """
    client = get_client()
    if not client: return None, "Client Missing"
    try:
        res = client.auth.sign_in_with_password({"email": email, "password": password})
        return res.user, None
    except Exception as e:
        return None, str(e)

def send_password_reset(email):
    """
    Sends a password reset email.
    """
    client = get_client()
    if not client: return False, "Client Missing"
    try:
        # You might need to configure the redirect_to URL in Supabase dashboard
        client.auth.reset_password_for_email(email)
        return True, None
    except Exception as e:
        return False, str(e)

def verify_otp(email, token, type="recovery"):
    """
    Verifies a One-Time Password (used for password reset flows).
    """
    client = get_client()
    if not client: return None, "Client Missing"
    try:
        res = client.auth.verify_otp({"email": email, "token": token, "type": type})
        return res.session, None
    except Exception as e:
        return None, str(e)

def update_user_password(new_password):
    """
    Updates the password for the currently authenticated user.
    """
    client = get_client()
    if not client: return False, "Client Missing"
    try:
        client.auth.update_user({"password": new_password})
        return True, None
    except Exception as e:
        return False, str(e)
def sign_out():
    """
    Clears the Supabase session active in the client.
    """
    client = get_client()
    if not client: return
    
    try:
        # This clears the local session cache in the GoTrue client
        client.auth.sign_out()
    except Exception as e:
        logger.warning(f"Supabase SignOut Error: {e}")