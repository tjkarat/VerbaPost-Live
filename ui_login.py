import streamlit as st
import auth_engine
import time

def render_login():
    """
    Renders the Authentication Interface (Login, Signup, Forgot Password).
    Highlights the active tab in RED (#FF4B4B) to match branding.
    """
    # --- CSS STYLING FOR RED TABS ---
    st.markdown("""
    <style>
        /* Center the main header */
        .auth-header {
            text-align: center;
            font-weight: 700;
            color: #203A60;
            margin-bottom: 20px;
        }
        
        /* STREAMLIT TAB OVERRIDES 
           This forces the selected tab to be Red (#FF4B4B)
        */
        
        /* The text color of the UNSELECTED tabs */
        .stTabs [data-baseweb="tab-list"] button {
            color: #555;
            font-weight: 600;
        }

        /* The text color of the SELECTED tab */
        .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] div {
            color: #FF4B4B !important;
            font-weight: 800 !important;
            font-size: 1.1rem;
        }

        /* The underline indicator of the selected tab */
        .stTabs [data-baseweb="tab-highlight"] {
            background-color: #FF4B4B !important;
            height: 3px;
        }

        /* Hover effect */
        .stTabs [data-baseweb="tab-list"] button:hover {
            color: #FF4B4B !important;
        }
        
        /* Make form buttons full width and bold */
        .stButton button {
            width: 100%;
            font-weight: 700;
            border-radius: 8px;
        }
    </style>
    """, unsafe_allow_html=True)

    # --- HANDLE PASSWORD RESET RETURN ---
    # If the user clicked a magic link in email, Supabase sends them back with params.
    # We check for 'type=recovery' to show the actual reset form immediately.
    q_params = st.query_params
    if q_params.get("type") == "recovery":
        render_reset_password_interface()
        return

    # --- MAIN AUTH UI ---
    st.markdown("<h2 class='auth-header'>Access VerbaPost</h2>", unsafe_allow_html=True)
    
    # 1. Determine which tab to show first based on previous actions
    default_idx = 0
    if st.session_state.get("auth_view") == "signup":
        default_idx = 1
    
    # 2. Define Explicit Tabs
    tab1, tab2, tab3 = st.tabs([
        "🔑 Returning User (Log In)", 
        "✨ New User (Sign Up)", 
        "❓ Forgot Password"
    ])

    # --- TAB 1: LOG IN ---
    with tab1:
        st.write("")
        st.info("👋 Access your existing account.")
        with st.form("login_form"):
            email = st.text_input("Email Address", key="login_email")
            password = st.text_input("Password", type="password", key="login_pass")
            
            # Submit Button
            if st.form_submit_button("Log In", type="primary"):
                if not email or not password:
                    st.error("Please enter both email and password.")
                else:
                    res, err = auth_engine.sign_in(email, password)
                    if res:
                        st.session_state.authenticated = True
                        st.session_state.user_email = email
                        st.session_state.user_id = res.user.id
                        st.success("Login successful! Redirecting...")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error(err)

    # --- TAB 2: SIGN UP ---
    with tab2:
        st.write("")
        st.success("🚀 Create a new account to start sending mail.")
        with st.form("signup_form"):
            new_email = st.text_input("Email Address", key="signup_email")
            new_pass = st.text_input("Create Password", type="password", help="Min 8 chars, 1 uppercase, 1 lowercase, 1 number", key="signup_pass")
            full_name = st.text_input("Full Name")
            
            st.markdown("---")
            st.caption("📍 Return Address (Required for USPS)")
            
            c1, c2 = st.columns(2)
            street = c1.text_input("Street Address")
            street2 = c2.text_input("Apt / Suite")
            
            c3, c4, c5 = st.columns([2, 1, 1])
            city = c3.text_input("City")
            state = c4.text_input("State")
            zip_code = c5.text_input("Zip")
            
            # Submit Button
            if st.form_submit_button("Create Account", type="primary"):
                if not new_email or not new_pass or not street or not city or not state or not zip_code:
                    st.error("Please fill in all required fields.")
                else:
                    res, err = auth_engine.sign_up(
                        new_email, new_pass, full_name, 
                        street, street2, city, state, zip_code, "US", "English"
                    )
                    if res:
                        st.success("Account created! Please check your email to confirm.")
                    else:
                        st.error(err)

    # --- TAB 3: FORGOT PASSWORD (Recovery) ---
    with tab3:
        st.write("")
        st.warning("🔒 Reset your password")
        st.write("Enter your email address below. We will send you a secure link to reset your password.")
        
        with st.form("forgot_pass_form"):
            reset_email = st.text_input("Email Address", key="reset_email")
            submitted = st.form_submit_button("Send Reset Link")
            
            if submitted:
                if not reset_email:
                    st.error("Please enter your email.")
                else:
                    success, msg = auth_engine.send_password_reset(reset_email)
                    if success:
                        st.success("Check your email for the password reset link!")
                    else:
                        st.error(msg)
        
        st.markdown("<br>", unsafe_allow_html=True)
        with st.expander("I have a token code"):
            st.info("If the link didn't work automatically, paste the token from the email here.")
            m_token = st.text_input("Token / OTP")
            m_pass = st.text_input("New Password", type="password", key="manual_reset_pass")
            if st.button("Update Password"):
                if not reset_email or not m_token or not m_pass:
                    st.error("Please fill in Email (above), Token, and New Password.")
                else:
                    success, msg = auth_engine.reset_password_with_token(reset_email, m_token, m_pass)
                    if success:
                        st.success("Password updated! Please log in.")
                    else:
                        st.error(msg)

def render_reset_password_interface():
    """
    Renders the specific form when a user returns via a 'Recovery' email link.
    """
    st.markdown("<h2 style='text-align: center; color: #FF4B4B;'>Set New Password</h2>", unsafe_allow_html=True)
    st.info("Please set a new password for your account.")
    
    with st.form("final_reset_form"):
        email_confirm = st.text_input("Confirm Email Address")
        # In some flows, the token is in the hash, Streamlit might not parse it easily.
        # We ask for it or try to find it. For now, manual paste is safest fallback if auto-detect fails.
        token_input = st.text_input("Token (Paste from email if not auto-filled)")
        new_pass = st.text_input("New Password", type="password")
        
        if st.form_submit_button("Change Password", type="primary"):
            success, msg = auth_engine.reset_password_with_token(email_confirm, token_input, new_pass)
            if success:
                st.balloons()
                st.success("Password Changed Successfully! Redirecting to login...")
                # Clear params to exit recovery mode
                st.query_params.clear()
                time.sleep(2)
                st.rerun()
            else:
                st.error(msg)