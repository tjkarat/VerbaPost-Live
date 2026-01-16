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

# ==========================================
# 🎧 PUBLIC PLAYER (QR Code Access)
# ==========================================
def render_public_player(audio_id):
    """
    Public-facing player for QR code scans. 
    Does not require login.
    """
    # 1. Clean Layout for Mobile/Public
    st.markdown("""
        <style>
            header {visibility: hidden;}
            .block-container {padding-top: 3rem;}
            .stAudio {width: 100%;}
            .player-card {
                background-color: #f8fafc;
                padding: 20px;
                border-radius: 12px;
                border: 1px solid #e2e8f0;
                text-align: center;
            }
        </style>
    """, unsafe_allow_html=True)

    # 2. Header
    st.markdown("<div style='text-align: center; margin-bottom: 20px;'><h1>🎙️ The Family Legacy Archive</h1></div>", unsafe_allow_html=True)
    
    # 3. Resolve Audio URL (Logic for Demo vs Real DB)
    audio_url = None
    story_title = "Private Recording"
    story_date = "Unknown Date"
    storyteller = "Family Member"

    # NOTE: If your QR code contains ?play=demo, this works immediately.
    # Otherwise, it attempts to fetch from DB if you have a helper.
    if audio_id == "demo" or audio_id == "sample":
        audio_url = "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3"
        story_title = "Barnaby Jones - Childhood Memories"
        story_date = "January 16, 2026"
        storyteller = "Barnaby Jones"
    else:
        # Try to find the draft in the DB by tracking_number or ID
        # This assumes your DB has a way to get public URLs
        try:
            # Placeholder: In a real scenario, you'd look up the draft by ID
            # draft = database.get_draft_by_id(audio_id) 
            # if draft: ...
            st.warning(f"Note: Looking up secure recording ID: {audio_id}")
        except Exception:
            pass
    
    # 4. Render Player UI
    if audio_url:
        st.markdown(f"""
            <div class='player-card'>
                <h3 style='margin-top: 0; color: #0f172a;'>{story_title}</h3>
                <p style='color: #64748b; font-size: 0.9rem;'>Storyteller: <strong>{storyteller}</strong></p>
                <p style='color: #94a3b8; font-size: 0.8rem;'>Recorded: {story_date}</p>
            </div>
            <br>
        """, unsafe_allow_html=True)
        
        st.audio(audio_url, format="audio/mp3")
        
        st.markdown("---")
        
        # Call to Action
        st.markdown("""
            <div style='text-align: center; color: #64748b; font-size: 0.9rem;'>
                <em>Preserved by VerbaPost</em><br><br>
                <p>Do you have a story to tell?</p>
            </div>
        """, unsafe_allow_html=True)
        
        if st.button("Claim this Memory / Log In", use_container_width=True):
            # Clear the play param so the main router sends them to login next time
            st.query_params["nav"] = "login"
            st.rerun()
            
    else:
        st.error("⚠️ Audio file not found or access link expired.")
        if st.button("Return to Home"):
            st.query_params.clear()
            st.rerun()

# ==========================================
# 🏛️ AUTHENTICATED DASHBOARD
# ==========================================

def render_family_archive():
    """Alias function to ensure main.py calls the correct entry point."""
    render_dashboard()

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
        """)
        if st.button("🔄 Refresh Status"):
            st.rerun()
        return

    # --- IF SPONSORED, CONTINUE TO DASHBOARD ---

    # --- 🆕 ONBOARDING TRACKER (HEIR) ---
    drafts = database.get_user_drafts(user_email)
    heirloom_drafts = [d for d in drafts if d.get('tier') == 'Heirloom' or d.get('project_type')]
    
    has_phone = len(profile.get("parent_phone", "")) > 9
    has_stories = len(heirloom_drafts) > 0
    has_mailed = any(d.get('status') == 'Approved' or d.get('status') == 'Sent' for d in heirloom_drafts)
    
    h_msg = ""
    h_pct = 0
    if not has_phone:
        h_msg = "Step 1: Enter the Interviewee's Phone Number below."
        h_pct = 10
    elif has_phone and not has_stories:
        h_msg = "Step 2: Start an Interview Call to record a story."
        h_pct = 40
    elif has_stories and not has_mailed:
        h_msg = "Step 3: Edit the transcript and Mail the Letter."
        h_pct = 70
    elif has_mailed:
        h_msg = "Legacy Secured. Archive Active."
        h_pct = 100

    st.markdown(f"""
    <div style="background-color: #f0fdf4; padding: 15px; border-radius: 10px; border: 1px solid #bbf7d0; margin-bottom: 25px;">
        <p style="margin: 0; font-size: 0.9rem; font-weight: 600; color: #166534; text-transform: uppercase;">Archive Progress</p>
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <h3 style="margin: 5px 0; color: #14532d;">{h_msg}</h3>
            <span style="font-weight: bold; color: #22c55e;">{h_pct}%</span>
        </div>
        <div style="width: 100%; background-color: #bbf7d0; height: 8px; border-radius: 4px; margin-top: 5px;">
            <div style="width: {h_pct}%; background-color: #22c55e; height: 8px; border-radius: 4px;"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # --- HEADER & INSTRUCTIONS ---
    st.title("🏛️ The Family Legacy Project")
    advisor_firm = profile.get("advisor_firm", "VerbaPost Wealth")
    st.caption(f"Sponsored by {advisor_firm}")
    
    with st.expander("📝 How it works", expanded=False):
        st.markdown("""
        **Step 1: Notify.** Send the 'Prep Email' so the interviewee knows the topic.
        **Step 2: Interview.** Click 'Start Interview Call'.
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
        
    btn_col1, btn_col2 = st.columns(2)
    with btn_col1:
        if st.button("📧 Send Prep Email", use_container_width=True):
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
                        st.error("Failed to send email.")

    with btn_col2:
        if st.button("📞 Start Interview Call", use_container_width=True, type="primary"):
            clean_phone = "".join(filter(str.isdigit, target_phone))
            if not clean_phone or len(clean_phone) < 10:
                st.error("⚠️ Please enter a valid 10-digit phone number.")
            else:
                with st.spinner("☎️ Connecting AI Biographer..."):
                    advisor_name = profile.get("advisor_firm") or "Your Advisor"
                    sid, err = ai_engine.trigger_outbound_call(
                        to_phone=clean_phone,
                        advisor_name=advisor_name,
                        firm_name=profile.get("advisor_firm", "VerbaPost"),
                        project_id=profile.get("id"), 
                        question_text=custom_question
                    )
                    if sid:
                        database.create_draft(
                            user_email=user_email, content="Waiting for recording...",
                            status="Pending", call_sid=sid
                        )
                        if audit_engine:
                            audit_engine.log_event(user_email, "Interview Started", metadata={"sid": sid})
                        st.success(f"📞 Calling {target_phone} now... Call Initiated!")
                    else:
                        st.error(f"Call Failed: {err}")

    st.divider()

    # --- SECTION 2: THE VAULT (INBOX) ---
    st.subheader("📂 Story Archive")
    
    if st.button("🔄 Check for New Stories"):
        with st.spinner("Syncing with Biographer..."):
            all_drafts = database.get_user_drafts(user_email)
            pending = [d for d in all_drafts if d.get('call_sid')]
            synced_count = 0
            for p in pending:
                sid = p.get('call_sid')
                text, url = ai_engine.find_and_transcribe_recording(sid)
                if text and url:
                    database.update_draft_by_sid(sid, text, url)
                    synced_count += 1
            if synced_count > 0: st.success(f"Found {synced_count} new stories!")
            else: st.info("No new recordings found yet.")
            time.sleep(1)
            st.rerun()

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
                    if days_left > 0: st.caption(f"⚠️ Expires in **{days_left} days**")
                    else: st.caption("🔴 Archived (Offline)")

                audio_url = draft.get('tracking_number') 
                if audio_url and "http" in audio_url:
                     st.audio(audio_url)
                     st.link_button("⬇️ Download (.mp3)", url=audio_url)
                elif draft.get('status') == 'Pending':
                    st.warning("⏳ Waiting for recording... click Refresh above.")

                with st.expander("✍️ Edit Text & Mail Letter"):
                    new_text = st.text_area("Transcript", value=draft.get('content', ''), height=200, key=f"txt_{draft['id']}")
                    
                    b_col1, b_col2 = st.columns([1, 1])
                    with b_col1:
                        if st.button("✨ AI Polish", key=f"polish_{draft['id']}"):
                            with st.spinner("Polishing story..."):
                                polished_text = ai_engine.refine_text(new_text)
                                if polished_text:
                                    database.update_draft(draft['id'], polished_text)
                                    st.success("Story Polished!")
                                    time.sleep(1)
                                    st.rerun()
                                else: st.error("Polish failed.")
                    with b_col2:
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
                            with st.spinner("Queueing for Print..."):
                                try:
                                    new_credits = credits - CREDIT_COST
                                    database.update_user_credits(user_email, new_credits)
                                    database.update_project_details(draft['id'], status='Approved')
                                    if audit_engine:
                                        audit_engine.log_event(user_email, "Manual Print Queued", metadata={"draft_id": draft['id']})
                                    st.success("✅ Added to Print Queue! Your advisor will finalize fulfillment.")
                                    time.sleep(2)
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Error queueing order: {e}")

    with st.expander("⚙️ Mailing Settings"):
        st.write("Ensure your mailing address is correct for the physical manuscript.")
        st.info("To update your mailing address, please visit the main Settings page.")