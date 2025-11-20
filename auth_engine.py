import streamlit as st
from supabase import create_client, Client

# --- LOAD SECRETS SAFELY ---
try:
    # We use .get() to avoid crashing if keys are missing
    url = st.secrets.get("supabase", {}).get("url", "")
    key = st.secrets.get("supabase", {}).get("key", "")
    
    if url and key:
        supabase: Client = create_client(url, key)
        AUTH_ACTIVE = True
    else:
        supabase = None
        AUTH_ACTIVE = False
        print("⚠️ Supabase Secrets missing.")
except Exception as e:
    print(f"⚠️ Auth Init Error: {e}")
    supabase = None
    AUTH_ACTIVE = False

def sign_up(email, password):
    if not AUTH_ACTIVE: return None, "System Error: Auth not configured."
    
    try:
        response = supabase.auth.sign_up({"email": email, "password": password})
        # Check if user was created (Supabase returns a User object)
        if response.user:
             return response, None
        return None, "Signup failed"
    except Exception as e:
        return None, str(e)

def sign_in(email, password):
    if not AUTH_ACTIVE: return None, "System Error: Auth not configured."
    
    try:
        response = supabase.auth.sign_in_with_password({"email": email, "password": password})
        if response.user:
            return response, None
        return None, "Login failed"
    except Exception as e:
        return None, str(e)

def get_current_address(email):
    """
    Fetches the saved address from the SQL database (via database.py logic, not Supabase API)
    """
    import database # Import inside function to avoid circular loops
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
