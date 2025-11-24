import streamlit as st
import streamlit.components.v1 as components

# --- 1. PAGE CONFIG (MUST BE FIRST) ---
st.set_page_config(
    page_title="VerbaPost | Send Mail to Inmates, Congress & Homeowners", 
    page_icon="📮", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. GOOGLE ANALYTICS (Inject immediately after config) ---
GA_MEASUREMENT_ID = "G-D3P178CESF"

def inject_google_analytics():
    """Injects GA tracking using components.html for better compatibility"""
    if GA_MEASUREMENT_ID and GA_MEASUREMENT_ID.startswith("G-"):
        ga_html = f"""
        <script async src="https://www.googletagmanager.com/gtag/js?id={GA_MEASUREMENT_ID}"></script>
        <script>
          window.dataLayer = window.dataLayer || [];
          function gtag(){{dataLayer.push(arguments);}}
          gtag('js', new Date());
          gtag('config', '{GA_MEASUREMENT_ID}');
        </script>
        """
        # Using components.html to ensure script executes
        components.html(ga_html, height=0)

# Inject GA immediately
inject_google_analytics()

# --- 3. CUSTOM CSS ---
def inject_custom_css():
    st.markdown("""
        <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        .block-container {padding-top: 1rem !important; padding-bottom: 1rem !important;}
        div.stButton > button {border-radius: 8px; font-weight: 600; border: 1px solid #e0e0e0;}
        input {border-radius: 5px !important;}
        
        /* Ensure sidebar is visible */
        [data-testid="stSidebar"] {
            background-color: white !important;
            border-right: 1px solid #e2e8f0;
        }
        </style>
        """, unsafe_allow_html=True)

inject_custom_css()

# --- 4. LAZY IMPORTS (Import modules AFTER config to avoid circular dependencies) ---
try:
    import ui_splash
    import ui_login
    import ui_admin
    import ui_legal
    import ui_main
    import auth_engine
except ImportError as e:
    st.error(f"Critical Import Error: {e}")
    st.stop()

# --- 5. SESSION STATE INITIALIZATION ---
if "current_view" not in st.session_state:
    st.session_state.current_view = "splash"
if "user" not in st.session_state:
    st.session_state.user = None
if "user_email" not in st.session_state:
    st.session_state.user_email = None

# --- 6. STRIPE RETURN HANDLER ---
qp = st.query_params
if "session_id" in qp and "current_view" not in st.session_state:
    st.session_state.current_view = "main_app"

# --- 7. AUTH HANDLERS ---
def handle_login(email, password):
    user, error = auth_engine.sign_in(email, password)
    if error:
        st.error(f"Login Failed: {error}")
        return False
    else:
        st.success("Welcome!")
        st.session_state.user = user
        st.session_state.user_email = email
        try:
            saved = auth_engine.get_current_address(email)
            if saved:
                st.session_state["from_name"] = saved.get("name", "")
                st.session_state["from_street"] = saved.get("street", "")
                st.session_state["from_city"] = saved.get("city", "")
                st.session_state["from_state"] = saved.get("state", "")
                st.session_state["from_zip"] = saved.get("zip", "")
                st.session_state["selected_language"] = saved.get("language", "English")
        except Exception as e:
            st.warning(f"Could not load saved address: {e}")
        st.session_state.current_view = "main_app"
        return True

def handle_signup(email, password, name, street, city, state, zip_code, language):
    user, error = auth_engine.sign_up(email, password, name, street, city, state, zip_code, language)
    if error:
        st.error(f"Signup Error: {error}")
        return False
    else:
        st.success("Account Created!")
        st.session_state.user = user
        st.session_state.user_email = email
        st.session_state.selected_language = language
        st.session_state.current_view = "main_app"
        return True

# --- 8. ADMIN CHECK HELPER ---
def is_user_admin():
    """Safely checks if current user is admin"""
    try:
        # Check if user exists
        if not st.session_state.get("user"):
            return False
        
        # Get admin email from secrets
        admin_email = st.secrets.get("admin", {}).get("email", "").strip().lower()
        if not admin_email:
            st.warning("⚠️ Admin email not configured in secrets")
            return False
        
        # Get user email - try multiple paths for different auth structures
        user_email = None
        user_obj = st.session_state.user
        
        # Try direct email attribute
        if hasattr(user_obj, 'email'):
            user_email = user_obj.email
        # Try nested user.email (Supabase structure)
        elif hasattr(user_obj, 'user') and hasattr(user_obj.user, 'email'):
            user_email = user_obj.user.email
        # Fallback to session state email
        elif st.session_state.get("user_email"):
            user_email = st.session_state.user_email
        
        if not user_email:
            return False
        
        return user_email.strip().lower() == admin_email
        
    except Exception as e:
        st.error(f"Admin check failed: {e}")
        return False

# --- 9. SIDEBAR NAVIGATION ---
with st.sidebar:
    # Home button
    if st.button("🏠 Home", use_container_width=True, key="sidebar_home"):
        st.session_state.current_view = "splash"
        st.rerun()
    
    st.divider()
    
    # User section
    if st.session_state.get("user"):
        user_email = st.session_state.get("user_email", "Unknown")
        st.caption(f"👤 **User:** {user_email}")
        
        # Admin panel button
        if is_user_admin():
            st.success("✅ Admin Access")
            if st.button("🔐 Admin Panel", type="primary", use_container_width=True, key="sidebar_admin"):
                st.session_state.current_view = "admin"
                st.rerun()
        
        # Logout button
        if st.button("🚪 Log Out", use_container_width=True, key="sidebar_logout"):
            # Clear all session state
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.session_state.current_view = "splash"
            st.rerun()
    else:
        # Guest user - show login button
        if st.session_state.current_view not in ["login", "splash"]:
            if st.button("🔑 Log In / Sign Up", use_container_width=True, key="sidebar_login"):
                st.session_state.current_view = "login"
                st.rerun()
    
    # Footer
    st.divider()
    st.markdown("📧 **Support:** support@verbapost.com")
    if st.button("⚖️ Terms & Privacy", type="secondary", use_container_width=True, key="sidebar_legal"):
        st.session_state.current_view = "legal"
        st.rerun()

# --- 10. MAIN CONTENT ROUTER ---
if st.session_state.current_view == "splash":
    ui_splash.show_splash()

elif st.session_state.current_view == "login":
    ui_login.show_login(handle_login, handle_signup)

elif st.session_state.current_view == "admin":
    if is_user_admin():
        ui_admin.show_admin()
    else:
        st.error("🚫 Access Denied: Admin privileges required")
        st.session_state.current_view = "splash"
        st.rerun()

elif st.session_state.current_view == "legal":
    ui_legal.show_legal()

elif st.session_state.current_view == "main_app":
    ui_main.show_main_app()

else:
    # Fallback for unknown views
    st.error(f"Unknown view: {st.session_state.current_view}")
    st.session_state.current_view = "splash"
    st.rerun()