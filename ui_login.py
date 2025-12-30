import streamlit as st
import time

# --- IMPORTS ---
try: import auth_engine
except ImportError: auth_engine = None
try: import database
except ImportError: database = None
try: import mailer
except ImportError: mailer = None

def render_login_page():
    """
    Renders the Login, Signup, and Password Recovery interface.
    Includes Address Validation on Signup to ensure return addresses are valid.
    """
    st.markdown("""
    <style>
    .stTextInput input { font-size: 16px; padding: 10px; }
    div[data-testid="stForm"] { border: 1px solid #ddd; padding: 20px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
    .auth-explanation { background-color: #f0f9ff; border-left: 4px solid #0ea5e9; padding: 10px; font-size: 0.9rem; color: #0c4a6e; margin-bottom: 15px; }
    </style>
    """, unsafe_allow_html=True)

    # --- 1. HANDLE RECOVERY LINK (Redirect from Email) ---
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
    
    # CHANGED: "New Account" is now first, making it the default tab
    tab_signup, tab_login, tab_forgot = st.tabs(["New Account", "Sign In", "Forgot Password"])

    # --- TAB A: SIGN UP (Now Default) ---
    with tab_signup:
        st.markdown("""
        <div class="auth-explanation">
        <b>Why do we need your address?</b><br>
        VerbaPost mails physical letters for you. We need a valid <b>Return Address</b> to ensure your mail is accepted by the USPS and can be returned to you if undeliverable.
        </div>
        """, unsafe_allow_html=True)

        with st.form("signup_form"):
            new_email = st.text_input("Email Address")
            new_pass = st.text_input("Create Password", type="password")
            full_name = st.text_input("Full Name")
            
            st.markdown("---")
            st.caption("Mailing & Config")
            
            # New Fields
            c_tz, c_country = st.columns(2)
            timezone = c_tz.selectbox("Timezone", ["US/Eastern", "US/Central", "US/Mountain", "US/Pacific", "UTC"], index=1)
            country = c_country.selectbox("Country", ["US", "CA", "UK"], index=0)

            addr = st.text_input("Street Address")
            city = st.text_input("City")
            c1, c2 = st.columns(2)
            state = c1.text_input("State")
            zip_code = c2.text_input("Zip")

            if st.form_submit_button("Create Account"):
                # 1. Validation Step
                if not addr or not city or not state or not zip_code:
                    st.error("Please complete your full address.")
                else:
                    # Validate with PostGrid BEFORE creating auth user
                    is_valid = False
                    details = {}
                    
                    if mailer:
                        with st.spinner("Verifying Address..."):
                            address_payload = {
                                "street": addr, 
                                "city": city, 
                                "state": state, 
                                "zip": zip_code, 
                                "country": country
                            }
                            is_valid, details = mailer.validate_address(address_payload)
                    else:
                        # Fallback if mailer engine missing (dev mode)
                        is_valid = True 

                    if not is_valid:
                        # --- FIX: SAFEGUARD AGAINST ATTRIBUTE ERROR ---
                        error_msg = "Unknown Error"
                        if isinstance(details, dict):
                            error_msg = details.get('error', 'Unknown Error')
                        elif isinstance(details, str):
                            error_msg = details
                        elif details is None:
                            error_msg = "Address validation service unavailable."
                        
                        st.error(f"❌ Invalid Address: {error_msg}")
                        st.warning("Please double-check your street, city, and zip.")
                    else:
                        # 2. Create User
                        if auth_engine:
                            user, error = auth_engine.sign_up(new_email, new_pass, data={"full_name": full_name})
                            if user:
                                if database:
                                    database.create_user(new_email, full_name)
                                    # Update Profile with Validated Address & Timezone
                                    with database.get_db_session() as db:
                                        p = db.query(database.UserProfile).filter(database.UserProfile.email == new_email).first()
                                        if p:
                                            p.address_line1 = addr
                                            p.address_city = city
                                            p.address_state = state
                                            p.address_zip = zip_code
                                            p.country = country
                                            p.timezone = timezone
                                            db.commit()
                                
                                # --- AUDIT LOG (NEW) ---
                                if hasattr(database, "save_audit_log"):
                                    try:
                                        database.save_audit_log({
                                            "user_email": new_email,
                                            "event_type": "USER_SIGNUP",
                                            "description": "New Account Created & Address Verified"
                                        })
                                    except Exception: pass
                                # -----------------------

                                st.success("✅ Account created! Address Verified.")
                                st.session_state.authenticated = True
                                st.session_state.user_email = new_email
                                
                                # --- ROUTING FIX ---
                                target = st.session_state.get("redirect_to", "main")
                                if target == "heirloom":
                                    st.session_state.app_mode = "heirloom"
                                    st.query_params["view"] = "heirloom"
                                else:
                                    st.session_state.app_mode = "main"

                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error(f"Signup failed: {error}")

    # --- TAB B: SIGN IN ---
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
                        
                        # --- AUDIT LOG ---
                        if hasattr(database, "save_audit_log"):
                            try:
                                database.save_audit_log({
                                    "user_email": email,
                                    "event_type": "USER_LOGIN",
                                    "description": "Successful Login via Auth Engine"
                                })
                            except Exception: pass
                        # -----------------------

                        # --- ROUTING FIX ---
                        target = st.session_state.get("redirect_to", "main")
                        
                        if target == "heirloom":
                            st.session_state.app_mode = "heirloom"
                            st.query_params["view"] = "heirloom"
                        else:
                            st.session_state.app_mode = "main"
                        
                        st.rerun()
                    else:
                        st.error(f"Login failed: {error}")

    # --- TAB C: FORGOT PASSWORD ---
    with tab_forgot:
        st.write("Enter your email to receive a password reset link.")
        
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
        
        with st.form("otp_verification"):
            otp_email = st.text_input("Email")
            otp_code = st.text_input("6-Digit Code")
            if st.form_submit_button("Verify Code"):
                if auth_engine:
                    session, error = auth_engine.verify_otp(otp_email, otp_code)
                    if session:
                        st.success("✅ Code Verified! Redirecting...")
                        st.query_params["type"] = "recovery" 
                        st.rerun()
                    else:
                        st.error(f"Invalid Code: {error}")
    return ""