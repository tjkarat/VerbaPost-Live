import streamlit as st
from supabase import create_client

# --- HELPER: CONNECT TO DB ---
def get_client():
    try:
        if "SUPABASE_URL" in st.secrets:
            url = st.secrets["SUPABASE_URL"]
            key = st.secrets["SUPABASE_KEY"]
            return create_client(url, key), None
        elif "supabase" in st.secrets:
            url = st.secrets["supabase"]["url"]
            key = st.secrets["supabase"]["key"]
            return create_client(url, key), None
        else:
            return None, "❌ Secrets Missing"
    except Exception as e:
        return None, f"Connection Error: {e}"

# --- AUTH FUNCTIONS ---

def sign_in(email, password):
    client, err = get_client()
    if err: return None, err
    try:
        res = client.auth.sign_in_with_password({"email": email, "password": password})
        return res, None
    except Exception as e:
        return None, f"Login Failed: {e}"

def sign_up(email, password, name, street, city, state, zip_code, language):
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
                    "id": res.user.id, "email": email, "full_name": name,
                    "address_line1": street, "address_city": city,
                    "address_state": state, "address_zip": zip_code,
                    "language_preference": language
                }
                client.table("user_profiles").upsert(profile_data).execute()
            except: pass
        return res, None
    except Exception as e:
        return None, f"Signup Failed: {e}"

# --- NEW: PASSWORD RESET FUNCTIONS ---

def send_password_reset(email):
    """Sends the recovery token to the user's email"""
    client, err = get_client()
    if err: return False, err
    try:
        client.auth.reset_password_email(email)
        return True, None
    except Exception as e:
        return False, str(e)

def reset_password_with_token(email, token, new_password):
    """Verifies the token and updates the password"""
    client, err = get_client()
    if err: return False, err
    try:
        # 1. Verify the OTP (Token)
        res = client.auth.verify_otp({
            "email": email,
            "token": token,
            "type": "recovery"
        })
        
        # 2. If valid, update the password
        if res.user:
            client.auth.update_user({"password": new_password})
            return True, None
        else:
            return False, "Invalid Token"
    except Exception as e:
        return False, str(e)