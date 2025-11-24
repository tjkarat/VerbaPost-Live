# auth_ui.py
import streamlit as st
import ui_main
from supabase import create_client

# --- HELPER: INIT SUPABASE (Local Copy for this module) ---
@st.cache_resource
def get_supabase_client():
    try:
        if "SUPABASE_URL" not in st.secrets: return None
        return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except: return None

# --- AUTH FLOW FUNCTIONS ---

def render_login_page():
    # Calling hero from ui_main is clean
    ui_main.render_hero("Welcome Back", "Log in to continue.")
    
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        with st.container(border=True):
            email = st.text_input("Email Address")
            password = st.text_input("Password", type="password")
            
            if st.button("Log In", type="primary", use_container_width=True):
                sb = get_supabase_client()
                try:
                    res = sb.auth.sign_in_with_password({"email": email, "password": password})
                    st.session_state.user = res
                    st.session_state.user_email = email 
                    ui_main.reset_app()
                    st.session_state.app_mode = "store"
                    st.rerun()
                except Exception as e: st.error(f"Login failed: {e}")
            
            if st.button("Sign Up", use_container_width=True):
                sb = get_supabase_client()
                try:
                    sb.auth.sign_up({"email": email, "password": password})
                    st.success("Account created! Check email.")
                except Exception as e: st.error(f"Signup failed: {e}")
            
            if st.button("Forgot Password?", type="secondary", use_container_width=True):
                st.session_state.app_mode = "forgot_password"
                st.rerun()
                
    c_back1, c_back2, c_back3 = st.columns([1, 1, 1])
    with c_back2:
        if st.button("← Back to Home", use_container_width=True):
            st.session_state.app_mode = "splash"
            st.rerun()

def render_forgot_password_page():
    ui_main.render_hero("Recover Account", "Let's get you back in.")
    # (Rest of Forgot Password logic would go here)
    st.write("Forgot Password Logic...")


# --- FINAL ENTRY POINT ---
def route_auth_page(app_mode):
    if app_mode == "login":
        render_login_page()
    elif app_mode == "forgot_password":
        render_forgot_password_page()
    elif app_mode == "verify_reset":
        # (Render verify reset code page)
        st.write("Verify Reset Code Logic...")
    else:
        st.error("Unknown Auth Route.")
