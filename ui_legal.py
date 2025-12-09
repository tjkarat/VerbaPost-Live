import streamlit as st

def show_legal():
    st.title("⚖️ Legal & Privacy")
    st.markdown("Last Updated: December 8, 2025")

    tab1, tab2, tab3 = st.tabs(["Privacy Policy", "Terms of Service", "Acceptable Use"])

    with tab1:
        st.header("Privacy Policy")
        st.write("We respect your privacy. We do not sell your data. We only use your data to print and mail your letters.")
        
        st.markdown("""
        **1. Data Collection:** We collect your email, name, and address to facilitate account creation and letter delivery. We also collect the content of your letters for printing purposes.
        
        **2. Data Usage:** We use your data to:
        * Create and manage your account.
        * Process your payments securely via Stripe.
        * Print and mail your letters via our third-party print partner, PostGrid.
        * Improve our services and communicate with you about your account.

        **3. Data Sharing:** We do not sell your personal data to third parties. We share data only with trusted partners (Stripe, PostGrid, OpenAI) as necessary to provide our services.
        
        **4. Security:** We employ industry-standard security measures to protect your data. However, no method of transmission over the internet is 100% secure.
        """)

    with tab2:
        st.header("Terms of Service")
        st.write("By using VerbaPost, you agree to the following terms:")
        
        st.markdown("""
        **1. Acceptance of Terms:** By accessing or using VerbaPost, you agree to be bound by these Terms of Service.

        **2. Services:** VerbaPost provides a platform for dictating and sending physical mail. We reserve the right to modify or discontinue the service at any time.

        **3. Payment:** You agree to pay all fees associated with your use of the service. Payments are processed securely via Stripe.

        **4. User Conduct:** You agree to use VerbaPost only for lawful purposes. You are responsible for the content of your letters.
        
        **5. Limitation of Liability:** VerbaPost shall not be liable for any indirect, incidental, special, consequential or punitive damages, including without limitation, loss of profits, data, use, goodwill, or other intangible losses.
        """)

    with tab3:
        st.header("Acceptable Use")
        st.write("By using VerbaPost, you agree NOT to:")
        st.markdown("""
        * Send mail containing threats of violence or illegal activities.
        * Use the service for fraud or "phishing" via physical mail.
        * Harass individuals or organizations.
        * Send spam or unsolicited bulk mail.
        """)
        st.warning("Violation of these terms will result in immediate account termination.")

    st.markdown("---")
    
    # --- FIXED NAVIGATION BUTTON ---
    if st.button("⬅️ Return to Home", use_container_width=True, key="legal_home_btn"):
        st.session_state.app_mode = "splash"
        st.rerun()