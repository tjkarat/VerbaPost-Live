import streamlit as st

# --- VERSION CONTROL ---
VERSION = "4.3.0"  # OAuth Flow Complete Rewrite

# --- 1. CRITICAL: CONFIG MUST BE THE FIRST COMMAND ---
st.set_page_config(
    page_title=f"VerbaPost Wealth v{VERSION}", 
    page_icon="🛡️", 
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
# 🔧 SYSTEM & LOGGING SETUP
# ==========================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# --- 2. ENHANCED OAUTH FRAGMENT BRIDGE ---
# This JavaScript extracts tokens from URL hash and converts them to query params
components.html(
    """
    <script>
    (function() {
        try {
            const hash = window.location.hash;
            
            if (hash && hash.includes('access_token=')) {
                console.log('VerbaPost: OAuth token detected in hash');
                
                // Parse hash fragment
                const params = new URLSearchParams(hash.substring(1));
                const accessToken = params.get('access_token');
                const refreshToken = params.get('refresh_token');
                const tokenType = params.get('token_type');
                
                if (accessToken) {
                    // Build new URL with query params instead of hash
                    const url = new URL(window.location.href.split('#')[0]);
                    url.searchParams.set('access_token', accessToken);
                    if (refreshToken) url.searchParams.set('refresh_token', refreshToken);
                    if (tokenType) url.searchParams.set('token_type', tokenType);
                    
                    // Redirect to clean URL with tokens in query params
                    console.log('VerbaPost: Redirecting to process tokens');
                    window.location.href = url.toString();
                }
            }
        } catch (e) {
            console.error('VerbaPost OAuth Bridge Error:', e);
        }
    })();
    </script>
    """,
    height=0,
)

# --- 3. MODULE IMPORTS ---
try: import ui_splash
except ImportError as e: 
    logger.error(f"UI Splash Import Error: {e}")
    ui_splash = None

try: import ui_advisor
except ImportError as e: 
    logger.error(f"UI Advisor Import Error: {e}")
    ui_advisor = None

try: import ui_login
except ImportError as e: 
    logger.error(f"UI Login Import Error: {e}")
    ui_login = None

try: import ui_admin
except ImportError as e: 
    logger.error(f"UI Admin Import Error: {e}")
    ui_admin = None

try: import ui_main
except ImportError as e: 
    logger.error(f"UI Main Import Error: {e}")
    ui_main = None

try: import ui_setup
except ImportError as e: 
    logger.error(f"UI Setup Import Error: {e}")
    ui_setup = None

try: import ui_archive
except ImportError as e: 
    logger.error(f"UI Archive Import Error: {e}")
    ui_archive = None

try: import ui_heirloom
except ImportError as e:
    logger.error(f"UI Heirloom Import Error: {e}")
    ui_heirloom = None

try: import ui_legal
except ImportError as e:
    logger.error(f"UI Legal Import Error: {e}")
    ui_legal = None

try: import ui_blog
except ImportError as e:
    logger.error(f"UI Blog Import Error: {e}")
    ui_blog = None

try: import ui_partner
except ImportError as e:
    logger.error(f"UI Partner Import Error: {e}")
    ui_partner = None

try: import auth_engine
except ImportError as e: 
    logger.error(f"Auth Engine Import Error: {e}")
    auth_engine = None

try: import database
except ImportError as e: 
    logger.error(f"Database Import Error: {e}")
    database = None

try: import secrets_manager
except ImportError as e: 
    logger.error(f"Secrets Manager Import Error: {e}")
    secrets_manager = None

try: import module_validator
except ImportError: 
    module_validator = None

# ==========================================
# 🛠️ HELPER FUNCTIONS
# ==========================================

def sync_user_session():
    """Synchronizes session state with database UserProfile."""
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
    """Clears all application state and triggers clean restart."""
    logger.info("Triggering global logout and session clear.")
    if auth_engine: 
        auth_engine.sign_out()
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# ==========================================
# 🚀 MAIN APPLICATION ENTRY POINT
# ==========================================

def main():
    # --- STEP 1: OAUTH TOKEN INTERCEPTOR ---
    query_params = st.query_params
    access_token = query_params.get("access_token")
    oauth_callback = query_params.get("oauth_callback")
    
    # Check if this is an OAuth callback with token
    if access_token and not st.session_state.get("authenticated"):
        if auth_engine:
            logger.info("🔐 OAuth token detected - Processing authentication...")
            
            with st.spinner("🔄 Completing Google Sign-In..."):
                email, err = auth_engine.verify_oauth_token(access_token)
                
                if email:
                    logger.info(f"✅ OAuth Success: {email}")
                    
                    # Set session state
                    st.session_state.authenticated = True
                    st.session_state.user_email = email
                    st.session_state.app_mode = "heirloom"
                    
                    # Create/sync user profile
                    if database:
                        try:
                            profile = database.get_user_profile(email)
                            if not profile:
                                logger.info(f"Creating new profile for OAuth user: {email}")
                                # Extract name from email if available
                                display_name = email.split('@')[0]
                                database.create_user(email, display_name)
                            sync_user_session()
                        except Exception as db_err:
                            logger.error(f"Database sync error: {db_err}")
                    
                    # Clear OAuth params and redirect to clean URL
                    st.query_params.clear()
                    logger.info("Redirecting to dashboard...")
                    time.sleep(0.5)  # Brief delay for user feedback
                    st.rerun()
                else:
                    logger.error(f"OAuth verification failed: {err}")
                    st.error(f"❌ Authentication Error: {err}")
                    st.info("Please try signing in again.")
                    if st.button("Return to Login"):
                        st.query_params.clear()
                        st.session_state.app_mode = "login"
                        st.rerun()
                    st.stop()
        else:
            st.error("Auth engine not available")
            st.stop()
    
    # --- STEP 2: SYSTEM HEALTH CHECK ---
    if module_validator and not st.session_state.get("system_verified"):
        health = module_validator.run_preflight_checks()
        if not health["status"]:
            st.error("⚠️ System configuration error. Check logs for missing API keys.")
            st.stop()
        st.session_state.system_verified = True

    # --- STEP 3: INITIALIZE SESSION STATE ---
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "user_email" not in st.session_state:
        st.session_state.user_email = None
    if "user_role" not in st.session_state:
        st.session_state.user_role = "user"
        
    # --- STEP 4: APP MODE ROUTING ---
    nav = query_params.get("nav")
    project_id = query_params.get("id")
    
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

    # --- STEP 5: SIDEBAR ---
    with st.sidebar:
        st.caption(f"VerbaPost Wealth Build: v{VERSION}")
        st.divider()

    if st.session_state.get("authenticated"):
        user_email = st.session_state.get("user_email")
        admin_email = secrets_manager.get_secret("admin.email") if secrets_manager else None
        
        # Admin Master Switch
        if user_email and admin_email and user_email == admin_email:
             with st.sidebar:
                 st.markdown("### 🛠️ Admin Master Switch")
                 st.sidebar.caption("Override current view for internal testing.")
                 
                 if st.button("⚙️ Admin Console", use_container_width=True):
                     st.session_state.app_mode = "admin"
                     st.rerun()
                 
                 if st.button("🛡️ Advisor Portal", use_container_width=True):
                     st.session_state.app_mode = "advisor"
                     st.rerun()
                     
                 if st.button("🔮 Consumer Store", use_container_width=True):
                     st.session_state.app_mode = "store"
                     st.rerun()
                 
                 if st.button("🤝 Partner Portal", use_container_width=True):
                     st.session_state.app_mode = "partner"
                     st.rerun()

                 st.sidebar.divider()

        # Logout Button
        with st.sidebar:
            if st.button("🚪 Sign Out", use_container_width=True):
                handle_logout()

    # --- STEP 6: ROUTE TO APPROPRIATE VIEW ---
    mode = st.session_state.app_mode

    if mode == "admin":
        if ui_admin: 
            ui_admin.render_admin_page()
        else:
            st.error("Admin module not found.")
        return

    if mode == "archive":
        if ui_archive: 
            ui_archive.render_heir_vault(project_id)
        else:
            st.error("Archive module missing.")
        return
        
    if mode == "setup":
        if ui_setup: 
            ui_setup.render_parent_setup(project_id)
        else:
            st.error("Setup module missing.")
        return

    if mode == "legal":
        if ui_legal: 
            ui_legal.render_legal_page()
        else:
            st.error("Legal module missing.")
        return
        
    if mode == "blog":
        if ui_blog: 
            ui_blog.render_blog_page()
        else:
            st.error("Blog module missing.")
        return

    if mode == "heirloom":
        if not st.session_state.authenticated:
            st.session_state.app_mode = "login"
            st.rerun()
        if ui_heirloom: 
            ui_heirloom.render_dashboard()
        else:
            st.error("Heirloom module missing.")
        return

    if mode in ["store", "workspace", "review", "receipt"]:
        if ui_main: 
            ui_main.render_main()
        else:
            st.error("Retail module missing.")
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
            st.error("Login module missing.")
        return

    # Default: Splash page
    if ui_splash:
        ui_splash.render_splash_page()
    else:
        st.title("VerbaPost Wealth")
        st.write("System initialization failed. Check logs.")

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