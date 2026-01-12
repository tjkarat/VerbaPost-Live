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
try: import ui_setup # NEW: Parent Portal
except ImportError: ui_setup = None
try: import ui_archive # NEW: Heir Vault
except ImportError: ui_archive = None
try: import secrets_manager
except ImportError: secrets_manager = None

# --- CONFIG ---
st.set_page_config(
    page_title="VerbaPost Wealth", 
    page_icon="🏛️", 
    layout="centered",
    initial_sidebar_state="expanded" 
)

def main():
    # 1. CAPTURE NAVIGATION PARAMS (The "Entry Points")
    # This allows links like ?nav=setup&id=123 or ?nav=archive
    query_params = st.query_params
    nav = query_params.get("nav")
    project_id = query_params.get("id")

    # 2. INITIALIZE APP MODE
    if "app_mode" not in st.session_state:
        # Priority 1: Direct Entry Points
        if nav == "setup": st.session_state.app_mode = "setup"
        elif nav == "archive": st.session_state.app_mode = "archive"
        elif nav == "partner": st.session_state.app_mode = "login"
        else: st.session_state.app_mode = "splash"

    # 3. ADMIN MASTER SWITCH (REFACTORED)
    if st.session_state.get("authenticated"):
        user_email = st.session_state.get("user_email")
        admin_email = secrets_manager.get_secret("admin.email") if secrets_manager else None
        
        # Admin-Only Sidebar Controls
        if user_email and admin_email and user_email == admin_email:
             st.sidebar.title("🛠️ Admin Master Switch")
             
             if st.sidebar.button("⚙️ Admin Console (Backend)", use_container_width=True):
                 st.session_state.app_mode = "admin"
                 st.rerun()
             
             if st.sidebar.button("🏛️ Advisor Portal (QB View)", use_container_width=True):
                 st.session_state.app_mode = "advisor"
                 st.rerun()

    # 4. ROUTER LOGIC
    mode = st.session_state.app_mode

    # MODE A: ADVISOR LOGIN & DASHBOARD
    if mode == "login":
        if ui_login: ui_login.render_login_page()
        return

    # MODE B: THE PARENT PORTAL (SECURE SETUP)
    if mode == "setup":
        if ui_setup: ui_setup.render_parent_setup(project_id)
        else: st.error("Setup module missing.")
        return

    # MODE C: THE HEIR VAULT (ARCHIVE)
    if mode == "archive":
        if ui_archive: ui_archive.render_heir_vault(project_id)
        else: st.error("Archive module missing.")
        return

    # MODE D: ADMIN CONSOLE
    if mode == "admin":
        if ui_admin: ui_admin.render_admin_page()
        return

    # MODE E: AUTHENTICATED ADVISOR VIEW
    if st.session_state.get("authenticated"):
        if ui_advisor: ui_advisor.render_dashboard()
        return

    # DEFAULT: SPLASH PAGE
    if ui_splash:
        ui_splash.render_splash_page()

if __name__ == "__main__":
    main()