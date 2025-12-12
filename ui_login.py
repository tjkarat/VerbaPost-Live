import streamlit as st
import time

# --- CONSTANTS ---
COMMON_COUNTRIES = [
    "United States", "Canada", "United Kingdom", "Australia", 
    "Germany", "France", "Japan", "Mexico", "Other"
]

def show_login(sign_in_func, sign_up_func, *args, **kwargs):
    """
    Renders the main authentication interface.
    
    Arguments:
    - sign_in_func: The actual function to call for signing in.
    - sign_up_func: The actual function to call for signing up.
    - *args, **kwargs: Catch-alls to prevent crashes if extra data is passed.
    """
    
    # Container to keep the form centered and neat
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Tabs for switching modes
    tab_login, tab_signup = st.tabs(["Log In", "Sign Up"])

    # --- LOGIN TAB ---
    with tab_login:
        st.header("Welcome Back")
        
        with st.form("login_form"):
            email = st.text_input("Email", placeholder="you@example.com")
            password = st.text_input("Password", type="password")
            
            submitted = st.form_submit_button("Log In", type="primary", use_container_width=True)
            
            if submitted:
                if not email or not password:
                    st.error("Please enter both email and password.")
                else:
                    with st.spinner("Logging in..."):
                        # FIXED: Call the passed function directly
                        user, error = sign_in_func(email, password)
                        
                        if error:
                            st.error(f"❌ {error}")
                        else:
                            # Success: Set Session State
                            st.session_state.user_email = user.user.email
                            st.session_state.user_id = user.user.id
                            
                            # Attempt to grab full name from metadata
                            meta_name = user.user.user_metadata.get('full_name', '')
                            st.session_state.user_name = meta_name if meta_name else email.split('@')[0]
                            
                            st.success("Login successful!")
                            st.session_state.app_mode = "store" # Redirect to store
                            st.rerun()

        # Forgot Password Link
        st.markdown("")
        col_space, col_link = st.columns([2, 1])
        with col_link:
            # FIXED: Used 'secondary' to prevent StreamlitAPIException
            if st.button("Forgot Password?", type="secondary"):
                st.session_state.app_mode = "password_reset"
                st.rerun()

    # --- SIGN UP TAB ---
    with tab_signup:
        st.header("Create Account")
        
        with st.form("signup_form"):
            # 1. Identity Section
            col_name, col_email = st.columns(2)
            with col_name:
                new_name = st.text_input("Full Name", placeholder="Jane Doe")
            with col_email:
                new_email = st.text_input("Email", placeholder="jane@example.com")
            
            new_password = st.text_input("Password (min 8 chars)", type="password")
            
            st.markdown("---") # Visual separator
            st.caption("📍 Return Address (Required for Mail)")

            # 2. Address Line 1 & 2
            street = st.text_input("Street Address", placeholder="123 Main St")
            street2 = st.text_input("Apt / Suite (Optional)", placeholder="Apt 4B")

            # 3. Compact Address Grid (Includes Country)
            # Row 1: City & State
            c1, c2 = st.columns([2, 1]) 
            with c1:
                city = st.text_input("City")
            with c2:
                state = st.text_input("State / Province")

            # Row 2: Zip & Country
            c3, c4 = st.columns([1, 2])
            with c3:
                zip_code = st.text_input("Zip / Postal")
            with c4:
                # Default index 0 is "United States"
                country = st.selectbox("Country", options=COMMON_COUNTRIES, index=0)

            # 4. Submit
            submitted = st.form_submit_button("Create Account", type="primary", use_container_width=True)

            if submitted:
                # Basic Validation
                if not new_email or not new_password or not new_name or not street:
                    st.error("Please fill in all required fields.")
                elif len(new_password) < 8:
                    st.error("Password must be at least 8 characters long.")
                else:
                    with st.spinner("Creating account..."):
                        # FIXED: Call the passed function directly
                        user, error = sign_up_func(
                            email=new_email, 
                            password=new_password, 
                            name=new_name, 
                            street=street, 
                            street2=street2, 
                            city=city, 
                            state=state, 
                            zip_code=zip_code, 
                            country=country,
                            language="English"
                        )
                        
                        if error:
                            st.error(f"❌ {error}")
                        else:
                            st.success("✅ Account created! Please log in via the first tab.")
                            st.balloons()

def render_password_reset(auth_engine, *args, **kwargs):
    """
    Renders the view to request a password reset email.
    Note: ui_main.py might pass auth_engine here correctly, so we keep it.
    """
    st.header("Reset Password")
    st.write("Enter your email address below. We'll send you a link to reset your password.")
    
    with st.form("reset_request"):
        email = st.text_input("Email Address")
        submitted = st.form_submit_button("Send Reset Link", type="primary", use_container_width=True)
        
        if submitted:
            if not email:
                st.error("Please enter your email.")
            else:
                with st.spinner("Sending..."):
                    # This uses the module passed in, which is correct for this specific view
                    success, msg = auth_engine.send_password_reset(email)
                    if success:
                        st.success("✅ Check your email inbox for the reset link.")
                    else:
                        st.error(f"❌ Error: {msg}")
    
    if st.button("← Back to Login"):
        st.session_state.app_mode = "login"
        st.rerun()