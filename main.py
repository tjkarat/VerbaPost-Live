import streamlit as st

# --- 1. CRITICAL FIX: CONFIG MUST BE THE FIRST COMMAND ---
st.set_page_config(
    page_title="VerbaPost Wealth | Family Legacy Retention", 
    page_icon="🏛️", 
    layout="centered",
    initial_sidebar_state="expanded" 
)

import streamlit.components.v1 as components
import logging
import os
import sys
import time

# ==========================================
# 🔧 SYSTEM & LOGGING SETUP (PRESERVED)
# ==========================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# --- 1. OAUTH FRAGMENT BRIDGE (NEW FIX) ---
components.html(
    """
    <script>
    var hash = window.parent.location.hash;
    if (hash && hash.includes('access_token=')) {
        var newUrl = window.parent.location.pathname + hash.replace('#', '?');
        window.parent.location.href = newUrl;
    }
    </script>
    """,
    height=0,
)

# --- MODULE IMPORTS (COMPLETE & UNREFACTORED) ---
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

# ==========================================
# 🛠️ HELPER FUNCTIONS (PRESERVED IN FULL)
# ==========================================

def sync_user_session():
    if st.session_state.get("authenticated") and st.session_state.get("user_email"):
        try:
            email = st.session_state.get("user_email")
            profile = database.get_user_profile(email)
            if profile:
                st.session_state.user_role = profile.get("role", "user")
                st.session_state.user_credits = profile.get("credits", 0)
                st.session_state.full_name = profile.get("full_name", "")
                logger.info(f"Session Synced for {email} (Role: {st.session_state.user_role})")
        except Exception as e:
            logger.error(f"Session Sync Failure: {e}")

def handle_logout():
    logger.info("Triggering global logout and session clear.")
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# ==========================================
# 🚀 MAIN APPLICATION ENTRY POINT
# ==========================================

def main():
    query_params = st.query_params
    nav = query_params.get("nav")
    project_id = query_params.get("id")
    access_token = query_params.get("access_token")

    if access_token and not st.session_state.get("authenticated"):
        if auth_engine:
            logger.info("Access token detected. Attempting OAuth verification...")
            user_email, error = auth_engine.verify_oauth_token(access_token)
            if user_email:
                st.session_state.authenticated = True
                st.session_state.user_email = user_email
                sync_user_session()
                st.query_params.clear()
                st.session_state.app_mode = "heirloom" 
                st.rerun()
            else:
                st.error(f"Authentication Error: {error}")

    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "user_email" not in st.session_state:
        st.session_state.user_email = None
    if "user_role" not in st.session_state:
        st.session_state.user_role = "user"
    if "draft_id" not in st.session_state:
        st.session_state.draft_id = None
        
    if "app_mode" not in st.session_state:
        if nav == "archive": 
            if project_id:
                st.session_state.app_mode = "archive"
            else:
                st.session_state.app_mode = "heirloom"
        elif nav == "setup": 
            st.session_state.app_mode = "setup"
        elif nav == "legal":
            st.session_state.app_mode = "legal"
        elif nav == "blog":
            st.session_state.app_mode = "blog"
        elif nav in ["partner", "login"]:
            st.session_state.app_mode = "login"
        else:
            st.session_state.app_mode = "splash"

    if st.session_state.get("authenticated"):
        user_email = st.session_state.get("user_email")
        admin_email = secrets_manager.get_secret("admin.email") if secrets_manager else None
        
        if user_email and admin_email and user_email == admin_email:
             st.sidebar.markdown("### 🛠️ Admin Master Switch")
             if st.sidebar.button("⚙️ Admin Console (Backend)", use_container_width=True):
                 st.session_state.app_mode = "admin"
                 st.rerun()
             if st.sidebar.button("🏛️ Advisor Portal (QB View)", use_container_width=True):
                 st.session_state.app_mode = "advisor"
                 st.rerun()
             if st.sidebar.button("📮 Consumer Store", use_container_width=True):
                 st.session_state.app_mode = "store"
                 st.rerun()
             st.sidebar.divider()

        if st.sidebar.button("🚪 Sign Out", use_container_width=True):
            handle_logout()

    mode = st.session_state.app_mode

    if mode == "admin":
        if ui_admin: ui_admin.render_admin_page()
        else: st.error("Admin module missing.")
        return

    if mode == "archive":
        if ui_archive: ui_archive.render_heir_vault(project_id)
        else: st.error("Archive module missing.")
        return

    if mode == "heirloom":
        if not st.session_state.get("authenticated"):
            st.session_state.app_mode = "login"
            st.rerun()
        if ui_heirloom: ui_heirloom.render_dashboard()
        else: st.error("Heirloom module missing.")
        return

    if mode == "setup":
        if ui_setup: ui_setup.render_parent_setup(project_id)
        else: st.error("Setup module missing.")
        return

    if mode == "legal":
        st.title("⚖️ Legal & Terms of Service")
        st.markdown("VerbaPost Wealth standard terms for Advisors, Clients, and Heirs.")
        if st.button("Return to Home"): 
            st.session_state.app_mode = "splash"
            st.rerun()
        return

    if mode == "blog":
        st.title("🗞️ The VerbaPost Blog")
        if st.button("Return to Home"): 
            st.session_state.app_mode = "splash"
            st.rerun()
        return

    if mode in ["store", "workspace", "review", "receipt"]:
        if ui_main: ui_main.render_main()
        else: st.error("Retail module missing.")
        return

    if mode == "login":
        if ui_login: ui_login.render_login_page()
        else: st.error("Login module missing.")
        return

    if st.session_state.get("authenticated"):
        if ui_advisor: ui_advisor.render_dashboard()
        else: st.error("Advisor module missing.")
        return

    if ui_splash: ui_splash.render_splash_page()
    else: st.title("VerbaPost Wealth Initialization Failed.")

# ==========================================
# 🚀 SYSTEM BOOTSTRAP & ERROR WRAPPER
# ==========================================

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