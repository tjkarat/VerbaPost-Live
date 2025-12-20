import streamlit as st
import time
import textwrap
from datetime import datetime

# --- MODULE IMPORTS ---
try: import database
except ImportError: database = None
try: import ai_engine
except ImportError: ai_engine = None
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

# --- HELPER: EMAIL SENDER ---
def _send_receipt(user_email, subject, body_html):
    """Safe wrapper to send receipts without crashing if engine is missing."""
    if email_engine:
        try:
            email_engine.send_email(
                to_email=user_email,
                subject=subject,
                html_content=body_html
            )
        except Exception as e:
            print(f"Email Receipt Failed: {e}")

# --- HELPER: PAYWALL RENDERER (PROFESSIONAL DESIGN) ---
def render_paywall():
    """
    Blocks access to the archive if the user has no credits.
    Includes Promo Code bypass and Stripe integration with a Premium UI.
    """
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

    html_content = textwrap.dedent("""
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
    """)
    
    st.markdown(html_content, unsafe_allow_html=True)
    
    c_pad_left, c_main, c_pad_right = st.columns([1, 2, 1])
    with c_main:
        if st.button("🔓 Subscribe Now", type="primary", use_container_width=True):
            user_email = st.session_state.get("user_email")
            if payment_engine:
                with st.spinner("Connecting to Secure Payment..."):
                    try:
                        st.session_state.pending_subscription = True
                        url = payment_engine.create_checkout_session(
                            line_items=[{
                                "price_data": {
                                    "currency": "usd",
                                    "product_data": {"name": "VerbaPost Family Archive (Monthly)"},
                                    "unit_amount": 1900,
                                },
                                "quantity": 1,
                            }],
                            user_email=user_email,
                            draft_id="SUBSCRIPTION_INIT"
                        )
                        if url:
                            st.link_button("👉 Proceed to Stripe Checkout", url, type="primary", use_container_width=True)
                        else:
                            st.error("Connection Error.")
                    except Exception as e:
                        st.error(f"Error: {e}")
            else:
                st.error("System Error: Payment Engine Missing")
        
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
                    if isinstance(result, tuple) and len(result) == 2:
                        is_valid, _ = result
                    elif isinstance(result, bool):
                        is_valid = result
                    
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
                    else:
                        st.error("Invalid Code")

# --- MAIN DASHBOARD RENDERER ---
def render_dashboard():
    # 1. AUTH CHECK
    if not st.session_state.get("authenticated"):
        st.warning("Please log in to access the archive.")
        if st.button("Go to Login"):
            st.session_state.app_mode = "login"
            st.rerun()
        return

    # 2. LOAD USER DATA
    user_email = st.session_state.get("user_email")
    if not st.session_state.get("profile_synced") and database:
        profile = database.get_user_profile(user_email)
        st.session_state.user_profile = profile or {}
        st.session_state.profile_synced = True
    
    profile = st.session_state.get("user_profile", {})
    credits = profile.get("credits", 0)
    
    # 3. HEADER
    col_title, col_status = st.columns([3, 1])
    with col_title:
        st.title("🎙️ The Family Archive")
    with col_status:
        st.metric("Credits Remaining", credits)

    # 4. PAYWALL CHECK
    if credits <= 0:
        render_paywall()
        return

    # 5. MAIN NAVIGATION TABS
    tab_inbox, tab_settings = st.tabs(["📥 Story Inbox", "⚙️ Settings & Setup"])

    # --- TAB A: INBOX ---
    with tab_inbox:
        # -- VALUE PROP / INSTRUCTION CARD --
        st.info("💡 **How it Works:** Once you set up the 'Remote Interviewer' in Settings, we will call your parent, ask them a question, and record their answer. Their story will appear here automatically for you to edit and mail.")
        
        col_act1, col_act2 = st.columns([2, 1])
        with col_act1:
            st.write("") # Spacer
        with col_act2:
            if st.button("🔄 Check for New Stories", use_container_width=True):
                parent_phone = profile.get("parent_phone")
                if not parent_phone:
                    st.error("⚠️ Set 'Parent Phone' in Settings first.")
                elif ai_engine:
                    with st.spinner("Scanning phone line..."):
                        transcript, err = ai_engine.fetch_and_transcribe_latest_call(parent_phone)
                        if transcript:
                            if database:
                                database.save_draft(user_email, transcript, "Heirloom", 0.0)
                            st.success("✅ New Story Found!")
                            time.sleep(1)
                            st.rerun()
                        elif err:
                            st.warning(f"No new stories. ({err})")
                        else:
                            st.info("No new calls found.")
        
        st.divider()

        if database:
            all_drafts = database.get_user_drafts(user_email)
            heirloom_drafts = [d for d in all_drafts if d.get('tier') == 'Heirloom']
        else:
            heirloom_drafts = []

        if not heirloom_drafts:
            st.markdown("""
                <div style="text-align: center; color: #888; padding: 40px;">
                    <h3>📭 Inbox is Empty</h3>
                    <p>Go to <b>Settings</b> to trigger your first interview call!</p>
                </div>
            """, unsafe_allow_html=True)
        
        for draft in heirloom_drafts:
            d_id = draft.get('id')
            d_date = draft.get('created_at', 'Unknown Date')
            d_status = draft.get('status', 'Draft')
            d_content = draft.get('content', '')
            status_icon = "🟢" if d_status == "Draft" else "✅ Sent"
            
            with st.expander(f"{status_icon} Story from {d_date}", expanded=(d_status == "Draft")):
                new_text = st.text_area("Edit Transcript", value=d_content, height=250, key=f"txt_{d_id}")
                c_save, c_send = st.columns([1, 4])
                with c_save:
                    if st.button("💾 Save", key=f"save_{d_id}"):
                        if database: database.update_draft_data(d_id, content=new_text)
                        st.toast("Saved changes.")
                with c_send:
                    if d_status == "Draft":
                        if st.button("📮 Send Mail (Costs 1 Credit)", key=f"send_{d_id}", type="primary"):
                            if credits > 0:
                                if address_standard:
                                    std_to = address_standard.StandardAddress(
                                        name=profile.get("full_name", "Valued Member"), 
                                        street=profile.get("address_line1", ""), 
                                        city=profile.get("address_city", ""),
                                        state=profile.get("address_state", ""),
                                        zip_code=profile.get("address_zip", "")
                                    )
                                    p_name = profile.get("parent_name", "The Family Archive")
                                    std_from = address_standard.StandardAddress(
                                        name=p_name, 
                                        street="VerbaPost Archive Ctr", 
                                        city="Nashville", 
                                        state="TN", 
                                        zip_code="37209"
                                    )
                                else:
                                    st.error("Address Module Error")
                                    st.stop()

                                if mailer and letter_format:
                                    try:
                                        with st.spinner("Printing & Mailing..."):
                                            pdf_bytes = letter_format.create_pdf(new_text, std_to, std_from, "Heirloom")
                                            ref_id = mailer.send_letter(pdf_bytes, std_to, std_from, description=f"Heirloom {d_date}")
                                            
                                            if ref_id:
                                                new_credits = credits - 1
                                                if database:
                                                    database.update_user_credits(user_email, new_credits)
                                                    database.update_draft_data(d_id, status="Sent", tracking_number=ref_id)
                                                
                                                _send_receipt(
                                                    user_email,
                                                    f"VerbaPost Sent: {d_date}",
                                                    f"<h3>Story Sent!</h3><p>Tracking: {ref_id}</p>"
                                                )

                                                if audit_engine:
                                                    audit_engine.log_event(user_email, "HEIRLOOM_SENT", metadata={"ref": ref_id})
                                                
                                                st.session_state.user_profile['credits'] = new_credits
                                                st.balloons()
                                                st.success(f"✅ Mailed! Tracking ID: {ref_id}")
                                                time.sleep(2)
                                                st.rerun()
                                            else:
                                                st.error("Mailing API Failed.")
                                    except Exception as e:
                                        st.error(f"System Error: {e}")
                                else:
                                    st.error("System modules missing.")
                            else:
                                st.error("Insufficient Credits.")
                    else:
                        st.info(f"Tracking: {draft.get('tracking_number', 'N/A')}")

    # --- TAB B: SETTINGS ---
    with tab_settings:
        st.markdown("### ⚙️ Account Configuration")
        c_parent, c_user = st.columns(2)
        
        with c_parent:
            st.markdown("#### 👵 Parent Details")
            st.caption("We use this phone number to identify incoming calls.")
            with st.form("settings_parent"):
                curr_p_name = profile.get("parent_name", "")
                curr_p_phone = profile.get("parent_phone", "")
                
                new_p_name = st.text_input("Parent Name", value=curr_p_name, placeholder="e.g. Mom")
                new_p_phone = st.text_input("Parent Phone Number", value=curr_p_phone, placeholder="e.g. 6155551234")
                
                if st.form_submit_button("Save Parent Info"):
                    if database:
                        success = database.update_heirloom_settings(user_email, new_p_name, new_p_phone)
                        if success:
                            st.session_state.user_profile['parent_name'] = new_p_name
                            st.session_state.user_profile['parent_phone'] = new_p_phone
                            st.success("Saved!")
                            st.rerun()
                        else:
                            st.error("Database Error")
            
            st.markdown("---")
            st.markdown("#### 📞 Remote Interviewer")
            st.info("Select a topic below, then click 'Call Parent Now'. We will call them immediately and ask this specific question.")
            
            # --- NEW TOPIC SELECTOR ---
            topic_options = [
                "Tell me about your childhood home.",
                "How did you meet your spouse?",
                "What was your first job like?",
                "What is your favorite family tradition?",
                "What advice would you give your younger self?",
                "Write your own question..."
            ]
            
            selected_topic = st.selectbox("Interview Topic", topic_options)
            final_topic = selected_topic
            if selected_topic == "Write your own question...":
                final_topic = st.text_input("Custom Question", placeholder="e.g. Tell me about the day I was born.")

            if st.button("Call Parent Now", type="primary"):
                p_phone = profile.get("parent_phone")
                p_name = profile.get("parent_name", "Mom")
                twilio_phone = "+16156567667"
                
                if not p_phone:
                    st.error("Please save Parent Phone first.")
                elif not final_topic:
                    st.error("Please select or write a topic.")
                elif ai_engine:
                    with st.spinner(f"Dialing {p_phone}..."):
                        # NOW PASSING TOPIC TO ENGINE
                        if hasattr(ai_engine, "trigger_outbound_call"):
                            sid, err = ai_engine.trigger_outbound_call(p_phone, twilio_phone, parent_name=p_name, topic=final_topic)
                            if sid:
                                st.success(f"Calling! SID: {sid}")
                                st.info("Wait for them to hang up, then check the Inbox tab.")
                            else:
                                st.error(f"Call Failed: {err}")
            # --------------------------

        with c_user:
            st.markdown("#### 📬 Your Mailing Address")
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
                            st.success("Address Updated!")
                            st.rerun()
                        else:
                            st.error("Update Failed")