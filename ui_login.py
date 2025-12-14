import streamlit as st
import time

# --- ROBUST IMPORTS ---
try:
    import auth_engine
except Exception:
    auth_engine = None

try:
    import database
except Exception:
    database = None

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
    /* Status Badge Styling */
    .status-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 0.8rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .badge-gray { background-color: #f0f2f6; color: #555; }
    .badge-green { background-color: #e6fffa; color: #047857; border: 1px solid #047857; }
    </style>
    """, unsafe_allow_html=True)

def render_login_page():
    trigger_shake_error() # Pre-load CSS
    
    # Check for Password Recovery Mode URL params
    if "type" in st.query_params and st.query_params["type"] == "recovery":
        _render_password_reset()
        return

    # --- HEADER ---
    st.markdown("<h2 style='text-align: center; font-family: Merriweather, serif;'>Welcome Back</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #666;'>Secure access to your correspondence.</p>", unsafe_allow_html=True)
    st.write("")

    # --- TABS (Clean toggle) ---
    tab_login, tab_signup = st.tabs(["🔒 Log In", "✨ New Account"])

    # --- TAB 1: LOGIN ---
    with tab_login:
        with st.container(border=True):
            email = st.text_input("Email Address", key="login_email")
            password = st.text_input("Password", type="password", key="login_pass")
            
            st.write("")
            if st.button("Sign In", type="primary", use_container_width=True):
                if not email or not password:
                    trigger_shake_error()
                    st.error("Please enter both email and password.")
                elif auth_engine:
                    user = auth_engine.verify_user(email, password)
                    if user:
                        st.session_state.authenticated = True
                        st.session_state.user_email = user.get("email")
                        st.session_state.user_id = user.get("id")
                        st.toast("Login Successful!", icon="✅")
                        time.sleep(0.5)
                        st.session_state.app_mode = "store"
                        st.rerun()
                    else:
                        trigger_shake_error()
                        st.error("Incorrect email or password.")
                else:
                    st.error("Auth Engine Disconnected")

            # Expandable "Forgot Password" Section
            with st.expander("❓ Trouble signing in?"):
                st.info("Enter your email below to receive a secure reset link.")
                reset_email = st.text_input("Recovery Email", key="reset_req_email")
                if st.button("Send Reset Link"):
                    if auth_engine and reset_email:
                        auth_engine.send_password_reset(reset_email)
                        st.success(f"Reset link sent to {reset_email}")

    # --- TAB 2: SIGNUP (With Progress Tracker) ---
    with tab_signup:
        # Progress Tracker
        st.markdown("""
        <div style="display: flex; justify-content: space-between; margin-bottom: 20px; color: #888; font-size: 0.85rem;">
            <span><strong style="color: #667eea;">Step 1:</strong> Account</span>
            <span><strong style="color: #ccc;">Step 2:</strong> Address</span>
            <span><strong style="color: #ccc;">Step 3:</strong> Verify</span>
        </div>
        <div style="height: 4px; background: #eee; border-radius: 2px; margin-bottom: 20px;">
            <div style="height: 100%; width: 33%; background: #667eea; border-radius: 2px;"></div>
        </div>
        """, unsafe_allow_html=True)

        with st.container(border=True):
            # Quick Tip Box
            st.info("💡 **Quick Tip:** Use your real name. It will appear on your return address labels.")
            
            new_email = st.text_input("Email", key="su_email")
            new_pass = st.text_input("Create Password", type="password", key="su_pass")
            new_name = st.text_input("Full Name", key="su_name")
            
            st.markdown("#### 🏠 Return Address")
            s_addr = st.text_input("Street Address", key="su_street")
            c1, c2, c3 = st.columns(3)
            s_city = c1.text_input("City", key="su_city")
            s_state = c2.text_input("State", key="su_state")
            s_zip = c3.text_input("Zip", key="su_zip")
            
            st.write("")
            if st.button("Create Account", type="primary", use_container_width=True):
                if not (new_email and new_pass and new_name and s_addr and s_zip):
                    trigger_shake_error()
                    st.error("All fields are required for account creation.")
                elif auth_engine:
                    try:
                        # 1. Create Auth User
                        user = auth_engine.create_user(new_email, new_pass)
                        if user:
                            # 2. Save Profile Data
                            if database:
                                profile_data = {
                                    "user_id": user.get("id"),
                                    "email": new_email,
                                    "full_name": new_name,
                                    "return_address_street": s_addr,
                                    "return_address_city": s_city,
                                    "return_address_state": s_state,
                                    "return_address_zip": s_zip,
                                    "return_address_country": "US"
                                }
                                database.create_user_profile(profile_data)
                            
                            st.balloons()
                            st.success("Account Created! Please log in.")
                        else:
                            trigger_shake_error()
                            st.error("Email already registered or invalid.")
                    except Exception as e:
                        st.error(f"Signup Error: {e}")

    # Back Button
    st.markdown("---")
    if st.button("⬅️ Back to Home", use_container_width=True):
        st.query_params.clear()
        st.session_state.app_mode = "splash"
        st.rerun()

def _render_password_reset():
    """Isolated view for password reset to keep main logic clean."""
    st.markdown("### 🔐 Set New Password")
    with st.form("new_pass_form"):
        p1 = st.text_input("New Password", type="password")
        p2 = st.text_input("Confirm Password", type="password")
        if st.form_submit_button("Update Password"):
            if p1 == p2 and len(p1) > 5:
                if auth_engine:
                    auth_engine.update_user_password(p1)
                    st.success("Password Updated! Please log in.")
                    time.sleep(2)
                    st.query_params.clear()
                    st.rerun()
            else:
                trigger_shake_error()
                st.error("Passwords must match and be at least 6 characters.")