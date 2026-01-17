import streamlit as st
import pandas as pd
import time
import database
import payment_engine
import email_engine 
import audit_engine 

def render_advisor_portal():
    """
    The Advisor Portal (B2B View).
    Simplified Layout: No "Briefcase", Activate First, Email-Only Instructions.
    """
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
    
    # --- 2. COMPACT HEADER ---
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

    # --- 3. MAIN TABS (ACTIVATE IS NOW FIRST) ---
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
            st.markdown("""
            Enter the recipient's details below to create their private vault.
            
            **⚠️ IMPORTANT NOTIFICATION PROTOCOL:**
            * **Email Only:** The client will receive an immediate **Welcome Email** from VerbaPost (on your behalf).
            * **No Physical Letter:** We do *not* mail a physical notification card at this stage.
            * **Action:** We recommend you send a personal follow-up note to let them know to look for the email.
            """)
            
            if credits < 1:
                st.warning(f"⚠️ Balance: {credits}. Please purchase a credit above to proceed.")
            
            with st.form("activate_client_form"):
                c_name = st.text_input("Recipient Name (The Heir)", placeholder="e.g. Sarah Jones")
                c_email = st.text_input("Recipient Email", placeholder="e.g. sarah@example.com")
                # Removed Phone Number field as requested to simplify flow
                
                submitted = st.form_submit_button("🚀 Send Gift (Deduct 1 Credit)", disabled=(credits < 1))
                
                if submitted:
                    if credits < 1:
                        st.error("Insufficient Credits.")
                    elif not c_email or not c_name:
                        st.error("Name and Email are required.")
                    else:
                        with st.spinner("Provisioning Vault & Sending Email..."):
                            # Create User (Passing empty string for phone since we removed input)
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
                                email_engine.send_heir_welcome_email(
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
                                
                                st.success(f"🎉 Success! Welcome email sent to {c_email}.")
                                time.sleep(2)
                                st.rerun()
                            else:
                                st.error(f"Activation Failed: {msg}")

    # === TAB 2: CLIENT ROSTER ===
    with tab2:
        st.subheader("Your Sponsored Families")
        clients = database.fetch_advisor_clients(user_email)
        
        if not clients:
            st.info("No active clients found.")
        else:
            # Simple, clean table
            df = pd.DataFrame(clients)
            # Filter to show only useful columns if they exist
            cols = [c for c in ['full_name', 'email', 'created_at', 'status'] if c in df.columns]
            st.dataframe(df[cols] if cols else df, use_container_width=True)

    # === TAB 3: MEDIA LOCKER ===
    with tab3:
        st.subheader("Media Approvals")
        st.markdown("When a family finishes a recording, it will appear here. Toggle **Release** to unlock the audio for them.")
        
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