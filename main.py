import streamlit as st
import ui_main
import ui_splash

# --- 1. GLOBAL PAGE CONFIG ---
st.set_page_config(
    page_title="VerbaPost",
    page_icon="✉️",
    layout="centered"
)

# --- 2. GLOBAL CSS (The Purple Theme - Stable Version) ---
def inject_global_css():
    st.markdown("""
    <style>
        /* --- CORE THEME OVERRIDES --- */
        /* Force Light Mode Background & Text regardless of user settings */
        .stApp {
            background-color: #f8f9fc;
            color: #2d3748; 
            font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        }
        
        /* HIDE STREAMLIT DEFAULT ELEMENTS */
        header {visibility: hidden;}
        .stDeployButton {display:none;}
        footer {visibility: hidden;}
        
        /* TEXT COLOR ENFORCEMENT */
        /* Forces headers and text to be dark grey, fixing the "Invisible Text" in dark mode */
        h1, h2, h3, h4, h5, h6, p, li, span, div { 
            color: #2d3748; 
        }
        
        /* --- CARD STYLING --- */
        /* White containers with soft shadow */
        div[data-testid="stVerticalBlockBorderWrapper"] > div {
            background-color: white;
            border-radius: 20px !important;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
            padding: 20px;
            border: 1px solid #e2e8f0;
            transition: box-shadow 0.3s ease;
        }
        
        /* --- BUTTON STYLING --- */
        /* Primary Buttons (Purple Gradient) */
        div.stButton > button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white !important;
            border: none;
            border-radius: 25px;
            padding: 0.5rem 1.5rem;
            font-weight: 600;
            box-shadow: 0 4px 6px rgba(102, 126, 234, 0.25);
        }
        /* Secondary Buttons (White with Grey Text) */
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
        /* Force white text inside the Hero, overriding the global dark text rule above */
        .hero-title { font-size: 3rem; font-weight: 800; margin: 0; color: white !important; }
        .hero-subtitle { font-size: 1.2rem; opacity: 0.9; margin-top: 10px; font-weight: 300; color: white !important; }
        .hero-banner p { color: white !important; }

        /* --- PRICING METRICS FIX --- */
        /* Ensures the $2.99 etc. are visible even if browser requests dark mode */
        [data-testid="stMetricLabel"] {
            color: #718096 !important; /* Grey for label */
        }
        [data-testid="stMetricValue"] {
            color: #2d3748 !important; /* Dark for price */
        }
        div[data-testid="stCaptionContainer"] {
            color: #718096 !important;
        }
    </style>
    """, unsafe_allow_html=True)

# --- 3. MAIN CONTROLLER ---
def main():
    # Inject CSS immediately
    inject_global_css()

    # Initialize Session State
    if "app_mode" not in st.session_state:
        st.session_state.app_mode = "splash"

    # Routing Logic
    if st.session_state.app_mode == "splash":
        ui_splash.show_splash()
    else:
        # Handles 'store', 'workspace', 'forgot_password', 'legal', etc.
        ui_main.show_main_app()

if __name__ == "__main__":
    main()