import streamlit as st
import database
import ai_engine
from datetime import datetime

def render_dashboard():
    """
    The Main Heirloom Dashboard.
    """
    
    # 1. GET USER DATA
    user_email = st.session_state.get("user_email")
    if not user_email:
        st.error("Please log in.")
        return

    # Fetch profile
    user = database.get_user_profile(user_email)
    
    # 2. HEADER
    st.markdown("## 🕰️ The Family Archive")
    
    if not user:
        st.error("User profile not found.")
        return

    # 3. TABS
    tab_overview, tab_stories, tab_settings = st.tabs(["🏠 Overview", "📖 Stories", "⚙️ Settings"])

    # --- TAB: OVERVIEW ---
    with tab_overview:
        col1, col2 = st.columns([2, 1])
        with col1:
            full_name = user.get('full_name', 'User')
            first_name = full_name.split(" ")[0] if full_name else "User"
            
            st.info(f"Welcome back, {first_name}. Your Story Line is active.")
            st.markdown(
                """
                ### 📞 How it works
                1. **Tell Mom to call:** `(615) 555-0199` (Your Twilio Number)
                2. **She talks:** We record her story.
                3. **You review:** You'll see the text here. Edit it, then click 'Print'.
                """
            )
        with col2:
            st.metric("Stories Captured", "0")
            st.metric("Next Letter Due", "Jan 15")

    # --- TAB: STORIES (The Inbox) ---
    with tab_stories:
        st.write("### 📥 Incoming Stories")
        
        # In the future, we will list database rows here.
        # For now, we show the manual uploader.
        
        st.markdown("---")
        with st.expander("🛠️ Admin: Upload Audio Manually", expanded=True):
            # Ensure unique key just in case
            uploaded_file = st.file_uploader("Upload MP3/WAV", type=['mp3', 'wav', 'm4a'], key="heirloom_uploader")
            
            if uploaded_file and st.button("Transcribe & Save", key="heirloom_btn"):
                with st.spinner("🎧 AI is listening to Mom..."):
                    try:
                        # 1. Transcribe
                        transcription = ai_engine.transcribe_audio(uploaded_file)
                        
                        if transcription:
                            # 2. Save to drafts
                            database.save_draft(
                                user_email=user_email,
                                content=transcription,
                                tier="Heirloom",
                                price=0.0
                            )
                            st.success("✅ Story captured! Check your drafts.")
                            time.sleep(1) # Give user time to see success
                            st.rerun()
                        else:
                            st.error("AI returned empty text.")
                            
                    except Exception as e:
                        st.error(f"Error processing audio: {e}")

    # --- TAB: SETTINGS ---
    with tab_settings:
        st.write("### 👵 Parent Details")
        with st.form("heirloom_setup"):
            current_parent = user.get('parent_name', '') or ""
            current_phone = user.get('parent_phone', '') or ""

            p_name = st.text_input("Parent's Name", value=current_parent, placeholder="e.g. Grandma Mary")
            p_phone = st.text_input("Parent's Phone Number", value=current_phone, placeholder="e.g. +1615...")
            
            if st.form_submit_button("Save Details"):
                if hasattr(database, 'update_heirloom_profile'):
                    success = database.update_heirloom_profile(user_email, p_name, p_phone)
                    if success:
                        st.success("Saved!")
                        st.rerun()
                    else:
                        st.error("Database update failed.")
                else:
                    st.error("Missing function: update_heirloom_profile in database.py")