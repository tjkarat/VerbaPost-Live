import streamlit as st
import time

# --- CONFIGURATION (Must be first) ---
st.set_page_config(
    page_title="VerbaPost | Send Real Letters",
    page_icon="📮",
    layout="centered",
    initial_sidebar_state="expanded"
)

# --- CSS INJECTION ---
st.markdown("""
<style>
    /* Force Sidebar Visibility */
    [data-testid="stSidebar"] {
        display: block !important;
    }
    .main .block-container {
        padding-top: 2rem;
    }
    /* Global Toast Styling */
    div[data-testid="stToast"] {
        background-color: #f0f2f6;
        border-left: 5px solid #ff4b4b;
    }
</style>
""", unsafe_allow_html=True)

# --- SAFE IMPORTS (Prevents app crash on module errors) ---
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

# --- OPTIONAL MODULES ---
try:
    import ui_splash
except ImportError:
    ui_splash = None

# --- 1. GLOBAL SETUP ---
if analytics and hasattr(analytics, 'inject_ga'):
    try:
        analytics.inject_ga()
    except Exception:
        pass 

if seo_injector and hasattr(seo_injector, 'inject_meta_tags'):
    try:
        seo_injector.inject_meta_tags()
    except Exception:
        pass 

# Initialize Session State
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'user_email' not in st.session_state:
    st.session_state.user_email = None

# --- 2. GLOBAL SIDEBAR (Admin Access) ---
# We force this to run on EVERY page load so the sidebar never disappears
if hasattr(ui_main, 'render_sidebar'):
    ui_main.render_sidebar()

# --- 3. PAYMENT HANDLER ---
query_params = st.query_params

if "session_id" in query_params:
    session_id = query_params["session_id"]
    with st.spinner("Verifying secure payment..."):
        # Verify with Stripe
        status, payer_email = payment_engine.verify_session(session_id)
        
        if status == "paid":
            # Success State
            st.success("✅ Payment Confirmed!")
            st.session_state.paid_order = True
            
            # --- REDIRECT LOGIC ---
            # If they bought Legacy, stay in Legacy view.
            if st.session_state.get("locked_tier") == "Legacy":
                st.query_params["view"] = "legacy"
            else:
                # Otherwise go to Workspace
                st.session_state.app_mode = "workspace"
                if "view" in st.query_params: 
                    del st.query_params["view"]
            
            # Audit Log
            if audit_engine:
                audit_engine.log_event(payer_email, "PAYMENT_SUCCESS", session_id)
            
            time.sleep(0.5) 
            st.rerun()
        else:
            st.error("❌ Payment verification failed or cancelled.")
            st.query_params.clear()

# --- 4. ROUTER CONTROLLER ---
view = st.query_params.get("view")

# A. Admin Console
if view == "admin":
    ui_admin.show_admin()

# B. Legacy Service
elif view == "legacy":
    ui_legacy.render_legacy_page()

# C. Legal Pages
elif view == "legal":
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
        # Prevent getting stuck on 'splash' if logged in
        if st.session_state.get("app_mode") == "splash":
             st.session_state.app_mode = "store"
        
        ui_main.render_main()
    else:
        # Guest User -> Show Splash
        if ui_splash:
            ui_splash.render_splash()
        else:
            st.error("System Error: Splash module unavailable.")