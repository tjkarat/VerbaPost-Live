import streamlit as st
import ui_login
import ui_advisor
import ui_heirloom
import ui_admin
import ui_splash

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="VerbaPost",
    page_icon="📬",
    layout="centered",
    initial_sidebar_state="auto"  # Changed from 'collapsed' to 'auto' so you see it
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
    if "user_email" not in st.session_state:
        st.session_state.user_email = ""

    # 2. Global Sidebar (Restored Admin Tools)
    if st.session_state.authenticated:
        with st.sidebar:
            st.write(f"User: **{st.session_state.user_email}**")
            st.write(f"Role: **{st.session_state.user_role.title()}**")
            
            # --- RESTORED: ROLE SWITCHER ---
            # Checks for explicit 'admin' role OR the hardcoded dev email
            is_admin = (st.session_state.user_role == "admin") or (st.session_state.user_email == "pat@gmail.com")
            
            if is_admin:
                st.divider()
                st.caption("🛠️ Admin / Dev Tools")
                
                if st.button("⚙️ Admin Console", use_container_width=True):
                    st.session_state.user_role = "admin"
                    st.rerun()
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("👔 Advisor", use_container_width=True):
                        st.session_state.user_role = "advisor"
                        st.rerun()
                with col2:
                    if st.button("📂 Heir", use_container_width=True):
                        st.session_state.user_role = "heir"
                        st.rerun()
            
            # Advisor specific toggle (Heir View Check)
            elif st.session_state.user_role == 'advisor':
                st.divider()
                if st.button("👀 View as Heir", use_container_width=True):
                    st.query_params["nav"] = "archive"
                    st.rerun()

            st.divider()
            if st.button("Log Out", use_container_width=True):
                handle_logout()

    # 3. Routing Logic
    query_params = st.query_params
    nav = query_params.get("nav")

    # --- ROUTE: AUTHENTICATED USERS ---
    if st.session_state.authenticated:
        role = st.session_state.user_role
        
        # --- DUAL ROLE CHECK ---
        force_heir = False
        if "pending_play_id" in st.session_state:
            force_heir = True
        if nav == "archive":
            force_heir = True
            
        if force_heir:
            if hasattr(ui_heirloom, 'render_family_archive'):
                ui_heirloom.render_family_archive()
            elif hasattr(ui_heirloom, 'render_dashboard'):
                 ui_heirloom.render_dashboard()
            else:
                st.error("Error: Heirloom view not found.")
            return

        # --- STANDARD ROLE ROUTING ---
        if role == "advisor":
            if hasattr(ui_advisor, 'render_advisor_portal'):
                ui_advisor.render_advisor_portal()
            elif hasattr(ui_advisor, 'render_dashboard'):
                ui_advisor.render_dashboard()
            else:
                st.error("Error: Advisor view not found.")
        
        elif role == "admin":
            if hasattr(ui_admin, 'render_admin_console'):
                ui_admin.render_admin_console()
            else:
                st.error("Error: Admin view not found.")
                
        else:
            # Fallback for standard users (Heirloom)
            if hasattr(ui_heirloom, 'render_family_archive'):
                ui_heirloom.render_family_archive()
            elif hasattr(ui_heirloom, 'render_dashboard'):
                 ui_heirloom.render_dashboard()
            else:
                st.error("Error: Heirloom view not found.")
        
        return  # Stop here so we don't render public pages

    # --- ROUTE: PUBLIC VISITORS (Unauthenticated) ---
    if nav == "login" or nav == "advisor":
        ui_login.render_login_page()
        
    elif nav == "archive":
        # Direct link to archive (triggers login inside heirloom if needed)
        if hasattr(ui_heirloom, 'render_family_archive'):
            ui_heirloom.render_family_archive()
        else:
             ui_login.render_login_page()

    else:
        # Default: The Marketing Splash Page
        if hasattr(ui_splash, 'render_splash_page'):
            ui_splash.render_splash_page()
        else:
            st.error("Error: Splash page function 'render_splash_page' not found.")

if __name__ == "__main__":
    main()