import streamlit as st
import auth_engine

def render_login(*args, **kwargs):
    st.markdown("""
    <style>
        .auth-header { text-align: center; font-weight: 700; color: #203A60; margin-bottom: 20px; }
        .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] div { color: #FF4B4B !important; }
        .stButton button { width: 100%; border-radius: 8px; font-weight: 600; }
    </style>
    """, unsafe_allow_html=True)

    if st.query_params.get("type") == "recovery":
        st.info("Recovery Mode")
        token = st.text_input("Reset Token"); pwd = st.text_input("New Password", type="password")
        if st.button("Reset Password"): 
            auth_engine.reset_password_with_token("", token, pwd)
            st.success("Updated! Please login."); st.query_params.clear()
        return

    st.markdown("<h2 class='auth-header'>Access VerbaPost</h2>", unsafe_allow_html=True)
    
    t1, t2, t3 = st.tabs(["Log In", "Sign Up", "Forgot Password"])
    
    with t1:
        with st.form("login_form"):
            email = st.text_input("Email")
            pwd = st.text_input("Password", type="password")
            if st.form_submit_button("Log In", type="primary"):
                res, err = auth_engine.sign_in(email, pwd)
                if res:
                    st.session_state.authenticated = True
                    st.session_state.user_email = email
                    st.session_state.app_mode = "store"
                    st.query_params.clear()
                    st.rerun()
                else: st.error(err)

    with t2:
        with st.form("signup_form"):
            email = st.text_input("Email")
            pwd = st.text_input("Password", type="password")
            name = st.text_input("Full Name")
            if st.form_submit_button("Sign Up"):
                res, err = auth_engine.sign_up(email, pwd, name, "123 St", "", "City", "ST", "00000", "US", "en")
                if res: st.success("Created! Please Log in.")
                else: st.error(err)

    with t3:
        email = st.text_input("Email Address")
        if st.button("Send Reset Link"): 
            auth_engine.send_password_reset(email)
            st.success("Check your email.")