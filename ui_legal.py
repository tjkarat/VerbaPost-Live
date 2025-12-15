import streamlit as st

def render_legal_page():
    st.markdown("## ⚖️ Legal & Privacy")
    
    st.info("VerbaPost is a privacy-first service. We do not sell your data.")

    tab_terms, tab_privacy = st.tabs(["Terms of Service", "Privacy Policy"])

    with tab_terms:
        st.markdown("""
        ### Terms of Service
        **Last Updated: December 2025**

        1. **Service Description**: VerbaPost provides physical mailing services for digital content.
        2. **User Responsibility**: You are responsible for the content of your letters. We reserve the right to refuse service for illegal or threatening content.
        3. **Delivery**: We utilize USPS for delivery. While we provide tracking where applicable, we are not liable for USPS delays or lost mail.
        4. **Refunds**: Orders can be refunded only if they have not yet been processed for printing. Once printed, orders are final.
        """)

    with tab_privacy:
        st.markdown("""
        ### Privacy Policy
        **Last Updated: December 2025**

        * **Data Retention**: We retain letter content only as long as necessary to fulfill the order and provide proof of delivery.
        * **AI Processing**: Audio recordings are processed via local AI or secure APIs for transcription. They are not used to train public models.
        * **Payment Data**: We do not store credit card numbers. All payments are processed securely via Stripe.
        * **Third Parties**: We share necessary address data with our print partner (PostGrid) solely for the purpose of fulfillment.
        """)

    st.markdown("---")
    if st.button("⬅️ Back to Home", type="primary"):
        st.session_state.app_mode = "splash"
        st.rerun()