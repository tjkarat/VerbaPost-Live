import streamlit as st
import sys
import os

# --- 🏷️ VERSION CONTROL ---
# Increment this constant at every functional update to this file.
VERSION = "4.3.3"  # Path Resolution & Security Fix

# --- 1. CRITICAL: CONFIG MUST BE THE FIRST COMMAND ---
st.set_page_config(
    page_title=f"VerbaPost Wealth v{VERSION}", 
    page_icon="🛡️", 
    layout="centered",
    initial_sidebar_state="expanded" 
)

# --- 2. PATH INJECTION (FIXES KEYERROR: 'DATABASE') ---
# This ensures that Streamlit can find local modules like database.py and ui_advisor.py
# even after code changes or repository pulls.
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

# --- 3. HARDENED OAUTH FRAGMENT BRIDGE ---
# This JavaScript bridge resolves the SecurityError by targeting window.top.
# If the automated redirect is blocked by the browser, a fallback button appears.
components.html(
    """
    <script>
    (function() {
        try {
            const topWin = window.top;
            const hash = topWin.location.hash;
            
            if (hash && hash.includes('access_token=')) {
                console.log('VerbaPost: OAuth token detected');
                
                const params = new URLSearchParams(hash.substring(1));
                const accessToken = params.get('access_token');
                const refreshToken = params.get('refresh_token');
                const tokenType = params.get('token_type');
                
                if (accessToken) {
                    const url = new URL(topWin.location.origin + topWin.location.pathname);
                    url.searchParams.set('access_token', accessToken);
                    if (refreshToken) url.searchParams.set('refresh_token', refreshToken);
                    if (tokenType) url.searchParams.set('token_type', tokenType);
                    
                    // Attempt automatic redirect to the top-level window
                    try {
                        topWin.location.href = url.toString();
                    } catch (e) {
                        console.warn("Seamless redirect blocked. Showing fallback button.");
                        document.body.innerHTML = `
                            <div style="font-family:sans-serif; text-align:center; padding-top:10px;">
                                <a href="${url.toString()}" target="_top" style="
                                    background-color:#ef4444; color:white; padding:12px 24px; 
                                    text-decoration:none; border-radius:6px; font-weight:600; display:inline-block;">
                                    Confirm Secure Login &rarr;
                                </a>
                            </div>
                        `;
                    }
                }
            }
        } catch (e) {
            console.error('VerbaPost OAuth Bridge Error:', e);
        }
    })();
    </script>
    """,
    height=60,
)

# --- 4. MODULE IMPORTS ---
# Wrapped in try/except to maintain stability even if individual modules are missing.
try: import ui_splash
except ImportError as e: logger.error(f"UI Splash Import Error: {e}"); ui_splash = None

try: import ui_advisor
except ImportError as e: logger.error(f"UI Advisor Import Error: {e}"); ui_advisor = None

try: import ui_login
except ImportError as e: logger.error(f"UI Login Import Error: {e}"); ui_login = None

try: import ui_admin
except ImportError as e: logger.error(f"UI Admin Import Error: {e}"); ui_admin = None

try: import ui_main
except ImportError as e: logger.error(f"UI Main Import Error: {e}"); ui_main = None

try: import ui_setup
except ImportError as e: logger.error(f"UI Setup Import Error: {e}"); ui_setup = None

try: import ui_archive
except ImportError as e: logger.error(f"UI Archive Import Error: {e}"); ui_archive = None

try: import ui_heirloom
except ImportError as e: logger.error(f"UI Heirloom Import Error: {e}"); ui_heirloom = None

try: import ui_legal
except ImportError as e: logger.error(f"UI Legal Import Error: {e}"); ui_legal = None

try: import ui_blog
except ImportError as e: logger.error(f"UI Blog Import Error: {e}"); ui_blog = None

try: import ui_partner
except ImportError as e: logger.error(f"UI Partner Import Error: {e}"); ui_partner = None

try: import auth_engine
except ImportError as e: logger.error(f"Auth Engine Import Error: {e}"); auth_engine = None

try: import database
except ImportError as e: logger.error(f"Database Import Error: {e}"); database = None

try: import secrets_manager
except ImportError as e: logger.error(f"Secrets Manager Import Error: {e}"); secrets_manager = None

try: import module_validator
except ImportError: module_validator = None

# ==========================================
# 🛠️ HELPER FUNCTIONS
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
                st.session_state.is_partner = (st.session_state.user_role in ["partner", "admin"])
        except Exception as e:
            logger.error(f"Session Sync Failure: {e}")

def handle_logout():
    if auth_engine: auth_engine.sign_out()
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
    
    if access_token and not st.session_state.get("authenticated"):
        if auth_engine:
            logger.info("🔐 OAuth token detected - Processing authentication...")
            with st.spinner("🔄 Verifying Secure Login..."):
                email, err = auth_engine.verify_oauth_token(access_token)
                if email:
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
                    st.query_params.clear()
                    st.rerun()
                else:
                    st.error(f"❌ Authentication Error: {err}")
                    if st.button("Return to Login"):
                        st.query_params.clear()
                        st.session_state.app_mode = "login"
                        st.rerun()
                    st.stop()

    # --- STEP 2: SYSTEM HEALTH CHECK ---
    if module_validator and not st.session_state.get("system_verified"):
        health = module_validator.run_preflight_checks()
        if not health["status"]:
            st.error("⚠️ System configuration error. Check logs.")
            st.stop()
        st.session_state.system_verified = True

    # --- STEP 3: INITIALIZE SESSION STATE ---
    if "authenticated" not in st.session_state: st.session_state.authenticated = False
    if "user_email" not in st.session_state: st.session_state.user_email = None
    if "user_role" not in st.session_state: st.session_state.user_role = "user"
        
    # --- STEP 4: APP MODE ROUTING ---
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

    # --- STEP 5: SIDEBAR ---
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
            if st.button("🚪 Sign Out", use_container_width=True): handle_logout()

    # --- STEP 6: ROUTE TO VIEW ---
    mode = st.session_state.app_mode
    if mode == "admin" and ui_admin: ui_admin.render_admin_page()
    elif mode == "archive" and ui_archive: ui_archive.render_heir_vault(project_id)
    elif mode == "setup" and ui_setup: ui_setup.render_parent_setup(project_id)
    elif mode == "legal" and ui_legal: ui_legal.render_legal_page()
    elif mode == "blog" and ui_blog: ui_blog.render_blog_page()
    elif mode == "heirloom":
        if not st.session_state.authenticated: st.session_state.app_mode = "login"; st.rerun()
        if ui_heirloom: ui_heirloom.render_dashboard()
    elif mode in ["store", "workspace", "review", "receipt"]:
        if ui_main: ui_main.render_main()
    elif mode == "advisor" and ui_advisor: ui_advisor.render_dashboard()
    elif mode == "partner" and ui_partner: ui_partner.render_dashboard()
    elif mode == "login" and ui_login: ui_login.render_login_page()
    elif ui_splash: ui_splash.render_splash_page()

if __name__ == "__main__":
    main()