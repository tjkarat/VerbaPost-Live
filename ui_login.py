import streamlit as st

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
            
            tab_login, tab_signup = st.tabs(["🔑 Log In", "📝 Sign Up"])
            
            # --- LOGIN ---
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
                
                if st.button("🔑 Lost Password?", type="secondary", use_container_width=True):
                    st.session_state.current_view = "forgot_password"
                    st.rerun()
            
            # --- SIGNUP WITH ADDRESS ---
            with tab_signup:
                st.caption("Create your account to save your Return Address.")
                new_email = st.text_input("Email", key="new_email")
                new_pass = st.text_input("Password", type="password", key="new_pass")
                confirm_pass = st.text_input("Confirm Password", type="password", key="confirm_pass")
                
                st.markdown("---")
                st.markdown("**Your Return Address**")
                name = st.text_input("Full Name", placeholder="John Doe")
                addr = st.text_input("Street Address", placeholder="123 Main St")
                
                c_city, c_state, c_zip = st.columns([2, 1, 1])
                city = c_city.text_input("City")
                state = c_state.text_input("State")
                zip_code = c_zip.text_input("Zip")
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                if st.button("Create Account", type="primary", use_container_width=True):
                    if new_pass != confirm_pass:
                        st.error("❌ Passwords do not match")
                    elif new_email and new_pass and name and addr and zip_code:
                        with st.spinner("Creating account..."):
                            signup_func(new_email, new_pass, name, addr, city, state, zip_code, "English")
                    else:
                        st.warning("Please fill in all fields (Email, Password, Name, Address)")

    f1, f2, f3 = st.columns([1, 2, 1])
    with f2:
        if st.button("← Back to Home", type="secondary", use_container_width=True):
            st.session_state.app_mode = "splash"
            st.rerun()

def show_forgot_password(send_code_func):
    st.info("Feature coming soon.")
    if st.button("Back"): st.session_state.app_mode = "login"; st.rerun()

def show_reset_verify(verify_func):
    pass