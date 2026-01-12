import streamlit as st
import time
import textwrap
import json
import os
from datetime import datetime
import uuid 
from sqlalchemy import text

# --- MODULE IMPORTS (COMPLETE) ---
try: import database
except ImportError: database = None
try: import secrets_manager
except ImportError: secrets_manager = None
try: import ai_engine
except ImportError: ai_engine = None
try: import heirloom_engine
except ImportError: heirloom_engine = None
try: import mailer
except ImportError: mailer = None
try: import letter_format
except ImportError: letter_format = None
try: import address_standard
except ImportError: address_standard = None
try: import audit_engine
except ImportError: audit_engine = None
try: import payment_engine
except ImportError: payment_engine = None
try: import promo_engine
except ImportError: promo_engine = None
try: import email_engine
except ImportError: email_engine = None

# --- STYLING: CSS INJECTION (PRESERVED) ---
def inject_heirloom_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,700;1,400&display=swap');
    
    .stApp { background-color: #fdfdfd; }
    
    .heirloom-header {
        font-family: 'Playfair Display', serif;
        font-size: 42px;
        font-weight: 700;
        color: #0f172a;
        margin-bottom: 5px;
    }
    .heirloom-sub {
        font-family: 'Playfair Display', serif;
        font-style: italic;
        font-size: 20px;
        color: #475569;
        margin-bottom: 30px;
    }
    .metric-container {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.02);
    }
    /* Senior-Friendly Accessibility */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 60px;
        background-color: #f8fafc;
        border-radius: 8px 8px 0 0;
        padding: 0 30px;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        background-color: #ffffff !important;
        border-top: 2px solid #0f172a !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- HELPER: ATOMIC DATABASE UPDATE (PRESERVED) ---
def _force_heirloom_update(draft_id, to_data=None, from_data=None, status=None, tracking=None):
    if not draft_id: return False
    safe_id = str(draft_id)
    try:
        to_json = json.dumps(to_data) if isinstance(to_data, dict) else (str(to_data) if to_data else None)
        from_json = json.dumps(from_data) if isinstance(from_data, dict) else (str(from_data) if from_data else None)
        
        with database.get_db_session() as session:
            query = text("""
                UPDATE letter_drafts
                SET 
                    status = :s,
                    tracking_number = :t,
                    recipient_data = :rd,
                    sender_data = :sd,
                    to_addr = :rd,
                    from_addr = :sd
                WHERE id = :id
            """)
            params = {"s": status, "t": tracking, "rd": to_json, "sd": from_json, "id": safe_id}
            result = session.execute(query, params)
            session.commit()
            return result.rowcount > 0
    except Exception as e:
        st.error(f"❌ DB Exception: {e}")
        return False

# --- HELPER: EMAIL SENDER (PRESERVED) ---
def _send_receipt(user_email, subject, body_html):
    if email_engine:
        try:
            email_engine.send_email(to_email=user_email, subject=subject, html_content=body_html)
        except Exception as e:
            logger.error(f"Email Receipt Failed: {e}")

# --- B2B DASHBOARD RENDERER (FULL) ---
def render_dashboard():
    inject_heirloom_css()
    
    if not st.session_state.get("authenticated"):
        st.warning("Please log in."); return

    user_email = st.session_state.get("user_email")
    if not st.session_state.get("profile_synced") and database:
        profile = database.get_user_profile(user_email)
        st.session_state.user_profile = profile or {}
        st.session_state.profile_synced = True
    
    profile = st.session_state.get("user_profile", {})
    credits = profile.get("credits", 0)
    p_phone = profile.get("parent_phone") 
    
    col_title, col_status = st.columns([3, 1])
    with col_title: 
        st.markdown('<div class="heirloom-header">The Family Archive</div>', unsafe_allow_html=True)
        st.markdown('<div class="heirloom-sub">"Capture family memories and history for future generations."</div>', unsafe_allow_html=True)
    
    with col_status: 
        st.markdown('<div class="metric-container">', unsafe_allow_html=True)
        st.metric(
            label="Letter Credits",
            value=credits,
            help="Each credit allows you to mail one physical keepsake letter. These are provided by your Advisor for authorized projects."
        )
        st.markdown('</div>', unsafe_allow_html=True)

    # --- B2B REFACTOR: NO INITIAL PAYWALL ---
    # We now allow users to proceed to Settings and Interview to maximize engagement.
    
    tab_settings, tab_int, tab_inbox = st.tabs(["⚙️ Settings & Setup", "📞 Start Interview", "📥 Stories (Inbox)"])

    # --- TAB A: SETTINGS ---
    with tab_settings:
        st.markdown("### ⚙️ Account Setup")
        st.info("ℹ️ **Instruction:** Provide the contact details for the interviewee and your preferred mailing address for deliverables.")

        c_parent, c_user = st.columns(2)
        with c_parent:
            st.markdown("#### Step 1: Who are we interviewing?")
            st.caption("We will call this person to record their stories.")
            with st.form("settings_parent"):
                curr_p_name = profile.get("parent_name", "")
                curr_p_phone = profile.get("parent_phone", "")
                new_p_name = st.text_input("Interviewee Name (e.g. Grandma)", value=curr_p_name)
                new_p_phone = st.text_input("Their Phone Number", value=curr_p_phone, placeholder="e.g. 615-555-1234")
                if st.form_submit_button("Save Interviewee Settings"):
                    if database:
                        if database.update_heirloom_settings(user_email, new_p_name, new_p_phone):
                            st.session_state.user_profile.update({'parent_name': new_p_name, 'parent_phone': new_p_phone})
                            st.success("✅ Settings Saved!")
                            time.sleep(1); st.rerun()
                        else: st.error("Database Update Error")

        with c_user:
            st.markdown("#### Step 2: Where should we mail letters?")
            st.caption("Finished physical letters will be dispatched to this address.")
            with st.form("settings_address"):
                n_name = st.text_input("Recipient Name", value=profile.get("full_name", ""))
                n_street = st.text_input("Street Address", value=profile.get("address_line1", ""))
                n_city = st.text_input("City", value=profile.get("address_city", ""))
                col_st, col_zp = st.columns(2)
                n_state = col_st.text_input("State", value=profile.get("address_state", ""))
                n_zip = col_zp.text_input("Zip Code", value=profile.get("address_zip", ""))
                
                if st.form_submit_button("Save Mailing Profile"):
                    if database and database.update_user_address(user_email, n_name, n_street, n_city, n_state, n_zip):
                        st.session_state.user_profile.update({
                            "full_name": n_name, "address_line1": n_street, "address_city": n_city,
                            "address_state": n_state, "address_zip": n_zip
                        })
                        st.success("✅ Mailing Address Updated!")
                        time.sleep(1); st.rerun()
                    else: st.error("Address Update Failed")

    # --- TAB B: INTERVIEWER ---
    with tab_int:
        st.markdown("### 🎙️ The Family Biographer")
        if not p_phone:
            st.warning("⚠️ Please configure Step 1 in Settings to start an interview.")
            st.stop()
        
        st.success(f"📞 **Spontaneous Entry:** They can call **(615) 656-7667** from **{p_phone}** at any time to record.")

        st.divider()
        topic_options = [
            "Tell me about your childhood home.", 
            "How did you meet your spouse?", 
            "What was your first job like?", 
            "What is your favorite family tradition?",
            "Write your own question..."
        ]
        selected_topic = st.selectbox("1. Select a Conversation Starter", topic_options)
        
        final_topic = selected_topic
        if selected_topic == "Write your own question...":
            final_topic = st.text_input("Type your question", placeholder="e.g. Tell me about the day I was born.")

        st.markdown("---")
        col_now, col_later = st.columns(2)
        with col_now:
            st.markdown("#### Option A: Call Immediately")
            st.caption("Initiate a phone call to the interviewee now.")
            if st.button("📞 Start Call Now", type="primary", use_container_width=True):
                if ai_engine:
                    with st.spinner(f"Dailing {p_phone}..."):
                        sid, err = ai_engine.trigger_outbound_call(
                            p_phone, 
                            "+16156567667", 
                            parent_name=profile.get("parent_name", "Client"), 
                            topic=final_topic
                        )
                        if sid:
                            if database: database.update_last_call_timestamp(user_email)
                            st.success("Call Initiated. Audio will appear in Inbox shortly.")
                        else: st.error(f"Call Error: {err}")

        with col_later:
            st.markdown("#### Option B: Schedule Reminder")
            st.caption("Schedule a notification to initiate an interview later.")
            d = st.date_input("Select Date")
            t = st.time_input("Select Time")
            if st.button("📅 Set Reminder", use_container_width=True):
                if database.schedule_call(user_email, p_phone, final_topic, datetime.combine(d, t)):
                    st.success("Interview reminder scheduled successfully.")
                else: st.error("Scheduling failed.")

    # --- TAB C: INBOX ---
    with tab_inbox:
        st.markdown("### 📥 Story Inbox")
        
        if st.button("🔄 Check for New Stories"):
            if heirloom_engine and p_phone:
                with st.spinner("Scanning for recent recordings..."):
                    transcript, audio_path, err = heirloom_engine.process_latest_call(p_phone, user_email)
                    if transcript:
                        if database: database.save_draft(user_email, transcript, "Heirloom", 0.0, audio_ref=audio_path)
                        st.success("New Story Found and Archived!"); time.sleep(1); st.rerun()
                    else: st.warning(f"No new recordings found. ({err})")
            else: st.error("Configuration Error: Phone or Engine missing.")

        st.divider()
        if database:
            all_drafts = database.get_user_drafts(user_email)
            heirloom_drafts = [d for d in all_drafts if d.get('tier') == 'Heirloom']
        else: heirloom_drafts = []

        if not heirloom_drafts:
            st.markdown("<div style='text-align:center; color:#888; padding: 40px;'>No stories in the archive yet. Try initiating a call!</div>", unsafe_allow_html=True)
        
        for draft in heirloom_drafts:
            did = draft.get('id')
            d_status = draft.get('status', 'Draft')
            status_icon = "🟢" if d_status == "Draft" else "✅ Sent"
            
            with st.expander(f"{status_icon} Story archived on {draft.get('created_at', 'Unknown Date')}"):
                new_text = st.text_area("Edit Transcript", value=draft.get('content', ''), height=250, key=f"txt_{did}")
                
                c_save, c_mail = st.columns([1, 1])
                with c_save:
                    if st.button("💾 Save Changes", key=f"save_{did}", use_container_width=True):
                        if database: database.update_draft_data(did, content=new_text)
                        st.toast("Edits saved successfully.")
                
                st.divider()
                if d_status == "Draft":
                    st.markdown("#### 📮 Physical Fulfillment")
                    st.info("Convert this digital transcript into a physical keepsake letter.")
                    
                    if st.button(f"🚀 Mail Keepsake (1 Credit)", key=f"m_{did}", type="primary", use_container_width=True):
                        # B2B GATE: Check credits here instead of at the start.
                        if credits > 0:
                            r_addr = {
                                "name": profile.get("full_name"), 
                                "street": profile.get("address_line1"), 
                                "city": profile.get("address_city"), 
                                "state": profile.get("address_state"), 
                                "zip": profile.get("address_zip")
                            }
                            s_addr = {
                                "name": profile.get("parent_name", "VerbaPost"), 
                                "street": profile.get("address_line1"), 
                                "city": profile.get("address_city"), 
                                "state": profile.get("address_state"), 
                                "zip": profile.get("address_zip")
                            }
                            
                            if mailer and letter_format:
                                try:
                                    pdf = letter_format.create_pdf(new_text, r_addr, s_addr, tier="Heirloom")
                                    tid = mailer.send_letter(pdf, r_addr, s_addr, tier="Heirloom", user_email=user_email)
                                    if tid:
                                        database.update_user_credits(user_email, credits - 1)
                                        _force_heirloom_update(did, r_addr, s_addr, "Sent", tid)
                                        st.success(f"Success! Physical mail dispatched (ID: {tid})")
                                        if audit_engine: audit_engine.log_event(user_email, "B2B_HEIRLOOM_SENT", metadata={"id": tid})
                                        time.sleep(2); st.rerun()
                                    else: st.error("Mailing API Error. Please contact support.")
                                except Exception as e: st.error(f"Fulfillment Exception: {e}")
                            else: st.error("Mailing Service Unavailable.")
                        else:
                            # B2B CONTEXT: Guide them to their Advisor.
                            st.error("⚠️ **No Credits Remaining.** Please contact your Financial Advisor to authorize additional Legacy Credits for your account.")
                else:
                    st.success(f"Physical Copy Sent. Tracking/Ref: {draft.get('tracking_number', 'N/A')}")

    st.markdown("<br><br><br>", unsafe_allow_html=True)
    st.markdown("<div style='text-align: center; color: #64748b; font-style: italic; border-top: 1px solid #e2e8f0; padding-top: 20px;'>VerbaPost Wealth: Preserving legacy through generations.</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    render_dashboard()