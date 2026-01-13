import streamlit as st

# --- VERSION CONTROL ---
VERSION = "4.3.2"  # OAuth Debug Build

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

# --- 2. DEBUGGING OAUTH BRIDGE ---
# This version includes a visual 'Debug Console' inside the iframe to catch SecurityErrors
components.html(
    """
    <div id="debug-log" style="font-family:monospace; font-size:10px; color:#ef4444; background:#fee2e2; border:1px solid #f87171; padding:10px; border-radius:4px; display:none;">
        <strong>VerbaPost Auth Debug:</strong> <span id="debug-msg">Initializing...</span>
    </div>
    <script>
    (function() {
        const logger = (msg, isError=false) => {
            console.log(msg);
            const el = document.getElementById('debug-log');
            const msgEl = document.getElementById('debug-msg');
            el.style.display = 'block';
            msgEl.innerText = msg;
            if(isError) el.style.background = '#fecaca';
        };

        try {
            const topWin = window.top;
            const hash = topWin.location.hash;
            const origin = topWin.location.origin;
            
            logger("Checking URL Fragment... Origin: " + origin);

            if (hash && hash.includes('access_token=')) {
                logger("Token detected. Processing redirect...");
                
                const params = new URLSearchParams(hash.substring(1));
                const accessToken = params.get('access_token');
                
                if (accessToken) {
                    const url = new URL(topWin.location.origin + topWin.location.pathname);
                    url.searchParams.set('access_token', accessToken);
                    
                    logger("Attempting Top-Level Navigation to: " + url.pathname);
                    
                    try {
                        topWin.location.href = url.toString();
                    } catch (navErr) {
                        logger("REDIRECT BLOCKED BY BROWSER: " + navErr.message, true);
                        document.body.innerHTML = `
                            <div style="font-family:sans-serif; text-align:center; padding-top:10px;">
                                <div style="color:#ef4444; font-size:12px; margin-bottom:10px;">Security Lock: Click below to enter portal</div>
                                <a href="${url.toString()}" target="_top" style="
                                    background-color:#0f172a; color:white; padding:12px 24px; 
                                    text-decoration:none; border-radius:6px; font-weight:600; display:inline-block;">
                                    Confirm & Enter Dashboard &rarr;
                                </a>
                            </div>
                        `;
                    }
                }
            } else {
                // No token found, but we want to log the state
                if(hash) logger("Hash present but no token: " + hash.substring(0, 20) + "...");
            }
        } catch (e) {
            logger("CRITICAL BRIDGE ERROR: " + e.message, true);
        }
    })();
    </script>
    """,
    height=80,
)

# --- 3. MODULE IMPORTS (REMAINDER PRESERVED) ---
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
# 🛠️ HELPER FUNCTIONS (PRESERVED)
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
    query_params = st.query_params
    access_token = query_params.get("access_token")
    
    if access_token and not st.session_state.get("authenticated"):
        if auth_engine:
            logger.info("🔐 OAuth token detected - Processing...")
            with st.spinner("🔄 Verifying..."):
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
                    st.error(f"❌ Auth Error: {err}")
                    if st.button("Back to Login"):
                        st.query_params.clear()
                        st.session_state.app_mode = "login"
                        st.rerun()
                    st.stop()

    if module_validator and not st.session_state.get("system_verified"):
        health = module_validator.run_preflight_checks()
        if not health["status"]:
            st.error("⚠️ System config error. Check logs.")
            st.stop()
        st.session_state.system_verified = True

    if "authenticated" not in st.session_state: st.session_state.authenticated = False
    if "user_email" not in st.session_state: st.session_state.user_email = None
    if "user_role" not in st.session_state: st.session_state.user_role = "user"
        
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