import streamlit as st
import time

# Robust import for Auth Engine
try: import auth_engine
except ImportError: auth_engine = None

def show_login(login_func, signup_func):
    # CSS for centering and styling
    st.markdown("""
    <style>
        .auth-container {
            max-width: 400px;
            margin: 0 auto;
            padding: 40px 20px;
            background: white;
            border-radius: 10px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            text-align: center;
        }
        .auth-header { color: #1e3c72; font-weight: 700; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

    # Initialize sub-view state if not present
    if "auth_view" not in st.session_state:
        st.session_state.auth_view = "login"

    # --- VIEW: FORGOT PASSWORD ---
    if st.session_state.auth_view == "forgot":
        st.markdown("<div class='auth-container'><h2 class='auth-header'>↺ Reset Password</h2>", unsafe_allow_html=True)
        st.info("Enter your email address. We will send you a link to reset your password.")
        
        email = st.text_input("Email Address", key="reset_email")
        
        if st.button("📩 Send Reset Link", type="primary", use_container_width=True):
            if auth_engine:
                with st.spinner("Sending..."):
                    success, msg = auth_engine.send_password_reset(email)
                    if success:
                        st.success("✅ Check your email! A reset link has been sent.")
                    else:
                        st.error(f"❌ {msg}")
            else:
                st.error("Auth Engine missing.")

        if st.button("⬅️ Back to Login"):
            st.session_state.auth_view = "login"
            st.rerun()
        
        st.markdown("</div>", unsafe_allow_html=True)
        return

    # --- VIEW: LOGIN & SIGNUP ---
    st.markdown("<div class='auth-container'>", unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["🔑 Log In", "📝 Sign Up"])

    # LOGIN TAB
    with tab1:
        st.markdown("<h3 class='auth-header'>Welcome Back</h3>", unsafe_allow_html=True)
        with st.form("login_form"):
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_pass")
            submit = st.form_submit_button("Log In", type="primary", use_container_width=True)
        
        if submit:
            if not email or not password:
                st.warning("Please enter both email and password.")
            else:
                with st.spinner("Verifying..."):
                    user, err = login_func(email, password)
                    if user:
                        st.success("✅ Success!")
                        st.session_state.user_email = user.user.email
                        st.session_state.app_mode = "store"
                        st.rerun()
                    else:
                        st.error(f"❌ {err}")

        # "Forgot Password" Button - Now functional
        if st.button("❓ Forgot Password?", type="secondary", use_container_width=True):
            st.session_state.auth_view = "forgot"
            st.rerun()

    # SIGNUP TAB
    with tab2:
        st.markdown("<h3 class='auth-header'>Create Account</h3>", unsafe_allow_html=True)
        with st.form("signup_form"):
            new_email = st.text_input("Email", key="signup_email")
            new_pass = st.text_input("Password", type="password", help="Min 8 chars, 1 uppercase, 1 lowercase, 1 number", key="signup_pass")
            full_name = st.text_input("Full Name")
            
            st.caption("Address (Required for Mailing)")
            street = st.text_input("Street Address")
            street2 = st.text_input("Apt / Suite")
            c1, c2, c3 = st.columns([2, 1, 1])
            city = c1.text_input("City")
            state = c2.text_input("State")
            zip_code = c3.text_input("Zip")
            
            signup_submit = st.form_submit_button("Create Account", type="primary", use_container_width=True)

        if signup_submit:
            if not all([new_email, new_pass, full_name, street, city, state, zip_code]):
                st.error("Please fill in all required fields.")
            else:
                with st.spinner("Creating account..."):
                    res, err = signup_func(new_email, new_pass, full_name, street, street2, city, state, zip_code, "US", "English")
                    if res:
                        st.success("✅ Account Created! Please check your email to confirm, then Log In.")
                        time.sleep(2)
                        st.session_state.auth_view = "login"
                        st.rerun()
                    else:
                        st.error(f"❌ {err}")

    st.markdown("</div>", unsafe_allow_html=True)