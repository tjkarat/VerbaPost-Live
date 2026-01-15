import streamlit as st
import time
import logging

# --- LOGGING SETUP ---
logger = logging.getLogger(__name__)

def render_login_page():
    """
    Renders the Login, Signup, and Password Recovery interface.
    Features: "Shake" Animation on Error, Visual Progress Tracker, and Robust Routing.
    """
    
    # --- 1. LAZY IMPORT SYSTEM MODULES ---
    try:
        import auth_engine
        import database
        import mailer
        import secrets_manager
        import audit_engine 
    except ImportError as e:
        st.error(f"System Module Error: {e}")
        return

    # --- 2. DETECT USER INTENT ---
    params = st.query_params
    url_advisor_intent = params.get("role") == "advisor"
    
    # Initialize Error State for Shake Animation
    if "login_shake" not in st.session_state:
        st.session_state.login_shake = False

    # --- 3. PREMIUM CSS STYLING (Restored) ---
    st.markdown("""
    <style>
    /* SHAKE ANIMATION */
    @keyframes shake {
        0% { transform: translate(1px, 1px) rotate(0deg); }
        10% { transform: translate(-1px, -2px) rotate(-1deg); }
        20% { transform: translate(-3px, 0px) rotate(1deg); }
        30% { transform: translate(3px, 2px) rotate(0deg); }
        40% { transform: translate(1px, -1px) rotate(1deg); }
        50% { transform: translate(-1px, 2px) rotate(-1deg); }
        60% { transform: translate(-3px, 1px) rotate(0deg); }
        70% { transform: translate(3px, 1px) rotate(-1deg); }
        80% { transform: translate(-1px, -1px) rotate(1deg); }
        90% { transform: translate(1px, 2px) rotate(0deg); }
        100% { transform: translate(1px, -2px) rotate(-1deg); }
    }
    
    .shake-box {
        animation: shake 0.5s;
        animation-iteration-count: 1;
        border: 2px solid #ef4444 !important; /* Red Border on Error */
    }

    /* Global Input Styling */
    .stTextInput input { 
        font-size: 16px; 
        padding: 12px; 
        border-radius: 8px;
    }
    
    /* Form Container Styling */
    div[data-testid="stForm"] { 
        border: 1px solid #e5e7eb; 
        padding: 35px; 
        border-radius: 16px; 
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06); 
        background-color: #ffffff;
    }

    /* Progress Tracker (Stepper) */
    .stepper-wrapper {
        display: flex;
        justify-content: space-between;
        margin-bottom: 25px;
        font-family: sans-serif;
    }
    .stepper-item {
        position: relative;
        display: flex;
        flex-direction: column;
        align-items: center;
        flex: 1;
    }
    .stepper-item::before {
        position: absolute;
        content: "";
        border-bottom: 2px solid #e5e7eb;
        width: 100%;
        top: 15px;
        left: -50%;
        z-index: 0;
    }
    .stepper-item::after {
        position: absolute;
        content: "";
        border-bottom: 2px solid #e5e7eb;
        width: 100%;
        top: 15px;
        left: 50%;
        z-index: 0;
    }
    .stepper-item .step-counter {
        position: relative;
        z-index: 2;
        display: flex;
        justify-content: center;
        align-items: center;
        width: 30px;
        height: 30px;
        border-radius: 50%;
        background: #f3f4f6;
        color: #6b7280;
        font-weight: bold;
        margin-bottom: 6px;
    }
    .stepper-item.active .step-counter {
        background-color: #0f172a;
        color: #fff;
    }
    .stepper-item.completed .step-counter {
        background-color: #22c55e;
        color: #fff;
    }
    .stepper-item:first-child::before { content: none; }
    .stepper-item:last-child::after { content: none; }
    
    /* Advisor Badge */
    .advisor-badge { 
        background-color: #fffbeb; 
        border: 1px solid #fcd34d; 
        color: #92400e; 
        padding: 10px; 
        border-radius: 8px; 
        font-weight: 600; 
        text-align: center; 
        margin-bottom: 20px; 
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 8px;
    }

    /* Google Button */
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
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    }
    .google-btn:hover {
        background: #f8f9fa;
        border-color: #dadce0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
    </style>
    """, unsafe_allow_html=True)

    # Inject Shake Class if Error Triggered
    if st.session_state.login_shake:
        st.markdown("""
        <script>
        const forms = window.parent.document.querySelectorAll('div[data-testid="stForm"]');
        forms.forEach(form => {
            form.classList.add('shake-box');
            setTimeout(() => { form.classList.remove('shake-box'); }, 500);
        });
        </script>
        """, unsafe_allow_html=True)
        st.session_state.login_shake = False # Reset

    # --- 4. RECOVERY LOGIC ---
    if params.get("type") == "recovery":
        st.info("🔓 Identity Verified! Please set your new password below.")
        with st.form("recovery_form"):
            st.subheader("Reset Password")
            new_pass = st.text_input("New Password", type="password")
            confirm_pass = st.text_input("Confirm New Password", type="password")
            if st.form_submit_button("Update Password", type="primary"):
                if new_pass != confirm_pass:
                    st.session_state.login_shake = True
                    st.error("Passwords do not match.")
                    st.rerun()
                elif len(new_pass) < 6:
                    st.session_state.login_shake = True
                    st.error("Password must be at least 6 characters.")
                    st.rerun()
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
    
    # 🔴 RESTORED WARNING
    st.error("🛑 **STOP: NEW USERS READ THIS FIRST**")
    st.markdown("""
    **Do NOT use "Sign in with Google" unless you have already created an account below.**
    
    You must create an account manually first to set your **Role (Advisor vs Family)** and **Firm Name**. 
    *If you skip this, your account will be misconfigured.*
    """)

    tab_signup, tab_login, tab_forgot = st.tabs(["✨ Create Account", "🔑 Sign In", "❓ Help"])

    # ==========================================
    # TAB A: NEW ACCOUNT CREATION (With Stepper)
    # ==========================================
    with tab_signup:
        
        # VISUAL PROGRESS TRACKER
        st.markdown("""
        <div class="stepper-wrapper">
          <div class="stepper-item completed">
            <div class="step-counter">1</div>
            <div class="step-name">Role</div>
          </div>
          <div class="stepper-item active">
            <div class="step-counter">2</div>
            <div class="step-name">Profile</div>
          </div>
          <div class="stepper-item">
            <div class="step-counter">3</div>
            <div class="step-name">Verify</div>
          </div>
        </div>
        """, unsafe_allow_html=True)
        
        # 1. ROLE SELECTION
        is_advisor = st.checkbox("🏛️ I am a Financial Advisor / Estate Planner", value=url_advisor_intent)
        
        if is_advisor:
            st.markdown('<div class="advisor-badge">💼 Configuring Advisor Workspace</div>', unsafe_allow_html=True)
        else:
            st.info("ℹ️ **Family Archive:** For heirs and seniors preserving their stories.")

        st.write("### Account Details")
        
        with st.form("signup_form"):
            c1, c2 = st.columns(2)
            new_email = c1.text_input("Email Address")
            full_name = c2.text_input("Full Name")
            new_pass = st.text_input("Create Password", type="password", help="Min. 6 characters")
            
            firm_name = ""
            if is_advisor:
                st.markdown("---")
                st.markdown("**Advisor Configuration**")
                firm_name = st.text_input("Firm / Practice Name (Required)", 
                                        help="This appears on all physical letters and client portals.")

            st.markdown("---")
            st.markdown("**📍 Mailing Address**")
            
            addr = st.text_input("Street Address")
            c_city, c_state, c_zip = st.columns([2, 1, 1])
            city = c_city.text_input("City")
            state = c_state.text_input("State")
            zip_code = c_zip.text_input("Zip Code")
            
            c_tz, c_country = st.columns(2)
            timezone = c_tz.selectbox("Timezone", ["US/Central", "US/Eastern", "US/Pacific"], index=0)
            country = c_country.selectbox("Country", ["US"], index=0)

            if st.form_submit_button("Create Account", type="primary", use_container_width=True):
                if not new_email or not new_pass or not full_name:
                    st.session_state.login_shake = True
                    st.error("Missing basic fields (Email, Password, Name).")
                    st.rerun()
                elif is_advisor and not firm_name:
                    st.session_state.login_shake = True
                    st.error("⚠️ Advisor Accounts must have a Firm Name.")
                    st.rerun()
                elif not addr or not city or not zip_code:
                    st.session_state.login_shake = True
                    st.error("Please complete your mailing address.")
                    st.rerun()
                else:
                    is_valid = True
                    if mailer:
                        with st.spinner("Validating address with USPS..."):
                            payload = {"street": addr, "city": city, "state": state, "zip": zip_code}
                            valid, details = mailer.validate_address(payload)
                            if not valid:
                                logger.warning(f"Address Validation Soft-Fail: {details}")
                                st.toast(f"Address Warning: {details}", icon="⚠️")

                    if auth_engine:
                        user, error = auth_engine.sign_up(new_email, new_pass, data={"full_name": full_name})
                        
                        if user:
                            if database:
                                try:
                                    database.create_user(new_email, full_name)
                                    with database.get_db_session() as db:
                                        p = db.query(database.UserProfile).filter_by(email=new_email).first()
                                        if p:
                                            p.address_line1 = addr
                                            p.address_city = city
                                            p.address_state = state
                                            p.address_zip = zip_code
                                            p.country = country
                                            p.timezone = timezone
                                            if is_advisor:
                                                p.role = "advisor"
                                                p.advisor_firm = firm_name
                                            else:
                                                p.role = "user"
                                            db.commit()
                                    
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
                            st.session_state.login_shake = True
                            st.error(f"Signup Failed: {error}")
                            st.rerun()

    # ==========================================
    # TAB B: SIGN IN
    # ==========================================
    with tab_login:
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
                        
                        # ROBUST ROLE CHECK
                        mode = "heirloom"
                        if database:
                            p = database.get_user_profile(email)
                            role = str(p.get("role")).lower()
                            if role == "advisor": mode = "advisor"
                            elif role == "admin": mode = "admin"
                        
                        if audit_engine:
                            audit_engine.log_event(email, "Login Successful", metadata={"mode": mode})

                        st.session_state.app_mode = mode
                        st.rerun()
                    else:
                        st.session_state.login_shake = True
                        st.error(f"Login failed: {err}")
                        st.rerun()

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
                    else: 
                        st.session_state.login_shake = True
                        st.error(f"Error: {msg}")
                        st.rerun()