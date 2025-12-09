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
    # 1. SEO Injection
    if seo_injector: 
        seo_injector.inject_seo()

    # 2. STRIPE RETURN LOGIC
    # We handle this HERE to prevent the app from loading the UI twice
    if "session_id" in st.query_params:
        
        # A. Mark Payment as Complete
        st.session_state.payment_complete = True
        
        # B. Force the app to go to Workspace (Compose)
        st.session_state.app_mode = "workspace"
        
        # C. Restore options from URL if present (legacy fallback)
        if "tier" in st.query_params: 
            st.session_state.locked_tier = st.query_params["tier"]
        if "certified" in st.query_params: 
            st.session_state.is_certified = True
            
        # D. Clean URL so we don't trigger this again on refresh
        st.query_params.clear()
        
        # E. Restart the app immediately with the new state
        st.rerun()

    # 3. Load Main App Interface
    import ui_main
    ui_main.show_main_app()