import streamlit as st

def show_legal():
    st.title("⚖️ Legal & Privacy")
    st.markdown("Last Updated: December 8, 2025")

    tab1, tab2, tab3 = st.tabs(["Privacy Policy", "Terms of Service", "Acceptable Use"])

    with tab1:
        st.header("Privacy Policy")
        st.write("We respect your privacy. We do not sell your data. We only use your data to print and mail your letters.")
        st.info("Full privacy policy text goes here.")

    with tab2:
        st.header("Terms of Service")
        st.write("By using VerbaPost, you agree to pay for the services rendered.")
        st.info("Full terms text goes here.")

    with tab3:
        st.header("Acceptable Use")
        st.write("By using VerbaPost, you agree NOT to:")
        st.markdown("""
        * Send mail containing threats of violence or illegal activities.
        * Use the service for fraud or "phishing" via physical mail.
        * Harass individuals or organizations.
        """)
        st.warning("Violation of these terms will result in immediate account termination.")

    st.markdown("---")
    
    # --- FIXED NAVIGATION BUTTON ---
    if st.button("⬅️ Return to Home", use_container_width=True, key="legal_home_btn"):
        st.session_state.app_mode = "splash"
        st.rerun()