import streamlit as st
import ui_main

# --- 1. CONFIG (Force Sidebar Expanded) ---
st.set_page_config(
    page_title="VerbaPost",
    page_icon="📮",
    layout="centered",
    initial_sidebar_state="expanded" 
)

# --- 2. GLOBAL CSS (Force Dark Text & Clean UI) ---
def inject_global_css():
    st.markdown("""
    <style>
        /* Main Background */
        .stApp { background-color: #f8f9fc; }
        
        /* Force Text Color to Dark Grey (Overrides Browser Dark Mode) */
        h1, h2, h3, h4, h5, h6, p, li, label, span, div, .stMarkdown {
            color: #2d3748 !important;
        }
        
        /* Hide Defaults */
        header, .stDeployButton, footer { visibility: hidden; }
        
        /* Inputs: Force White Background */
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
        
        /* Primary Buttons */
        div.stButton > button[kind="primary"] {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
            color: white !important; 
            border: none; 
            border-radius: 25px; 
            padding: 0.5rem 1.5rem;
        }
        /* Fix text color INSIDE primary buttons to be white */
        div.stButton > button[kind="primary"] p { color: white !important; }
        
        /* Secondary Buttons (FIXED VISIBILITY) */
        div.stButton > button[kind="secondary"] {
            background-color: white !important; 
            color: #2d3748 !important; /* Force dark text */
            border: 1px solid #e2e8f0 !important;
            border-radius: 25px;
        }
        /* Explicitly target text inside secondary buttons */
        div.stButton > button[kind="secondary"] p { 
            color: #2d3748 !important; 
        }
    </style>
    """, unsafe_allow_html=True)

# --- 3. RUN CONTROLLER ---
if __name__ == "__main__":
    inject_global_css()
    
    # Init App State if missing
    if "app_mode" not in st.session_state:
        st.session_state.app_mode = "splash"
    
    # Launch UI
    try:
        ui_main.show_main_app()
    except Exception as e:
        st.error(f"⚠️ App Error: {e}")
        if st.button("Hard Reset"):
            st.session_state.clear()
            st.rerun()