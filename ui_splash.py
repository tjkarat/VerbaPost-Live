import streamlit as st

def render_splash_page():
    st.markdown("""
        <div style='text-align: center; padding: 40px 0;'>
            <h1 style='font-family: "Helvetica Neue", serif; font-size: 3rem; font-weight: 700; color: #1f2937;'>
                VerbaPost Wealth
            </h1>
            <p style='font-size: 1.2rem; color: #4b5563; max-width: 600px; margin: 0 auto;'>
                The high-touch client retention platform for independent financial advisors.
            </p>
        </div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        with st.container(border=True):
            st.markdown("### 🏛️ Advisor Portal")
            st.write("Secure dashboard for managing client legacy outreach.")
            
            # --- FIX: Set Intent to 'advisor' before routing ---
            if st.button("Login as Advisor", use_container_width=True, type="primary"):
                st.query_params["role"] = "advisor"  # <--- Triggers Smart Routing in ui_login
                st.session_state.app_mode = "login"
                st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)

        with st.container(border=True):
            st.markdown("### 📜 Family Archive")
            st.write("Preserve family stories through voice-to-letter dictation.")
            if st.button("Access My Archive", use_container_width=True):
                st.session_state.app_mode = "heirloom"
                st.rerun()

    st.markdown("<br><br><hr>", unsafe_allow_html=True)
    col_l, col_r = st.columns([4, 1])
    col_l.caption("© 2026 VerbaPost Wealth Management Solutions.")
    if col_r.button("⚖️ Legal & Terms", use_container_width=True):
        st.session_state.app_mode = "legal"
        st.rerun()