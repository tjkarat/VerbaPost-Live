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
try: import ui_main
except ImportError: ui_main = None
try: import ui_setup  # New: Parent Setup Portal
except ImportError: ui_setup = None
try: import ui_archive # New: Heir Archive Vault
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
    # 1. INITIALIZE NAVIGATION PARAMETERS
    # Captures ?nav=... and ?id=... from the URL for Hybrid Model entry
    query_params = st.query_params
    nav = query_params.get("nav")
    project_id = query_params.get("id")

    # 2. INITIALIZE APP MODE
    # Prioritizes direct links for Heirs and Parents before defaulting to Splash
    if "app_mode" not in st.session_state:
        if nav == "archive": 
            st.session_state.app_mode = "archive"
        elif nav == "setup": 
            st.session_state.app_mode = "setup"
        elif nav == "partner":
            st.session_state.app_mode = "login"
        else:
            st.session_state.app_mode = "splash"

    # 3. ADMIN SIDEBAR MASTER SWITCH (PRESERVED IN FULL)
    if st.session_state.get("authenticated"):
        user_email = st.session_state.get("user_email")
        admin_email = secrets_manager.get_secret("admin.email") if secrets_manager else None
        
        if user_email and admin_email and user_email == admin_email:
             st.sidebar.title("🛠️ Admin Master Switch")
             
             # Option 1: Back Office Tools
             if st.sidebar.button("⚙️ Admin Console", use_container_width=True):
                 st.session_state.app_mode = "admin"
                 st.rerun()
             
             # Option 2: Advisor Portal
             if st.sidebar.button("🏛️ Advisor Portal", use_container_width=True):
                 st.session_state.app_mode = "advisor"
                 st.rerun()
                 
             # Option 3: Retail Store / Sales Cannon
             if st.sidebar.button("📮 Consumer Store", use_container_width=True):
                 st.session_state.app_mode = "store"
                 st.rerun()

    # 4. ROUTER LOGIC (PRESERVED & ADDITIVE)
    mode = st.session_state.app_mode

    # MODE A: ADMIN CONSOLE
    if mode == "admin":
        if ui_admin: 
            ui_admin.render_admin_page()
        return

    # MODE B: HEIR ARCHIVE (HYBRID MODEL)
    if mode == "archive":
        if ui_archive: 
            ui_archive.render_heir_vault(project_id)
        else:
            st.error("Heir Archive module not found.")
        return

    # MODE C: PARENT SETUP (HYBRID MODEL)
    if mode == "setup":
        if ui_setup: 
            ui_setup.render_parent_setup(project_id)
        else:
            st.error("Parent Setup module not found.")
        return

    # MODE D: RETAIL STORE / SALES CANNON (PRESERVED)
    if mode in ["store", "workspace", "review", "receipt"]:
        if ui_main: 
            ui_main.render_main()
        return

    # MODE E: LOGIN FLOW
    if mode == "login":
        if ui_login: 
            ui_login.render_login_page()
        return

    # MODE F: AUTHENTICATED ADVISOR DASHBOARD
    if st.session_state.get("authenticated"):
        if ui_advisor:
            ui_advisor.render_dashboard()
        else:
            st.error("Advisor Dashboard module not found.")
        return

    # DEFAULT: SPLASH PAGE
    if ui_splash:
        ui_splash.render_splash_page()

if __name__ == "__main__":
    main()