import streamlit as st
from splash_view import show_splash
from main_app_view import show_main_app

# --- PAGE CONFIG ---
st.set_page_config(page_title="VerbaPost", page_icon="📮", layout="centered")

# --- CSS INJECTOR (Removes Streamlit Branding) ---
def inject_custom_css():
    st.markdown("""
        <style>
        /* 1. Hide Streamlit Branding */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        
        /* 2. Remove Top Padding (The Forehead) */
        .block-container {
            padding-top: 1rem !important;
            padding-bottom: 1rem !important;
        }
        
        /* 3. Button Styling */
        div.stButton > button {
            border-radius: 8px;
            font-weight: 600;
            border: 1px solid #e0e0e0;
        }
        
        /* 4. Input Field Styling */
        input {
            border-radius: 5px !important;
        }
        </style>
        """, unsafe_allow_html=True)

# Apply the styling immediately
inject_custom_css()

# --- NAVIGATION STATE ---
if "current_view" not in st.session_state:
    st.session_state.current_view = "splash" 

# --- ROUTER ---
if st.session_state.current_view == "splash":
    show_splash()

elif st.session_state.current_view == "main_app":
    # Custom Sidebar Navigation
    with st.sidebar:
        st.subheader("Navigation")
        if st.button("🏠 Home", use_container_width=True):
            st.session_state.current_view = "splash"
            st.rerun()
        st.caption("VerbaPost v0.9 (Alpha)")
        
    show_main_app()