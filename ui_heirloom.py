import streamlit as st
import time
import textwrap
import json
import os
from datetime import datetime
import uuid 
from sqlalchemy import text

# --- MODULE IMPORTS ---
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

# --- HELPER: ATOMIC DATABASE UPDATE (Heirloom Specific) ---
def _force_heirloom_update(draft_id, to_data=None, from_data=None, status=None, tracking=None):
    """
    FIXED: Uses shared database session to force save Heirloom status and addresses.
    """
    if not draft_id: return False
    
    # Force String ID to match Schema
    safe_id = str(draft_id)
    
    try:
        # Serialize
        to_json = json.dumps(to_data) if isinstance(to_data, dict) else (str(to_data) if to_data else None)
        from_json = json.dumps(from_data) if isinstance(from_data, dict) else (str(from_data) if from_data else None)
        
        # USE SHARED SESSION (Fixes Split-Brain)
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
            
            params = {
                "s": status,
                "t": tracking,
                "rd": to_json,
                "sd": from_json,
                "id": safe_id
            }

            result = session.execute(query, params)
            session.commit()
            
            if result.rowcount > 0:
                return True
            else:
                st.error(f"❌ DB Update Failed: ID {safe_id} not found.")
                return False

    except Exception as e:
        st.error(f"❌ DB Exception: {e}")
        return False

# --- HELPER: EMAIL SENDER ---
def _send_receipt(user_email, subject, body_html):
    if email_engine:
        try:
            email_engine.send_email(
                to_email=user_email,
                subject=subject,
                html_content=body_html
            )
        except Exception as e:
            print(f"Email Receipt Failed: {e}")

# --- HELPER: PAYWALL RENDERER ---
def render_paywall():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,700;1,400&display=swap');
    
    .paywall-container {
        max-width: 700px;
        margin: 20px auto;
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 12px;
        padding: 40px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.05);
        text-align: center;
        font-family: 'Helvetica Neue', sans-serif;
    }
    .lock-icon {
        font-size: 50px;
        background: #fdfbf7;
        width: 100px;
        height: 100px;
        line-height: 100px;
        border-radius: 50%;
        margin: 0 auto 20px auto;
        border: 1px solid #efebe0;
    }
    .paywall-title {
        font-family: 'Playfair Display', serif;
        font-size: 36px;
        color: #1f2937;
        margin-bottom: 10px;
        font-weight: 700;
    }
    .paywall-sub {
        color: #6b7280;
        font-size: 18px;
        margin-bottom: 30px;
        line-height: 1.6;
        font-family: 'Playfair Display', serif;
        font-style: italic;
    }
    .price-box {
        background: #f9fafb;
        border-top: 1px solid #e5e7eb;
        border-bottom: 1px solid #e5e7eb;
        padding: 30px 0;
        margin: 30px 0;
    }
    .price-amount {
        font-family: 'Playfair Display', serif;
        font-size: 52px;
        color: #b91c1c; /* Deep Red */
        font-weight: 700;
    }
    .price-freq {
        font-size: 16px;
        color: #9ca3af;
        text-transform: uppercase;
        letter-spacing: 1px;
        font-weight: 600;
    }
    .feature-list {
        text-align: left;
        display: inline-block;
        color: #374151;
        font-size: 16px;
        margin: 0 auto;
    }
    .feature-item {
        margin-bottom: 12px;
        display: flex;
        align-items: center;
    }
    .check {
        color: #059669;
        margin-right: 12px;
        font-size: 18px;
    }
    </style>
    """, unsafe_allow_html=True)

    html_content = """
<div class="paywall-container">
    <div class="lock-icon">🔒</div>
    <div class="paywall-title">The Family Archive</div>
    <div class="paywall-sub">"Capture family memories and history for future generations."</div>
    <div class="price-box">
        <span class="price-amount">$19</span><span class="price-freq"> / Month</span>
        <br><br>
        <div class="feature-list">
            <div class="feature-item"><span class="check">✔</span> 4 Mailed "Vintage" Letters per Month</div>
            <div class="feature-item"><span class="check">✔</span> Unlimited Voice Recording Storage</div>
            <div class="feature-item"><span class="check">✔</span> Private Family Dashboard</div>
            <div class="feature-item"><span class="check">✔</span> Cancel Anytime</div>
        </div>
    </div>
</div>
"""
    
    st.markdown(html_content, unsafe_allow_html=True)
    
    c_pad_left, c_main, c_pad_right = st.columns([1, 2, 1])
    with c_main:
        if st.button("🔓 Subscribe Now", type="primary", use_container_width=True):
            user_email = st.session_state.get("user_email")
            if payment_engine:
                with st.spinner("Connecting to Secure Payment..."):
                    try:
                        st.session_state.pending_subscription = True
                        
                        # --- FIX: DYNAMIC PRICE ID ---
                        # 1. Try Secrets Manager (Env Specific)
                        price_id = secrets_manager.get_secret("STRIPE_PRICE_ID")
                        
                        # 2. Fallback to Hardcoded (Live) if missing
                        if not price_id:
                            price_id = "price_1SjVdgRmmrLilo6X2d4lU7K0"

                        url = payment_engine.create_checkout_session(
                            line_items=[{
                                "price": price_id, 
                                "quantity": 1,
                            }],
                            mode="subscription",
                            user_email=user_email,
                            draft_id="SUBSCRIPTION_INIT"
                        )
                        if url: 
                            st.link_button("👉 Proceed to Stripe Checkout", url, type="primary", use_container_width=True)
                        else: 
                            st.error("Connection Error.")
                    except Exception as e: st.error(f"Error: {e}")
            else: st.error("System Error: Payment Engine Missing")
        
        st.markdown("<div style='text-align: center; color: #9ca3af; font-size: 12px; margin-top: 10px;'>Secured by Stripe SSL</div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("🎟️ Have an Access Code?", expanded=False):
        c_code, c_btn = st.columns([3, 1])
        with c_code:
            code = st.text_input("Code", label_visibility="collapsed", placeholder="Enter Promo Code")
        with c_btn:
            if st.button("Apply"):
                if promo_engine:
                    result = promo_engine.validate_code(code)
                    is_valid = False
                    if isinstance(result, tuple) and len(result) == 2: is_valid, _ = result
                    elif isinstance(result, bool): is_valid = result
                    
                    if is_valid:
                        user_email = st.session_state.get("user_email")
                        if database:
                            database.update_user_credits(user_email, 4)
                            if "user_profile" in st.session_state:
                                st.session_state.user_profile["credits"] = 4
                        _send_receipt(user_email, "Archive Unlocked", f"Welcome to the Family Archive. Code {code} applied.")
                        st.balloons()
                        st.success("Unlocked! Redirecting...")
                        time.sleep(1)
                        st.rerun()
                    else: st.error("Invalid Code")

# --- MAIN DASHBOARD RENDERER ---
def render_dashboard():
    p_phone = None  
    credits = 0
    
    if not st.session_state.get("authenticated"):
        st.warning("Please log in to access the archive.")
        if st.button("Go to Login"):
            st.session_state.app_mode = "login"
            st.rerun()
        return

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
        st.title("The Family Archive")
        st.markdown("**Preserve your loved one’s voice, stories, and memories—forever.**")
    
    with col_status: 
        st.metric(
            label="Letter Credits",
            value=credits,
            help="Each credit = 1 mailed letter (worth $5.99). Your subscription includes 4 credits per month."
        )

    if credits <= 0:
        st.warning("⚠️ **Out of Credits** - Your subscription will refill on your next billing date.")
        render_paywall()
        return

    tab_settings, tab_int, tab_inbox = st.tabs(["⚙️ Settings & Setup", "📞 Start Interview", "📥 Stories (Inbox)"])

    # --- TAB A: SETTINGS ---
    with tab_settings:
        st.markdown("### ⚙️ Account Setup")
        st.info("ℹ️ **Important:** We need to know who to call (the interviewee) and where to mail the finished letters (you).")

        c_parent, c_user = st.columns(2)
        with c_parent:
            st.markdown("#### Step 1: Who are we interviewing?")
            st.caption("We will call this person to record stories.")
            with st.form("settings_parent"):
                curr_p_name = profile.get("parent_name", "")
                curr_p_phone = profile.get("parent_phone", "")
                new_p_name = st.text_input("Their Name (e.g. Grandma)", value=curr_p_name)
                new_p_phone = st.text_input("Their Phone Number", value=curr_p_phone, placeholder="e.g. 615-555-1234")
                if st.form_submit_button("Save Interviewee"):
                    if database:
                        success = database.update_heirloom_settings(user_email, new_p_name, new_p_phone)
                        if success:
                            st.session_state.user_profile['parent_name'] = new_p_name
                            st.session_state.user_profile['parent_phone'] = new_p_phone
                            st.success("✅ Saved!")
                            time.sleep(1)
                            st.rerun()
                        else: st.error("Database Error")

        with c_user:
            st.markdown("#### Step 2: Where should we mail letters?")
            st.caption("When you click 'Send', the physical letter goes here.")
            with st.form("settings_address"):
                curr_name = profile.get("full_name", "")
                curr_street = profile.get("address_line1", "")
                curr_city = profile.get("address_city", "")
                curr_state = profile.get("address_state", "")
                curr_zip = profile.get("address_zip", "")
                
                n_name = st.text_input("Your Name", value=curr_name)
                n_street = st.text_input("Street Address", value=curr_street)
                n_city = st.text_input("City", value=curr_city)
                
                col_st, col_zp = st.columns(2)
                n_state = col_st.text_input("State", value=curr_state)
                n_zip = col_zp.text_input("Zip Code", value=curr_zip)
                
                if st.form_submit_button("Save My Address"):
                    if database:
                        success = database.update_user_address(
                            user_email, n_name, n_street, n_city, n_state, n_zip
                        )
                        if success:
                            st.session_state.user_profile.update({
                                "full_name": n_name,
                                "address_line1": n_street,
                                "address_city": n_city,
                                "address_state": n_state,
                                "address_zip": n_zip
                            })
                            st.success("✅ Address Updated!")
                            st.rerun()
                        else: st.error("Update Failed")

    # --- TAB B: INTERVIEWER ---
    with tab_int:
        st.markdown("### 🎙️ The Remote Interviewer")
        
        if not p_phone:
            st.warning("⚠️ Please complete **Step 1** in the Settings tab to add a phone number.")
            st.stop()
        
        st.success(f"📞 **Pro Tip:** You (or {profile.get('parent_name', 'they')}) can also call **(615) 656-7667** anytime from **{p_phone}** to record a story on your own terms.")
        
        st.info("💡 **Pre-Call Tip:** Text them beforehand! *'The robot is going to ask about [Topic]. Just gather your thoughts!'* It makes the call feel like a chat, not a quiz.")

        st.divider()

        topic_options = [
            "Tell me about your childhood home.",
            "How did you meet your spouse?",
            "What was your first job like?",
            "What is your favorite family tradition?",
            "What advice would you give your younger self?",
            "Write your own question..."
        ]
        selected_topic = st.selectbox("1. Choose a Topic", topic_options)
        
        final_topic = selected_topic
        if selected_topic == "Write your own question...":
            final_topic = st.text_input("Type your question here", placeholder="e.g. Tell me about the day I was born.")

        st.markdown("---")
        
        col_now, col_later = st.columns(2)
        with col_now:
            st.markdown("#### Option A: Call Immediately")
            st.caption("We will dial their number right now.")
            if st.button("📞 Call Now", type="primary", use_container_width=True):
                allowed, msg = database.check_call_limit(user_email)
                if not allowed:
                    st.error(msg)
                elif ai_engine:
                    with st.spinner(f"Dialing {p_phone}..."):
                        sid, err = ai_engine.trigger_outbound_call(
                            p_phone, 
                            "+16156567667",
                            parent_name=profile.get("parent_name", "Mom"), 
                            topic=final_topic
                        )
                        if sid:
                            database.update_last_call_timestamp(user_email)
                            st.success(f"Connecting... (SID: {sid})")
                            st.info("Wait for them to answer and finish speaking. Then check the 'Stories' tab.")
                        else: st.error(f"Call Failed: {err}")

        with col_later:
            st.markdown("#### Option B: Schedule for Later")
            st.info("""
            **How Scheduling Works:**
            1. Pick a date & time below.
            2. We save this to your account.
            3. On that day, you will receive an **email reminder** to initiate the call manually.
            """)
            
            d = st.date_input("Date", help="When do you want to do the interview?")
            t = st.time_input("Time", help="Select a time")
            
            if st.button("📅 Schedule Reminder", use_container_width=True):
                combined_time = datetime.combine(d, t)
                if database.schedule_call(user_email, p_phone, final_topic, combined_time):
                    st.success(f"✅ Saved! We've added this to your schedule for {d} at {t}.")
                else:
                    st.error("Scheduling failed.")

    # --- TAB C: INBOX ---
    with tab_inbox:
        st.markdown("### 📥 Your Story Inbox")
        
        if st.button("🔄 Check for New Recordings"):
            if not p_phone:
                st.error("⚠️ Set 'Parent Phone' in Settings first.")
            elif heirloom_engine:
                with st.spinner(f"Scanning for calls from {p_phone}..."):
                    transcript, audio_path, err = heirloom_engine.process_latest_call(p_phone, user_email)
                    if transcript:
                        if database: 
                            database.save_draft(user_email, transcript, "Heirloom", 0.0, audio_ref=audio_path)
                        st.success("✅ New Story Found!")
                        time.sleep(1)
                        st.rerun()
                    else: 
                        st.warning(f"No new recordings found. ({err})")
            else:
                st.error("Heirloom Engine not loaded.")
        
        st.divider()

        if database:
            all_drafts = database.get_user_drafts(user_email)
            heirloom_drafts = [d for d in all_drafts if d.get('tier') == 'Heirloom']
        else: heirloom_drafts = []

        if not heirloom_drafts:
            st.markdown("<div style='text-align:center; color:#888;'>No stories yet. Try calling!</div>", unsafe_allow_html=True)
        
        for draft in heirloom_drafts:
            d_id = draft.get('id')
            d_date = draft.get('created_at', 'Unknown Date')
            d_status = draft.get('status', 'Draft')
            d_content = draft.get('content', '')
            status_icon = "🟢" if d_status == "Draft" else "✅ Sent"
            
            with st.expander(f"{status_icon} Story from {d_date}", expanded=(d_status == "Draft")):
                
                new_text = st.text_area("Edit Story Transcript", value=d_content, height=250, key=f"txt_{d_id}")
                
                c_save, c_send = st.columns([1, 1])
                with c_save:
                    if st.button("💾 Save Changes", key=f"save_{d_id}", use_container_width=True):
                        if database: database.update_draft_data(d_id, content=new_text)
                        st.toast("Saved changes.")
                
                st.divider()

                if d_status == "Draft":
                    st.markdown("#### 📮 Mail this Story")
                    
                    recipient_name = profile.get("full_name", "")
                    recipient_street = profile.get("address_line1", "")
                    recipient_city = profile.get("address_city", "")
                    sender_name = profile.get("parent_name", "The Family Archive")
                    
                    if not recipient_street or not recipient_city:
                        st.warning("⚠️ **Missing Address:** Go to the 'Settings' tab.")
                    else:
                        st.info(f"""
                        **Flight Check:**
                        • **From:** {sender_name}
                        • **To:** {recipient_name}, {recipient_street}
                        • **Cost:** 1 Credit (Balance: {credits})
                        """)
                        
                        if st.button("🚀 Send Mail (1 Credit)", key=f"send_{d_id}", type="primary"):
                            if credits > 0:
                                snapshot_to = {
                                    "name": recipient_name, "street": recipient_street, 
                                    "city": recipient_city, "state": profile.get("address_state", ""), 
                                    "zip": profile.get("address_zip", "")
                                }
                                snapshot_from = {
                                    "name": sender_name, "street": "VerbaPost Archive Ctr", 
                                    "city": "Nashville", "state": "TN", "zip": "37209"
                                }

                                ref_id = f"MANUAL_{str(uuid.uuid4())[:8].upper()}"
                                
                                new_credits = credits - 1
                                if database:
                                    database.update_user_credits(user_email, new_credits)
                                    
                                    # --- ATOMIC UPDATE CALL ---
                                    if _force_heirloom_update(d_id, snapshot_to, snapshot_from, "Queued (Manual)", ref_id):
                                        st.success("Data secured in DB.")
                                    else:
                                        st.error("DB Write Failed.")
                                
                                # 1. NOTIFY ADMIN (NEW)
                                if email_engine:
                                    email_engine.send_admin_alert(
                                        trigger_event="New Heirloom Letter",
                                        details_html=f"""
                                        <p><strong>User:</strong> {user_email}</p>
                                        <p><strong>Ref ID:</strong> {ref_id}</p>
                                        <p><strong>Status:</strong> Queued for Manual Print</p>
                                        """
                                    )

                                # 2. NOTIFY USER
                                _send_receipt(
                                    user_email,
                                    f"VerbaPost Sent: {d_date}",
                                    f"<h3>Story Queued!</h3><p>Your letter is in the manual print queue.</p><p>ID: {ref_id}</p>"
                                )
                                if audit_engine:
                                    audit_engine.log_event(user_email, "HEIRLOOM_SENT_MANUAL", metadata={"ref": ref_id})
                                
                                st.session_state.user_profile['credits'] = new_credits
                                st.balloons()
                                st.success(f"✅ Queued for Printing! ID: {ref_id}")
                                time.sleep(2)
                                st.rerun()
                            else: st.error("Insufficient Credits. Please top up.")
                else:
                    st.success(f"Sent! Tracking Number: {draft.get('tracking_number', 'N/A')}")

    st.markdown("<br><br><br>", unsafe_allow_html=True)
    st.markdown("<div style='text-align: center; color: #888; font-style: italic;'>VerbaPost helps families save voices, stories, and moments—before they’re gone.</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    render_dashboard()