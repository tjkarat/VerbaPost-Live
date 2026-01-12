import streamlit as st
import logging

# --- MODULE IMPORTS ---
try: import ui_splash
except ImportError: ui_splash = None
try: import ui_advisor
except ImportError: ui_advisor = None
try: import ui_login
except ImportError: ui_login = None
try: import ui_admin
except ImportError: ui_admin = None
try: import auth_listener
except ImportError: auth_listener = None
try: import module_validator
except ImportError: module_validator = None
try: import secrets_manager
except ImportError: secrets_manager = None

# --- RESTORED ANALYTICS & SEO ---
try: import seo_injector
except ImportError: seo_injector = None
try: import analytics
except ImportError: analytics = None

# --- CONFIG ---
st.set_page_config(
    page_title="VerbaPost Wealth", 
    page_icon="🏛️", 
    layout="centered",
    initial_sidebar_state="collapsed"
)
logging.basicConfig(level=logging.INFO)

# --- CSS (Minimalist B2B) ---
st.markdown("""
<style>
    [data-testid="stSidebar"] {display: none;} 
    button[kind="primary"] {background-color: #0f172a; border: none;}
    .block-container {padding-top: 2rem !important;}
</style>
""", unsafe_allow_html=True)

def main():
    # 1. HEALTH CHECK
    if module_validator and not module_validator.validate_environment():
        st.stop()

    # 2. RESTORE SEO & ANALYTICS
    if seo_injector:
        # Default to "advisor" mode for metadata
        seo_injector.inject_meta_tags(mode="advisor")
    
    if analytics:
        analytics.inject_ga()

    # 3. AUTH LISTENER
    if auth_listener:
        auth_listener.listen_for_oauth()

    # 4. ROUTING LOGIC
    if "app_mode" not in st.session_state:
        st.session_state.app_mode = "splash"

    # --- ADMIN ---
    if st.session_state.app_mode == "admin":
        if ui_admin: ui_admin.render_admin_page()
        return

    # --- LOGIN ---
    if st.session_state.app_mode == "login":
        if ui_login: ui_login.render_login_page()
        return

    # --- ADVISOR DASHBOARD ---
    if st.session_state.get("authenticated"):
        # Admin Bypass
        user_email = st.session_state.get("user_email")
        admin_email = secrets_manager.get_secret("admin.email") if secrets_manager else None
        
        if user_email and admin_email and user_email == admin_email:
             if st.sidebar.button("⚡ Admin Console"):
                 st.session_state.app_mode = "admin"
                 st.rerun()

        if ui_advisor:
            ui_advisor.render_dashboard()
        else:
            st.error("⚠️ Advisor Dashboard Module (ui_advisor.py) not found.")
        return

    # --- SPLASH ---
    if ui_splash:
        ui_splash.render_splash_page()

if __name__ == "__main__":
    main()