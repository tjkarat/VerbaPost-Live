import streamlit as st
import auth_engine 
import payment_engine

# 1. INTERCEPT STRIPE RETURN BEFORE ANYTHING ELSE
# Check query params directly
qp = st.query_params
if "session_id" in qp:
    # Force state to main_app immediately
    if "current_view" not in st.session_state:
        st.session_state.current_view = "main_app"

# 2. NOW DO IMPORTS (This prevents circular logic)
from ui_splash import show_splash
from ui_main import show_main_app
from ui_login import show_login

# 3. CONFIG
st.set_page_config(page_title="VerbaPost", page_icon="📮", layout="centered")

# 4. CSS
def inject_custom_css():
    st.markdown("""
        <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        .block-container {padding-top: 1rem !important; padding-bottom: 1rem !important;}
        div.stButton > button {border-radius: 8px; font-weight: 600; border: 1px solid #e0e0e0;}
        input {border-radius: 5px !important;}
        </style>
        """, unsafe_allow_html=True)
inject_custom_css()

# 5. HANDLERS
def handle_login(email, password):
    user, error = auth_engine.sign_in(email, password)
    if error:
        st.error(f"Login Failed: {error}")
    else:
        st.success("Welcome!")
        st.session_state.user = user
        st.session_state.user_email = email
        saved = auth_engine.get_current_address(email)
        if saved:
            # Populate session
            st.session_state["from_name"] = saved.get("name", "")
            st.session_state["from_street"] = saved.get("street", "")
            st.session_state["from_city"] = saved.get("city", "")
            st.session_state["from_state"] = saved.get("state", "")
            st.session_state["from_zip"] = saved.get("zip", "")
        st.session_state.current_view = "main_app"
        st.rerun()

def handle_signup(email, password, name, street, city, state, zip_code):
    user, error = auth_engine.sign_up(email, password, name, street, city, state, zip_code)
    if error:
        st.error(f"Error: {error}")
    else:
        st.success("Created!")
        st.session_state.user = user
        st.session_state.user_email = email
        st.session_state.current_view = "main_app"
        st.rerun()

# 6. DEFAULT STATE
if "current_view" not in st.session_state:
    st.session_state.current_view = "splash" 
if "user" not in st.session_state:
    st.session_state.user = None

# 7. ROUTER
if st.session_state.current_view == "splash":
    show_splash()

elif st.session_state.current_view == "login":
    show_login(handle_login, handle_signup)

elif st.session_state.current_view == "main_app":
    # Sidebar
    with st.sidebar:
        if st.button("🏠 Home", use_container_width=True):
            st.session_state.current_view = "splash"
            st.rerun()
        if st.session_state.get("user"):
            st.caption(f"User: {st.session_state.user_email}")
            if st.button("Log Out"):
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()
        
    show_main_app()