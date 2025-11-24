import streamlit as st
import time

def show_login(handle_login, handle_signup): 
    # --- LAZY IMPORTS (Fixes KeyError/Circular Import) ---
    import auth_engine
    import analytics
    # -----------------------------------------------------

    # --- INJECT ANALYTICS ---
    analytics.inject_ga() 

    c1, c2, c3 = st.columns([1, 2, 1])
    
    with c2:
        st.title("VerbaPost 📮")
        st.subheader("Member Access")
        
        client, err = auth_engine.get_supabase_client()
        if err: st.error(f"System Error: {err}")

        # --- ROBUST NAVIGATION STATE ---
        if "auth_mode" not in st.session_state:
            st.session_state.auth_mode = st.session_state.get("initial_mode", "login")

        # Create the switcher
        # Note: using a unique key ensures the state tracks correctly
        mode = st.radio("Select Mode:", ["Log In", "Create Account"], 
                        index=0 if st.session_state.auth_mode == "login" else 1,
                        horizontal=True, 
                        label_visibility="collapsed",
                        key="auth_mode_radio")

        # Update session state based on switcher
        if mode == "Log In":
            st.session_state.auth_mode = "login"
        else:
            st.session_state.auth_mode = "signup"

        st.divider()

        # ==========================================
        #  LOGIN VIEW
        # ==========================================
        if st.session_state.auth_mode == "login":
            with st.form("login_form"):
                email = st.text_input("Email")
                password = st.text_input("Password", type="password")
                submitted = st.form_submit_button("Log In", type="primary", use_container_width=True)
                
                if submitted:
                    with st.spinner("Verifying..."):
                        handle_login(email, password)
            
            # --- REAL PASSWORD RECOVERY ---
            with st.expander("Forgot Password?"):
                st.caption("Enter your email to receive a reset link.")
                reset_email = st.text_input("Reset Email", key="reset_email")
                
                if st.button("Send Reset Link"):
                    if not reset_email:
                        st.warning("Please enter an email address.")
                    else:
                        try:
                            # This actually calls Supabase to trigger the email
                            client.auth.reset_password_email(reset_email, options={"redirect_to": "https://verbapost.streamlit.app"})
                            st.success(f"Reset link sent to {reset_email} (if account exists).")
                            st.info("Check your spam folder if you don't see it.")
                        except Exception as e:
                            st.error(f"Error: {e}")

        # ==========================================
        #  SIGN UP VIEW
        # ==========================================
        else:
            with st.form("signup_form"):
                st.caption("Create your secure account")
                new_email = st.text_input("Email")
                
                # Vertical Passwords (No Columns)
                new_pass = st.text_input("Password", type="password")
                confirm_pass = st.text_input("Confirm Password", type="password")

                st.markdown("---")
                st.caption("Return Address")
                new_name = st.text_input("Full Name")
                new_street = st.text_input("Street Address")
                
                c_a, c_b = st.columns(2)
                new_city = c_a.text_input("City")
                new_state = c_b.text_input("State", max_chars=2)
                new_zip = st.text_input("Zip Code", max_chars=5)
                
                st.markdown("---")
                new_lang = st.selectbox("Preferred Language:", ["English", "Japanese", "Chinese", "Korean"])
                
                if st.form_submit_button("Create Account", type="primary", use_container_width=True):
                    # 1. Force State Update
                    st.session_state.auth_mode = "signup"
                    
                    # 2. Validation
                    if new_pass != confirm_pass:
                        st.error("❌ Passwords do not match.")
                    elif not (new_name and new_street and new_city and new_state and new_zip):
                        st.error("❌ Please fill all address fields.")
                    else:
                        with st.spinner("Creating account..."):
                            handle_signup(new_email, new_pass, new_name, new_street, new_city, new_state, new_zip, new_lang)
                            # If successful, handle_signup usually handles redirection, 
                            # but if it fails, we want to stay here.
        
        st.divider()
        c_back, c_legal = st.columns(2)
        with c_back:
            if st.button("⬅️ Home", type="secondary", use_container_width=True):
                st.session_state.current_view = "splash"
                st.rerun()
        with c_legal:
            if st.button("⚖️ Terms", type="secondary", use_container_width=True):
                st.session_state.current_view = "legal"
                st.rerun()