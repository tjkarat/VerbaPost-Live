import streamlit as st
import time
import logging
import base64
from datetime import datetime

# --- LOGGING SETUP ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- MODULE IMPORTS ---
try: import database
except ImportError: database = None
try: import ai_engine
except ImportError: ai_engine = None
try: import email_engine
except ImportError: email_engine = None
try: import letter_format
except ImportError: letter_format = None

def get_db():
    return database

def render_dashboard():
    """
    The Heir's Interface: View stories, edit transcripts, and send for print.
    """
    # 1. SETUP & AUTH CHECK
    db = get_db()
    if not db: 
        st.error("Database unavailable.")
        st.stop()
        
    user_email = st.session_state.get("user_email")
    if not user_email:
        st.error("Authentication lost. Please log in again.")
        st.stop()

    try: db.fix_heir_account(user_email)
    except Exception: pass

    # 2. GET USER DATA
    profile = db.get_user_profile(user_email)
    user_status = profile.get('status', 'Pending') 
    
    # 3. BRANDING
    advisor_firm = "VerbaPost" 
    projects = db.get_heir_projects(user_email)
    
    if projects:
        advisor_firm = projects[0].get('firm_name', 'VerbaPost')
    elif profile.get('advisor_firm'):
         advisor_firm = profile.get('advisor_firm')

    # --- SIDEBAR: IMMEDIATE ACTIONS ---
    with st.sidebar:
        st.divider()
        st.subheader("🎙️ Action Center")
        
        # 1. CALL BUTTON
        if st.button("📞 Call Me Now", type="primary", use_container_width=True):
            with st.spinner("Connecting..."):
                target_phone = profile.get('parent_phone')
                # Find prompt from latest active project
                active_p = next((p for p in projects if p.get('status') in ['Authorized', 'Recording']), None)
                prompt_text = active_p.get('strategic_prompt') if active_p else "Please share a memory."
                
                if not target_phone:
                    st.error("Please add a phone number in 'Setup' first.")
                else:
                    try:
                        sid, error = ai_engine.trigger_outbound_call(
                            to_phone=target_phone,
                            advisor_name="Your Advisor",
                            firm_name=advisor_firm,
                            prompt_text=prompt_text 
                        )
                        if sid:
                            st.toast(f"Calling {target_phone}...")
                            db.create_draft(user_email, "", "Recording", sid)
                            time.sleep(2)
                            st.rerun()
                        else:
                            st.error(f"Call Failed: {error}")
                    except Exception as e:
                        st.error(f"Error: {e}")

        # 2. REFRESH BUTTON
        st.markdown("---")
        if st.button("🔄 Check for New Stories", use_container_width=True):
            with st.spinner("Downloading from phone system..."):
                recording_projects = [p for p in projects if p.get('status') == 'Recording' and p.get('call_sid')]
                found_new = False
                for p in recording_projects:
                    sid = p.get('call_sid')
                    pid = p.get('id')
                    text, audio_url, err = ai_engine.fetch_and_transcribe(sid)
                    
                    if text:
                        with db.get_db_session() as session:
                            proj = session.query(db.Project).filter_by(id=pid).first()
                            if proj:
                                proj.content = text
                                proj.audio_ref = audio_url
                                session.commit()
                        found_new = True
                        
                        if email_engine:
                            email_engine.send_email(
                                user_email,
                                "New Story Recorded! 🎙️",
                                f"<p>A new story has been recorded and transcribed.</p><p><strong>Preview:</strong> {text[:100]}...</p><p>Log in to edit and save it.</p>"
                            )
                
                if found_new:
                    st.success("New story transcribed! Email sent.")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.info("No new completed recordings found.")

    # --- MAIN CONTENT ---
    st.title("📂 Family Legacy Archive")
    st.markdown(f"**Sponsored by {advisor_firm}**")
    st.caption(f"Logged in as: {user_email}")
    st.divider()
    
    if user_status != 'Active':
        st.warning("🔒 Account Not Active")
        st.markdown(f"This service requires a sponsorship credit from your Financial Advisor. Current Status: `{user_status}`")
        st.stop()

    tab_inbox, tab_vault, tab_setup = st.tabs(["📥 Story Inbox", "🏛️ The Vault", "⚙️ Setup & Schedule"])

    # --- TAB: INBOX ---
    with tab_inbox:
        st.subheader("Pending Stories")
        active_projects = [p for p in projects if p.get('status') in ['Authorized', 'Recording', 'Pending Approval']]
        
        if not active_projects:
            st.info("No active stories pending review. Click 'Call Me Now' in the sidebar to start!")
        
        for p in active_projects:
            pid = p.get('id')
            status = p.get('status')
            content = p.get('content') or ""
            prompt = p.get('strategic_prompt') or "No prompt set."
            
            with st.expander(f"Draft: {prompt[:50]}...", expanded=True):
                if status == "Authorized":
                    st.info("📞 Status: Ready for Interview Call")
                elif status == "Recording":
                    if not content: st.warning("🎙️ Status: Waiting for Recording... (Click 'Check for New Stories')")
                    else: st.success("📝 Status: Transcribed / Ready to Edit")

                st.markdown(f"**Interview Question:** *{prompt}*")
                
                # Editable Text
                new_text = st.text_area(
                    "Transcript Edit", 
                    value=content, 
                    height=300, 
                    key=f"txt_{pid}"
                )
                
                # --- ACTION BUTTONS ---
                c1, c2, c3 = st.columns([1, 1, 2])
                
                # 1. SAVE
                if c1.button("💾 Save Draft", key=f"sv_{pid}"):
                    if db.update_project_content(pid, new_text):
                        st.toast("Draft Saved!")
                        time.sleep(1)
                        st.rerun()

                # 2. AI POLISH
                if c2.button("✨ AI Polish", key=f"ai_{pid}"):
                    with st.spinner("Polishing transcript..."):
                        if ai_engine:
                            # Auto-save current state before polishing to prevent data loss
                            db.update_project_content(pid, new_text)
                            refined = ai_engine.refine_text(new_text)
                            if refined:
                                db.update_project_content(pid, refined)
                                st.success("Polished! Reloading...")
                                time.sleep(1)
                                st.rerun()
                        else:
                            st.error("AI Engine missing.")

                # 3. PREVIEW & SEND
                # We use session state to toggle the preview window
                preview_key = f"show_preview_{pid}"
                if c3.button("📄 Preview PDF", key=f"prev_{pid}", type="secondary"):
                    st.session_state[preview_key] = True
                
                # --- PREVIEW WINDOW ---
                if st.session_state.get(preview_key):
                    st.divider()
                    st.subheader("🔎 Document Proof")
                    st.info("Please review the PDF below. This is exactly how it will print.")
                    
                    if letter_format:
                        # Construct Metadata for Preview
                        meta = {
                            "storyteller": profile.get('parent_name', 'Unknown'), # Uses the editable field from Setup
                            "firm_name": advisor_firm,
                            "heir_name": profile.get('full_name', ''),
                            "interview_date": datetime.now().strftime("%B %d, %Y"),
                            "question_text": prompt
                        }
                        
                        pdf_bytes = letter_format.create_pdf(
                            body_text=new_text,
                            to_addr={},
                            from_addr={},
                            tier="Heirloom",
                            metadata=meta,
                            audio_url=str(pid) # Enables QR Code generation
                        )
                        
                        # Display PDF
                        b64_pdf = base64.b64encode(pdf_bytes).decode('latin-1')
                        pdf_display = f'<iframe src="data:application/pdf;base64,{b64_pdf}" width="100%" height="600" type="application/pdf"></iframe>'
                        st.markdown(pdf_display, unsafe_allow_html=True)
                        
                        st.markdown("<br>", unsafe_allow_html=True)
                        
                        # 4. FINAL SEND BUTTON
                        col_close, col_send = st.columns([1, 3])
                        if col_close.button("Close", key=f"cls_{pid}"):
                            st.session_state[preview_key] = False
                            st.rerun()
                            
                        if col_send.button("🚀 Looks Good - Mail Letter", type="primary", key=f"final_{pid}"):
                            if db.finalize_heir_project(pid, new_text):
                                st.session_state[preview_key] = False
                                st.balloons()
                                st.success("Sent to Print Queue! Your keepsake is being prepared.")
                                time.sleep(3)
                                st.rerun()
                    else:
                        st.error("PDF Engine Unavailable.")

    # --- TAB: VAULT ---
    with tab_vault:
        st.subheader("Preserved Memories")
        completed = [p for p in projects if p.get('status') in ['Approved', 'Sent']]
        if not completed: st.caption("No completed letters yet.")
        for p in completed:
            date_str = str(p.get('created_at'))[:10]
            with st.expander(f"✅ {date_str} - {p.get('strategic_prompt')[:30]}..."):
                st.markdown(p.get('content'))
                st.divider()
                if p.get('audio_released'):
                    if p.get('audio_ref'):
                        st.success("🔓 Audio Unlocked by Advisor")
                        st.audio(p.get('audio_ref'))
                    else: st.info("Audio available but file missing.")
                else:
                    st.warning("🔒 Audio Archive Locked")
                    st.caption(f"The audio recording is currently held in the {advisor_firm} secure vault. Contact your advisor to request release.")
                st.download_button("⬇️ Download PDF", data=p.get('content') or "", file_name="letter.txt")

    # --- TAB: SETUP & SCHEDULE ---
    with tab_setup:
        st.subheader("Interview Settings")
        with st.form("settings_form"):
            st.markdown("### 👨‍👩‍👧 Family Details")
            
            # UPDATED LABEL: Allows user to modify the Storyteller Name explicitly
            p_name = st.text_input("Storyteller Name (Appears on Letter Header)", 
                                 value=profile.get('parent_name', ''),
                                 help="e.g. 'Dad', 'Robert Smith', 'Grandma Alice'")
            
            p_phone = st.text_input("Parent Phone", value=profile.get('parent_phone', ''))
            
            st.divider()
            st.markdown("### 📬 Shipping Address")
            c_str, c_city = st.columns([2, 1])
            addr1 = c_str.text_input("Street Address", value=profile.get('address_line1', ''))
            city = c_city.text_input("City", value=profile.get('address_city', ''))
            
            c_st, c_zip = st.columns(2)
            state = c_st.text_input("State", value=profile.get('address_state', ''))
            zip_code = c_zip.text_input("Zip Code", value=profile.get('address_zip', ''))

            if st.form_submit_button("Update Settings"):
                if db.update_heirloom_settings(user_email, p_name, p_phone, addr1, city, state, zip_code):
                    st.success("Settings Updated")
                    st.rerun()

        st.divider()
        st.subheader("📅 Schedule Future Call")
        c1, c2 = st.columns(2)
        d = c1.date_input("Date")
        t = c2.time_input("Time")
        if st.button("Schedule Call"):
            st.success(f"Call scheduled for {d} at {t}.")