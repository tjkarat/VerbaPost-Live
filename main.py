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
        /* Force Light Mode Background & Text */
        .stApp {
            background-color: #f8f9fc;
            color: #2d3748; 
            font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        }
        
        /* HIDE STREAMLIT DEFAULT ELEMENTS */
        header {visibility: hidden;}
        .stDeployButton {display:none;}
        footer {visibility: hidden;}
        
        /* HEADERS */
        h1, h2, h3 { color: #2d3748; font-weight: 700; }
        
        /* CARDS (White containers with shadow) */
        div[data-testid="stVerticalBlockBorderWrapper"] > div {
            background-color: white;
            border-radius: 20px !important;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
            padding: 20px;
            border: 1px solid #e2e8f0;
            transition: box-shadow 0.3s ease;
        }
        div[data-testid="stVerticalBlockBorderWrapper"] > div:hover {
            box-shadow: 0 10px 15px -3px rgba(118, 75, 162, 0.1);
            /* Removed transform to prevent click errors */
        }

        /* PRIMARY BUTTONS (Purple Gradient) */
        div.stButton > button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white !important;
            border: none;
            border-radius: 25px;
            padding: 0.5rem 1.5rem;
            font-weight: 600;
            box-shadow: 0 4px 6px rgba(102, 126, 234, 0.25);
            transition: box-shadow 0.3s ease;
        }
        div.stButton > button:hover {
            box-shadow: 0 7px 14px rgba(102, 126, 234, 0.4);
            color: white !important;
            /* Removed transform to prevent click errors */
        }
        
        /* SECONDARY BUTTONS */
        div.stButton > button[kind="secondary"] {
            background: white;
            color: #555 !important;
            border: 1px solid #ddd;
        }

        /* HERO BANNER CLASS */
        .hero-banner {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 40px;
            border-radius: 20px;
            color: white;
            margin-bottom: 30px;
            text-align: center;
            box-shadow: 0 10px 20px rgba(118, 75, 162, 0.3);
        }
        .hero-title { font-size: 3rem; font-weight: 800; margin: 0; color: white !important; }
        .hero-subtitle { font-size: 1.2rem; opacity: 0.9; margin-top: 10px; font-weight: 300; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. MAIN CONTROLLER ---
def main():
    # Inject CSS immediately
    inject_global_css()

    # Initialize Session State
    if "app_mode" not in st.session_state:
        st.session_state.app_mode = "splash"

    # Routing
    if st.session_state.app_mode == "splash":
        ui_splash.show_splash()
    else:
        # Handles 'store', 'workspace', 'forgot_password', etc.
        ui_main.show_main_app()

if __name__ == "__main__":
    main()