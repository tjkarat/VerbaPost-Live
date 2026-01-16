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
    global _supabase_client
    if _supabase_client: return _supabase_client
    
    try:
        url = None
        key = None
        
        if secrets_manager:
            url = secrets_manager.get_secret("supabase.url")
            key = secrets_manager.get_secret("supabase.key")
            
        if not url and "supabase" in st.secrets:
            url = st.secrets["supabase"]["url"]
            key = st.secrets["supabase"]["key"]
            
        if url and key:
            _supabase_client = create_client(url, key)
            return _supabase_client
        return None
    except Exception as e:
        logger.error(f"Supabase Init Error: {e}")
        return None

def get_oauth_url(provider="google", redirect_to=None):
    """
    Generates a Google OAuth URL using PKCE flow.
    """
    client = get_client()
    if not client: return None
    
    try:
        if not redirect_to:
            if secrets_manager:
                redirect_to = secrets_manager.get_secret("base.url") or "https://app.verbapost.com"
            else:
                redirect_to = st.secrets.get("base_url", "https://app.verbapost.com")
            
        # IMPORTANT: flow_type="pkce" forces a ?code= response instead of #fragment
        data = client.auth.sign_in_with_oauth({
            "provider": provider,
            "options": {
                "redirect_to": redirect_to,
                "flow_type": "pkce" 
            }
        })
        return data.url
    except Exception as e:
        logger.error(f"Failed to generate OAuth URL: {e}")
        return None

def exchange_code_for_user(auth_code):
    """
    Exchanges the PKCE auth code for a session.
    """
    client = get_client()
    if not client: return None, "Client Missing"
    try:
        res = client.auth.exchange_code_for_session({"auth_code": auth_code})
        return res.user, None
    except Exception as e:
        logger.error(f"Auth Exchange Error: {e}")
        return None, str(e)

def verify_oauth_token(access_token):
    client = get_client()
    if not client: return None, "Supabase Client Missing"
    try:
        user_response = client.auth.get_user(access_token)
        if user_response and user_response.user:
            return user_response.user.email, None
        return None, "Invalid Token or User not found"
    except Exception as e:
        return None, str(e)

# --- 🚨 CRITICAL COMPATIBILITY BRIDGES ADDED HERE 🚨 ---

def get_google_auth_url():
    """Alias for UI compatibility."""
    return get_oauth_url(provider="google")

def handle_google_callback(code):
    """Alias for Main.py compatibility."""
    return exchange_code_for_user(code)

# --- STANDARD AUTH FLOWS ---

def sign_up(email, password, data=None):
    client = get_client()
    if not client: return None, "Client Missing"
    try:
        options = {"data": data} if data else {}
        res = client.auth.sign_up({"email": email, "password": password, "options": options})
        return res.user, None
    except Exception as e: return None, str(e)

def sign_in(email, password):
    client = get_client()
    if not client: return None, "Client Missing"
    try:
        res = client.auth.sign_in_with_password({"email": email, "password": password})
        return res.user, None
    except Exception as e: return None, str(e)

def send_password_reset(email):
    client = get_client()
    if not client: return False, "Client Missing"
    try:
        client.auth.reset_password_for_email(email)
        return True, None
    except Exception as e: return False, str(e)

def verify_otp(email, token, type="recovery"):
    client = get_client()
    if not client: return None, "Client Missing"
    try:
        res = client.auth.verify_otp({"email": email, "token": token, "type": type})
        return res.session, None
    except Exception as e: return None, str(e)

def update_user_password(new_password):
    client = get_client()
    if not client: return False, "Client Missing"
    try:
        client.auth.update_user({"password": new_password})
        return True, None
    except Exception as e: return False, str(e)

def sign_out():
    client = get_client()
    if not client: return
    try: client.auth.sign_out()
    except Exception: pass