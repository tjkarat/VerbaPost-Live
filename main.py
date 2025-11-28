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
    
    # --- DEEP LINK & STRIPE RETURN LOGIC ---
    try:
        q_params = st.query_params
        
        # 1. Marketing Links (e.g. ?tier=Santa)
        # We only treat it as marketing if we are NOT returning from payment
        if "tier" in q_params and "session_id" not in q_params:
            st.session_state.target_marketing_tier = q_params["tier"]

        # 2. Stripe Return (e.g. ?session_id=...&tier=Civic)
        if "session_id" in q_params:
            st.session_state.app_mode = "workspace"
            st.session_state.payment_complete = True
            
            # --- THE FIX: CAPTURE TIER FROM URL ---
            if "tier" in q_params:
                st.session_state.locked_tier = q_params["tier"]
            # --------------------------------------
            
            # RECOVER INTERNATIONAL STATUS
            if "intl" in q_params:
                st.session_state.is_intl = True
            
            # Clear params to prevent reload loops
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