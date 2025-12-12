import streamlit as st

def show_help():
    st.markdown("""
    <div style="text-align: center; margin-bottom: 30px;">
        <h1>❓ Help & FAQ</h1>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("← Back to Workspace"):
        # Check if they were logged in to decide where to send them
        if st.session_state.get("user_email"):
            st.session_state.app_mode = "workspace"
        else:
            st.session_state.app_mode = "splash"
        st.rerun()
        
    st.write("---")

    with st.expander("📝 How does dictation work?", expanded=True):
        st.write("""
        1. **Click Record:** Speak your letter clearly.
        2. **Wait for AI:** We transcribe your speech into text.
        3. **Refine:** Use our 'Professional' or 'Friendly' buttons to polish the grammar.
        """)

    with st.expander("💸 Pricing & Payments"):
        st.write("""
        * **Standard ($2.99):** Printed on standard paper, mailed USPS First Class.
        * **Heirloom ($5.99):** High-quality archival paper, wet-ink style font.
        * **Santa ($9.99):** Special North Pole postmark and festive paper.
        """)

    with st.expander("📮 Shipping & Delivery"):
        st.write("""
        * **USPS First Class:** Usually arrives in 3-5 business days.
        * **Global:** We mail to most countries (International option required).
        * **Tracking:** Available for bulk campaigns or Certified Mail only.
        """)
        
    with st.expander("🔒 Privacy & Security"):
        st.write("""
        * We encrypt all data in transit.
        * Your audio files are deleted immediately after transcription.
        * We do not sell your address data.
        """)
