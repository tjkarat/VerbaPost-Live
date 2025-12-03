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

# --- UPDATED SIGNUP ---
def sign_up(email, password, name, street, street2, city, state, zip_code, country, language):
    client, err = get_client()
    if err: return None, err
    try:
        res = client.auth.sign_up({
            "email": email, 
            "password": password,
            "options": {"data": {"full_name": name}}
        })
        
        if res.user:
            try:
                profile_data = {
                    "id": res.user.id, 
                    "email": email, 
                    "full_name": name,
                    "address_line1": street,
                    "address_line2": street2, # <--- New Field
                    "address_city": city,
                    "address_state": state, 
                    "address_zip": zip_code,
                    "country": country,
                    "language_preference": language
                }
                client.table("user_profiles").upsert(profile_data).execute()
            except Exception as e:
                print(f"Profile Save Error: {e}")
        
        return res, None
    except Exception as e:
        return None, f"Signup Failed: {e}"

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