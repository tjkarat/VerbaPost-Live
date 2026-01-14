import streamlit as st
import logging
import time

# --- LOGGING SETUP ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- MODULE IMPORTS ---
try: import database
except ImportError: database = None
try: import email_engine
except ImportError: email_engine = None

def render_dashboard():
    """
    Advisor Portal: Manage clients, consume credits, and trigger invites.
    """
    st.title("💼 Advisor Portal")
    
    # 1. AUTH & PROFILE
    if not database:
        st.error("Database module missing.")
        st.stop()
        
    user_email = st.session_state.get("user_email")
    if not user_email:
        st.error("Please log in.")
        st.stop()

    # Fetch Advisor Profile (Credits, Firm Name)
    advisor = database.get_advisor_profile(user_email)
    if not advisor:
        st.warning("Advisor profile not found. Please contact admin.")
        st.stop()
        
    credits = advisor.get('credits', 0)
    firm_name = advisor.get('firm_name', 'VerbaPost Wealth')

    # 2. HEADER
    c1, c2 = st.columns([3, 1])
    c1.markdown(f"**Firm:** {firm_name}")
    c2.metric("Available Credits", credits)
    st.divider()

    # 3. ROSTER TABS
    tab_roster, tab_approve, tab_action = st.tabs(["👥 Client Roster", "✅ Approvals", "🚀 Activate Client"])

    # --- TAB: ROSTER ---
    with tab_roster:
        st.subheader("Active Families")
        clients = database.get_advisor_clients(user_email)
        
        if not clients:
            st.info("No active clients yet. Go to 'Activate Client' to start.")
        
        for c in clients:
            with st.expander(f"👤 {c.get('name')} ({c.get('status')})"):
                st.write(f"**Heir:** {c.get('heir_name')}")
                st.write(f"**Email:** {c.get('email')}")
                st.write(f"**Phone:** {c.get('phone')}")

    # --- TAB: APPROVALS (RELEASE GATE) ---
    with tab_approve:
        st.subheader("Pending Review")
        st.caption("Approve drafts to unlock audio for the family and send for printing.")
        
        pending = database.get_pending_approvals(user_email)
        
        if not pending:
            st.info("No drafts waiting for review.")
            
        for p in pending:
            pid = p.get('id')
            heir_name = p.get('heir_name')
            heir_email = p.get('heir_email')
            
            with st.container(border=True):
                st.markdown(f"**Draft from {heir_name}**")
                st.text_area("Content", p.get('content'), height=150, disabled=True, key=f"rev_{pid}")
                
                if st.button("✅ Approve & Release Audio", key=f"app_{pid}", type="primary"):
                    if database.update_project_details(pid, status="Approved"):
                        
                        # --- 📧 EMAIL INJECTION: RELEASE NOTIFICATION ---
                        if email_engine and heir_email:
                            subject = f"Legacy Letter Approved: Audio Unlocked 🔓"
                            
                            # Build Play Link
                            # Assuming audio_ref is stored, or we use project_id to lookup
                            play_link = f"https://verbapost.streamlit.app/?play={pid}"
                            
                            html = f"""
                            <div style="font-family: sans-serif; padding: 20px; color: #333;">
                                <h2 style="color: #2c3e50;">Great news, {heir_name}</h2>
                                <p>Your advisor, <strong>{firm_name}</strong>, has approved your family story for printing.</p>
                                <p><strong>The audio recording has been unlocked.</strong></p>
                                <p>You can listen to the original voice recording by scanning the QR code on your physical letter, or by clicking below:</p>
                                <br>
                                <a href="{play_link}" style="background-color: #27ae60; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; font-weight: bold;">
                                    🎧 Listen to Story
                                </a>
                            </div>
                            """
                            email_engine.send_email(heir_email, subject, html)
                            st.toast(f"Release email sent to {heir_email}")
                        # -----------------------------------------------
                        
                        st.success("Project Approved! Audio Unlocked.")
                        time.sleep(2)
                        st.rerun()

    # --- TAB: ACTION (CONSUME CREDIT) ---
    with tab_action:
        st.subheader("Start a New Family Archive")
        st.info(f"Cost: 1 Credit (Balance: {credits})")

        with st.form("activation_form"):
            c_name = st.text_input("Client Name (The Senior)")
            c_phone = st.text_input("Client Phone (For Interviews)")
            h_name = st.text_input("Heir Name (Beneficiary)")
            h_email = st.text_input("Heir Email (For Delivery)")
            prompt = st.text_area("Strategic Question", "Why did you choose VerbaPost to protect your family's legacy?")
            
            submitted = st.form_submit_button("🚀 Consume Credit & Invite")
            
            if submitted:
                # 1. Validation
                if credits < 1:
                    st.error("Insufficient Credits. Please contact Admin.")
                    st.stop()
                    
                if not c_name or not h_email:
                    st.error("Client Name and Heir Email are required.")
                    st.stop()

                # 2. Consume Credit & Create Project
                try:
                    success, msg = database.create_b2b_project(
                        advisor_email=user_email,
                        client_name=c_name,
                        client_phone=c_phone,
                        heir_name=h_name,
                        heir_email=h_email,
                        prompt=prompt
                    )
                    
                    if success:
                        # --- 📧 EMAIL INJECTION: THE INVITE ---
                        if email_engine:
                            subject = f"Invitation: Family Legacy Archive (Sponsored by {firm_name})"
                            invite_link = "https://verbapost.streamlit.app"
                            
                            html = f"""
                            <div style="font-family: serif; color: #333; padding: 20px;">
                                <h2 style="color: #2c3e50;">You have been invited.</h2>
                                <p>Dear {h_name},</p>
                                <p><strong>{firm_name}</strong> has sponsored a private Family Archive for you to preserve your stories.</p>
                                <p>We have scheduled an automated biography interview for <strong>{c_name}</strong>. The stories will be preserved for you.</p>
                                <br>
                                <a href="{invite_link}" style="background-color: #2c3e50; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px;">
                                    Access Your Archive
                                </a>
                            </div>
                            """
                            email_engine.send_email(h_email, subject, html)
                            st.toast(f"Invite sent to {h_email}")
                        # --------------------------------------

                        st.success("✅ Client Activated! Invitation Sent.")
                        time.sleep(2)
                        st.rerun()
                    else:
                        st.error(f"Activation Failed: {msg}")
                        
                except Exception as e:
                    st.error(f"System Error: {e}")