import streamlit as st
import streamlit.components.v1 as components

# --- 1. PAGE CONFIG ---
st.set_page_config(
    page_title="VerbaPost", 
    page_icon="📮", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. ANALYTICS (Reliable Injection) ---
# We use components.html here because it creates an iframe that guarantees execution
GA_ID = "G-D3P178CESF"
ga_code = f"""
<script async src="https://www.googletagmanager.com/gtag/js?id={GA_ID}"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){{dataLayer.push(arguments);}}
  gtag('js', new Date());
  gtag('config', '{GA_ID}');
</script>
"""
components.html(ga_code, height=0, width=0)

# --- 3. CSS STYLING ---
st.markdown("""
    <style>
    /* Force Light Mode */
    [data-testid="stAppViewContainer"] { background-color: #ffffff; }
    [data-testid="stSidebar"] { background-color: #f8f9fa; }
    [data-testid="stHeader"] { background-color: rgba(0,0,0,0); }
    
    /* Text Colors */
    h1, h2, h3, h4, h5, h6, p, li, div, label, span { 
        color: #31333F !important; 
    }
    
    /* Standard Buttons */
    div.stButton > button {
        background-color: #ffffff; 
        color: #31333F;
        border: 1px solid #e0e0e0;
    }
    
    /* Primary Buttons */
    div.stButton > button[kind="primary"] {
        background-color: #2a5298 !important;
        border: none !important;
    }
    div.stButton > button[kind="primary"] p {
        color: #FFFFFF !important;
    }
    
    /* --- PAY BUTTON FIX (TARGETING INTERNALS) --- */
    a[data-testid="stLinkButton"] {
        background-color: #2a5298 !important;
        border: none !important;
    }
    /* Target the specific div that holds the text inside the link */
    a[data-testid="stLinkButton"] > div {
        color: #FFFFFF !important;
    }
    /* Target visited state explicitly */
    a[data-testid="stLinkButton"]:visited {
        color: #FFFFFF !important;
    }
    /* Hover State */
    a[data-testid="stLinkButton"]:hover {
        background-color: #1e3c72 !important;
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }

    /* Inputs */
    input, textarea, select {
        color: #31333F !important;
        background-color: #ffffff !important;
        border: 1px solid #e0e0e0 !important;
    }
    
    /* Hide Defaults */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: visible;}
    </style>
""", unsafe_allow_html=True)

# --- 4. IMPORTS ---
try:
    import ui_splash, ui_login, ui_admin, ui_main, auth_engine
except ImportError as e:
    st.error(f"System Error: {e}")
    st.stop()

# --- 5. SESSION STATE ---
if "current_view" not in st.session_state: st.session_state.current_view = "splash"
if "user" not in st.session_state: st.session_state.user = None

# --- 6. ADMIN CHECK ---
def check_is_admin():
    try:
        if "ADMIN_EMAIL" in st.secrets: t = st.secrets["ADMIN_EMAIL"]
        elif "admin" in st.secrets: t = st.secrets["admin"]["email"]
        else: return False
    except: return False
    if not st.session_state.user: return False
    u = st.session_state.user
    e = u.get("email") if isinstance(u, dict) else (u.email if hasattr(u, "email") else "")
    return e.strip().lower() == t.strip().lower()

# --- 7. SIDEBAR ---
with st.sidebar:
    if st.button("🏠 Home", use_container_width=True):
        st.session_state.current_view = "splash"
        st.rerun()
    st.divider()
    if st.session_state.user:
        if check_is_admin():
            if st.button("🔐 Admin Console", type="primary", use_container_width=True):
                st.session_state.current_view = "admin"; st.rerun()
        if st.button("Sign Out", use_container_width=True):
            st.session_state.clear(); st.rerun()
    else:
        if st.session_state.current_view != "login":
            if st.button("Log In", use_container_width=True):
                st.session_state.current_view = "login"; st.rerun()

# --- 8. ROUTING ---
if "session_id" in st.query_params: st.session_state.current_view = "main_app"
v = st.session_state.current_view

if v == "splash": ui_splash.show_splash()
elif v == "login": 
    def L(e,p):
        u, err = auth_engine.sign_in(e,p)
        if u: st.session_state.user=u; st.session_state.current_view="main_app"; st.rerun()
        else: st.error(err)
    def S(e,p,n,s,c,stt,z,l):
        u, err = auth_engine.sign_up(e,p,n,s,c,stt,z,l)
        if u: st.session_state.user=u; st.session_state.current_view="main_app"; st.rerun()
        else: st.error(err)
    ui_login.show_login(L, S)
elif v == "forgot_password": ui_login.show_forgot_password(auth_engine.send_password_reset)
elif v == "reset_verify": ui_login.show_reset_verify(auth_engine.reset_password_with_token)
elif v == "main_app": ui_main.show_main_app()
elif v == "admin": 
    if check_is_admin(): ui_admin.show_admin()
    else: st.session_state.current_view="splash"; st.rerun()
elif v == "legal": import ui_legal; ui_legal.show_legal()