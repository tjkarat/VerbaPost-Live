import streamlit as st
from ui_splash import show_splash
from ui_main import show_main_app
from ui_login import show_login
import auth_engine 
import payment_engine

st.set_page_config(page_title="VerbaPost", page_icon="📮", layout="centered")

def inject_custom_css():
    st.markdown("""
        <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        .block-container {padding-top: 1rem !important; padding-bottom: 1rem !important;}
        div.stButton > button {border-radius: 8px; font-weight: 600; border: 1px solid #e0e0e0;}
        input {border-radius: 5px !important;}
        </style>
        """, unsafe_allow_html=True)
inject_custom_css()

def handle_login(email, password):
    user, error = auth_engine.sign_in(email, password)
    if error:
        st.error(f"Login Failed: {error}")
    else:
        st.success("Welcome!")
        st.session_state.user = user
        st.session_state.user_email = email
        
        # --- MEMORY RESTORATION ---
        saved = auth_engine.get_current_address(email)
        if saved:
            # Force these into session state so inputs auto-fill
            st.session_state["from_name"] = saved.get("name", "")
            st.session_state["from_street"] = saved.get("street", "")
            st.session_state["from_city"] = saved.get("city", "")
            st.session_state["from_state"] = saved.get("state", "")
            st.session_state["from_zip"] = saved.get("zip", "")
            
        st.session_state.current_view = "main_app"
        st.rerun()

def handle_signup(email, password, name, street, city, state, zip_code):
    user, error = auth_engine.sign_up(email, password, name, street, city, state, zip_code)
    if error:
        st.error(f"Error: {error}")
    else:
        st.success("Created!")
        st.session_state.user = user
        st.session_state.user_email = email
        st.session_state.current_view = "main_app"
        st.rerun()

# --- PAYMENT ROUTER CHECK ---
# We do NOT auto-approve here anymore. We let ui_main handle it to track used IDs.

if "current_view" not in st.session_state:
    st.session_state.current_view = "splash" 
if "user" not in st.session_state:
    st.session_state.user = None

if st.session_state.current_view == "splash":
    show_splash()
elif st.session_state.current_view == "login":
    show_login(handle_login, handle_signup)
elif st.session_state.current_view == "main_app":
    with st.sidebar:
        if st.button("🏠 Home", use_container_width=True):
            st.session_state.current_view = "splash"
            st.rerun()
        if st.session_state.user:
            st.caption(f"User: {st.session_state.user_email}")
    show_main_app()