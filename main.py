import streamlit as st
import sys
import os
import logging
import time

# --- 🏷️ VERSION CONTROL ---
VERSION = "5.1.1" 

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

# --- 3. LOGGING ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- 4. HARDENED IMPORTS (Prevents KeyError/Crash Loop) ---
try: import ui_splash
except Exception: ui_splash = None

try: import ui_login
except Exception: ui_login = None

try: import ui_heirloom
except Exception: ui_heirloom = None

try: import ui_advisor
except Exception: ui_advisor = None

try: import ui_admin
except Exception: ui_admin = None

# Static Pages
try: import ui_legal
except Exception: ui_legal = None
try: import ui_blog
except Exception: ui_blog = None
try: import ui_partner
except Exception: ui_partner = None

# Engines
try: import auth_engine
except Exception: auth_engine = None
try: import database
except Exception: database = None
try: import secrets_manager
except Exception: secrets_manager = None
try: import module_validator
except Exception: module_validator = None
try: import ui_archive
except Exception: ui_archive = None
try: import payment_engine 
except Exception: payment_engine = None
try: import audit_engine # <--- NEW IMPORT
except Exception: audit_engine = None

# --- 5. ROUTER LOGIC ---
def main():
    # A. PRE-FLIGHT
    if module_validator and not st.session_state.get("system_verified"):
        try:
            health = module_validator.run_preflight_checks()
            if not health["status"]: 
                st.error("System Error: Modules missing.")
                st.stop()
            st.session_state.system_verified = True
        except Exception: 
            st.session_state.system_verified = True

    # B. SESSION INIT
    if "authenticated" not in st.session_state: st.session_state.authenticated = False
    if "app_mode" not in st.session_state: st.session_state.app_mode = "splash"

    # C. URL PARAMS & CALLBACKS
    params = st.query_params
    
    # 1. PLAYBACK GATE (QR CODE)
    if "play" in params:
        pid = params.get("play")
        if ui_archive:
            ui_archive.render_heir_vault(pid)
            return

    # 2. QR CODE SCAN (Archive View - Legacy)
    if ("project_id" in params or "id" in params) and ui_archive:
        pid = params.get("project_id") or params.get("id")
        ui_archive.render_heir_vault(pid)
        return

    # 3. GOOGLE AUTH (PKCE)
    if "code" in params:
        code = params["code"]
        if auth_engine and database:
            user, err = auth_engine.exchange_code_for_user(code)
            
            if user:
                profile = database.get_user_profile(user.email)
                st.session_state.authenticated = True
                st.session_state.user_email = user.email
                
                # AUDIT LOG
                if audit_engine:
                    audit_engine.log_event(user.email, "Google Login", metadata={"role": profile.get('role')})

                if profile.get('role') == 'advisor':
                    st.session_state.app_mode = "advisor"
                else:
                    st.session_state.app_mode = "heirloom"
                
                st.query_params.clear()
                st.rerun()

    # 4. STRIPE PAYMENT RETURN
    if "session_id" in params:
        session_id = params["session_id"]
        if payment_engine and database:
            with st.spinner("Verifying secure payment..."):
                if database.is_fulfillment_recorded(session_id):
                    st.warning("Transaction already processed.")
                    time.sleep(2)
                    st.query_params.clear()
                    st.rerun()
                else:
                    session = payment_engine.verify_session(session_id)
                    if session and session.payment_status == 'paid':
                        user_email = session.metadata.get('user_email')
                        if user_email:
                            database.add_advisor_credit(user_email, 1) 
                            database.record_stripe_fulfillment(session_id, "Advisor Credit", user_email)
                            
                            # AUDIT LOG
                            if audit_engine:
                                audit_engine.log_event(user_email, "Payment Verified", metadata={"session": session_id, "item": "Advisor Credit"})

                            st.balloons()
                            st.success("Payment Successful! Credit added.")
                            st.session_state.authenticated = True
                            st.session_state.user_email = user_email
                            st.session_state.app_mode = "advisor"
                            time.sleep(2)
                            st.query_params.clear()
                            st.rerun()

    # 5. LANDING PAGE ROUTING (?nav=...)
    if "nav" in params:
        nav_target = params["nav"]
        if "nav_processed" not in st.session_state:
            if nav_target == "login": st.session_state.app_mode = "login"
            elif nav_target == "archive": st.session_state.app_mode = "login" 
            elif nav_target == "legal": st.session_state.app_mode = "legal"
            elif nav_target == "blog": st.session_state.app_mode = "blog"
            st.session_state.nav_processed = True
            st.query_params.clear()
            st.rerun()

    # D. SIDEBAR NAV
    if st.session_state.authenticated:
        with st.sidebar:
            st.caption(f"VerbaPost v{VERSION}")
            
            if st.button("🚪 Sign Out"):
                # AUDIT LOG (Logout)
                if audit_engine:
                    audit_engine.log_event(st.session_state.get("user_email", "unknown"), "Logout")
                st.session_state.clear()
                st.rerun()
            
            user = st.session_state.get("user_email", "")
            
            is_admin = "admin" in user or \
                       (secrets_manager and user == secrets_manager.get_secret("admin.email")) or \
                       user == "tjkarat@gmail.com"
            
            if is_admin:
                st.divider()
                st.markdown("**Role Switcher**")
                
                if st.button("⚙️ Admin Console"): 
                    st.session_state.app_mode = "admin"
                    st.rerun()
                
                if st.button("👔 Advisor Portal"): 
                    st.session_state.app_mode = "advisor"
                    st.rerun()
                    
                if st.button("📂 Family Archive"): 
                    st.session_state.app_mode = "heirloom"
                    st.rerun()

    # E. VIEW CONTROLLER
    mode = st.session_state.app_mode

    if mode in ["heirloom", "advisor", "admin"]:
        if not st.session_state.authenticated:
            st.session_state.app_mode = "login"
            st.rerun()
            
        if mode == "heirloom" and ui_heirloom: ui_heirloom.render_dashboard()
        elif mode == "advisor" and ui_advisor: ui_advisor.render_dashboard()
        elif mode == "admin" and ui_admin: ui_admin.render_admin_page()
    
    elif mode == "legal" and ui_legal: ui_legal.render_legal_page()
    elif mode == "blog" and ui_blog: ui_blog.render_blog_page()
    elif mode == "partner" and ui_partner: ui_partner.render_partner_page()

    elif mode == "login" and ui_login: ui_login.render_login_page()
    
    else:
        if ui_splash: ui_splash.render_splash_page()
        else: st.write("Loading...")

if __name__ == "__main__":
    main()