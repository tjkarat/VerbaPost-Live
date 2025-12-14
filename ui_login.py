import streamlit as st
import time

# --- ROBUST IMPORT ---
try:
    import auth_engine
except ImportError:
    auth_engine = None

def render_login():
    """
    Renders the Authentication UI (Login / Signup / Recovery).
    """
    # --- CSS STYLING ---
    st.markdown("""
    <style>
        .auth-container { max-width: 400px; margin: 0 auto; }
        .stButton button { width: 100%; border-radius: 5px; font-weight: 600; }
        .stTextInput input { border-radius: 5px; }
    </style>
    """, unsafe_allow_html=True)

    # --- PASSWORD RECOVERY FLOW ---
    if st.query_params.get("type") == "recovery":
        st.info("🔄 Password Recovery Mode")
        with st.form("recovery_form"):
            new_pwd = st.text_input("New Password", type="password")
            confirm_pwd = st.text_input("Confirm Password", type="password")
            
            if st.form_submit_button("Reset Password"):
                if new_pwd != confirm_pwd:
                    st.error("Passwords do not match.")
                elif auth_engine:
                    if auth_engine.reset_password_with_token(None, new_pwd):
                        st.success("✅ Password Updated! Please log in.")
                        time.sleep(2)
                        st.query_params.clear()
                        st.rerun()
                    else:
                        st.error("Reset failed. Token may be expired.")
        return

    # --- MAIN AUTH TABS ---
    st.markdown("## 🔐 Access VerbaPost")
    t1, t2, t3 = st.tabs(["Log In", "Create Account", "Forgot Password"])

    # --- TAB 1: LOGIN ---
    with t1:
        with st.form("login_form"):
            email = st.text_input("Email Address")
            pwd = st.text_input("Password", type="password")
            
            if st.form_submit_button("Log In", type="primary"):
                if auth_engine:
                    success, msg = auth_engine.sign_in(email, pwd)
                    if success:
                        st.success("Welcome back!")
                        time.sleep(0.5)
                        # Check where to redirect
                        if st.session_state.get("locked_tier") == "Legacy":
                            st.query_params["view"] = "legacy"
                        else:
                            st.session_state.app_mode = "store"
                            st.query_params.clear()
                        st.rerun()
                    else:
                        st.error(f"Login Failed: {msg}")
                else:
                    st.error("Auth Engine Missing")

    # --- TAB 2: SIGN UP (Restored Full Address) ---
    with t2:
        st.markdown("#### 👤 Profile Info")
        with st.form("signup_form"):
            new_email = st.text_input("Email")
            new_pwd = st.text_input("Password", type="password", help="Min 6 characters")
            full_name = st.text_input("Full Name")
            
            st.markdown("#### 📍 Return Address")
            st.caption("Required for mailing your letters.")
            
            addr1 = st.text_input("Street Address", placeholder="123 Main St")
            addr2 = st.text_input("Apt / Suite / Other", placeholder="Apt 4B")
            
            c_city, c_state, c_zip = st.columns(3)
            city = c_city.text_input("City")
            state = c_state.text_input("State")
            zip_code = c_zip.text_input("Zip")
            
            country = st.selectbox("Country", ["US", "CA", "UK", "AU"], index=0)
            
            if st.form_submit_button("Create Account"):
                # Basic Validation
                if not new_email or not new_pwd or not full_name:
                    st.warning("Please fill in Name, Email, and Password.")
                elif not addr1 or not city or not state or not zip_code:
                    st.warning("Please complete your Return Address.")
                elif auth_engine:
                    with st.spinner("Creating account..."):
                        # Call the full signature sign_up
                        success, msg = auth_engine.sign_up(
                            new_email, new_pwd, full_name,
                            addr1, addr2, city, state, zip_code, country
                        )
                        
                        if success:
                            st.success("✅ Account Created! Please check your email to confirm, then Log In.")
                        else:
                            st.error(f"Signup Error: {msg}")

    # --- TAB 3: FORGOT PASSWORD ---
    with t3:
        st.caption("Enter your email to receive a reset link.")
        reset_email = st.text_input("Email Address", key="reset_email")
        if st.button("Send Reset Link"):
            if auth_engine:
                if auth_engine.send_password_reset(reset_email):
                    st.success("Check your inbox for the reset link.")
                else:
                    st.error("Failed to send link. Please check the email.")