import streamlit as st
import time
import os
import logging

# --- LOGGING SETUP ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="VerbaPost",
    page_icon="📮",
    layout="centered",
    initial_sidebar_state="collapsed",
    menu_items={
        'Get Help': 'mailto:support@verbapost.com',
        'About': "# VerbaPost \n Send real mail from your screen."
    }
)

# --- CSS STYLING ---
st.markdown("""
<style>
    [data-testid="stSidebarNav"] {display: none !important;}
    .block-container {padding-top: 1rem !important;}
    button[kind="primary"] {
        background-color: #d93025 !important;
        border-color: #d93025 !important;
        color: white !important; 
        font-weight: 600;
    }
    .success-box {
        background-color: #ecfdf5; 
        border: 1px solid #10b981; 
        padding: 20px; 
        border-radius: 10px; 
        text-align: center;
        margin-bottom: 20px;
    }
    .success-title { color: #047857; font-size: 24px; font-weight: bold; margin-bottom: 10px; }
</style>
""", unsafe_allow_html=True)

# --- LAZY MODULE LOADER ---
def get_module(module_name):
    try:
        if module_name == "ui_splash": import ui_splash as m; return m
        if module_name == "ui_login": import ui_login as m; return m
        if module_name == "ui_main": import ui_main as m; return m
        if module_name == "ui_admin": import ui_admin as m; return m
        if module_name == "ui_legacy": import ui_legacy as m; return m
        if module_name == "ui_heirloom": import ui_heirloom as m; return m
        if module_name == "payment_engine": import payment_engine as m; return m
        if module_name == "email_engine": import email_engine as m; return m
        if module_name == "audit_engine": import audit_engine as m; return m
        if module_name == "auth_engine": import auth_engine as m; return m
        if module_name == "seo_injector": import seo_injector as m; return m
        if module_name == "analytics": import analytics as m; return m
        if module_name == "mailer": import mailer as m; return m
        if module_name == "letter_format": import letter_format as m; return m
        if module_name == "address_standard": import address_standard as m; return m
        if module_name == "database": import database as m; return m
    except Exception as e:
        logger.error(f"Failed to load {module_name}: {e}")
        return None

# --- SECRET MANAGER IMPORT ---
try: import secrets_manager
except Exception: secrets_manager = None

# --- MAIN LOGIC ---
def main():
    # --- SYSTEM HEALTH CHECK ---
    import module_validator
    is_healthy, error_log = module_validator.validate_critical_modules()
    if not is_healthy:
        st.error("🚨 SYSTEM CRITICAL FAILURE")
        st.stop()

    # 1. SEO & ANALYTICS
    seo = get_module("seo_injector")
    if seo: seo.inject_meta()
    analytics = get_module("analytics")
    if analytics: analytics.inject_ga()

    params = st.query_params

    # 2. ADMIN BACKDOOR
    if params.get("view") == "admin":
        st.session_state.app_mode = "admin"

    # 3. HANDLE PAYMENT RETURN
    if "session_id" in params:
        session_id = params["session_id"]
        pay_eng = get_module("payment_engine")
        db = get_module("database")
        
        status = "error"
        result = {}
        user_email = st.session_state.get("user_email")
        
        if pay_eng:
            try:
                raw_obj = pay_eng.verify_session(session_id)
                if hasattr(raw_obj, 'payment_status') and (raw_obj.payment_status == 'paid' or raw_obj.status == 'complete'):
                    status = "paid"
                    result = raw_obj
                    if not user_email: user_email = raw_obj.customer_email
            except Exception as e:
                logger.error(f"Verify Error: {e}")

        if status == "paid":
            # Record Transaction (Idempotency)
            if db: db.record_stripe_fulfillment(session_id)
            
            # UNLOCK WORKSPACE LOGIC
            st.session_state.authenticated = True
            st.session_state.user_email = user_email
            
            # Initialize variables safely to prevent NameError
            meta_id = None
            ref_id = getattr(result, 'client_reference_id', '')
            
            if hasattr(result, 'metadata') and result.metadata:
                meta_id = result.metadata.get('draft_id', '')

            # SUBSCRIPTION PATH
            is_subscription = (ref_id == "SUBSCRIPTION_INIT") or (meta_id == "SUBSCRIPTION_INIT")
            if is_subscription:
                if db and user_email: db.update_user_credits(user_email, 4)
                st.query_params.clear()
                st.success("Archive Unlocked!"); st.balloons()
                if st.button("Enter Archive"): st.session_state.app_mode = "heirloom"; st.rerun()
                return

            # LETTER PATH (Correct Pay-First Logic)
            paid_tier = "Standard"
            if db and meta_id:
                try:
                    with db.get_db_session() as s:
                        d = s.query(db.LetterDraft).filter(db.LetterDraft.id == meta_id).first()
                        if d: 
                            paid_tier = d.tier
                            # CRITICAL: Mark as Paid so user can resume if browser closes
                            d.status = "Paid/Writing"
                            s.commit()
                except Exception as e:
                    logger.error(f"DB Update Error: {e}")
            
            st.session_state.paid_tier = paid_tier
            st.session_state.current_draft_id = meta_id
            st.session_state.app_mode = "workspace" # SEND USER TO WRITE, DO NOT MAIL YET
            
            st.query_params.clear()
            st.rerun()

    # 4. PASSWORD RESET
    elif params.get("type") == "recovery":
        st.session_state.app_mode = "login"

    # 5. INIT STATE
    if "app_mode" not in st.session_state:
        st.session_state.app_mode = "splash"
        
    mode = st.session_state.app_mode
    current_email = st.session_state.get("user_email")

    # 6. SIDEBAR
    with st.sidebar:
        st.header("VerbaPost System")
        if st.button("✉️ Write a Letter", use_container_width=True):
            st.query_params.clear()
            st.session_state.app_mode = "store"
            st.rerun()
            
        if st.button("🕊️ Legacy Service", use_container_width=True):
            st.query_params.clear()
            st.session_state.app_mode = "legacy"
            st.rerun()
            
        if st.button("📚 Family Stories", use_container_width=True):
            st.query_params.clear()
            st.session_state.app_mode = "heirloom"
            st.rerun()
        st.markdown("---")
        
        is_admin = st.session_state.get("admin_authenticated", False)
        if secrets_manager:
            admin_email = secrets_manager.get_secret("admin.email")
            if is_admin or (current_email and admin_email and current_email.strip() == admin_email.strip()):
                 if st.button("🔒 Account Settings", use_container_width=True):
                    st.session_state.app_mode = "admin"
                    st.rerun()

    if mode == "splash": m = get_module("ui_splash"); m.render_splash_page() if m else None
    elif mode == "login": m = get_module("ui_login"); m.render_login_page() if m else None
    elif mode == "store": m = get_module("ui_main"); m.render_store_page() if m else None
    elif mode == "workspace": m = get_module("ui_main"); m.render_workspace_page() if m else None
    elif mode == "heirloom": m = get_module("ui_heirloom"); m.render_dashboard() if m else None
    elif mode == "admin": m = get_module("ui_admin"); m.render_admin_page() if m else None
    elif mode == "legacy": m = get_module("ui_legacy"); m.render_legacy_page() if m else None
    else: m = get_module("ui_splash"); m.render_splash_page() if m else None

if __name__ == "__main__":
    main()