import streamlit as st
import auth_engine
import time

def show_login(handle_login, handle_signup): 
    c1, c2, c3 = st.columns([1, 2, 1])
    
    with c2:
        st.title("VerbaPost 📮")
        st.subheader("Member Access")
        
        client, err = auth_engine.get_supabase_client()
        if err:
            st.error(f"⚠️ System Error: {err}")
            st.stop()

        tab_login, tab_signup = st.tabs(["Log In", "Create Account"]) 

        # --- LOGIN TAB ---
        with tab_login:
            with st.form("login_form"):
                email = st.text_input("Email")
                password = st.text_input("Password", type="password")
                
                # Submit Button
                if st.form_submit_button("Log In", type="primary", use_container_width=True):
                    with st.spinner("Verifying..."):
                        handle_login(email, password)

        # --- SIGN UP TAB ---
        with tab_signup:
            with st.form("signup_form"):
                st.caption("Create your secure account")
                new_email = st.text_input("Email")
                
                # Double Password Validation
                c_p1, c_p2 = st.columns(2)
                new_pass = c_p1.text_input("Password", type="password")
                confirm_pass = c_p2.text_input("Confirm Password", type="password")

                st.markdown("---")
                st.caption("Return Address (Autofill fix enabled)")
                
                new_name = st.text_input("Full Name")
                new_street = st.text_input("Street Address")
                c_a, c_b = st.columns(2)
                new_city = c_a.text_input("City")
                new_state = c_b.text_input("State", max_chars=2)
                new_zip = st.text_input("Zip Code", max_chars=5)
                
                # Submit Button acts as the "Catch All" for data
                if st.form_submit_button("Create Account", type="primary", use_container_width=True):
                    if new_pass != confirm_pass:
                        st.error("❌ Passwords do not match.")
                    elif not (new_name and new_street and new_city and new_state and new_zip):
                        st.error("❌ Please fill all address fields.")
                    else:
                        with st.spinner("Creating account..."):
                            handle_signup(new_email, new_pass, new_name, new_street, new_city, new_state, new_zip)
        
        st.divider()
        if st.button("⬅️ Back to Home", type="secondary"):
            st.session_state.current_view = "splash"
            st.rerun()