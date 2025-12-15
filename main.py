import streamlit as st
import time
import os

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

# --- IMPORTS ---
try: import ui_splash
except ImportError: ui_splash = None
try: import ui_login
except ImportError: ui_login = None
try: import ui_main
except ImportError: ui_main = None
try: import ui_admin
except ImportError: ui_admin = None
try: import ui_legal
except ImportError: ui_legal = None
try: import ui_legacy
except ImportError: ui_legacy = None
try: import payment_engine
except ImportError: payment_engine = None
try: import auth_engine
except ImportError: auth_engine = None
try: import audit_engine
except ImportError: audit_engine = None
try: import seo_injector
except ImportError: seo_injector = None
try: import email_engine  # <--- NEW: REQUIRED FOR CONFIRMATIONS
except ImportError: email_engine = None

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
    button[kind="secondary"] {
        background-color: #ffffff !important;
        color: #333 !important;
        border: 1px solid #ccc !important;
    }
    .stTextInput input:focus {
        border-color: #d93025 !important;
        box-shadow: 0 0 0 1px #d93025 !important;
    }
</style>
""", unsafe_allow_html=True)

# --- MAIN APP LOGIC ---
def main():
    if seo_injector: seo_injector.inject_meta()

    # 1. HANDLE PAYMENT RETURNS (STRIPE REDIRECT)
    params = st.query_params
    if "session_id" in params and payment_engine:
        session_id = params["session_id"]
        with st.spinner("Verifying Payment & Generating Tracking..."):
            status = payment_engine.verify_session(session_id)
            
            if status == "paid":
                st.session_state.paid_success = True
                
                # A. Determine User Logic
                current_user = st.session_state.get("user_email", "guest")
                if auth_engine and st.session_state.get("authenticated"):
                    current_user = st.session_state.get("user_email")

                # B. Audit Log
                if audit_engine:
                    audit_engine.log_event("PAYMENT_SUCCESS", current_user, f"Session: {session_id}")

                # C. Generate Mock Tracking (Real system would fetch from DB/PostGrid)
                import random
                track_num = f"94055{random.randint(10000000,99999999)}"
                st.session_state.tracking_number = track_num

                # D. SEND EMAIL (FIXED)
                if email_engine:
                    # Determine Tier for email subject
                    tier_sold = "Legacy" if st.session_state.get("last_mode") == "legacy" else "Standard"
                    email_engine.send_confirmation(current_user, track_num, tier=tier_sold)

                # E. ROUTING (FIXED)
                st.success("✅ Payment Confirmed!")
                time.sleep(1)
                st.query_params.clear()
                
                # Route back to the correct engine
                if st.session_state.get("last_mode") == "legacy":
                    st.session_state.app_mode = "legacy"
                else:
                    st.session_state.app_mode = "workspace"
                
                st.rerun()

            elif status == "open":
                st.info("Payment is processing...")
            else:
                st.error("Payment not found or failed. Please contact support.")
    
    # 2. PASSWORD RESET
    if "type" in params and params["type"] == "recovery":
        st.session_state.app_mode = "login"

    # 3. INIT STATE
    if "app_mode" not in st.session_state:
        st.session_state.app_mode = "splash"
    
    # 4. SIDEBAR NAVIGATION
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
        st.caption(f"v3.3.1 | {st.session_state.app_mode}")

    # 5. ROUTING SWITCHBOARD
    mode = st.session_state.app_mode
    if mode == "splash":
        if ui_splash: ui_splash.render_splash_page()
    elif mode == "login":
        if ui_login: ui_login.render_login_page()
    elif mode == "legacy":
        if ui_legacy: ui_legacy.render_legacy_page()
    elif mode == "legal":
        if ui_legal: ui_legal.render_legal_page()
    elif mode == "admin":
        if ui_admin: ui_admin.render_admin_page()
    elif mode in ["store", "workspace", "review"]:
        if ui_main: ui_main.render_main()
    else:
        if ui_splash: ui_splash.render_splash_page()

if __name__ == "__main__":
    main()