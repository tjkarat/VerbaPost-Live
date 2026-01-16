import streamlit as st
import time

def render_login_page():
    """
    Unified Auth Page.
    """
    # --- LAZY IMPORTS (CRITICAL FIX) ---
    # Moving these inside the function stops the crash
    import auth_engine
    import database
    import mailer
    
    st.markdown("""
    <style>
    .auth-container { max-width: 400px; margin: 0 auto; padding-top: 2rem; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("<div class='auth-container'>", unsafe_allow_html=True)
    st.markdown("## Welcome to VerbaPost")
    
    nav_mode = st.query_params.get("nav")
    if nav_mode == "advisor":
        st.caption("💼 Advisor Portal Access")
    else:
        st.caption("Sign in to manage your letters")

    # --- GOOGLE AUTH BUTTON ---
    if st.button("🇬 Google Sign In", key="google_auth_btn", use_container_width=True):
        try:
            auth_url = auth_engine.get_google_auth_url()
            # Show link as backup in case redirect fails
            st.link_button("👉 Click here to continue", auth_url)
            # Auto-redirect
            st.markdown(f'<meta http-equiv="refresh" content="0;url={auth_url}">', unsafe_allow_html=True)
        except Exception as e:
            st.error(f"Google Config Error: {e}")

    st.markdown("---") 

    tab1, tab2, tab3 = st.tabs(["Sign In", "Create Account", "Recovery"])

    # --- TAB 1: LOGIN ---
    with tab1:
        with st.form("login_form"):
            email = st.text_input("Email", key="login_email").strip()
            password = st.text_input("Password", type="password", key="login_pass")
            submit = st.form_submit_button("Sign In", use_container_width=True)
            
            if submit:
                with st.spinner("Verifying..."):
                    user, error = auth_engine.sign_in(email, password)
                    if user:
                        st.session_state.authenticated = True
                        st.session_state.user_email = user.email
                        
                        profile = database.get_user_profile(user.email)
                        if profile:
                            st.session_state.user_role = profile.get("role", "user")
                        
                        st.success("Success!")
                        st.query_params.clear()
                        st.rerun()
                    else:
                        st.error(f"Login failed: {error}")

    # --- TAB 2: SIGN UP ---
    with tab2:
        target_role = "advisor" if nav_mode == "advisor" else "user"
        if target_role == "advisor":
            st.info("✨ Creating Advisor Account")
            
        with st.form("signup_form"):
            new_email = st.text_input("Email", key="su_email").strip()
            new_pass = st.text_input("Password", type="password", key="su_pass")
            full_name = st.text_input("Full Name", key="su_name")
            
            st.caption("Mailing Address")
            s_street = st.text_input("Street", key="su_street")
            c1, c2 = st.columns(2)
            s_city = c1.text_input("City", key="su_city")
            s_state = c2.text_input("State", key="su_state")
            s_zip = st.text_input("Zip", key="su_zip")
            
            if st.form_submit_button("Create Account", use_container_width=True):
                with st.spinner("Creating account..."):
                    is_valid, val_result = mailer.validate_address({
                        "street": s_street, "city": s_city, 
                        "state": s_state, "zip": s_zip
                    })
                    
                    if not is_valid:
                        st.error(f"Address Error: {val_result}")
                    else:
                        user, error = auth_engine.sign_up(new_email, new_pass, {"full_name": full_name})
                        if user:
                            database.create_user_profile(new_email, full_name, target_role, val_result)
                            st.success("Account created! Check email.")
                        else:
                            st.error(f"Signup Error: {error}")

    # --- TAB 3: RECOVERY ---
    with tab3:
        rec_email = st.text_input("Email", key="rec_email")
        if st.button("Send Recovery Link"):
            success, msg = auth_engine.send_password_reset(rec_email)
            if success: st.success("Link sent.")
            else: st.error(msg)

    st.markdown("</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    render_login_page()