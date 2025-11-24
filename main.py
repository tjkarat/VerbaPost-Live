import streamlit as st
import streamlit.components.v1 as components

# --- 1. PAGE CONFIG ---
st.set_page_config(
    page_title="VerbaPost", 
    page_icon="📮", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. GLOBAL STYLES & ANALYTICS ---
GA_ID = "G-D3P178CESF"
st.markdown(f"""
    <script async src="https://www.googletagmanager.com/gtag/js?id={GA_ID}"></script>
    <script>
        window.dataLayer = window.dataLayer || [];
        function gtag(){{dataLayer.push(arguments);}}
        gtag('js', new Date());
        gtag('config', '{GA_ID}');
    </script>
    <style>
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    header {{visibility: hidden;}}
    .block-container {{padding-top: 2rem !important; padding-bottom: 3rem !important;}}
    div.stButton > button {{
        border-radius: 12px; font-weight: 600; 
        border: 1px solid #e0e0e0; padding: 0.5rem 1rem;
        transition: all 0.3s ease;
    }}
    div.stButton > button:hover {{
        border-color: #667eea; color: #667eea;
    }}
    </style>
""", unsafe_allow_html=True)

# --- 3. IMPORTS ---
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

# --- 4. SESSION STATE ---
if "current_view" not in st.session_state: st.session_state.current_view = "splash"
if "user" not in st.session_state: st.session_state.user = None
if "user_email" not in st.session_state: st.session_state.user_email = None

# --- 5. AUTH HANDLERS (The "Brain" needed for Login) ---
def handle_login_wrapper(email, password):
    """
    Connects ui_login to auth_engine.
    If successful, updates session state to show the Main App.
    """
    if not auth_engine:
        st.error("Auth Engine missing")
        return

    # Call the engine
    user, error = auth_engine.sign_in(email, password)
    
    if error:
        st.error(f"Login Failed: {error}")
    else:
        # SUCCESS! Update State
        st.session_state.user = user
        st.session_state.user_email = email
        st.session_state.current_view = "main_app"
        st.toast("✅ Welcome back!")
        st.rerun()

def handle_signup_wrapper(email, password, name, street, city, state, zip_code, language):
    """
    Connects ui_login signup to auth_engine.
    """
    if not auth_engine:
        st.error("Auth Engine missing")
        return

    user, error = auth_engine.sign_up(email, password, name, street, city, state, zip_code, language)
    
    if error:
        st.error(f"Signup Failed: {error}")
    else:
        # SUCCESS!
        st.session_state.user = user
        st.session_state.user_email = email
        st.session_state.selected_language = language
        st.session_state.current_view = "main_app"
        st.success("Account Created!")
        st.rerun()

# --- 6. ADMIN CHECK ---
def check_is_admin():
    if not st.session_state.get("user"): return False
    try:
        # Check for Admin Email in Secrets (supports Flat or Nested)
        admin_email = ""
        if "ADMIN_EMAIL" in st.secrets: admin_email = st.secrets["ADMIN_EMAIL"]
        elif "admin" in st.secrets and "email" in st.secrets["admin"]: admin_email = st.secrets["admin"]["email"]
        
        if not admin_email: return False
        
        # Check current user email
        u = st.session_state.user
        curr = ""
        if hasattr(u, "email") and u.email: curr = u.email
        elif hasattr(u, "user") and hasattr(u.user, "email"): curr = u.user.email
        elif isinstance(u, dict) and "email" in u: curr = u["email"]
        
        return curr.strip().lower() == admin_email.strip().lower()
    except: return False

# --- 7. SIDEBAR ---
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

# --- 8. ROUTER ---
if "session_id" in st.query_params: st.session_state.current_view = "main_app"

view = st.session_state.current_view

if view == "splash": 
    ui_splash.show_splash()
elif view == "login": 
    # PASS THE WRAPPERS, NOT THE RAW FUNCTIONS
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