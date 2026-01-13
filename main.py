import streamlit as st
import sys
import os

# --- 🏷️ VERSION CONTROL ---
# Increment this constant at every functional update to this file.
VERSION = "4.5.1"  # Restored Auth Bridge + QR Fix

# --- 1. CRITICAL: CONFIG MUST BE THE FIRST COMMAND ---
st.set_page_config(
    page_title=f"VerbaPost Wealth v{VERSION}", 
    page_icon="🛡️", 
    layout="centered",
    initial_sidebar_state="collapsed" 
)

# --- 2. PATH INJECTION (FIXES KEYERROR: 'DATABASE') ---
# Ensures local modules are visible even during production environment transitions.
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
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# --- 3. HARDENED OAUTH BRIDGE WITH SANDBOX ESCAPE ---
# Updated to resolve the 'about:srcdoc' sandbox warning from your logs.
# NOTE: Kept as fallback, but PKCE (Step 0 below) is now the primary method.
components.html(
    """
    <div id="bridge-debug" style="font-family:monospace; font-size:11px; color:#1e293b; background:#f1f5f9; border:1px solid #cbd5e1; padding:8px; border-radius:4px; display:none; margin-bottom:10px;">
        <strong>Auth Bridge Status:</strong> <span id="debug-msg">Initializing...</span>
    </div>
    <script>
    (function() {
        const log = (msg) => {
            console.log("VerbaPost Bridge:", msg);
            const el = document.getElementById('bridge-debug');
            const msgEl = document.getElementById('debug-msg');
            el.style.display = 'block';
            msgEl.innerText = msg;
        };

        // Safety Timeout: If nothing happens in 3 seconds, show a manual recovery link
        setTimeout(() => {
            const el = document.getElementById('bridge-debug');
            if (el.style.display === 'none') {
                log("Bridge Timeout. If you are stuck, please refresh the page.");
            }
        }, 3000);

        try {
            // Accessing the top-most window to capture the OAuth fragment
            const topWin = window.top || window.parent;
            const hash = topWin.location.hash;
            
            if (hash && hash.includes('access_token=')) {
                log("Token found in URL fragment. Escaping sandbox...");
                
                const params = new URLSearchParams(hash.substring(1));
                const accessToken = params.get('access_token');
                const refreshToken = params.get('refresh_token');
                
                if (accessToken) {
                    const cleanUrl = topWin.location.origin + topWin.location.pathname;
                    let finalUrl = cleanUrl + '?access_token=' + encodeURIComponent(accessToken);
                    if (refreshToken) finalUrl += '&refresh_token=' + encodeURIComponent(refreshToken);

                    log("Redirecting to top-level window...");
                    
                    // Attempting multiple breakout methods to bypass 'about:srcdoc' restrictions
                    try {
                        topWin.location.href = finalUrl;
                    } catch (e) {
                        window.open(finalUrl, "_top");
                    }
                }
            } else {
                log("No token in fragment. Ready.");
            }
        } catch (e) {
            log("SANDBOX BLOCK: " + e.message + ". Manual interaction may be required.");
        }
    })();
    </script>
    """,
    height=100,
)

# --- 4. MODULE IMPORTS (FULL ROBUST WRAPPING) ---
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
# 🛠️ HELPER FUNCTIONS (FULL RESTORATION)
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
    # --- STEP 0: PKCE AUTH LISTENER (NEW) ---
    # Catches the ?code=... from Google/Supabase
    if "code" in st.query_params:
        auth_code = st.query_params["code"]
        
        # Prevent double-processing
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
                        
                        # Clear URL to prevent refresh loops
                        st.query_params.clear()
                        st.rerun()
                    else:
                        st.error(f"Login Failed: {err}")
                        st.session_state.auth_processing = False
                else:
                    st.error("Auth Engine Missing")

    # --- STEP 1: OAUTH TOKEN INTERCEPTOR (LEGACY IMPLICIT) ---
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
                    
                    st.query_params.clear()
                    st.rerun()
                else:
                    st.error(f"❌ Auth Error: {err}")
                    if st.button("Return to Login"):
                        st.query_params.clear()
                        st.session_state.app_mode = "login"
                        st.rerun()
                    st.stop()

    # --- STEP 2: SYSTEM HEALTH PRE-FLIGHT ---
    if module_validator and not st.session_state.get("system_verified"):
        health = module_validator.run_preflight_checks()
        if not health["status"]:
            st.error("⚠️ System configuration error. See Details Below.")
            st.json(health.get("details", {"error": "Missing critical secrets or modules."}))
            st.stop()
        st.session_state.system_verified = True

    # --- STEP 3: INITIALIZE SESSION STATE DEFAULTS ---
    if "authenticated" not in st.session_state: st.session_state.authenticated = False
    if "user_email" not in st.session_state: st.session_state.user_email = None
    if "user_role" not in st.session_state: st.session_state.user_role = "user"
        
    # --- STEP 4: APP MODE ROUTING (UPDATED FOR QR) ---
    nav = query_params.get("nav")
    project_id = query_params.get("id")
    
    # 🔥 QR CODE HANDLER 🔥
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
        
        elif nav == "legal": st.session_state.app_mode = "legal"
        elif nav == "blog": st.session_state.app_mode = "blog"
        elif nav == "partner": st.session_state.app_mode = "partner"
        elif nav == "setup": st.session_state.app_mode = "setup"
        elif nav == "archive": st.session_state.app_mode = "archive"
        elif nav == "login": st.session_state.app_mode = "login"
        elif nav == "heirloom": st.session_state.app_mode = "heirloom"
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
            if st.button("🚪 Sign Out", use_container_width=True): handle_logout()

    # --- STEP 6: ROUTE TO VIEW ---
    mode = st.session_state.app_mode
    if mode == "admin" and ui_admin: ui_admin.render_admin_page()
    
    # 🔥 QR CODE VIEWER 🔥
    # Passes 'project_id' (which is the Play ID) to the archive viewer
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
    else:
        # Emergency Routing Recovery
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