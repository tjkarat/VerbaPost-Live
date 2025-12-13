import streamlit as st
import ui_main
import ui_login
import ui_admin
import ui_legal
import ui_legacy  # 🆕 NEW IMPORT
import audit_engine
import payment_engine
import time

# --- OPTIONAL MODULES (Graceful Degradation) ---
# These prevent the app from crashing if utility files are missing
try:
    import analytics
    import seo_injector
except ImportError:
    analytics = None
    seo_injector = None

# --- STREAMLIT QUIRK FIX ---
# Lazy loading ui_splash can sometimes fail on Cloud Run
try:
    import ui_splash
except ImportError:
    ui_splash = None

# --- CONFIGURATION ---
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
    /* Toast Styling */
    div[data-testid="stToast"] {
        background-color: #f0f2f6;
        border-left: 5px solid #ff4b4b;
    }
</style>
""", unsafe_allow_html=True)

# --- ANALYTICS & SEO (FIXED) ---
# We use hasattr() to check if the function exists before calling it.
# This fixes the AttributeError if seo_injector.py is empty.
if analytics and hasattr(analytics, 'inject_ga'):
    try:
        analytics.inject_ga()
    except Exception:
        pass # Fail silently if analytics breaks

if seo_injector and hasattr(seo_injector, 'inject_meta_tags'):
    try:
        seo_injector.inject_meta_tags()
    except Exception:
        pass # Fail silently if SEO breaks

# --- SESSION STATE INIT ---
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'user_email' not in st.session_state:
    st.session_state.user_email = None

# --- PAYMENT RETURN HANDLER (SECURITY GATE) ---
# Handles the ?session_id=... return from Stripe
query_params = st.query_params
if "session_id" in query_params:
    session_id = query_params["session_id"]
    with st.spinner("Verifying secure payment..."):
        # Verify with Stripe
        status, payer_email = payment_engine.verify_session(session_id)
        
        if status == "paid":
            # CSRF Check: Ensure the payer matches the logged-in user (if logged in)
            current_user = st.session_state.get("user_email")
            
            # If user is logged in, verify emails match. 
            # If guest checkout (no login), we trust the session ID but log it.
            if current_user and payer_email:
                if current_user.lower().strip() != payer_email.lower().strip():
                    st.error("⚠️ Security Alert: Payment email does not match session.")
                    audit_engine.log_event(current_user, "PAYMENT_CSRF_BLOCK", session_id)
                    st.stop()
            
            # Success
            st.success("✅ Payment Confirmed!")
            st.session_state.paid_order = True
            
            # Log it
            audit_engine.log_event(payer_email, "PAYMENT_SUCCESS", session_id)
            
            # Clear params to prevent replay attacks
            st.query_params.clear()
            time.sleep(0.5) # Race condition fix (as per v3.0 docs)
            st.rerun()
        else:
            st.error("❌ Payment verification failed or cancelled.")
            st.query_params.clear()

# --- ROUTER ---
view = st.query_params.get("view", "store")

# 1. Admin Route
if view == "admin":
    ui_admin.render_admin()

# 2. Legacy Route (NEW)
elif view == "legacy":
    ui_legacy.render_legacy_page()

# 3. Legal Routes
elif view in ["terms", "privacy", "legal"]:
    ui_legal.render_legal()

# 4. Auth Route (Direct Link)
elif view == "login":
    st.session_state.auth_view = "login"
    ui_login.render_login()

# 5. Main App Logic
else:
    # Logic:
    # If Authenticated -> Show Workspace
    # If Guest -> Show Splash (unless they just paid, then let them in)
    if st.session_state.authenticated or st.session_state.get("paid_order"):
        ui_main.render_main()
    else:
        if ui_splash:
            ui_splash.render_splash()
        else:
            st.error("System Error: Splash module failed to load. Please refresh.")