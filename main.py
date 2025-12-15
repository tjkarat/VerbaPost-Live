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
        'Report a bug': "mailto:support@verbapost.com",
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
    .stStatusWidget {border: 1px solid #e0e0e0; border-radius: 8px; padding: 15px;}
</style>
""", unsafe_allow_html=True)

# --- HELPER: LAZY MODULE LOADER ---
# This prevents the "Torch/AI" crash from breaking the Payment/Splash screens.
def get_module(module_name):
    try:
        if module_name == "ui_splash": import ui_splash as m; return m
        if module_name == "ui_login": import ui_login as m; return m
        if module_name == "ui_main": import ui_main as m; return m
        if module_name == "ui_admin": import ui_admin as m; return m
        if module_name == "ui_legal": import ui_legal as m; return m
        if module_name == "ui_legacy": import ui_legacy as m; return m
        if module_name == "payment_engine": import payment_engine as m; return m
        if module_name == "auth_engine": import auth_engine as m; return m
        if module_name == "audit_engine": import audit_engine as m; return m
        if module_name == "email_engine": import email_engine as m; return m
        if module_name == "seo_injector": import seo_injector as m; return m
    except Exception as e:
        logger.error(f"Failed to load {module_name}: {e}")
        return None

# --- MAIN APP LOGIC ---
def main():
    # 1. SEO Injection (Safe)
    seo = get_module("seo_injector")
    if seo: seo.inject_meta()

    # 2. HANDLE PAYMENT RETURNS (ISOLATED FROM UI)
    params = st.query_params
    if "session_id" in params:
        session_id = params["session_id"]
        
        # Load Payment Engine ONLY here
        pay_eng = get_module("payment_engine")
        
        with st.container():
            st.markdown("### 🔐 Verifying Order...")
            
            status = "error"
            if pay_eng:
                try:
                    # VERIFY
                    status = pay_eng.verify_session(session_id)
                    logger.info(f"Verification Result: {status}")
                except Exception as e:
                    logger.error(f"Verify Crash: {e}")
            
            # --- SUCCESS PATH ---
            if status == "paid":
                st.success("✅ Payment Confirmed!")
                st.session_state.paid_success = True
                
                # A. Get User
                current_user = st.session_state.get("user_email", "guest")
                auth = get_module("auth_engine")
                if auth and st.session_state.get("authenticated"):
                    current_user = st.session_state.get("user_email")

                # B. Audit Log
                audit = get_module("audit_engine")
                if audit:
                    audit.log_event("PAYMENT_SUCCESS", current_user, f"Session: {session_id}")

                # C. Generate Tracking
                import random
                track_num = f"94055{random.randint(10000000,99999999)}"
                st.session_state.tracking_number = track_num

                # D. SEND EMAIL
                email_eng = get_module("email_engine")
                if email_eng:
                    tier_sold = "Standard"
                    if st.session_state.get("last_mode") == "legacy":
                        tier_sold = "Legacy"
                    email_eng.send_confirmation(current_user, track_num, tier=tier_sold)

                # E. ROUTE
                time.sleep(1)
                st.query_params.clear()
                
                if st.session_state.get("last_mode") == "legacy":
                    st.session_state.app_mode = "legacy"
                else:
                    st.session_state.app_mode = "workspace"
                
                st.rerun()

            # --- PENDING PATH ---
            elif status == "open":
                st.info("⏳ Processing... Please wait.")
                time.sleep(2)
                st.rerun()

            # --- FAILURE PATH ---
            else:
                st.warning("⚠️ Verification Pending")
                st.markdown("Stripe confirmed the transaction, but our check timed out.")
                
                c1, c2 = st.columns(2)
                with c1:
                    # Force a hard reload of the script
                    if st.button("🔄 Click to Verify Again", type="primary"):
                        st.rerun()
                with c2:
                    st.link_button("💬 Support", "mailto:support@verbapost.com")
                
                st.stop()

    # 3. PASSWORD RESET
    elif "type" in params and params["type"] == "recovery":
        st.session_state.app_mode = "login"

    # 4. INIT STATE
    if "app_mode" not in st.session_state:
        st.session_state.app_mode = "splash"
    
    # 5. SIDEBAR NAVIGATION
    with st.sidebar:
        st.header("VerbaPost System")
        st.markdown("---")
        if st.button("🏠 Home / Splash", use_container_width=True):
            st.session_state.app_mode = "splash"
            st.rerun()
        st.markdown("### 🛠️ Administration")
        if st.button("🔐 Admin Console", key="sidebar_admin_btn", use_container_width=True):
            st.session_state.app_mode = "admin"
            st.rerun()
        st.markdown("---")
        st.caption(f"v3.3.5 | {st.session_state.app_mode}")

    # 6. ROUTING (LAZY LOADING)
    # This ensures heavy UI modules are ONLY loaded when needed.
    mode = st.session_state.app_mode
    
    if mode == "splash":
        m = get_module("ui_splash")
        if m: m.render_splash_page()
        
    elif mode == "login":
        m = get_module("ui_login")
        if m: m.render_login_page()
        
    elif mode == "legacy":
        m = get_module("ui_legacy")
        if m: m.render_legacy_page()
        
    elif mode == "legal":
        m = get_module("ui_legal")
        if m: m.render_legal_page()
        
    elif mode == "admin":
        m = get_module("ui_admin")
        if m: m.render_admin_page()
        
    elif mode in ["store", "workspace", "review"]:
        m = get_module("ui_main")
        if m: m.render_main()
        
    else:
        m = get_module("ui_splash")
        if m: m.render_splash_page()

if __name__ == "__main__":
    main()