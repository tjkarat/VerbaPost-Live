import streamlit as st
import ui_main

# --- 1. CONFIG ---
st.set_page_config(
    page_title="VerbaPost",
    page_icon="📮",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- 2. CSS ---
def inject_global_css():
    st.markdown("""
    <style>
        /* Core Theme */
        .stApp { background-color: #f8f9fc; color: #2d3748; font-family: 'Helvetica Neue', sans-serif; }
        
        /* Hide default elements */
        header, .stDeployButton, footer { visibility: hidden; }
        
        /* Fix Input Visibility (Force White BG) */
        .stTextInput input, .stSelectbox div, div[data-baseweb="select"] > div {
            background-color: white !important; 
            color: #2d3748 !important; 
            border: 1px solid #e2e8f0 !important;
        }
        
        /* Sidebar Styling */
        [data-testid="stSidebar"] { 
            background-color: white !important; 
            border-right: 1px solid #e2e8f0; 
        }
        
        /* Primary Buttons (Purple Gradient) */
        div.stButton > button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white !important; 
            border: none; 
            border-radius: 25px; 
            padding: 0.5rem 1.5rem;
        }
        
        /* Secondary Buttons (White) */
        div.stButton > button[kind="secondary"] {
            background: white; 
            color: #555 !important; 
            border: 1px solid #ddd;
        }
    </style>
    """, unsafe_allow_html=True)

# --- 3. RUN ---
if __name__ == "__main__":
    inject_global_css()
    
    # Initialize App Mode
    if "app_mode" not in st.session_state:
        st.session_state.app_mode = "splash"
    
    # Hand off to UI Controller
    # ui_main.show_main_app() handles all routing (Splash -> Login -> Store -> Workspace)
    try:
        ui_main.show_main_app()
    except Exception as e:
        st.error(f"⚠️ Application Error: {e}")
        if st.button("Hard Reset App"):
            st.session_state.clear()
            st.rerun()