import streamlit as st
import streamlit.components.v1 as components

# --- 1. PAGE CONFIG (Must be first) ---
st.set_page_config(
    page_title="VerbaPost", 
    page_icon="📮", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. ANALYTICS (Injected into Head) ---
# We use a specific ID to ensure this script runs in the main window
GA_ID = "G-D3P178CESF"
st.markdown(f"""
    <script async src="https://www.googletagmanager.com/gtag/js?id={GA_ID}"></script>
    <script>
        window.dataLayer = window.dataLayer || [];
        function gtag(){{dataLayer.push(arguments);}}
        gtag('js', new Date());
        gtag('config', '{GA_ID}');
    </script>
""", unsafe_allow_html=True)

# --- 3. GLOBAL BLUE THEME ---
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Professional Blue Styling */
    .stApp {
        background-color: #ffffff;
    }
    
    /* Button Styling - Trustworthy Blue */
    div.stButton > button {
        background-color: white;
        border: 1px solid #2980b9;
        color: #2980b9;
        border-radius: 8px;
        transition: all 0.3s;
    }
    div.stButton > button:hover {
        background-color: #2980b9;
        color: white;
        border-color: #2980b9;
    }
    
    /* Primary Buttons (Solid Blue) */
    button[kind="primary"] {
        background-color: #2980b9 !important;
        color: white !important;
        border: none !important;
    }
    button[kind="primary"]:hover {
        background-color: #3498db !important;
        box-shadow: 0 4px 10px rgba(41, 128, 185, 0.3);
    }
    </style>
""", unsafe_allow_html=True)

# --- 4. IMPORTS ---
try:
    import ui_splash
    import ui_login
    import ui_admin
    import ui_legal
    import ui_main
    import auth_engine
except ImportError as e:
    st.error(f"System Error: {e}")
    st.stop()

# --- 5. SESSION STATE ---
if "current_view" not in st.session_state: st.session_state.current_view = "splash"
if "user" not in st.session_state: st.session_state.user = None

# --- 6. AUTH HANDLERS ---
def handle_login_wrapper(email, password):
    user, error = auth_engine.sign_in(email, password)
    if error:
        st.error(f"Login Failed: {error}")
    else:
        st.session_state.user = user
        st.session_state.user_email = email
        # FORCE VIEW CHANGE
        st.session_state.current_view = "main_app"
        st.rerun()

def handle_signup_wrapper(email, password, name, street, city, state, zip_code, language):
    user, error = auth_engine.sign_up(email, password, name, street, city, state, zip_code, language)
    if error:
        st.error(f"Signup Failed: {error}")
    else:
        st.session_state.user = user
        st.session_state.user_email = email
        st.session_state.selected_language = language
        st.session_state.current_view = "main_app"
        st.rerun()

# --- 7. ADMIN CHECK (DEBUG MODE) ---
def check_is_admin():
    if not st.session_state.get("user"): return False
    
    # 1. Get Configured Admin Email
    admin_email = ""
    if "ADMIN_EMAIL" in st.secrets: admin_email = st.secrets["ADMIN_EMAIL"]
    elif "admin" in st.secrets and "email" in st.secrets["admin"]: admin_email = st.secrets["admin"]["email"]
    
    # 2. Get Current User Email
    u = st.session_state.user
    curr = ""
    if hasattr(u, "email") and u.email: curr = u.email
    elif hasattr(u, "user") and hasattr(u.user, "email"): curr = u.user.email
    elif isinstance(u, dict) and "email" in u: curr = u["email"]
    
    # 3. PRINT DEBUG INFO TO TERMINAL (Look at your logs!)
    print(f"DEBUG: Checking Admin. Configured: '{admin_email}' | Current: '{curr}'")
    
    return curr.strip().lower() == admin_email.strip().lower()

# --- 8. SIDEBAR ---
with st.sidebar:
    if st.button("🏠 Home", use_container_width=True):
        st.session_state.current_view = "splash"
        st.rerun()
    st.divider()
    
    if st.session_state.user:
        st.caption(f"👤 {st.session_state.user_email}")
        
        if check_is_admin():
            if st.button("🔐 Admin Console", type="primary", use_container_width=True):
                st.session_state.current_view = "admin"
                st.rerun()
                
        if st.button("🚪 Sign Out", use_container_width=True):
            st.session_state.clear()
            st.rerun()
    else:
        if st.session_state.current_view not in ["login", "splash"]:
            if st.button("🔑 Log In", use_container_width=True):
                st.session_state.current_view = "login"
                st.rerun()
    
    st.divider()
    if st.button("⚖️ Legal", type="secondary", use_container_width=True):
        st.session_state.current_view = "legal"
        st.rerun()

# --- 9. ROUTING ---
if "session_id" in st.query_params: 
    st.session_state.current_view = "main_app"

view = st.session_state.current_view

if view == "splash": 
    ui_splash.show_splash()
elif view == "login": 
    ui_login.show_login(handle_login_wrapper, handle_signup_wrapper)
elif view == "main_app": 
    ui_main.show_main_app()
elif view == "admin": 
    if check_is_admin(): ui_admin.show_admin()
    else: st.error("Unauthorized"); st.session_state.current_view = "splash"
elif view == "legal": 
    ui_legal.show_legal()
else:
    st.session_state.current_view = "splash"
    st.rerun()