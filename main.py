import streamlit as st
import ui_main

# --- 1. CONFIG (Force Sidebar Expanded) ---
st.set_page_config(
    page_title="VerbaPost",
    page_icon="📮",
    layout="centered",
    initial_sidebar_state="expanded" 
)

# --- 2. CSS (Dark Text & Clean UI) ---
def inject_global_css():
    st.markdown("""
    <style>
        .stApp { background-color: #f8f9fc; }
        
        /* Force Dark Text */
        h1, h2, h3, h4, h5, h6, p, li, label, span, div {
            color: #2d3748 !important;
        }
        
        /* Inputs */
        .stTextInput input, .stSelectbox div {
            background-color: white !important; 
            color: #2d3748 !important; 
            border: 1px solid #e2e8f0 !important;
        }
        
        /* Sidebar */
        [data-testid="stSidebar"] { 
            background-color: white !important; 
            border-right: 1px solid #e2e8f0; 
        }
        
        /* Buttons */
        div.stButton > button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white !important; border: none; border-radius: 25px;
        }
        div.stButton > button p { color: white !important; }
        
        div.stButton > button[kind="secondary"] {
            background: white; color: #555 !important; border: 1px solid #ddd;
        }
    </style>
    """, unsafe_allow_html=True)

# --- 3. RUN ---
if __name__ == "__main__":
    inject_global_css()
    
    if "app_mode" not in st.session_state:
        st.session_state.app_mode = "splash"
    
    try:
        ui_main.show_main_app()
    except Exception as e:
        st.error(f"⚠️ App Error: {e}")
        if st.button("Hard Reset"):
            st.session_state.clear()
            st.rerun()