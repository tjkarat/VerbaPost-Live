import streamlit as st
import time
import logging

# --- LOGGING SETUP ---
logger = logging.getLogger(__name__)

def render_login_page():
    """
    Renders the Login, Signup, and Password Recovery interface.
    HEAVILY STYLED for visual hierarchy and "New User" awareness.
    """
    
    # --- 1. LAZY IMPORT SYSTEM MODULES ---
    try:
        import auth_engine
        import database
        import mailer
        import secrets_manager
        import audit_engine # <--- NEW IMPORT
    except ImportError as e:
        st.error(f"System Module Error: {e}")
        return

    # --- 2. DETECT USER INTENT ---
    # Auto-detect from URL, but allow manual override later
    params = st.query_params
    url_advisor_intent = params.get("role") == "advisor"

    # --- 3. PAGE STYLING (Restored "Bulk") ---
    st.markdown("""
    <style>
    /* Global Input Styling */
    .stTextInput input { 
        font-size: 16px; 
        padding: 12px; 
    }
    
    /* Form Container Styling */
    div[data-testid="stForm"] { 
        border: 1px solid #d1d5db; 
        padding: 30px; 
        border-radius: 12px; 
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1); 
        background-color: #ffffff;
    }
    
    /* The "New User" Warning Box */
    .new-user-alert {
        background-color: #fef2f2;
        border: 2px solid #ef4444;
        color: #991b1b;
        padding: 15px;
        border-radius: 8px;
        font-weight: bold;
        text-align: center;
        margin-bottom: 20px;
    }

    /* Advisor Badge */
    .advisor-badge { 
        background-color: #fffbeb; 
        border: 2px solid #f59e0b; 
        color: #92400e; 
        padding: 12px; 
        border-radius: 6px; 
        font-weight: 700; 
        text-align: center; 
        margin-bottom: 20px; 
        font-size: 1.1rem;
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
        text-decoration: none;
        transition: all 0.2s ease;
        margin-bottom: 20px;
        gap: 10px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    }
    .google-btn:hover {
        background: #f8f9fa;
        border-color: #dadce0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        transform: translateY(-1px);
    }
    </style>
    """, unsafe_allow_html=True)

    # --- 4. RECOVERY LOGIC (Preserved) ---
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
                            st.success("✅ Password Updated! Redirecting...")
                            st.query_params.clear()
                            time.sleep(2)
                            st.rerun()
                        else:
                            st.error(f"Update failed: {msg}")
        if st.button("⬅️ Cancel"):
            st.query_params.clear()
            st.rerun()
        return

    # --- 5. MAIN HEADER ---
    st.title("🔐 Access VerbaPost")
    
    # 🛑 THE LOUD WARNING 🛑
    st.error("🛑 **STOP: NEW USERS READ THIS FIRST**")
    st.markdown("""
    **Do NOT use "Sign in with Google" unless you have already created an account below.**
    
    You must create an account manually first to set your **Role (Advisor vs Family)** and **Firm Name**. 
    *If you skip this, your account will be misconfigured.*
    """)

    tab_signup, tab_login, tab_forgot = st.tabs(["✨ Create Account (Start Here)", "🔑 Sign In", "❓ Forgot Password"])

    # ==========================================
    # TAB A: NEW ACCOUNT CREATION
    # ==========================================
    with tab_signup:
        
        # 1. MANUAL ROLE SELECTION (The Fix for Missing "Firm Name")
        st.write("### Step 1: Select Account Type")
        is_advisor = st.checkbox("🏛️ I am a Financial Advisor / Estate Planner", value=url_advisor_intent)
        
        if is_advisor:
            st.markdown("""
            <div class="advisor-badge">
                Creating Professional Advisor Account
            </div>
            """, unsafe_allow_html=True)
            st.info("ℹ️ This account type allows you to purchase credits and authorize client gifts.")
        else:
            st.info("ℹ️ **Family Archive:** For heirs and seniors preserving their stories.")

        st.write("### Step 2: Account Details")
        
        with st.form("signup_form"):
            c1, c2 = st.columns(2)
            new_email = c1.text_input("Email Address")
            full_name = c2.text_input("Full Name")
            new_pass = st.text_input("Create Password", type="password", help="Min. 6 characters")
            
            # FIRM NAME (Conditional)
            firm_name = ""
            if is_advisor:
                st.markdown("---")
                st.markdown("**Advisor Configuration**")
                firm_name = st.text_input("Firm / Practice Name (Required)", 
                                        help="This appears on all physical letters and client portals.")

            st.markdown("---")
            st.markdown("**📍 Mailing Address** (Required for USPS Validation)")
            
            addr = st.text_input("Street Address")
            c_city, c_state, c_zip = st.columns([2, 1, 1])
            city = c_city.text_input("City")
            state = c_state.text_input("State")
            zip_code = c_zip.text_input("Zip Code")
            
            c_tz, c_country = st.columns(2)
            timezone = c_tz.selectbox("Timezone", ["US/Central", "US/Eastern", "US/Pacific"], index=0)
            country = c_country.selectbox("Country", ["US"], index=0)

            if st.form_submit_button("Create Account", type="primary", use_container_width=True):
                # Validation Logic
                if not new_email or not new_pass or not full_name:
                    st.error("Missing basic fields (Email, Password, Name).")
                elif is_advisor and not firm_name:
                    st.error("⚠️ Advisor Accounts must have a Firm Name.")
                elif not addr or not city or not zip_code:
                    st.error("Please complete your mailing address.")
                else:
                    # Address Check (Soft Fail to prevent 404 blocking)
                    is_valid = True
                    if mailer:
                        with st.spinner("Validating address with USPS..."):
                            payload = {"street": addr, "city": city, "state": state, "zip": zip_code}
                            valid, details = mailer.validate_address(payload)
                            if not valid:
                                # Log but allow
                                logger.warning(f"Address Validation Soft-Fail: {details}")
                                st.toast(f"Address Warning: {details}", icon="⚠️")

                    # Create Auth User
                    if auth_engine:
                        user, error = auth_engine.sign_up(new_email, new_pass, data={"full_name": full_name})
                        
                        if user:
                            if database:
                                try:
                                    # Create Base User
                                    database.create_user(new_email, full_name)
                                    
                                    # Update Profile
                                    with database.get_db_session() as db:
                                        p = db.query(database.UserProfile).filter_by(email=new_email).first()
                                        if p:
                                            p.address_line1 = addr
                                            p.address_city = city
                                            p.address_state = state
                                            p.address_zip = zip_code
                                            p.country = country
                                            p.timezone = timezone
                                            
                                            # SET ROLE EXPLICITLY
                                            if is_advisor:
                                                p.role = "advisor"
                                                p.advisor_firm = firm_name
                                            else:
                                                p.role = "user"
                                            
                                            db.commit()
                                    
                                    # AUDIT LOG
                                    if audit_engine:
                                        audit_engine.log_event(new_email, "Account Created", metadata={"role": "advisor" if is_advisor else "user"})
                                    
                                    st.success("✅ Account Created! Logging you in...")
                                    st.session_state.authenticated = True
                                    st.session_state.user_email = new_email
                                    st.session_state.app_mode = "advisor" if is_advisor else "heirloom"
                                    time.sleep(1)
                                    st.rerun()

                                except Exception as e:
                                    st.error(f"Database Error: {e}")
                        else:
                            st.error(f"Signup Failed: {error}")

    # ==========================================
    # TAB B: SIGN IN
    # ==========================================
    with tab_login:
        # GOOGLE BUTTON
        if auth_engine:
            base_url = secrets_manager.get_secret("general.BASE_URL") or "http://localhost:8501"
            google_url = auth_engine.get_oauth_url("google", redirect_to=base_url)
            if google_url:
                st.markdown(f'<a href="{google_url}" class="google-btn">🇬 Sign In with Google (Returning Users)</a>', unsafe_allow_html=True)

        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            if st.form_submit_button("Sign In", type="primary", use_container_width=True):
                if auth_engine:
                    user, err = auth_engine.sign_in(email, password)
                    if user:
                        st.session_state.authenticated = True
                        st.session_state.user_email = email
                        
                        # Route based on DB Role
                        mode = "heirloom"
                        if database:
                            p = database.get_user_profile(email)
                            if p.get("role") == "advisor": mode = "advisor"
                            elif p.get("role") == "admin": mode = "admin"
                        
                        # AUDIT LOG
                        if audit_engine:
                            audit_engine.log_event(email, "Login Successful", metadata={"mode": mode})

                        st.session_state.app_mode = mode
                        st.rerun()
                    else:
                        st.error(f"Login failed: {err}")

    # ==========================================
    # TAB C: FORGOT PASSWORD
    # ==========================================
    with tab_forgot:
        st.write("Enter your email to receive a password reset link.")
        with st.form("reset_request"):
            reset_email = st.text_input("Email Address")
            if st.form_submit_button("Send Reset Link"):
                if auth_engine:
                    success, msg = auth_engine.send_password_reset(reset_email)
                    if success: st.success("✅ Check your email!")
                    else: st.error(f"Error: {msg}")