import streamlit as st
import streamlit.components.v1 as components
import traceback

st.set_page_config(page_title="VerbaPost", page_icon="📮", layout="wide", initial_sidebar_state="expanded")

# --- ANALYTICS ---
GA_ID = "G-D3P178CESF"
components.html(f"""
<script async src="https://www.googletagmanager.com/gtag/js?id={GA_ID}"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){{dataLayer.push(arguments);}}
  gtag('js', new Date());
  gtag('config', '{GA_ID}');
</script>
""", height=0, width=0)

# --- GLOBAL STYLES ---
st.markdown(f"""
    <style>
    [data-testid="stAppViewContainer"] {{ background-color: #ffffff; }}
    [data-testid="stSidebar"] {{ background-color: #f8f9fa; }}
    h1, h2, h3, h4, p, li, label {{ color: #31333F !important; }}
    
    div.stButton > button {{
        background-color: #ffffff; color: #31333F; border: 1px solid #e0e0e0;
    }}
    div.stButton > button[kind="primary"] {{
        background-color: #2a5298 !important; border: none;
    }}
    div.stButton > button[kind="primary"] p {{ color: #FFFFFF !important; }}
    
    input, textarea, select {{
        color: #31333F !important;
        background-color: #ffffff !important;
        border: 1px solid #e0e0e0 !important;
    }}
    
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    </style>
""", unsafe_allow_html=True)

# --- ROBUST IMPORT BLOCK ---
# 1. Import Core Modules (Critical)
try:
    import ui_splash, ui_login, ui_admin, ui_main, auth_engine
except Exception as e:
    st.error(f"CRITICAL ERROR: Could not load core modules.\n{e}")
    st.stop()

# 2. Import Santa Module (Optional)
# This allows the app to run even if ui_santa.py is missing
santa_module = None
try:
    import ui_santa
    santa_module = ui_santa
except ImportError:
    pass # Santa module not found, feature will be hidden

if "current_view" not in st.session_state: st.session_state.current_view = "splash"
if "user" not in st.session_state: st.session_state.user = None

def check_is_admin():
    try:
        if "ADMIN_EMAIL" in st.secrets: t = st.secrets["ADMIN_EMAIL"]
        elif "admin" in st.secrets: t = st.secrets["admin"]["email"]
        else: return False
    except: return False
    
    if not st.session_state.user: return False
    
    u = st.session_state.user
    e = ""
    if isinstance(u, dict): e = u.get("email", "")
    elif hasattr(u, "email"): e = u.email
    elif hasattr(u, "user"): e = u.user.email # Handle nested auth objects
        
    return e.strip().lower() == t.strip().lower()

with st.sidebar:
    if st.button("🏠 Home", use_container_width=True): st.session_state.current_view = "splash"; st.rerun()
    
    # Only show Santa button if the module loaded successfully
    if santa_module:
        if st.button("🎅 Letter from Santa", use_container_width=True): st.session_state.current_view="santa_app"; st.rerun()

    if st.session_state.user:
        if check_is_admin():
            if st.button("🔐 Admin Console", type="primary", use_container_width=True): st.session_state.current_view="admin"; st.rerun()
        if st.button("Sign Out", use_container_width=True): st.session_state.clear(); st.rerun()
    else:
        if st.session_state.current_view != "login":
            if st.button("Log In", use_container_width=True): st.session_state.current_view="login"; st.rerun()

if "session_id" in st.query_params: st.session_state.current_view = "main_app"
v = st.session_state.current_view

if v == "splash": ui_splash.show_splash()
elif v == "login": 
    def L(e,p): 
        u,er=auth_engine.sign_in(e,p)
        if u: st.session_state.user=u; st.session_state.current_view="main_app"; st.rerun()
        else: st.error(er)
    def S(e,p,n,s,c,stt,z,l):
        u,er=auth_engine.sign_up(e,p,n,s,c,stt,z,l)
        if u: st.session_state.user=u; st.session_state.current_view="main_app"; st.rerun()
        else: st.error(er)
    ui_login.show_login(L, S)
elif v == "main_app": ui_main.show_main_app()
elif v == "admin": 
    if check_is_admin(): ui_admin.show_admin()
    else: st.session_state.current_view="splash"; st.rerun()
elif v == "santa_app" and santa_module: 
    santa_module.render_santa_page()
elif v == "forgot_password": ui_login.show_forgot_password(auth_engine.send_password_reset)
elif v == "reset_verify": ui_login.show_reset_verify(auth_engine.reset_password_with_token)
elif v == "legal": import ui_legal; ui_legal.show_legal()