import streamlit as st

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
        
        /* ANIMATION */
        @keyframes flyAcross {
            0% { transform: translateX(-200px); }
            100% { transform: translateX(110vw); }
        }
        .santa-sled {
            position: fixed; top: 20%; left: 0; font-size: 80px; z-index: 9999;
            animation: flyAcross 12s linear forwards; pointer-events: none;
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
        
        # 1. Marketing Links (e.g. ?tier=Santa)
        # Only activate if NOT returning from a payment flow
        if "tier" in q_params and "session_id" not in q_params:
            st.session_state.target_marketing_tier = q_params["tier"]

        # 2. SECURE STRIPE RETURN LOGIC
        if "session_id" in q_params:
            sess_id = q_params["session_id"]
            
            # Import engine to verify payment
            try:
                import payment_engine
                # Verify with Stripe API that this ID is real and paid
                is_paid = payment_engine.check_payment_status(sess_id)
            except ImportError:
                is_paid = False # Fail safe if engine missing

            if is_paid:
                # ✅ Payment Verified
                st.session_state.app_mode = "workspace"
                st.session_state.payment_complete = True
                
                # --- NEW: AUDIT LOGGING ---
                st.session_state.current_stripe_id = sess_id # Save for later use in ui_main
                try:
                    import audit_engine
                    user_email = st.session_state.get("user_email", "Unknown")
                    audit_engine.log_event(user_email, "PAYMENT_VERIFIED", sess_id, {"tier": q_params.get("tier", "Unknown")})
                except Exception as e:
                    print(f"Audit Log Failed: {e}")
                # --------------------------

                # Restore session flags from URL
                if "tier" in q_params: st.session_state.locked_tier = q_params["tier"]
                if "intl" in q_params: st.session_state.is_intl = True
                if "certified" in q_params: st.session_state.is_certified = True
                if "qty" in q_params: st.session_state.bulk_paid_qty = int(q_params["qty"])
                
                st.success("Payment Verified! Loading workspace...")
            else:
                # ❌ Payment Failed Verification
                st.error("❌ Payment Verification Failed. Please try again.")
                st.session_state.app_mode = "store"
            
            # Clear params to prevent replay loops
            st.query_params.clear()
            st.rerun()
            
    except Exception as e:
        print(f"Routing Error: {e}")

    # --- LAUNCH UI ---
    try:
        import ui_main
        ui_main.show_main_app()
    except Exception as e:
        st.error(f"⚠️ Application Error: {e}")
        if st.button("Hard Reset App"):
            st.session_state.clear()
            st.rerun()