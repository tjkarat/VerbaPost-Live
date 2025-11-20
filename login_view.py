import streamlit as st
import auth_engine

def show_login():
    st.title("VerbaPost 📮")
    st.subheader("Login")

    # Create tabs for neat UI
    tab_login, tab_signup = st.tabs(["Login", "Create Account"])

    # --- LOGIN TAB ---
    with tab_login:
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Password", type="password", key="login_pass")
        
        if st.button("Log In", type="primary"):
            if not email or not password:
                st.error("Please enter both email and password.")
            else:
                success, error = auth_engine.sign_in(email, password)
                if success:
                    st.success("Welcome back!")
                    st.rerun() # Reloads the app to show the Main Interface
                else:
                    st.error(f"Login Failed: {error}")

    # --- SIGN UP TAB ---
    with tab_signup:
        new_email = st.text_input("Email", key="signup_email")
        new_password = st.text_input("Password", type="password", key="signup_pass")
        
        if st.button("Create Account"):
            if not new_email or not new_password:
                st.error("Please fill in all fields.")
            elif len(new_password) < 6:
                st.warning("Password must be at least 6 characters.")
            else:
                success, error = auth_engine.sign_up(new_email, new_password)
                if success:
                    st.success("Account Created! Logging you in...")
                    st.rerun()
                else:
                    st.error(f"Signup Failed: {error}")
