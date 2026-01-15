import streamlit as st
import time
from datetime import datetime, timedelta
import database
import ai_engine
import mailer
import email_engine 
import letter_format
import audit_engine 

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
        **Step 1: Notify.** Send the 'Prep Email' so the interviewee knows the topic and the incoming phone number **(615) 656-7667**.
        **Step 2: Interview.** When they are ready, click 'Start Interview Call'.
        **Step 3: Preserve.** The recording will appear below within minutes.
        """)

    st.divider()

    # --- SECTION 1: THE INTERVIEW STATION ---
    st.subheader("🎙️ Start a New Interview")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Default to parent phone if saved, otherwise empty
        default_phone = profile.get("parent_phone", "")
        target_phone = st.text_input("Interviewee Phone Number", value=default_phone, help="The number we will call.")
        target_email = st.text_input("Interviewee Email", placeholder="grandma@example.com", help="We send the prep email here.")
        
    with col2:
        custom_question = st.text_area("Interview Question", value="Please share a favorite memory from your childhood.", height=100)
        
    # --- SPLIT ACTION BUTTONS ---
    btn_col1, btn_col2 = st.columns(2)
    
    # BUTTON 1: SEND EMAIL
    with btn_col1:
        if st.button("📧 Send Prep Email", use_container_width=True, help="Sends the question and heads-up to the interviewee."):
            if not target_email or "@" not in target_email:
                st.error("⚠️ Please enter a valid email address.")
            else:
                with st.spinner("Sending Notification..."):
                    advisor_name = profile.get("advisor_firm") or "Your Advisor"
                    email_sent = email_engine.send_interview_prep_email(target_email, advisor_name, custom_question)
                    
                    if email_sent:
                        if audit_engine:
                            audit_engine.log_event(user_email, "Prep Email Sent", metadata={"target": target_email})
                        st.toast("✅ Notification Sent!", icon="📧")
                    else:
                        st.error("Failed to send email. Please check the address.")

    # BUTTON 2: START CALL
    with btn_col2:
        if st.button("📞 Start Interview Call", use_container_width=True, type="primary", help="Triggers the phone call immediately."):
            # --- 🟡 FIX: PHONE SANITIZATION ---
            clean_phone = "".join(filter(str.isdigit, target_phone))
            
            if not clean_phone or len(clean_phone) < 10:
                st.error("⚠️ Please enter a valid 10-digit phone number (e.g., 6155550123).")
            else:
                with st.spinner("☎️ Connecting AI Biographer..."):
                    advisor_name = profile.get("advisor_firm") or "Your Advisor"
                    
                    sid, err = ai_engine.trigger_outbound_call(
                        to_phone=clean_phone, # Sending the clean digits
                        advisor_name=advisor_name,
                        firm_name=profile.get("advisor_firm", "VerbaPost"),
                        project_id=profile.get("id"), 
                        question_text=custom_question
                    )
                    
                    if sid:
                        # 🔴 CRITICAL FIX: Save Pending Draft with SID
                        database.create_draft(
                            user_email=user_email,
                            content="Waiting for recording...",
                            status="Pending",
                            call_sid=sid
                        )
                        
                        if audit_engine:
                            audit_engine.log_event(user_email, "Interview Started", metadata={"sid": sid, "target": clean_phone})
                        st.success(f"📞 Calling {target_phone} now... Call Initiated! System is listening for result.")
                    else:
                        st.error(f"Call Failed: {err}")

    st.divider()

    # --- SECTION 2: THE VAULT (INBOX) ---
    st.subheader("📂 Story Archive")
    
    # 🔴 CRITICAL FIX: POLLING LOGIC
    if st.button("🔄 Check for New Stories"):
        with st.spinner("Syncing with Biographer..."):
            # 1. Fetch Drafts that are Pending
            all_drafts = database.get_user_drafts(user_email)
            pending = [d for d in all_drafts if d.get('call_sid')]
            
            synced_count = 0
            for p in pending:
                sid = p.get('call_sid')
                # 2. Check Twilio via AI Engine
                text, url = ai_engine.find_and_transcribe_recording(sid)
                if text and url:
                    # 3. Update DB
                    database.update_draft_by_sid(sid, text, url)
                    synced_count += 1
            
            if synced_count > 0:
                st.success(f"Found {synced_count} new stories!")
            else:
                st.info("No new recordings found yet.")
            time.sleep(1)
            st.rerun()

    # Fetch Drafts
    drafts = database.get_user_drafts(user_email)
    # Filter for B2B drafts
    heirloom_drafts = [d for d in drafts if d.get('tier') == 'Heirloom' or d.get('project_type')]
    
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
                audio_url = draft.get('tracking_number') 
                if audio_url and "http" in audio_url:
                     st.audio(audio_url)
                     # Using link_button for URL-based downloads
                     st.link_button(
                         label="⬇️ Download (.mp3)", 
                         url=audio_url,
                         help="Click to open the audio file in a new tab for saving."
                     )
                elif draft.get('status') == 'Pending':
                    st.warning("⏳ Waiting for recording... click Refresh above.")

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
                            
                            # --- 🔴 MANUAL QUEUE LOGIC (No PostGrid) ---
                            with st.spinner("Queueing for Print..."):
                                try:
                                    # 1. Deduct Credit
                                    new_credits = credits - CREDIT_COST
                                    database.update_user_credits(user_email, new_credits)
                                    
                                    # 2. Set Status to 'Approved' (This makes it show up in Admin Console Queue)
                                    # We use update_project_details which takes (id, content, status)
                                    # Ensuring we pass the draft/project ID correctly
                                    database.update_project_details(draft['id'], status='Approved')
                                    
                                    # 3. Log
                                    if audit_engine:
                                        audit_engine.log_event(user_email, "Manual Print Queued", metadata={"draft_id": draft['id']})
                                    
                                    st.success("✅ Added to Print Queue! Your advisor will finalize fulfillment.")
                                    time.sleep(2)
                                    st.rerun()
                                    
                                except Exception as e:
                                    st.error(f"Error queueing order: {e}")

    # --- SETTINGS (Address Book) ---
    with st.expander("⚙️ Mailing Settings"):
        st.write("Ensure your mailing address is correct for the physical manuscript.")
        st.info("To update your mailing address, please visit the main Settings page.")