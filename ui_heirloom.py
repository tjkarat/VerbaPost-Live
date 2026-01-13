import streamlit as st
import time
from datetime import datetime

# --- MODULE IMPORTS ---
try: import database
except ImportError: database = None
try: import ai_engine
except ImportError: ai_engine = None
try: import heirloom_engine
except ImportError: heirloom_engine = None
try: import audit_engine
except ImportError: audit_engine = None
try: import letter_format
except ImportError: letter_format = None
try: import mailer
except ImportError: mailer = None

def render_dashboard():
    """
    The Family Archive Portal (Heir View).
    Streamlined for B2B: Edit -> Submit -> Wait for Advisor.
    """
    if not st.session_state.get("authenticated"):
        st.warning("Please log in."); return

    user_email = st.session_state.get("user_email")
    
    # 1. HEADER: BRANDING
    # We fetch projects to see who the advisor is
    projects = []
    if database:
        projects = database.get_heir_projects(user_email)
    
    firm_name = projects[0].get('firm_name') if projects else "VerbaPost"
    
    col_logo, col_title = st.columns([1, 4])
    with col_title:
        st.title("The Family Archive")
        st.caption(f"Sponsored by {firm_name} | Preserving your family legacy.")

    st.divider()

    # 2. TABS
    tab_inbox, tab_setup = st.tabs(["📥 Story Inbox", "⚙️ Setup & Interview"])

    # --- TAB A: INBOX (THE WORKFLOW) ---
    with tab_inbox:
        if not projects:
            st.info("No stories found yet. Use the 'Setup' tab to start an interview.")
        
        for p in projects:
            pid = p.get('id')
            status = p.get('status', 'Recording')
            date_str = p.get('created_at', 'Unknown Date')
            content = p.get('content', '')
            
            # Status Badge Logic
            if status == "Pending Approval":
                icon = "⏳"
                badge_color = "orange"
                label = "Waiting for Advisor Review"
            elif status == "Approved" or status == "Sent":
                icon = "✅"
                badge_color = "green"
                label = "Preserved & Mailed"
            else:
                icon = "🎙️"
                badge_color = "blue"
                label = "Draft (Needs Editing)"

            with st.expander(f"{icon} {date_str} | {label}", expanded=(status=='Recording')):
                
                # STATUS BANNER
                st.markdown(f":{badge_color}[**Status: {label}**]")
                
                # EDITING AREA (Only editable if not yet approved)
                is_editable = (status == "Recording" or status == "Authorized")
                
                new_text = st.text_area(
                    "Transcript", 
                    value=content, 
                    height=250, 
                    key=f"txt_{pid}",
                    disabled=not is_editable
                )
                
                if is_editable:
                    col_save, col_submit = st.columns([1, 2])
                    
                    with col_save:
                        if st.button("💾 Save Draft", key=f"sav_{pid}", use_container_width=True):
                            if database: database.update_project_content(pid, new_text)
                            st.toast("Draft saved.")
                    
                    with col_submit:
                        st.markdown("**Ready to print?**")
                        if st.button("✨ Submit to Advisor", key=f"sub_{pid}", type="primary", use_container_width=True):
                            # 1. Save final text first
                            if database: 
                                database.update_project_content(pid, new_text)
                                # 2. Update status
                                success = database.submit_project(pid)
                                if success:
                                    if audit_engine: 
                                        audit_engine.log_event(user_email, "PROJECT_SUBMITTED", pid)
                                    st.balloons()
                                    st.success("Submitted! Your advisor has been notified.")
                                    time.sleep(2)
                                    st.rerun()
                                else:
                                    st.error("Submission failed.")
                else:
                    st.info("This story has been submitted/archived and is now read-only.")

    # --- TAB B: SETUP (RETAINED FOR SELF-SERVICE CALLS) ---
    with tab_setup:
        st.subheader("Start a New Interview")
        
        # Load profile for defaults
        profile = database.get_user_profile(user_email) if database else {}
        curr_p_name = profile.get("parent_name", "")
        curr_p_phone = profile.get("parent_phone", "")
        
        with st.form("interview_target"):
            st.markdown("Who are we interviewing?")
            p_name = st.text_input("Name", value=curr_p_name)
            p_phone = st.text_input("Phone Number", value=curr_p_phone)
            
            if st.form_submit_button("Save Settings"):
                if database:
                    database.update_heirloom_settings(user_email, p_name, p_phone)
                    st.success("Saved.")
                    st.rerun()
        
        st.divider()
        
        if p_phone:
            st.markdown(f"#### 📞 Call {p_name or 'Parent'}")
            topic = st.text_input("Topic / Question", placeholder="e.g. Tell me about your first car.")
            
            if st.button("Trigger Call Now", type="primary"):
                if ai_engine:
                    with st.spinner("Connecting..."):
                        # Uses the hardened AI engine with Prep-SMS
                        sid, err = ai_engine.trigger_outbound_call(p_phone, "your advisor", firm_name)
                        if sid:
                            st.success("Calling now! Pick up the phone.")
                        else:
                            st.error(f"Call failed: {err}")

if __name__ == "__main__":
    render_dashboard()