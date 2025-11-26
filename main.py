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
        .stApp { background-color: #f8f9fc; color: #2d3748; font-family: 'Helvetica Neue', sans-serif; }
        header, .stDeployButton, footer { visibility: hidden; }
        .stTextInput input, .stSelectbox div, div[data-baseweb="select"] > div {
            background-color: white !important; color: #2d3748 !important; border: 1px solid #e2e8f0 !important;
        }
        [data-testid="stSidebar"] { background-color: white !important; border-right: 1px solid #e2e8f0; }
        div.stButton > button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white !important; border: none; border-radius: 25px; padding: 0.5rem 1.5rem;
        }
        div.stButton > button[kind="secondary"] {
            background: white; color: #555 !important; border: 1px solid #ddd;
        }
    </style>
    """, unsafe_allow_html=True)

# --- 3. RUN ---
if __name__ == "__main__":
    inject_global_css()
    # Hand off completely to ui_main. No logic here.
    ui_main.show_main_app()