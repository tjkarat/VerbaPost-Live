import streamlit as st
from supabase import create_client, Client
import logging
import os

# Try to import the robust secrets manager
try:
    from secrets_manager import get_secret
except ImportError:
    # Fallback if module missing
    def get_secret(key):
        return st.secrets.get(key)

# --- CONFIGURATION ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

supabase = None

def init_supabase():
    global supabase
    if supabase:
        return supabase

    # 1. Fetch Credentials safely
    # Try looking for "supabase.url" (TOML) or "SUPABASE_URL" (Env Var)
    url = get_secret("supabase.url") or get_secret("SUPABASE_URL")
    key = get_secret("supabase.key") or get_secret("SUPABASE_KEY")

    # Debugging (Masked)
    if url:
        print(f"✅ Supabase URL found: {url[:8]}...")
    else:
        print("❌ Supabase URL NOT found in secrets.")

    if key:
        print(f"✅ Supabase Key found: {key[:5]}...")
    else:
        print("❌ Supabase Key NOT found in secrets.")

    if not url or not key:
        logger.error("Supabase config missing. Check secrets.toml or Env Vars.")
        return None

    try:
        supabase = create_client(url, key)
        return supabase
    except Exception as e:
        logger.error(f"Supabase Client Init Error: {e}")
        return None

# Initialize immediately on module load
init_supabase()

# --- AUTHENTICATION FUNCTIONS ---

def verify_user(email, password):
    """
    Attempts to sign in the user.
    Returns the User object (dict) if successful, None if failed.
    """
    if not supabase:
        print("Auth Failed: Supabase client is None")
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
        print(f"Login Error Details: {e}") # Print to Cloud logs
    
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
    """
    if not supabase:
        return False, "Supabase disconnected (Check Config)"
        
    try:
        # Ensure we redirect back to the app's recovery page
        # Check general.BASE_URL or fallback
        base = "https://verbapost.streamlit.app"
        # Try fetching from secrets safely
        if get_secret("general.BASE_URL"):
            base = get_secret("general.BASE_URL")
        elif get_secret("BASE_URL"):
            base = get_secret("BASE_URL")
            
        redirect_to = f"{base}/?type=recovery"
        
        supabase.auth.reset_password_email(email, options={"redirect_to": redirect_to})
        return True, "Success"
    except Exception as e:
        logger.error(f"Reset email failed: {e}")
        return False, str(e)

def verify_otp(email, token):
    """
    Verifies the OTP (6-digit code) or token from the email link.
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

def get_current_user():
    if not supabase: return None
    try:
        session = supabase.auth.get_session()
        if session and session.user:
            return session.user
    except:
        pass
    return None