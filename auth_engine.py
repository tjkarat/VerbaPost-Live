import streamlit as st
from supabase import create_client
import secrets_manager 
import re
from datetime import datetime, timedelta
import logging

# Configure Logging
logger = logging.getLogger(__name__)

# --- RESTORED: In-memory rate limiting for reset attempts ---
reset_attempts = {}

def get_client():
    try:
        url = secrets_manager.get_secret("SUPABASE_URL") or secrets_manager.get_secret("supabase.url")
        key = secrets_manager.get_secret("SUPABASE_KEY") or secrets_manager.get_secret("supabase.key")
        
        if not url or not key: 
            return None, "Missing Supabase Credentials in secrets.toml"
        
        return create_client(url, key), None
    except Exception as e:
        logger.error(f"Supabase Connection Error: {e}")
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
    except Exception as e:
        # --- FIXED: Explicit Error Logging ---
        err_msg = str(e)
        logger.error(f"Login Failed: {err_msg}")
        if "Invalid login credentials" in err_msg:
            return None, "Incorrect email or password."
        elif "Email not confirmed" in err_msg:
            return None, "Please confirm your email address."
        return None, f"Login Failed: {err_msg}"

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
                logger.error(f"Profile Error: {e}")
                # Don't fail auth just because profile sync failed
                pass 
        return res, None

    except Exception as e:
        error_msg = str(e)
        if "User already registered" in error_msg:
            # Attempt recovery login if needed, or just warn
            return None, "Account already exists. Please log in."
        return None, f"Signup Failed: {error_msg}"

def send_password_reset(email):
    client, err = get_client()
    if err: return False, err
    try:
        client.auth.reset_password_email(email)
        return True, None
    except Exception as e:
        logger.error(f"Reset Email Error: {e}")
        return False, "Error sending reset email."

# --- RESTORED: Token Verification Function ---
def reset_password_with_token(email, token, new_password):
    # Rate Limiting Logic
    now = datetime.now()
    attempts = reset_attempts.get(email, [])
    # Filter attempts in the last 15 mins
    recent_attempts = [t for t, _ in attempts if now - t < timedelta(minutes=15)]
    
    if len(recent_attempts) >= 5:
        return False, "Too many attempts. Please wait 15 minutes."
    
    # Validate Password
    valid, msg = validate_password_strength(new_password)
    if not valid: return False, msg

    client, err = get_client()
    if err: return False, err
    
    try:
        # Verify the OTP (Token)
        res = client.auth.verify_otp({"email": email, "token": token, "type": "recovery"})
        
        if res.user and res.session:
            reset_attempts.setdefault(email, []).append((now, True))
            # Set session and update password
            client.auth.set_session(res.session.access_token, res.session.refresh_token)
            client.auth.update_user({"password": new_password})
            return True, None
        else:
            reset_attempts.setdefault(email, []).append((now, False))
            return False, "Invalid or expired token."
    except Exception as e:
        reset_attempts.setdefault(email, []).append((now, False))
        logger.error(f"Reset Error: {e}")
        return False, f"Reset failed: {str(e)}"