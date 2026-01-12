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
    # 1. INITIALIZE APP MODE
    if "app_mode" not in st.session_state:
        st.session_state.app_mode = "splash"

    # 2. ADMIN SIDEBAR (The Switcher)
    if st.session_state.get("authenticated"):
        user_email = st.session_state.get("user_email")
        admin_email = secrets_manager.get_secret("admin.email") if secrets_manager else None
        
        if user_email and admin_email and user_email == admin_email:
             st.sidebar.title("🛠️ Admin Master Switch")
             
             # Option 1: The Back Office Diagnostic Tools
             if st.sidebar.button("⚙️ Admin Console", use_container_width=True):
                 st.session_state.app_mode = "admin"
                 st.rerun()
             
             # Option 2: The Portal your Advisors see
             if st.sidebar.button("🏛️ Advisor Portal", use_container_width=True):
                 st.session_state.app_mode = "advisor"
                 st.rerun()
                 
             # Option 3: The Retail Store (Use for Sales Cannon)
             if st.sidebar.button("📮 Consumer Store", use_container_width=True):
                 st.session_state.app_mode = "store"
                 st.rerun()

    # 3. ROUTER LOGIC
    mode = st.session_state.app_mode

    # Forced Admin Mode
    if mode == "admin":
        if ui_admin: ui_admin.render_admin_page()
        return

    # Retail Store / Sales Cannon Mode
    if mode in ["store", "workspace", "review", "receipt"]:
        if ui_main: ui_main.render_main()
        return

    # Login Flow
    if mode == "login":
        if ui_login: ui_login.render_login_page()
        return

    # Default Authenticated View for Advisors
    if st.session_state.get("authenticated"):
        if ui_advisor:
            ui_advisor.render_dashboard()
        return

    # Default Public View
    if ui_splash:
        ui_splash.render_splash_page()

if __name__ == "__main__":
    main()