import streamlit as st
import sys
import os
import logging
import time

# --- 🏷️ VERSION CONTROL ---
VERSION = "5.0.2" # B2B Payment Integration

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

# --- 3. IMPORTS ---
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
try: import ui_archive
except ImportError: ui_archive = None
try: import payment_engine 
except ImportError: payment_engine = None

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

    # C. URL PARAMS & CALLBACKS
    params = st.query_params
    
    # 1. QR CODE SCAN (Archive View)
    if ("project_id" in params or "id" in params) and ui_archive:
        pid = params.get("project_id") or params.get("id")
        ui_archive.render_heir_vault(pid)
        return

    # 2. GOOGLE AUTH (PKCE)
    if "code" in params:
        code = params["code"]
        if auth_engine:
            user, err = auth_engine.exchange_code_for_user(code)
            if user:
                st.session_state.authenticated = True
                st.session_state.user_email = user.email
                # Smart Route: Check if advisor
                profile = database.get_user_profile(user.email)
                if profile.get('role') == 'advisor':
                    st.session_state.app_mode = "advisor"
                else:
                    st.session_state.app_mode = "heirloom"
                st.query_params.clear()
                st.rerun()

    # 3. STRIPE PAYMENT RETURN
    if "session_id" in params:
        session_id = params["session_id"]
        if payment_engine and database:
            with st.spinner("Verifying secure payment..."):
                # 1. Idempotency Check (Prevent double-crediting)
                if database.is_fulfillment_recorded(session_id):
                    st.warning("Transaction already processed.")
                    time.sleep(2)
                    st.query_params.clear()
                    st.rerun()
                else:
                    # 2. Verify with Stripe
                    session = payment_engine.verify_session(session_id)
                    if session and session.payment_status == 'paid':
                        user_email = session.metadata.get('user_email')
                        
                        # 3. Credit the Advisor
                        if user_email:
                            # We assume the metadata contains intent='advisor_credit' or similar
                            # For B2B, we blindly credit 1 unit per successful session for now
                            database.add_advisor_credit(user_email, 1) 
                            database.record_stripe_fulfillment(session_id, "Advisor Credit", user_email)
                            
                            st.balloons()
                            st.success("Payment Successful! Credit added to your firm.")
                            st.session_state.authenticated = True
                            st.session_state.user_email = user_email
                            st.session_state.app_mode = "advisor"
                            time.sleep(2)
                            st.query_params.clear()
                            st.rerun()
                    else:
                        st.error("Payment verification failed.")

    # D. SIDEBAR NAV
    if st.session_state.authenticated:
        with st.sidebar:
            st.caption(f"VerbaPost v{VERSION}")
            if st.button("🚪 Sign Out"):
                st.session_state.clear()
                st.rerun()
            
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
    
    # 2. Public Static Routes
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