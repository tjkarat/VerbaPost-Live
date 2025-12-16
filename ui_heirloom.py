import streamlit as st
import database
import ai_engine
import letter_engine
import postgrid_engine
import time

def render_dashboard():
    user_email = st.session_state.get("user_email")
    if not user_email:
        st.error("Please log in.")
        return

    # Fetch profile (with credits, parent info, prompt)
    user_data = database.get_user_profile(user_email)
    if not user_data:
        st.error("Profile not found.")
        return
        
    credits = user_data.get("credits_remaining", 4)

    # --- 🚨 FIX: FETCH DRAFTS HERE (Global Scope for this function) ---
    # This ensures both the Overview tab and Stories tab can see 'drafts'
    drafts = database.get_user_drafts(user_email)
    # ------------------------------------------------------------------

    # --- HEADER ---
    col_head, col_cred = st.columns([3, 1])
    with col_head:
        st.markdown("## 🕰️ The Family Archive")
    with col_cred:
        st.metric("💌 Letter Credits", f"{credits}/4")

    # --- TABS ---
    tab_overview, tab_stories, tab_settings = st.tabs(["🏠 Overview", "📖 Stories", "⚙️ Settings"])

    # --- TAB: OVERVIEW (AI DIRECTOR MODE) ---
    with tab_overview:
        col1, col2 = st.columns([2, 1])
        with col1:
            full_name = user_data.get('full_name', 'User')
            first_name = full_name.split(" ")[0] if full_name else "User"
            
            st.info(f"Welcome back, {first_name}. Your Story Line is active.")
            
            # THE AI DIRECTOR SECTION
            st.markdown("### 🎬 This Week's Topic")
            st.caption("This is what the AI will ask Mom when she calls.")
            
            # Fetch current prompt safely
            current_prompt = user_data.get("current_prompt") or "Tell me about your favorite childhood memory."
            
            # Editable Prompt Area
            new_prompt = st.text_area("AI Interview Question:", value=current_prompt, height=100)
            
            if st.button("Update Topic"):
                if hasattr(database, "update_user_prompt"):
                    success = database.update_user_prompt(user_email, new_prompt)
                    if success:
                        st.success("Topic updated! Next call will use this.")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Database update failed.")
                else:
                    st.error("Missing function in database.py.")

            st.markdown(
                """
                ---
                **Suggested Topics:**
                * *How did you meet Dad?*
                * *What was your first job like?*
                * *Tell me about the house you grew up in.*
                """
            )

        with col2:
            # Now 'drafts' is available here!
            st.metric("Stories Captured", len(drafts) if drafts else 0)
            st.metric("Next Letter Due", "Jan 15")

    # --- TAB: STORIES (INBOX + SYNC) ---
    with tab_stories:
        st.header("📥 Inbox")
        
        # --- NEW: SYNC BUTTON (Connects Streamlit to Twilio) ---
        col_sync, col_status = st.columns([1, 3])
        with col_sync:
            if st.button("🔄 Check for New Stories"):
                with st.spinner("Checking phone line..."):
                    # 1. Get Parent Phone
                    p_phone = user_data.get('parent_phone')
                    if not p_phone:
                        st.error("Please set Parent Phone in Settings.")
                    else:
                        # 2. Run the AI Engine
                        text, error = ai_engine.fetch_and_transcribe_latest_call(p_phone)
                        
                        if text:
                            # 3. Save to Database
                            import uuid
                            new_draft = database.LetterDraft(
                                id=str(uuid.uuid4()),
                                user_email=user_email,
                                content=text,
                                status="draft"
                            )
                            with database.get_db_session() as session:
                                session.add(new_draft)
                                session.commit()
                            
                            st.success("✨ New Story Found & Transcribed!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.warning(f"No new stories: {error}")

        st.divider()

        # --- DRAFT LIST ---
        # 'drafts' was already fetched at the top
        
        if not drafts:
            st.info("No stories found. Waiting for Mom to call!")
        else:
            for draft in drafts:
                draft_id = draft.get('id')
                content = draft.get('content', '')
                date_str = draft.get('created_at').strftime("%b %d, %Y")
                
                with st.expander(f"🎙️ {date_str} - {content[:40]}..."):
                    # EDIT AREA
                    new_content = st.text_area("Edit", content, height=150, key=f"edit_{draft_id}")
                    
                    col_save, col_prev = st.columns([1, 1])
                    
                    # 1. SAVE BUTTON
                    with col_save:
                        if st.button("💾 Save", key=f"save_{draft_id}"):
                            database.update_draft_data(draft_id, content=new_content)
                            st.success("Saved!")
                            st.rerun()
                    
                    # 2. PREVIEW PDF BUTTON
                    with col_prev:
                        if st.button("📄 Preview PDF", key=f"prev_{draft_id}"):
                             path = letter_engine.create_pdf(
                                 new_content, 
                                 user_data.get('full_name', 'Family').split()[0], 
                                 date_str
                             )
                             st.session_state[f"pdf_{draft_id}"] = path
                             st.rerun()

                    # 3. ACTION AREA (Download / Send)
                    if f"pdf_{draft_id}" in st.session_state:
                        pdf_path = st.session_state[f"pdf_{draft_id}"]
                        
                        col_dl, col_send = st.columns(2)
                        with col_dl:
                            with open(pdf_path, "rb") as f:
                                st.download_button(
                                    "⬇️ Download PDF", 
                                    f, 
                                    file_name="letter.pdf", 
                                    key=f"dl_{draft_id}"
                                )
                                
                        with col_send:
                            # SEND MAIL BUTTON (Cost: 1 Credit)
                            if st.button(f"📮 Send Mail (1 Credit)", key=f"send_{draft_id}"):
                                if credits > 0:
                                    with st.spinner("Dispatching to PostGrid..."):
                                        success, new_balance = database.decrement_user_credits(user_email)
                                        
                                        if success:
                                            # Using Profile Address (with fallback)
                                            recipient = {
                                                "first_name": user_data.get("full_name"),
                                                "address_line1": user_data.get("address_line1", "123 Main St"), 
                                                "city": user_data.get("address_city", "Nashville"), 
                                                "state": user_data.get("address_state", "TN"), 
                                                "country_code": "US"
                                            }
                                            
                                            result = postgrid_engine.send_letter(pdf_path, recipient)
                                            
                                            if result["success"]:
                                                st.balloons()
                                                st.success(f"✅ Sent! Credits left: {new_balance}")
                                                time.sleep(2)
                                                st.rerun()
                                            else:
                                                st.error(f"PostGrid Error: {result['error']}")
                                        else:
                                            st.error("Credit deduction failed.")
                                else:
                                    st.warning("⚠️ 0 Credits. Upgrade to send.")

    # --- TAB: SETTINGS ---
    with tab_settings:
        st.write("### 👵 Parent Details")
        st.info("The system uses the phone number below to recognize Mom when she calls.")
        
        with st.form("heirloom_setup"):
            current_parent = user_data.get('parent_name', '') or ""
            current_phone = user_data.get('parent_phone', '') or ""

            p_name = st.text_input("Parent's Name", value=current_parent)
            p_phone = st.text_input("Parent's Phone Number", value=current_phone, help="Use US format e.g. 615-555-1234")
            
            if st.form_submit_button("Save Details"):
                if hasattr(database, 'update_heirloom_profile'):
                    # This function in database.py handles the +1 formatting automatically
                    success = database.update_heirloom_profile(user_email, p_name, p_phone)
                    if success:
                        st.success("Details saved! Phone number formatted for Twilio.")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Save failed.")
                else:
                    st.error("Database function missing.")