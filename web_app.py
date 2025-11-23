import streamlit as st
import auth_engine 
import payment_engine
import database

# 1. INTERCEPT STRIPE RETURN
qp = st.query_params
if "session_id" in qp:
    if "current_view" not in st.session_state:
        st.session_state.current_view = "main_app"

# 2. IMPORTS
from ui_splash import show_splash
from ui_main import show_main_app
from ui_login import show_login
from ui_admin import show_admin

# 3. CONFIG
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

# 4. HANDLERS
def handle_login(email, password):
    user, error = auth_engine.sign_in(email, password)
    if error:
        st.error(f"Login Failed: {error}")
    else:
        st.success("Welcome!")
        st.session_state.user = user
        st.session_state.user_email = email
        try:
            saved = auth_engine.get_current_address(email)
            if saved:
                st.session_state["from_name"] = saved.get("name", "")
                st.session_state["from_street"] = saved.get("street", "")
                st.session_state["from_city"] = saved.get("city", "")
                st.session_state["from_state"] = saved.get("state", "")
                st.session_state["from_zip"] = saved.get("zip", "")
                st.session_state["selected_language"] = saved.get("language", "English")
        except: pass
        st.session_state.current_view = "main_app"
        st.rerun()

def handle_signup(email, password, name, street, city, state, zip_code, language):
    user, error = auth_engine.sign_up(email, password, name, street, city, state, zip_code, language)
    if error:
        st.error(f"Error: {error}")
    else:
        st.success("Created!")
        st.session_state.user = user
        st.session_state.user_email = email
        st.session_state.selected_language = language
        st.session_state.current_view = "main_app"
        st.rerun()

# 5. STATE & ROUTER
if "current_view" not in st.session_state: st.session_state.current_view = "splash" 
if "user" not in st.session_state: st.session_state.user = None

if st.session_state.current_view == "splash":
    show_splash()
elif st.session_state.current_view == "login":
    show_login(handle_login, handle_signup)
elif st.session_state.current_view == "admin":
    show_admin()
elif st.session_state.current_view == "main_app":
    with st.sidebar:
        if st.button("🏠 Home", use_container_width=True):
            st.session_state.current_view = "splash"
            st.rerun()
        
        if st.session_state.get("user"):
            st.caption(f"User: {st.session_state.user_email}")
            if st.session_state.user.user.email == "tjkarat@gmail.com": 
                if st.button("🔐 Admin Panel", type="primary"):
                    st.session_state.current_view = "admin"
                    st.rerun()
            if st.button("Log Out"):
                for key in list(st.session_state.keys()): del st.session_state[key]
                st.rerun()
                
    show_main_app()

# 6. GLOBAL FOOTER
with st.sidebar:
    st.divider()
    st.markdown("📧 **Help:** support@verbapost.com")