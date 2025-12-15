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
# Import engines and UI modules.
# We use try-except to handle potential missing files gracefully during dev,
# but for production, these should all be present.

try: import ui_splash
except ImportError: ui_splash = None

try: import ui_login
except ImportError: ui_login = None

try: import ui_main
except ImportError: ui_main = None

try: import ui_admin
except ImportError: ui_admin = None

try: import ui_legal  # <--- THIS WAS MISSING OR FAILING
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
    # 1. SEO Injection
    if seo_injector:
        seo_injector.inject_meta()

    # 2. Handle URL Parameters (e.g. Payment Returns)
    params = st.query_params
    
    if "session_id" in params and payment_engine:
        session_id = params["session_id"]
        # Payment Verification Logic
        with st.spinner("Verifying Payment..."):
            status = payment_engine.verify_session(session_id)
            
            if status == "paid":
                st.session_state.paid_success = True
                # Anti-CSRF: Ensure the payer matches the logged-in user if possible
                if auth_engine and st.session_state.get("authenticated"):
                    current_user = st.session_state.get("user_email")
                    # Log the event
                    if audit_engine:
                        audit_engine.log_event("Payment Success", current_user, f"Session: {session_id}")
                
                st.success("✅ Payment Confirmed!")
                time.sleep(1)
                # Clear param to prevent re-trigger
                st.query_params.clear()
                st.session_state.app_mode = "workspace"
                st.rerun()
            elif status == "open":
                st.info("Payment is processing...")
            else:
                st.error("Payment not found or failed.")
    
    # 3. Handle Password Reset Token
    if "type" in params and params["type"] == "recovery":
        st.session_state.app_mode = "login"

    # 4. Initialize Session State
    if "app_mode" not in st.session_state:
        st.session_state.app_mode = "splash"
    
    # --- SIDEBAR: SYSTEM MENU & ADMIN ACCESS ---
    # This block forces the sidebar toggle to appear in the top-left
    with st.sidebar:
        st.header("VerbaPost System")
        st.markdown("---")
        
        # Navigation shortcuts
        if st.button("🏠 Home / Splash", use_container_width=True):
            st.session_state.app_mode = "splash"
            st.rerun()
            
        st.markdown("### 🛠️ Administration")
        if st.button("🔐 Admin Console", key="sidebar_admin_btn", use_container_width=True):
            st.session_state.app_mode = "admin"
            st.rerun()
            
        st.markdown("---")
        st.caption(f"v3.3.0 | {st.session_state.app_mode}")

    # 5. Routing
    mode = st.session_state.app_mode
    
    if mode == "splash":
        if ui_splash: ui_splash.render_splash_page()
        else: st.error("Splash module missing")
        
    elif mode == "login":
        if ui_login: ui_login.render_login_page()
        else: st.error("Login module missing")
        
    elif mode == "legacy":
        if ui_legacy: ui_legacy.render_legacy_page()
        else: st.error("Legacy module missing")
        
    elif mode == "legal":
        # FIX: Check if ui_legal was actually imported
        if ui_legal: 
            ui_legal.render_legal_page()
        else: 
            st.error("Legal module missing (ui_legal.py)")
            if st.button("Back Home"):
                st.session_state.app_mode = "splash"
                st.rerun()
                
    elif mode == "admin":
        if ui_admin: ui_admin.render_admin_page()
        else: st.error("Admin module missing")
        
    elif mode in ["store", "workspace", "review"]:
        if ui_main: ui_main.render_main()
        else: st.error("Main UI module missing")
        
    else:
        # Fallback
        if ui_splash: ui_splash.render_splash_page()
        else: st.write("Application Error: No modules found.")

if __name__ == "__main__":
    main()