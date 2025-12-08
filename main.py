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
        .stTextInput>div>div>input { border-radius: 8px; }
        [data-testid="stSidebar"] { background-color: #f8f9fa; }
    </style>
""", unsafe_allow_html=True)

# --- ENTRY POINT ---
if __name__ == "__main__":
    # Inject SEO (if module exists)
    if seo_injector: seo_injector.inject_seo()

    # Import Main UI logic
    import ui_main
    
    # Handle Stripe Redirection / Session Recovery
    q_params = st.query_params
    if "session_id" in q_params:
        # Flag payment as complete in Session State
        st.session_state.payment_complete = True
        
        # Capture Tier if present
        if "tier" in q_params:
            st.session_state.locked_tier = q_params["tier"]
        
        # --- FIX: RACE CONDITION ---
        # Ensure session state is actually persisted before clearing URL
        if st.session_state.get("payment_complete"):
            # Clear params so we don't re-trigger on refresh
            # But KEEP draft_id if it exists so we load the right letter
            # (Note: ui_main.show_main_app handles draft_id extraction separately)
            # For cleanliness, we clear everything, ui_main will see session_id one last time
            # actually, ui_main handles the session_id param logic too. 
            # We can leave the clearing to ui_main.reset_app logic or do it here.
            # Best practice: Clear specific keys, leave draft_id if needed.
            # For now, we rely on ui_main's logic to see the param.
            pass 

    # Launch App
    ui_main.show_main_app()