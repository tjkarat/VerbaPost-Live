import streamlit as st

def validate_address(street, city, state, zip_code):
    errors = []
    if len(zip_code) != 5 or not zip_code.isdigit():
        errors.append("Zip code must be exactly 5 digits.")
    if len(state) != 2:
        errors.append("State must be a 2-letter abbreviation (e.g., TN, NY).")
    if len(street) < 5:
        errors.append("Street address looks too short.")
    return errors

def show_login(login_func, signup_func):
    # --- LAYOUT FIX: WIDENED COLUMNS ---
    # Changed from [1, 1.5, 1] to [1, 3, 1]
    c1, c2, c3 = st.columns([1, 3, 1])
    
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
            
            # --- LOGIN TAB ---
            with tab_login:
                with st.form("login_form"):
                    email = st.text_input("Email Address", key="login_email")
                    password = st.text_input("Password", type="password", key="login_pass")
                    st.markdown("<br>", unsafe_allow_html=True)
                    
                    submitted = st.form_submit_button("Log In", type="primary", use_container_width=True)
                    
                    if submitted:
                        if email and password:
                            with st.spinner("Verifying..."):
                                login_func(email, password)
                        else:
                            st.warning("Enter email & password")
                
                # Forgot Password Link
                if st.button("🔑 Lost Password?", type="secondary", use_container_width=True):
                    st.session_state.app_mode = "forgot_password"
                    st.rerun()
            
            # --- SIGNUP TAB ---
            with tab_signup:
                st.caption("Please fill out your details below. Your address is required for return labels.")
                
                with st.form("signup_form"):
                    new_email = st.text_input("Email")
                    new_pass = st.text_input("Password", type="password")
                    confirm_pass = st.text_input("Confirm Password", type="password")
                    
                    st.markdown("---")
                    st.markdown("**Your Return Address**")
                    name = st.text_input("Full Legal Name", placeholder="e.g. John Doe")
                    addr = st.text_input("Street Address", placeholder="e.g. 123 Main St")
                    
                    c_city, c_state, c_zip = st.columns([2, 1, 1])
                    city = c_city.text_input("City")
                    state = c_state.text_input("State (2 letters)")
                    zip_code = c_zip.text_input("Zip Code (5 digits)")
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    
                    submitted_signup = st.form_submit_button("Create Account", type="primary", use_container_width=True)
                    
                    if submitted_signup:
                        # Validation
                        addr_errors = validate_address(addr, city, state, zip_code)
                        
                        if new_pass != confirm_pass:
                            st.error("❌ Passwords do not match")
                        elif not new_email or not name:
                            st.error("❌ Name and Email are required.")
                        elif addr_errors:
                            for e in addr_errors: st.error(f"❌ {e}")
                        else:
                            with st.spinner("Creating account..."):
                                signup_func(new_email, new_pass, name, addr, city, state, zip_code, "English")

    f1, f2, f3 = st.columns([1, 2, 1])
    with f2:
        if st.button("← Back to Home", type="secondary", use_container_width=True):
            st.session_state.app_mode = "splash"
            st.rerun()

# ... (Rest of file remains unchanged) ...
def show_forgot_password(send_code_func):
    c1, c2, c3 = st.columns([1, 1.5, 1]) # Keep this one narrow for password reset
    with c2:
        st.markdown("<h2 style='text-align: center; color: #2a5298 !important;'>Recovery 🔐</h2>", unsafe_allow_html=True)
        with st.container(border=True):
            st.info("Enter your email. We will send you a verification token.")
            email = st.text_input("Email Address", key="reset_email_input")
            if st.button("Send Token", type="primary", use_container_width=True):
                if email and send_code_func:
                    success, msg = send_code_func(email)
                    if success:
                        st.session_state.reset_email = email
                        st.session_state.app_mode = "reset_verify" 
                        st.rerun()
                    else: st.error(f"Error: {msg}")
                else: st.warning("Please enter your email")
            if st.button("Cancel", type="secondary", use_container_width=True):
                st.session_state.app_mode = "login"; st.rerun()

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
                if token and new_pass and verify_func:
                    success, msg = verify_func(email, token, new_pass)
                    if success:
                        st.success("✅ Password Updated! Please log in.")
                        if st.button("Go to Login"):
                            st.session_state.app_mode = "login"; st.rerun()
                    else: st.error(f"Failed: {msg}")
                else: st.warning("Please enter token and new password")