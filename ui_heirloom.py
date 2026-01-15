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
    is_sponsored = (
        profile.get("role") in ["heir", "heirloom"] or 
        profile.get("created_by") is not None
    )

    if not is_sponsored:
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
        return

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
                        if audit_engine:
                            audit_engine.log_event(user_email, "Interview Started", metadata={"sid": sid, "target": clean_phone})
                        st.success(f"📞 Calling {target_phone} now...")
                    else:
                        st.error(f"Call Failed: {err}")

    st.divider()

    # --- SECTION 2: THE VAULT (INBOX) ---
    st.subheader("📂 Story Archive")
    
    if st.button("🔄 Check for New Stories"):
        with st.spinner("Syncing with Biographer..."):
            time.sleep(1) 
            st.rerun()

    drafts = database.get_user_drafts(user_email)
    heirloom_drafts = [d for d in drafts if d.get('tier') == 'Heirloom']
    
    if not heirloom_drafts:
        st.info("No stories recorded yet. Start an interview above!")
    else:
        for draft in heirloom_drafts:
            with st.container(border=True):
                c1, c2 = st.columns([3, 1])
                with c1:
                    st.markdown(f"**Recorded:** {draft.get('created_at', 'Unknown Date')}")
                with c2:
                    created_dt = draft.get('created_at')
                    if isinstance(created_dt, str):
                        try: created_dt = datetime.strptime(created_dt, "%Y-%m-%d %H:%M:%S")
                        except: created_dt = datetime.now()
                    
                    days_left = 30 - (datetime.now() - created_dt).days
                    if days_left > 0:
                        st.caption(f"⚠️ Expires in **{days_left} days**")
                    else:
                        st.caption("🔴 Archived (Offline)")

                audio_url = draft.get('tracking_number')
                if audio_url:
                     st.audio(audio_url)
                     
                     # --- 🔴 FIX: FAKE DOWNLOAD BUTTON REPLACED ---
                     # Using link_button for URL-based downloads
                     st.link_button(
                         label="⬇️ Download (.mp3)", 
                         url=audio_url,
                         help="Click to open the audio file in a new tab for saving."
                     )

                with st.expander("✍️ Edit Text & Mail Letter"):
                    new_text = st.text_area("Transcript", value=draft.get('content', ''), height=200, key=f"txt_{draft['id']}")
                    
                    if st.button("💾 Save Changes", key=f"save_{draft['id']}"):
                        database.update_draft(draft['id'], new_text)
                        st.toast("Changes Saved", icon="💾")
                    
                    st.divider()
                    
                    m_col1, m_col2 = st.columns([2, 1])
                    with m_col1:
                        st.caption(f"**Mailing to:** {profile.get('address_line1', 'No Address Set')}...")
                    with m_col2:
                        credits = profile.get('credits', 0)
                        if st.button(f"📮 Mail Letter ({CREDIT_COST} Credit)", key=f"mail_{draft['id']}", disabled=(credits < CREDIT_COST)):
                            
                            pdf_bytes = letter_format.create_pdf(
                                body_text=new_text,
                                to_addr=profile, 
                                from_addr=profile, 
                                advisor_firm=profile.get('advisor_firm', 'VerbaPost'),
                                audio_url=audio_url
                            )
                            
                            with st.spinner("Processing Manuscript..."):
                                letter_id = mailer.send_letter(
                                    pdf_bytes=pdf_bytes,
                                    to_addr=profile,
                                    from_addr=profile 
                                )
                                
                                if letter_id:
                                    new_credits = credits - CREDIT_COST
                                    database.update_user_credits(user_email, new_credits)
                                    database.mark_draft_sent(draft['id'], letter_id)
                                    
                                    # AUDIT LOG
                                    if audit_engine:
                                        audit_engine.log_event(user_email, "Letter Mailed", metadata={"draft_id": draft['id'], "letter_id": letter_id})
                                    
                                    st.toast("Manuscript Sent to Printing!", icon="📮")
                                    time.sleep(2)
                                    st.rerun()
                                else:
                                    st.error("Mailing Service Error. Please try again.")

    with st.expander("⚙️ Mailing Settings"):
        st.write("Ensure your mailing address is correct for the physical manuscript.")
        st.info("To update your mailing address, please visit the main Settings page.")