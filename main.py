import streamlit as st

# --- 1. CRITICAL FIX: CONFIG MUST BE THE FIRST COMMAND ---
# Moved to the top to prevent StreamlitSetPageConfigMustBeFirstCommandError
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
# This block ensures high-resolution logs for production debugging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# --- 2. OAUTH FRAGMENT BRIDGE (PRESERVED) ---
# This JS snippet catches '#access_token=...' and turns it into '?access_token=...'
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

# --- MODULE IMPORTS (COMPLETE & UNREFACTORED) ---
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

# ==========================================
# 🛠️ HELPER FUNCTIONS (PRESERVED IN FULL)
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
                logger.info(f"Session Synced for {email} (Role: {st.session_state.user_role})")
        except Exception as e:
            logger.error(f"Session Sync Failure: {e}")

def handle_logout():
    """
    Clears all application state and triggers a clean restart.
    Ensures that OAuth tokens are cleared from the browser session.
    """
    logger.info("Triggering global logout and session clear.")
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# ==========================================
# 🚀 MAIN APPLICATION ENTRY POINT
# ==========================================

def main():
    # 1. INITIALIZE NAVIGATION & AUTH PARAMETERS
    # This section parses the URL directly to handle unauthenticated entry points
    query_params = st.query_params
    nav = query_params.get("nav")
    project_id = query_params.get("id")
    
    # Captured access_token from URL for Google Auth (Handled by JS Bridge)
    access_token = query_params.get("access_token")

    # 2. OAUTH VERIFICATION LOGIC (NEW FIX)
    # Intercepts the redirect before any UI is rendered
    if access_token and not st.session_state.get("authenticated"):
        if auth_engine:
            logger.info("Access token detected. Attempting OAuth verification...")
            user_email, error = auth_engine.verify_oauth_token(access_token)
            if user_email:
                st.session_state.authenticated = True
                st.session_state.user_email = user_email
                # Perform the full session sync immediately
                sync_user_session()
                st.query_params.clear()
                # Default to Heirloom Dashboard for archive-related logins
                st.session_state.app_mode = "heirloom" 
                logger.info(f"OAuth success: {user_email} authenticated.")
                st.rerun()
            else:
                logger.error(f"OAuth Failed: {error}")
                st.error(f"Authentication Error: {error}")

    # 3. SESSION STATE DEFAULTS (PRESERVED)
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "user_email" not in st.session_state:
        st.session_state.user_email = None
    if "user_role" not in st.session_state:
        st.session_state.user_role = "user"
    if "draft_id" not in st.session_state:
        st.session_state.draft_id = None
        
    # 4. INITIALIZE APP MODE ROUTING (FIXED)
    # This defines the "State Machine" that controls the UI
    if "app_mode" not in st.session_state:
        if nav == "archive": 
            # If a project_id exists, it's a shared vault view
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

    # 5. SIDEBAR: ADMIN MASTER SWITCH (PRESERVED IN FULL)
    # This section is strictly for the Founder/Developer
    if st.session_state.get("authenticated"):
        user_email = st.session_state.get("user_email")
        admin_email = secrets_manager.get_secret("admin.email") if secrets_manager else None
        
        # Security: Only verify against the hard-coded Admin Email
        if user_email and admin_email and user_email == admin_email:
             st.sidebar.markdown("### 🛠️ Admin Master Switch")
             st.sidebar.caption("Override current view for internal testing.")
             
             # Switch 1: Back Office Diagnostic Tools
             if st.sidebar.button("⚙️ Admin Console (Backend)", use_container_width=True):
                 st.session_state.app_mode = "admin"
                 st.rerun()
             
             # Switch 2: The Portal your Advisors see
             if st.sidebar.button("🏛️ Advisor Portal (QB View)", use_container_width=True):
                 st.session_state.app_mode = "advisor"
                 st.rerun()
                 
             # Switch 3: The Retail Consumer Store
             if st.sidebar.button("📮 Consumer Store", use_container_width=True):
                 st.session_state.app_mode = "store"
                 st.rerun()
             
             st.sidebar.divider()

        # Global Sidebar Navigation
        if st.sidebar.button("🚪 Sign Out", use_container_width=True):
            handle_logout()

    # 6. ROUTER LOGIC: VIEW RENDERING (FIXED)
    mode = st.session_state.app_mode

    # A. BACK OFFICE (Restricted to Authenticated Admin)
    if mode == "admin":
        if ui_admin: 
            ui_admin.render_admin_page()
        else:
            st.error("Admin module (ui_admin.py) not found in directory.")
        return

    # B. HEIR ARCHIVE (The Family Vault Entry Point)
    if mode == "archive":
        if ui_archive: 
            ui_archive.render_heir_vault(project_id)
        else:
            st.error("Archive module (ui_archive.py) missing.")
        return

    # C. HEIRLOOM DASHBOARD (The Family Archive Dashboard)
    if mode == "heirloom":
        if not st.session_state.get("authenticated"):
            st.session_state.app_mode = "login"
            st.rerun()
        if ui_heirloom:
            ui_heirloom.render_dashboard()
        else:
            st.error("Heirloom module (ui_heirloom.py) missing.")
        return

    # D. PARENT SETUP (Concierge Scheduling Entry Point)
    if mode == "setup":
        if ui_setup: 
            ui_setup.render_parent_setup(project_id)
        else:
            st.error("Setup module (ui_setup.py) missing.")
        return

    # E. STATIC PAGES (Direct Routing Fix for URLs)
    # UPDATED: Now calls respective render functions for Legal and Blog
    if mode == "legal":
        if ui_legal:
            ui_legal.render_legal_page()
        else:
            st.title("⚖️ Legal & Terms of Service")
            st.markdown("VerbaPost Wealth standard terms for Advisors, Clients, and Heirs.")
            if st.button("Return to Home"): 
                st.session_state.app_mode = "splash"
                st.rerun()
        return

    if mode == "blog":
        if ui_blog:
            ui_blog.render_blog_page()
        else:
            st.title("🗞️ The VerbaPost Blog")
            st.markdown("Insights on High-Net-Worth Retention and the $84 Trillion Wealth Transfer.")
            if st.button("Return to Home"): 
                st.session_state.app_mode = "splash"
                st.rerun()
        return

    # F. CONSUMER STORE / RETAIL (Preserved Retail Logic)
    if mode in ["store", "workspace", "review", "receipt"]:
        if ui_main: 
            ui_main.render_main()
        else:
            st.error("Retail module (ui_main.py) missing.")
        return

    # G. AUTHENTICATION (B2B Entry)
    if mode == "login":
        if ui_login: 
            ui_login.render_login_page()
        else:
            st.error("Login module (ui_login.py) missing.")
        return

    # H. ADVISOR DASHBOARD (Default B2B View)
    if st.session_state.get("authenticated"):
        if ui_advisor:
            ui_advisor.render_dashboard()
        else:
            st.error("Advisor module (ui_advisor.py) not found.")
        return

    # I. PUBLIC LANDING PAGE (The Splash)
    if ui_splash:
        ui_splash.render_splash_page()
    else:
        st.title("VerbaPost Wealth")
        st.write("Platform initialization failed. Contact system administrator.")

# ==========================================
# 🚀 SYSTEM BOOTSTRAP & ERROR WRAPPER
# ==========================================

if __name__ == "__main__":
    try:
        # Pre-flight data sync for authenticated users
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