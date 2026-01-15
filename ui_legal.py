import streamlit as st

def render_legal_page():
    """
    Renders the Terms of Service and Privacy Policy.
    Updated for the B2B 'Family Legacy Project' model (30-Day Retention).
    """
    
    # Navigation Header
    col1, col2 = st.columns([1, 5])
    with col1:
        if st.button("⬅️ Back"):
            st.session_state.app_mode = "splash"
            st.rerun()
            
    st.title("📜 Terms of Service & Privacy Policy")
    st.caption("Last Updated: December 2025")
    
    st.divider()
    
    # --- SECTION 1: SERVICE DEFINITION ---
    st.header("1. The Service")
    st.markdown("""
    **VerbaPost** ("The Service") provides a legacy preservation platform known as **"The Family Legacy Project."** The Service includes:
    * Automated telephony interviews.
    * AI-powered transcription and formatting.
    * Production of physical manuscripts ("The Keepsake Letter").
    * Temporary digital hosting of media files.
    
    **Nature of Service:** VerbaPost acts as a **Production Studio**, not a permanent data storage facility. Our primary deliverable is the physical manuscript and the downloadable master media file.
    """)
    
    # --- SECTION 2: DATA RETENTION (THE 30-DAY RULE) ---
    st.header("2. Data Retention & Archival Policy")
    st.warning("""
    ⚠️ **IMPORTANT: 30-DAY ACTIVE WINDOW**
    
    VerbaPost guarantees active hosting of your media (audio recordings and digital transcripts) for a period of **30 days** from the date of creation.
    """)
    
    st.markdown("""
    **User Responsibility:**
    It is the sole responsibility of the User (The Heir or Interviewee) to **download and save** a local copy of their audio recordings and transcripts within this 30-day window.
    
    **Archival & Purging:**
    After 30 days, media files are automatically moved to "Cold Storage" or permanently purged to ensure client privacy and data security. VerbaPost is not liable for any data loss resulting from the failure to download content within the active window.
    """)

    # --- SECTION 3: INTELLECTUAL PROPERTY (B2B PROTECTION) ---
    st.header("3. Ownership & Advisor Role")
    st.markdown("""
    **Client Ownership:**
    The content created via the Service (including voice recordings, stories, and transcripts) remains the sole intellectual property of the **Interviewee** and their designated **Heir**.
    
    **The Advisor's Role:**
    If this Service was purchased or sponsored by a Financial Advisor or third-party professional ("The Quarterback"), said Advisor acts solely as a **facilitator**. The Advisor **does not** retain ownership rights to the family's personal stories or data.
    """)

    # --- SECTION 4: LIABILITY DISCLAIMER ---
    st.header("4. Legal Disclaimer")
    st.error("""
    🚫 **NOT A LEGAL DOCUMENT**
    
    VerbaPost services are for **keepsake, sentimental, and historical purposes only**. 
    
    * Letters, recordings, and transcripts produced by VerbaPost **DO NOT** constitute a legal will, testament, estate plan, or binding legal directive.
    * VerbaPost is not a law firm and does not provide legal advice.
    * Please consult a qualified attorney for all matters regarding estate planning and legal wills.
    """)

    # --- SECTION 5: PRIVACY ---
    st.header("5. Privacy & Security")
    st.markdown("""
    We take your privacy seriously.
    * **No Sale of Data:** We do not sell your personal information or voice data to third parties.
    * **Encryption:** All data is encrypted in transit and at rest.
    * **AI Processing:** We utilize third-party AI processors (OpenAI) solely for the purpose of transcription and formatting. Your data is not used to train public AI models.
    """)

    st.divider()
    st.caption("© 2025 VerbaPost. All Rights Reserved.")