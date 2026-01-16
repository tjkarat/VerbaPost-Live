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
    initial_sidebar_state="collapsed"
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

    # 2. Global Sidebar (For Logged In Users)
    if st.session_state.authenticated:
        with st.sidebar:
            st.write(f"Logged in as: **{st.session_state.user_role.title()}**")
            
            # Debug/Test Control: Allow Advisors to switch views manually
            if st.session_state.user_role == 'advisor':
                if st.button("Switch to Heir View"):
                    st.query_params["nav"] = "archive"
                    st.rerun()

            if st.button("Log Out"):
                handle_logout()

    # 3. Routing Logic
    query_params = st.query_params
    nav = query_params.get("nav")

    # --- ROUTE: AUTHENTICATED USERS ---
    if st.session_state.authenticated:
        role = st.session_state.user_role
        
        # --- DUAL ROLE CHECK (THE FIX) ---
        # If user is Advisor BUT has a 'play' context (QR code) or requested archive,
        # we FORCE the Heir view.
        force_heir = False
        if "pending_play_id" in st.session_state:
            force_heir = True
        if nav == "archive":
            force_heir = True
            
        if force_heir:
            try:
                ui_heirloom.render_family_archive()
            except AttributeError:
                st.error("Error: Heirloom view not found.")
            return

        # --- STANDARD ROLE ROUTING ---
        if role == "advisor":
            # 💼 Advisor Portal
            try:
                ui_advisor.render_advisor_portal()
            except AttributeError:
                st.error("Error: Advisor view not found. Check `ui_advisor.render_advisor_portal`.")
        
        elif role == "admin":
            # ⚙️ Admin Console
            try:
                ui_admin.render_admin_console()
            except AttributeError:
                st.error("Error: Admin view not found.")
                
        else:
            # 🏡 Heir/User Portal (Default Fallback)
            try:
                ui_heirloom.render_family_archive()
            except AttributeError:
                st.error("Error: Heirloom view not found.")
        
        return  # Stop here so we don't render public pages

    # --- ROUTE: PUBLIC VISITORS (Unauthenticated) ---
    if nav == "login" or nav == "advisor":
        # The 'advisor' param just triggers the login page with advisor messaging
        ui_login.render_login_page()
        
    elif nav == "archive":
        # Direct link to archive (might trigger login inside)
        try:
            ui_heirloom.render_family_archive()
        except AttributeError:
             ui_login.render_login_page()

    else:
        # Default: The Marketing Splash Page
        ui_splash.render_splash()

if __name__ == "__main__":
    main()