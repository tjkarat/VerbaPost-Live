import streamlit as st
import database

def render_heir_vault(project_id):
    """
    Landing page for Heirs to claim their digital archive.
    Secured by the unique Project UUID.
    """
    if not project_id:
        st.error("No archive ID found. Please scan the QR code on your physical letter.")
        return

    # Fetch family context from the additive database models
    project = database.get_project_by_id(project_id)
    if not project:
        st.error("Archive not found. Please verify the link or contact the sender's advisor.")
        return

    # Warm, legacy-focused branding
    st.markdown(f"""
        <div style='text-align: center; padding-top: 30px;'>
            <h1 style='font-family: serif; color: #0f172a;'>Your Family Archive</h1>
            <p style='color: #64748b; font-size: 1.1rem;'>Preserved by <b>{project.get('firm_name')}</b></p>
        </div>
    """, unsafe_allow_html=True)

    st.divider()

    # The Message
    st.markdown(f"### Welcome, {project.get('heir_name')}")
    st.write(f"""
        You have received a physical Legacy Letter from **{project.get('parent_name')}**. 
        This digital vault contains the original audio recording of those stories, 
        ensuring your parent's voice is preserved forever.
    """)

    # The Conversion Hook: "Claiming" the Vault for Wealth Retention
    with st.container(border=True):
        st.markdown("#### 🎧 Listen to the Voice")
        st.write("To protect your family's privacy, please claim this archive to unlock the audio recording.")
        
        if st.button("🔓 Claim Archive & Listen", use_container_width=True, type="primary"):
            # This triggers a signup flow that tags the heir to the advisor
            st.session_state.app_mode = "heir_signup"
            st.session_state.target_project = project_id
            st.rerun()

    st.caption(f"Securely hosted by VerbaPost in partnership with {project.get('firm_name')}.")