import streamlit as st
import time

# --- CONFIG ---
st.set_page_config(
    page_title="VerbaPost", 
    page_icon="📮", 
    layout="centered", 
    initial_sidebar_state="expanded"
)

# Force Sidebar to display
st.markdown("""<style>[data-testid="stSidebar"] {display: block !important;} .main .block-container {padding-top: 2rem;}</style>""", unsafe_allow_html=True)

# --- ROBUST IMPORTS ---
# We use individual try/excepts to ensure one broken module doesn't kill the app
try: import ui_main; except ImportError: ui_main = None
try: import ui_login; except ImportError: ui_login = None
try: import ui_admin; except ImportError: ui_admin = None
try: import ui_legal; except ImportError: ui_legal = None
try: import ui_legacy; except ImportError: ui_legacy = None
try: import ui_splash; except ImportError: ui_splash = None
try: import payment_engine; except ImportError: payment_engine = None
try: import audit_engine; except ImportError: audit_engine = None
try: import analytics; except ImportError: analytics = None
try: import seo_injector; except ImportError: seo_injector = None

# --- INITIALIZATION ---
if 'authenticated' not in st.session_state: st.session_state.authenticated = False
if 'app_mode' not in st.session_state: st.session_state.app_mode = "splash"

# 1. Analytics Injection (Non-blocking)
if analytics and hasattr(analytics, 'inject_ga'): 
    analytics.inject_ga()

# 2. SEO Injection (Non-blocking)
if seo_injector and hasattr(seo_injector, 'inject_meta_tags'):
    seo_injector.inject_meta_tags()

# --- GLOBAL SIDEBAR ---
# This ensures the sidebar (and Admin Link) renders on EVERY page view
if ui_main and hasattr(ui_main, 'render_sidebar'): 
    ui_main.render_sidebar()

# --- PAYMENT RETURN HANDLER (Loop Fix) ---
if "session_id" in st.query_params:
    sid = st.query_params["session_id"]
    with st.spinner("Verifying Payment..."):
        # Default to failed unless proven otherwise
        status = "failed"
        email = None
        
        if payment_engine:
            status, email = payment_engine.verify_session(sid)
        
        if status == "paid":
            st.success("✅ Payment Confirmed!")
            st.session_state.paid_order = True
            
            # Log to Audit Engine
            if audit_engine: 
                audit_engine.log_event(email, "PAYMENT_SUCCESS", sid)
            
            # Route user based on what they bought
            if st.session_state.get("locked_tier") == "Legacy": 
                st.query_params["view"] = "legacy"
            else: 
                st.session_state.app_mode = "workspace"
            
            # CRITICAL FIX: Clear params to prevent infinite loop
            st.query_params.clear()
            time.sleep(0.5)
            st.rerun()
        else:
            st.error("Payment validation failed or pending.")
            # Clear params so user isn't stuck seeing the error
            st.query_params.clear()

# --- MAIN VIEW ROUTING ---
view = st.query_params.get("view")

if view == "admin":
    if ui_admin: ui_admin.show_admin()
    else: st.error("Admin module missing")

elif view == "legacy":
    if ui_legacy: ui_legacy.render_legacy_page()

elif view == "legal":
    if ui_legal: ui_legal.render_legal()

elif view == "login":
    st.session_state.auth_view = "login"
    if ui_login: ui_login.render_login()

elif view == "signup":
    st.session_state.auth_view = "signup"
    if ui_login: ui_login.render_login()

else:
    # --- STANDARD APP FLOW ---
    # If logged in OR just paid, show the App (Controller)
    if st.session_state.authenticated or st.session_state.get("paid_order"):
        # If we were in splash mode, switch to store
        if st.session_state.get("app_mode") == "splash": 
            st.session_state.app_mode = "store"
            
        if ui_main: 
            ui_main.render_main()
        else:
            st.error("UI Controller (ui_main) is missing.")
    else:
        # Otherwise, show the Marketing Splash
        if ui_splash: 
            ui_splash.render_splash()
        else: 
            st.info("Welcome to VerbaPost (Splash Loading...)")