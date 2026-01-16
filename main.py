import streamlit as st
import time
import ui_login
import ui_advisor
import ui_heirloom
import ui_admin
import ui_splash

# --- AUTH IMPORTS ---
try: import auth_engine
except ImportError: auth_engine = None
try: import database
except ImportError: database = None

# --- CONFIG ---
st.set_page_config(
    page_title="VerbaPost",
    page_icon="📬",
    layout="centered",
    initial_sidebar_state="expanded" # FORCE OPEN SIDEBAR
)

def handle_logout():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.query_params.clear()
    st.rerun()

def main():
    # 1. INIT STATE
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "user_role" not in st.session_state:
        st.session_state.user_role = "user"
    if "user_email" not in st.session_state:
        st.session_state.user_email = None

    # 2. GLOBAL SIDEBAR (Debug & Admin)
    with st.sidebar:
        st.header("VerbaPost Admin")
        
        # SYSTEM CHECK (Visible Debugging)
        if st.checkbox("Show System Status", value=True):
            st.caption(f"Auth Engine: {'✅ Loaded' if auth_engine else '❌ Missing'}")
            st.caption(f"Database: {'✅ Loaded' if database else '❌ Missing'}")
            st.caption(f"Logged In: {st.session_state.authenticated}")
        
        if st.session_state.authenticated:
            st.success(f"User: {st.session_state.user_email}")
            st.info(f"Role: {st.session_state.user_role}")
            
            # ADMIN SWITCHER
            # Update 'pat@gmail.com' to match your actual admin email
            is_admin = (st.session_state.user_role == "admin") or (st.session_state.user_email == "pat@gmail.com")
            
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
            
            st.divider()
            if st.button("🚪 Log Out"):
                handle_logout()
        else:
            st.warning("Not Logged In")

    # 3. GOOGLE CALLBACK LISTENER (Must be before Routing)
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
                        
                        # Sync Role
                        if database:
                            profile = database.get_user_profile(user.email)
                            if profile:
                                st.session_state.user_role = profile.get("role", "user")
                        
                        st.success(f"✅ Welcome, {user.email}")
                        time.sleep(1)
                        st.query_params.clear()
                        st.rerun()
                    else:
                        st.error(f"❌ Google Auth Failed: {error}")
            except Exception as e:
                st.error(f"⚠️ Auth Exception: {e}")
        else:
            st.error("⚠️ Auth Engine missing. Cannot login.")

    # 4. ROUTING
    nav = query_params.get("nav")
    
    # Bridge for old Splash buttons
    if not nav and st.session_state.get("app_mode") == "login":
        nav = "login"

    # --- AUTHENTICATED ---
    if st.session_state.authenticated:
        role = st.session_state.user_role
        
        force_heir = ("pending_play_id" in st.session_state) or (nav == "archive")
        
        if force_heir:
            if ui_heirloom: ui_heirloom.render_family_archive()
            else: st.error("Heirloom UI missing")
            return

        if role == "advisor":
            if ui_advisor: ui_advisor.render_advisor_portal()
            else: st.error("Advisor UI missing")
        elif role == "admin":
            if ui_admin: ui_admin.render_admin_console()
            else: st.error("Admin UI missing")
        else: 
            if ui_heirloom: ui_heirloom.render_family_archive()
            else: st.error("Heirloom UI missing")
        return

    # --- PUBLIC ---
    if nav == "login" or nav == "advisor":
        if ui_login: ui_login.render_login_page()
        else: st.error("Login UI missing")
    elif nav == "archive":
        if ui_login: ui_login.render_login_page()
        else: st.error("Login UI missing")
    else:
        if ui_splash:
            if hasattr(ui_splash, 'render_splash_page'):
                ui_splash.render_splash_page()
            else:
                st.write("Splash page function not found.")
        else:
            st.write("Splash module missing.")

if __name__ == "__main__":
    main()