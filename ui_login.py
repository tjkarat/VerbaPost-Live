import streamlit as st

COUNTRIES = {
    "US": "United States", "CA": "Canada", "GB": "United Kingdom", "FR": "France",
    "DE": "Germany", "IT": "Italy", "ES": "Spain", "AU": "Australia", "MX": "Mexico",
    "JP": "Japan", "BR": "Brazil", "IN": "India"
}

LANGUAGES = [
    "English", "Spanish", "French", "German", "Italian", 
    "Japanese", "Korean", "Chinese", "Portuguese"
]

def validate_address(street, city, state, zip_code, country_code):
    errors = []
    if country_code == "US":
        if len(zip_code) != 5 or not zip_code.isdigit():
            errors.append("US Zip code must be exactly 5 digits.")
        if len(state) != 2:
            errors.append("US State must be a 2-letter abbreviation.")
    else:
        if len(str(zip_code)) < 3: errors.append("Postal code looks too short.")
        if len(str(state)) < 2: errors.append("State/Province required.")
    if len(street) < 5: errors.append("Street address looks too short.")
    return errors

def show_login(login_func, signup_func):
    # --- CSS: INPUT FIELD STYLING ---
    st.markdown("""
    <style>
        /* Clean Input Borders & Focus Highlight */
        div[data-testid="stForm"] input, div[data-testid="stForm"] select {
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 10px;
            transition: all 0.2s ease;
        }
        div[data-testid="stForm"] input:focus {
            border-color: #2a5298 !important;
            box-shadow: 0 0 0 3px rgba(42, 82, 152, 0.15) !important;
            outline: none;
        }
        /* Info Box Styling */
        .stAlert {
            background-color: #f0f9ff;
            border: 1px solid #bae6fd;
            color: #0c4a6e;
        }
    </style>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1, 3, 1])
    
    with c2:
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
            
            active_tab = st.session_state.get("auth_view", "login")
            if active_tab == "signup": t_signup, t_login = st.tabs(["📝 Create Account", "🔑 Log In"])
            else: t_login, t_signup = st.tabs(["🔑 Log In", "📝 Create Account"])
            
            # --- LOGIN TAB ---
            with t_login:
                with st.form("login_form"):
                    email = st.text_input("Email Address", key="login_email")
                    password = st.text_input("Password", type="password", key="login_pass")
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.form_submit_button("Log In", type="primary", use_container_width=True):
                        if email and password:
                            with st.spinner("Verifying..."): login_func(email, password)
                        else: st.warning("Enter email & password")
                if st.button("🔑 Lost Password?", type="secondary", use_container_width=True):
                    st.session_state.app_mode = "forgot_password"; st.rerun()
            
            # --- SIGNUP TAB ---
            with t_signup:
                st.caption("Please fill out your details below.")
                with st.form("signup_form"):
                    new_email = st.text_input("Email")
                    new_pass = st.text_input("Password", type="password")
                    confirm_pass = st.text_input("Confirm Password", type="password")
                    
                    st.markdown("---")
                    st.markdown("### 🏠 Your Return Address")
                    st.info("ℹ️ **Note:** This address will be printed on your envelopes so mail can be returned to you if undeliverable.")
                    
                    name = st.text_input("Full Legal Name")
                    
                    # --- NEW: LANGUAGE SELECTOR ---
                    c_cntry, c_lang = st.columns([1, 1])
                    country_code = c_cntry.selectbox("Country", list(COUNTRIES.keys()), format_func=lambda x: COUNTRIES[x], index=0)
                    language = c_lang.selectbox("Preferred Language", LANGUAGES, index=0)
                    
                    addr = st.text_input("Street Address")
                    addr2 = st.text_input("Apt / Suite / Unit (Optional)")
                    
                    s_lbl_st = "State (2 letters)" if country_code == "US" else "State/Province"
                    s_lbl_zip = "Zip Code" if country_code == "US" else "Postal Code"
                    
                    # Columns for City/State/Zip only
                    c_city, c_state, c_zip = st.columns([2, 1, 1.2])
                    city = c_city.text_input("City")
                    state = c_state.text_input(s_lbl_st)
                    zip_code = c_zip.text_input(s_lbl_zip)
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.form_submit_button("Create Account", type="primary", use_container_width=True):
                        
                        # --- FIX: AUTOFILL DETECTION ---
                        if not name or not addr or not city or not state or not zip_code:
                             st.error("⚠️ **Missing Info:** Some fields appear empty. If you used autofill, please click inside the boxes to ensure they are saved.")
                        else:
                            addr_errors = validate_address(addr, city, state, zip_code, country_code)
                            if new_pass != confirm_pass: st.error("❌ Passwords do not match")
                            elif not new_email: st.error("❌ Email is required.")
                            elif addr_errors: 
                                for e in addr_errors: st.error(f"❌ {e}")
                            else:
                                with st.spinner("Creating account..."):
                                    # --- PASS SELECTED LANGUAGE ---
                                    res, err = signup_func(
                                        new_email, new_pass, name, 
                                        addr, addr2, city, state, zip_code, country_code, 
                                        language  # <--- No longer hardcoded "English"
                                    )
                                    
                                    if res:
                                        st.success("✅ Account created! Please check your email or log in.")
                                    elif err:
                                        st.error(f"❌ Signup Failed: {err}")

    f1, f2, f3 = st.columns([1, 2, 1])
    with f2:
        if st.button("← Back to Home", type="secondary", use_container_width=True):
            st.session_state.app_mode = "splash"; st.rerun()

def show_forgot_password(send_code_func):
    c1, c2, c3 = st.columns([1, 1.5, 1])
    with c2:
        st.markdown("<h2 style='text-align: center; color: #2a5298 !important;'>Recovery 🔐</h2>", unsafe_allow_html=True)
        with st.container(border=True):
            st.info("Enter your email. We will send you a verification token.")
            email = st.text_input("Email Address", key="reset_email_input")
            if st.button("Send Token", type="primary", use_container_width=True):
                if email and send_code_func:
                    success, msg = send_code_func(email)
                    if success: st.session_state.reset_email = email; st.session_state.app_mode = "reset_verify"; st.rerun()
                    else: st.error(f"Error: {msg}")
                else: st.warning("Please enter your email")
            if st.button("Cancel", type="secondary", use_container_width=True):
                st.session_state.app_mode = "login"; st.rerun()

def show_reset_verify(verify_func):
    c1, c2, c3 = st.columns([1, 1.5, 1])
    with c2:
        st.markdown("<h2 style='text-align: center; color: #2a5298 !important;'>Set Password 🔑</h2>", unsafe_allow_html=True)
        with st.container(border=True):
            email = st.session_state.get("reset_email", "")
            st.success(f"Token sent to: **{email}**")
            token = st.text_input("Enter Token (from email)")
            new_pass = st.text_input("New Password", type="password")
            if st.button("Update Password", type="primary", use_container_width=True):
                if token and new_pass and verify_func:
                    success, msg = verify_func(email, token, new_pass)
                    if success:
                        st.success("✅ Password Updated! Please log in.")
                        if st.button("Go to Login"): st.session_state.app_mode = "login"; st.rerun()
                    else: st.error(f"Failed: {msg}")
                else: st.warning("Please enter token and new password")