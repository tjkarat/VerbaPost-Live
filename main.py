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
    
    # 1. Early Secrets Check
    try:
        import secrets_manager
    except ImportError:
        st.error("❌ CRITICAL: secrets_manager.py file is missing.")
        st.stop()
    except Exception as e:
        st.error(f"❌ CRITICAL: Secrets loading failed: {e}")
        st.stop()

    if "app_mode" not in st.session_state:
        st.session_state.app_mode = "splash"
    
    try:
        q_params = st.query_params
        
        # --- STRIPE RETURN HANDLER (MANUAL BREAK) ---
        if "session_id" in q_params:
            sess_id = q_params["session_id"]
            
            # Placeholder for status
            status_box = st.empty()
            status_box.info("🔄 Verifying Payment...")
            
            # 1. Verify Payment
            try:
                import payment_engine
                is_paid, session_details = payment_engine.verify_session(sess_id)
            except Exception as e:
                print(f"Payment Engine Error: {e}")
                is_paid = False
                session_details = None

            # 2. Audit / CSRF
            current_user = st.session_state.get("user_email")
            payer_email = session_details.get("customer_details", {}).get("email") if session_details else None
            
            if is_paid and current_user and payer_email:
                if current_user.lower().strip() != payer_email.lower().strip():
                    status_box.error("⚠️ Security Alert: Payment email mismatch.")
                    st.stop()

            if is_paid:
                # 3. SET STATE
                st.session_state.payment_complete = True
                st.session_state.current_stripe_id = sess_id 
                st.session_state.app_mode = "workspace"
                
                if not current_user and payer_email:
                    st.session_state.user_email = payer_email

                # Restore Config
                if "tier" in q_params: st.session_state.locked_tier = q_params["tier"]
                if "intl" in q_params: st.session_state.is_intl = True
                if "certified" in q_params: st.session_state.is_certified = True
                if "qty" in q_params: st.session_state.bulk_paid_qty = int(q_params["qty"])
                
                # 4. STOP LOOP: FORCE USER CLICK
                status_box.success("✅ Payment Verified!")
                
                st.markdown("### 🚀 Ready to write?")
                if st.button("👉 Click here to start letter", type="primary"):
                    st.query_params.clear()
                    st.rerun()
                
                # CRITICAL: Stop execution here. Do not auto-reload.
                st.stop()
                
            else:
                status_box.error("❌ Payment Verification Failed or Expired.")
                if st.button("Return to Store"):
                    st.session_state.app_mode = "store"
                    st.query_params.clear()
                    st.rerun()
                st.stop()

        # --- OTHER LINKS ---
        elif "view" in q_params:
            st.session_state.app_mode = q_params["view"]
            st.query_params.clear()
            st.rerun()

    except Exception as e:
        st.error(f"Routing Error: {e}")
        st.code(traceback.format_exc())

    # --- LAUNCH UI ---
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