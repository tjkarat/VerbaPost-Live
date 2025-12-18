import streamlit as st
import database
import ai_engine
import letter_format
import mailer  
import audit_engine 
import time
# REMOVED: import tempfile (No longer needed)
import os
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
            # Handle both dict (if raw SQL) and object (if ORM) access
            if isinstance(c, dict):
                name = c.get('name', 'Unknown')
                city = c.get('city', 'Unknown')
                street = c.get('street', '') or c.get('address_line1', '')
                state = c.get('state', '')
                zip_code = c.get('zip_code', '') or c.get('zip', '')
            else:
                name = getattr(c, 'name', 'Unknown')
                city = getattr(c, 'city', 'Unknown')
                street = getattr(c, 'street', '')
                state = getattr(c, 'state', '')
                zip_code = getattr(c, 'zip_code', '')

            label = f"{name} ({city})"
            options[label] = {
                "first_name": name,
                "address_line1": street,
                "city": city,
                "state": state,
                "country_code": "US",
                "zip": zip_code
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

    # --- PREPARE SENDER ADDRESS ---
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
            
            # --- NEW: PHONE NUMBER DISPLAY ---
            st.success("📞 **Story Line Number:** 1-615-656-7667")
            st.caption("Share this number with your parent. When they call, the story will appear in the 'Stories' tab.")

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

        with col2:
            st.metric("Stories Captured", len(drafts) if drafts else 0)
            st.metric("Next Letter Due", "Jan 15")

    # --- TAB: STORIES ---
    with tab_stories:
        st.header("📥 Inbox")
        
        # SYNC BUTTON
        if st.button("🔄 Check for New Stories"):
            with st.spinner("Checking phone line..."):
                p_phone = user_data.get('parent_phone')
                if not p_phone:
                    st.error("Please set Parent Phone in Settings.")
                else:
                    try:
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
                            st.warning(f"No new stories found. ({error if error else 'No recordings'})")
                    except Exception as e:
                        st.error(f"Sync Error: {e}")

        st.divider()

        if not drafts:
            st.info("No stories found. Waiting for Mom to call!")
        else:
            address_options = load_heirloom_contacts(user_email)
            
            for draft in drafts:
                draft_id = getattr(draft, 'id', None) or draft.get('id')
                content = getattr(draft, 'content', '') or draft.get('content', '')
                status = getattr(draft, 'status', 'draft') or draft.get('status', 'draft')
                raw_date = getattr(draft, 'created_at', None) or draft.get('created_at')
                date_str = raw_date.strftime("%B %d, %Y") if raw_date else "Unknown Date"
                icon = "✅" if "Sent" in status else "🎙️"
                
                with st.expander(f"{icon} {date_str} - {content[:40]}..."):
                    new_content = st.text_area("Edit", content, height=150, key=f"edit_{draft_id}")
                    
                    if st.button("💾 Save Changes", key=f"save_{draft_id}"):
                        database.update_draft_data(draft_id, content=new_content)
                        st.success("Saved!")
                        st.rerun()

                    st.divider()

                    selected_label = st.selectbox("Send To:", options=list(address_options.keys()), key=f"dest_{draft_id}")
                    raw_recipient = address_options.get(selected_label)
                    
                    if raw_recipient:
                        recipient_addr = {
                            "name": raw_recipient.get("first_name"),
                            "street": raw_recipient.get("address_line1"),
                            "city": raw_recipient.get("city"),
                            "state": raw_recipient.get("state"),
                            "zip_code": raw_recipient.get("zip")
                        }
                    else:
                        recipient_addr = {}

                    col_prev, col_mail = st.columns([1, 1])
                    
                    # --- PREVIEW (Addresses Shown) ---
                    with col_prev:
                        if st.button("📄 Preview PDF", key=f"prev_{draft_id}"):
                             pdf_bytes = letter_format.create_pdf(
                                 content=new_content, 
                                 to_addr=recipient_addr,
                                 from_addr=from_address,
                                 tier="Heirloom",
                                 date_str=date_str,
                                 clean_render=False # SHOW addresses for user preview
                             )
                             # STORE BYTES IN SESSION STATE
                             st.session_state[f"pdf_bytes_{draft_id}"] = pdf_bytes
                             st.rerun()

                    if f"pdf_bytes_{draft_id}" in st.session_state:
                        stored_bytes = st.session_state[f"pdf_bytes_{draft_id}"]
                        st.caption(f"✅ Preview Ready")
                        
                        with col_mail:
                            st.download_button("⬇️ Download PDF", data=stored_bytes, file_name="heirloom_letter.pdf", mime="application/pdf", key=f"dl_{draft_id}")
                            
                            if "Sent" not in status:
                                if st.button(f"🚀 Send (1 Credit)", key=f"send_{draft_id}"):
                                    if credits > 0:
                                        with st.spinner("Connecting to PostGrid..."):
                                            # RE-GENERATE CLEAN PDF (Addresses Hidden)
                                            # This prevents the 'Content overlap' error because
                                            # PostGrid will insert a blank cover page with addresses.
                                            clean_bytes = letter_format.create_pdf(
                                                content=new_content, 
                                                to_addr=recipient_addr,
                                                from_addr=from_address,
                                                tier="Heirloom",
                                                date_str=date_str,
                                                clean_render=True # HIDE addresses for mailing
                                            )
                                            
                                            letter_id = mailer.send_letter(
                                                clean_bytes, 
                                                recipient_addr, 
                                                from_address, 
                                                description=f"Heirloom: {date_str}"
                                            )
                                            if letter_id:
                                                database.decrement_user_credits(user_email)
                                                database.update_draft_data(draft_id, status=f"Sent: {letter_id}")
                                                
                                                # AUDIT LOG
                                                if audit_engine:
                                                    audit_engine.log_event(user_email, "LETTER_SENT", metadata={"id": letter_id, "tier": "Heirloom"})
                                                
                                                st.balloons()
                                                st.success(f"✅ Mailed! Tracking ID: {letter_id}")
                                                del st.session_state[f"pdf_bytes_{draft_id}"]
                                                time.sleep(2)
                                                st.rerun()
                                            else:
                                                st.error("Mailing Failed.")
                                    else:
                                        st.warning("⚠️ 0 Credits.")

    # --- TAB: SETTINGS (UPDATED) ---
    with tab_settings:
        st.write("### 👵 Parent Details")
        with st.form("heirloom_setup"):
            current_parent = user_data.get('parent_name', '') or ""
            current_phone = user_data.get('parent_phone', '') or ""
            p_name = st.text_input("Parent's Name", value=current_parent)
            p_phone = st.text_input("Parent's Phone Number", value=current_phone)
            if st.form_submit_button("Save Details"):
                if hasattr(database, 'update_heirloom_profile'):
                    if database.update_heirloom_profile(user_email, p_name, p_phone):
                        st.success("Details saved!")
                        time.sleep(1)
                        st.rerun()