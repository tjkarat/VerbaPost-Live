import streamlit as st
import time

# --- PAGE CONFIGURATION (Must be first) ---
st.set_page_config(
    page_title="VerbaPost",
    page_icon="📮",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- ROBUST IMPORTS ---
# We use try/except to prevent the "White Screen of Death" if a module has a typo
try:
    import ui_splash
except Exception as e:
    print(f"Error importing ui_splash: {e}")
    ui_splash = None

try:
    import ui_login
except Exception as e:
    print(f"Error importing ui_login: {e}")
    ui_login = None

try:
    import ui_main
except Exception as e:
    print(f"Error importing ui_main: {e}")
    ui_main = None

try:
    import ui_legacy
except Exception as e:
    print(f"Error importing ui_legacy: {e}")
    ui_legacy = None

try:
    import ui_legal
except Exception as e:
    print(f"Error importing ui_legal: {e}")
    ui_legal = None

try:
    import analytics
    import seo_injector
except Exception:
    analytics = None
    seo_injector = None

# --- SESSION STATE INITIALIZATION ---
if "app_mode" not in st.session_state:
    st.session_state.app_mode = "splash"
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

# --- ANALYTICS & SEO ---
if analytics:
    try: analytics.inject_ga()
    except: pass
if seo_injector:
    try: seo_injector.inject_meta()
    except: pass

# --- PAYMENT RETURN HANDLER ---
# Checks if user is returning from Stripe
if "session_id" in st.query_params:
    try:
        import payment_engine
        import audit_engine
        
        s_id = st.query_params["session_id"]
        
        # Verify payment with Stripe
        if payment_engine and payment_engine.verify_session(s_id):
            st.session_state.paid_order = True
            st.session_state.app_mode = "review"
            st.toast("Payment Confirmed! 💳", icon="✅")
            
            # Log success
            if audit_engine:
                audit_engine.log_event(
                    st.session_state.get("user_email", "guest"), 
                    "PAYMENT_SUCCESS", 
                    s_id
                )
        else:
            st.error("⚠️ Payment verification failed or expired.")
            
        # Clear params to prevent replay
        st.query_params.clear()
        
    except Exception as e:
        st.error(f"Payment Error: {e}")

# --- MAIN ROUTING LOGIC ---
def main():
    # 1. Check for URL overrides (e.g., ?view=login)
    view_param = st.query_params.get("view", None)
    
    if view_param == "legacy" and ui_legacy:
        ui_legacy.render_legacy_page()
        
    elif view_param == "legal" and ui_legal:
        ui_legal.render_legal_page() # Ensure ui_legal.py has this function
        
    elif view_param == "login" and ui_login:
        ui_login.render_login_page()
        
    elif view_param == "admin":
        if st.session_state.authenticated:
            # Simple admin check (you can make this stricter)
            if ui_main: 
                ui_main.render_sidebar()
                st.info("Admin Console Loading...")
        else:
            st.warning("Please log in first.")
            if ui_login: ui_login.render_login_page()

    # 2. Normal App Flow
    else:
        # If logged in OR just paid, show the App
        if st.session_state.authenticated or st.session_state.get("paid_order"):
            if ui_main:
                ui_main.render_main()
            else:
                st.error("System Error: UI Main module missing.")
        
        # Otherwise, show Splash
        else:
            if st.session_state.app_mode == "store" and ui_main:
                # Allow guest access to store
                ui_main.render_main()
            elif ui_splash:
                ui_splash.render_splash()
            else:
                st.error("System Error: Splash module missing.")

if __name__ == "__main__":
    main()