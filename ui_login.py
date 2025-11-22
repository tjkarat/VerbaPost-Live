cat <<EOF > ui_login.py
import streamlit as st
import auth_engine
import time

# FIX: Function accepts the 2 handlers passed by web_app.py
def show_login(handle_login, handle_signup): 
    
    # Layout Columns
    c1, c2, c3 = st.columns([1, 2, 1])
    
    with c2:
        st.title("VerbaPost 📮")
        st.subheader("Member Access")
        
        # Diagnostic: Check connection immediately but don't crash
        client, err = auth_engine.get_supabase_client()
        if err:
            st.error(f"⚠️ System Error: {err}")
            st.stop()

        # UI Logic: Decide which tab to show first
        default_idx = 1 if st.session_state.get('initial_mode', 'login') == 'signup' else 0
        
        # Safe Tab Rendering
        tab_login, tab_signup = st.tabs(["Log In", "Create Account"])
        
        # We manually select which content to show based on the default_idx if needed,
        # but Streamlit tabs handles clicking automatically. 
        # The 'index' param is unstable in cloud, so we let user click.
        
        # --- LOGIN TAB ---
        with tab_login:
            st.caption("Welcome back")
            l_email = st.text_input("Email", key="l_email")
            l_pass = st.text_input("Password", type="password", key="l_pass")
            
            if st.button("Log In", type="primary", use_container_width=True):
                with st.spinner("Verifying..."):
                    handle_login(l_email, l_pass)

        # --- SIGN UP TAB ---
        with tab_signup:
            st.caption("New Account")
            s_email = st.text_input("Email", key="s_email")
            s_pass = st.text_input("Password", type="password", key="s_pass")

            st.markdown("---")
            st.caption("Return Address (Saved for future letters)")

            s_name = st.text_input("Full Name", key="s_name")
            s_street = st.text_input("Street Address", key="s_street")
            c_a, c_b = st.columns(2)
            s_city = c_a.text_input("City", key="s_city")
            s_state = c_b.text_input("State", max_chars=2, key="s_state")
            s_zip = st.text_input("Zip Code", max_chars=5, key="s_zip")
            
            if st.button("Create Account", type="primary", use_container_width=True):
                if not (s_name and s_street and s_city and s_state and s_zip):
                    st.error("Please fill all address fields.")
                else:
                    with st.spinner("Creating account..."):
                        handle_signup(s_email, s_pass, s_name, s_street, s_city, s_state, s_zip)
        
        st.divider()
        if st.button("⬅️ Back to Home", type="secondary"):
            st.session_state.current_view = "splash"
            st.rerun()
EOF