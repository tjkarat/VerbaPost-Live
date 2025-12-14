import streamlit as st

def render_legal_page():
    st.markdown("## ⚖️ Legal Information")
    
    tab1, tab2 = st.tabs(["Terms of Service", "Privacy Policy"])
    
    with tab1:
        st.markdown("### Terms of Service")
        st.markdown("""
        **1. Service Usage:** VerbaPost provides automated dictation and mailing services. By using this service, you agree not to transmit illegal, threatening, or harassing content.
        
        **2. Fulfillment:** We utilize third-party providers (PostGrid) for physical fulfillment. While we strictly monitor performance, VerbaPost is not liable for delays caused by the United States Postal Service (USPS).
        
        **3. Payments:** All payments are processed securely via Stripe. Refunds are issued at the sole discretion of VerbaPost management for failed deliveries.
        
        **4. Legacy Services:** "End of Life" letters are processed with high priority and certified tracking. It is the user's responsibility to ensure recipient addresses are current.
        """)
        
    with tab2:
        st.markdown("### Privacy Policy")
        st.markdown("""
        **1. Data Handling:** Your voice data and transcribed text are processed ephemeral. We do not use your personal correspondence to train public AI models.
        
        **2. Third Parties:** To fulfill your order, strictly necessary data (recipient address, PDF content) is transmitted via encrypted API to our print partner, PostGrid.
        
        **3. Audio Retention:** Audio files are deleted from our servers immediately after transcription processing is complete.
        
        **4. Contact:** For privacy concerns, contact support@verbapost.com.
        """)

    st.markdown("---")
    if st.button("⬅️ Return Home"):
        st.query_params.clear()
        st.session_state.app_mode = "splash"
        st.rerun()

# --- SAFETY ALIAS ---
# Prevents crash if main.py calls the wrong name
render_legal = render_legal_page