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
    
    # 1. Prepare Profile Data Template
    # We define this dictionary once so we can use it in both the 
    # standard signup flow AND the auto-healing flow below.
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
        # 2. Try Standard Signup via Supabase Auth
        res = client.auth.sign_up({
            "email": email, 
            "password": password,
            "options": {"data": {"full_name": name}}
        })
        
        # 3. If Auth was successful, insert the Profile into the database
        if res.user:
            try:
                # Add the specific User ID returned by Supabase
                profile_data_template["id"] = res.user.id
                
                # Upsert = Update if exists, Insert if new
                client.table("user_profiles").upsert(profile_data_template).execute()
                
            except Exception as e:
                # This catches DB errors specifically (like missing columns)
                return None, f"Auth Success, but DB Error: {e}"
        
        return res, None

    except Exception as e:
        error_msg = str(e)
        
        # --- 4. AUTO-HEALING LOGIC ---
        # This fixes the "Zombie User" loop.
        # If Supabase says "User already registered", we try to log them in automatically.
        if "User already registered" in error_msg:
            print("⚠️ User exists. Attempting to repair profile...")
            try:
                # Attempt to log in with the password provided to verify ownership
                login_res = client.auth.sign_in_with_password({"email": email, "password": password})
                
                if login_res.user:
                    # Login worked! This proves they own the account.
                    # Now we FORCE the profile creation to fix the missing row.
                    profile_data_template["id"] = login_res.user.id
                    client.table("user_profiles").upsert(profile_data_template).execute()
                    
                    st.toast("🔄 Account recovered and profile updated!")
                    return login_res, None # Return success as if signup worked
            except Exception as login_e:
                # Password was wrong, so we can't auto-heal.
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