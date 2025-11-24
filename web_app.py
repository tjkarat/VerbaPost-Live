import streamlit as st
import importlib
import ui_splash
import auth_engine 
import payment_engine
import database

# 1. INTERCEPT STRIPE RETURN
qp = st.query_params
if "session_id" in qp:
    if "current_view" not in st.session_state:
        st.session_state.current_view = "main_app"

# 2. IMPORTS
import ui_main
import ui_login
import ui_admin
import ui_legal 

# 3. CONFIG (No change)
st.set_page_config(
    page_title="VerbaPost | Send Mail to Inmates, Congress & Homeowners", 
    page_icon="📮", 
    layout="centered",
    initial_sidebar_state="collapsed"
)

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

# 4. HANDLERS (No change)
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

# 5. STATE (No change)
if "current_view" not in st.session_state: st.session_state.current_view = "splash" 
if "user" not in st.session_state: st.session_state.user = None

# --- 6. ADMIN & SIDEBAR CONTROLLER (NEW BLOCK) ---

# This function is executed regardless of the current_view to handle login/admin status
def render_admin_and_logout_sidebar():
    if st.session_state.current_view == "main_app":
        if st.button("🏠 Home", use_container_width=True):
            st.session_state.current_view = "splash"
            st.rerun()
    
    if st.session_state.get("user"):
        st.caption(f"User: {st.session_state.user_email}")
        
        # ADMIN CHECK LOGIC (Consolidated and simplified)
        is_admin = False
        try:
            admin_email = st.secrets["admin"]["email"].strip().lower()
            user_email = st.session_state.user.user.email.strip().lower()
            if user_email == admin_email: 
                is_admin = True
        except: pass

        if is_admin: 
            if st.button("🔐 Admin Panel", type="primary", use_container_width=True):
                st.session_state.current_view = "admin"
                st.rerun()

        if st.button("Log Out", use_container_width=True):
            # Clear all session state keys
            for key in list(st.session_state.keys()): del st.session_state[key]
            st.rerun()
            
# --- 7. ROUTER (Updated) ---

with st.sidebar:
    # Always render the admin/logout buttons first
    render_admin_and_logout_sidebar()
    # Separator for the footer links
    st.divider()
    st.markdown("📧 **Help:** support@verbapost.com")
    if st.button("⚖️ Terms & Privacy", type="secondary", use_container_width=True):
        st.session_state.current_view = "legal"
        st.rerun()
        
# The main content router (No sidebar rendering here)
if st.session_state.current_view == "splash":
    ui_splash.show_splash()
elif st.session_state.current_view == "login":
    ui_login.show_login(handle_login, handle_signup)
elif st.session_state.current_view == "admin":
    ui_admin.show_admin()
elif st.session_state.current_view == "legal": 
    ui_legal.show_legal()
elif st.session_state.current_view == "main_app":
    # Only render the main app UI here
    ui_main.show_main_app()