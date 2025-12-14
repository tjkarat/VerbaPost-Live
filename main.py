import streamlit as st
import time

# --- CONFIGURATION (Must be first) ---
st.set_page_config(
    page_title="VerbaPost | Send Real Letters",
    page_icon="📮",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- CSS INJECTION ---
st.markdown("""
<style>
    [data-testid="stSidebar"] {display: none;}
    .main .block-container {padding-top: 2rem;}
    /* Global Toast Styling */
    div[data-testid="stToast"] {
        background-color: #f0f2f6;
        border-left: 5px solid #ff4b4b;
    }
</style>
""", unsafe_allow_html=True)

# --- SAFE IMPORTS ---
try:
    import ui_main
    import ui_login
    import ui_admin
    import ui_legal
    import ui_legacy
    import audit_engine
    import payment_engine
    import analytics
    import seo_injector
except ImportError as e:
    st.error(f"CRITICAL SYSTEM ERROR: Module import failed. {e}")
    st.stop()

try:
    import ui_splash
except ImportError:
    ui_splash = None

# --- 1. GLOBAL SETUP ---
if analytics and hasattr(analytics, 'inject_ga'):
    try: analytics.inject_ga()
    except: pass

if seo_injector and hasattr(seo_injector, 'inject_meta_tags'):
    try: seo_injector.inject_meta_tags()
    except: pass

# Initialize Session State
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'user_email' not in st.session_state:
    st.session_state.user_email = None

# --- 2. DEEP LINK & PAYMENT HANDLER ---
query_params = st.query_params

# Handle Session ID (Stripe Return)
if "session_id" in query_params:
    session_id = query_params["session_id"]
    with st.spinner("Verifying secure payment..."):
        # Verify with Stripe
        status, payer_email = payment_engine.verify_session(session_id)
        
        if status == "paid":
            # CSRF Check
            current_user = st.session_state.get("user_email")
            if current_user and payer_email:
                if current_user.lower().strip() != payer_email.lower().strip():
                    st.error("⚠️ Security Alert: Payment email does not match active session.")
                    audit_engine.log_event(current_user, "PAYMENT_CSRF_BLOCK", session_id)
                    st.stop()
            
            # --- FIX: CAPTURE STATE BEFORE CLEARING URL ---
            if "tier" in query_params:
                st.session_state.locked_tier = query_params["tier"]
            if "draft_id" in query_params:
                st.session_state.current_draft_id = query_params["draft_id"]
            if "qty" in query_params:
                st.session_state.bulk_paid_qty = int(query_params["qty"])

            # Success State
            st.success("✅ Payment Confirmed!")
            st.session_state.paid_order = True
            
            # --- FIX: FORCE NAVIGATION TO WORKSPACE ---
            st.session_state.app_mode = "workspace"
            
            audit_engine.log_event(payer_email, "PAYMENT_SUCCESS", session_id)
            
            # Clear params and reload
            st.query_params.clear()
            time.sleep(0.5) 
            st.rerun()
        else:
            st.error("❌ Payment verification failed or cancelled.")
            audit_engine.log_event(None, "PAYMENT_FAILED", session_id)
            st.query_params.clear()

# Handle Other Deep Links (Marketing)
if "tier" in query_params:
    st.session_state.locked_tier = query_params["tier"]
if "draft_id" in query_params:
    st.session_state.current_draft_id = query_params["draft_id"]
    if st.session_state.authenticated:
        st.session_state.app_mode = "workspace"

# --- 3. ROUTER CONTROLLER ---
view = st.query_params.get("view", "store")

# A. Admin Console
if view == "admin":
    ui_admin.show_admin()

# B. Legacy Service
elif view == "legacy":
    ui_legacy.render_legacy_page()

# C. Legal Pages
elif view in ["terms", "privacy", "legal"]:
    ui_legal.render_legal()

# D. Auth Direct Links
elif view == "login":
    st.session_state.auth_view = "login"
    ui_login.render_login()
elif view == "signup":
    st.session_state.auth_view = "signup"
    ui_login.render_login()

# E. Default App Flow
else:
    # Logic: If Authenticated OR Paid -> Go to Main App (Store/Workspace)
    if st.session_state.authenticated or st.session_state.get("paid_order"):
        # Default to workspace if paid, otherwise store logic inside ui_main handles it
        if st.session_state.get("paid_order") and st.session_state.get("app_mode") != "review":
             st.session_state.app_mode = "workspace"
        
        ui_main.render_main()
    else:
        # Guest User -> Show Splash
        if ui_splash:
            ui_splash.render_splash()
        else:
            st.error("System Error: Splash module unavailable.")