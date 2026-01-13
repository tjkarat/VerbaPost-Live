import streamlit as st
import sys
import os

# --- 🏷️ VERSION CONTROL ---
# Increment this constant at every functional update to this file.
VERSION = "4.5.0"  # QR Code & Routing Fixes

# --- 1. CRITICAL: CONFIG MUST BE THE FIRST COMMAND ---
st.set_page_config(
    page_title=f"VerbaPost Wealth v{VERSION}", 
    page_icon="🛡️", 
    layout="centered",
    initial_sidebar_state="collapsed" 
)

# --- 2. PATH INJECTION ---
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

import streamlit.components.v1 as components
import logging
import time
import json

# ==========================================
# 🔧 SYSTEM & LOGGING SETUP
# ==========================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# --- 3. HARDENED OAUTH BRIDGE (PKCE) ---
# ... (Keep existing OAuth Bridge / Components code here) ...

# --- 4. MODULE IMPORTS (ROBUST) ---
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
try: import ui_setup
except ImportError: ui_setup = None
try: import ui_archive
except ImportError: ui_archive = None
try: import ui_heirloom
except ImportError: ui_heirloom = None
try: import ui_legal
except ImportError: ui_legal = None
try: import ui_blog
except ImportError: ui_blog = None
try: import ui_partner
except ImportError: ui_partner = None
try: import auth_engine
except ImportError: auth_engine = None
try: import database
except ImportError: database = None
try: import secrets_manager
except ImportError: secrets_manager = None
try: import module_validator
except ImportError: module_validator = None

# ==========================================
# 🛠️ HELPER FUNCTIONS
# ==========================================

def sync_user_session():
    """Updates session state with profile data from database."""
    if st.session_state.get("authenticated") and st.session_state.get("user_email"):
        try:
            email = st.session_state.get("user_email")
            profile = database.get_user_profile(email)
            if profile:
                st.session_state.user_role = profile.get("role", "user")
                st.session_state.user_credits = profile.get("credits", 0)
                st.session_state.full_name = profile.get("full_name", "")
                st.session_state.is_partner = (st.session_state.user_role in ["partner", "admin"])
        except Exception as e:
            logger.error(f"Session Sync Failure: {e}")

def handle_logout():
    """Clears session and redirects to splash."""
    if auth_engine: auth_engine.sign_out()
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# ==========================================
# 🚀 MAIN APPLICATION ENTRY POINT (ROUTER)
# ==========================================

def main():
    # --- STEP 0: PKCE AUTH LISTENER ---
    if "code" in st.query_params:
        auth_code = st.query_params["code"]
        if not st.session_state.get("auth_processing"):
            st.session_state.auth_processing = True
            with st.spinner("Verifying Google Account..."):
                if auth_engine:
                    user, err = auth_engine.exchange_code_for_user(auth_code)
                    if user:
                        logger.info(f"✅ PKCE Success: {user.email}")
                        st.session_state.authenticated = True
                        st.session_state.user_email = user.email
                        st.session_state.app_mode = "heirloom"
                        if database:
                            try:
                                if not database.get_user_profile(user.email):
                                    database.create_user(user.email, user.email.split('@')[0])
                                sync_user_session()
                            except Exception as db_err: logger.error(f"DB Sync: {db_err}")
                        st.query_params.clear()
                        st.rerun()
                    else:
                        st.error(f"Login Failed: {err}")
                        st.session_state.auth_processing = False

    # --- STEP 1: OAUTH TOKEN INTERCEPTOR (LEGACY) ---
    query_params = st.query_params
    access_token = query_params.get("access_token")
    if access_token and not st.session_state.get("authenticated"):
        # ... (Keep existing Legacy OAuth logic) ...
        pass

    # --- STEP 2: SYSTEM HEALTH PRE-FLIGHT ---
    if module_validator and not st.session_state.get("system_verified"):
        health = module_validator.run_preflight_checks()
        if not health["status"]:
            st.error("⚠️ System configuration error.")
            st.stop()
        st.session_state.system_verified = True

    # --- STEP 3: SESSION DEFAULTS ---
    if "authenticated" not in st.session_state: st.session_state.authenticated = False
    if "user_email" not in st.session_state: st.session_state.user_email = None
    if "user_role" not in st.session_state: st.session_state.user_role = "user"
        
    # --- STEP 4: ROUTING LOGIC (UPDATED) ---
    nav = query_params.get("nav")
    project_id = query_params.get("id")
    
    # 🔥 QR CODE HANDLER (NEW) 🔥
    # Captures '?play=XYZ' from QR codes and routes to the player
    play_id = query_params.get("play")
    
    if "app_mode" not in st.session_state:
        if play_id:
            # QR Code Scanned -> Go to Public Player
            st.session_state.app_mode = "archive"
            project_id = play_id # Pass the play ID as the project ID
            
        elif nav == "archive":
            # Direct link to player (likely requires ID)
            st.session_state.app_mode = "archive"
            
        elif nav == "setup": st.session_state.app_mode = "setup"
        elif nav == "legal": st.session_state.app_mode = "legal"
        elif nav == "blog": st.session_state.app_mode = "blog"
        elif nav == "partner": st.session_state.app_mode = "partner"
        elif nav == "login": st.session_state.app_mode = "login"
        elif nav == "heirloom": st.session_state.app_mode = "heirloom" # Explicit Dashboard Link
        
        # Default Landing:
        else: st.session_state.app_mode = "splash"

    # --- STEP 5: SIDEBAR ---
    with st.sidebar:
        st.caption(f"VerbaPost Wealth v{VERSION}")
        st.divider()

    if st.session_state.get("authenticated"):
        user_email = st.session_state.get("user_email")
        admin_email = secrets_manager.get_secret("admin.email") if secrets_manager else None
        
        if user_email and admin_email and user_email == admin_email:
             with st.sidebar:
                 st.markdown("### 🛠️ Admin Master Switch")
                 if st.button("⚙️ Admin Console", use_container_width=True):
                     st.session_state.app_mode = "admin"; st.rerun()
                 if st.button("🛡️ Advisor Portal", use_container_width=True):
                     st.session_state.app_mode = "advisor"; st.rerun()
                 if st.button("🔮 Consumer Store", use_container_width=True):
                     st.session_state.app_mode = "store"; st.rerun()
                 if st.button("🤝 Partner Portal", use_container_width=True):
                     st.session_state.app_mode = "partner"; st.rerun()
                 st.sidebar.divider()

        with st.sidebar:
            if st.button("🚪 Sign Out", use_container_width=True): handle_logout()

    # --- STEP 6: RENDER VIEW ---
    mode = st.session_state.app_mode
    
    if mode == "admin" and ui_admin: ui_admin.render_admin_page()
    
    # 🔥 QR CODE VIEWER 🔥
    # Passes 'project_id' (which is the Play ID) to the archive viewer
    elif mode == "archive" and ui_archive: 
        ui_archive.render_heir_vault(project_id)
        
    elif mode == "setup" and ui_setup: ui_setup.render_parent_setup(project_id)
    elif mode == "legal" and ui_legal: ui_legal.render_legal_page()
    elif mode == "blog" and ui_blog: ui_blog.render_blog_page()
    elif mode == "partner" and ui_partner: ui_partner.render_dashboard()
    
    # 🔥 DASHBOARD (Login Protected) 🔥
    elif mode == "heirloom":
        if not st.session_state.authenticated: 
            st.session_state.app_mode = "login"
            st.rerun()
        if ui_heirloom: ui_heirloom.render_dashboard()
        
    elif mode == "login" and ui_login: ui_login.render_login_page()
    elif mode in ["store", "workspace", "review", "receipt"]:
        if ui_main: ui_main.render_main()
    elif mode == "advisor" and ui_advisor: ui_advisor.render_dashboard()
    
    elif ui_splash: ui_splash.render_splash_page()
    else:
        st.info("System Resetting...")
        st.session_state.app_mode = "splash"
        st.rerun()

if __name__ == "__main__":
    try:
        if database and st.session_state.get("authenticated"): sync_user_session()
        main()
    except Exception as e:
        logger.critical(f"FATAL SYSTEM CRASH: {e}", exc_info=True)
        st.error("A critical system error occurred.")
        if st.button("🔄 Emergency Recovery"): handle_logout()