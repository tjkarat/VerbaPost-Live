import streamlit as st

# --- 1. CRITICAL: CONFIG MUST BE THE FIRST COMMAND ---
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
import json

# ==========================================
# 🔧 SYSTEM & LOGGING SETUP (PRESERVED)
# ==========================================
# This block ensures high-resolution logs for production debugging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# --- 2. OAUTH FRAGMENT BRIDGE ---
# Converts URL fragments (#access_token) into parameters (?access_token)
# so that the Python router can process the login fragment.
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

# --- 3. MODULE IMPORTS (ROBUST ERROR WRAPPING) ---
# Each import is wrapped in an individual try/except to prevent app-wide crashes
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
    # Intercepts the redirect before any UI or defaults are rendered
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
                    # Default to Heirloom Dashboard for archive-related logins
                    st.session_state.app_mode = "heirloom" 
                    sync_user_session()
                    st.query_params.clear()
                    logger.info(f"OAuth Success: {email}")
                    st.rerun()
                else:
                    logger.error(f"Auth failed: {err}")
                    st.error(f"Authentication Error: {err}")

    # 2. SYSTEM HEALTH PRE-FLIGHT (RESTORED)
    # Verifies critical third-party engines before allowing the UI to load
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
        # Check for nav params from landing page index.html
        if nav == "legal": 
            st.session_state.app_mode = "legal"
        elif nav == "blog": 
            st.session_state.app_mode = "blog"
        elif nav == "partner": 
            st.session_state.app_mode = "login"
        elif nav == "setup": 
            st.session_state.app_mode = "setup"
        elif nav == "archive":
            st.session_state.app_mode = "archive"
        else: 
            st.session_state.app_mode = "splash"

    # 5. SIDEBAR: ADMIN MASTER SWITCH (RESTORED IN FULL)
    # This section is strictly for the Founder/Developer
    if st.session_state.get("authenticated"):
        user_email = st.session_state.get("user_email")
        admin_email = secrets_manager.get_secret("admin.email") if secrets_manager else None
        
        # Security: Only verify against the hard-coded Admin Email
        if user_email and admin_email and user_email == admin_email:
             with st.sidebar:
                 st.markdown("### 🛠️ Admin Master Switch")
                 st.sidebar.caption("Override current view for internal testing.")
                 
                 # Switch 1: Back Office Diagnostic Tools
                 if st.button("⚙️ Admin Console (Backend)", use_container_width=True):
                     st.session_state.app_mode = "admin"
                     st.rerun()
                 
                 # Switch 2: The Portal your Advisors see
                 if st.button("🏛️ Advisor Portal (QB View)", use_container_width=True):
                     st.session_state.app_mode = "advisor"
                     st.rerun()
                     
                 # Switch 3: The Retail Consumer Store
                 if st.button("📮 Consumer Store", use_container_width=True):
                     st.session_state.app_mode = "store"
                     st.rerun()
                 
                 st.sidebar.divider()

        # Global Sidebar Navigation
        if st.sidebar.button("🚪 Sign Out", use_container_width=True):
            handle_logout()

    # 6. ROUTER LOGIC: VIEW RENDERING (EXPLICIT ROUTE MAP)
    mode = st.session_state.app_mode

    # --- CATEGORY 1: BACK OFFICE ---
    if mode == "admin":
        if ui_admin: 
            ui_admin.render_admin_page()
        else:
            st.error("Admin module (ui_admin.py) not found.")
        return

    # --- CATEGORY 2: FAMILY VAULT / SETUP ---
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

    # --- CATEGORY 3: STATIC PAGES ---
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

    # --- CATEGORY 4: HEIRLOOM DASHBOARD (DASHBOARD) ---
    if mode == "heirloom":
        if not st.session_state.authenticated:
            st.session_state.app_mode = "login"
            st.rerun()
        if ui_heirloom: 
            ui_heirloom.render_dashboard()
        else:
            st.error("Heirloom module (ui_heirloom.py) missing.")
        return

    # --- CATEGORY 5: CONSUMER STORE / WORKSPACE ---
    if mode in ["store", "workspace", "review", "receipt"]:
        if ui_main: 
            ui_main.render_main()
        else:
            st.error("Retail module (ui_main.py) missing.")
        return

    # --- CATEGORY 6: ADVISOR B2B PORTAL ---
    # Default view for authenticated Advisor accounts
    if st.session_state.get("authenticated"):
        if ui_advisor: 
            ui_advisor.render_dashboard()
        else:
            st.error("Advisor module (ui_advisor.py) not found.")
        return

    # --- CATEGORY 7: AUTHENTICATION GATE ---
    if mode == "login":
        if ui_login: 
            ui_login.render_login_page()
        else:
            st.error("Login module (ui_login.py) missing.")
        return

    # --- CATEGORY 8: DEFAULT PUBLIC LANDING ---
    if ui_splash:
        ui_splash.render_splash_page()
    else:
        st.title("VerbaPost Wealth")
        st.write("System failed to initialize. Please check logs.")

# ==========================================
# 🚀 SYSTEM BOOTSTRAP & ERROR WRAPPER
# ==========================================

if __name__ == "__main__":
    try:
        # Pre-flight data sync for authenticated sessions
        if database and st.session_state.get("authenticated"):
             sync_user_session()
             
        # Execute Main Application logic
        main()
        
    except Exception as e:
        # Final safety net for uncaught system exceptions
        logger.critical(f"FATAL SYSTEM CRASH: {e}", exc_info=True)
        st.error("A critical system error occurred. Our engineering team has been notified.")
        if st.button("🔄 Attempt Emergency Recovery"):
            handle_logout()