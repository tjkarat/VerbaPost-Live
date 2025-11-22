import streamlit as st
import database

# Try to import library safely
try:
    from supabase import create_client, Client
    LIB_AVAILABLE = True
except ImportError:
    LIB_AVAILABLE = False

def get_supabase_client():
    """
    Connects to Supabase only when requested.
    """
    if not LIB_AVAILABLE:
        return None, "Library 'supabase' not installed."

    try:
        # Use .get() to prevent KeyErrors if secrets are missing
        supabase_secrets = st.secrets.get("supabase", None)
        
        if not supabase_secrets:
            return None, "Missing [supabase] section in Secrets."
            
        url = supabase_secrets.get("url")
        key = supabase_secrets.get("key") # Anon key for login
        
        if not url or not key:
            return None, "Missing 'url' or 'key' inside [supabase] secrets."
            
        return create_client(url, key), None
        
    except Exception as e:
        return None, f"Connection Error: {e}"

def sign_up(email, password, name, street, city, state, zip_code):
    client, err = get_supabase_client()
    if err: return None, err
    
    try:
        response = client.auth.sign_up({"email": email, "password": password})
        
        # If successful, sync with our SQL database
        if response.user:
             try:
                 database.create_or_get_user(email)
                 database.update_user_address(email, name, street, city, state, zip_code)
             except Exception as db_err:
                 print(f"DB Sync Error: {db_err}")
             return response, None
        return None, "Signup failed (No user returned)"
    except Exception as e:
        return None, str(e)

def sign_in(email, password):
    client, err = get_supabase_client()
    if err: return None, err
    
    try:
        response = client.auth.sign_in_with_password({"email": email, "password": password})
        if response.user:
            # Ensure user exists in our SQL DB
            try:
                 database.create_or_get_user(email)
            except:
                 pass
            return response, None
        return None, "Login failed"
    except Exception as e:
        return None, str(e)

def get_current_address(email):
    # Helper to get address from SQL DB
    try:
        user = database.get_user_by_email(email)
        if user:
            return {
                "name": user.address_name or "",
                "street": user.address_street or "",
                "city": user.address_city or "",
                "state": user.address_state or "",
                "zip": user.address_zip or ""
            }
    except Exception as e:
        print(f"Address Load Error: {e}")
    return {}
