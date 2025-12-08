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
        return None, f"Connection Error: {e}"

def sign_in(email, password):
    client, err = get_client()
    if err: return None, err
    try:
        res = client.auth.sign_in_with_password({"email": email, "password": password})
        return res, None
    except Exception as e:
        return None, f"Login Failed: {e}"

def sign_up(email, password, name, street, street2, city, state, zip_code, country, language):
    client, err = get_client()
    if err: return None, err
    
    # 1. Prepare Profile Data
    # We define this early so we can use it in both standard flow and recovery flow
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
        # 2. Try Standard Signup
        res = client.auth.sign_up({
            "email": email, 
            "password": password,
            "options": {"data": {"full_name": name}}
        })
        
        # If successful, insert profile
        if res.user:
            try:
                profile_data_template["id"] = res.user.id
                client.table("user_profiles").upsert(profile_data_template).execute()
            except Exception as e:
                return None, f"Auth Success, but DB Error: {e}"
        
        return res, None

    except Exception as e:
        error_msg = str(e)
        
        # --- 3. AUTO-HEALING LOGIC ---
        # If user exists, try to Sign In and fix the missing profile
        if "User already registered" in error_msg:
            print("⚠️ User exists. Attempting to repair profile...")
            try:
                # Try logging in to prove ownership
                login_res = client.auth.sign_in_with_password({"email": email, "password": password})
                
                if login_res.user:
                    # Login worked! Now force-create the missing profile
                    profile_data_template["id"] = login_res.user.id
                    client.table("user_profiles").upsert(profile_data_template).execute()
                    
                    st.toast("🔄 Account recovered and profile updated!")
                    return login_res, None # Return success as if signup worked
            except Exception as login_e:
                return None, "Account exists, but password incorrect. Please log in."
        
        return None, f"Signup Failed: {error_msg}"

def send_password_reset(email):
    client, err = get_client()
    if err: return False, err
    try:
        client.auth.reset_password_email(email)
        return True, None
    except Exception as e:
        return False, str(e)

def reset_password_with_token(email, token, new_password):
    client, err = get_client()
    if err: return False, err
    try:
        res = client.auth.verify_otp({"email": email, "token": token, "type": "recovery"})
        if res.user:
            client.auth.update_user({"password": new_password})
            return True, None
        else:
            return False, "Invalid Token"
    except Exception as e:
        return False, str(e)