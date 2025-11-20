import streamlit as st
import auth_engine
import time

# FIX: Added required positional arguments handle_login and handle_signup
def show_login(handle_login, handle_signup): 
    # Center the login box
    c1, c2, c3 = st.columns([1, 2, 1])
    
    with c2:
        st.title("VerbaPost 📮")
        st.subheader("Member Access")
        
        # Diagnostic Check
        client, err = auth_engine.get_supabase_client()
        if err:
            st.error(f"⚠️ System Error: {err}")
            st.info("Please ensure your Supabase URL and Key are in Streamlit Secrets.")
            if st.button("Back"):
                st.session_state.current_view = "splash"
                st.rerun()
            st.stop()

        tab_login, tab_signup = st.tabs(["Log In", "Create Account"], index=1 if st.session_state.get('initial_mode', 'login') == 'signup' else 0) 

        # --- LOGIN TAB ---
        with tab_login:
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_pass")
            
            if st.button("Log In", type="primary", use_container_width=True):
                with st.spinner("Verifying credentials..."):
                    handle_login(email, password)

        # --- SIGN UP TAB ---
        with tab_signup:
            new_email = st.text_input("Email", key="s_email")
            new_pass = st.text_input("Password", type="password", key="s_pass")

            st.markdown("---")
            st.subheader("Your Return Address (Saved Automatically)")

            new_name = st.text_input("Your Full Name", key="s_name")
            new_street = st.text_input("Street Address", key="s_street")
            c3, c4 = st.columns(2)
            new_city = c3.text_input("City", key="s_city")
            new_state = c3.text_input("State", max_chars=2, key="s_state")
            new_zip = c4.text_input("Zip Code", max_chars=5, key="s_zip")
            
            if st.button("Create Account & Save Address", type="primary", use_container_width=True):
                if not (new_name and new_street and new_city and new_state and new_zip):
                    st.error("Please fill all address fields to create account.")
                else:
                    with st.spinner("Creating account..."):
                        handle_signup(new_email, new_pass, new_name, new_street, new_city, new_state, new_zip)
        
        st.divider()
        if st.button("⬅️ Back to Home", type="secondary"):
            st.session_state.current_view = "splash"
            st.rerun()
