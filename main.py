import streamlit as st
import payment_engine
import auth_engine
import audit_engine
import ui_main
import ui_legacy
import ui_splash
import ui_login
import ui_admin
import ui_legal
import database

# --- CONFIGURATION ---
st.set_page_config(page_title="VerbaPost", page_icon="📮", layout="wide")

# --- GLOBAL SIDEBAR ---
def render_sidebar():
    """
    Renders the Global Sidebar with Navigation, Admin Access, and Help.
    """
    with st.sidebar:
        # 1. Logo / Brand
        st.markdown("# 📮 VerbaPost")
        st.markdown("---")
        
        # 2. Navigation
        st.markdown("### 🧭 Navigation")
        if st.button("🏠 Home / Splash", use_container_width=True):
            st.session_state.app_mode = "splash"
            st.rerun()
            
        if st.button("🔐 Login / Account", use_container_width=True):
            st.session_state.app_mode = "login"
            st.rerun()

        # 3. Admin Access
        st.markdown("---")
        if st.button("⚙️ Admin Console", use_container_width=True):
            st.session_state.app_mode = "admin"
            st.rerun()

        # 4. Help / Tutorial
        st.markdown("---")
        with st.expander("❓ Help & Tutorial"):
            st.markdown("""
            **How to use VerbaPost:**
            1. **Choose Service:** Select Standard or Legacy.
            2. **Compose:** Type or Dictate your letter.
            3. **Address:** Enter recipient details.
            4. **Pay:** Checkout securely via Stripe.
            5. **Track:** We email you the tracking #.
            """)
            st.info("Support: help@verbapost.com")

        # 5. Session Debug
        if st.session_state.get("authenticated"):
            st.success(f"Logged in as: {st.session_state.get('user_email')}")
            if st.button("Logout"):
                st.session_state.authenticated = False
                st.session_state.user_email = ""
                st.session_state.app_mode = "splash"
                st.rerun()

def main():
    # 1. Initialize Global Session State
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "user_email" not in st.session_state:
        st.session_state.user_email = ""
    if "app_mode" not in st.session_state:
        st.session_state.app_mode = "splash"

    # 2. Render Global Sidebar
    render_sidebar()

    # 3. Handle URL Parameters (Routing)
    query_params = st.query_params
    
    # A. Handle Payment Return (Stripe Redirect)
    session_id = query_params.get("session_id", None)
    
    # Only verify if we haven't already processed this session
    if session_id and session_id != st.session_state.get("last_processed_session"):
        with st.spinner("Verifying secure payment..."):
            # Verify with Stripe
            result = payment_engine.verify_session(session_id)
            
            if result and result.get("paid"):
                st.session_state.last_processed_session = session_id
                
                # CAPTURE EMAIL (Critical for Guests)
                payer_email = result.get("email")
                if payer_email:
                    st.session_state.user_email = payer_email
                    
                    # Update the draft record with this email
                    if st.session_state.get("current_legacy_draft_id"):
                        database.update_draft_data(
                            st.session_state.current_legacy_draft_id, 
                            status="Paid",
                            price=15.99
                        )

                # Log Success
                audit_engine.log_event(st.session_state.user_email, "PAYMENT_SUCCESS", session_id, {})
                
                # Set Flags
                st.session_state.paid_success = True
                
                # Force routing to legacy view so it can show the Success Screen
                if st.session_state.get("current_legacy_draft_id"):
                     st.session_state.app_mode = "legacy"
                else:
                     st.session_state.app_mode = "review"
                
                st.success("Payment Confirmed!")
            else:
                st.error("Payment Verification Failed or Cancelled.")
        
        # Clear URL to prevent re-triggering
        st.query_params.clear()

    # B. Handle View Routing
    view_param = query_params.get("view", None)
    if view_param == "legacy":
        st.session_state.app_mode = "legacy"
    elif view_param == "legal":
        st.session_state.app_mode = "legal"
    elif view_param == "admin":
        st.session_state.app_mode = "admin"

    # 4. Render Application based on App Mode
    mode = st.session_state.app_mode

    if mode == "splash":
        if ui_splash: ui_splash.render_splash_page()
        else: st.error("Splash module missing")

    elif mode == "login":
        if ui_login: ui_login.render_login_page()
        
    elif mode == "legacy":
        if ui_legacy: ui_legacy.render_legacy_page()
        
    elif mode == "legal":
        if ui_legal: ui_legal.render_legal_page()
        
    elif mode == "admin":
        if ui_admin: ui_admin.render_admin_page()
        
    # Default / Standard App Flow
    elif mode in ["store", "workspace", "review"]:
        if ui_main: ui_main.render_main()
    
    else:
        # Fallback
        if ui_main: ui_main.render_main()

if __name__ == "__main__":
    main()