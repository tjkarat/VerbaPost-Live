import streamlit as st
from supabase import create_client
import secrets_manager 
import re
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# Simple in-memory rate limiting for reset attempts
reset_attempts = {}

def get_client():
    try:
        url = secrets_manager.get_secret("SUPABASE_URL") or secrets_manager.get_secret("supabase.url")
        key = secrets_manager.get_secret("SUPABASE_KEY") or secrets_manager.get_secret("supabase.key")
        
        if not url or not key: 
            return None, "Missing Supabase Credentials"
        
        return create_client(url, key), None
    except Exception as e:
        return None, "Database Connection Error"

def validate_password_strength(password):
    if len(password) < 8: return False, "Password must be at least 8 characters"
    if not re.search(r'[A-Z]', password): return False, "Password must contain an uppercase letter"
    if not re.search(r'[a-z]', password): return False, "Password must contain a lowercase letter"
    if not re.search(r'\d', password): return False, "Password must contain a number"
    return True, None

def sign_in(email, password):
    client, err = get_client()
    if err: return None, err
    try:
        res = client.auth.sign_in_with_password({"email": email, "password": password})
        return res, None
    except Exception:
        return None, "Login Failed. Please check your email and password."

def sign_up(email, password, name, street, street2, city, state, zip_code, country, language):
    client, err = get_client()
    if err: return None, err
    
    # Check password strength first
    valid, msg = validate_password_strength(password)
    if not valid: return None, msg
    
    profile_data_template = {
        "email": email, "full_name": name, "address_line1": street,
        "address_line2": street2, "address_city": city, "address_state": state, 
        "address_zip": zip_code, "country": country, "language_preference": language
    }

    try:
        res = client.auth.sign_up({
            "email": email, "password": password, "options": {"data": {"full_name": name}}
        })
        
        if res.user:
            try:
                profile_data_template["id"] = res.user.id
                client.table("user_profiles").upsert(profile_data_template).execute()
            except Exception as e:
                return None, f"Auth Success, but Profile Error: {e}"
        return res, None

    except Exception as e:
        error_msg = str(e)
        if "User already registered" in error_msg:
            try:
                login_res = client.auth.sign_in_with_password({"email": email, "password": password})
                if login_res.user:
                    profile_data_template["id"] = login_res.user.id
                    client.table("user_profiles").upsert(profile_data_template).execute()
                    st.toast("🔄 Account recovered and profile updated!")
                    return login_res, None 
            except Exception:
                return None, "Account exists, but password incorrect."
        return None, f"Signup Failed: {error_msg}"

def send_password_reset(email):
    client, err = get_client()
    if err: return False, err
    try:
        client.auth.reset_password_email(email)
        return True, None
    except Exception:
        return False, "Error sending reset email."

def reset_password_with_token(email, token, new_password):
    # Rate Limiting
    now = datetime.now()
    attempts = reset_attempts.get(email, [])
    recent_attempts = [t for t, _ in attempts if now - t < timedelta(minutes=15)]
    
    if len(recent_attempts) >= 5:
        return False, "Too many attempts. Please try again later."
    
    # Validate
    valid, msg = validate_password_strength(new_password)
    if not valid: return False, msg

    client, err = get_client()
    if err: return False, err
    
    try:
        res = client.auth.verify_otp({"email": email, "token": token, "type": "recovery"})
        
        if res.user and res.session:
            reset_attempts.setdefault(email, []).append((now, True))
            client.auth.set_session(res.session.access_token, res.session.refresh_token)
            client.auth.update_user({"password": new_password})
            return True, None
        else:
            reset_attempts.setdefault(email, []).append((now, False))
            return False, "Invalid or expired token."
    except Exception as e:
        reset_attempts.setdefault(email, []).append((now, False))
        logger.error(f"Reset Error: {e}")
        return False, "Password reset failed."