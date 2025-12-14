import streamlit as st
import payment_engine
import auth_engine
import audit_engine
import ui_main
import ui_legacy
import ui_splash
import ui_login
import ui_admin
import ui_legal
import database

# FIX: Collapsed Sidebar
st.set_page_config(page_title="VerbaPost", page_icon="📮", layout="wide", initial_sidebar_state="collapsed")

def render_sidebar():
    with st.sidebar:
        st.markdown("# 📮 VerbaPost")
        if st.button("🏠 Home"): 
            st.session_state.app_mode = "splash"
            st.rerun()
        if st.button("🔐 Login"): 
            st.session_state.app_mode = "login"
            st.rerun()

        # FIX: Admin Access
        email = st.session_state.get("user_email")
        if email in ["admin@verbapost.com", "tjkarat@gmail.com"]:
            st.markdown("---")
            if st.button("⚙️ Admin Console"): 
                st.session_state.app_mode = "admin"
                st.rerun()

        st.markdown("---")
        st.info("Support: support@verbapost.com")

def main():
    if "app_mode" not in st.session_state: st.session_state.app_mode = "splash"
    
    render_sidebar()
    
    # Check Payment Return
    qs = st.query_params
    if "session_id" in qs and qs["session_id"] != st.session_state.get("last_processed"):
        res = payment_engine.verify_session(qs["session_id"])
        if res and res.get("paid"):
            st.session_state.last_processed = qs["session_id"]
            if res.get("email"): st.session_state.user_email = res["email"]
            
            # FIX: Update draft to "Paid"
            if st.session_state.get("current_legacy_draft_id"):
                database.update_draft_data(st.session_state.current_legacy_draft_id, status="Paid")
            
            # Set Legacy Success Flag
            st.session_state.paid_success = True
            
            # Route to correct view
            if st.session_state.get("current_legacy_draft_id"):
                st.session_state.app_mode = "legacy"
            else:
                st.session_state.app_mode = "review" # or a success page for main
                
            st.toast("Payment Successful!")
        st.query_params.clear()

    mode = st.session_state.app_mode
    
    if mode == "splash": ui_splash.render_splash_page()
    elif mode == "login": ui_login.render_login_page()
    elif mode == "admin": 
        # Double check auth
        if st.session_state.get("user_email") in ["admin@verbapost.com", "tjkarat@gmail.com"]:
            ui_admin.render_admin_page()
        else:
            st.error("Access Denied")
    elif mode == "legacy": ui_legacy.render_legacy_page()
    else: ui_main.render_main()

if __name__ == "__main__":
    main()