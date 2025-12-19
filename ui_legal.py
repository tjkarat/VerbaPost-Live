import streamlit as st

def render_legal_page():
    """
    Renders the Terms of Service and Privacy Policy.
    Maintains the Merriweather/Helvetica design system of VerbaPost.
    """
    # --- CSS INJECTION ---
    st.markdown("""
        <style>
        .legal-container { max-width: 800px; margin: 0 auto; padding: 2rem 1rem; font-family: 'Helvetica Neue', sans-serif; line-height: 1.6; color: #333; }
        .legal-header { font-family: 'Merriweather', serif; font-size: 2.5rem; font-weight: 700; border-bottom: 2px solid #eaeaea; padding-bottom: 1rem; margin-bottom: 2rem; }
        .legal-section { margin-bottom: 2rem; }
        .legal-title { font-weight: 700; text-transform: uppercase; letter-spacing: 1px; font-size: 0.9rem; color: #d93025; margin-bottom: 0.5rem; }
        .legal-text { font-size: 1rem; color: #555; margin-bottom: 1rem; }
        </style>
    """, unsafe_allow_html=True)

    # --- TOP NAVIGATION ---
    c_back1, c_back2, c_back3 = st.columns([1, 2, 1])
    with c_back2:
        if st.button("← Back to VerbaPost Home", use_container_width=True):
            st.session_state.app_mode = "splash"
            st.rerun()

    # --- CONTENT ---
    st.markdown('<div class="legal-container">', unsafe_allow_html=True)
    st.markdown('<div class="legal-header">Legal & Terms</div>', unsafe_allow_html=True)

    # 1. TERMS OF SERVICE
    st.markdown('<div class="legal-section">', unsafe_allow_html=True)
    st.markdown('<div class="legal-title">1. Terms of Service</div>', unsafe_allow_html=True)
    st.markdown("""
        <div class="legal-text">
            By using VerbaPost.com, you agree to our terms. We provide a platform for voice-to-letter transcription and physical mail fulfillment. 
            You are responsible for the content of your letters and ensuring the recipient's address is accurate.
        </div>
    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # 2. PRIVACY POLICY
    st.markdown('<div class="legal-section">', unsafe_allow_html=True)
    st.markdown('<div class="legal-title">2. Privacy & Data Security</div>', unsafe_allow_html=True)
    st.markdown("""
        <div class="legal-text">
            Your privacy is our core principle. 
            <ul>
                <li><strong>Transcription:</strong> Audio is processed via OpenAI Whisper and is not used for training models.</li>
                <li><strong>Storage:</strong> Drafts are stored securely in Supabase and are only accessible to you.</li>
                <li><strong>Mailing:</strong> PDF data is transmitted to PostGrid for printing and is deleted from their servers following fulfillment.</li>
            </ul>
        </div>
    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # 3. FULFILLMENT & REFUNDS
    st.markdown('<div class="legal-section">', unsafe_allow_html=True)
    st.markdown('<div class="legal-title">3. Fulfillment & Refunds</div>', unsafe_allow_html=True)
    st.markdown("""
        <div class="legal-text">
            Once a letter is dispatched to the USPS, we cannot cancel it or issue a refund. 
            If a letter is returned due to our error in printing, we will re-mail it at no additional cost. 
            VerbaPost is not responsible for USPS delivery delays or incorrect addresses provided by the user.
        </div>
    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # 4. CONTACT
    st.markdown('<div class="legal-section">', unsafe_allow_html=True)
    st.markdown('<div class="legal-title">4. Contact Information</div>', unsafe_allow_html=True)
    st.markdown("""
        <div class="legal-text">
            Questions regarding these terms should be directed to <strong>support@verbapost.com</strong>.
        </div>
    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True) # End legal-container

if __name__ == "__main__":
    render_legal_page()