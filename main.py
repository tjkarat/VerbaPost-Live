import streamlit as st
import sys
import os

# --- 🏷️ VERSION CONTROL ---
# Increment this constant at every functional update to this file.
VERSION = "4.4.1"  # Full Restoration & Hash-to-Query Bridge

# --- 1. CRITICAL: CONFIG MUST BE THE FIRST COMMAND ---
st.set_page_config(
    page_title=f"VerbaPost Wealth v{VERSION}", 
    page_icon="🛡️", 
    layout="centered",
    initial_sidebar_state="collapsed" 
)

# --- 2. PATH INJECTION (FIXES KEYERROR: 'DATABASE') ---
# This ensures that Streamlit can find local modules like database.py and ui_advisor.py
# especially during production environment transitions or GitHub pulls.
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

import streamlit.components.v1 as components
import logging
import time
import json

# ==========================================
# 🔧 SYSTEM & LOGGING SETUP (RESTORED)
# ==========================================
# This block ensures high-resolution logs for production debugging.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# --- 3. SEAMLESS OAUTH BRIDGE (HASH-TO-QUERY) ---
# Simple hash-to-query converter that works with Streamlit's sandbox.
# It converts #access_token=... into ?access_token=... within the same context.
components.html(
    """
    <script>
    (function() {
        const hash = window.location.hash;
        
        if (hash && hash.includes('access_token=')) {
            console.log('VerbaPost: Token found in hash, processing...');
            
            // Extract just the access_token
            const params = new URLSearchParams(hash.substring(1));
            const token = params.get('access_token');
            
            if (token) {
                // Construct new URL with token as query param
                const newUrl = window.location.origin + 
                              window.location.pathname + 
                              '?access_token=' + encodeURIComponent(token);
                
                // Replace current URL (doesn't add to history)
                // This bypasses the sandboxed top-level navigation block.
                window.location.replace(newUrl);
            }
        }
    })();
    </script>
    """,
    height=0,
)

# --- 4. MODULE IMPORTS (FULL ROBUST WRAPPING) ---
# Each import is wrapped individually to prevent the entire system from failing 
# if a single UI or engine file is corrupted or missing.
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
# 🛠️ HELPER FUNCTIONS (FULL RESTORATION)
# ==========================================

def sync_user_session():
    """Synchronizes Streamlit session state with the database UserProfile."""
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
    """Clears all application state and triggers a clean restart."""
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
    # --- STEP 1: OAUTH TOKEN INTERCEPTOR ---
    query_params = st.query_params
    access_token = query_params.get("access_token")
    
    if access_token and not st.session_state.get("authenticated"):
        if auth_engine:
            logger.info("🔐 OAuth token detected - Processing authentication...")
            with st.spinner("🔄 Finalizing Secure Login..."):
                email, err = auth_engine.verify_oauth_token(access_token)
                
                if email:
                    logger.info(f"✅ OAuth Success: {email}")
                    st.session_state.authenticated = True
                    st.session_state.user_email = email
                    st.session_state.app_mode = "heirloom"
                    
                    if database:
                        try:
                            if not database.get_user_profile(email):
                                database.create_user(email, email.split('@')[0])
                            sync_user_session()
                        except Exception as db_err:
                            logger.error(f"Database sync error: {db_err}")
                    
                    # Clear query params to prevent re-authentication loops
                    st.query_params.clear()
                    st.rerun()
                else:
                    logger.error(f"OAuth verification failed: {err}")
                    st.error(f"❌ Authentication Error: {err}")
                    if st.button("Return to Login"):
                        st.query_params.clear()
                        st.session_state.app_mode = "login"
                        st.rerun()
                    st.stop()

    # --- STEP 2: SYSTEM HEALTH PRE-FLIGHT ---
    if module_validator and not st.session_state.get("system_verified"):
        health = module_validator.run_preflight_checks()
        if not health["status"]:
            st.error("⚠️ System configuration error. Check Admin logs.")
            st.stop()
        st.session_state.system_verified = True

    # --- STEP 3: INITIALIZE SESSION STATE DEFAULTS ---
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "user_email" not in st.session_state:
        st.session_state.user_email = None
    if "user_role" not in st.session_state:
        st.session_state.user_role = "user"
        
    # --- STEP 4: APP MODE ROUTING (STATE MACHINE) ---
    nav = query_params.get("nav")
    project_id = query_params.get("id")
    
    if "app_mode" not in st.session_state:
        if nav == "legal": st.session_state.app_mode = "legal"
        elif nav == "blog": st.session_state.app_mode = "blog"
        elif nav == "partner": st.session_state.app_mode = "partner"
        elif nav == "setup": st.session_state.app_mode = "setup"
        elif nav == "archive": st.session_state.app_mode = "archive"
        elif nav == "login": st.session_state.app_mode = "login"
        else: st.session_state.app_mode = "splash"

    # --- STEP 5: SIDEBAR MASTER SWITCH ---
    with st.sidebar:
        st.caption(f"VerbaPost Wealth Build: v{VERSION}")
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
            if st.button("🚪 Sign Out", use_container_width=True):
                handle_logout()

    # --- STEP 6: ROUTE TO APPROPRIATE VIEW ---
    mode = st.session_state.app_mode

    if mode == "admin" and ui_admin: ui_admin.render_admin_page()
    elif mode == "archive" and ui_archive: ui_archive.render_heir_vault(project_id)
    elif mode == "setup" and ui_setup: ui_setup.render_parent_setup(project_id)
    elif mode == "legal" and ui_legal: ui_legal.render_legal_page()
    elif mode == "blog" and ui_blog: ui_blog.render_blog_page()
    elif mode == "heirloom":
        if not st.session_state.authenticated:
            st.session_state.app_mode = "login"
            st.rerun()
        if ui_heirloom: ui_heirloom.render_dashboard()
    elif mode in ["store", "workspace", "review", "receipt"]:
        if ui_main: ui_main.render_main()
    elif mode == "advisor" and ui_advisor: ui_advisor.render_dashboard()
    elif mode == "partner" and ui_partner: ui_partner.render_dashboard()
    elif mode == "login" and ui_login: ui_login.render_login_page()
    elif ui_splash: ui_splash.render_splash_page()

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