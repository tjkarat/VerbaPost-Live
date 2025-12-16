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

    # Fetch profile (Now includes credits!)
    user_data = database.get_user_profile(user_email)
    if not user_data:
        st.error("Profile not found.")
        return
        
    credits = user_data.get("credits_remaining", 4)

    # --- HEADER WITH CREDITS ---
    col_head, col_cred = st.columns([3, 1])
    with col_head:
        st.markdown("## 🕰️ The Family Archive")
    with col_cred:
        st.metric("💌 Letter Credits", f"{credits}/4")

    tab_overview, tab_stories, tab_settings = st.tabs(["🏠 Overview", "📖 Stories", "⚙️ Settings"])

    # --- TAB: OVERVIEW ---
# --- TAB: OVERVIEW ---
    with tab_overview:
        col1, col2 = st.columns([2, 1])
        with col1:
            full_name = user_data.get('full_name', 'User')
            first_name = full_name.split(" ")[0] if full_name else "User"
            
            st.info(f"Welcome back, {first_name}. Your Story Line is active.")
            
            # --- PHASE 2: THE AI DIRECTOR ---
            st.markdown("### 🎬 This Week's Topic")
            
            current_prompt = user_data.get("current_prompt", "Tell me about your favorite childhood memory.")
            
            # Editable Prompt Area
            new_prompt = st.text_area("When Mom calls, the AI will ask:", value=current_prompt, height=100)
            
            if st.button("Update Topic"):
                # We need a small helper in database.py to save this, or use raw SQL here for speed
                # Let's assume we add update_prompt to database.py next
                if hasattr(database, "update_user_prompt"):
                    database.update_user_prompt(user_email, new_prompt)
                    st.success("Topic updated! Next call will use this.")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.warning("Please update database.py first (Step 3).")

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
            st.metric("Stories Captured", len(drafts) if drafts else 0)
            st.metric("Next Letter Due", "Jan 15")
    # --- TAB: STORIES (Inbox) ---
    with tab_stories:
        st.header("📥 Inbox")
        drafts = database.get_user_drafts(user_email)
        
        if not drafts:
            st.info("No stories found. Waiting for Mom to call!")
        else:
            for draft in drafts:
                draft_id = draft.get('id')
                content = draft.get('content', '')
                date_str = draft.get('created_at').strftime("%b %d, %Y")
                
                with st.expander(f"🎙️ {date_str} - {content[:40]}..."):
                    new_content = st.text_area("Edit", content, height=150, key=f"edit_{draft_id}")
                    
                    # 1. SAVE
                    if st.button("💾 Save", key=f"save_{draft_id}"):
                        database.update_draft_data(draft_id, content=new_content)
                        st.success("Saved!")
                        st.rerun()
                        
                    # 2. PREVIEW PDF
                    if st.button("📄 Preview PDF", key=f"prev_{draft_id}"):
                         path = letter_engine.create_pdf(
                             new_content, 
                             user_data.get('full_name', 'Family').split()[0], 
                             date_str
                         )
                         st.session_state[f"pdf_{draft_id}"] = path
                         st.rerun()

                    # 3. ACTION AREA
                    if f"pdf_{draft_id}" in st.session_state:
                        pdf_path = st.session_state[f"pdf_{draft_id}"]
                        
                        col_dl, col_send = st.columns(2)
                        with col_dl:
                            with open(pdf_path, "rb") as f:
                                # FIX: Added 'key' argument to prevent Duplicate ID Error
                                st.download_button(
                                    "⬇️ Download PDF", 
                                    f, 
                                    file_name="letter.pdf", 
                                    key=f"dl_{draft_id}"
                                )
                                
                        with col_send:
                            if credits > 0:
                                if st.button(f"📮 Send Mail (1 Credit)", key=f"send_{draft_id}"):
                                    with st.spinner("Dispatching to PostGrid..."):
                                        success, new_balance = database.decrement_user_credits(user_email)
                                        
                                        if success:
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
        with st.form("heirloom_setup"):
            current_parent = user_data.get('parent_name', '') or ""
            current_phone = user_data.get('parent_phone', '') or ""

            p_name = st.text_input("Parent's Name", value=current_parent)
            p_phone = st.text_input("Parent's Phone Number", value=current_phone)
            
            if st.form_submit_button("Save Details"):
                if hasattr(database, 'update_heirloom_profile'):
                    database.update_heirloom_profile(user_email, p_name, p_phone)
                    st.success("Saved!")
                    st.rerun()