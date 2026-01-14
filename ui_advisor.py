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
    
    if not database:
        st.error("Database module missing.")
        st.stop()
        
    user_email = st.session_state.get("user_email")
    if not user_email:
        st.error("Please log in.")
        st.stop()

    advisor = database.get_advisor_profile(user_email)
    if not advisor:
        st.warning("Advisor profile not found.")
        st.stop()
        
    credits = advisor.get('credits', 0)
    firm_name = advisor.get('firm_name', 'VerbaPost Wealth')

    c1, c2 = st.columns([3, 1])
    c1.markdown(f"**Firm:** {firm_name}")
    c2.metric("Available Credits", credits)
    st.divider()

    tab_roster, tab_media, tab_action = st.tabs(["👥 Client Roster", "🔐 Media Locker", "🚀 Activate Client"])

    # --- TAB: ROSTER ---
    with tab_roster:
        st.subheader("Active Families")
        clients = database.get_advisor_clients(user_email)
        
        if not clients:
            st.info("No active clients yet.")
        
        for c in clients:
            with st.expander(f"👤 {c.get('name')} ({c.get('status')})"):
                st.write(f"**Heir:** {c.get('heir_name')}")
                st.write(f"**Email:** {c.get('email')}")
                st.write(f"**Phone:** {c.get('phone')}")

    # --- TAB: MEDIA LOCKER (CONTROL ROOM) ---
    with tab_media:
        st.subheader("Family Media Controls")
        st.caption("Unlock audio recordings for families when appropriate.")
        
        projects = database.get_advisor_projects_for_media(user_email)
        
        if not projects:
            st.info("No media archives found.")
            
        for p in projects:
            pid = p.get('id')
            heir_name = p.get('heir_name')
            status = p.get('status')
            is_released = p.get('audio_released', False)
            
            with st.container(border=True):
                c_info, c_action = st.columns([3, 1])
                
                with c_info:
                    st.markdown(f"**{heir_name}**")
                    st.caption(f"Status: {status} | Created: {str(p.get('created_at'))[:10]}")
                    if is_released:
                        st.success("✅ Audio Unlocked")
                    else:
                        st.warning("🔒 Audio Locked")

                with c_action:
                    if not is_released:
                        if st.button("🔓 Unlock", key=f"ul_{pid}", type="primary"):
                            if database.toggle_media_release(pid, True):
                                st.toast("Audio Unlocked!")
                                
                                # Notify Heir
                                if email_engine:
                                    email_engine.send_email(
                                        p.get('heir_email'), 
                                        "Audio Archive Unlocked 🔓", 
                                        f"Your advisor at {firm_name} has unlocked the audio for your family story."
                                    )
                                time.sleep(1)
                                st.rerun()
                    else:
                        if st.button("🔒 Re-Lock", key=f"lk_{pid}"):
                            database.toggle_media_release(pid, False)
                            st.rerun()

    # --- TAB: ACTION ---
    with tab_action:
        st.subheader("Start a New Family Archive")
        st.info(f"Cost: 1 Credit (Balance: {credits})")

        with st.form("activation_form"):
            c_name = st.text_input("Client Name (The Senior)")
            c_phone = st.text_input("Client Phone (For Interviews)")
            h_name = st.text_input("Heir Name (Beneficiary)")
            h_email = st.text_input("Heir Email (For Delivery)")
            prompt = st.text_area("Strategic Question", "Why did you choose VerbaPost to protect your family's legacy?")
            
            if st.form_submit_button("🚀 Consume Credit & Invite"):
                if credits < 1:
                    st.error("Insufficient Credits.")
                elif not c_name or not h_email:
                    st.error("Name and Email required.")
                else:
                    success, msg = database.create_b2b_project(
                        advisor_email=user_email,
                        client_name=c_name,
                        client_phone=c_phone,
                        heir_name=h_name,
                        heir_email=h_email,
                        prompt=prompt
                    )
                    
                    if success:
                        if email_engine:
                            email_engine.send_email(
                                h_email, 
                                f"Invitation: Family Archive (Sponsored by {firm_name})", 
                                f"You have been invited by {firm_name} to preserve your family legacy."
                            )
                        st.success("Client Activated!")
                        time.sleep(2)
                        st.rerun()
                    else:
                        st.error(f"Failed: {msg}")