import streamlit as st
import ui_login
import ui_advisor
import ui_heirloom
import ui_admin
import ui_splash
import auth_engine  # Needed for Google Callback
import database     # Needed for Profile Sync

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="VerbaPost",
    page_icon="📬",
    layout="centered",
    initial_sidebar_state="auto"
)

def handle_logout():
    """Clear session and reload to home."""
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.query_params.clear()
    st.rerun()

def main():
    # 1. Initialize Session State
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "user_role" not in st.session_state:
        st.session_state.user_role = "user"

    # --- CRITICAL FIX: HANDLE GOOGLE CALLBACK ---
    # This must happen BEFORE the router logic
    query_params = st.query_params
    if "code" in query_params and not st.session_state.authenticated:
        try:
            with st.spinner("Authenticating with Google..."):
                # Exchange code for user session
                user, error = auth_engine.handle_google_callback(query_params["code"])
                if user:
                    st.session_state.authenticated = True
                    st.session_state.user_email = user.email
                    
                    # Sync Role
                    profile = database.get_user_profile(user.email)
                    if profile:
                        st.session_state.user_role = profile.get("role", "user")
                    
                    # Cleanup URL and Enter
                    st.query_params.clear()
                    st.rerun()
                else:
                    st.error(f"Google Auth Failed: {error}")
        except Exception as e:
            st.error(f"Auth Error: {e}")

    # 2. GLOBAL SIDEBAR (Visible only when logged in)
    if st.session_state.authenticated:
        with st.sidebar:
            st.write(f"User: **{st.session_state.get('user_email')}**")
            st.write(f"Role: **{st.session_state.user_role.title()}**")
            
            # Role Switcher for Admin/Dev
            # Update 'pat@gmail.com' to your actual admin email if different
            is_admin = (st.session_state.user_role == "admin") or (st.session_state.get("user_email") == "pat@gmail.com")
            
            if is_admin:
                st.divider()
                st.caption("🛠️ Admin Tools")
                if st.button("⚙️ Admin"): 
                    st.session_state.user_role = "admin"
                    st.rerun()
                if st.button("👔 Advisor"): 
                    st.session_state.user_role = "advisor"
                    st.rerun()
                if st.button("📂 Heir"): 
                    st.session_state.user_role = "heir"
                    st.rerun()
            
            elif st.session_state.user_role == 'advisor':
                st.divider()
                if st.button("👀 View as Heir"):
                    st.query_params["nav"] = "archive"
                    st.rerun()

            st.divider()
            if st.button("Log Out"):
                handle_logout()

    # 3. ROUTING LOGIC
    nav = query_params.get("nav")

    # --- AUTHENTICATED ROUTES ---
    if st.session_state.authenticated:
        role = st.session_state.user_role
        
        # Dual Role / Force Heir View
        force_heir = ("pending_play_id" in st.session_state) or (nav == "archive")
        
        if force_heir:
            if hasattr(ui_heirloom, 'render_family_archive'):
                ui_heirloom.render_family_archive()
            elif hasattr(ui_heirloom, 'render_dashboard'):
                 ui_heirloom.render_dashboard()
            return

        # Role Routing
        if role == "advisor":
            if hasattr(ui_advisor, 'render_advisor_portal'):
                ui_advisor.render_advisor_portal()
            elif hasattr(ui_advisor, 'render_dashboard'):
                ui_advisor.render_dashboard()
        
        elif role == "admin":
            if hasattr(ui_admin, 'render_admin_console'):
                ui_admin.render_admin_console()
            else:
                st.write("Admin Console not found.")
                
        else: # Default/Heir
            if hasattr(ui_heirloom, 'render_family_archive'):
                ui_heirloom.render_family_archive()
            elif hasattr(ui_heirloom, 'render_dashboard'):
                 ui_heirloom.render_dashboard()
        return

    # --- PUBLIC ROUTES ---
    if nav == "login" or nav == "advisor":
        ui_login.render_login_page()
    elif nav == "archive":
        # Deep link to archive (triggers login inside if needed)
        ui_login.render_login_page()
    else:
        # Default: The Marketing Splash Page
        if hasattr(ui_splash, 'render_splash_page'):
            ui_splash.render_splash_page()
        elif hasattr(ui_splash, 'render_splash'):
            ui_splash.render_splash()

if __name__ == "__main__":
    main()