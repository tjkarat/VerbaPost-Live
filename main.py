import streamlit as st
import time
import logging

# --- MODULE IMPORTS ---
try: import ui_main
except ImportError: ui_main = None
try: import payment_engine
except ImportError: payment_engine = None
try: import audit_engine
except ImportError: audit_engine = None
try: import database
except ImportError: database = None

# --- CONFIGURATION ---
st.set_page_config(
    page_title="VerbaPost", 
    page_icon="📮",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- SESSION STATE INIT ---
if "app_mode" not in st.session_state:
    st.session_state.app_mode = "splash"
if "payment_complete" not in st.session_state:
    st.session_state.payment_complete = False

# --- MAIN ROUTER ---
def main():
    # 1. HANDLE PAYMENT RETURN (SECURITY CRITICAL)
    if "session_id" in st.query_params:
        sess_id = st.query_params["session_id"]
        
        # Prevent re-verification loop
        if sess_id != st.session_state.get("last_verified_session"):
            try:
                if payment_engine:
                    with st.spinner("Verifying Payment..."):
                        is_paid, session_obj = payment_engine.verify_session(sess_id)
                    
                    if is_paid:
                        # --- SECURITY FIX: ENFORCE AUTH & IDENTITY ---
                        current_user = st.session_state.get("user_email")
                        
                        # A. Force Login if Guest
                        if not current_user:
                            st.error("⚠️ Session Expired. Please log in to claim this payment.")
                            st.session_state.app_mode = "login"
                            st.session_state.pending_payment_id = sess_id # Save for post-login claim
                            st.stop()

                        # B. CSRF / Identity Check (The Fix)
                        # Ensure the person who paid is the person logged in
                        payer_email = session_obj.customer_details.email if (session_obj and session_obj.customer_details) else None
                        
                        if payer_email and current_user:
                            if current_user.lower().strip() != payer_email.lower().strip():
                                # Log the attack/mismatch
                                if audit_engine:
                                    audit_engine.log_event(
                                        current_user, 
                                        "PAYMENT_MISMATCH_BLOCK", 
                                        sess_id, 
                                        {"payer": payer_email, "logged_in": current_user}
                                    )
                                
                                st.error("⚠️ Security Alert: Payment email does not match logged-in user.")
                                st.stop() # HALT EXECUTION

                        # C. Success State
                        st.success("✅ Payment Verified!")
                        st.session_state.payment_complete = True
                        st.session_state.last_verified_session = sess_id
                        
                        # Log Success
                        if audit_engine:
                            audit_engine.log_event(current_user, "PAYMENT_SUCCESS", sess_id)

                        # Restore State from URL Params
                        if "tier" in st.query_params:
                            st.session_state.locked_tier = st.query_params["tier"]
                        if "draft_id" in st.query_params:
                            st.session_state.current_draft_id = st.query_params["draft_id"]
                        if "qty" in st.query_params:
                            st.session_state.bulk_paid_qty = int(st.query_params["qty"])
                        
                        # Cleanup URL
                        time.sleep(1) # Allow UI to show success
                        st.query_params.clear()
                        st.session_state.app_mode = "workspace"
                        st.rerun()
                    else:
                        st.error("❌ Payment Verification Failed or Unpaid.")
                        if audit_engine:
                             audit_engine.log_event(None, "PAYMENT_FAILED", sess_id)
            except Exception as e:
                st.error(f"System Error: {e}")
                logger.error(f"Router Error: {e}")

    # 2. LOAD UI CONTROLLER
    if ui_main:
        ui_main.show_main_app()
    else:
        st.error("CRITICAL: UI Module not found.")

if __name__ == "__main__":
    main()