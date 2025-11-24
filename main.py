import streamlit as st

# --- 1. PAGE CONFIG ---
st.set_page_config(page_title="VerbaPost", layout="wide")

# --- 2. STYLE ---
st.markdown("""
    <style>
    .block-container {padding-top: 2rem !important;}
    section[data-testid="stSidebar"] {background-color: #f0f2f6;}
    div.stButton > button {border-radius: 8px; width: 100%;}
    </style>
""", unsafe_allow_html=True)

# --- 3. IMPORTS (Safe Mode) ---
try:
    import ui_splash, ui_login, ui_admin, ui_main, auth_engine
except ImportError as e:
    st.error(f"CRITICAL IMPORT ERROR: {e}")
    st.stop()

# --- 4. SESSION STATE ---
if "current_view" not in st.session_state: st.session_state.current_view = "splash"
if "user" not in st.session_state: st.session_state.user = None

# --- 5. ADMIN CHECK (WITH ON-SCREEN DEBUGGING) ---
def check_is_admin():
    # 1. Get Configured Admin Email
    admin_email = ""
    try:
        if "ADMIN_EMAIL" in st.secrets: admin_email = st.secrets["ADMIN_EMAIL"]
        elif "admin" in st.secrets: admin_email = st.secrets["admin"]["email"]
    except: pass # Secrets missing
    
    # 2. Get Current User Email
    user_obj = st.session_state.user
    current_email = "Not Logged In"
    if user_obj:
        if hasattr(user_obj, "email"): current_email = user_obj.email
        elif hasattr(user_obj, "user"): current_email = user_obj.user.email
        elif isinstance(user_obj, dict): current_email = user_obj.get("email", "")
    
    # 3. RETURN BOTH FOR DEBUGGING
    return admin_email.strip().lower(), current_email.strip().lower()

# --- 6. SIDEBAR (The Control Center) ---
with st.sidebar:
    st.header("VerbaPost")
    
    if st.button("🏠 Home"):
        st.session_state.current_view = "splash"
        st.rerun()

    # --- DEBUG SECTION (TEMPORARY) ---
    st.divider()
    st.markdown("### 🛠️ Debug Info")
    
    target_admin, my_email = check_is_admin()
    is_match = (target_admin == my_email) and (target_admin != "")
    
    st.caption(f"Target: `{target_admin}`")
    st.caption(f"You: `{my_email}`")
    
    if is_match:
        st.success("✅ MATCH! Admin Unlocked")
        if st.button("🔐 Open Admin Console", type="primary"):
            st.session_state.current_view = "admin"
            st.rerun()
    else:
        if st.session_state.user:
            st.error("❌ EMAILS DO NOT MATCH")
            st.info("Check your secrets.toml file.")
        else:
            st.warning("Waiting for login...")

    st.divider()
    
    # Logout
    if st.session_state.user:
        if st.button("Sign Out"):
            st.session_state.clear()
            st.rerun()
    elif st.session_state.current_view != "login":
        if st.button("Log In"):
            st.session_state.current_view = "login"
            st.rerun()

# --- 7. ROUTING ---
view = st.session_state.current_view

if view == "splash": ui_splash.show_splash()
elif view == "login": 
    # Simple wrapper to handle login state updates
    def on_login(email, pw):
        u, e = auth_engine.sign_in(email, pw)
        if u: 
            st.session_state.user = u
            st.session_state.current_view = "main_app"
            st.rerun()
        else: st.error(e)
    def on_signup(e, p, n, s, c, stt, z, l):
        u, err = auth_engine.sign_up(e, p, n, s, c, stt, z, l)
        if u: 
            st.session_state.user = u
            st.session_state.current_view = "main_app"
            st.rerun()
        else: st.error(err)
    ui_login.show_login(on_login, on_signup)
    
elif view == "main_app": ui_main.show_main_app()
elif view == "admin": ui_admin.show_admin()
elif view == "legal": import ui_legal; ui_legal.show_legal()