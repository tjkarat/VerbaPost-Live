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

def get_oauth_url(provider="google"):
    """
    Generate proper OAuth URL with redirect configuration.
    Returns the full authorization URL.
    """
    try:
        if secrets_manager:
            sb_url = secrets_manager.get_secret("supabase.url")
            base_url = secrets_manager.get_secret("base.url") or "http://localhost:8501"
        elif "supabase" in st.secrets:
            sb_url = st.secrets["supabase"]["url"]
            base_url = st.secrets.get("base_url", "http://localhost:8501")
        else:
            return None
            
        if not sb_url:
            return None
            
        # Construct OAuth URL with proper redirect
        oauth_url = f"{sb_url}/auth/v1/authorize?provider={provider}&redirect_to={base_url}?oauth_callback=true"
        logger.info(f"Generated OAuth URL: {oauth_url}")
        return oauth_url
        
    except Exception as e:
        logger.error(f"Failed to generate OAuth URL: {e}")
        return None

def verify_oauth_token(access_token):
    """
    Uses the access token from the URL hash to verify the user
    and fetch their profile from Supabase.
    Returns: (user_email, error_message)
    """
    client = get_client()
    if not client: return None, "Supabase Client Missing"

    try:
        # Set the session using the access token
        logger.info("Attempting to verify OAuth token...")
        user_response = client.auth.get_user(access_token)
        
        if user_response and user_response.user:
            logger.info(f"OAuth verification successful for: {user_response.user.email}")
            return user_response.user.email, None
        else:
            logger.error("Invalid token or user not found")
            return None, "Invalid Token or User not found"
    except Exception as e:
        logger.error(f"Token Verification Failed: {e}")
        return None, str(e)

def exchange_code_for_session(code):
    """
    Exchange authorization code for session (alternative OAuth flow).
    """
    client = get_client()
    if not client: return None, "Client Missing"
    
    try:
        logger.info("Exchanging code for session...")
        response = client.auth.exchange_code_for_session(code)
        
        if response and response.user:
            logger.info(f"Code exchange successful for: {response.user.email}")
            return response.user.email, None
        else:
            return None, "Failed to exchange code"
    except Exception as e:
        logger.error(f"Code exchange failed: {e}")
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
        client.auth.sign_out()
        logger.info("Supabase session cleared")
    except Exception as e:
        logger.warning(f"Supabase SignOut Error: {e}")