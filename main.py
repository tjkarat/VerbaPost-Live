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
st.set_page_config(page_title="VerbaPost", page_icon="📮", layout="centered")

def main():
    # 1. Initialize Global Session State
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "user_email" not in st.session_state:
        st.session_state.user_email = ""
    if "app_mode" not in st.session_state:
        st.session_state.app_mode = "splash"

    # 2. Handle URL Parameters (Routing)
    query_params = st.query_params
    
    # A. Handle Payment Return (Stripe Redirect)
    session_id = query_params.get("session_id", None)
    
    # LOGIC FIX: Check if we already processed this session to prevent duplicate fulfillment
    if session_id and session_id != st.session_state.get("last_processed_session"):
        with st.spinner("Verifying secure payment..."):
            # Verify with Stripe
            verification = payment_engine.verify_session(session_id)
            
            if verification and verification.get("paid"):
                # Mark session as processed immediately
                st.session_state.last_processed_session = session_id
                
                # CAPTURE EMAIL (Critical for Guests)
                payer_email = verification.get("email")
                
                if payer_email:
                    st.session_state.user_email = payer_email
                    st.session_state.payment_email = payer_email
                    
                    # FINANCIAL FIX: Update DB immediately to "Paid" to lock the draft
                    if st.session_state.get("current_legacy_draft_id"):
                        database.update_draft_data(
                            st.session_state.current_legacy_draft_id, 
                            status="Paid",
                            price=verification.get("amount", 15.99)
                        )

                # Log Success
                audit_engine.log_event(st.session_state.user_email, "PAYMENT_SUCCESS", session_id, {})
                
                # Set Flags for UI
                st.session_state.paid_success = True
                
                # Routing
                if st.session_state.get("current_legacy_draft_id"):
                     st.session_state.app_mode = "legacy"
                else:
                     st.session_state.app_mode = "review"
                
                st.toast("Payment Confirmed! 💳", icon="✅")
            else:
                st.error("Payment Verification Failed or Cancelled.")
        
        # Clear URL to prevent re-triggering on refresh
        st.query_params.clear()

    # B. Handle View Routing
    view_param = query_params.get("view", None)
    if view_param == "legacy":
        st.session_state.app_mode = "legacy"
    elif view_param == "legal":
        st.session_state.app_mode = "legal"
    elif view_param == "admin":
        st.session_state.app_mode = "admin"
    elif view_param == "login":
        st.session_state.app_mode = "login"

    # 3. Render Application based on App Mode
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