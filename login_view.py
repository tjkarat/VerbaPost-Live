import streamlit as st
import auth_engine
import time

def show_login():
    # --- FIX 1: Corrected Ternary Syntax for tab index calculation ---
    initial_tab_index = 1 if st.session_state.get('initial_mode', 'login') == 'signup' else 0
    
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

        # Render tabs using the fixed index calculation
        tab_login, tab_signup = st.tabs(["Log In", "Create Account"], index=initial_tab_index) 

        # --- LOGIN TAB ---
        with tab_login:
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_pass")
            
            if st.button("Log In", type="primary", use_container_width=True):
                with st.spinner("Verifying credentials..."):
                    user, error = auth_engine.sign_in(email, password)
                    if error:
                        st.error(f"Login Failed: {error}")
                    else:
                        st.success("Welcome!")
                        st.session_state.user = user
                        st.session_state.user_email = email
                        
                        # LOAD SAVED DATA
                        saved_addr = auth_engine.get_current_address(email)
                        if saved_addr:
                            st.session_state["from_name"] = saved_addr.get("name", "")
                            st.session_state["from_street"] = saved_addr.get("street", "")
                            st.session_state["from_city"] = saved_addr.get("city", "")
                            st.session_state["from_state"] = saved_addr.get("state", "")
                            st.session_state["from_zip"] = saved_addr.get("zip", "")
                        
                        st.session_state.current_view = "main_app"
                        st.rerun()

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
                        user, error = auth_engine.sign_up(
                            new_email, new_pass, new_name, new_street, new_city, new_state, new_zip
                        )
                        if error:
                            st.error(f"Error: {error}")
                        else:
                            st.success("Account created! Logged in.")
                            st.session_state.user = user
                            st.session_state.user_email = new_email
                            st.session_state.current_view = "main_app"
                            st.rerun()
        
        st.divider()
        if st.button("⬅️ Back to Home", type="secondary"):
            st.session_state.current_view = "splash"
            st.rerun()