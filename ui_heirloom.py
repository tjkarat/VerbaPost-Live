import streamlit as st
import database
import ai_engine
import letter_format
import postgrid_engine
import time
import tempfile # Added for PDF bridge
import os       # Added for safe file handling
from datetime import datetime

# --- HELPER: ADDRESS BOOK ---
def load_heirloom_contacts(user_email):
    """Fetches contacts and formats them for the dropdown."""
    try:
        contacts = database.get_contacts(user_email)
        options = {}
        # Option 1: The User's own profile (Default)
        user_profile = database.get_user_profile(user_email)
        if user_profile:
            label = f"Me ({user_profile.get('address_line1', 'No Address')})"
            options[label] = {
                "first_name": user_profile.get("full_name"),
                "address_line1": user_profile.get("address_line1"),
                "city": user_profile.get("address_city"),
                "state": user_profile.get("address_state"),
                "country_code": "US",
                "zip": user_profile.get("address_zip") 
            }
        
        # Option 2: Saved Contacts
        for c in contacts:
            name = c.get('name', 'Unknown')
            city = c.get('city', 'Unknown')
            label = f"{name} ({city})"
            options[label] = {
                "first_name": name,
                "address_line1": c.get("street"),
                "city": c.get("city"),
                "state": c.get("state"),
                "country_code": "US",
                "zip": c.get("zip_code")
            }
        return options
    except Exception as e:
        st.error(f"Error loading contacts: {e}")
        return {}

def render_dashboard():
    user_email = st.session_state.get("user_email")
    if not user_email:
        st.error("Please log in.")
        return

    # Fetch profile
    user_data = database.get_user_profile(user_email)
    if not user_data:
        st.error("Profile not found.")
        return
        
    credits = user_data.get("credits_remaining", 4)
    drafts = database.get_user_drafts(user_email)

    # --- PREPARE SENDER ADDRESS (Needed for PDF) ---
    from_address = {
        "name": user_data.get("full_name"),
        "street": user_data.get("address_line1"),
        "city": user_data.get("address_city"),
        "state": user_data.get("address_state"),
        "zip_code": user_data.get("address_zip")
    }

    # --- HEADER ---
    col_head, col_cred = st.columns([3, 1])
    with col_head:
        st.markdown("## 🕰️ The Family Archive")
    with col_cred:
        st.metric("💌 Letter Credits", f"{credits}/4")

    # --- TABS ---
    tab_overview, tab_stories, tab_settings = st.tabs(["🏠 Overview", "📖 Stories", "⚙️ Settings"])

    # --- TAB: OVERVIEW ---
    with tab_overview:
        col1, col2 = st.columns([2, 1])
        with col1:
            full_name = user_data.get('full_name', 'User')
            first_name = full_name.split(" ")[0] if full_name else "User"
            st.info(f"Welcome back, {first_name}. Your Story Line is active.")
            
            st.markdown("### 🎬 This Week's Topic")
            st.caption("This is what the AI will ask Mom when she calls.")
            
            current_prompt = user_data.get("current_prompt") or "Tell me about your favorite childhood memory."
            new_prompt = st.text_area("AI Interview Question:", value=current_prompt, height=100)
            
            if st.button("Update Topic"):
                if hasattr(database, "update_user_prompt"):
                    success = database.update_user_prompt(user_email, new_prompt)
                    if success:
                        st.success("Topic updated!")
                        time.sleep(1)
                        st.rerun()
                    else: st.error("Update failed.")
                else: st.error("Missing DB function.")

            st.markdown("""
                ---
                **Suggested Topics:**
                * *How did you meet Dad?*
                * *What was your first job like?*
                * *Tell me about the house you grew up in.*
            """)

        with col2:
            st.metric("Stories Captured", len(drafts) if drafts else 0)
            st.metric("Next Letter Due", "Jan 15")

    # --- TAB: STORIES (INBOX + SYNC) ---
    with tab_stories:
        st.header("📥 Inbox")
        
        # SYNC BUTTON
        col_sync, col_status = st.columns([1, 3])
        with col_sync:
            if st.button("🔄 Check for New Stories"):
                with st.spinner("Checking phone line..."):
                    p_phone = user_data.get('parent_phone')
                    if not p_phone:
                        st.error("Please set Parent Phone in Settings.")
                    else:
                        text, error = ai_engine.fetch_and_transcribe_latest_call(p_phone)
                        if text:
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
                            st.success("✨ New Story Found!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.warning(f"No new stories: {error}")

        st.divider()

        # DRAFT LIST
        if not drafts:
            st.info("No stories found. Waiting for Mom to call!")
        else:
            # 1. Load Address Book Options ONCE
            address_options = load_heirloom_contacts(user_email)
            
            for draft in drafts:
                draft_id = draft.get('id')
                content = draft.get('content', '')
                
                # Safe Date
                raw_date = draft.get('created_at')
                date_str = raw_date.strftime("%B %d, %Y") if raw_date else "Unknown Date"
                
                with st.expander(f"🎙️ {date_str} - {content[:40]}..."):
                    # EDIT CONTENT
                    new_content = st.text_area("Edit", content, height=150, key=f"edit_{draft_id}")
                    
                    if st.button("💾 Save Changes", key=f"save_{draft_id}"):
                        database.update_draft_data(draft_id, content=new_content)
                        st.success("Saved!")
                        st.rerun()

                    st.divider()

                    # SELECT RECIPIENT (Needed for PDF generation)
                    selected_label = st.selectbox(
                        "Send To:", 
                        options=list(address_options.keys()),
                        key=f"dest_{draft_id}"
                    )
                    
                    # Convert selected option back to address dict
                    raw_recipient = address_options.get(selected_label)
                    # Normalize keys for letter_format (needs 'name', 'street') vs PostGrid (needs 'first_name', 'address_line1')
                    recipient_addr = {
                        "name": raw_recipient.get("first_name"),
                        "street": raw_recipient.get("address_line1"),
                        "city": raw_recipient.get("city"),
                        "state": raw_recipient.get("state"),
                        "zip_code": raw_recipient.get("zip")
                    }

                    col_prev, col_mail = st.columns([1, 1])
                    
                    # PREVIEW PDF BUTTON
                    with col_prev:
                        if st.button("📄 Preview PDF", key=f"prev_{draft_id}"):
                             # FIX: letter_format now returns BYTES, not a path.
                             # We write to a temp file to maintain compatibility with downstream 'open()' logic.
                             pdf_bytes = letter_format.create_pdf(
                                 content=new_content, 
                                 to_addr=recipient_addr,
                                 from_addr=from_address,
                                 tier="Heirloom",
                                 date_str=date_str
                             )
                             
                             # Create Temp File Bridge
                             with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tf:
                                 tf.write(pdf_bytes)
                                 temp_path = tf.name
                             
                             st.session_state[f"pdf_{draft_id}"] = temp_path
                             st.rerun()

                    # MAIL/DOWNLOAD ACTION
                    if f"pdf_{draft_id}" in st.session_state:
                        pdf_path = st.session_state[f"pdf_{draft_id}"]
                        
                        # Only show if file actually still exists
                        if os.path.exists(pdf_path):
                            st.caption(f"Preview generated for: {recipient_addr['name']}")
                            
                            with col_mail:
                                # Download
                                # This logic (open) caused the crash because pdf_path was bytes. 
                                # Now it is a valid file path again.
                                with open(pdf_path, "rb") as f:
                                    st.download_button("⬇️ Download", f, file_name="letter.pdf", key=f"dl_{draft_id}")
                                
                                # Send
                                if st.button(f"🚀 Send (1 Credit)", key=f"send_{draft_id}"):
                                    if credits > 0:
                                        with st.spinner("Dispatching..."):
                                            success, new_balance = database.decrement_user_credits(user_email)
                                            
                                            if success:
                                                # Use raw_recipient for PostGrid (it has the right keys like address_line1)
                                                result = postgrid_engine.send_letter(pdf_path, raw_recipient)
                                                
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
                                        st.warning("⚠️ 0 Credits.")

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
                    success = database.update_heirloom_profile(user_email, p_name, p_phone)
                    if success:
                        st.success("Details saved!")
                        time.sleep(1)
                        st.rerun()
                    else: st.error("Save failed.")
                else: st.error("Database function missing.")