import streamlit as st
from gotrue.client import Client
import database

# Load Supabase Config safely
try:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    auth_client = Client(url=url, headers={"apikey": key})
except Exception as e:
    auth_client = None
    print(f"Auth init failed: {e}")

def sign_up(email, password):
    if not auth_client: return None, "System Error: Auth not configured"
    try:
        response = auth_client.sign_up(email=email, password=password)
        if response:
            # Sync with local DB
            try:
                database.create_or_get_user(email)
            except:
                pass 
        return response, None
    except Exception as e:
        return None, str(e)

def sign_in(email, password):
    if not auth_client: return None, "System Error: Auth not configured"
    try:
        response = auth_client.sign_in(email=email, password=password)
        if response:
             try:
                database.create_or_get_user(email)
             except:
                pass
        return response, None
    except Exception as e:
        return None, str(e)

def get_current_address(email):
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
    except:
        pass
    return {}
