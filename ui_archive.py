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

    # Fetch family context
    project = database.get_project_by_id(project_id)
    if not project:
        st.error("Archive not found. It may have been moved or the link is invalid.")
        return

    firm_name = project.get('firm_name', 'VerbaPost Wealth')
    
    # --- 🔴 FIX: SAFE NAME FALLBACK ---
    heir_name = project.get('heir_name')
    if not heir_name or heir_name == "None":
        heir_name = "Family Member"

    parent_name = project.get('parent_name') or "Your Loved One"

    # 2. BRANDED HEADER
    st.markdown(f"""
        <div style='text-align: center; padding-top: 30px;'>
            <h1 style='font-family: serif; color: #0f172a;'>Your Family Archive</h1>
            <p style='color: #64748b; font-size: 1.1rem;'>Preserved by <b>{firm_name}</b></p>
        </div>
    """, unsafe_allow_html=True)

    st.divider()

    # 3. THE MESSAGE
    st.markdown(f"### Welcome, {heir_name}")
    st.write(f"""
        You have received a physical Legacy Letter from **{parent_name}**. 
        This digital vault contains the original audio recording of those stories.
    """)

    # 4. THE VAULT PLAYER (Conditional)
    with st.container(border=True):
        st.markdown("#### 🎧 Voice Recording")
        
        # CHECK RELEASE STATUS
        if project.get('audio_released'):
            # UNLOCKED STATE
            # Try audio_ref first, fall back to tracking_number if it holds the URL
            audio_url = project.get('audio_ref') or project.get('tracking_number')
            
            if audio_url and "http" in audio_url:
                st.success("🔓 Audio Unlocked - Ready to Play")
                st.audio(audio_url, format="audio/mp3")
                st.balloons()
            else:
                st.warning("Audio file is pending upload or missing.")
        else:
            # LOCKED STATE
            st.info("🔒 This audio archive is currently secured.")
            st.markdown(f"""
            To protect family privacy, this recording is held in the **{firm_name}** secure vault.
            
            Please contact your advisor to request access.
            """)

    # 5. TRUST FOOTER
    st.markdown("---")
    st.caption(f"Securely hosted by VerbaPost in partnership with {firm_name}.")