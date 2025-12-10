import streamlit as st

def show_legal():
    st.markdown("""
    <div style="text-align: center; margin-bottom: 30px;">
        <h1 style="color: #2a5298;">⚖️ Legal & Privacy</h1>
    </div>
    """, unsafe_allow_html=True)

    # FIX: Clear params to break the loop
    if st.button("⬅️ Return to Home", use_container_width=True):
        st.session_state.app_mode = "splash"
        st.query_params.clear()
        st.rerun()

    with st.expander("Privacy Policy", expanded=True):
        st.markdown("""
        **1. Data Collection**
        We collect audio files solely for the purpose of transcription. Files are processed and then deleted from our servers.
        
        **2. Third Parties**
        We use Stripe for payments and PostGrid for physical mailing. Address data is shared with these providers strictly for fulfillment.
        """)

    with st.expander("Terms of Service"):
        st.markdown("""
        **1. Refunds**
        Refunds are available if a letter is not mailed due to system error. Once mailed, no refunds are possible.
        
        **2. Content**
        You are responsible for the content of your letters. We do not censor mail, but we reserve the right to refuse service for illegal content.
        """)