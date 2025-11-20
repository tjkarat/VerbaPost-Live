cat <<EOF > login_view.py
import streamlit as st
import time

def show_login():
    # Import logic is now inside the function, preventing global crash
    import auth_engine 
    
    # Use columns to center the form on desktop
    c1, c2, c3 = st.columns([1, 2, 1])
    
    with c2:
        st.title("VerbaPost 📮")
        st.subheader("Member Access")
        
        client, err = auth_engine.get_supabase_client()
        if err:
            st.error(f"⚠️ System Error: {err}")
            st.info("Please ensure your Supabase URL and Key are in Streamlit Secrets.")
            if st.button("Back"):
                st.session_state.current_view = "splash"
                st.rerun()
            st.stop()

        tab_login, tab_signup = st.tabs(["Log In", "Create Account"])

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
            new_email = st.text_input("Email", key="new_email")
            new_pass = st.text_input("Password", type="password", key="new_pass")
            
            if st.button("Create Account", use_container_width=True):
                with st.spinner("Creating account..."):
                    user, error = auth_engine.sign_up(new_email, new_pass)
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
EOF