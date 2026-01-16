import streamlit as st
import time
import ui_login
import ui_advisor
import ui_heirloom
import ui_admin
import ui_splash

# --- IMPORTS FOR AUTH ---
try: import auth_engine
except ImportError: auth_engine = None
try: import database
except ImportError: database = None

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="VerbaPost",
    page_icon="📬",
    layout="centered",
    initial_sidebar_state="expanded" # FORCE OPEN
)

def handle_logout():
    """Clear session and reload to home."""
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.query_params.clear()
    st.rerun()

def main():
    # 1. INITIALIZE STATE
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "user_role" not in st.session_state:
        st.session_state.user_role = "user"
    if "user_email" not in st.session_state:
        st.session_state.user_email = None

    # 2. 🚨 PRIORITY: HANDLE GOOGLE CALLBACK 🚨
    # We check this FIRST before rendering anything else.
    query_params = st.query_params
    if "code" in query_params and not st.session_state.authenticated:
        if auth_engine:
            try:
                with st.spinner("🔄 Verifying Google Login..."):
                    # Exchange code for user session
                    user, error = auth_engine.handle_google_callback(query_params["code"])
                    
                    if user:
                        # SUCCESS
                        st.session_state.authenticated = True
                        st.session_state.user_email = user.email
                        
                        # Sync Role from DB
                        if database:
                            profile = database.get_user_profile(user.email)
                            if profile:
                                st.session_state.user_role = profile.get("role", "user")
                        
                        st.success(f"✅ Logged in as {user.email}")
                        time.sleep(1)
                        # Clear URL to prevent re-triggering
                        st.query_params.clear()
                        st.rerun()
                    else:
                        st.error(f"❌ Google Auth Failed: {error}")
            except Exception as e:
                st.error(f"⚠️ Auth System Error: {e}")
        else:
            st.error("⚠️ Auth Engine not loaded.")

    # 3. 🛠️ GLOBAL SIDEBAR (ALWAYS VISIBLE NOW) 🛠️
    with st.sidebar:
        st.header("VerbaPost Admin")
        
        # STATUS INDICATOR
        if st.session_state.authenticated:
            st.success(f"🟢 Online: {st.session_state.user_email}")
            st.caption(f"Role: {st.session_state.user_role}")
            
            # ADMIN TOOLS
            # Check if Admin OR if it's YOU (hardcoded safety net)
            is_admin = (st.session_state.user_role == "admin") or (st.session_state.user_email == "pat@gmail.com") # <--- VERIFY THIS EMAIL
            
            if is_admin:
                st.divider()
                st.subheader("🕵️ Role Switcher")
                if st.button("⚙️ Admin Console"): 
                    st.session_state.user_role = "admin"
                    st.rerun()
                if st.button("👔 Advisor View"): 
                    st.session_state.user_role = "advisor"
                    st.rerun()
                if st.button("📂 Heir View"): 
                    st.session_state.user_role = "heir"
                    st.rerun()
            
            # LOGOUT
            st.divider()
            if st.button("🚪 Log Out"):
                handle_logout()
        else:
            st.warning("🔴 Not Logged In")
            st.info("Please sign in to access tools.")

    # 4. ROUTING LOGIC
    nav = query_params.get("nav")
    
    # --- COMPATIBILITY BRIDGE (Fixes 'Button Does Nothing') ---
    # If the Splash page uses the old 'app_mode' state, we force the router to respect it
    if not nav and st.session_state.get("app_mode") == "login":
        nav = "login"

    # --- AUTHENTICATED ROUTES ---
    if st.session_state.authenticated:
        role = st.session_state.user_role
        
        # Dual Role / Force Heir View
        force_heir = ("pending_play_id" in st.session_state) or (nav == "archive")
        
        if force_heir:
            if ui_heirloom: ui_heirloom.render_family_archive()
            else: st.error("Heirloom UI missing")
            return

        # Role Routing
        if role == "advisor":
            if ui_advisor: ui_advisor.render_advisor_portal()
            else: st.error("Advisor UI missing")
        
        elif role == "admin":
            if ui_admin: ui_admin.render_admin_console()
            else: st.error("Admin UI missing")
                
        else: # Default/Heir
            if ui_heirloom: ui_heirloom.render_family_archive()
            else: st.error("Heirloom UI missing")
        return

    # --- PUBLIC ROUTES ---
    if nav == "login" or nav == "advisor":
        if ui_login: ui_login.render_login_page()
        else: st.error("Login UI missing")
        
    elif nav == "archive":
        if ui_login: ui_login.render_login_page()
        else: st.error("Login UI missing")

    else:
        # Default: The Marketing Splash Page
        if ui_splash and hasattr(ui_splash, 'render_splash_page'):
            ui_splash.render_splash_page()
        elif ui_splash and hasattr(ui_splash, 'render_splash'):
            ui_splash.render_splash()
        else:
            # Fallback if splash is broken
            st.title("VerbaPost")
            if st.button("Go to Login"):
                st.query_params["nav"] = "login"
                st.rerun()

if __name__ == "__main__":
    main()