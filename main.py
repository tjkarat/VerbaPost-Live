import streamlit as st
import time
import traceback

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
    
    # --- DEBUG: EARLY SECRETS CHECK ---
    try:
        import secrets_manager
    except ImportError:
        st.error("❌ CRITICAL: secrets_manager.py file is missing.")
        st.stop()
    except Exception as e:
        st.error(f"❌ CRITICAL: Secrets loading failed: {e}")
        st.code(traceback.format_exc())
        st.stop()

    if "app_mode" not in st.session_state:
        st.session_state.app_mode = "splash"
    
    try:
        q_params = st.query_params
        
        # --- A. DEEP LINKING ---
        if "view" in q_params:
            target_view = q_params["view"]
            if target_view in ["legal", "login", "splash"]:
                st.session_state.app_mode = target_view
                st.query_params.clear()
        
        # --- B. MARKETING LINKS ---
        if "tier" in q_params and "session_id" not in q_params:
            st.session_state.target_marketing_tier = q_params["tier"]

        # --- C. SECURE STRIPE RETURN LOGIC (ANTI-WHITE SCREEN) ---
        if "session_id" in q_params:
            sess_id = q_params["session_id"]
            
            # Show visible feedback so user doesn't see a dead white screen
            status_placeholder = st.empty()
            status_placeholder.info("🔄 Verifying Payment... Please wait.")
            
            # 1. Verify Payment
            try:
                import payment_engine
                is_paid, session_details = payment_engine.verify_session(sess_id)
            except Exception as e:
                is_paid = False
                session_details = None
                print(f"Payment Verification Error: {e}")

            # 2. Audit & CSRF Logic
            current_user = st.session_state.get("user_email")
            payer_email = session_details.get("customer_details", {}).get("email") if session_details else None
            
            if is_paid and current_user and payer_email:
                if current_user.lower().strip() != payer_email.lower().strip():
                    status_placeholder.error("⚠️ Security Alert: Payment email does not match logged-in user.")
                    time.sleep(5)
                    st.stop()

            if is_paid:
                status_placeholder.success("✅ Payment Verified!")
                st.session_state.app_mode = "workspace"
                st.session_state.payment_complete = True
                st.session_state.current_stripe_id = sess_id 
                
                # Recover email if guest checkout
                if not current_user and payer_email:
                    st.session_state.user_email = payer_email

                # Restore session flags from URL
                if "tier" in q_params: st.session_state.locked_tier = q_params["tier"]
                if "intl" in q_params: st.session_state.is_intl = True
                if "certified" in q_params: st.session_state.is_certified = True
                if "qty" in q_params: st.session_state.bulk_paid_qty = int(q_params["qty"])
                
            else:
                status_placeholder.error("❌ Payment Verification Failed or Expired.")
                st.session_state.app_mode = "store"
            
            # Small delay to ensure state is saved before reload
            time.sleep(1.0) 
            st.query_params.clear()
            st.rerun()
            
    except Exception as e:
        st.error(f"Routing Error: {e}")
        st.code(traceback.format_exc())

    # --- LAUNCH UI (WITH ERROR REPORTING) ---
    try:
        import ui_main
        ui_main.show_main_app()
    except Exception as e:
        st.error("⚠️ Application Crash")
        st.markdown(f"**Error:** `{e}`")
        st.code(traceback.format_exc())
        
        if st.button("Hard Reset App State"):
            st.session_state.clear()
            st.rerun()