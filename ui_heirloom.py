import streamlit as st
import time
from datetime import datetime, timedelta
import database
import ai_engine
import mailer
import email_engine # New import for prep emails
import letter_format

# --- CONFIGURATION ---
CREDIT_COST = 1 

def render_dashboard():
    """
    The Family Legacy Archive (B2B Mode).
    Features: Audio Player, 30-Day Countdown, Download, and Interview Trigger.
    """
    if not st.session_state.get("authenticated"):
        st.warning("Please log in to access the Family Archive.")
        return

    user_email = st.session_state.user_email
    profile = database.get_user_profile(user_email)
    
    if not profile:
        st.error("Profile not found.")
        return

    # --- 🔒 THE GATE: CHECK SPONSORSHIP ---
    # We check if they have a specific role OR if they were created by an advisor
    is_sponsored = (
        profile.get("role") in ["heir", "heirloom"] or 
        profile.get("created_by") is not None
    )

    if not is_sponsored:
        # RENDER BLOCKED STATE
        st.title("🏛️ The Family Legacy Project")
        st.divider()
        st.info("🔒 Account Verification Pending")
        st.markdown(f"""
        **Welcome to VerbaPost.**
        
        Your account is currently in **Guest Mode**. To unlock the Family Archive and start recording stories, 
        your account must be activated by your sponsoring financial advisor.
        
        **What to do:**
        1. Contact your advisor to confirm your invitation.
        2. Ask them to "Activate" your email address: `{user_email}`.
        3. Refresh this page once confirmed.
        """)
        if st.button("🔄 Refresh Status"):
            st.rerun()
        return  # <--- STOP RENDERING THE REST OF THE DASHBOARD

    # --- IF SPONSORED, CONTINUE TO DASHBOARD ---

    # --- HEADER & INSTRUCTIONS ---
    st.title("🏛️ The Family Legacy Project")
    advisor_firm = profile.get("advisor_firm", "VerbaPost Wealth")
    st.caption(f"Sponsored by {advisor_firm}")
    
    with st.expander("📝 HOW TO CAPTURE A STORY (Read First)", expanded=True):
        st.markdown("""
        **1. Prepare the Interviewee:** Enter their email below to send them the question in advance.
        **2. Start the Interview:** Click **'Send Request & Call'**. Our AI Biographer will call them immediately.
        **3. Save & Share:** The recording will appear below. You have **30 days** to download the master file or mail the keepsake letter.
        """)

    st.divider()

    # --- SECTION 1: THE INTERVIEW STATION ---
    st.subheader("🎙️ Start a New Interview")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Default to parent phone if saved, otherwise empty
        default_phone = profile.get("parent_phone", "")
        target_phone = st.text_input("Interviewee Phone Number", value=default_phone, help="The number we will call.")
        
        # NEW: Explicit Email Field for the Senior
        target_email = st.text_input("Interviewee Email", placeholder="grandma@example.com", help="We send the prep email here.")
        
    with col2:
        custom_question = st.text_area("Interview Question", value="Please share a favorite memory from your childhood.", height=100)
        
    if st.button("🚀 Send Request & Call Now", use_container_width=True):
        if not target_phone or len(target_phone) < 10:
            st.error("⚠️ Please enter a valid phone number.")
        elif not target_email:
            st.error("⚠️ Please enter the Interviewee's email for the prep notification.")
        else:
            with st.spinner("📧 Sending Prep Email..."):
                # 1. Send Email to the SENIOR (Interviewee)
                advisor_name = profile.get("advisor_firm") or "Your Advisor"
                email_sent = email_engine.send_interview_prep_email(target_email, advisor_name, custom_question)
                
                if email_sent:
                    st.toast("✅ Prep Email Sent!", icon="📧")
                    time.sleep(1)
                    
                    with st.spinner("☎️ Connecting AI Biographer..."):
                        # 2. Trigger Call (Passing the Custom Question)
                        sid, err = ai_engine.trigger_outbound_call(
                            to_phone=target_phone,
                            advisor_name=advisor_name,
                            firm_name=profile.get("advisor_firm", "VerbaPost"),
                            project_id=profile.get("id"), # Use User ID as Project ID
                            question_text=custom_question
                        )
                        
                        if sid:
                            st.success(f"📞 Calling {target_phone} now...")
                        else:
                            st.error(f"Call Failed: {err}")
                else:
                    st.error("Failed to send prep email. Check email address.")

    st.divider()

    # --- SECTION 2: THE VAULT (INBOX) ---
    st.subheader("📂 Story Archive")
    
    # Refresh Button
    if st.button("🔄 Check for New Stories"):
        with st.spinner("Syncing with Biographer..."):
            # Trigger logic to fetch from Twilio (Implementation in ai_engine logic)
            # For B2B MVP, we assume webhooks push to DB, or we poll here.
            # Using existing ai_engine polling if available, or just refreshing DB.
            time.sleep(1) 
            st.rerun()

    # Fetch Drafts
    drafts = database.get_user_drafts(user_email)
    heirloom_drafts = [d for d in drafts if d.get('tier') == 'Heirloom']
    
    if not heirloom_drafts:
        st.info("No stories recorded yet. Start an interview above!")
    else:
        for draft in heirloom_drafts:
            with st.container(border=True):
                # Header
                c1, c2 = st.columns([3, 1])
                with c1:
                    st.markdown(f"**Recorded:** {draft.get('created_at', 'Unknown Date')}")
                with c2:
                    # 30-DAY COUNTDOWN LOGIC
                    created_dt = draft.get('created_at')
                    if isinstance(created_dt, str):
                        try: created_dt = datetime.strptime(created_dt, "%Y-%m-%d %H:%M:%S")
                        except: created_dt = datetime.now()
                    
                    days_left = 30 - (datetime.now() - created_dt).days
                    if days_left > 0:
                        st.caption(f"⚠️ Expires in **{days_left} days**")
                    else:
                        st.caption("🔴 Archived (Offline)")

                # Audio Player & Download
                audio_url = draft.get('tracking_number') # Storing audio_ref in tracking column for now
                if audio_url:
                     st.audio(audio_url)
                     # DOWNLOAD BUTTON (The "Golden Copy")
                     st.download_button(
                         label="⬇️ Download & Keep (.mp3)",
                         data=audio_url, # In real prod, this needs to be bytes. For URL, we provide link.
                         file_name=f"story_{draft['id']}.mp3",
                         mime="audio/mpeg",
                         help="Save this file to your computer. It will be deleted from the cloud in 30 days."
                     )

                # Edit & Mail Section
                with st.expander("✍️ Edit Text & Mail Letter"):
                    new_text = st.text_area("Transcript", value=draft.get('content', ''), height=200, key=f"txt_{draft['id']}")
                    
                    # Save Button
                    if st.button("💾 Save Changes", key=f"save_{draft['id']}"):
                        database.update_draft(draft['id'], new_text)
                        st.toast("Changes Saved", icon="💾")
                    
                    st.divider()
                    
                    # MAILING SECTION
                    m_col1, m_col2 = st.columns([2, 1])
                    with m_col1:
                        st.caption(f"**Mailing to:** {profile.get('address_line1', 'No Address Set')}...")
                    with m_col2:
                        credits = profile.get('credits', 0)
                        if st.button(f"📮 Mail Letter ({CREDIT_COST} Credit)", key=f"mail_{draft['id']}", disabled=(credits < CREDIT_COST)):
                            
                            # 1. Generate PDF (Manuscript Format)
                            pdf_bytes = letter_format.create_pdf(
                                body_text=new_text,
                                to_addr=profile, # Sends to User (Heir)
                                from_addr=profile, # "Storyteller" Name comes from Profile Name
                                advisor_firm=profile.get('advisor_firm', 'VerbaPost'),
                                audio_url=audio_url
                            )
                            
                            # 2. Send via PostGrid
                            with st.spinner("Processing Manuscript..."):
                                letter_id = mailer.send_letter(
                                    pdf_bytes=pdf_bytes,
                                    to_addr=profile,
                                    from_addr=profile # Return address is Advisor (mapped in mailer/format)
                                )
                                
                                if letter_id:
                                    # 3. Deduct Credit & Log
                                    new_credits = credits - CREDIT_COST
                                    database.update_user_credits(user_email, new_credits)
                                    database.mark_draft_sent(draft['id'], letter_id)
                                    
                                    # 4. Success Toast (No Balloons)
                                    st.toast("Manuscript Sent to Printing!", icon="📮")
                                    time.sleep(2)
                                    st.rerun()
                                else:
                                    st.error("Mailing Service Error. Please try again.")

    # --- SETTINGS (Address Book) ---
    with st.expander("⚙️ Mailing Settings"):
        st.write("Ensure your mailing address is correct for the physical manuscript.")
        # Simple inputs to update profile address if needed
        # (Implementation relies on existing profile update logic or ui_main)
        st.info("To update your mailing address, please visit the main Settings page.")