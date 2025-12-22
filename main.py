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
    menu_items={'Get Help': 'mailto:support@verbapost.com'}
)

st.markdown("""
<style>
    [data-testid="stSidebarNav"] {display: none !important;}
    .block-container {padding-top: 1rem !important;}
    button[kind="primary"] { background-color: #d93025 !important; border-color: #d93025 !important; color: white !important; font-weight: 600; }
    .success-box { background-color: #ecfdf5; border: 1px solid #10b981; padding: 20px; border-radius: 10px; text-align: center; margin-bottom: 20px; }
    .success-title { color: #047857; font-size: 24px; font-weight: bold; margin-bottom: 10px; }
    .tracking-code { font-family: monospace; font-size: 20px; color: #d93025; background: #fff; padding: 5px 10px; border-radius: 4px; border: 1px dashed #ccc;}
</style>
""", unsafe_allow_html=True)

def get_module(module_name):
    try:
        if module_name == "ui_splash": import ui_splash as m; return m
        if module_name == "ui_login": import ui_login as m; return m
        if module_name == "ui_main": import ui_main as m; return m
        if module_name == "ui_admin": import ui_admin as m; return m
        if module_name == "ui_legacy": import ui_legacy as m; return m
        if module_name == "ui_heirloom": import ui_heirloom as m; return m
        if module_name == "payment_engine": import payment_engine as m; return m
        if module_name == "database": import database as m; return m
        if module_name == "analytics": import analytics as m; return m
        if module_name == "seo_injector": import seo_injector as m; return m
    except: return None

try: import secrets_manager
except: secrets_manager = None

def main():
    import module_validator
    is_healthy, _ = module_validator.validate_critical_modules()
    if not is_healthy: st.error("🚨 System Failure"); st.stop()

    # ANALYTICS
    seo = get_module("seo_injector")
    if seo: seo.inject_meta()
    analytics = get_module("analytics")
    if analytics: analytics.inject_ga()

    params = st.query_params
    if params.get("view") == "admin": st.session_state.app_mode = "admin"

    if "session_id" in params:
        session_id = params["session_id"]
        pay_eng = get_module("payment_engine")
        db = get_module("database")
        status = "error"
        user_email = st.session_state.get("user_email")
        
        if pay_eng:
            try:
                obj = pay_eng.verify_session(session_id)
                if obj and (obj.payment_status == 'paid' or obj.status == 'complete'):
                    status = "paid"
                    if not user_email: user_email = obj.customer_email
            except: pass

        if status == "paid":
            if db: db.record_stripe_fulfillment(session_id)
            st.session_state.authenticated = True
            st.session_state.user_email = user_email
            
            # LETTER PATH
            paid_tier = "Standard"
            meta_id = None
            if hasattr(obj, 'metadata') and obj.metadata: meta_id = obj.metadata.get('draft_id')
            
            if db and meta_id:
                try:
                    with db.get_db_session() as s:
                        d = s.query(db.LetterDraft).filter(db.LetterDraft.id == meta_id).first()
                        if d: 
                            paid_tier = d.tier
                            d.status = "Paid/Writing"
                            s.commit()
                except: pass
            
            st.session_state.paid_tier = paid_tier
            st.session_state.current_draft_id = meta_id
            st.session_state.app_mode = "workspace"
            st.query_params.clear()
            st.rerun()

    # --- ROUTING ---
    if "app_mode" not in st.session_state: st.session_state.app_mode = "splash"
    mode = st.session_state.app_mode
    
    with st.sidebar:
        st.header("VerbaPost")
        if st.button("✉️ Write Letter"): st.session_state.app_mode = "store"; st.rerun()
        if st.button("🕊️ Legacy"): st.session_state.app_mode = "legacy"; st.rerun()
        if st.button("📚 Family"): st.session_state.app_mode = "heirloom"; st.rerun()
        st.markdown("---")
        if st.button("🔒 Admin"): st.session_state.app_mode = "admin"; st.rerun()

    if mode == "splash": m = get_module("ui_splash"); m.render_splash_page() if m else None
    elif mode == "login": m = get_module("ui_login"); m.render_login_page() if m else None
    elif mode == "store": m = get_module("ui_main"); m.render_store_page() if m else None
    elif mode == "workspace": m = get_module("ui_main"); m.render_workspace_page() if m else None
    elif mode == "receipt": m = get_module("ui_main"); m.render_receipt_page() if m else None
    elif mode == "heirloom": m = get_module("ui_heirloom"); m.render_dashboard() if m else None
    elif mode == "admin": m = get_module("ui_admin"); m.render_admin_page() if m else None
    elif mode == "legacy": m = get_module("ui_legacy"); m.render_legacy_page() if m else None
    else: m = get_module("ui_splash"); m.render_splash_page() if m else None

if __name__ == "__main__":
    main()