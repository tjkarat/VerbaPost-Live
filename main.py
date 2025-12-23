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
    .tracking-code { font-family: monospace; font-size: 20px; color: #d93025; background: #fff; padding: 5px 10px; border-radius: 4px; border: 1px dashed #ccc;}
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
        if module_name == "ui_legal": import ui_legal as m; return m
        if module_name == "payment_engine": import payment_engine as m; return m
        if module_name == "database": import database as m; return m
        if module_name == "analytics": import analytics as m; return m
        if module_name == "seo_injector": import seo_injector as m; return m
    except Exception as e:
        logger.error(f"Failed to load {module_name}: {e}")
        return None

try: import secrets_manager
except Exception: secrets_manager = None

# --- MAIN LOGIC ---
def main():
    import module_validator
    is_healthy, error_log = module_validator.validate_critical_modules()
    if not is_healthy:
        st.error("🚨 SYSTEM CRITICAL FAILURE")
        st.stop()

    seo = get_module("seo_injector")
    if seo: seo.inject_meta()
    analytics = get_module("analytics")
    if analytics: analytics.inject_ga()

    params = st.query_params

    if params.get("view") == "admin":
        st.session_state.app_mode = "admin"

    if "session_id" in params:
        session_id = params["session_id"]
        db = get_module("database")
        
        # FIXED: IDEMPOTENCY-FIRST CHECK
        if db and hasattr(db, "record_stripe_fulfillment"):
            if not db.record_stripe_fulfillment(session_id):
                st.warning("⚠️ This payment has already been processed.")
                st.query_params.clear()
                return

        pay_eng = get_module("payment_engine")
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
            st.session_state.authenticated = True
            st.session_state.user_email = user_email
            
            meta_id = None
            ref_id = getattr(result, 'client_reference_id', '')
            if hasattr(result, 'metadata') and result.metadata:
                meta_id = result.metadata.get('draft_id', '')

            is_annual = (ref_id == "SUBSCRIPTION_INIT") or (meta_id == "SUBSCRIPTION_INIT")
            if is_annual:
                if db and user_email: db.update_user_credits(user_email, 48)
                st.query_params.clear()
                st.success("Annual Pass Activated!"); st.balloons()
                if st.button("Enter Archive"): st.session_state.app_mode = "heirloom"; st.rerun()
                return

            paid_tier = "Standard"
            if db and meta_id:
                try:
                    with db.get_db_session() as s:
                        d = s.query(db.LetterDraft).filter(db.LetterDraft.id == meta_id).first()
                        if d: 
                            paid_tier = d.tier
                            d.status = "Paid/Writing"
                            s.commit()
                except Exception as e:
                    logger.error(f"DB Update Error: {e}")
            
            st.session_state.paid_tier = paid_tier
            st.session_state.current_draft_id = meta_id
            st.session_state.app_mode = "main" # Standard redirect
            st.query_params.clear()
            st.rerun()

    if "app_mode" not in st.session_state:
        st.session_state.app_mode = "splash"
        
    mode = st.session_state.app_mode

    with st.sidebar:
        st.header("VerbaPost System")
        if st.button("✉️ Write a Letter", use_container_width=True):
            st.query_params.clear()
            st.session_state.app_mode = "main"; st.rerun()
        if st.button("📚 Family Archive", use_container_width=True):
            st.query_params.clear()
            st.session_state.app_mode = "heirloom"; st.rerun()
        st.markdown("---")
        if st.button("🔒 Account Settings", use_container_width=True):
            st.session_state.app_mode = "admin"; st.rerun()

    # --- FULL ROUTING LOGIC (RESTORED) ---
    m = get_module(f"ui_{mode}")
    if m:
        if mode == "splash" and hasattr(m, "render_splash_page"):
            m.render_splash_page()
        elif mode == "login" and hasattr(m, "render_login_page"):
            m.render_login_page()
        # ROUTER ALIGNMENT
        elif mode == "main" and hasattr(m, "render_store_page"):
            m.render_store_page()
        elif mode == "workspace" and hasattr(m, "render_workspace_page"):
            m.render_workspace_page()
        elif mode == "heirloom" and hasattr(m, "render_dashboard"):
            m.render_dashboard()
        elif mode == "admin" and hasattr(m, "render_admin_page"):
            m.render_admin_page()
        elif mode == "legacy" and hasattr(m, "render_legacy_page"):
            m.render_legacy_page()
        elif mode == "legal" and hasattr(m, "render_legal_page"):
            m.render_legal_page()
        elif mode == "receipt" and hasattr(m, "render_receipt_page"):
            m.render_receipt_page()
    else:
        m_splash = get_module("ui_splash")
        if m_splash:
            m_splash.render_splash_page()

if __name__ == "__main__":
    main()