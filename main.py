import streamlit as st
import streamlit.components.v1 as components

# --- 1. PAGE CONFIG ---
st.set_page_config(
    page_title="VerbaPost", 
    page_icon="📮", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. ANALYTICS (Injecting at Top Level) ---
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
    /* --- FORCE LIGHT MODE --- */
    [data-testid="stAppViewContainer"] {{ background-color: #ffffff; }}
    [data-testid="stSidebar"] {{ background-color: #f8f9fa; }}
    
    /* --- TEXT COLORS --- */
    h1, h2, h3, h4, h5, h6, p, li, div, label, span {{ color: #31333F !important; }}
    
    /* --- BUTTONS (STANDARD) --- */
    div.stButton > button {{
        background-color: #ffffff; 
        color: #31333F;
        border: 1px solid #e0e0e0;
    }}
    
    /* --- PRIMARY BUTTONS (Blue) --- */
    div.stButton > button[kind="primary"] {{
        background-color: #2a5298 !important;
        border: none !important;
    }}
    div.stButton > button[kind="primary"] p {{
        color: #FFFFFF !important;
    }}
    div.stButton > button[kind="primary"]:hover {{
        background-color: #1e3c72 !important;
    }}
    
    /* --- LINK BUTTONS (PAY BUTTON FIX) --- */
    a[data-testid="stLinkButton"] {{
        background-color: #2a5298 !important;
        border: none !important;
    }}
    /* FORCE TEXT WHITE ON ALL STATES */
    a[data-testid="stLinkButton"] *,
    a[data-testid="stLinkButton"]:link *,
    a[data-testid="stLinkButton"]:visited *,
    a[data-testid="stLinkButton"]:hover *,
    a[data-testid="stLinkButton"]:active * {{
        color: #FFFFFF !important;
        fill: #FFFFFF !important;
        text-decoration: none !important;
    }}
    
    a[data-testid="stLinkButton"]:hover {{
        background-color: #1e3c72 !important;
    }}

    /* --- INPUTS --- */
    input, textarea, select {{
        color: #31333F !important;
        background-color: #ffffff !important;
        border: 1px solid #e0e0e0 !important;
    }}
    
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    header {{visibility: visible;}}
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
def get_current_user_email():
    if not st.session_state.user: return None
    u = st.session_state.user
    if isinstance(u, dict): return u.get("email")
    if hasattr(u, "email"): return u.email
    if hasattr(u, "user"): return u.user.email
    return None

def check_is_admin():
    try:
        if "ADMIN_EMAIL" in st.secrets: target = st.secrets["ADMIN_EMAIL"]
        elif "admin" in st.secrets: target = st.secrets["admin"]["email"]
        else: return False
    except: return False
    curr = get_current_user_email()
    if not curr: return False
    return curr.strip().lower() == target.strip().lower()

# --- 6. SIDEBAR ---
with st.sidebar:
    if st.button("🏠 Home", use_container_width=True):
        st.session_state.current_view = "splash"
        st.rerun()

    st.divider()

    if st.session_state.user:
        my_email = get_current_user_email()
        st.caption(f"👤 {my_email}")
        
        if check_is_admin():
            if st.button("🔐 Admin Console", type="primary", use_container_width=True):
                st.session_state.current_view = "admin"
                st.rerun()
        
        if st.button("Sign Out", use_container_width=True):
            st.session_state.clear()
            st.rerun()
    else:
        if st.session_state.current_view != "login":
            if st.button("Log In", use_container_width=True):
                st.session_state.current_view = "login"
                st.rerun()

# --- 7. ROUTING ---
if "session_id" in st.query_params: st.session_state.current_view = "main_app"

view = st.session_state.current_view

if view == "splash": 
    ui_splash.show_splash()
elif view == "login": 
    def on_login(e, p):
        u, err = auth_engine.sign_in(e, p)
        if u: 
            st.session_state.user = u
            st.session_state.current_view = "main_app"
            st.rerun()
        else: st.session_state.auth_error = err
    def on_signup(e, p, n, s, c, stt, z, l):
        u, err = auth_engine.sign_up(e, p, n, s, c, stt, z, l)
        if u: 
            st.session_state.user = u
            st.session_state.current_view = "main_app"
            st.rerun()
        else: st.session_state.auth_error = err
    ui_login.show_login(on_login, on_signup)
    
elif view == "forgot_password":
    if hasattr(ui_login, 'show_forgot_password'):
        ui_login.show_forgot_password(auth_engine.send_password_reset)
    else: st.error("UI Missing")

elif view == "reset_verify":
    if hasattr(ui_login, 'show_reset_verify'):
        ui_login.show_reset_verify(auth_engine.reset_password_with_token)
    else: st.error("UI Missing")

elif view == "main_app": 
    ui_main.show_main_app()
elif view == "admin": 
    if check_is_admin(): ui_admin.show_admin()
    else: st.session_state.current_view = "splash"; st.rerun()
elif view == "legal": 
    import ui_legal
    ui_legal.show_legal()
else:
    st.session_state.current_view = "splash"
    st.rerun()