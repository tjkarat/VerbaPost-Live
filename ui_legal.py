import streamlit as st

def show_legal():
    # --- HEADER ---
    st.markdown("""
    <div style="text-align: center; margin-bottom: 30px;">
        <h1>⚖️ Legal & Privacy</h1>
        <p style="color: #666;">Last Updated: December 8, 2025</p>
    </div>
    """, unsafe_allow_html=True)

    # --- TABS ---
    tab1, tab2, tab3 = st.tabs(["Privacy Policy", "Terms of Service", "Acceptable Use"])

    with tab1:
        st.markdown("""
        ### Privacy Policy
        **1. Data Handling**
        We respect your privacy. Audio files uploaded to VerbaPost are processed solely for the purpose of transcription and letter generation.
        
        **2. Storage**
        * **Audio:** Deleted immediately after transcription.
        * **Transcripts:** Stored securely in our database to allow you to review and edit.
        * **Addresses:** Stored to facilitate mailing. We do not sell your address book.
        
        **3. Third Parties**
        We use trusted third-party vendors for specific functions:
        * **OpenAI:** For transcription and text refinement.
        * **PostGrid:** For physical printing and mailing.
        * **Stripe:** For secure payment processing.
        """)

    with tab2:
        st.markdown("""
        ### Terms of Service
        **1. Service Description**
        VerbaPost provides a service to convert digital audio into physical mail. We are not responsible for delays caused by the US Postal Service (USPS).
        
        **2. Refunds**
        * **Drafts:** You are not charged until you click "Pay & Send".
        * **Sent Letters:** Once a letter is sent to our printing partner, it cannot be cancelled or refunded.
        * **Errors:** If a system error prevents mailing after payment, a full refund will be issued.
        
        **3. User Responsibility**
        You are responsible for the content of your letters. We reserve the right to refuse service for content that is illegal, threatening, or harassing.
        """)

    with tab3:
        st.markdown("""
        ### Acceptable Use
        By using VerbaPost, you agree NOT to:
        * Send mail containing threats of violence or illegal activities.
        * Use the service for fraud or "phishing" via physical mail.
        * Harass individuals or organizations.
        
        **Violation of these terms will result in immediate account termination.**
        """)

    st.markdown("---")
    if st.button("⬅️ Return to Home", use_container_width=True):
        st.session_state.app_mode = "splash"
        st.rerun()