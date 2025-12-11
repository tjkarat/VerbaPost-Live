import streamlit as st
import time

try: import auth_engine
except ImportError: auth_engine = None

def show_login(login_func, signup_func):
    # CSS: minimal adjustments for centering
    st.markdown("""
    <style>
        .block-container {
            padding-top: 1rem !important;
            padding-bottom: 1rem !important;
        }
    </style>
    """, unsafe_allow_html=True)

    # Initialize View State
    if "auth_view" not in st.session_state:
        st.session_state.auth_view = "login"

    # Use columns to center the card on desktop
    _, col_center, _ = st.columns([1, 2, 1])

    with col_center:
        # --- VIEW 3: UPDATE PASSWORD (WITH TOKEN) ---
        if st.session_state.auth_view == "update_password":
            with st.container(border=True):
                st.subheader("🔐 Set New Password")
                st.info("Enter the code sent to your email.")
                
                with st.form("reset_token_form"):
                    r_email = st.text_input("Email Address")
                    r_token = st.text_input("Reset Code / Token")
                    r_new_pass = st.text_input("New Password", type="password")
                    r_btn = st.form_submit_button("Update Password", type="primary", use_container_width=True)
                
                if r_btn:
                    if auth_engine:
                        with st.spinner("Updating..."):
                            success, msg = auth_engine.reset_password_with_token(r_email, r_token, r_new_pass)
                            if success:
                                st.success("✅ Password Updated! Please Log In.")
                                time.sleep(2)
                                st.session_state.auth_view = "login"
                                st.rerun()
                            else:
                                st.error(f"❌ {msg}")
                
                if st.button("⬅️ Back to Login"):
                    st.session_state.auth_view = "login"
                    st.rerun()
            return

        # --- VIEW 2: FORGOT PASSWORD REQUEST ---
        if st.session_state.auth_view == "forgot":
            with st.container(border=True):
                st.subheader("↺ Recovery")
                st.caption("We'll send a code to your email.")
                
                f_email = st.text_input("Email Address", key="forgot_email_input")
                
                if st.button("📩 Send Reset Code", type="primary", use_container_width=True):
                    if auth_engine:
                        with st.spinner("Sending..."):
                            success, msg = auth_engine.send_password_reset(f_email)
                            if success:
                                st.success("✅ Code sent! Check your inbox.")
                                time.sleep(1)
                                st.session_state.auth_view = "update_password" # Auto-advance
                                st.rerun()
                            else:
                                st.error(f"❌ {msg}")
                
                if st.button("I already have a code"):
                    st.session_state.auth_view = "update_password"
                    st.rerun()

                if st.button("⬅️ Back to Login"):
                    st.session_state.auth_view = "login"
                    st.rerun()
            return

        # --- VIEW 1: LOGIN / SIGNUP ---
        with st.container(border=True):
            
            # Helper to render Login Form
            def _render_login_form():
                st.subheader("Welcome Back")
                with st.form("login_form"):
                    l_email = st.text_input("Email", key="login_email")
                    l_pass = st.text_input("Password", type="password", key="login_pass")
                    l_btn = st.form_submit_button("Log In", type="primary", use_container_width=True)
                
                if l_btn:
                    if not l_email or not l_pass:
                        st.warning("Enter email and password.")
                    else:
                        with st.spinner("Verifying..."):
                            user, err = login_func(l_email, l_pass)
                            if user and user.user:
                                st.success(f"Welcome back!")
                                st.session_state.user_email = user.user.email
                                st.session_state.app_mode = "store"
                                st.rerun()
                            else:
                                st.error(f"❌ {err}")

                if st.button("Forgot Password?", type="secondary", use_container_width=True):
                    st.session_state.auth_view = "forgot"
                    st.rerun()

            # Helper to render Signup Form
            def _render_signup_form():
                st.subheader("Create Account")
                with st.form("signup_form"):
                    s_email = st.text_input("Email", key="signup_email")
                    s_pass = st.text_input("Password", type="password", help="8+ chars, Uppercase, Lowercase, Number", key="signup_pass")
                    s_name = st.text_input("Full Name")
                    
                    st.markdown("---")
                    st.caption("Mailing Address (Required)")
                    st.warning("⚠️ Browser Autofill (Light Blue) may not save correctly. verify all fields are filled.")
                    
                    s_addr = st.text_input("Street Address")
                    s_addr2 = st.text_input("Apt / Suite")
                    c1, c2, c3 = st.columns([2, 1, 1])
                    s_city = c1.text_input("City")
                    s_state = c2.text_input("State")
                    s_zip = c3.text_input("Zip")
                    
                    s_btn = st.form_submit_button("Sign Up", type="primary", use_container_width=True)

                if s_btn:
                    if not all([s_email, s_pass, s_name, s_addr, s_city, s_state, s_zip]):
                        st.error("Please complete all required fields.")
                    else:
                        with st.spinner("Creating Account..."):
                            res, err = signup_func(s_email, s_pass, s_name, s_addr, s_addr2, s_city, s_state, s_zip, "US", "English")
                            if res and res.user:
                                st.success("✅ Account created! Please Log In.")
                                time.sleep(2)
                                st.session_state.auth_view = "login"
                                st.rerun()
                            else:
                                st.error(f"❌ {err}")

            # --- TAB SWAPPING LOGIC ---
            # If came from "Start a Letter", show Signup first.
            is_signup_mode = st.session_state.get("auth_view") == "signup"
            
            if is_signup_mode:
                # Signup first, Login second (Bold)
                t1, t2 = st.tabs(["📝 New User Sign Up", "**🔑 Existing Users Log In**"])
                with t1: _render_signup_form()
                with t2: _render_login_form()
            else:
                # Login first (Default)
                t1, t2 = st.tabs(["🔑 Log In", "📝 Sign Up"])
                with t1: _render_login_form()
                with t2: _render_signup_form()

        st.markdown("</div>", unsafe_allow_html=True)