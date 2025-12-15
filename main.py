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

# --- LAZY MODULE LOADER (CRITICAL FOR STABILITY) ---
def get_module(module_name):
    """Safely imports modules to prevent Torch/AI crashes from breaking the router."""
    try:
        if module_name == "ui_splash": import ui_splash as m; return m
        if module_name == "ui_login": import ui_login as m; return m
        if module_name == "ui_main": import ui_main as m; return m
        if module_name == "ui_admin": import ui_admin as m; return m
        if module_name == "ui_legal": import ui_legal as m; return m
        if module_name == "ui_legacy": import ui_legacy as m; return m
        if module_name == "payment_engine": import payment_engine as m; return m
        if module_name == "email_engine": import email_engine as m; return m
        if module_name == "audit_engine": import audit_engine as m; return m
        if module_name == "auth_engine": import auth_engine as m; return m
        if module_name == "seo_injector": import seo_injector as m; return m
    except Exception as e:
        logger.error(f"Failed to load {module_name}: {e}")
        return None

# --- MAIN LOGIC ---
def main():
    # 1. SEO (Safe)
    seo = get_module("seo_injector")
    if seo: seo.inject_meta()

    # 2. HANDLE PAYMENT (SAFE LANDING MODE)
    # We handle the success screen HERE to avoid loading the heavy "ui_legacy" module
    # which causes the Torch crash loops.
    params = st.query_params
    if "session_id" in params:
        session_id = params["session_id"]
        
        # Load Payment Engine
        pay_eng = get_module("payment_engine")
        
        # Verify
        status = "error"
        if pay_eng:
            try:
                # Returns dict: {'paid': True, 'email': '...', 'amount': 15.99} or string status
                result = pay_eng.verify_session(session_id)
                if isinstance(result, dict) and result.get('paid'):
                    status = "paid"
                    user_email = result.get('email')
                elif result == "paid":
                    status = "paid"
                    user_email = st.session_state.get("user_email")
            except Exception as e:
                logger.error(f"Verify Error: {e}")

        # --- RENDER SUCCESS SCREEN (ISOLATED) ---
        if status == "paid":
            # 1. Generate Tracking
            import random
            if "tracking_number" not in st.session_state:
                st.session_state.tracking_number = f"94055{random.randint(10000000,99999999)}"
            
            track_num = st.session_state.tracking_number

            # 2. Send Email (Once)
            if "email_sent" not in st.session_state:
                email_eng = get_module("email_engine")
                if email_eng:
                    email_eng.send_confirmation(user_email, track_num, tier="Legacy")
                st.session_state.email_sent = True

            # 3. Show UI (Directly in main.py)
            st.markdown(f"""
                <div class="success-box">
                    <div class="success-title">✅ Payment Confirmed!</div>
                    <p>Your legacy letter has been securely generated.</p>
                    <p>Tracking Number: <span class="tracking-code">{track_num}</span></p>
                    <p><small>A confirmation email has been sent to <b>{user_email}</b></small></p>
                </div>
            """, unsafe_allow_html=True)

            st.balloons()

            if st.button("🏠 Start Another Letter", type="primary", use_container_width=True):
                # Clean Reset
                st.query_params.clear()
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()
            
            # STOP here. Do not load other modules.
            return

        elif status == "open":
            st.info("⏳ Payment processing...")
            time.sleep(2)
            st.rerun()
        else:
            st.warning("⚠️ Verification Pending")
            st.write("We received the signal from Stripe, but could not verify instantly.")
            if st.button("🔄 Check Again"):
                st.rerun()
            return

    # 3. ROUTING (Standard Flow)
    if "app_mode" not in st.session_state:
        st.session_state.app_mode = "splash"
        
    mode = st.session_state.app_mode

    # Sidebar
    with st.sidebar:
        st.header("VerbaPost System")
        st.markdown("---")
        if st.button("🏠 Home", use_container_width=True):
            st.session_state.app_mode = "splash"
            st.rerun()
        if st.button("🔐 Admin", use_container_width=True):
            st.session_state.app_mode = "admin"
            st.rerun()
        st.caption("v3.3.6 Stable")

    # Module Router
    if mode == "splash":
        m = get_module("ui_splash")
        if m: m.render_splash_page()
    elif mode == "legacy":
        m = get_module("ui_legacy")
        if m: m.render_legacy_page()
    elif mode == "login":
        m = get_module("ui_login")
        if m: m.render_login_page()
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