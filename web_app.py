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
import streamlit.components.v1 as components 


# --- CONFIG (Must run early) ---
st.set_page_config(
    page_title="VerbaPost | Send Mail to Inmates, Congress & Homeowners", 
    page_icon="📮", 
    layout="wide", # Use wide layout for better sidebar visibility
    initial_sidebar_state="expanded" # Force sidebar to be open
)

# --- GOOGLE ANALYTICS INJECTION ---
GA_MEASUREMENT_ID = "G-D3P178CESF"

def inject_google_analytics():
    """Injects the Google Analytics tracking script into the page using st.markdown."""
    if GA_MEASUREMENT_ID and GA_MEASUREMENT_ID.startswith("G-"):
        tracking_script = f"""
            <script async src="https://www.googletagmanager.com/gtag/js?id={GA_MEASUREMENT_ID}"></script>
            <script>
              window.dataLayer = window.dataLayer || [];
              function gtag(){{dataLayer.push(arguments);}}
              gtag('js', new Date());
              gtag('config', '{GA_MEASUREMENT_ID}');
            </script>
            """
        # Using st.markdown with unsafe_allow_html=True to push the script high in the DOM
        st.markdown(tracking_script, unsafe_allow_html=True)
    else:
        pass

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

# 1. INTERCEPT STRIPE RETURN
qp = st.query_params
if "session_id" in qp:
    if "current_view" not in st.session_state:
        st.session_state.current_view = "main_app"

# 4. HANDLERS
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

# 5. STATE
if "current_view" not in st.session_state: st.session_state.current_view = "splash" 
if "user" not in st.session_state: st.session_state.user = None


# --- 6. SIDEBAR CONTROLLER (RENDERED DIRECTLY) ---

# Inject CSS and GA immediately after config/imports
inject_custom_css()
inject_google_analytics()


with st.sidebar:
    
    # 6.1 Navigation Buttons
    if st.button("🏠 Home", use_container_width=True):
        st.session_state.current_view = "splash"
        st.rerun()
    
    # 6.2 User/Admin Logic (Only renders if a user object exists)
    if st.session_state.get("user"):
        st.caption(f"User: {st.session_state.user_email}")
        
        # ADMIN CHECK LOGIC
        is_admin = False
        try:
            admin_email = st.secrets["admin"]["email"].strip().lower()
            # Access user email via the complex path (Supabase object)
            user_email = st.session_state.user.user.email.strip().lower()
            if user_email == admin_email: 
                is_admin = True
        except: 
            # This debug warning helps diagnose the failure
            st.warning("Admin check logic failed. Check st.secrets or user object path.")
            pass

        if is_admin: 
            # ADMIN PANEL BUTTON: Only visible if is_admin is True
            if st.button("🔐 Admin Panel", type="primary", use_container_width=True):
                st.session_state.current_view = "admin"
                st.rerun()

        if st.button("Log Out", use_container_width=True):
            # Clear all session state keys
            for key in list(st.session_state.keys()): del st.session_state[key]
            st.rerun()
    else:
        # 6.3 Login/Signup Button for Guest Users
        if st.session_state.current_view != "login" and st.session_state.current_view != "splash":
            if st.button("Log In / Sign Up", use_container_width=True):
                st.session_state.current_view = "login"
                st.rerun()

    # 6.4 Footer Links (Always visible at the bottom of the sidebar)
    st.divider()
    st.markdown("📧 **Help:** support@verbapost.com")
    if st.button("⚖️ Terms & Privacy", type="secondary", use_container_width=True):
        st.session_state.current_view = "legal"
        st.rerun()
        
# --- 7. ROUTER ---
        
# The main content router (executes outside of the sidebar context)
if st.session_state.current_view == "splash":
    ui_splash.show_splash()
elif st.session_state.current_view == "login":
    ui_login.show_login(handle_login, handle_signup)
elif st.session_state.current_view == "admin":
    # Renders the content of ui_admin.py
    ui_admin.show_admin()
elif st.session_state.current_view == "legal": 
    ui_legal.show_legal()
elif st.session_state.current_view == "main_app":
    # Renders the main store/workspace content
    ui_main.show_main_app()