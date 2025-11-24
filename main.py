import streamlit as st
import ui_main
import ui_splash

# --- 1. GLOBAL PAGE CONFIG ---
st.set_page_config(
    page_title="VerbaPost",
    page_icon="✉️",
    layout="centered"
)

# --- 2. GLOBAL CSS (The Purple Theme - Final UI Fix) ---
def inject_global_css():
    st.markdown("""
    <style>
        /* --- CORE THEME --- */
        .stApp {
            background-color: #f8f9fc;
            color: #2d3748; 
            font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        }
        
        /* HIDE DEFAULTS */
        header {visibility: hidden;}
        .stDeployButton {display:none;}
        footer {visibility: hidden;}
        
        /* TEXT COLOR FORCE */
        h1, h2, h3, h4, h5, h6, p, li, span, div, label { 
            color: #2d3748 !important; 
        }
        /* --- PATCH FOR BLACK WIDGETS --- */
        
        /* Force Tabs to be White */
        .stTabs [data-baseweb="tab-list"] {
            background-color: white !important;
        }
        .stTabs [data-baseweb="tab"] {
            color: #2d3748 !important;
        }
        
        /* Force Audio Input to be White/Light */
        .stAudio {
            background-color: white !important;
            color: black !important;
        }
        
        /* Force generic buttons to be light if not primary */
        button {
            color: #2d3748; 
        }
        /* --- FIX DROPDOWNS & INPUTS (The Nuclear Option) --- */
        
        /* 1. The Container of the Dropdown Options (The floating black box in your screenshot) */
        div[data-baseweb="popover"], div[data-baseweb="popover"] > div, ul[data-baseweb="menu"] {
            background-color: white !important;
            border: 1px solid #e2e8f0 !important;
        }
        
        /* 2. The Text inside the Dropdown Options */
        li[data-baseweb="option"] {
            color: #2d3748 !important; /* Dark Text */
            background-color: white !important; /* White Background */
        }
        
        /* 3. Hover Effect on Options */
        li[data-baseweb="option"]:hover, li[data-baseweb="option"][aria-selected="true"] {
            background-color: #f7fafc !important; /* Light Grey Hover */
            color: #667eea !important; /* Purple Text on Hover */
        }
        
        /* 4. The Closed Dropdown Box & Text Inputs */
        .stTextInput input, div[data-baseweb="select"] > div {
            background-color: white !important;
            color: #2d3748 !important;
            border: 1px solid #e2e8f0 !important;
            border-radius: 10px !important;
        }

        /* --- SIDEBAR STYLING --- */
        [data-testid="stSidebar"] {
            background-color: #ffffff !important;
            border-right: 1px solid #e2e8f0;
        }
        [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
             color: #2d3748 !important;
        }
        
        /* --- CARD STYLING --- */
        div[data-testid="stVerticalBlockBorderWrapper"] > div {
            background-color: white;
            border-radius: 20px !important;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
            padding: 20px;
            border: 1px solid #e2e8f0;
            transition: box-shadow 0.3s ease;
        }
        
        /* --- BUTTON STYLING --- */
        div.stButton > button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white !important;
            border: none;
            border-radius: 25px;
            padding: 0.5rem 1.5rem;
            font-weight: 600;
            box-shadow: 0 4px 6px rgba(102, 126, 234, 0.25);
        }
        div.stButton > button[kind="secondary"] {
            background: white;
            color: #555 !important;
            border: 1px solid #ddd;
        }

        /* --- HERO BANNER --- */
        .hero-banner {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 40px;
            border-radius: 20px;
            color: white !important;
            margin-bottom: 30px;
            text-align: center;
            box-shadow: 0 10px 20px rgba(118, 75, 162, 0.3);
        }
        .hero-title { font-size: 3rem; font-weight: 800; margin: 0; color: white !important; }
        .hero-subtitle { font-size: 1.2rem; opacity: 0.9; margin-top: 10px; font-weight: 300; color: white !important; }
        .hero-banner p { color: white !important; }

        /* --- METRICS FIX --- */
        [data-testid="stMetricLabel"] { color: #718096 !important; }
        [data-testid="stMetricValue"] { color: #2d3748 !important; }
        div[data-testid="stCaptionContainer"] { color: #718096 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. MAIN CONTROLLER ---
def main():
    # Inject CSS immediately
    inject_global_css()

    if "app_mode" not in st.session_state:
        st.session_state.app_mode = "splash"

    if st.session_state.app_mode == "splash":
        ui_splash.show_splash()
    else:
        ui_main.show_main_app()

if __name__ == "__main__":
    main()