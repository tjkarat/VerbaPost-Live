import streamlit as st
import streamlit.components.v1 as components

# --- 1. PAGE CONFIG (Must be first) ---
st.set_page_config(
    page_title="VerbaPost", 
    page_icon="📮", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. GLOBAL STYLES (The Modern Purple Look) ---
st.markdown("""
    <style>
    /* Hide default Streamlit headers */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Modern Container Spacing */
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 3rem !important;
    }
    
    /* Modern Button Styling */
    div.stButton > button {
        border-radius: 12px; 
        font-weight: 600; 
        border: 1px solid #e0e0e0;
        padding: 0.5rem 1rem;
        transition: all 0.3s ease;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    div.stButton > button:hover {
        border-color: #667eea;
        color: #667eea;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        transform: translateY(-1px);
    }
    
    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background-color: #f8f9fa;
        border-right: 1px solid #e0e0e0;
    }
    </style>
""", unsafe_allow_html=True)

# --- 3. ANALYTICS (Inject into Head) ---
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

# --- 4. IMPORTS ---
try:
    import ui_splash
    import ui_login
    import ui_admin
    import ui_legal
    import ui_main
    import auth_engine
except ImportError as e:
    st.error(f"System Error: Missing module {e}")
    st.stop()

# --- 5. SESSION STATE ---
if "current_view" not in st.session_state: st.session_state.current_view = "splash"
if "user" not in st.session_state: st.session_state.user = None
if "user_email" not in st.session_state: st.session_state.user_email = None

# --- 6. ADMIN CHECK (ROBUST) ---
def check_is_admin():
    """Checks for admin privileges safely"""
    if not st.session_state.user: return False
    try:
        # Get admin email from secrets
        admin_email = st.secrets["admin"]["email"].strip().lower()
        
        # Get user email (Handles Supabase objects or Dicts)
        user_obj = st.session_state.user
        u_email = ""
        
        if hasattr(user_obj, "email") and user_obj.email: 
            u_email = user_obj.email
        elif hasattr(user_obj, "user") and hasattr(user_obj.user, "email"): 
            u_email = user_obj.user.email
        elif isinstance(user_obj, dict) and "email" in user_obj: 
            u_email = user_obj["email"]
            
        return u_email.strip().lower() == admin_email
    except Exception as e:
        print(f"Admin check failed: {e}")
        return False

# --- 7. SIDEBAR NAVIGATION ---
with st.sidebar:
    if st.button("🏠 Home", use_container_width=True):
        st.session_state.current_view = "splash"
        st.rerun()
    st.divider()
    
    # Authenticated User Menu
    if st.session_state.user:
        st.caption(f"👤 {st.session_state.user_email}")
        
        # Admin Button
        if check_is_admin():
            if st.button("🔐 Admin Console", type="primary", use_container_width=True):
                st.session_state.current_view = "admin"
                st.rerun()
        
        if st.button("🚪 Sign Out", use_container_width=True):
            st.session_state.clear()
            st.session_state.current_view = "splash"
            st.rerun()
    else:
        # Guest Menu
        if st.session_state.current_view not in ["login", "splash"]:
            if st.button("🔑 Log In", use_container_width=True):
                st.session_state.current_view = "login"
                st.rerun()
    
    st.divider()
    if st.button("⚖️ Legal", type="secondary", use_container_width=True):
        st.session_state.current_view = "legal"
        st.rerun()

# --- 8. ROUTING ---
# Catch Stripe Returns
if "session_id" in st.query_params: 
    st.session_state.current_view = "main_app"

view = st.session_state.current_view

if view == "splash": 
    ui_splash.show_splash()
elif view == "login": 
    ui_login.show_login(
        lambda e,p: (auth_engine.sign_in(e,p) if auth_engine else (None, "No Auth")), 
        lambda e,p,n,s,c,st,z,l: (auth_engine.sign_up(e,p,n,s,c,st,z,l) if auth_engine else (None, "No Auth"))
    )
elif view == "main_app": 
    ui_main.show_main_app()
elif view == "admin": 
    if check_is_admin(): 
        ui_admin.show_admin()
    else: 
        st.error("⛔ Unauthorized"); st.session_state.current_view = "splash"
elif view == "legal": 
    ui_legal.show_legal()