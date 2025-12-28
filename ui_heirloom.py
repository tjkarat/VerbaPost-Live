import streamlit as st
import time
import textwrap
import hashlib
import os
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
try: import heirloom_engine # NEW: For Audio/Vault Logic
except ImportError: heirloom_engine = None
try: import storage_engine # NEW: For Audio Playback
except ImportError: storage_engine = None

# --- HELPER: EMAIL SENDER ---
def _send_receipt(user_email, subject, body_html):
    """Sends simple alerts via Resend."""
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
    """Renders the Digital Vault Annual Pass paywall with integrated Promo entry."""
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,700;1,400&display=swap');
    
    .paywall-container {
        max-width: 800px;
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
        font-size: 38px;
        color: #1f2937;
        margin-bottom: 10px;
        font-weight: 700;
    }
    .paywall-sub {
        color: #4b5563;
        font-size: 20px;
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
        font-size: 64px;
        color: #b91c1c; 
        font-weight: 700;
    }
    .price-freq {
        font-size: 18px;
        color: #6b7280;
        text-transform: uppercase;
        letter-spacing: 1px;
        font-weight: 600;
    }
    .feature-list {
        text-align: left;
        display: inline-block;
        color: #374151;
        font-size: 18px;
        margin: 0 auto 30px auto;
    }
    .feature-item {
        margin-bottom: 15px;
        display: flex;
        align-items: center;
    }
    .check {
        color: #059669;
        margin-right: 15px;
        font-size: 20px;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

    # Main Card logic
    html_content = textwrap.dedent("""
        <div class="paywall-container">
            <div class="lock-icon">🔒</div>
            <div class="paywall-title">The Family Archive Annual Pass</div>
            <div class="paywall-sub">"The easiest way to record, transcribe, and preserve your family history."</div>
            
            <div class="price-box">
                <span class="price-amount">$190</span><span class="price-freq"> / Per Year</span>
                <p style="color: #6b7280; font-size: 14px; margin-top: 10px;">Equivalent to just $15.83/month</p>
            </div>

            <div class="feature-list">
                <div class="feature-item"><span class="check">✔</span> <b>48 Story Recording Sessions:</b> Capture a new memory every week.</div>
                <div class="feature-item"><span class="check">✔</span> <b>Protected Vault:</b> Full access to edit, copy, and export your history.</div>
                <div class="feature-item"><span class="check">✔</span> <b>48 Keepsake Letters:</b> Mailed on heavy cream paper.</div>
                <div class="feature-item"><span class="check">✔</span> <b>Automated Interviews:</b> We call your loved ones for you.</div>
                <div class="feature-item"><span class="check">✔</span> <b>AI Transcription:</b> Audio converted to text automatically.</div>
                <div class="feature-item"><span class="check">✔</span> <b>Permanent Storage:</b> We hold the legacy so you don't have to.</div>
            </div>
        </div>
    """).strip()

    st.html(html_content)
    
    # Action Buttons & Promo Entry (Now visibly associated with the card)
    c_left, c_pay, c_promo, c_right = st.columns([0.5, 2, 2, 0.5])
    
    with c_pay:
        if st.button("🔓 Unlock with Stripe", type="primary", use_container_width=True):
            user_email = st.session_state.get("user_email")
            if payment_engine:
                with st.spinner("Connecting to Secure Checkout..."):
                    try:
                        url = payment_engine.create_checkout_session(
                            line_items=[{
                                "price_data": {
                                    "currency": "usd",
                                    "product_data": {"name": "VerbaPost Family Archive - Annual Pass"},
                                    "unit_amount": 19000,
                                },
                                "quantity": 1,
                            }],
                            user_email=user_email,
                            draft_id="SUBSCRIPTION_INIT"
                        )
                        if url: st.link_button("👉 Proceed to Checkout", url, type="primary", use_container_width=True)
                        else: st.error("Link creation failed.")
                    except Exception as e: st.error(f"Error: {e}")
    
    with c_promo:
        # Integrated promo logic
        with st.container(border=True):
            promo_input = st.text_input("Have an Access Code?", placeholder="Enter Code", label_visibility="collapsed")
            if st.button("Redeem Code", use_container_width=True):
                if promo_engine:
                    valid, val = promo_engine.validate_code(promo_input)
                    if valid:
                        user_email = st.session_state.get("user_email")
                        if database:
                            database.update_user_credits(user_email, 1) # Small trial
                            if "user_profile" in st.session_state:
                                st.session_state.user_profile["credits"] = 1
                        
                        # AUDIT LOG
                        if audit_engine:
                            audit_engine.log_event(user_email, "PROMO_REDEEMED", metadata={"code": promo_input})

                        st.balloons()
                        st.success("Access Granted!")
                        time.sleep(1)
                        st.rerun()
                    else: 
                        st.error(f"Invalid: {val}")

# --- MAIN DASHBOARD RENDERER ---
def render_dashboard():
    # --- CRITICAL INITIALIZATION ---
    p_phone = None  
    credits = 0
    
    if not st.session_state.get("authenticated"):
        st.warning("Please log in to access the archive.")
        return ""

    user_email = st.session_state.get("user_email")
    
    # Ensure profile is synced
    if not st.session_state.get("profile_synced") and database:
        profile = database.get_user_profile(user_email)
        st.session_state.user_profile = profile or {}
        st.session_state.profile_synced = True
    
    profile = st.session_state.get("user_profile", {})
    credits = profile.get("credits", 0)
    p_phone = profile.get("parent_phone") 
    
    # ---------------------------------------------------------
    # HEADER
    # ---------------------------------------------------------
    col_title, col_status = st.columns([3, 1])
    with col_title: 
        st.title("📚 The Family Archive")
        st.markdown("**Welcome to your private family library of voices and legacy stories.**")
    
    with col_status: 
        st.metric("Annual Letter Credits", credits)

    # --- THE GATE (Vault-First Protection) ---
    if credits <= 0:
        render_paywall()
        return ""

    # --- TABS ---
    tab_settings, tab_int, tab_inbox = st.tabs(["⚙️ Settings & Setup", "📞 Start Interview", "📥 Stories (Inbox)"])

    # --- TAB A: SETTINGS ---
    with tab_settings:
        st.markdown("### ⚙️ Account Configuration")
        st.info("💡 **How it works:** We call the person in **Step 1** to record their stories. When you are ready to mail a keepsake, we send it to the address in **Step 2**.")

        c_parent, c_user = st.columns(2)
        
        with c_parent:
            st.markdown("#### Step 1: Who are we calling?")
            st.caption("This is the person whose stories you want to capture.")
            with st.form("settings_parent"):
                curr_p_name = profile.get("parent_name", "")
                curr_p_phone = profile.get("parent_phone", "")
                new_p_name = st.text_input("Interviewee Name", value=curr_p_name, placeholder="e.g. Grandma Betty")
                new_p_phone = st.text_input("Their Phone Number", value=curr_p_phone, placeholder="e.g. 615-555-1212")
                
                st.markdown("---")
                if st.form_submit_button("💾 Save Interviewee Details"):
                    if database:
                        if database.update_heirloom_settings(user_email, new_p_name, new_p_phone):
                            st.session_state.user_profile.update({'parent_name': new_p_name, 'parent_phone': new_p_phone})
                            
                            # AUDIT LOG
                            if audit_engine:
                                audit_engine.log_event(user_email, "SETTINGS_UPDATE_PARENT", metadata={"name": new_p_name, "phone": new_p_phone})

                            st.success("✅ Details Saved!")
                            time.sleep(1)
                            st.rerun()

        with c_user:
            st.markdown("#### Step 2: Where do we mail letters?")
            st.caption("Finished keepsakes will be mailed to this address.")
            with st.form("settings_address"):
                n_name = st.text_input("Recipient Name", value=profile.get("full_name", ""))
                n_street = st.text_input("Street Address", value=profile.get("address_line1", ""))
                n_city = st.text_input("City", value=profile.get("address_city", ""))
                col_st, col_zp = st.columns(2)
                n_state = col_st.text_input("State", value=profile.get("address_state", ""))
                n_zip = col_zp.text_input("Zip Code", value=profile.get("address_zip", ""))
                
                st.markdown("---")
                if st.form_submit_button("💾 Save Mailing Address"):
                    if database:
                        if database.update_user_address(user_email, n_name, n_street, n_city, n_state, n_zip):
                            st.session_state.user_profile.update({
                                "full_name": n_name, 
                                "address_line1": n_street,
                                "address_city": n_city,
                                "address_state": n_state,
                                "address_zip": n_zip
                            })
                            
                            # AUDIT LOG
                            if audit_engine:
                                audit_engine.log_event(user_email, "SETTINGS_UPDATE_ADDRESS", metadata={"zip": n_zip})

                            st.success("✅ Address Updated!")

    # --- TAB B: INTERVIEWER ---
    with tab_int:
        st.markdown("### 🎙️ The Remote Interviewer")
        
        if not p_phone:
            st.warning("⚠️ **Wait!** You must complete **Step 1** in the Settings tab before you can start an interview.")
            st.stop()

        # VAULT CHOKE POINT: Limit recording sessions
        if credits <= 0:
            st.warning("🔒 **Recorder Locked:** You have reached your trial limit. Purchase an Annual Pass to ask more questions.")
            st.stop()

        st.markdown("""
        <div style="background-color: #f0f7ff; border-left: 5px solid #007bff; padding: 15px; border-radius: 5px; margin-bottom: 20px;">
        <b>How to perform an interview:</b><br>
        1. Select a topic question below.<br>
        2. Click 'Call Now'. We will dial your loved one immediately.<br>
        3. They will hear a greeting and the question. After the tone, they tell their story.<br>
        4. Once they hang up, the recording is processed and appears in your Inbox.
        </div>
        """, unsafe_allow_html=True)

        topic_options = [
            "Tell me about your favorite childhood memory.",
            "How did you meet your spouse?",
            "What was your first house like?",
            "What is the best advice you ever received?",
            "Tell me about your favorite family holiday tradition.",
            "Custom Question..."
        ]
        topic = st.selectbox("Select a Topic to Record", topic_options)
        if topic == "Custom Question...":
            topic = st.text_input("Type your own question here...")

        # ACTIVE CALL LOCK Logic
        call_lock = False
        if "last_call_time" in st.session_state:
            elapsed = time.time() - st.session_state.last_call_time
            if elapsed < 300: # 5 Minute Lock
                call_lock = True
                st.warning(f"⏳ **Call in Progress:** Please wait {int((300 - elapsed)/60)} more minutes before starting a new interview.")

        if st.button("📞 Start Call Now", type="primary", use_container_width=True, disabled=call_lock):
            allowed, msg = database.check_call_limit(user_email) if database else (True, "")
            if not allowed:
                st.error(msg)
            elif ai_engine:
                with st.spinner(f"Dialing {p_phone}..."):
                    sid, err = ai_engine.trigger_outbound_call(
                        p_phone, 
                        "+16156567667", 
                        parent_name=profile.get("parent_name", "Mom"), 
                        topic=topic
                    )
                    if sid:
                        st.session_state.last_call_time = time.time()
                        if database: database.update_last_call_timestamp(user_email)
                        
                        # AUDIT LOG
                        if audit_engine:
                            audit_engine.log_event(user_email, "INTERVIEW_STARTED", metadata={"sid": sid, "topic": topic})

                        st.success(f"✅ Connection initiated! (SID: {sid})")
                        st.info("Please wait for your loved one to finish speaking before checking the Inbox.")
                        time.sleep(2)
                        st.rerun()
                    else: st.error(f"Call Error: {err}")

    # --- TAB C: INBOX (Story Protection) ---
    with tab_inbox:
        # PROTECT FROM COPY-PASTE (CSS INJECTION)
        st.markdown("""
        <style>
        .stTextArea textarea {
            user-select: none; /* Block copying */
            -webkit-user-select: none;
        }
        </style>
        """, unsafe_allow_html=True)

        st.markdown("### 📥 Captured Stories")
        st.caption("New recordings are automatically transcribed and saved here.")
        
        # --- NEW: INTEGRATED ARCHIVE ENGINE ---
        if st.button("🔄 Check for New Recordings", use_container_width=True):
            if not p_phone:
                st.error("⚠️ Set 'Parent Phone' in Settings first.")
            elif heirloom_engine: 
                # AUDIT LOG (SCAN START)
                if audit_engine:
                    audit_engine.log_event(user_email, "ARCHIVE_SCAN_INITIATED", metadata={"target": p_phone})

                with st.spinner(f"Scanning calls from {p_phone} & Archiving..."):
                    # Uses the new engine to download, upload to Vault, and transcribe
                    transcript, audio_path, err = heirloom_engine.process_latest_call(p_phone, user_email)
                    
                    if transcript:
                        if database: 
                            # Save with the new audio_ref column
                            d_id = database.save_draft(
                                user_email, 
                                transcript, 
                                "Heirloom", 
                                0.0, 
                                audio_ref=audio_path
                            )
                            # AUDIT LOG (SUCCESS)
                            if audit_engine:
                                audit_engine.log_event(user_email, "DRAFT_CREATED", metadata={"id": d_id, "source": "Heirloom"})

                        st.success("✅ Story Archived & Transcribed!")
                        time.sleep(1)
                        st.rerun()
                    else: 
                        msg = f"No new recordings found. ({err})" if err else "No new recordings found."
                        st.warning(msg)

        st.divider()

        all_drafts = database.get_user_drafts(user_email) if database else []
        heirloom_drafts = [d for d in all_drafts if d.get('tier') == 'Heirloom']

        if not heirloom_drafts:
            st.info("Your inbox is empty. Try starting an interview!")
        
        for d in heirloom_drafts:
            d_id = d['id']
            d_status = d.get('status', 'Draft')
            status_color = "green" if d_status == "Draft" else "blue"
            
            with st.expander(f"📜 Story from {d.get('created_at')} ({d_status})", expanded=(d_status == "Draft")):
                # VAULT PROTECTION: Block viewing/editing if credits exhausted
                if credits <= 0:
                    st.error("🔒 **Story Locked:** Upgrade to the Annual Pass to read the full transcript, edit details, or download copies.")
                    st.caption(f"Snippet: {d.get('content', '')[:100]}...")
                    continue
                
                # --- NEW LAYOUT: TEXT FIRST (HERO) ---
                st.markdown("**Transcript Editor**")
                txt = st.text_area("Review and edit the transcription here.", value=d.get('content'), height=300, key=f"edit_{d_id}")
                
                # SAVE BUTTON
                if st.button("💾 Save Changes", key=f"s_{d_id}"):
                    if database:
                        database.update_draft_data(d_id, content=txt)
                        # AUDIT LOG
                        if audit_engine:
                            audit_engine.log_event(user_email, "DRAFT_SAVED", metadata={"id": d_id})
                        st.toast("Saved!")

                # --- AUDIO PLAYER (SECONDARY/COLLAPSED) ---
                d_audio = d.get('audio_ref')
                if d_audio and storage_engine:
                    with st.expander("🎧 Listen to Original Audio"):
                        url = storage_engine.get_signed_url(d_audio)
                        if url:
                            st.audio(url, format="audio/mp3")
                        else:
                            st.caption("Audio unavailable (Link Expired or Missing)")
                
                # MAILING LOGIC
                if d_status == "Draft":
                    st.markdown("---")
                    st.markdown("#### 📮 The Flight Check")
                    
                    # Flight Check Logic
                    r_name = profile.get("full_name", "")
                    r_addr = profile.get("address_line1", "")
                    s_name = profile.get("parent_name", "The Family Archive")

                    if not r_addr:
                        st.warning("⚠️ **Missing Address:** Please go to 'Settings' and add a mailing address before sending.")
                    else:
                        st.markdown(f"""
                        <div style="background-color: #f8f9fa; border: 1px solid #dee2e6; padding: 15px; border-radius: 8px;">
                        <b>Ready to Mail:</b><br>
                        • <b>Sender:</b> {s_name}<br>
                        • <b>Destination:</b> {r_name}, {r_addr}<br>
                        • <b>Service:</b> Vintage Keepsake Letter (Heavy Cream Paper)<br>
                        • <b>Cost:</b> 1 Credit (Balance: {credits})
                        </div>
                        """, unsafe_allow_html=True)
                        
                        if st.button("🚀 Send Keepsake Mail", key=f"send_{d_id}", type="primary"):
                            if credits > 0:
                                with st.spinner("Preparing Mailer..."):
                                    # 1. Generate PDF first
                                    to_addr = {"name": r_name, "address_line1": r_addr, "city": profile.get("address_city"), "state": profile.get("address_state"), "zip_code": profile.get("address_zip")}
                                    from_addr = {"name": s_name, "address_line1": profile.get("address_line1", "The Family Archive")}
                                    pdf_bytes = letter_format.create_pdf(txt, to_addr, from_addr, tier="Vintage") if letter_format else b""

                                    # 2. Attempt mailing
                                    tracking_id = mailer.send_letter(pdf_bytes, to_addr, from_addr, tier="Vintage") if mailer else None

                                    # 3. Only deduct credits on SUCCESS
                                    if tracking_id and database:
                                        database.update_user_credits(user_email, credits - 1)
                                        database.update_draft_data(d_id, status="Sent", tracking_number=tracking_id)
                                        
                                        # AUDIT LOG (CRITICAL)
                                        if audit_engine:
                                            audit_engine.log_event(user_email, "MAIL_SENT", metadata={"draft_id": d_id, "tracking": tracking_id})

                                        st.success(f"✅ Dispatched! Ref: {tracking_id}")
                                        st.balloons()
                                        time.sleep(2)
                                        st.rerun()
                                    else:
                                        st.error("❌ Mailing failed. Credits not deducted.")
                            else:
                                st.error("Insufficient Credits.")
                else:
                    st.success(f"This story was mailed on {d.get('created_at')}.")

    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("<div style='text-align: center; color: #9ca3af; font-size: 14px;'>Helping families preserve their history, one phone call at a time.</div>", unsafe_allow_html=True)
    
    return