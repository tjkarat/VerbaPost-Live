import streamlit as st
import ui_main

# --- 1. CONFIG ---
st.set_page_config(
    page_title="VerbaPost",
    page_icon="📮",
    layout="centered",
    initial_sidebar_state="collapsed" # <--- FIXED: Default to hidden
)

# --- 2. CSS ---
def inject_global_css():
    st.markdown("""
    <style>
        .stApp { background-color: #f8f9fc; color: #2d3748; font-family: 'Helvetica Neue', sans-serif; }
        header, .stDeployButton, footer { visibility: hidden; }
        
        /* Inputs */
        .stTextInput input, .stSelectbox div, div[data-baseweb="select"] > div {
            background-color: white !important; color: #2d3748 !important; border: 1px solid #e2e8f0 !important;
        }
        
        /* Sidebar */
        [data-testid="stSidebar"] { background-color: white !important; border-right: 1px solid #e2e8f0; }
        
        /* Buttons */
        div.stButton > button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white !important; border: none; border-radius: 25px; padding: 0.5rem 1.5rem;
        }
        div.stButton > button[kind="secondary"] {
            background: white; color: #555 !important; border: 1px solid #ddd;
        }
    </style>
    """, unsafe_allow_html=True)

# --- 3. CONTROLLER ---
if __name__ == "__main__":
    inject_global_css()

    if "app_mode" not in st.session_state:
        st.session_state.app_mode = "splash"
    
    if "session_id" in st.query_params:
        st.session_state.app_mode = "workspace"

    try:
        ui_main.show_main_app()
    except Exception as e:
        st.error(f"⚠️ App Error: {e}")
        if st.button("Hard Reset"):
            st.session_state.clear()
            st.rerun()