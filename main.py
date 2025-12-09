import streamlit as st
try: import seo_injector
except: seo_injector = None
try: import secrets_manager
except: secrets_manager = None

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="VerbaPost - Making sending physical mail easier",
    page_icon="📮",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- GLOBAL STYLES ---
st.markdown("""
    <style>
        .stButton>button { width: 100%; border-radius: 8px; font-weight: 600; }
        .stTextInput>div>div>input { border-radius: 8px; font-family: 'Source Sans Pro', sans-serif; }
        .stTextArea>div>div>textarea { border-radius: 8px; font-family: 'Source Sans Pro', sans-serif; }
        [data-testid="stSidebar"] { background-color: #f8f9fa; }
    </style>
""", unsafe_allow_html=True)

# --- ENTRY POINT ---
if __name__ == "__main__":
    # 1. SEO Injection (First thing)
    if seo_injector: 
        seo_injector.inject_seo()

    # 2. CRITICAL: Handle Stripe Return Logic HERE (Before loading UI)
    # This prevents the infinite loop by catching the params immediately.
    if "session_id" in st.query_params:
        
        # A. Capture Payment Success
        st.session_state.payment_complete = True
        st.session_state.app_mode = "workspace"
        
        # B. Capture Tier & Options
        if "tier" in st.query_params: 
            st.session_state.locked_tier = st.query_params["tier"]
        if "qty" in st.query_params: 
            st.session_state.bulk_paid_qty = int(st.query_params["qty"])
        if "certified" in st.query_params: 
            st.session_state.is_certified = True
            
        # C. NUKE THE URL PARAMS
        # This breaks the loop. The next run will be clean.
        st.query_params.clear()
        
        # D. Restart immediately with clean URL
        st.rerun()

    # 3. Load Main App Interface
    # We only import this if we aren't rerunning, saving resources.
    import ui_main
    ui_main.show_main_app()