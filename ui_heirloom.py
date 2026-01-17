import streamlit as st
import time
from datetime import datetime, timedelta
import database
import ai_engine
import mailer
import email_engine 
import letter_format
import audit_engine 
import logging
import analytics  # <--- RESTORED

# --- CONFIGURATION ---
CREDIT_COST = 1 
logger = logging.getLogger(__name__)

# ==========================================
# 🎧 PUBLIC PLAYER (QR Code Access)
# ==========================================
def render_public_player(audio_id):
    """
    Public-facing player for QR code scans. 
    Does not require login.
    """
    # 1. INJECT ANALYTICS (RESTORED)
    if hasattr(analytics, 'inject_ga'):
        analytics.inject_ga()
    
    # 2. Clean Layout for Mobile/Public
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

    # 3. Header
    st.markdown("<div style='text-align: center; margin-bottom: 20px;'><h1>🎙️ The Family Legacy Archive</h1></div>", unsafe_allow_html=True)
    
    # 4. Resolve Audio URL
    audio_url = None
    story_title = "Private Recording"
    story_date = "Unknown Date"
    storyteller = "Family Member"

    if audio_id == "demo" or audio_id == "sample":
        audio_url = "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3"
        story_title = "Barnaby Jones - Childhood Memories"
        story_date = "January 16, 2026"
        storyteller = "Barnaby Jones"
    else:
        try:
            if hasattr(database, 'get_public_draft'):
                draft_data = database.get_public_draft(audio_id)
                if draft_data:
                    audio_url = draft_data.get("url")
                    story_title = draft_data.get("title")
                    story_date = draft_data.get("date")
                    storyteller = draft_data.get("storyteller")
            else:
                st.warning(f"Note: Looking up secure recording ID: {audio_id}")
        except Exception:
            pass
    
    # 5. Render Player UI
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
        
        st.markdown("""
            <div style='text-align: center; color: #64748b; font-size: 0.9rem;'>
                <em>Preserved by VerbaPost</em><br><br>
                <p>Do you have a story to tell?</p>
            </div>
        """, unsafe_allow_html=True)
        
        if st.button("Claim this Memory / Log In", use_container_width=True):
            st.session_state["pending_play_id"] = audio_id
            st.query_params.clear()
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

def render_dashboard():
    """
    The Family Legacy Archive.
    """
    if not st.session_state.get("authenticated"):
        st.warning("Please log in to access the Family Archive.")
        return

    user_email = st.session_state.user_email
    profile = database.get_user_profile(user_email)
    
    if not profile:
        st.error("Profile not found.")
        return

    # --- SPONSORSHIP CHECK ---
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

    # --- HEADER (Smaller as requested) ---
    st.markdown("### 🏛️ The Family Legacy Project")
    advisor_firm = profile.get("advisor_firm", "VerbaPost Wealth")
    st.caption(f"Sponsored by {advisor_firm}")

    # --- INSTRUCTIONS (Updated to your Steps) ---
    st.info("""
    **How to Archive a Story:**
    1. **Enter Data:** Fill in the Interviewee's Phone, Email, and Question below.
    2. **Notify:** Click 'Send Prep Email'. The call comes from **(615) 656-7669** (VerbaPost) — ensure it's not blocked.
    3. **Record:** After the call, wait a few minutes and click 'Check for New Stories' below.
    4. **Edit:** Review the transcript and download the audio.
    5. **Mail:** Click 'Mail Letter' (You will be asked for your shipping address if missing).
    6. **Receive:** Watch your mailbox for the USPS delivery.
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
        if st.button("📧 Send Prep Email (Step 2)", use_container_width=True):
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
        if st.button("📞 Start Interview Call (Step 3)", use_container_width=True, type="primary"):
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
                            status="Pending", call_sid=sid, prompt=custom_question
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
    
    heirloom_drafts = [d for d in database.get_user_drafts(user_email) if d.get('tier') == 'Heirloom' or d.get('project_type')]

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
                    
                    # --- 🚨 ADDRESS GATE LOGIC ---
                    
                    # 1. Check if we have an address
                    has_address = (
                        profile.get('address_line1') and 
                        profile.get('address_city') and 
                        profile.get('address_state') and 
                        profile.get('address_zip')
                    )

                    if not has_address:
                        # 🔴 BLOCKED: Show Form
                        st.error("🛑 Shipping Address Required")
                        st.info("Step 5: Please enter the address where you want the physical letter sent.")
                        
                        with st.form(key=f"addr_form_{draft['id']}"):
                            s_street = st.text_input("Street Address")
                            sc1, sc2, sc3 = st.columns(3)
                            s_city = sc1.text_input("City")
                            s_state = sc2.text_input("State")
                            s_zip = sc3.text_input("Zip")
                            
                            if st.form_submit_button("Save Address & Unlock"):
                                try:
                                    from database import supabase
                                    if supabase:
                                        supabase.table("user_profiles").update({
                                            "address_line1": s_street,
                                            "address_city": s_city,
                                            "address_state": s_state,
                                            "address_zip": s_zip
                                        }).eq("email", user_email).execute()
                                        st.success("Address Saved! You can now mail the letter.")
                                        time.sleep(1)
                                        st.rerun()
                                except Exception as e:
                                    st.error(f"Save failed: {e}")
                    else:
                        # 🟢 UNLOCKED: Show Mail Button
                        m_col1, m_col2 = st.columns([2, 1])
                        with m_col1:
                            addr_str = f"{profile.get('address_line1')}, {profile.get('address_city')}, {profile.get('address_state')} {profile.get('address_zip')}"
                            st.caption(f"**Mailing to:** {addr_str}")
                            if st.button("📝 Edit Address", key=f"edit_addr_{draft['id']}"):
                                # Quick reset to force re-entry
                                from database import supabase
                                if supabase:
                                    supabase.table("user_profiles").update({"address_line1": ""}).eq("email", user_email).execute()
                                    st.rerun()
                                    
                        with m_col2:
                            credits = profile.get('credits', 0)
                            if st.button(f"📮 Mail Letter ({CREDIT_COST} Credit)", key=f"mail_{draft['id']}", type="primary", disabled=(credits < CREDIT_COST)):
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

# --- ALIAS ---
render_family_archive = render_dashboard