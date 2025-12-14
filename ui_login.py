import streamlit as st
import auth_engine

def render_login():
    st.markdown("## Access VerbaPost")
    
    if st.query_params.get("type") == "recovery":
        token = st.text_input("Reset Token"); pwd = st.text_input("New Password", type="password")
        if st.button("Reset"): 
            auth_engine.reset_password_with_token("", token, pwd); st.success("Updated! Login now.")
        return

    t1, t2, t3 = st.tabs(["Log In", "Sign Up", "Forgot Password"])
    
    with t1:
        with st.form("login"):
            email = st.text_input("Email"); pwd = st.text_input("Password", type="password")
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
        with st.form("signup"):
            email = st.text_input("Email"); pwd = st.text_input("Password", type="password"); name = st.text_input("Name")
            if st.form_submit_button("Sign Up"):
                res, err = auth_engine.sign_up(email, pwd, name, "123 St", "", "City", "ST", "00000", "US", "en")
                if res: st.success("Created! Log in.")
                else: st.error(err)

    with t3:
        email = st.text_input("Email")
        if st.button("Send Link"): auth_engine.send_password_reset(email); st.success("Sent!")