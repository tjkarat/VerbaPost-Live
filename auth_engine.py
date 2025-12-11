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
        # CRITICAL FIX: Log the actual error instead of hiding it
        err_msg = str(e)
        logger.error(f"Login Failed: {err_msg}")
        
        if "Invalid login credentials" in err_msg:
            return None, "Incorrect email or password."
        elif "Email not confirmed" in err_msg:
            return None, "Please confirm your email address before logging in."
        else:
            return None, f"Login Failed: {err_msg}"

def sign_up(email, password, name, street, street2, city, state, zip_code, country, language):
    client, err = get_client()
    if err: return None, err
    
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
                logger.error(f"Profile Create Error: {e}")
                # Don't fail the whole signup if just profile table fails, but warn
                return res, None
        return res, None

    except Exception as e:
        error_msg = str(e)
        if "User already registered" in error_msg:
            return None, "This email is already registered. Please Log In."
        return None, f"Signup Failed: {error_msg}"

def send_password_reset(email):
    """
    Sends a password reset email via Supabase.
    Ensure your Redirect URL in Supabase Auth Settings matches your app URL.
    """
    client, err = get_client()
    if err: return False, err
    try:
        # This triggers the Supabase 'Reset Password' email template
        client.auth.reset_password_email(email)
        return True, None
    except Exception as e:
        logger.error(f"Reset Email Error: {e}")
        return False, "Could not send reset email. Please check the address."