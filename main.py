import streamlit as st
import ui_main
import ui_splash

# --- 1. PAGE CONFIG ---
st.set_page_config(page_title="VerbaPost", page_icon="✉️", layout="centered")

# --- 2. CSS STYLES (The Purple Theme) ---
def inject_global_css():
    st.markdown("""
    <style>
        /* Force Light Mode Background */
        .stApp { background-color: #f8f9fc; color: #2d3748; }
        
        /* Hide Streamlit Header */
        header {visibility: hidden;}
        
        /* Purple Gradient Buttons */
        div.stButton > button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white !important;
            border: none;
            border-radius: 25px;
            padding: 0.5rem 1.5rem;
            font-weight: 600;
            box-shadow: 0 4px 6px rgba(102, 126, 234, 0.25);
        }
        div.stButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 7px 14px rgba(102, 126, 234, 0.4);
        }
        
        /* Hero Banner (The Purple Box) */
        .hero-banner {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 40px;
            border-radius: 20px;
            color: white;
            text-align: center;
            margin-bottom: 30px;
            box-shadow: 0 10px 20px rgba(118, 75, 162, 0.3);
        }
        .hero-title { font-size: 3rem; font-weight: 800; margin: 0; color: white !important; }
        .hero-subtitle { font-size: 1.2rem; opacity: 0.9; margin-top: 10px; color: white !important; }
        
        /* Card Styling */
        div[data-testid="stVerticalBlockBorderWrapper"] > div {
            background-color: white;
            border-radius: 20px;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
            padding: 20px;
        }
    </style>
    """, unsafe_allow_html=True)

# --- 3. MAIN APP CONTROLLER ---
def main():
    inject_global_css() # <--- This applies the styles
    
    if "app_mode" not in st.session_state:
        st.session_state.app_mode = "splash"

    if st.session_state.app_mode == "splash":
        ui_splash.show_splash()
    else:
        ui_main.show_main_app()

if __name__ == "__main__":
    main()