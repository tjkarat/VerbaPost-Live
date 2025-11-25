import streamlit as st
import streamlit.components.v1 as components

# --- 1. PAGE CONFIG ---
st.set_page_config(
    page_title="VerbaPost", 
    page_icon="📮", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. GLOBAL STYLES ---
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
    /* Force Light Theme */
    [data-testid="stAppViewContainer"] {{background-color: #ffffff;}}
    [data-testid="stSidebar"] {{background-color: #f8f9fa;}}
    [data-testid="stHeader"] {{background-color: rgba(0,0,0,0);}}
    
    /* Text Colors */
    h1, h2, h3, h4, h5, h6, p, li, div, label, span {{color: #31333F !important;}}
    
    /* Inputs */
    input, textarea, select {{
        color: #31333F !important;
        background-color: #ffffff !important;
        border: 1px solid #e0e0e0 !important;
    }}
    
    /* Hide Defaults */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    header {{visibility: hidden;}}
    
    /* Buttons */
    div.stButton > button {{
        border-radius: 12px; font-weight: 600; 
        border: 1px solid #e0e0e0; padding: 0.5rem 1rem;
        transition: all 0.3s ease;
    }}
    div.stButton > button:hover {{
        border-color: #2a5298; color: #2a5298;
    }}
    </style>
""", unsafe_allow_html=True)

# --- 3. IMPORTS ---
try:
    import ui_splash, ui_login, ui_admin, ui_main, auth_engine
except ImportError as e:
    st.error(f"System Error: {e}")
    st.stop()

# --- 4. SESSION STATE ---
if "current_view" not in st.session_state: st.session_state.current_view = "splash"
if "user" not in st.session_state: st.session_state.user = None

# --- 5. ADMIN CHECK ---
def check_is_admin():
    try:
        if "ADMIN_EMAIL" in st.secrets: target = st.secrets["ADMIN_EMAIL"]
        elif "admin" in st.secrets: target = st.secrets["admin"]["email"]
        else: return False
    except: return False
    
    if not st.session_state.user: return False
    u = st.session_state.user
    curr = ""
    if hasattr(u, "email"): curr = u.email
    elif hasattr(u, "user"): curr = u.user.email
    elif isinstance(u, dict): curr = u.get("email", "")
    return curr.strip().lower() == target.strip().lower()

# --- 6. SIDEBAR ---
with st.sidebar:
    if st.button("🏠 Home", use_container_width=True):
        st.session_state.current_view = "splash"
        st.rerun()

    st.divider()

    # Logged In Menu
    if st.session_state.user:
        st.caption("👤 Logged in")
        if check_is_admin():
            if st.button("🔐 Admin Console", type="primary", use_container_width=True):
                st.session_state.current_view = "admin"
                st.rerun()
        if st.button("Sign Out", use_container_width=True):
            st.session_state.clear()
            st.rerun()
    
    # NOTE: "Log In" button removed for guest users as requested
    
    st.divider()
    if st.button("⚖️ Terms of Service", type="secondary", use_container_width=True):
        st.session_state.current_view = "legal"
        st.rerun()

# --- 7. ROUTING ---
if "session_id" in st.query_params: st.session_state.current_view = "main_app"
view = st.session_state.current_view

if view == "splash": ui_splash.show_splash()
elif view == "login": 
    def on_login(e, p):
        u, err = auth_engine.sign_in(e, p)
        if u: 
            st.session_state.user = u
            st.session_state.current_view = "main_app"
            st.rerun()
        else: st.error(err)
    def on_signup(e, p, n, s, c, stt, z, l):
        u, err = auth_engine.sign_up(e, p, n, s, c, stt, z, l)
        if u: 
            st.session_state.user = u
            st.session_state.current_view = "main_app"
            st.rerun()
        else: st.error(err)
    ui_login.show_login(on_login, on_signup)
elif view == "main_app": ui_main.show_main_app()
elif view == "admin": 
    if check_is_admin(): ui_admin.show_admin()
    else: st.session_state.current_view = "splash"; st.rerun()
elif view == "legal": 
    import ui_legal
    ui_legal.show_legal()
else:
    st.session_state.current_view = "splash"
    st.rerun()