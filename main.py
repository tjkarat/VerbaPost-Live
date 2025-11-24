import streamlit as st
import ui_main
import ui_splash

# --- 1. GLOBAL PAGE CONFIG ---
st.set_page_config(page_title="VerbaPost", page_icon="✉️", layout="centered")

# --- 2. GLOBAL CSS ---
def inject_global_css():
    st.markdown("""
    <style>
        /* Core Theme */
        .stApp { background-color: #f8f9fc; color: #2d3748; font-family: 'Helvetica Neue', sans-serif; }
        header, .stDeployButton, footer { visibility: hidden; }
        
        /* Text & Input Fixes */
        h1, h2, h3, p, div, label, span { color: #2d3748 !important; }
        .stTextInput input, .stSelectbox div, div[data-baseweb="select"] > div {
            background-color: white !important;
            color: #2d3748 !important;
            border: 1px solid #e2e8f0 !important;
        }
        
        /* Sidebar & Menus */
        [data-testid="stSidebar"] { background-color: white !important; border-right: 1px solid #e2e8f0; }
        div[data-baseweb="popover"], ul[data-baseweb="menu"] { background-color: white !important; }
        li[data-baseweb="option"] { color: #2d3748 !important; }
        
        /* Buttons */
        div.stButton > button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white !important;
            border: none; border-radius: 25px; padding: 0.5rem 1.5rem;
        }
        div.stButton > button[kind="secondary"] {
            background: white; color: #555 !important; border: 1px solid #ddd;
        }
        
        /* Hero */
        .hero-banner {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 40px; border-radius: 20px; color: white !important;
            text-align: center; margin-bottom: 30px;
        }
        .hero-title { font-size: 3rem; font-weight: 800; margin: 0; color: white !important; }
        .hero-subtitle { font-size: 1.2rem; opacity: 0.9; margin-top: 10px; color: white !important; }
        .hero-banner p { color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. MAIN CONTROLLER ---
def main():
    inject_global_css()

    # Initialize Session
    if "app_mode" not in st.session_state:
        st.session_state.app_mode = "splash"

    # --- LOGIC FIX: DETECT STRIPE RETURN ---
    # If URL has session_id, force app_mode to 'store' or 'workspace' so ui_main runs
    if "session_id" in st.query_params:
        st.session_state.app_mode = "workspace"

    # Routing
    if st.session_state.app_mode == "splash":
        ui_splash.show_splash()
    else:
        # This handles Login, Store, Workspace, etc.
        ui_main.show_main_app()

if __name__ == "__main__":
    main()