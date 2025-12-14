import streamlit as st
from supabase import create_client, Client
import secrets_manager
import logging
import datetime

logger = logging.getLogger(__name__)

# Singleton Client
_supabase_client = None

def get_client() -> Client:
    global _supabase_client
    if _supabase_client:
        return _supabase_client
        
    url = secrets_manager.get_secret("SUPABASE_URL")
    key = secrets_manager.get_secret("SUPABASE_KEY")
    
    if not url or not key:
        return None
        
    try:
        _supabase_client = create_client(url, key)
        return _supabase_client
    except Exception as e:
        logger.error(f"Supabase Connection Error: {e}")
        return None

def sign_in(email, password):
    client = get_client()
    if not client: return False, "Database connection failed"

    try:
        res = client.auth.sign_in_with_password({"email": email, "password": password})
        if res.user:
            st.session_state.authenticated = True
            st.session_state.user_email = res.user.email
            st.session_state.user_id = res.user.id
            return True, None
    except Exception as e:
        msg = str(e)
        if "Invalid login credentials" in msg: return False, "Incorrect email/password"
        return False, msg
    
    return False, "Unknown error"

def sign_up(email, password, full_name, line1, line2, city, state, zip_code, country="US"):
    client = get_client()
    if not client: return False, "System offline"

    try:
        # 1. Create Auth User
        res = client.auth.sign_up({
            "email": email, 
            "password": password,
            "options": {"data": {"full_name": full_name}}
        })
        
        if not res.user:
            return False, "User creation failed"

        # 2. Create Profile (Atomic safety)
        profile_data = {
            "id": res.user.id,
            "email": email,
            "full_name": full_name,
            "return_address_street": line1,
            "return_address_street2": line2,
            "return_address_city": city,
            "return_address_state": state,
            "return_address_zip": zip_code,
            "return_address_country": country,
            "updated_at": datetime.datetime.now().isoformat()
        }
        
        # Upsert ensures we don't crash if a DB trigger already created the row
        client.table("user_profiles").upsert(profile_data).execute()
        return True, None

    except Exception as e:
        logger.error(f"Signup Error: {e}")
        return False, str(e)

def send_password_reset(email):
    client = get_client()
    if not client: return False
    try:
        base = secrets_manager.get_secret("BASE_URL") or "https://verbapost.com"
        client.auth.reset_password_for_email(email, {"redirect_to": f"{base}?type=recovery"})
        return True
    except: return False