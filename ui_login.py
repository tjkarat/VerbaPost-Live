import streamlit as st
import auth_engine
import time

def render_login():
    """
    Renders the Authentication Interface (Login, Signup, Forgot Password).
    Includes CSS to highlight the active tab in Red.
    """
    # --- CSS STYLING ---
    st.markdown("""
    <style>
        /* General Auth Container styling */
        .auth-header {
            text-align: center;
            font-weight: 700;
            color: #203A60;
            margin-bottom: 10px;
        }
        
        /* CUSTOM TAB STYLING 
           Targeting Streamlit's internal classes to force the Active Tab to be Red 
        */
        
        /* The text color of the selected tab */
        .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] div {
            color: #FF4B4B !important;
            font-weight: 800 !important;
        }

        /* The underline indicator color of the selected tab */
        .stTabs [data-baseweb="tab-highlight"] {
            background-color: #FF4B4B !important;
        }

        /* Hover effect for tabs */
        .stTabs [data-baseweb="tab-list"] button:hover {
            color: #FF4B4B !important;
        }
        
        /* Form Submit Buttons */
        .stButton button {
            width: 100%;
            border-radius: 8px;
            font-weight: 600;
        }
    </style>
    """, unsafe_allow_html=True)

    # --- PASSWORD RESET RETURN HANDLER ---
    # Checks if user arrived via email link (Supabase redirect)
    query_params = st.query_params
    if "type" in query_params and query_params["type"] == "recovery":
        render_reset_password_interface()
        return

    # --- MAIN UI ---
    st.markdown("<h2 class='auth-header'>Access VerbaPost</h2>", unsafe_allow_html=True)
    
    # Determine default tab based on previous interactions
    default_index = 0
    if st.session_state.get("auth_view") == "signup":
        default_index = 1
        
    # Explicit Tab Names
    tab1, tab2, tab3 = st.tabs(["🔑 Returning User", "✨ New User", "❓ Forgot Password"])

    # --- TAB 1: RETURNING USER (LOGIN) ---
    with tab1:
        st.write("")
        st.markdown("##### Welcome Back! Please log in.")
        with st.form("login_form"):
            email = st.text_input("Email Address", key="login_email")
            password = st.text_input("Password", type="password", key="login_pass")
            submit = st.form_submit_button("Log In", type="primary", use_container_width=True)
            
            if submit:
                if not email or not password:
                    st.error("Please fill in all fields.")
                else:
                    res, err = auth_engine.sign_in(email, password)
                    if res:
                        st.session_state.authenticated = True
                        st.session_state.user_email = email
                        st.session_state.user_id = res.user.id
                        st.success("Login successful!")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error(err)

    # --- TAB 2: NEW USER (SIGN UP) ---
    with tab2:
        st.write("")
        st.markdown("##### Create your account to start sending mail.")
        with st.form("signup_form"):
            new_email = st.text_input("Email Address", key="signup_email")
            new_pass = st.text_input("Create Password", type="password", help="Min 8 chars, 1 uppercase, 1 lowercase, 1 number", key="signup_pass")
            full_name = st.text_input("Full Name")
            
            st.markdown("---")
            st.caption("📍 Return Address (Required for USPS return mail)")
            c1, c2 = st.columns(2)
            street = c1.text_input("Street Address")
            street2 = c2.text_input("Apt / Suite")
            
            c3, c4, c5 = st.columns([2, 1, 1])
            city = c3.text_input("City")
            state = c4.text_input("State")
            zip_code = c5.text_input("Zip")
            
            if st.form_submit_button("Sign Up & Create Account", type="primary", use_container_width=True):
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

    # --- TAB 3: FORGOT PASSWORD ---
    with tab3:
        st.write("")
        st.markdown("##### Reset your password")
        st.write("Enter your email address and we'll send you a secure link.")
        with st.form("forgot_pass_form"):
            reset_email = st.text_input("Email Address", key="reset_email")
            submitted = st.form_submit_button("Send Reset Link", use_container_width=True)
            
            if submitted:
                if not reset_email:
                    st.error("Please enter your email.")
                else:
                    success, msg = auth_engine.send_password_reset(reset_email)
                    if success:
                        st.success("Check your email for the password reset link!")
                    else:
                        st.error(msg)
        
        st.markdown("---")
        # Manual Token Entry (Optional fallback)
        with st.expander("Have a code to enter manually?"):
            st.caption("If the link didn't work, paste the token code here.")
            m_token = st.text_input("Token / Code")
            m_pass = st.text_input("New Password", type="password", key="m_reset_pass")
            if st.button("Update Password"):
                if not m_token or not m_pass:
                    st.error("Missing token or password")
                else:
                    # Use reset_email from the form above, or ask user to re-type if needed
                    # For simplicity assuming they typed it in the form above
                    if not reset_email:
                        st.error("Please enter your email in the box above first.")
                    else:
                        success, msg = auth_engine.reset_password_with_token(reset_email, m_token, m_pass)
                        if success:
                            st.success("Password updated! Please log in.")
                        else:
                            st.error(msg)

def render_reset_password_interface():
    """
    Renders when user clicks the email link and returns to the app.
    """
    st.markdown("<h3 style='text-align: center; color: #FF4B4B;'>Reset Your Password</h3>", unsafe_allow_html=True)
    
    with st.form("final_reset"):
        email_confirm = st.text_input("Confirm Email Address")
        token_input = st.text_input("Paste Access Token (from URL or Email)")
        new_pass = st.text_input("New Password", type="password")
        
        if st.form_submit_button("Change Password", type="primary"):
            success, msg = auth_engine.reset_password_with_token(email_confirm, token_input, new_pass)
            if success:
                st.success("Password Changed! Redirecting to Login...")
                st.query_params.clear()
                time.sleep(2)
                st.rerun()
            else:
                st.error(msg)