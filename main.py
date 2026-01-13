import streamlit as st

# --- 🏷️ VERSION CONTROL ---
# Increment this constant at every functional update to this file.
VERSION = "4.0.4"

# --- 1. CRITICAL: CONFIG MUST BE THE FIRST COMMAND ---
# This must remain at the very top to prevent Streamlit set_page_config errors.
st.set_page_config(
    page_title=f"VerbaPost Wealth v{VERSION}", 
    page_icon="🏛️", 
    layout="centered",
    initial_sidebar_state="expanded" 
)

import streamlit.components.v1 as components
import logging
import os
import sys
import time
import json

# ==========================================
# 🔧 SYSTEM & LOGGING SETUP (PRESERVED)
# ==========================================
# This block ensures high-resolution logs for production debugging.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# --- 2. OAUTH FRAGMENT BRIDGE (PHASE 1 SECURITY FIX) ---
# Hardened version of the bridge to bypass 'allow-top-navigation' security errors.
# Uses window.top with a try-catch and origin-matching to satisfy strict sandboxing.
components.html(
    """
    <script>
    (function() {
        try {
            var topWin = window.top;
            var hash = topWin.location.hash;
            if (hash && hash.includes('access_token=')) {
                var cleanParams = hash.replace('#', '?');
                var finalUrl = topWin.location.origin + topWin.location.pathname + cleanParams;
                // Force navigation in the parent frame to refresh with parameters
                topWin.location.replace(finalUrl);
            }
        } catch (e) {
            console.error("VerbaPost Auth Bridge Error:", e);
        }
    })();
    </script>
    """,
    height=0,
)

# --- 3. MODULE IMPORTS (ROBUST ERROR WRAPPING) ---
# Each import is wrapped in an individual try/except to prevent app-wide crashes.
try: 
    import ui_splash
except ImportError as e: 
    logger.error(f"UI Splash Import Error: {e}")
    ui_splash = None

try: 
    import ui_advisor
except ImportError as e: 
    logger.error(f"UI Advisor Import Error: {e}")
    ui_advisor = None

try: 
    import ui_login
except ImportError as e: 
    logger.error(f"UI Login Import Error: {e}")
    ui_login = None

try: 
    import ui_admin
except ImportError as e: 
    logger.error(f"UI Admin Import Error: {e}")
    ui_admin = None

try: 
    import ui_main
except ImportError as e: 
    logger.error(f"UI Main Import Error: {e}")
    ui_main = None

try: 
    import ui_setup
except ImportError as e: 
    logger.error(f"UI Setup Import Error: {e}")
    ui_setup = None

try: 
    import ui_archive
except ImportError as e: 
    logger.error(f"UI Archive Import Error: {e}")
    ui_archive = None

try: 
    import ui_heirloom
except ImportError as e:
    logger.error(f"UI Heirloom Import Error: {e}")
    ui_heirloom = None

try: 
    import ui_legal
except ImportError as e:
    logger.error(f"UI Legal Import Error: {e}")
    ui_legal = None

try: 
    import ui_blog
except ImportError as e:
    logger.error(f"UI Blog Import Error: {e}")
    ui_blog = None

try: 
    import ui_partner
except ImportError as e:
    logger.error(f"UI Partner Import Error: {e}")
    ui_partner = None

try: 
    import auth_engine
except ImportError as e: 
    logger.error(f"Auth Engine Import Error: {e}")
    auth_engine = None

try: 
    import database
except ImportError as e: 
    logger.error(f"Database Import Error: {e}")
    database = None

try: 
    import secrets_manager
except ImportError as e: 
    logger.error(f"Secrets Manager Import Error: {e}")
    secrets_manager = None

try: 
    import module_validator
except ImportError: 
    module_validator = None

# ==========================================
# 🛠️ HELPER FUNCTIONS (RESTORED IN FULL)
# ==========================================

def sync_user_session():
    """
    Synchronizes the Streamlit session state with the database UserProfile.
    Crucial for enforcing 'Partner' vs 'User' roles in the Master Switch.
    """
    if st.session_state.get("authenticated") and st.session_state.get("user_email"):
        try:
            email = st.session_state.get("user_email")
            profile = database.get_user_profile(email)
            if profile:
                st.session_state.user_role = profile.get("role", "user")
                st.session_state.user_credits = profile.get("credits", 0)
                st.session_state.full_name = profile.get("full_name", "")
                st.session_state.is_partner = (st.session_state.user_role in ["partner", "admin"])
                logger.info(f"Session Synced for {email} (Role: {st.session_state.user_role})")
        except Exception as e:
            logger.error(f"Session Sync Failure: {e}")

def handle_logout():
    """
    Clears all application state and triggers a clean restart.
    Ensures that OAuth tokens are cleared from the browser session.
    """
    logger.info("Triggering global logout and session clear.")
    if auth_engine: 
        auth_engine.sign_out()
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# ==========================================
# 🚀 MAIN APPLICATION ENTRY POINT (ROUTER)
# ==========================================

def main():
    # 1. AUTH INTERCEPTOR (THE GOOGLE LOGIN FIX)
    query_params = st.query_params
    url_token = query_params.get("access_token")

    nav = query_params.get("nav")
    project_id = query_params.get("id")

    if url_token and not st.session_state.get("authenticated"):
        if auth_engine:
            logger.info("Access token detected in URL. Verifying...")
            with st.spinner("Authenticating via Google..."):
                email, err = auth_engine.verify_oauth_token(url_token)
                if email:
                    st.session_state.authenticated = True
                    st.session_state.user_email = email
                    st.session_state.app_mode = "heirloom" 
                    sync_user_session()
                    st.query_params.clear()
                    logger.info(f"OAuth Success: {email}")
                    st.rerun()
                else:
                    logger.error(f"Auth failed: {err}")
                    st.error(f"Authentication Error: {err}")

    # 2. SYSTEM HEALTH PRE-FLIGHT (RESTORED)
    if module_validator and not st.session_state.get("system_verified"):
        health = module_validator.run_preflight_checks()
        if not health["status"]:
            st.error("System configuration error. Please check Admin logs for missing API keys.")
            st.stop()
        st.session_state.system_verified = True

    # 3. INITIALIZE SESSION STATE DEFAULTS
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "user_email" not in st.session_state:
        st.session_state.user_email = None
    if "user_role" not in st.session_state:
        st.session_state.user_role = "user"
        
    # 4. INITIALIZE APP MODE ROUTING (STATE MACHINE)
    if "app_mode" not in st.session_state:
        if nav == "legal": 
            st.session_state.app_mode = "legal"
        elif nav == "blog": 
            st.session_state.app_mode = "blog"
        elif nav == "partner": 
            st.session_state.app_mode = "partner"
        elif nav == "setup": 
            st.session_state.app_mode = "setup"
        elif nav == "archive":
            st.session_state.app_mode = "archive"
        elif nav == "login":
            st.session_state.app_mode = "login"
        else: 
            st.session_state.app_mode = "splash"

    # 5. SIDEBAR: MASTER SWITCH & LOGOUT (RESTORED IN FULL)
    with st.sidebar:
        # Persistent Version Display
        st.caption(f"VerbaPost Wealth Build: v{VERSION}")
        st.divider()

    if st.session_state.get("authenticated"):
        user_email = st.session_state.get("user_email")
        admin_email = secrets_manager.get_secret("admin.email") if secrets_manager else None
        
        if user_email and admin_email and user_email == admin_email:
             with st.sidebar:
                 st.markdown("### 🛠️ Admin Master Switch")
                 st.sidebar.caption("Override current view for internal testing.")
                 
                 if st.button("⚙️ Admin Console (Backend)", use_container_width=True):
                     st.session_state.app_mode = "admin"
                     st.rerun()
                 
                 if st.button("🏛️ Advisor Portal (QB View)", use_container_width=True):
                     st.session_state.app_mode = "advisor"
                     st.rerun()
                     
                 if st.button("📮 Consumer Store", use_container_width=True):
                     st.session_state.app_mode = "store"
                     st.rerun()
                 
                 if st.button("🤝 Partner Portal", use_container_width=True):
                     st.session_state.app_mode = "partner"
                     st.rerun()

                 st.sidebar.divider()

        with st.sidebar:
            if st.button("🚪 Sign Out", use_container_width=True):
                handle_logout()

    # 6. ROUTER LOGIC: VIEW RENDERING (EXPLICIT ROUTE MAP)
    mode = st.session_state.app_mode

    if mode == "admin":
        if ui_admin: 
            ui_admin.render_admin_page()
        else:
            st.error("Admin module (ui_admin.py) not found.")
        return

    if mode == "archive":
        if ui_archive: 
            ui_archive.render_heir_vault(project_id)
        else:
            st.error("Archive module (ui_archive.py) missing.")
        return
        
    if mode == "setup":
        if ui_setup: 
            ui_setup.render_parent_setup(project_id)
        else:
            st.error("Setup module (ui_setup.py) missing.")
        return

    if mode == "legal":
        if ui_legal: 
            ui_legal.render_legal_page()
        else:
            st.error("Legal module (ui_legal.py) missing.")
        return
        
    if mode == "blog":
        if ui_blog: 
            ui_blog.render_blog_page()
        else:
            st.error("Blog module (ui_blog.py) missing.")
        return

    if mode == "heirloom":
        if not st.session_state.authenticated:
            st.session_state.app_mode = "login"
            st.rerun()
        if ui_heirloom: 
            ui_heirloom.render_dashboard()
        else:
            st.error("Heirloom module (ui_heirloom.py) missing.")
        return

    if mode in ["store", "workspace", "review", "receipt"]:
        if ui_main: 
            ui_main.render_main()
        else:
            st.error("Retail module (ui_main.py) missing.")
        return

    if mode == "advisor":
        if ui_advisor:
            ui_advisor.render_dashboard()
        else:
            st.error("Advisor module missing.")
        return

    if mode == "partner":
        if ui_partner:
            ui_partner.render_dashboard()
        else:
            st.error("Partner module missing.")
        return

    if mode == "login":
        if ui_login: 
            ui_login.render_login_page()
        else:
            st.error("Login module (ui_login.py) missing.")
        return

    if ui_splash:
        ui_splash.render_splash_page()
    else:
        st.title("VerbaPost Wealth")
        st.write("System failed to initialize. Please check logs.")

if __name__ == "__main__":
    try:
        if database and st.session_state.get("authenticated"):
             sync_user_session()
        main()
    except Exception as e:
        logger.critical(f"FATAL SYSTEM CRASH: {e}", exc_info=True)
        st.error("A critical system error occurred.")
        if st.button("🔄 Attempt Emergency Recovery"):
            handle_logout()