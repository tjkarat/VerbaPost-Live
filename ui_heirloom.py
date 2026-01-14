import streamlit as st
import time
import logging

# --- LOGGING SETUP ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- LAZY IMPORTS ---
def get_db():
    import database
    return database

def get_ai():
    import ai_engine
    return ai_engine

def render_dashboard():
    """
    The Heir's Interface: View stories, edit transcripts, and submit to advisor.
    """
    # 1. SETUP & AUTH CHECK
    db = get_db()
    user_email = st.session_state.get("user_email")
    if not user_email:
        st.error("Authentication lost. Please log in again.")
        st.stop()

    # 2. GET USER DATA & ACCESS CONTROL
    # We fetch the profile to check status ('Active', 'Pending', etc.)
    profile = db.get_user_profile(user_email)
    
    # --- SECURITY GATE: BLOCK NON-PAYING USERS ---
    # If the user wasn't activated by an Advisor (no credit spent), block access.
    # We assume the 'status' column in your 'clients' table handles this.
    user_status = profile.get('status', 'Pending') 
    
    if user_status != 'Active':
        st.warning("🔒 Account Not Active")
        st.markdown(f"""
        **Access Restricted**
        
        Your Family Archive has not been activated yet. 
        
        This service requires a sponsorship credit from your Financial Advisor to cover 
        telephony, transcription, and archival mailing costs.
        
        **Current Status:** `{user_status}`
        
        Please contact your advisor to activate your vault.
        """)
        st.stop() # <--- Halts execution here. Safe.

    # 3. BRANDING & HEADER
    # Fetch branding based on the linked advisor
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

    # 4. MAIN CONTENT TABS
    tab_inbox, tab_vault, tab_setup = st.tabs(["📥 Story Inbox", "🏛️ The Vault", "⚙️ Setup & Interview"])

    # --- TAB: INBOX ---
    with tab_inbox:
        st.subheader("Pending Stories")
        
        # Filter for active drafts
        active_projects = [p for p in projects if p.get('status') in ['Authorized', 'Recording', 'Pending Approval']]
        
        if not active_projects:
            st.info("No active stories pending review.")
            st.markdown("""
            **How it works:**
            1. We call your parent/senior.
            2. The audio is transcribed.
            3. It appears here for you to edit.
            4. You submit it to your Advisor for printing.
            """)
        
        for p in active_projects:
            pid = p.get('id')
            status = p.get('status')
            content = p.get('content') or ""
            prompt = p.get('strategic_prompt') or "No prompt set."
            call_sid = p.get('call_sid') # Useful for debugging
            
            with st.expander(f"Draft: {prompt[:50]}...", expanded=True):
                if status == "Authorized":
                    st.info("📞 Status: Ready for Interview Call")
                elif status == "Recording":
                    st.warning(f"🎙️ Status: Drafting / Needs Edit (Call SID: {call_sid})")
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
                st.error("❌ No Parent Phone found. Please save settings above first.")
            else:
                try:
                    ai = get_ai()
                    
                    # 1. TRIGGER THE CALL
                    sid, error = ai.trigger_outbound_call(
                        to_phone=target_phone,
                        advisor_name="Your Advisor",
                        firm_name=advisor_firm
                    )
                    
                    if sid:
                        st.success(f"✅ Call dispatched! SID: {sid}")
                        
                        # 2. SAVE THE RECEIPT (Fixes 'Lost Story' Issue)
                        # We immediately create a draft linked to this SID so the database expects it.
                        try:
                            # Note: Ensure create_draft exists in database.py or use create_project
                            db.create_draft(
                                user_email=user_email,
                                content="", 
                                status="Recording",
                                call_sid=sid,
                                tier="Heirloom"
                            )
                            st.info("📝 Database record created. Check 'Inbox' tab.")
                        except AttributeError:
                            st.warning("⚠️ Call sent, but could not save draft record (Database method missing).")
                        except Exception as db_e:
                            st.error(f"⚠️ Call sent, but DB save failed: {db_e}")
                            
                    else:
                        st.error(f"❌ Call Failed: {error}")
                        
                except ImportError as e:
                    st.error(f"❌ Import Error: {e}")
                except Exception as e:
                    st.error(f"❌ System Error: {e}")