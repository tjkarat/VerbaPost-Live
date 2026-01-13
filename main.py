import streamlit as st
import sys
import os

# --- 🏷️ VERSION CONTROL ---
VERSION = "4.5.3"  # Silent Auth Bridge + Advisor Routing

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

# --- 3. HARDENED OAUTH BRIDGE (SILENT MODE) ---
# FIX: Removed visible HTML <div>. Logic remains intact.
components.html(
    """
    <script>
    (function() {
        const log = (msg) => { console.log("VerbaPost Bridge:", msg); };

        try {
            const topWin = window.top || window.parent;
            const hash = topWin.location.hash;
            
            if (hash && hash.includes('access_token=')) {
                log("Token found. Processing...");
                
                const params = new URLSearchParams(hash.substring(1));
                const accessToken = params.get('access_token');
                const refreshToken = params.get('refresh_token');
                
                if (accessToken) {
                    const cleanUrl = topWin.location.origin + topWin.location.pathname;
                    let finalUrl = cleanUrl + '?access_token=' + encodeURIComponent(accessToken);
                    if (refreshToken) finalUrl += '&refresh_token=' + encodeURIComponent(refreshToken);

                    try {
                        topWin.location.href = finalUrl;
                    } catch (e) {
                        window.open(finalUrl, "_top");
                    }
                }
            }
        } catch (e) {
            console.error("Bridge Error:", e);
        }
    })();
    </script>
    """,
    height=0,
    width=0
)

# --- 4. MODULE IMPORTS (ROBUST) ---
try: import ui_splash
except ImportError as e: logger.error(f"UI Splash Error: {e}"); ui_splash = None
try: import ui_advisor
except ImportError as e: logger.error(f"UI Advisor Error: {e}"); ui_advisor = None
try: import ui_login
except ImportError as e: logger.error(f"UI Login Error: {e}"); ui_login = None
try: import ui_admin
except ImportError as e: logger.error(f"UI Admin Error: {e}"); ui_admin = None
try: import ui_main
except ImportError as e: logger.error(f"UI Main Error: {e}"); ui_main = None
try: import ui_setup
except ImportError as e: logger.error(f"UI Setup Error: {e}"); ui_setup = None
try: import ui_archive
except ImportError as e: logger.error(f"UI Archive Error: {e}"); ui_archive = None
try: import ui_heirloom
except ImportError as e: logger.error(f"UI Heirloom Error: {e}"); ui_heirloom = None
try: import ui_legal
except ImportError as e: logger.error(f"UI Legal Error: {e}"); ui_legal = None
try: import ui_blog
except ImportError as e: logger.error(f"UI Blog Error: {e}"); ui_blog = None
try: import ui_partner
except ImportError as e: logger.error(f"UI Partner Error: {e}"); ui_partner = None
try: import auth_engine
except ImportError as e: logger.error(f"Auth Engine Error: {e}"); auth_engine = None
try: import database
except ImportError as e: logger.error(f"Database Error: {e}"); database = None
try: import secrets_manager
except ImportError as e: logger.error(f"Secrets Error: {e}"); secrets_manager = None
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
                st.session_state.is_partner = (st.session_state.user_role in ["partner", "admin", "advisor"])
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
                            except Exception as db_err:
                                logger.error(f"Database sync error: {db_err}")
                        
                        st.query_params.clear()
                        st.rerun()
                    else:
                        st.error(f"Login Failed: {err}")
                        st.session_state.auth_processing = False

    # --- STEP 1: OAUTH TOKEN INTERCEPTOR (LEGACY) ---
    query_params = st.query_params
    access_token = query_params.get("access_token")
    if access_token and not st.session_state.get("authenticated"):
        if auth_engine:
            with st.spinner("🔄 Finalizing Secure Login..."):
                email, err = auth_engine.verify_oauth_token(access_token)
                if email:
                    logger.info(f"✅ OAuth Success: {email}")
                    st.session_state.authenticated = True
                    st.session_state.user_email = email
                    
                    if database:
                        try:
                            # Immediate Profile Check for Routing
                            profile = database.get_user_profile(email)
                            if profile and profile.get("role") == "advisor":
                                st.session_state.app_mode = "advisor"
                            else:
                                st.session_state.app_mode = "heirloom"
                                
                            if not profile:
                                database.create_user(email, email.split('@')[0])
                            sync_user_session()
                        except Exception as db_err:
                            logger.error(f"Database sync error: {db_err}")
                    
                    st.query_params.clear()
                    st.rerun()
                else:
                    st.error(f"Auth Error: {err}")
                    if st.button("Return to Login"):
                        st.query_params.clear()
                        st.session_state.app_mode = "login"
                        st.rerun()
                    st.stop()

    # --- STEP 2: HEALTH ---
    if module_validator and not st.session_state.get("system_verified"):
        health = module_validator.run_preflight_checks()
        if not health["status"]:
            st.error("System configuration error.")
            st.stop()
        st.session_state.system_verified = True

    # --- STEP 3: SESSION DEFAULTS ---
    if "authenticated" not in st.session_state: st.session_state.authenticated = False
    if "user_email" not in st.session_state: st.session_state.user_email = None
    
    # --- STEP 4: ROUTING ---
    nav = query_params.get("nav")
    play_id = query_params.get("play")
    
    if "app_mode" not in st.session_state:
        if play_id:
            st.session_state.app_mode = "archive"
            query_params["id"] = play_id
        elif nav == "advisor": st.session_state.app_mode = "advisor"
        elif nav == "login": st.session_state.app_mode = "login"
        elif nav == "heirloom": st.session_state.app_mode = "heirloom"
        elif nav == "admin": st.session_state.app_mode = "admin"
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
                 st.sidebar.divider()

        with st.sidebar:
            if st.button("🚪 Sign Out", use_container_width=True): handle_logout()

    # --- STEP 6: VIEW CONTROLLER ---
    mode = st.session_state.app_mode
    
    if mode == "admin" and ui_admin: ui_admin.render_admin_page()
    elif mode == "archive" and ui_archive: ui_archive.render_heir_vault(play_id)
    elif mode == "login" and ui_login: ui_login.render_login_page()
    elif mode == "advisor" and ui_advisor: ui_advisor.render_dashboard()
    
    # HEIRLOOM (Protected)
    elif mode == "heirloom":
        if not st.session_state.authenticated:
            st.session_state.app_mode = "login"
            st.rerun()
        if ui_heirloom: ui_heirloom.render_dashboard()

    elif ui_splash: ui_splash.render_splash_page()
    else:
        st.session_state.app_mode = "splash"
        st.rerun()

if __name__ == "__main__":
    if database and st.session_state.get("authenticated"): sync_user_session()
    main()