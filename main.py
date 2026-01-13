import streamlit as st
import sys
import os
import logging

# --- 🏷️ VERSION CONTROL ---
VERSION = "5.0.0" # B2B Concierge Pivot

# --- 1. CONFIG ---
st.set_page_config(
    page_title=f"VerbaPost | Family Archive", 
    page_icon="🛡️", 
    layout="centered",
    initial_sidebar_state="collapsed" 
)

# --- 2. PATHS ---
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path: sys.path.append(current_dir)

# --- 3. IMPORTS (CLEAN LIST) ---
try: import ui_splash
except ImportError: ui_splash = None
try: import ui_login
except ImportError: ui_login = None
try: import ui_heirloom
except ImportError: ui_heirloom = None
try: import ui_advisor
except ImportError: ui_advisor = None
try: import ui_admin
except ImportError: ui_admin = None

# --- RESTORED IMPORTS FOR STATIC PAGES ---
try: import ui_legal
except ImportError: ui_legal = None
try: import ui_blog
except ImportError: ui_blog = None
try: import ui_partner
except ImportError: ui_partner = None

try: import auth_engine
except ImportError: auth_engine = None
try: import database
except ImportError: database = None
try: import secrets_manager
except ImportError: secrets_manager = None
try: import module_validator
except ImportError: module_validator = None
try: import ui_archive # Hook for QR codes
except ImportError: ui_archive = None

# --- 4. LOGGING ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- 5. ROUTER LOGIC ---
def main():
    # A. PRE-FLIGHT
    if module_validator and not st.session_state.get("system_verified"):
        health = module_validator.run_preflight_checks()
        if not health["status"]: st.error("System Error: Modules missing."); st.stop()
        st.session_state.system_verified = True

    # B. SESSION INIT
    if "authenticated" not in st.session_state: st.session_state.authenticated = False
    if "app_mode" not in st.session_state: st.session_state.app_mode = "splash"

    # C. URL PARAMS & AUTH CALLBACKS
    params = st.query_params
    
    # 1. QR CODE SCAN (Archive View)
    if ("project_id" in params or "id" in params) and ui_archive:
        pid = params.get("project_id") or params.get("id")
        ui_archive.render_heir_vault(pid)
        return # Stop processing to show only the vault

    # 2. PKCE Callback (Google Auth)
    if "code" in params:
        code = params["code"]
        if auth_engine:
            user, err = auth_engine.exchange_code_for_user(code)
            if user:
                st.session_state.authenticated = True
                st.session_state.user_email = user.email
                st.session_state.app_mode = "heirloom"
                st.query_params.clear()
                st.rerun()
    
    # D. SIDEBAR NAV
    if st.session_state.authenticated:
        with st.sidebar:
            st.caption(f"VerbaPost v{VERSION}")
            if st.button("🚪 Sign Out"):
                st.session_state.clear()
                st.rerun()
            
            # Admin/Advisor Backdoors
            user = st.session_state.get("user_email", "")
            if "admin" in user or (secrets_manager and user == secrets_manager.get_secret("admin.email")):
                st.divider()
                if st.button("⚙️ Admin Console"): st.session_state.app_mode = "admin"; st.rerun()
                if st.button("👔 Advisor Portal"): st.session_state.app_mode = "advisor"; st.rerun()

    # E. VIEW CONTROLLER
    mode = st.session_state.app_mode

    # 1. Protected Routes (Login Required)
    if mode in ["heirloom", "advisor", "admin"]:
        if not st.session_state.authenticated:
            st.session_state.app_mode = "login"
            st.rerun()
            
        if mode == "heirloom" and ui_heirloom: ui_heirloom.render_dashboard()
        elif mode == "advisor" and ui_advisor: ui_advisor.render_dashboard()
        elif mode == "admin" and ui_admin: ui_admin.render_admin_page()
    
    # 2. Public Static Routes (RESTORED)
    elif mode == "legal" and ui_legal: ui_legal.render_legal_page()
    elif mode == "blog" and ui_blog: ui_blog.render_blog_page()
    elif mode == "partner" and ui_partner: ui_partner.render_partner_page()

    # 3. Auth Routes
    elif mode == "login" and ui_login: ui_login.render_login_page()
    
    # 4. Default / Splash
    else:
        if ui_splash: ui_splash.render_splash_page()
        else: st.write("Loading...")

if __name__ == "__main__":
    main()