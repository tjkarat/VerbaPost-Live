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

# --- LAZY MODULE LOADER ---
def get_module(module_name):
    """Safely imports modules to prevent crashes."""
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
        if module_name == "analytics": import analytics as m; return m
    except Exception as e:
        logger.error(f"Failed to load {module_name}: {e}")
        return None

# --- SECRET MANAGER IMPORT ---
try: import secrets_manager
except ImportError: secrets_manager = None

# --- MAIN LOGIC ---
def main():
    # 1. SEO INJECTION
    seo = get_module("seo_injector")
    if seo: seo.inject_meta()

    # 2. ANALYTICS INJECTION
    analytics = get_module("analytics")
    if analytics: analytics.inject_ga()

    params = st.query_params

    # 3. ADMIN BACKDOOR
    if params.get("view") == "admin":
        st.session_state.app_mode = "admin"

    # 4. HANDLE PAYMENT
    if "session_id" in params:
        session_id = params["session_id"]
        pay_eng = get_module("payment_engine")
        
        status = "error"
        if pay_eng:
            try:
                result = pay_eng.verify_session(session_id)
                if isinstance(result, dict) and result.get('paid'):
                    status = "paid"
                    user_email = result.get('email')
                elif result == "paid":
                    status = "paid"
                    user_email = st.session_state.get("user_email")
            except Exception as e:
                logger.error(f"Verify Error: {e}")

        # Success Screen
        if status == "paid":
            import random
            if "tracking_number" not in st.session_state:
                st.session_state.tracking_number = f"94055{random.randint(10000000,99999999)}"
            
            track_num = st.session_state.tracking_number

            if "email_sent" not in st.session_state:
                email_eng = get_module("email_engine")
                if email_eng:
                    email_eng.send_confirmation(user_email, track_num, tier="Legacy")
                st.session_state.email_sent = True

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
                st.query_params.clear()
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()
            return

        elif status == "open":
            st.info("⏳ Payment processing...")
            time.sleep(2)
            st.rerun()
        else:
            st.warning("⚠️ Verification Pending")
            if st.button("🔄 Check Again"): st.rerun()
            return

    # 5. PASSWORD RESET
    elif params.get("type") == "recovery":
        st.session_state.app_mode = "login"

    # 6. INIT STATE
    if "app_mode" not in st.session_state:
        st.session_state.app_mode = "splash"
        
    mode = st.session_state.app_mode
    current_email = st.session_state.get("user_email")

    # 7. SIDEBAR (FIXED NAVIGATION)
    with st.sidebar:
        st.header("VerbaPost System")
        
        # FIX: Explicitly Clear Query Params to escape the "view=heirloom" trap
        if st.button("🏠 Home", use_container_width=True):
            st.query_params.clear()
            st.session_state.app_mode = "splash"
            st.rerun()
            
        if st.button("🕰️ Heirloom Dashboard", use_container_width=True):
            st.query_params["view"] = "heirloom"
            st.rerun()
            
        st.markdown("---")
        
        # Admin Logic
        admin_email = None
        if secrets_manager:
            raw_admin = secrets_manager.get_secret("admin.email")
            if raw_admin:
                admin_email = raw_admin.lower().strip()
        
        is_admin = st.session_state.get("admin_authenticated", False)
        
        if is_admin or (current_email and admin_email and current_email == admin_email):
            st.markdown("### 🛠️ Administration")
            if st.button("🔐 Admin Console", key="sidebar_admin_btn", use_container_width=True):
                st.query_params.clear() # FIX: Escape trap here too
                st.session_state.app_mode = "admin"
                st.rerun()
                
        st.caption(f"v3.3.13 | {st.session_state.app_mode}")

    # --- ROUTER LOGIC ---
    view_param = st.query_params.get("view", "store")

    # 1. Check for Heirloom View FIRST
    if view_param == "heirloom":
        try:
            import ui_heirloom
            ui_heirloom.render_dashboard()
            st.stop() 
        except ImportError:
            st.error("Heirloom module not found.")
            st.stop()

    # 2. Router
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
    elif mode == "legal":
        m = get_module("ui_legal")
        if m: m.render_legal_page()
    elif mode in ["store", "workspace", "review"]:
        m = get_module("ui_main")
        if m: m.render_main()
    else:
        m = get_module("ui_splash")
        if m: m.render_splash_page()

if __name__ == "__main__":
    main()