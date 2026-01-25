import streamlit as st
import pandas as pd
import time
# NOTE: Engines are imported INSIDE the function to prevent Circular Import Crash

def render_advisor_portal():
    """
    The Advisor Portal (B2B View).
    Detailed Instructions Restored + Resend Functionality.
    """
    # --- LAZY IMPORTS (Fixes KeyError: 'database') ---
    import database
    import payment_engine
    import email_engine 
    import audit_engine 

    # --- 1. AUTH & PROFILE ---
    if not st.session_state.get("authenticated"):
        st.warning("Please log in to access the Advisor Portal.")
        return

    user_email = st.session_state.user_email
    profile = database.get_user_profile(user_email)
    
    if not profile:
        st.error("User profile not found.")
        return

    # Basic Variables
    firm_name = profile.get("advisor_firm") or "Unspecified Firm"
    credits = profile.get("credits", 0)
    advisor_full_name = profile.get("full_name", "Your Advisor")
    
    # --- 2. HEADER ---
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("💼 Advisor Portal")
        # Display Firm Name prominently so they know who they are operating as
        if firm_name and firm_name != "Unspecified Firm":
            st.caption(f"Operating as: **{firm_name}**")
        else:
            st.error("⚠️ Firm Name Not Set (See Step 1 Below)")
            
    with col2:
        # Simple Credit Counter
        st.metric(label="Credits", value=credits)
        if st.button("➕ Add", help="Purchase additional client licenses"):
            checkout_url = payment_engine.create_checkout_session(
                line_items=[{
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': 'Legacy Project Credit',
                            'description': '1 Credit = 1 Family Archive'
                        },
                        'unit_amount': 9900, 
                    },
                    'quantity': 1,
                }],
                user_email=user_email,
                mode='payment'
            )
            if checkout_url:
                st.link_button("Pay $99", checkout_url)

    st.divider()

    # --- 3. MAIN TABS ---
    tab1, tab2, tab3 = st.tabs(["🚀 Activate Client", "👥 Client Roster", "🔐 Media Locker"])

    # === TAB 1: ACTIVATE CLIENT (DEFAULT) ===
    with tab1:
        
        # --- STEP 1: BRANDING ---
        with st.container(border=True):
            st.markdown("#### Step 1: Confirm Firm Branding")
            st.info(f"**Current Label:** {firm_name}")
            st.caption("""
            **Why is this important?** This name appears in the 'From' field of the notification email sent to your client.
            Ensure it is recognizable (e.g., 'Smith Wealth Management').
            """)
            
            with st.expander("🖊️ Edit Firm Name"):
                new_firm_name = st.text_input("New Firm Name", value=firm_name)
                if st.button("Save Branding"):
                    if new_firm_name:
                        database.update_advisor_firm_name(user_email, new_firm_name)
                        st.success("Branding Updated!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.warning("Name cannot be empty.")

        st.write("") # Spacer

        # --- STEP 2: GIFTING ---
        with st.container(border=True):
            st.markdown("#### Step 2: Send the Gift")
            st.warning("""
            **⚠️ REQUIREMENTS (Please Read):**
            
            1. **Purchase Required:** You must purchase credits ($99/client) using the 'Add' button above to proceed.
            2. **The Hand-off:** Clicking 'Send Gift' deducts 1 Credit and immediately emails the client.
            3. **Client Action Required:** The client **must log in** to VerbaPost using that email to enter the Senior's phone number and schedule the interview.
            """)
            
            st.markdown("""
            **Notification Protocol:**
            * **Email Only:** We send a digital Welcome Email immediately.
            * **No Physical Card:** We do *not* mail a physical notification card at this stage.
            * **Your Role:** We recommend sending a personal follow-up note telling them to look for an email from VerbaPost.
            """)
            
            if credits < 1:
                st.error(f"⚠️ Insufficient Funds: You have {credits} credits. Please click 'Add' above to purchase a credit ($99).")
            
            with st.form("activate_client_form"):
                c_name = st.text_input("Recipient Name (The Heir)", placeholder="e.g. Sarah Jones")
                c_email = st.text_input("Recipient Email", placeholder="e.g. sarah@example.com")
                
                submitted = st.form_submit_button("🚀 Send Gift (Deduct 1 Credit)", disabled=(credits < 1))
                
                if submitted:
                    if credits < 1:
                        st.error("Insufficient Credits. Please purchase a credit ($99) to proceed.")
                    elif not c_email or not c_name:
                        st.error("Name and Email are required.")
                    else:
                        with st.spinner("Provisioning Vault & Sending Welcome Email..."):
                            # Create User
                            success, msg = database.create_sponsored_user(
                                advisor_email=user_email,
                                client_name=c_name,
                                client_email=c_email,
                                client_phone="" 
                            )
                            
                            if success:
                                # Deduct Credit
                                new_balance = credits - 1
                                database.update_user_credits(user_email, new_balance)
                                
                                # Send Email
                                email_sent = email_engine.send_heir_welcome_email(
                                    to_email=c_email,
                                    advisor_firm=firm_name,
                                    advisor_name=advisor_full_name
                                )
                                
                                if audit_engine:
                                    audit_engine.log_event(
                                        user_email, 
                                        "Client Activated", 
                                        metadata={"client_email": c_email, "credit_spent": 1}
                                    )
                                
                                if email_sent:
                                    st.success(f"🎉 Success! Welcome email sent to {c_email}.")
                                    st.info("The client can now log in to setup their interview.")
                                else:
                                    st.warning(f"User created, but email failed to send. Use the 'Resend' button in the Client Roster tab.")
                                
                                time.sleep(3)
                                st.rerun()
                            else:
                                st.error(f"Activation Failed: {msg}")

    # === TAB 2: CLIENT ROSTER (UPDATED WITH RESEND) ===
    with tab2:
        st.subheader("Your Sponsored Families")
        st.info("""
        **What is this?** This is your master list of all gifts you have sent.
        **Use it to:** Monitor who has accepted their gift and their current account status.
        **Resend Feature:** If a client missed their welcome email, click "Resend Invite" to trigger it again.
        """)
        
        clients = database.fetch_advisor_clients(user_email)
        
        if not clients:
            st.info("No active clients found.")
        else:
            # Header Row
            c1, c2, c3 = st.columns([2, 3, 2])
            c1.markdown("**Name**")
            c2.markdown("**Email**")
            c3.markdown("**Action**")
            st.divider()
            
            # Client Rows
            for client in clients:
                c1, c2, c3 = st.columns([2, 3, 2])
                c1.write(client.get('full_name', 'Unknown'))
                c2.write(client.get('email', 'Unknown'))
                
                # Action Button: Resend Email
                if c3.button("📧 Resend Invite", key=f"resend_{client.get('id', client.get('email'))}"):
                    with st.spinner("Resending Welcome Email..."):
                        sent = email_engine.send_heir_welcome_email(
                            to_email=client.get('email'),
                            advisor_firm=firm_name,
                            advisor_name=advisor_full_name
                        )
                        if sent:
                            st.toast(f"✅ Email sent to {client.get('email')}", icon="📨")
                        else:
                            st.error("Failed to send. Please check configuration.")
                st.divider()

    # === TAB 3: MEDIA LOCKER ===
    with tab3:
        st.subheader("Media Approvals")
        st.info("""
        **What is this?** This is your Quality Control center.
        **How it works:** When a family finishes a recording, it appears here first (Locked). 
        You can listen to the audio or read the transcript. When you are satisfied, click **'Release'** to unlock it for the family.
        """)
        
        projects = database.get_advisor_projects_for_media(user_email)
        
        if not projects:
            st.info("No recordings pending review.")
        else:
            for p in projects:
                with st.expander(f"📁 {p.get('heir_name', 'Unknown')} - {p.get('created_at', 'Undated')}"):
                    c1, c2 = st.columns([3, 1])
                    
                    with c1:
                        st.write(f"**Transcript Preview:** {str(p.get('content', ''))[:150]}...")
                        # Audio Player Logic
                        audio_src = p.get('audio_ref') or p.get('tracking_number')
                        if audio_src and "http" in str(audio_src):
                             st.audio(audio_src)
                        else:
                            st.caption("Audio processing...")

                    with c2:
                        is_released = p.get('audio_released', False)
                        if st.toggle("🔓 Release Audio", value=is_released, key=f"tog_{p['id']}"):
                            if not is_released:
                                database.toggle_media_release(p['id'], True)
                                st.toast("Audio Unlocked for Heir!")
                                time.sleep(0.5)
                                st.rerun()
                        else:
                            if is_released:
                                database.toggle_media_release(p['id'], False)
                                st.toast("Audio Locked.")
                                time.sleep(0.5)
                                st.rerun()