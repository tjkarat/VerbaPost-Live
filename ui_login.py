import streamlit as st

def show_login(login_func, signup_func):
    # --- CENTER THE LOGIN FORM ---
    c1, c2, c3 = st.columns([1, 1.5, 1])
    
    with c2:
        # Header with specific Brand Blue color
        st.markdown("""
        <div style="text-align: center; margin-bottom: 20px;">
            <h1 style="color: #2a5298 !important; margin-bottom: 0;">VerbaPost 📮</h1>
            <p style="font-size: 1.1em; color: #666 !important;">Member Access</p>
        </div>
        """, unsafe_allow_html=True)

        with st.container(border=True):
            if "auth_error" in st.session_state:
                st.error(st.session_state.auth_error)
                del st.session_state.auth_error
            
            tab_login, tab_signup = st.tabs(["🔑 Log In", "📝 Create Account"])
            
            with tab_login:
                email = st.text_input("Email Address", key="login_email")
                password = st.text_input("Password", type="password", key="login_pass")
                st.markdown("<br>", unsafe_allow_html=True)
                
                if st.button("Log In", type="primary", use_container_width=True):
                    if email and password:
                        with st.spinner("Verifying..."):
                            login_func(email, password)
                    else:
                        st.warning("Enter email & password")
            
            with tab_signup:
                new_email = st.text_input("Email", key="new_email")
                new_pass = st.text_input("Password", type="password", key="new_pass")
                st.markdown("---")
                name = st.text_input("Full Name")
                lang = st.selectbox("Language", ["English", "Spanish", "French"])
                
                st.caption("Address (for return labels)")
                addr = st.text_input("Street Address")
                c_city, c_state, c_zip = st.columns([2, 1, 1])
                city = c_city.text_input("City")
                state = c_state.text_input("State")
                zip_code = c_zip.text_input("Zip")
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                if st.button("Create Account", type="primary", use_container_width=True):
                    if new_email and new_pass:
                        with st.spinner("Creating account..."):
                            signup_func(new_email, new_pass, name, addr, city, state, zip_code, lang)
                    else:
                        st.warning("Missing fields")

    st.markdown("<br><br>", unsafe_allow_html=True)
    f1, f2, f3 = st.columns([1, 2, 1])
    with f2:
        if st.button("← Back to Home", type="secondary", use_container_width=True):
            st.session_state.current_view = "splash"
            st.rerun()