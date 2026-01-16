import streamlit as st
import time

def render_login_page():
    """
    Unified Auth Page: Login, Signup, and Recovery.
    Features:
    - Implicit Role Assignment (Advisor vs User) based on URL.
    - Shake Animation on error.
    - Robust Address Validation handling.
    - RESTORED: Google Authentication
    - FIXED: Circular Import (Lazy Loading)
    """
    # --- LAZY IMPORTS (Breaks Circular Dependency) ---
    import auth_engine
    import database
    import mailer
    
    # --- CSS: Shake Animation & Clean Tabs ---
    st.markdown("""
    <style>
    @keyframes shake {
        0% { transform: translateX(0); }
        25% { transform: translateX(-5px); }
        50% { transform: translateX(5px); }
        75% { transform: translateX(-5px); }
        100% { transform: translateX(0); }
    }
    .shake {
        animation: shake 0.3s ease-in-out;
        border: 1px solid #ef4444 !important;
    }
    .auth-container {
        max-width: 400px;
        margin: 0 auto;
        padding-top: 2rem;
    }
    .google-btn {
        width: 100%;
        margin-bottom: 15px;
    }
    </style>
    """, unsafe_allow_html=True)

    # --- HEADER ---
    st.markdown("<div class='auth-container'>", unsafe_allow_html=True)
    st.markdown("## Welcome to VerbaPost")
    
    # Check Context for Messaging
    nav_mode = st.query_params.get("nav")
    if nav_mode == "advisor":
        st.caption("💼 Advisor Portal Access")
    elif st.session_state.get("pending_play_id"):
        st.caption("🎧 Login to access Family Archive")
    else:
        st.caption("Sign in to manage your letters")

    # --- GOOGLE AUTH ---
    if st.button("🇬 Google Sign In", key="google_auth_btn", use_container_width=True):
        try:
            auth_url = auth_engine.get_google_auth_url()
            st.link_button("Continue to Google", auth_url)
            st.markdown(f'<meta http-equiv="refresh" content="0;url={auth_url}">', unsafe_allow_html=True)
        except Exception as e:
            st.error(f"Google Auth Error: {e}")

    st.markdown("---") 

    tab1, tab2, tab3 = st.tabs(["Sign In", "Create Account", "Reset Password"])

    # ==========================================
    # 🔐 TAB 1: LOGIN
    # ==========================================
    with tab1:
        with st.form("login_form"):
            email = st.text_input("Email Address", key="login_email").strip()
            password = st.text_input("Password", type="password", key="login_pass")
            submit = st.form_submit_button("Sign In", use_container_width=True)
            
            if submit:
                if not email or not password:
                    st.error("Please enter both email and password.")
                else:
                    with st.spinner("Verifying credentials..."):
                        user, error = auth_engine.sign_in(email, password)
                        if user:
                            # Success: Set Session
                            st.session_state.authenticated = True
                            st.session_state.user_email = user.email
                            
                            # Sync Profile
                            profile = database.get_user_profile(user.email)
                            if profile:
                                st.session_state.user_role = profile.get("role", "user")
                            
                            st.success("Welcome back!")
                            time.sleep(0.5)
                            
                            # Fix Loop
                            st.query_params.clear() 
                            st.rerun()
                        else:
                            st.markdown(f"<div class='shake'></div>", unsafe_allow_html=True)
                            st.error(f"Login failed: {error}")

    # ==========================================
    # 🆕 TAB 2: SIGN UP
    # ==========================================
    with tab2:
        target_role = "user"
        if nav_mode == "advisor":
            target_role = "advisor"
            st.info("✨ Creating Professional Advisor Account")
        
        with st.form("signup_form"):
            new_email = st.text_input("Email", key="su_email").strip()
            new_pass = st.text_input("Password", type="password", key="su_pass")
            full_name = st.text_input("Full Name", key="su_name")
            
            st.markdown("---")
            st.caption("Mailing Address (For Return Address)")
            s_street = st.text_input("Street Address", key="su_street")
            c1, c2, c3 = st.columns([3, 1, 1])
            s_city = c1.text_input("City", key="su_city")
            s_state = c2.text_input("State", key="su_state")
            s_zip = c3.text_input("Zip", key="su_zip")
            
            su_submit = st.form_submit_button("Create Account", use_container_width=True)
            
            if su_submit:
                if not new_email or not new_pass or not s_street:
                    st.error("Please fill in all required fields.")
                else:
                    with st.spinner("Creating secure account..."):
                        # Address Validation
                        addr_payload = {
                            "street": s_street, "city": s_city, 
                            "state": s_state, "zip": s_zip
                        }
                        is_valid, val_result = mailer.validate_address(addr_payload)
                        
                        if not is_valid:
                            err_msg = val_result if isinstance(val_result, str) else "Address validation failed."
                            st.error(f"📍 {err_msg}")
                        else:
                            user, error = auth_engine.sign_up(
                                new_email, 
                                new_pass, 
                                data={"full_name": full_name, "role": target_role}
                            )
                            
                            if user:
                                database.create_user_profile(
                                    email=new_email,
                                    full_name=full_name,
                                    role=target_role,
                                    address=val_result 
                                )
                                st.success("Account created! Please check your email to confirm.")
                            else:
                                st.error(f"Signup failed: {error}")

    # ==========================================
    # 🔄 TAB 3: RECOVERY
    # ==========================================
    with tab3:
        st.caption("Enter your email to receive a recovery link.")
        rec_email = st.text_input("Email", key="rec_email")
        if st.button("Send Recovery Link"):
            if rec_email:
                success, msg = auth_engine.send_password_reset(rec_email)
                if success:
                    st.success("Check your email for the reset link.")
                else:
                    st.error(f"Error: {msg}")
            else:
                st.warning("Please enter your email.")

    st.markdown("</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    render_login_page()