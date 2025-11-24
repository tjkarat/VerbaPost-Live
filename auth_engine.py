import streamlit as st
from supabase import create_client

# --- HELPER: CONNECT TO DB ---
def get_client():
    """Connects to Supabase using FLAT secrets (SUPABASE_URL)"""
    try:
        # 1. Look for the FLAT keys you prefer
        if "SUPABASE_URL" in st.secrets:
            url = st.secrets["SUPABASE_URL"]
            key = st.secrets["SUPABASE_KEY"]
            return create_client(url, key), None
            
        # 2. Fallback: Look for the [nested] keys (just in case)
        elif "supabase" in st.secrets:
            url = st.secrets["supabase"]["url"]
            key = st.secrets["supabase"]["key"]
            return create_client(url, key), None
            
        else:
            return None, "❌ Secrets Missing: Please add SUPABASE_URL and SUPABASE_KEY to secrets."
            
    except Exception as e:
        return None, f"Connection Error: {e}"

# --- AUTH FUNCTIONS ---

def sign_in(email, password):
    """Log in an existing user"""
    client, err = get_client()
    if err: return None, err
    
    try:
        res = client.auth.sign_in_with_password({"email": email, "password": password})
        return res, None
    except Exception as e:
        return None, f"Login Failed: {e}"

def sign_up(email, password, name, street, city, state, zip_code, language):
    """Create a new user and save their profile"""
    client, err = get_client()
    if err: return None, err
    
    try:
        # 1. Create Auth User
        res = client.auth.sign_up({
            "email": email, 
            "password": password,
            "options": {"data": {"full_name": name}}
        })
        
        # 2. If successful, try to save the address to the database table
        if res.user:
            try:
                # We try to insert into a 'users' table if it exists
                # If this fails, we still allow the signup to proceed so they can log in
                profile_data = {
                    "id": res.user.id,
                    "email": email,
                    "full_name": name,
                    "address_line1": street,
                    "address_city": city,
                    "address_state": state,
                    "address_zip": zip_code,
                    "language_preference": language
                }
                client.table("user_profiles").upsert(profile_data).execute()
            except:
                pass # Fail silently on profile creation if table doesn't exist yet
                
        return res, None
    except Exception as e:
        return None, f"Signup Failed: {e}"

def get_current_address(email):
    """Fetch address for the logged-in user"""
    client, err = get_client()
    if err: return None
    
    try:
        res = client.table("user_profiles").select("*").eq("email", email).execute()
        if res.data and len(res.data) > 0:
            d = res.data[0]
            return {
                "name": d.get("full_name", ""),
                "street": d.get("address_line1", ""),
                "city": d.get("address_city", ""),
                "state": d.get("address_state", ""),
                "zip": d.get("address_zip", ""),
                "language": d.get("language_preference", "English")
            }
    except:
        return None
    return None