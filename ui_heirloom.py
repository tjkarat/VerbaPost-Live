import streamlit as st
import database
import ai_engine
import letter_engine  # <--- NEW IMPORT for PDF generation
import time
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
                3. **You review:** You'll see the text here. Edit it, then click 'Preview PDF'.
                """
            )
        with col2:
            st.metric("Stories Captured", "0")
            st.metric("Next Letter Due", "Jan 15")

    # --- TAB: STORIES (The Inbox) ---
    with tab_stories:
        st.header("📥 Inbox")
        
        # 1. Fetch Drafts from Database
        drafts = database.get_user_drafts(user_email)
        
        if not drafts:
            st.info("No stories found. Upload a recording below or wait for Mom to call!")
        else:
            for draft in drafts:
                # Safe dictionary access
                content = draft.get('content', '') or ""
                created_at = draft.get('created_at')
                draft_id = draft.get('id')
                draft_status = draft.get('status', 'Draft')
                
                date_str = created_at.strftime("%b %d, %Y") if created_at else "Unknown Date"
                preview = content[:60] + "..." if content else "No content"
                
                # Expandable card for each story
                with st.expander(f"🎙️ {date_str} - {preview}"):
                    st.caption(f"ID: {draft_id} | Status: {draft_status}")
                    
                    # EDITOR
                    new_content = st.text_area(
                        "Edit Transcript", 
                        value=content, 
                        height=200,
                        key=f"editor_{draft_id}"
                    )
                    
                    col_save, col_print = st.columns([1, 4])
                    
                    # SAVE BUTTON
                    with col_save:
                        if st.button("💾 Save", key=f"save_{draft_id}"):
                            database.update_draft_data(draft_id, content=new_content)
                            st.success("Saved!")
                            time.sleep(1)
                            st.rerun()
                            
                    # PRINT / GENERATE PDF SECTION
                    with col_print:
                        # 1. Generate PDF Button
                        if st.button("📄 Preview PDF", key=f"gen_{draft_id}"):
                            try:
                                # Get user first name for the letter salutation
                                full_name = user.get('full_name', 'Family')
                                recipient_name = full_name.split(" ")[0]
                                
                                # Call the engine
                                pdf_path = letter_engine.create_pdf(
                                    text_content=new_content,
                                    recipient_name=recipient_name,
                                    date_str=date_str
                                )
                                
                                # Save path to session state so download button persists
                                st.session_state[f"pdf_{draft_id}"] = pdf_path
                                st.rerun()
                                
                            except Exception as e:
                                st.error(f"PDF Error: {e}")

                        # 2. Download Button (Only shows if PDF exists)
                        if f"pdf_{draft_id}" in st.session_state:
                            pdf_file = st.session_state[f"pdf_{draft_id}"]
                            
                            # Read file binary for download
                            try:
                                with open(pdf_file, "rb") as f:
                                    st.download_button(
                                        label="⬇️ Download Letter",
                                        data=f,
                                        file_name=f"Letter_{draft_id}.pdf",
                                        mime="application/pdf",
                                        key=f"dl_{draft_id}"
                                    )
                                
                                # 3. Send via PostGrid (Mockup)
                                if st.button("📮 Send via Mail ($0.80)", key=f"send_{draft_id}"):
                                    with st.spinner("Connecting to PostGrid..."):
                                        time.sleep(1.5)
                                        st.success("Sent to printer!")
                                        # Future: database.update_status(draft_id, 'Sent')
                            except FileNotFoundError:
                                st.warning("PDF expired. Click 'Preview PDF' again.")

        # --- MANUAL UPLOAD ---
        st.markdown("---")
        with st.expander("🛠️ Admin: Upload Audio Manually"):
            uploaded_file = st.file_uploader("Upload MP3/WAV", type=['mp3', 'wav', 'm4a'], key="heirloom_uploader")
            
            if uploaded_file and st.button("Transcribe & Save", key="heirloom_btn"):
                with st.spinner("🎧 AI is listening to Mom..."):
                    try:
                        transcription = ai_engine.transcribe_audio(uploaded_file)
                        if transcription:
                            database.save_draft(
                                user_email=user_email,
                                content=transcription,
                                tier="Heirloom",
                                price=0.0
                            )
                            st.success("✅ Story captured!")
                            time.sleep(1)
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
                    st.error("Missing function: update_heirloom_profile")