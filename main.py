import streamlit as st
import ui_main
import sys

# --- 1. CONFIG (Minimal Config) ---
st.set_page_config(
    page_title="VerbaPost",
    page_icon="📮",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- 2. GLOBAL STYLES & CONTROLLER ---
if __name__ == "__main__":
    # Hand off control immediately to ui_main (which handles CSS and routing)
    try:
        ui_main.show_main_app()
    except Exception as e:
        # Emergency print for debugging
        st.error(f"FATAL APP CRASH: {type(e).__name__} - Please check ui_main.py for syntax errors.")
        if st.button("Reset Session"):
            st.session_state.clear()
            st.rerun()