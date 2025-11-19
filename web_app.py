import streamlit as st
from views.splash import show_splash
from views.main_app import show_main_app
# from views.dashboard import show_dashboard (Coming Soon)

# --- PAGE CONFIG ---
st.set_page_config(page_title="VerbaPost", page_icon="📮", layout="centered")

# --- NAVIGATION STATE ---
if "current_view" not in st.session_state:
    st.session_state.current_view = "splash" 

# --- ROUTER ---
if st.session_state.current_view == "splash":
    show_splash()

elif st.session_state.current_view == "main_app":
    # Add a "Back to Home" button in the sidebar
    if st.sidebar.button("⬅️ Back to Home"):
        st.session_state.current_view = "splash"
        st.rerun()
        
    show_main_app()

elif st.session_state.current_view == "dashboard":
    st.title("Dashboard")
    st.info("Coming in the Subscription Tier Update")