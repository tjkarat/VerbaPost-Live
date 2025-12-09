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
        button[kind="primary"] { background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%) !important; border: none !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. RUN ---
if __name__ == "__main__":
    inject_global_css()
    
    # 1. Early Secrets Check
    try: import secrets_manager
    except ImportError: st.error("❌ secrets_manager.py missing"); st.stop()
    except Exception as e: st.error(f"❌ Secrets Error: {e}"); st.stop()

    if "app_mode" not in st.session_state:
        st.session_state.app_mode = "splash"
    
    try:
        q_params = st.query_params
        
        # --- STRIPE RETURN HANDLER (CRASH PROOFED) ---
        if "session_id" in q_params:
            sess_id = q_params["session_id"]
            
            # Use a placeholder to prevent white screen
            status_box = st.empty()
            status_box.info("🔄 Verifying Payment...")
            
            try:
                import payment_engine
                is_paid, session_details = payment_engine.verify_session(sess_id)
            except Exception as e:
                status_box.error(f"Payment Engine Error: {e}")
                is_paid = False
                session_details = None
                time.sleep(3) # Let user see error

            # Audit / CSRF
            current_user = st.session_state.get("user_email")
            payer_email = session_details.get("customer_details", {}).get("email") if session_details else None
            
            if is_paid:
                # CSRF CHECK
                if current_user and payer_email:
                    if current_user.lower().strip() != payer_email.lower().strip():
                        status_box.error("⚠️ Security Alert: Payment email mismatch.")
                        st.stop()

                # Success State
                st.session_state.app_mode = "workspace"
                st.session_state.payment_complete = True
                st.session_state.current_stripe_id = sess_id 
                if not current_user and payer_email:
                    st.session_state.user_email = payer_email

                # Restore Params
                if "tier" in q_params: st.session_state.locked_tier = q_params["tier"]
                if "intl" in q_params: st.session_state.is_intl = True
                if "certified" in q_params: st.session_state.is_certified = True
                if "qty" in q_params: st.session_state.bulk_paid_qty = int(q_params["qty"])
                
                status_box.success("✅ Payment Verified! Redirecting...")
            else:
                status_box.error("❌ Payment Verification Failed.")
                st.session_state.app_mode = "store"
            
            # Clear params and reload
            time.sleep(1.0)
            st.query_params.clear()
            st.rerun()

        # --- OTHER LINKS ---
        elif "view" in q_params:
            st.session_state.app_mode = q_params["view"]
            st.query_params.clear()
            st.rerun()

    except Exception as e:
        st.error(f"Routing Crash: {e}")
        st.code(traceback.format_exc())

    # --- LAUNCH UI ---
    try:
        import ui_main
        ui_main.show_main_app()
    except Exception as e:
        st.error("⚠️ Critical UI Crash")
        st.code(traceback.format_exc())
        if st.button("Emergency Reset"):
            st.session_state.clear()
            st.rerun()