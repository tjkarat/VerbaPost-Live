import streamlit as st

def show_legal():
    st.title("⚖️ Legal & Compliance")
    
    # --- FIX: Changed 'current_view' to 'app_mode' ---
    if st.button("⬅️ Back to Home", type="secondary"):
        st.session_state.app_mode = "splash"
        st.rerun()
        
    tab_privacy, tab_terms = st.tabs(["Privacy Policy", "Terms of Service"])
    
    with tab_privacy:
        st.markdown("""
        ### Privacy Policy
        **Effective Date:** November 23, 2025
        
        **1. Introduction**
        VerbaPost LLC ("we," "us," or "our") respects your privacy. This Privacy Policy explains how we collect, use, and protect your personal information when you use our voice-to-mail service.
        
        **2. Information We Collect**
        * **Personal Data:** Name, email address, and physical address for return mail.
        * **Recipient Data:** Names and physical addresses of the people you mail letters to.
        * **Content Data:** Audio recordings and transcribed text of your letters.
        * **Payment Data:** We use Stripe for payments. We do not store your full credit card number.
        
        **3. How We Use Your Data**
        * **Fulfillment:** We transmit your letter content and address data to our print partner (Lob/PostGrid) solely for the purpose of printing and mailing your physical document.
        * **Processing:** We use OpenAI's API to transcribe and polish your voice dictation.
        * **Civic Features:** We use Geocodio to identify your elected officials based on your address.
        
        **4. Data Sharing**
        We do not sell your data. We share data only with the following infrastructure providers to deliver the service:
        * **Stripe:** Payment processing.
        * **PostGrid:** Physical mail printing and delivery.
        * **OpenAI:** Audio transcription.
        * **Supabase:** Secure database storage.
        
        **5. Your Rights**
        You may request the deletion of your account and all associated data by emailing support@verbapost.com.
        
        **6. Contact Us**
        For privacy concerns, please contact: support@verbapost.com
        """)

    with tab_terms:
        st.markdown("""
        ### Terms of Service
        **Effective Date:** November 23, 2025
        
        **1. Acceptance of Terms**
        By using VerbaPost, you agree to these Terms. If you do not agree, do not use our service.
        
        **2. Description of Service**
        VerbaPost converts digital input (voice/text) into physical mail delivered via the US Postal Service. We are not the USPS and cannot guarantee delivery times once the mail is handed off to the postal carrier.
        
        **3. User Conduct**
        You agree NOT to use VerbaPost to send:
        * Threatening, harassing, or illegal content.
        * Content that violates a protective order.
        * Fraudulent materials or scams.
        * We reserve the right to block any user and cancel any order (with refund) if it violates these standards.
        
        **4. Payments & Refunds**
        * Payments are processed immediately upon order.
        * If a letter cannot be delivered due to an invalid address provided by you, we cannot offer a refund.
        * If our system fails to generate or mail your letter due to a technical error, we will provide a full refund.
        
        **5. Liability**
        VerbaPost LLC is not liable for any damages resulting from delayed, lost, or misdirected mail. Our liability is limited to the cost of the service paid.
        
        **6. Governing Law**
        These terms are governed by the laws of the State of Tennessee.
        """)
    
    st.divider()
    
    # Added a bottom button for convenience
    if st.button("⬅️ Return to Home Page", type="secondary", key="bot_home_btn"):
        st.session_state.app_mode = "splash"
        st.rerun()