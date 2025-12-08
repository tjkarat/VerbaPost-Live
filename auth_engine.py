import streamlit as st
from supabase import create_client
import secrets_manager 

def get_client():
    try:
        url = secrets_manager.get_secret("SUPABASE_URL") or secrets_manager.get_secret("supabase.url")
        key = secrets_manager.get_secret("SUPABASE_KEY") or secrets_manager.get_secret("supabase.key")
        
        if not url or not key: 
            return None, "Missing Supabase Credentials"
        
        return create_client(url, key), None
    except Exception as e:
        return None, "Database Connection Error"

def sign_in(email, password):
    client, err = get_client()
    if err: return None, err
    try:
        res = client.auth.sign_in_with_password({"email": email, "password": password})
        return res, None
    except Exception:
        # Generic error to prevent user enumeration or info leakage
        return None, "Login Failed. Please check your email and password."

def sign_up(email, password, name, street, street2, city, state, zip_code, country, language):
    client, err = get_client()
    if err: return None, err
    
    # Define profile data once for reuse
    profile_data_template = {
        "email": email, 
        "full_name": name,
        "address_line1": street,
        "address_line2": street2,
        "address_city": city,
        "address_state": state, 
        "address_zip": zip_code,
        "country": country,
        "language_preference": language
    }

    try:
        # 1. Try Standard Signup
        res = client.auth.sign_up({
            "email": email, 
            "password": password,
            "options": {"data": {"full_name": name}}
        })
        
        # 2. Insert Profile if successful
        if res.user:
            try:
                profile_data_template["id"] = res.user.id
                client.table("user_profiles").upsert(profile_data_template).execute()
            except Exception as e:
                return None, f"Auth Success, but Profile Error: {e}"
        
        return res, None

    except Exception as e:
        error_msg = str(e)
        
        # --- 3. AUTO-HEALING LOGIC (Restored) ---
        # If user exists, try to log in and force-create the profile
        if "User already registered" in error_msg:
            print("⚠️ User exists. Attempting to repair profile...")
            try:
                # Verify ownership via login
                login_res = client.auth.sign_in_with_password({"email": email, "password": password})
                
                if login_res.user:
                    # Login worked! Force-create the missing profile row.
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
    client, err = get_client()
    if err: return False, err
    try:
        # Verify OTP
        res = client.auth.verify_otp({"email": email, "token": token, "type": "recovery"})
        
        # --- SECURITY FIX: Check for active session ---
        if res.user and res.session:
            # Set the session explicitly
            client.auth.set_session(res.session.access_token, res.session.refresh_token)
            
            # Now safe to update password
            client.auth.update_user({"password": new_password})
            return True, None
        else:
            return False, "Session invalid or token expired."
    except Exception as e:
        return False, str(e)