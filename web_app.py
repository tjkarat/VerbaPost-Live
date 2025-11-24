import streamlit as st
import importlib
import ui_splash
import auth_engine 
import payment_engine
import database
import ui_main
import ui_login
import ui_admin
import ui_legal 

# 1. INTERCEPT STRIPE RETURN
qp = st.query_params
if "session_id" in qp:
    if "current_view" not in st.session_state:
        st.session_state.current_view = "main_app"

# 3. CONFIG (Removed collapsed state)
st.set_page_config(
    page_title="VerbaPost | Send Mail to Inmates, Congress & Homeowners", 
    page_icon="📮", 
    layout="centered"
    # initial_sidebar_state="collapsed" <-- REMOVED THIS LINE
)

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

# 4. HANDLERS (No change)
def handle_login(email, password):
    user, error = auth_engine.sign_in(email, password)
    if error:
        st.error(f"Login Failed: {error}")
    else:
        st.success("Welcome!")
        st.session_state.user = user
        st.session_state.user_email = email
        try:
            saved = auth_engine.get_current_address(email)
            if saved:
                st.session_state["from_name"] = saved.get("name", "")
                st.session_state["from_street"] = saved.get("street", "")
                st.session_state["from_city"] = saved.get("city", "")
                st.session_state["from_state"] = saved.get("state", "")
                st.session_state["from_zip"] = saved.get("zip", "")
                st.session_state["selected_language"] = saved.get("language", "English")
        except: pass
        st.session_state.current_view = "main_app"
        st.rerun()

def handle_signup(email, password, name, street, city, state, zip_code, language):
    user, error = auth_engine.sign_up(email, password, name, street, city, state, zip_code, language)
    if error:
        st.error(f"Error: {error}")
    else:
        st.success("Created!")
        st.session_state.user = user
        st.session_state.user_email = email
        st.session_state.selected_language = language
        st.session_state.current_view = "main_app"
        st.rerun()

# 5. STATE (No change)
if "current_view" not in st.session_state: st.session_state.current_view = "splash" 
if "user" not in st.session_state: st.session_state.user = None


# --- 6. SIDEBAR AND ADMIN CONTROLLER (RENDERED UNCONDITIONALLY) ---

def render_admin_and_logout_sidebar():
    """Renders the persistent sidebar content, including the Admin button."""
    
    # Navigation Buttons
    if st.button("🏠 Home", use_container_width=True):
        st.session_state.current_view = "splash"
        st.rerun()
    
    # Only render user-specific elements if a user is logged in
    if st.session_state.get("user"):
        st.caption(f"User: {st.session_state.user_email}")
        
        # ADMIN CHECK LOGIC
        is_admin = False
        try:
            admin_email = st.secrets["admin"]["email"].strip().lower()
            # Must safely access the email property of the user object
            user_email = st.session_state.user.user.email.strip().lower()
            if user_email == admin_email: 
                is_admin = True
        except: pass

        if is_admin: 
            if st.button("🔐 Admin Panel", type="primary", use_container_width=True):
                st.session_state.current_view = "admin"
                st.rerun()

        if st.button("Log Out", use_container_width=True):
            # Clear all session state keys
            for key in list(st.session_state.keys()): del st.session_state[key]
            st.rerun()
    else:
        # If not logged in, show a way to login/signup if on the main page
        if st.session_state.current_view != "login" and st.session_state.current_view != "splash":
            if st.button("Log In / Sign Up", use_container_width=True):
                st.session_state.current_view = "login"
                st.rerun()


# --- 7. ROUTER ---

# Force the sidebar to render always
with st.sidebar:
    render_admin_and_logout_sidebar()
    
    # Footer links, rendered at the bottom of the sidebar
    st.divider()
    st.markdown("📧 **Help:** support@verbapost.com")
    if st.button("⚖️ Terms & Privacy", type="secondary", use_container_width=True):
        st.session_state.current_view = "legal"
        st.rerun()
        
# The main content router
if st.session_state.current_view == "splash":
    ui_splash.show_splash()
elif st.session_state.current_view == "login":
    ui_login.show_login(handle_login, handle_signup)
elif st.session_state.current_view == "admin":
    # This is where ui_admin.show_admin() displays the console
    ui_admin.show_admin()
elif st.session_state.current_view == "legal": 
    ui_legal.show_legal()
elif st.session_state.current_view == "main_app":
    # This calls ui_main.show_main_app(), which contains the store and workspace
    ui_main.show_main_app()