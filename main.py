import streamlit as st
import ui_main
import ui_splash
import ui_login 
import ui_admin 
# Import the handlers from ui_main where they are now defined
from ui_main import handle_login, handle_signup 

# --- 1. GLOBAL PAGE CONFIG ---
st.set_page_config(
    page_title="VerbaPost", 
    page_icon="✉️", 
    layout="wide", # Use wide layout for better sidebar visibility
    initial_sidebar_state="expanded" # Force sidebar to be open
)

# --- GA MEASUREMENT ID ---
GA_MEASUREMENT_ID = "G-D3P178CESF"

# --- 2. GLOBAL CSS / GA INJECTION ---
def inject_global_css_and_ga():
    """Injects CSS styles and the Google Analytics script."""
    
    # Inject GA script using st.markdown (must be the first block for best results)
    ga_script = f"""
        <!-- Google tag (gtag.js) -->
        <script async src="https://www.googletagmanager.com/gtag/js?id={GA_MEASUREMENT_ID}"></script>
        <script>
          window.dataLayer = window.dataLayer || [];
          function gtag(){{dataLayer.push(arguments);}}
          gtag('js', new Date());
          gtag('config', '{GA_MEASUREMENT_ID}');
        </script>
        """
    st.markdown(ga_script, unsafe_allow_html=True)
    
    # Inject custom CSS
    st.markdown("""
    <style>
        /* Core Theme */
        .stApp { background-color: #f8f9fc; color: #2d3748; font-family: 'Helvetica Neue', sans-serif; }
        header, .stDeployButton, footer { visibility: hidden; }
        
        /* Text & Input Fixes */
        h1, h2, h3, p, div, label, span { color: #2d3748 !important; }
        .stTextInput input, .stSelectbox div, div[data-baseweb="select"] > div {
            background-color: white !important;
            color: #2d3748 !important;
            border: 1px solid #e2e8f0 !important;
        }
        
        /* Sidebar & Menus */
        [data-testid="stSidebar"] { background-color: white !important; border-right: 1px solid #e2e8f0; }
        div[data-baseweb="popover"], ul[data-baseweb="menu"] { background-color: white !important; }
        li[data-baseweb="option"] { color: #2d3748 !important; }
        
        /* Buttons */
        div.stButton > button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white !important;
            border: none; border-radius: 25px; padding: 0.5rem 1.5rem;
        }
        div.stButton > button[kind="secondary"] {
            background: white; color: #555 !important; border: 1px solid #ddd;
        }
        
        /* Hero */
        .hero-banner {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 40px; border-radius: 20px; color: white !important;
            text-align: center; margin-bottom: 30px;
        }
        .hero-title { font-size: 3rem; font-weight: 800; margin: 0; color: white !important; }
        .hero-subtitle { font-size: 1.2rem; opacity: 0.9; margin-top: 10px; color: white !important; }
        .hero-banner p { color: white !important; }
    </style>
    """, unsafe_allow_html=True)


# --- 3. MAIN CONTROLLER ---
def main():
    # Execute CSS and GA injection
    inject_global_css_and_ga()

    # Initialize Session
    if "app_mode" not in st.session_state:
        st.session_state.app_mode = "splash"
    
    # --- ADMIN/SIDEBAR LOGIC (MUST be rendered before the routing) ---
    with st.sidebar:
        
        # 3.1 Navigation Buttons
        if st.button("🏠 Home", use_container_width=True, key="sidebar_home_button"):
            st.session_state.app_mode = "splash"
            st.rerun()
        
        # 3.2 User/Admin Logic (Must be robust against missing keys)
        if st.session_state.get("user"):
            st.caption(f"User: {st.session_state.get('user_email')}")
            
            # --- ADMIN CHECK LOGIC ---
            is_admin = False
            try:
                # Assuming st.secrets['admin']['email'] is the comparison target
                admin_email = st.secrets.get("admin", {}).get("email", "").strip().lower()
                # Safely attempt to access the email
                user_email = st.session_state.user.user.email.strip().lower()
                if user_email == admin_email: 
                    is_admin = True
            except: 
                st.warning("Admin check failed. Log in to initialize session.")
                pass

            if is_admin: 
                # FIX 2: Admin Panel Button with unique key
                if st.button("🔐 Admin Panel", type="primary", use_container_width=True, key="sidebar_admin_panel"):
                    st.session_state.app_mode = "admin"
                    st.rerun()

            if st.button("Log Out", use_container_width=True, key="sidebar_logout"):
                # Clear all session state keys upon log out
                st.session_state.clear()
                st.session_state.app_mode = "splash"
                st.rerun()
        else:
            # Show Login/Signup if not logged in and not on the splash page
            if st.session_state.app_mode != "login" and st.session_state.app_mode != "splash":
                if st.button("Log In / Sign Up", use_container_width=True, key="sidebar_login_guest"):
                    st.session_state.app_mode = "login"
                    st.rerun()
        
        # 3.3 Footer Links
        st.divider()
        st.markdown("📧 **Help:** support@verbapost.com")
        if st.button("⚖️ Terms & Privacy", type="secondary", use_container_width=True, key="sidebar_legal"):
            st.session_state.app_mode = "legal"
            st.rerun()
        
    # --- LOGIC FIX: DETECT STRIPE RETURN ---
    if "session_id" in st.query_params:
        st.session_state.app_mode = "workspace"

    # --- 4. ROUTING ---
    if st.session_state.app_mode == "splash":
        ui_splash.show_splash()
    elif st.session_state.app_mode == "admin":
        ui_admin.show_admin()
    elif st.session_state.app_mode == "login":
        # FIX 3: Pass required arguments to show_login()
        ui_login.show_login(handle_login, handle_signup) 
    else:
        # This handles 'legal', 'store', 'workspace', etc.
        ui_main.show_main_app()

if __name__ == "__main__":
    main()