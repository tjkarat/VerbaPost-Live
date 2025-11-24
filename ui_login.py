import streamlit as st
from streamlit_drawable_canvas import st_canvas

def show_login(login_func, signup_func):
    # --- CENTER THE LOGIN FORM ---
    # We use columns [1, 2, 1] to create empty space on left/right
    # This fixes the "Too Wide" look
    c1, c2, c3 = st.columns([1, 1.5, 1])
    
    with c2:
        st.markdown("""
        <div style="text-align: center; margin-bottom: 20px;">
            <h1 style="color: #667eea; margin-bottom: 0;">VerbaPost 📮</h1>
            <p style="font-size: 1.1em; color: #666;">Member Access</p>
        </div>
        """, unsafe_allow_html=True)

        # --- LOGIN CONTAINER ---
        with st.container(border=True):
            # Check for error passed from previous attempts
            if "auth_error" in st.session_state:
                st.error(st.session_state.auth_error)
                del st.session_state.auth_error
            
            tab_login, tab_signup = st.tabs(["🔑 Log In", "📝 Create Account"])
            
            # --- LOGIN TAB ---
            with tab_login:
                email = st.text_input("Email Address", key="login_email")
                password = st.text_input("Password", type="password", key="login_pass")
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                if st.button("Log In", type="primary", use_container_width=True):
                    if email and password:
                        # Attempt login
                        with st.spinner("Verifying credentials..."):
                            # The main.py router passes the actual auth function here
                            login_func(email, password)
                    else:
                        st.warning("Please enter email and password")
            
            # --- SIGNUP TAB ---
            with tab_signup:
                new_email = st.text_input("Email", key="new_email")
                new_pass = st.text_input("Password", type="password", key="new_pass")
                st.markdown("---")
                c_name, c_lang = st.columns(2)
                name = c_name.text_input("Full Name")
                lang = c_lang.selectbox("Language", ["English", "Spanish", "French"])
                
                st.caption("Address (for return labels)")
                addr = st.text_input("Street Address")
                c_city, c_state, c_zip = st.columns([2, 1, 1])
                city = c_city.text_input("City")
                state = c_state.text_input("State")
                zip_code = c_zip.text_input("Zip")
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                if st.button("Create Account", type="primary", use_container_width=True):
                    if new_email and new_pass and name:
                        with st.spinner("Creating account..."):
                            signup_func(new_email, new_pass, name, addr, city, state, zip_code, lang)
                    else:
                        st.warning("Please fill in required fields")

    # --- FOOTER NAVIGATION ---
    st.markdown("<br><br>", unsafe_allow_html=True)
    f1, f2, f3 = st.columns([1, 2, 1])
    with f2:
        if st.button("← Back to Home", type="secondary", use_container_width=True):
            st.session_state.current_view = "splash"
            st.rerun()