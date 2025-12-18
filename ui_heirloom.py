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

    # --- CONFIGURE ADDRESSES ---
    # RECIPIENT: The Child (Logged-in User)
    recipient_addr = {
        "name": user_data.get("full_name"),
        "street": user_data.get("address_line1"),
        "city": user_data.get("address_city"),
        "state": user_data.get("address_state"),
        "zip_code": user_data.get("address_zip")
    }

    # SENDER: The Parent (Using User's address for return)
    parent_name = user_data.get('parent_name') or "Mom & Dad"
    from_address = {
        "name": parent_name,
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
            
            # PHONE NUMBER DISPLAY
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
                    
                    # Display the routing clearly
                    st.caption(f"📮 **To:** {recipient_addr.get('name', 'Unknown')} | **From:** {from_address.get('name', 'Mom & Dad')}")

                    # WARNING if address is missing
                    if not recipient_addr.get("street"):
                        st.warning("⚠️ Mailing Address Missing! Please go to Settings to add your address.")

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
                                    if not recipient_addr.get("street"):
                                        st.error("Cannot Send: Your mailing address is missing. Check Settings.")
                                    elif credits > 0:
                                        with st.spinner("Connecting to PostGrid..."):
                                            # RE-GENERATE CLEAN PDF (Addresses Hidden for Insert Page)
                                            clean_bytes = letter_format.create_pdf(
                                                content=new_content, 
                                                to_addr=recipient_addr,
                                                from_addr=from_address,
                                                tier="Heirloom",
                                                date_str=date_str,
                                                clean_render=True 
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

    # --- TAB: SETTINGS (CRITICAL FIX) ---
    with tab_settings:
        c1, c2 = st.columns(2)
        
        # 1. PARENT SETUP
        with c1:
            st.write("### 👵 Parent Details")
            st.caption("This allows the system to recognize who is calling.")
            with st.form("heirloom_parent"):
                current_parent = user_data.get('parent_name', '') or ""
                current_phone = user_data.get('parent_phone', '') or ""
                
                p_name = st.text_input("Parent's Name", value=current_parent, placeholder="Mom & Dad")
                p_phone = st.text_input("Parent's Phone Number", value=current_phone, placeholder="6155550100")
                
                if st.form_submit_button("Save Parent Info"):
                    if hasattr(database, 'update_heirloom_profile'):
                        if database.update_heirloom_profile(user_email, p_name, p_phone):
                            st.success("Saved!")
                            time.sleep(1)
                            st.rerun()
                            
        # 2. USER ADDRESS (THE "TO" ADDRESS)
        with c2:
            st.write("### 📬 Your Mailing Address")
            st.caption("Where should we send the physical letter?")
            with st.form("heirloom_me"):
                # Load current values safely
                my_name = user_data.get('full_name', '') or ""
                my_street = user_data.get('address_line1', '') or ""
                my_city = user_data.get('address_city', '') or ""
                my_state = user_data.get('address_state', '') or ""
                my_zip = user_data.get('address_zip', '') or ""

                u_name = st.text_input("Your Name", value=my_name)
                u_street = st.text_input("Street Address", value=my_street)
                u_city = st.text_input("City", value=my_city)
                
                cc1, cc2 = st.columns(2)
                u_state = cc1.text_input("State", value=my_state)
                u_zip = cc2.text_input("Zip Code", value=my_zip)

                if st.form_submit_button("Save My Address"):
                    # We reuse database.save_contact or create a new profile update function
                    # For now, assuming we can update the user profile directly via a DB call
                    if database.update_user_profile_address(user_email, u_name, u_street, u_city, u_state, u_zip):
                         st.success("Address Saved!")
                         time.sleep(1)
                         st.rerun()
                    else:
                        st.error("Save failed.")