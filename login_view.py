import streamlit as st
import auth_engine
import time

def show_login():
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        st.title("VerbaPost 📮")
        st.markdown("### Member Access")

        tab_login, tab_signup = st.tabs(["Log In", "Create Account"])

        with tab_login:
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_pass")
            
            if st.button("Log In", type="primary", use_container_width=True):
                with st.spinner("Verifying..."):
                    user, error = auth_engine.sign_in(email, password)
                    if error:
                        st.error(f"Failed: {error}")
                    else:
                        st.success("Welcome!")
                        st.session_state.user = user
                        
                        # Load address
                        saved_addr = auth_engine.get_current_address(email)
                        if saved_addr:
                            st.session_state["from_name"] = saved_addr.get("name", "")
                            st.session_state["from_street"] = saved_addr.get("street", "")
                            st.session_state["from_city"] = saved_addr.get("city", "")
                            st.session_state["from_state"] = saved_addr.get("state", "")
                            st.session_state["from_zip"] = saved_addr.get("zip", "")
                        
                        st.session_state.current_view = "main_app"
                        st.rerun()

        with tab_signup:
            new_email = st.text_input("Email", key="new_email")
            new_pass = st.text_input("Password", type="password", key="new_pass")
            
            if st.button("Create Account", use_container_width=True):
                with st.spinner("Creating..."):
                    user, error = auth_engine.sign_up(new_email, new_pass)
                    if error:
                        st.error(f"Error: {error}")
                    else:
                        st.success("Account created! Logged in.")
                        st.session_state.user = user
                        st.session_state.current_view = "main_app"
                        st.rerun()
        
        st.divider()
        if st.button("⬅️ Back"):
            st.session_state.current_view = "splash"
            st.rerun()
