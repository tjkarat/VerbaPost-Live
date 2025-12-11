import streamlit as st
import time
import logging

# --- 1. CONFIG ---
st.set_page_config(
    page_title="VerbaPost | Send Real Mail from Audio",
    page_icon="📮",
    layout="centered",
    initial_sidebar_state="collapsed" 
)

# --- 2. CSS ---
def inject_global_css():
    st.markdown("""
    <style>
        .stApp { background-color: #f8f9fc; }
        h1, h2, h3, h4, h5, h6, .stMarkdown, p, li, span, div { color: #2d3748 !important; }
        label, .stTextInput label, .stSelectbox label { color: #2a5298 !important; font-weight: 600 !important; }
        .custom-hero h1, .custom-hero div { color: white !important; }
        button p { color: #2a5298 !important; }
        button[kind="primary"] { background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%) !important; border: none !important; }
        button[kind="primary"] p { color: white !important; }
        [data-testid="stFormSubmitButton"] button { background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%) !important; border: none !important; }
        [data-testid="stFormSubmitButton"] button p { color: #FFFFFF !important; }
        button:hover { transform: scale(1.02); }
        [data-testid="stSidebar"] { background-color: white !important; border-right: 1px solid #e2e8f0; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. RUN ---
if __name__ == "__main__":
    inject_global_css()
    
    if "app_mode" not in st.session_state:
        st.session_state.app_mode = "splash"
    
    try:
        q_params = st.query_params
        
        # --- A. DEEP LINKING ---
        if "view" in q_params:
            target_view = q_params["view"]
            if target_view in ["legal", "login", "splash"]:
                if st.session_state.app_mode not in ["store", "workspace", "review"]:
                    st.session_state.app_mode = target_view
        
        if "tier" in q_params and "session_id" not in q_params:
            st.session_state.target_marketing_tier = q_params["tier"]

        # --- B. STRIPE RETURN LOGIC ---
        if "session_id" in q_params:
            sess_id = q_params["session_id"]
            
            try:
                import payment_engine
                import audit_engine 
                is_paid, session_details = payment_engine.verify_session(sess_id)
            except ImportError:
                is_paid = False
                session_details = None

            current_user = st.session_state.get("user_email")
            payer_email = session_details.get("customer_details", {}).get("email") if session_details else None
            
            if is_paid and current_user and payer_email:
                if current_user.lower().strip() != payer_email.lower().strip():
                    if audit_engine: audit_engine.log_event(current_user, "PAYMENT_MISMATCH", sess_id, {"payer": payer_email})
                    st.error("⚠️ Security Alert: Payment email does not match logged-in user.")
                    st.stop()

            if is_paid:
                # 1. Update State
                st.session_state.app_mode = "workspace"
                st.session_state.payment_complete = True
                st.session_state.current_stripe_id = sess_id 
                
                # Clear pending URL
                if "pending_stripe_url" in st.session_state:
                    del st.session_state.pending_stripe_url
                
                if audit_engine: audit_engine.log_event(current_user, "PAYMENT_VERIFIED", sess_id, {})

                if not current_user and payer_email:
                    st.session_state.user_email = payer_email

                # Restore tier/settings from URL params
                if "tier" in q_params: st.session_state.locked_tier = q_params["tier"]
                if "intl" in q_params: st.session_state.is_intl = True
                if "certified" in q_params: st.session_state.is_certified = True
                if "qty" in q_params: st.session_state.bulk_paid_qty = int(q_params["qty"])
                
                # 2. AUTO-FORWARD (No button required)
                st.toast("✅ Payment Verified! Preparing workspace...", icon="📮")
                time.sleep(0.5) # Brief pause for toast visibility
                st.query_params.clear()
                st.rerun()
                
            else:
                if audit_engine: audit_engine.log_event(current_user, "PAYMENT_FAILED", sess_id, {"reason": "Verification returned false"})
                st.error("❌ Payment Verification Failed.")
                st.session_state.app_mode = "store"
                time.sleep(2)
                st.query_params.clear()
                st.rerun()
            
    except Exception as e:
        print(f"Routing Error: {e}")

    # --- LAUNCH UI ---
    try:
        import ui_main
        ui_main.show_main_app()
    except Exception as e:
        st.error("⚠️ Application Error. Please refresh.")
        print(f"Critical UI Error: {e}")
        if st.button("Hard Reset App"):
            st.session_state.clear()
            st.rerun()