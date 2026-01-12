import streamlit as st

def render_heir_vault(archive_id):
    st.title("📂 Your Family Archive")
    st.markdown("### A Message Preserved Forever")
    
    # Emotional Hook: Listen to the voice
    st.info("You have a physical letter in your hands, but the heart of the legacy is the voice.")
    
    if st.button("🎧 Claim Archive & Listen to Audio"):
        # The Conversion Event: Heir signs up
        st.session_state.app_mode = "signup"
        st.session_state.claim_id = archive_id
        st.rerun()

    st.divider()
    st.caption("This digital vault is maintained and secured by VerbaPost in partnership with your family's advisor.")
