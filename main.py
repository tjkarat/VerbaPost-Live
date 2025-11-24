import streamlit as st
import streamlit.components.v1 as components

# --- 1. PAGE CONFIG ---
st.set_page_config(page_title="VerbaPost", layout="wide")

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
    .block-container {{padding-top: 2rem !important;}}
    /* Hide the 'manage app' button for users */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    header {{visibility: hidden;}}
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

# --- 5. ADMIN CHECK (STRICT) ---
def check_is_admin():
    # 1. Get Target Email from Secrets
    try:
        if "ADMIN_EMAIL" in st.secrets: target = st.secrets["ADMIN_EMAIL"]
        elif "admin" in st.secrets: target = st.secrets["admin"]["email"]
        else: return False
    except: return False
    
    # 2. Get Current User Email
    if not st.session_state.user: return False
    
    u = st.session_state.user
    curr = ""
    if hasattr(u, "email"): curr = u.email
    elif hasattr(u, "user"): curr = u.user.email
    elif isinstance(u, dict): curr = u.get("email", "")
    
    # 3. Strict Comparison
    return curr.strip().lower() == target.strip().lower()

# --- 6. SIDEBAR ---
with st.sidebar:
    if st.button("🏠 Home", use_container_width=True):
        st.session_state.current_view = "splash"
        st.rerun()

    st.divider()

    # User Menu
    if st.session_state.user:
        # ONLY SHOW ADMIN BUTTON IF CHECK PASSES
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
                
    st.divider()
    if st.button("⚖️ Legal", type="secondary", use_container_width=True):
        st.session_state.current_view = "legal"
        st.rerun()

# --- 7. ROUTING ---
if "session_id" in st.query_params: st.session_state.current_view = "main_app"

view = st.session_state.current_view

if view == "splash": ui_splash.show_splash()
elif view == "login": 
    # Login wrappers
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