import streamlit as st
import time
import logging

# --- LOGGING SETUP ---
logger = logging.getLogger(__name__)

def render_login_page():
    """
    Renders the Login, Signup, and Password Recovery interface.
    Includes Smart Routing for Advisors via URL params (?role=advisor).
    """
    
    # --- 1. LAZY IMPORT SYSTEM MODULES ---
    # We import here to avoid circular dependency issues with main.py
    try:
        import auth_engine
        import database
        import mailer
        import secrets_manager 
    except ImportError as e:
        st.error(f"System Module Error: {e}")
        return

    # --- 2. DETECT USER INTENT ---
    # Check if user came from "Start Retaining Heirs" link (e.g. ?role=advisor)
    params = st.query_params
    is_advisor_intent = params.get("role") == "advisor"

    # --- 3. PAGE STYLING ---
    st.markdown("""
    <style>
    /* Global Input Styling */
    .stTextInput input { 
        font-size: 16px; 
        padding: 10px; 
    }
    
    /* Form Container Styling */
    div[data-testid="stForm"] { 
        border: 1px solid #e5e7eb; 
        padding: 30px; 
        border-radius: 12px; 
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); 
        background-color: #ffffff;
    }
    
    /* Explanation Box */
    .auth-explanation { 
        background-color: #f0f9ff; 
        border-left: 4px solid #0ea5e9; 
        padding: 15px; 
        font-size: 0.95rem; 
        color: #0c4a6e; 
        margin-bottom: 25px;
        line-height: 1.5;
    }
    
    /* Advisor Badge */
    .advisor-badge { 
        background-color: #fffbeb; 
        border: 1px solid #f59e0b; 
        color: #92400e; 
        padding: 10px; 
        border-radius: 6px; 
        font-weight: 600; 
        text-align: center; 
        margin-bottom: 20px; 
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 8px;
    }

    /* Google Button Styling */
    .google-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 100%;
        padding: 12px;
        background: white;
        border: 1px solid #dadce0;
        border-radius: 6px;
        color: #3c4043;
        font-size: 15px;
        font-weight: 500;
        text-align: center;
        text-decoration: none;
        transition: all 0.2s ease;
        margin-bottom: 20px;
        gap: 10px;
    }
    .google-btn:hover {
        background: #f8f9fa;
        border-color: #dadce0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        transform: translateY(-1px);
    }
    </style>
    """, unsafe_allow_html=True)

    # --- 4. HANDLE PASSWORD RECOVERY FLOW ---
    # This triggers when a user clicks a reset link from their email
    if params.get("type") == "recovery":
        st.info("🔓 Identity Verified! Please set your new password below.")
        
        with st.form("recovery_form"):
            st.subheader("Reset Password")
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
                            st.balloons()
                            st.success("✅ Password Updated! Redirecting to login...")
                            st.query_params.clear()
                            time.sleep(2)
                            st.rerun()
                        else:
                            st.error(f"Update failed: {msg}")
        
        if st.button("⬅️ Cancel and Return to Login"):
            st.query_params.clear()
            st.rerun()
        return

    # --- 5. MAIN AUTHENTICATION INTERFACE ---
    st.markdown("## 🔐 Access VerbaPost")
    
    # Critical Warning for New Users
    st.info("⚠️ **First Time Here?** You MUST create an account below before using Google Sign-In.")

    # Tabs for separation of concerns
    tab_signup, tab_login, tab_forgot = st.tabs(["✨ New Account", "🔑 Sign In", "❓ Forgot Password"])

    # ==========================================
    # TAB A: NEW ACCOUNT CREATION
    # ==========================================
    with tab_signup:
        # Dynamic Header based on Role
        if is_advisor_intent:
            st.markdown("""
            <div class="advisor-badge">
                <span>🎓</span> Creating Professional Advisor Account
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="auth-explanation">
            <b>Start Here:</b> Create your account to enable secure mailing.<br>
            We need a valid <b>Return Address</b> to ensure your physical letters are accepted by the USPS.
            </div>
            """, unsafe_allow_html=True)

        with st.form("signup_form"):
            c_email, c_name = st.columns(2)
            new_email = c_email.text_input("Email Address")
            full_name = c_name.text_input("Full Name")
            
            new_pass = st.text_input("Create Password", type="password", help="Min. 6 characters")
            
            # Advisor-Specific Field
            firm_name = ""
            if is_advisor_intent:
                firm_name = st.text_input("Firm / Practice Name (Required)", 
                                        help="This will appear on your client's letters and portals.")

            st.markdown("---")
            st.caption("📍 Mailing Address (Required for Fulfillment)")
            
            addr = st.text_input("Street Address")
            c_city, c_state, c_zip = st.columns([2, 1, 1])
            city = c_city.text_input("City")
            state = c_state.text_input("State")
            zip_code = c_zip.text_input("Zip Code")
            
            c_tz, c_country = st.columns(2)
            timezone = c_tz.selectbox("Timezone", 
                ["US/Eastern", "US/Central", "US/Mountain", "US/Pacific", "UTC"], 
                index=1)
            country = c_country.selectbox("Country", ["US", "CA", "UK"], index=0)

            submitted = st.form_submit_button("Create Account", type="primary", use_container_width=True)

            if submitted:
                # 1. Input Validation
                if not new_email or not new_pass:
                    st.error("Email and password are required.")
                elif not full_name:
                    st.error("Full Name is required.")
                elif is_advisor_intent and not firm_name:
                    st.error("Firm Name is required for Advisor accounts.")
                elif not addr or not city or not state or not zip_code:
                    st.error("Please complete your full mailing address.")
                else:
                    # 2. Address Verification (via PostGrid/USPS)
                    is_valid = False
                    details = {}
                    
                    if mailer:
                        with st.spinner("Validating address with USPS..."):
                            address_payload = {
                                "street": addr, 
                                "city": city, 
                                "state": state, 
                                "zip": zip_code, 
                                "country": country
                            }
                            # This returns (True/False, details_dict)
                            is_valid, details = mailer.validate_address(address_payload)
                    else:
                        # Dev mode fallback
                        is_valid = True 

                    if not is_valid:
                        # Parse error details safely
                        error_msg = "Unknown Verification Error"
                        if isinstance(details, dict):
                            error_msg = details.get('error', str(details))
                        elif isinstance(details, str):
                            error_msg = details
                        
                        st.warning(f"⚠️ Address Warning: {error_msg}")
                        st.caption("We will proceed, but please verify your address in settings later.")
                    
                    # 3. Create Auth User (Supabase Auth)
                    if auth_engine:
                        user, error = auth_engine.sign_up(new_email, new_pass, data={"full_name": full_name})
                        
                        if user:
                            # 4. Create Database Profile (Public Table)
                            if database:
                                try:
                                    # Create basic user row
                                    database.create_user(new_email, full_name)
                                    
                                    # Enforce Role & Address Details
                                    with database.get_db_session() as db:
                                        p = db.query(database.UserProfile).filter(
                                            database.UserProfile.email == new_email
                                        ).first()
                                        
                                        if p:
                                            p.address_line1 = addr
                                            p.address_city = city
                                            p.address_state = state
                                            p.address_zip = zip_code
                                            p.country = country
                                            p.timezone = timezone
                                            
                                            # Apply Advisor Role if needed
                                            if is_advisor_intent:
                                                p.role = "advisor"
                                                p.advisor_firm = firm_name
                                            
                                            db.commit()
                                            
                                    st.success("✅ Account created successfully!")
                                    
                                    # 5. Set Session & Route
                                    st.session_state.authenticated = True
                                    st.session_state.user_email = new_email
                                    
                                    if is_advisor_intent:
                                        st.session_state.app_mode = "advisor"
                                    else:
                                        st.session_state.app_mode = "heirloom"
                                        
                                    time.sleep(1)
                                    st.rerun()
                                    
                                except Exception as db_err:
                                    st.error(f"Database Profile Error: {db_err}")
                        else:
                            st.error(f"Signup Failed: {error}")

    # ==========================================
    # TAB B: SIGN IN (RETURNING USERS)
    # ==========================================
    with tab_login:
        
        # --- GOOGLE OAUTH (Only shown here) ---
        if auth_engine:
            base_url = secrets_manager.get_secret("general.BASE_URL") or "http://localhost:8501"
            google_url = auth_engine.get_oauth_url("google", redirect_to=base_url)
            
            if google_url:
                st.markdown(
                    f'<a href="{google_url}" class="google-btn">🇬 Sign In with Google (Returning Users)</a>',
                    unsafe_allow_html=True
                )
                st.markdown('<div style="text-align: center; color: #666; font-size: 0.8rem; margin: 15px 0;">— OR —</div>', unsafe_allow_html=True)
            else:
                st.warning("⚠️ Google Sign-In config missing.")

        # --- EMAIL LOGIN ---
        with st.form("login_form"):
            email = st.text_input("Email Address")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Sign In", type="primary", use_container_width=True)
            
            if submit:
                if not email or not password:
                    st.error("Please enter both email and password.")
                elif auth_engine:
                    user, error = auth_engine.sign_in(email, password)
                    
                    if user:
                        st.success(f"Welcome back!")
                        st.session_state.authenticated = True
                        st.session_state.user_email = email
                        
                        # --- SMART ROUTING LOGIC ---
                        # Determine where to send them based on their Role
                        target_mode = "heirloom" # Default fallback
                        
                        if database:
                            profile = database.get_user_profile(email)
                            if profile:
                                role = profile.get("role", "user")
                                if role == "advisor": 
                                    target_mode = "advisor"
                                elif role == "admin":
                                    target_mode = "admin"
                        
                        st.session_state.app_mode = target_mode
                        st.rerun()
                    else:
                        st.error(f"Login failed: {error}")

    # ==========================================
    # TAB C: FORGOT PASSWORD
    # ==========================================
    with tab_forgot:
        st.write("Enter your email to receive a password reset link.")
        
        # Request Reset Link
        with st.form("reset_request"):
            reset_email = st.text_input("Email Address")
            if st.form_submit_button("Send Reset Link"):
                if not reset_email:
                    st.error("Please enter your email address.")
                elif auth_engine:
                    success, msg = auth_engine.send_password_reset(reset_email)
                    if success:
                        st.success("✅ Check your email for reset instructions!")
                    else:
                        st.error(f"Error: {msg}")

        st.divider()
        st.markdown("#### 📢 Have a verification code?")
        st.caption("If you received a 6-digit code via email, enter it here.")
        
        # Verify OTP (Alternative Flow)
        with st.form("otp_verification"):
            c_otp_email, c_otp_code = st.columns([2, 1])
            otp_email = c_otp_email.text_input("Email")
            otp_code = c_otp_code.text_input("6-Digit Code")
            
            if st.form_submit_button("Verify Code"):
                if not otp_email or not otp_code:
                    st.error("Please enter both email and code.")
                elif auth_engine:
                    session, error = auth_engine.verify_otp(otp_email, otp_code)
                    if session:
                        st.success("✅ Code Verified!")
                        st.query_params["type"] = "recovery" 
                        st.rerun()
                    else:
                        st.error(f"Invalid Code: {error}")