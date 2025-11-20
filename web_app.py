import streamlit as st
from splash_view import show_splash
from main_app_view import show_main_app
from login_view import show_login
import auth_engine

# --- PAGE CONFIG ---
st.set_page_config(page_title="VerbaPost", page_icon="📮", layout="centered")

# --- SESSION STATE INIT ---
if "user" not in st.session_state:
    st.session_state.user = None
if "current_view" not in st.session_state:
    st.session_state.current_view = "splash"

# --- SIDEBAR (Navigation) ---
# Only show sidebar if logged in or in app mode
if st.session_state.user:
    with st.sidebar:
        st.write(f"👤 {st.session_state.user.email}")
        if st.button("🚪 Sign Out"):
            auth_engine.sign_out()

# --- ROUTER LOGIC ---

# 1. If user is NOT logged in, they can only see Splash or Login
if not st.session_state.user:
    if st.session_state.current_view == "splash":
        show_splash()
    elif st.session_state.current_view == "login":
        show_login()
    else:
        # Redirect any other state to splash
        st.session_state.current_view = "splash"
        st.rerun()

# 2. If user IS logged in, they go straight to the Main App
else:
    show_main_app()