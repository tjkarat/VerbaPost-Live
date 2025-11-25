import streamlit as st

# --- MAIN LOGIN SCREEN ---
def show_login(login_func, signup_func):
    c1, c2, c3 = st.columns([1, 1.5, 1])
    
    with c2:
        st.markdown("""
        <div style="text-align: center; margin-bottom: 20px;">
            <h1 style="color: #2a5298 !important; margin-bottom: 0;">VerbaPost 📮</h1>
            <p style="font-size: 1.1em; color: #666 !important;">Member Access</p>
        </div>
        """, unsafe_allow_html=True)

        with st.container(border=True):
            if "auth_error" in st.session_state:
                st.error(st.session_state.auth_error)
                del st.session_state.auth_error
            
            tab_login, tab_signup = st.tabs(["🔑 Log In", "📝 Create Account"])
            
            with tab_login:
                email = st.text_input("Email Address", key="login_email")
                password = st.text_input("Password", type="password", key="login_pass")
                st.markdown("<br>", unsafe_allow_html=True)
                
                if st.button("Log In", type="primary", use_container_width=True):
                    if email and password:
                        with st.spinner("Verifying..."):
                            login_func(email, password)
                    else:
                        st.warning("Enter email & password")
                
                # --- NEW: FORGOT PASSWORD BUTTON ---
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("🔑 Lost Password?", type="secondary", use_container_width=True):
                    st.session_state.current_view = "forgot_password"
                    st.rerun()

            with tab_signup:
                new_email = st.text_input("Email", key="new_email")
                new_pass = st.text_input("Password", type="password", key="new_pass")
                st.markdown("---")
                name = st.text_input("Full Name")
                lang = st.selectbox("Language", ["English", "Spanish", "French"])
                
                st.caption("Address (for return labels)")
                addr = st.text_input("Street Address")
                c_city, c_state, c_zip = st.columns([2, 1, 1])
                city = c_city.text_input("City")
                state = c_state.text_input("State")
                zip_code = c_zip.text_input("Zip")
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                if st.button("Create Account", type="primary", use_container_width=True):
                    if new_email and new_pass:
                        with st.spinner("Creating account..."):
                            signup_func(new_email, new_pass, name, addr, city, state, zip_code, lang)
                    else:
                        st.warning("Missing fields")

    st.markdown("<br><br>", unsafe_allow_html=True)
    f1, f2, f3 = st.columns([1, 2, 1])
    with f2:
        if st.button("← Back to Home", type="secondary", use_container_width=True):
            st.session_state.current_view = "splash"
            st.rerun()

# --- NEW: STEP 1 - ASK FOR EMAIL ---
def show_forgot_password(send_code_func):
    c1, c2, c3 = st.columns([1, 1.5, 1])
    with c2:
        st.markdown("<h2 style='text-align: center; color: #2a5298 !important;'>Recovery 🔐</h2>", unsafe_allow_html=True)
        with st.container(border=True):
            st.info("Enter your email. We will send you a verification token.")
            email = st.text_input("Email Address", key="reset_email_input")
            
            if st.button("Send Token", type="primary", use_container_width=True):
                if email:
                    success, msg = send_code_func(email)
                    if success:
                        st.session_state.reset_email = email
                        st.session_state.current_view = "reset_verify"
                        st.rerun()
                    else:
                        st.error(f"Error: {msg}")
                else:
                    st.warning("Please enter your email")
            
            if st.button("Cancel", type="secondary", use_container_width=True):
                st.session_state.current_view = "login"
                st.rerun()

# --- NEW: STEP 2 - VERIFY TOKEN ---
def show_reset_verify(verify_func):
    c1, c2, c3 = st.columns([1, 1.5, 1])
    with c2:
        st.markdown("<h2 style='text-align: center; color: #2a5298 !important;'>Set Password 🔑</h2>", unsafe_allow_html=True)
        with st.container(border=True):
            email = st.session_state.get("reset_email", "")
            st.success(f"Token sent to: **{email}**")
            
            token = st.text_input("Enter Token (from email)")
            new_pass = st.text_input("New Password", type="password")
            
            if st.button("Update Password", type="primary", use_container_width=True):
                if token and new_pass:
                    success, msg = verify_func(email, token, new_pass)
                    if success:
                        st.success("✅ Password Updated! Please log in.")
                        if st.button("Go to Login"):
                            st.session_state.current_view = "login"
                            st.rerun()
                    else:
                        st.error(f"Failed: {msg}")
                else:
                    st.warning("Please enter token and new password")