import streamlit as st
import database

def render_heir_vault(project_id):
    """
    The landing page for Heirs scanning their physical letter.
    Secured by the unique Project UUID.
    """
    # 1. VALIDATE PROJECT CONTEXT
    if not project_id:
        st.error("No archive ID found. Please scan the QR code on your physical letter.")
        return

    # Fetch family context from the un-refactored database
    project = database.get_project_by_id(project_id)
    if not project:
        st.error("Archive not found. It may have been moved or the link is invalid.")
        return

    # 2. BRANDED HEADER
    # Establishes the connection between the firm and the family legacy
    st.markdown(f"""
        <div style='text-align: center; padding-top: 30px;'>
            <h1 style='font-family: serif; color: #0f172a;'>Your Family Archive</h1>
            <p style='color: #64748b; font-size: 1.1rem;'>Preserved by <b>{project.get('firm_name')}</b></p>
        </div>
    """, unsafe_allow_html=True)

    st.divider()

    # 3. THE MESSAGE
    # Personalized greeting using data from the Advisor's authorized play
    st.markdown(f"### Welcome, {project.get('heir_name')}")
    st.write(f"""
        You have received a physical Legacy Letter from **{project.get('parent_name')}**. 
        This digital vault contains the original audio recording of those stories, 
        ensuring your parent's voice is preserved forever.
    """)

    # 4. THE RETENTION HOOK: CLAIMING THE VAULT
    # This is where the Heir becomes a digital lead for the Advisor
    with st.container(border=True):
        st.markdown("#### 🎧 Listen to the Voice")
        st.write("To protect your family's privacy, please claim this archive to unlock the audio recording.")
        
        if st.button("🔓 Claim Archive & Listen", use_container_width=True, type="primary"):
            # Redirect to signup to capture Heir contact info for the Advisor
            st.session_state.app_mode = "heir_signup"
            st.session_state.target_project = project_id
            st.rerun()

    # 5. TRUST FOOTER
    st.markdown("---")
    st.caption(f"Securely hosted by VerbaPost in partnership with {project.get('firm_name')}.")