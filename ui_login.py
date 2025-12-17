import streamlit as st
import time

# --- IMPORTS ---
try: import auth_engine
except ImportError: auth_engine = None
try: import database
except ImportError: database = None

def render_login_page():
    """
    Renders the Login, Signup, and Password Recovery interface.
    """
    st.markdown("""
    <style>
    .stTextInput input { font-size: 16px; padding: 10px; }
    div[data-testid="stForm"] { border: 1px solid #ddd; padding: 20px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
    </style>
    """, unsafe_allow_html=True)

    # --- 1. HANDLE RECOVERY LINK (Redirect from Email) ---
    # This detects if the user clicked a "Reset Password" link in their email
    params = st.query_params
    if params.get("type") == "recovery":
        st.info("🔓 Verified! Please set your new password below.")
        
        with st.form("recovery_form"):
            new_pass = st.text_input("New Password", type="password")
            confirm_pass = st.text_input("Confirm New Password", type="password")
            
            if st.form_submit_button("Update Password", type="primary"):
                if new_pass != confirm_pass:
                    st.error("Passwords do not match.")
                elif len(new_pass) < 6:
                    st.error("Password must be at least 6 characters.")
                else:
                    if auth_engine:
                        success, msg = auth_engine.update_user_password(new_pass)
                        if success:
                            st.success("✅ Password Updated! Please log in.")
                            # Clear params to exit recovery mode
                            st.query_params.clear()
                            time.sleep(2)
                            st.rerun()
                        else:
                            st.error(f"Update failed: {msg}")
        
        if st.button("⬅️ Back to Login"):
            st.query_params.clear()
            st.rerun()
        return

    # --- 2. STANDARD LOGIN/SIGNUP UI ---
    st.markdown("## 🔐 Access VerbaPost")
    
    tab_login, tab_signup, tab_forgot = st.tabs(["Sign In", "New Account", "Forgot Password"])

    # --- TAB A: SIGN IN ---
    with tab_login:
        with st.form("login_form"):
            email = st.text_input("Email Address")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Sign In", type="primary")
            
            if submit:
                if auth_engine:
                    user, error = auth_engine.sign_in(email, password)
                    if user:
                        st.success(f"Welcome back, {email}!")
                        st.session_state.authenticated = True
                        st.session_state.user_email = email
                        st.session_state.app_mode = "store"
                        st.rerun()
                    else:
                        st.error(f"Login failed: {error}")

    # --- TAB B: SIGN UP ---
    with tab_signup:
        with st.form("signup_form"):
            new_email = st.text_input("Email Address")
            new_pass = st.text_input("Create Password", type="password")
            full_name = st.text_input("Full Name")
            
            st.markdown("---")
            st.caption("Return Address (For your letters)")
            addr = st.text_input("Street Address")
            city = st.text_input("City")
            c1, c2 = st.columns(2)
            state = c1.text_input("State")
            zip_code = c2.text_input("Zip")

            if st.form_submit_button("Create Account"):
                if auth_engine:
                    user, error = auth_engine.sign_up(new_email, new_pass, data={"full_name": full_name})
                    if user:
                        # Create DB Profile immediately
                        if database:
                            database.create_user(new_email, full_name)
                            # Update profile with address
                            with database.get_db_session() as db:
                                p = db.query(database.UserProfile).filter(database.UserProfile.email == new_email).first()
                                if p:
                                    p.address_line1 = addr
                                    p.address_city = city
                                    p.address_state = state
                                    p.address_zip = zip_code
                                    db.commit()
                        
                        st.success("✅ Account created! You are now logged in.")
                        st.session_state.authenticated = True
                        st.session_state.user_email = new_email
                        st.session_state.app_mode = "store"
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"Signup failed: {error}")

    # --- TAB C: FORGOT PASSWORD (FIXED) ---
    with tab_forgot:
        st.write("Enter your email to receive a password reset link.")
        
        # Step 1: Request Link
        with st.form("reset_request"):
            reset_email = st.text_input("Email Address")
            if st.form_submit_button("Send Reset Link"):
                if auth_engine:
                    success, msg = auth_engine.send_password_reset(reset_email)
                    if success:
                        st.success("✅ Check your email! Click the link inside to reset your password.")
                    else:
                        st.error(f"Error: {msg}")

        st.divider()
        st.markdown("#### 🔢 Have a code?")
        
        # Step 2: Enter OTP (Optional fallback)
        with st.form("otp_verification"):
            otp_email = st.text_input("Email")
            otp_code = st.text_input("6-Digit Code")
            if st.form_submit_button("Verify Code"):
                if auth_engine:
                    session, error = auth_engine.verify_otp(otp_email, otp_code)
                    if session:
                        st.success("✅ Code Verified! Redirecting...")
                        # Set a flag to show the password update UI on rerun
                        st.query_params["type"] = "recovery" 
                        st.rerun()
                    else:
                        st.error(f"Invalid Code: {error}")