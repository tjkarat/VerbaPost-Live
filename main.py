import streamlit as st
import streamlit.components.v1 as components

# --- 1. PAGE CONFIG (Must be the very first command) ---
st.set_page_config(
    page_title="VerbaPost | Send Mail to Inmates, Congress & Homeowners", 
    page_icon="📮", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. ANALYTICS & CSS INJECTION ---
# We inject this as a single markdown block with unsafe_html.
# This works better than components.html for GA because it's not in an iframe.
GA_ID = "G-D3P178CESF"

def inject_headers():
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
            .block-container {{padding-top: 2rem !important;}}
            
            /* Better Button Styling */
            div.stButton > button {{
                border-radius: 8px; 
                font-weight: 600;
                border: 1px solid #e0e0e0;
                transition: all 0.2s;
            }}
            div.stButton > button:hover {{
                border-color: #667eea;
                color: #667eea;
            }}
        </style>
    """, unsafe_allow_html=True)

inject_headers()

# --- 3. IMPORTS (After config) ---
try:
    import ui_splash
    import ui_login
    import ui_admin
    import ui_legal
    import ui_main
    import auth_engine
except ImportError as e:
    st.error(f"Critical System Error: Missing module {e}")
    st.stop()

# --- 4. SESSION STATE SETUP ---
if "current_view" not in st.session_state:
    st.session_state.current_view = "splash"
if "user" not in st.session_state:
    st.session_state.user = None
if "user_email" not in st.session_state:
    st.session_state.user_email = None

# --- 5. HELPER: ROBUST ADMIN CHECK ---
def check_is_admin():
    """
    Robustly checks if the current user is an admin.
    Handles different Supabase user object structures.
    """
    if not st.session_state.user:
        return False
        
    try:
        # 1. Get the configured admin email
        admin_email = st.secrets["admin"]["email"].strip().lower()
        
        # 2. Extract current user email safely
        user_obj = st.session_state.user
        current_email = ""
        
        # Check structure: Object with .email
        if hasattr(user_obj, "email") and user_obj.email:
            current_email = user_obj.email
        # Check structure: Object with .user.email (Supabase AuthResponse)
        elif hasattr(user_obj, "user") and hasattr(user_obj.user, "email"):
            current_email = user_obj.user.email
        # Check structure: Dictionary
        elif isinstance(user_obj, dict) and "email" in user_obj:
            current_email = user_obj["email"]
            
        # 3. Compare
        return current_email.strip().lower() == admin_email
        
    except Exception as e:
        # Log to console for dev, but don't crash app
        print(f"Admin Check Error: {e}")
        return False

# --- 6. AUTH HANDLERS ---
def handle_login(email, password):
    user, error = auth_engine.sign_in(email, password)
    if error:
        st.error(f"Login Failed: {error}")
    else:
        st.session_state.user = user
        st.session_state.user_email = email
        st.success("✅ Login successful")
        st.session_state.current_view = "main_app"
        st.rerun()

def handle_signup(email, password, name, street, city, state, zip_code, language):
    user, error = auth_engine.sign_up(email, password, name, street, city, state, zip_code, language)
    if error:
        st.error(f"Signup Error: {error}")
    else:
        st.session_state.user = user
        st.session_state.user_email = email
        st.session_state.selected_language = language
        st.session_state.current_view = "main_app"
        st.rerun()

# --- 7. SIDEBAR NAVIGATION ---
with st.sidebar:
    # Home
    if st.button("🏠 Home", use_container_width=True):
        st.session_state.current_view = "splash"
        st.rerun()

    st.divider()

    # User Section
    if st.session_state.user:
        st.caption(f"👤 {st.session_state.user_email}")
        
        # Admin Button (Now robust)
        if check_is_admin():
            if st.button("🔐 Admin Console", type="primary", use_container_width=True):
                st.session_state.current_view = "admin"
                st.rerun()
        
        if st.button("🚪 Sign Out", use_container_width=True):
            st.session_state.clear()
            st.session_state.current_view = "splash"
            st.rerun()
    else:
        # Guest Section
        if st.session_state.current_view not in ["login", "splash"]:
            if st.button("🔑 Log In / Sign Up", use_container_width=True):
                st.session_state.current_view = "login"
                st.rerun()

    st.divider()
    if st.button("⚖️ Legal & Privacy", type="secondary", use_container_width=True):
        st.session_state.current_view = "legal"
        st.rerun()
    st.markdown("<div style='text-align: center; color: grey; font-size: 0.8em;'>VerbaPost v2.1</div>", unsafe_allow_html=True)

# --- 8. MAIN ROUTING ---
# Stripe Return Intercept
if "session_id" in st.query_params:
    st.session_state.current_view = "main_app"

# View Controller
view = st.session_state.current_view

if view == "splash":
    ui_splash.show_splash()

elif view == "login":
    ui_login.show_login(handle_login, handle_signup)

elif view == "main_app":
    ui_main.show_main_app()

elif view == "admin":
    if check_is_admin():
        ui_admin.show_admin()
    else:
        st.error("⛔ Unauthorized Access")
        st.session_state.current_view = "splash"

elif view == "legal":
    ui_legal.show_legal()

else:
    # Default fallback
    st.session_state.current_view = "splash"
    st.rerun()