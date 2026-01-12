import streamlit as st
import logging

# --- MODULE IMPORTS ---
try: import ui_splash
except ImportError: ui_splash = None
try: import ui_advisor   # <--- THE NEW DASHBOARD
except ImportError: ui_advisor = None
try: import ui_login     # <--- PRESERVED AUTH
except ImportError: ui_login = None
try: import ui_admin     # <--- PRESERVED ADMIN
except ImportError: ui_admin = None
try: import auth_listener
except ImportError: auth_listener = None
try: import module_validator
except ImportError: module_validator = None
try: import secrets_manager
except ImportError: secrets_manager = None

# --- CONFIG ---
st.set_page_config(
    page_title="VerbaPost Wealth", 
    page_icon="🏛️", 
    layout="centered",
    initial_sidebar_state="collapsed"
)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VerbaPost_Router")

# --- CSS (Minimalist B2B) ---
st.markdown("""
<style>
    [data-testid="stSidebar"] {display: none;} /* Hide Sidebar */
    button[kind="primary"] {background-color: #0f172a; border: none;}
    .block-container {padding-top: 2rem !important;}
</style>
""", unsafe_allow_html=True)

def main():
    # 1. HEALTH CHECK
    if module_validator and not module_validator.validate_environment():
        st.stop()

    # 2. AUTH LISTENER
    if auth_listener:
        auth_listener.listen_for_oauth()

    # 3. ROUTING LOGIC
    # Initialize State
    if "app_mode" not in st.session_state:
        st.session_state.app_mode = "splash"

    # --- ADMIN OVERRIDE ---
    if st.session_state.app_mode == "admin":
        if ui_admin: ui_admin.render_admin_page()
        return

    # --- LOGIN SCREEN ---
    if st.session_state.app_mode == "login":
        if ui_login: ui_login.render_login_page()
        return

    # --- AUTHENTICATED USER ---
    if st.session_state.get("authenticated"):
        
        # Check for Admin Access via Email
        user_email = st.session_state.get("user_email")
        admin_email = None
        if secrets_manager: admin_email = secrets_manager.get_secret("admin.email")
        
        # Render Admin Button ONLY for you
        if user_email and admin_email and user_email == admin_email:
             if st.sidebar.button("⚡ Admin Console"):
                 st.session_state.app_mode = "admin"
                 st.rerun()

        # Render Advisor Dashboard (The New B2B App)
        if ui_advisor:
            ui_advisor.render_dashboard()
        else:
            st.error("⚠️ Advisor Dashboard Module (ui_advisor.py) not found.")
        return

    # --- PUBLIC VISITOR ---
    if ui_splash:
        ui_splash.render_splash_page()

if __name__ == "__main__":
    main()