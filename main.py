import streamlit as st
import time

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
        /* GLOBAL THEME */
        .stApp { background-color: #f8f9fc; }
        
        /* TEXT COLORS */
        h1, h2, h3, h4, h5, h6, .stMarkdown, p, li, span, div { 
            color: #2d3748 !important; 
        }

        /* INPUT LABELS */
        label, .stTextInput label, .stSelectbox label {
            color: #2a5298 !important;
            font-weight: 600 !important;
        }
        
        /* HERO HEADER */
        .custom-hero h1, .custom-hero div {
            color: white !important;
        }
        
        /* BUTTON FIXES */
        button p {
            color: #2a5298 !important;
        }
        
        /* Primary Buttons (Gradient) */
        button[kind="primary"] {
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%) !important;
            border: none !important;
        }
        button[kind="primary"] p {
            color: white !important;
        }

        /* LOGIN/FORM BUTTONS */
        [data-testid="stFormSubmitButton"] button,
        [data-testid="stFormSubmitButton"] button > div,
        [data-testid="stFormSubmitButton"] button > div > p {
            color: #FFFFFF !important;
            -webkit-text-fill-color: #FFFFFF !important;
            font-weight: 600 !important;
        }
        
        [data-testid="stFormSubmitButton"] button {
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%) !important;
            border: none !important;
        }

        /* Hover Effects */
        button:hover {
            transform: scale(1.02);
        }

        /* SIDEBAR */
        [data-testid="stSidebar"] { 
            background-color: white !important; 
            border-right: 1px solid #e2e8f0; 
        }
    </style>
    """, unsafe_allow_html=True)

# --- 3. RUN ---
if __name__ == "__main__":
    inject_global_css()
    
    if "app_mode" not in st.session_state:
        st.session_state.app_mode = "splash"
    
    try:
        q_params = st.query_params
        
        # --- A. DEEP LINKING LOGIC ---
        if "view" in q_params:
            target_view = q_params["view"]
            if target_view in ["legal", "login", "splash"]:
                st.session_state.app_mode = target_view
        
        # --- B. MARKETING LINKS ---
        if "tier" in q_params and "session_id" not in q_params:
            st.session_state.target_marketing_tier = q_params["tier"]

        # --- C. SECURE STRIPE RETURN LOGIC ---
        if "session_id" in q_params:
            sess_id = q_params["session_id"]
            
            # 1. CSRF/Replay Check: Does this session match the user?
            # (If user is not logged in yet, we skip this check but verify payment)
            
            try:
                import payment_engine
                # Verify with Stripe API
                is_paid, session_details = payment_engine.verify_session(sess_id)
            except Exception:
                is_paid = False 
                session_details = None

            if is_paid:
                # 2. Authorization Check (Prevent stealing sessions)
                # If we have a user email, ensure it matches the payer email
                current_user = st.session_state.get("user_email")
                payer_email = session_details.get("customer_details", {}).get("email") if session_details else None
                
                if current_user and payer_email and current_user.lower() != payer_email.lower():
                     st.error("⚠️ Security Alert: Payment email does not match logged-in user.")
                     st.stop() # Halt execution

                # ✅ Verified & Authorized
                st.session_state.app_mode = "workspace"
                st.session_state.payment_complete = True
                st.session_state.current_stripe_id = sess_id 
                
                # Capture email from Stripe if we don't have it (Guest checkout flow)
                if not current_user and payer_email:
                    st.session_state.user_email = payer_email

                # Restore session flags from URL
                if "tier" in q_params: st.session_state.locked_tier = q_params["tier"]
                if "intl" in q_params: st.session_state.is_intl = True
                if "certified" in q_params: st.session_state.is_certified = True
                if "qty" in q_params: st.session_state.bulk_paid_qty = int(q_params["qty"])
                
                # --- AUDIT LOGGING ---
                try:
                    import audit_engine
                    audit_engine.log_event(st.session_state.get("user_email"), "PAYMENT_VERIFIED", sess_id, {"tier": q_params.get("tier", "Unknown")})
                except: pass

                st.success("Payment Verified! Loading workspace...")
            else:
                st.error("❌ Payment Verification Failed or Expired.")
                st.session_state.app_mode = "store"
            
            # Race Condition Fix: Wait for state to settle before reload
            time.sleep(0.5) 
            st.query_params.clear()
            st.rerun()
            
    except Exception as e:
        # Hide sensitive error details in production
        print(f"Routing Error: {e}") # Log to console instead of UI

    # --- LAUNCH UI ---
    try:
        import ui_main
        ui_main.show_main_app()
    except Exception as e:
        # Generic error message for users
        st.error("⚠️ Application Error. Please refresh.")
        print(f"Critical UI Error: {e}") # Internal log
        if st.button("Hard Reset App"):
            st.session_state.clear()
            st.rerun()