import streamlit as st
import time
# DIRECT IMPORT - DO NOT WRAP IN TRY/EXCEPT
# We need to know if this fails immediately.
import auth_engine 
import database

# --- ANIMATIONS & STYLING ---
def trigger_shake_error():
    """Injects CSS to shake the next error alert."""
    st.markdown("""
    <style>
    @keyframes shake {
        0% { transform: translateX(0); }
        25% { transform: translateX(-5px); }
        50% { transform: translateX(5px); }
        75% { transform: translateX(-5px); }
        100% { transform: translateX(0); }
    }
    .stAlert {
        animation: shake 0.3s cubic-bezier(.36,.07,.19,.97) both;
        border-left: 4px solid #d93025 !important;
        background-color: #fff8f8;
        color: #d93025;
    }
    </style>
    """, unsafe_allow_html=True)

# --- RECOVERY VIEW ---
def _render_password_reset():
    st.markdown("### 🔐 Password Recovery")
    
    # Step 1: Verify Code
    if not st.session_state.get("recovery_verified"):
        st.info("Please enter the code sent to your email.")
        
        with st.form("otp_form"):
            email_input = st.text_input("Email Address")
            code_input = st.text_input("Recovery Code (6 digits)", placeholder="123456")
            
            if st.form_submit_button("Verify Code", type="primary", use_container_width=True):
                if auth_engine:
                    success, msg = auth_engine.verify_otp(email_input, code_input)
                    if success:
                        st.session_state.recovery_verified = True
                        st.success("Identity Verified! Please set your new password below.")
                        st.rerun()
                    else:
                        trigger_shake_error()
                        st.error(f"Verification Failed: {msg}")
                else:
                    st.error("System Error: Auth Engine Offline")
    
    # Step 2: Set New Password
    else:
        st.success("✅ Identity Verified")
        with st.form("new_pass_form"):
            p1 = st.text_input("New Password", type="password")
            p2 = st.text_input("Confirm Password", type="password")
            
            if st.form_submit_button("Update Password", type="primary", use_container_width=True):
                if p1 == p2 and len(p1) > 5:
                    if auth_engine.update_user_password(p1):
                        st.balloons()
                        st.success("Password Updated Successfully! Redirecting...")
                        st.session_state.recovery_verified = False
                        st.query_params.clear()
                        time.sleep(2)
                        st.session_state.app_mode = "login"
                        st.rerun()
                    else:
                        st.error("Failed to update. Session may have expired.")
                else:
                    trigger_shake_error()
                    st.error("Passwords must match and be at least 6 characters.")

# --- MAIN LOGIN PAGE ---
def render_login_page():
    trigger_shake_error()
    
    # Check URL for recovery mode
    if st.query_params.get("type") == "recovery":
        _render_password_reset()
        return

    st.markdown("<h2 style='text-align: center; font-family: Merriweather, serif;'>Welcome Back</h2>", unsafe_allow_html=True)
    st.write("")

    tab_login, tab_signup = st.tabs(["🔒 Log In", "✨ New Account"])

    # --- TAB 1: LOGIN ---
    with tab_login:
        with st.form("login_form"):
            email = st.text_input("Email Address", key="login_email")
            password = st.text_input("Password", type="password", key="login_pass")
            
            st.write("")
            if st.form_submit_button("Sign In", type="primary", use_container_width=True):
                if not email or not password:
                    trigger_shake_error()
                    st.error("Please enter email and password.")
                elif auth_engine:
                    user = auth_engine.verify_user(email, password)
                    if user:
                        st.session_state.authenticated = True
                        st.session_state.user_email = user.get("email")
                        st.toast("Login Successful!", icon="✅")
                        st.query_params.clear()
                        st.session_state.app_mode = "store"
                        st.rerun()
                    else:
                        trigger_shake_error()
                        st.error("Incorrect credentials or email not confirmed.")
        
        # Forgot Password (Correctly placed OUTSIDE the form)
        with st.expander("❓ Forgot Password?"):
            st.write("We will send a 6-digit code to your email.")
            rec_email = st.text_input("Enter your email", key="rec_email_input")
            if st.button("Send Code"):
                if auth_engine and rec_email:
                    success, msg = auth_engine.send_password_reset(rec_email)
                    if success:
                        st.success("Code sent! Check your inbox.")
                        time.sleep(1)
                        st.query_params["type"] = "recovery"
                        st.rerun()
                    else:
                        st.error(f"Error: {msg}")

    # --- TAB 2: SIGNUP ---
    with tab_signup:
        with st.container(border=True):
            st.info("💡 Use your real name for return address labels.")
            new_email = st.text_input("Email", key="su_email")
            new_pass = st.text_input("Password", type="password", key="su_pass")
            
            if st.button("Create Account", type="primary", use_container_width=True):
                if new_email and new_pass and auth_engine:
                    try:
                        user = auth_engine.create_user(new_email, new_pass)
                        if user:
                            # Auto-create profile entry if DB exists
                            if database:
                                try:
                                    database.create_user_profile({"user_id": user["id"], "email": new_email})
                                except: pass
                                
                            st.success("Account Created! Please check your email to confirm.")
                        else:
                            st.error("Could not create account.")
                    except Exception as e:
                        st.error(f"Error: {e}")

    st.markdown("---")
    if st.button("⬅️ Back to Home"):
        st.query_params.clear()
        st.session_state.app_mode = "splash"
        st.rerun()

# Safety Alias
render_login = render_login_page