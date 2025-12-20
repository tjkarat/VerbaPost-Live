import streamlit as st
import time
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
try: import email_engine  # Added for Receipts
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

# --- HELPER: PAYWALL RENDERER ---
def render_paywall():
    """
    Blocks access to the archive if the user has no credits.
    Includes Promo Code bypass and Stripe integration.
    """
    st.markdown("""
        <div style="background-color: #f8f9fa; padding: 40px; border-radius: 12px; text-align: center; border: 1px solid #e0e0e0; margin-top: 20px;">
            <div style="font-size: 60px;">🔒</div>
            <h2 style="color: #333; margin-top: 10px;">The Family Archive is Locked</h2>
            <p style="font-size: 18px; color: #555;">You need an active subscription to view, edit, and preserve family stories.</p>
            <hr style="margin: 25px 0;">
            <h1 style="color: #d93025; font-size: 48px; margin: 0;">$19<small style="font-size: 18px; color: #777;">/mo</small></h1>
            <p style="font-weight: 500;">Includes 4 Mailed Letters per month + Unlimited Voice Storage</p>
            <br>
        </div>
    """, unsafe_allow_html=True)
    
    col_promo, col_pay = st.columns([1, 1])

    # --- OPTION 1: PROMO CODE (BYPASS) ---
    with col_promo:
        with st.expander("🎟️ Have a Promo Code?", expanded=True):
            code = st.text_input("Enter Code", key="heirloom_promo")
            if st.button("Apply Code"):
                if promo_engine:
                    # Validate Code
                    result = promo_engine.validate_code(code)
                    is_valid = False
                    
                    # Robust Tuple Unpacking
                    if isinstance(result, tuple) and len(result) == 2:
                        is_valid, _ = result
                    elif isinstance(result, bool):
                        is_valid = result
                    
                    if is_valid:
                        # UNLOCK FOR FREE (Grant 4 Credits)
                        user_email = st.session_state.get("user_email")
                        if database:
                            database.update_user_credits(user_email, 4)
                            if "user_profile" in st.session_state:
                                st.session_state.user_profile["credits"] = 4
                        
                        # SEND RECEIPT (Zero Cost Invoice)
                        _send_receipt(
                            user_email, 
                            "VerbaPost Archive Unlocked", 
                            f"<p>Welcome! You have successfully unlocked the Family Archive using code <b>{code}</b>.</p><p>4 Credits have been added to your account.</p>"
                        )

                        st.balloons()
                        st.success("Code Accepted! Unlocking Archive...")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Invalid Promo Code.")
                else:
                    st.error("Promo system offline.")

    # --- OPTION 2: STRIPE CHECKOUT ---
    with col_pay:
        st.write("") # Spacer
        st.write("") # Spacer
        if st.button("🔓 Subscribe to Unlock", type="primary", use_container_width=True):
            user_email = st.session_state.get("user_email")
            
            if payment_engine:
                with st.spinner("Connecting to Stripe..."):
                    try:
                        # SET FLAG FOR MAIN.PY TO HANDLE RECEIPT ON RETURN
                        st.session_state.pending_subscription = True

                        url = payment_engine.create_checkout_session(
                            line_items=[{
                                "price_data": {
                                    "currency": "usd",
                                    "product_data": {"name": "VerbaPost Family Archive (Monthly)"},
                                    "unit_amount": 1900, # $19.00
                                },
                                "quantity": 1,
                            }],
                            user_email=user_email,
                            draft_id="SUBSCRIPTION_INIT"
                        )
                        
                        if url:
                            st.success("Link Generated!")
                            st.link_button("👉 Click Here to Pay Securely", url, type="primary", use_container_width=True)
                        else:
                            st.error("Could not generate checkout link.")
                    except Exception as e:
                        st.error(f"Payment Error: {e}")
            else:
                st.error("Payment engine missing.")

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
    
    # Ensure profile is loaded
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
        # Action Bar
        col_act1, col_act2 = st.columns([2, 1])
        with col_act1:
            st.info("💡 **Tip:** Ask Mom to call the Story Line. Her stories will appear here automatically.")
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

        # Load Drafts
        if database:
            all_drafts = database.get_user_drafts(user_email)
            heirloom_drafts = [d for d in all_drafts if d.get('tier') == 'Heirloom']
        else:
            heirloom_drafts = []

        if not heirloom_drafts:
            st.markdown("""
                <div style="text-align: center; color: #888; padding: 40px;">
                    <h3>📭 Inbox is Empty</h3>
                    <p>No stories recorded yet. Call the number to test it!</p>
                </div>
            """, unsafe_allow_html=True)
        
        # Display Drafts
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
                        if database:
                            database.update_draft_data(d_id, content=new_text)
                        st.toast("Saved changes.")
                
                with c_send:
                    if d_status == "Draft":
                        if st.button("📮 Send Mail (Costs 1 Credit)", key=f"send_{d_id}", type="primary"):
                            if credits > 0:
                                if address_standard:
                                    # Use profile name or fallback
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
                                                
                                                # SEND RECEIPT (Credit Usage)
                                                _send_receipt(
                                                    user_email,
                                                    f"VerbaPost Sent: {d_date}",
                                                    f"""
                                                    <h3>Your Family Story is on the way!</h3>
                                                    <p><b>Recipient:</b> {std_to.name}</p>
                                                    <p><b>Tracking ID:</b> {ref_id}</p>
                                                    <p><b>Remaining Credits:</b> {new_credits}</p>
                                                    """
                                                )

                                                if audit_engine:
                                                    audit_engine.log_event(user_email, "HEIRLOOM_SENT", metadata={"ref": ref_id})
                                                
                                                st.session_state.user_profile['credits'] = new_credits
                                                st.balloons()
                                                st.success(f"✅ Mailed! Tracking ID: {ref_id}")
                                                time.sleep(2)
                                                st.rerun()
                                            else:
                                                st.error("Mailing API Failed. Please contact support.")
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
            st.caption("Trigger a call to your parent right now.")
            if st.button("Call Parent Now"):
                p_phone = profile.get("parent_phone")
                twilio_phone = "+16156567667"
                
                if not p_phone:
                    st.error("Please save Parent Phone first.")
                elif ai_engine:
                    with st.spinner(f"Dialing {p_phone}..."):
                        if hasattr(ai_engine, "trigger_outbound_call"):
                            sid, err = ai_engine.trigger_outbound_call(p_phone, twilio_phone)
                            if sid:
                                st.success(f"Calling! SID: {sid}")
                                st.info("Wait for them to hang up, then check Inbox.")
                            else:
                                st.error(f"Call Failed: {err}")
                        else:
                            st.error("Outbound calling not enabled on server.")

        with c_user:
            st.markdown("#### 📬 Your Mailing Address")
            st.caption("Where should the physical letters be sent?")
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