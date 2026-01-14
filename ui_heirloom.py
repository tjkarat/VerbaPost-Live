import streamlit as st
import time
import logging

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

def get_db():
    return database

def render_dashboard():
    """
    The Heir's Interface: View stories, edit transcripts, and submit to advisor.
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

    # 2. GET USER DATA & ACCESS CONTROL
    profile = db.get_user_profile(user_email)
    user_status = profile.get('status', 'Pending') 
    
    # Paywall / Access Gate
    if user_status != 'Active':
        st.warning("🔒 Account Not Active")
        st.markdown(f"""
        **Access Restricted**
        This service requires a sponsorship credit from your Financial Advisor.
        **Current Status:** `{user_status}`
        """)
        st.stop()

    # 3. BRANDING
    advisor_firm = "VerbaPost" 
    projects = db.get_heir_projects(user_email)
    
    if projects:
        advisor_firm = projects[0].get('firm_name', 'VerbaPost')
    elif profile.get('advisor_firm'):
         advisor_firm = profile.get('advisor_firm')

    st.title("📂 Family Legacy Archive")
    st.markdown(f"**Sponsored by {advisor_firm}**")
    st.caption(f"Logged in as: {user_email}")
    st.divider()

    # 4. TABS
    tab_inbox, tab_vault, tab_setup = st.tabs(["📥 Story Inbox", "🏛️ The Vault", "⚙️ Setup & Interview"])

    # --- TAB: INBOX ---
    with tab_inbox:
        st.subheader("Pending Stories")
        active_projects = [p for p in projects if p.get('status') in ['Authorized', 'Recording', 'Pending Approval']]
        
        if not active_projects:
            st.info("No active stories pending review.")
        
        for p in active_projects:
            pid = p.get('id')
            status = p.get('status')
            content = p.get('content') or ""
            prompt = p.get('strategic_prompt') or "No prompt set."
            advisor_email = p.get('advisor_email') # Needed for email alert
            
            with st.expander(f"Draft: {prompt[:50]}...", expanded=True):
                if status == "Authorized":
                    st.info("📞 Status: Ready for Interview Call")
                elif status == "Recording":
                    st.warning("🎙️ Status: Drafting / Needs Edit")
                elif status == "Pending Approval":
                    st.warning("⏳ Status: Waiting for Advisor Review")

                st.markdown(f"**Interview Question:** *{prompt}*")
                
                is_locked = (status == "Pending Approval")
                
                new_text = st.text_area(
                    "Transcript Edit", 
                    value=content, 
                    height=300, 
                    disabled=is_locked,
                    key=f"txt_{pid}"
                )
                
                if not is_locked:
                    c1, c2 = st.columns(2)
                    if c1.button("💾 Save Draft", key=f"save_{pid}"):
                        if db.update_project_content(pid, new_text):
                            st.toast("Draft Saved!")
                            time.sleep(1)
                            st.rerun()
                    
                    if c2.button("✨ Submit to Advisor", type="primary", key=f"sub_{pid}"):
                        if db.submit_project(pid):
                            
                            # --- 📧 EMAIL INJECTION: THE ALERT ---
                            if email_engine and advisor_email:
                                subject = f"Action Required: {user_email} submitted a story"
                                html = f"""
                                <h3>Draft Submitted for Review</h3>
                                <p>Your client <strong>{user_email}</strong> has finished editing a story.</p>
                                <p>Please log in to the Advisor Portal to review and approve it for printing.</p>
                                """
                                email_engine.send_email(advisor_email, subject, html)
                            # -------------------------------------

                            st.balloons()
                            st.success("Sent to Advisor for final print approval!")
                            time.sleep(2)
                            st.rerun()

    # --- TAB: VAULT ---
    with tab_vault:
        st.subheader("Preserved Memories")
        completed = [p for p in projects if p.get('status') in ['Approved', 'Sent']]
        
        if not completed:
            st.caption("No completed letters yet.")
        
        for p in completed:
            date_str = str(p.get('created_at'))[:10]
            with st.expander(f"✅ {date_str}"):
                st.markdown(p.get('content'))
                st.download_button("⬇️ Download PDF", data=p.get('content'), file_name="letter.txt")

    # --- TAB: SETUP ---
    with tab_setup:
        st.subheader("Interview Settings")
        
        with st.form("settings_form"):
            p_name = st.text_input("Parent Name", value=profile.get('parent_name', ''))
            p_phone = st.text_input("Parent Phone", value=profile.get('parent_phone', ''))
            
            if st.form_submit_button("Update Settings"):
                if db.update_heirloom_settings(user_email, p_name, p_phone):
                    st.success("Settings Updated")
                    st.rerun()

        st.divider()
        st.markdown("#### 🔴 Danger Zone")
        
        if st.button("Trigger Test Call Now"):
            st.warning("System: Initiating outbound call sequence...")
            target_phone = profile.get('parent_phone')
            
            if not target_phone:
                st.error("❌ No Parent Phone found.")
            else:
                try:
                    # Trigger Call
                    sid, error = ai_engine.trigger_outbound_call(
                        to_phone=target_phone,
                        advisor_name="Your Advisor",
                        firm_name=advisor_firm
                    )
                    
                    if sid:
                        st.success(f"✅ Call dispatched! SID: {sid}")
                        # TRACK IN DB
                        try:
                            db.create_draft(
                                user_email=user_email,
                                content="", 
                                status="Recording",
                                call_sid=sid,
                                tier="Heirloom"
                            )
                            st.info("📝 Database record created.")
                        except Exception as db_e:
                            st.error(f"⚠️ DB Save Failed: {db_e}")
                    else:
                        st.error(f"❌ Call Failed: {error}")
                except Exception as e:
                    st.error(f"System Error: {e}")