import streamlit as st
from supabase import create_client, Client

# Initialize connection once and cache it
@st.cache_resource
def init_supabase():
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)

supabase = init_supabase()

def sign_up(email, password):
    """Creates a new user in Supabase Auth"""
    try:
        res = supabase.auth.sign_up({
            "email": email, 
            "password": password
        })
        # Auto-login after signup if confirmation is disabled
        st.session_state.user = res.user
        return True, None
    except Exception as e:
        return False, str(e)

def sign_in(email, password):
    """Logs in an existing user"""
    try:
        res = supabase.auth.sign_in_with_password({
            "email": email, 
            "password": password
        })
        st.session_state.user = res.user
        return True, None
    except Exception as e:
        return False, str(e)

def sign_out():
    """Clears session"""
    supabase.auth.sign_out()
    st.session_state.user = None
    # Clear other session data for safety
    if "audio_path" in st.session_state: del st.session_state["audio_path"]
    st.rerun()
