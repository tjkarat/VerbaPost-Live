import streamlit as st
import pandas as pd
import time
import database
import payment_engine
import email_engine 
import audit_engine 

def render_dashboard():
    """
    The Advisor Portal (B2B View).
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
    
    # --- 2. HEADER AREA ---
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("💼 Advisor Portal")
        st.markdown(f"**Firm:** {firm_name}")
    with col2:
        st.metric(label="Available Credits", value=credits)
        if st.button("➕ Buy Credits"):
            checkout_url = payment_engine.create_checkout_session(
                line_items=[{
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': 'Legacy Project Credit',
                            'description': '1 Credit = 1 Family Archive (30-Day Access)'
                        },
                        'unit_amount': 9900, 
                    },
                    'quantity': 1,
                }],
                user_email=user_email,
                mode='payment'
            )
            if checkout_url:
                st.link_button("Go to Checkout ($99)", checkout_url)

    st.divider()

    # --- 3. MAIN TABS ---
    tab1, tab2, tab3 = st.tabs(["👥 Client Roster", "🔐 Media Locker", "🚀 Activate Client"])

    # === TAB 1: CLIENT ROSTER ===
    with tab1:
        st.subheader("Your Sponsored Families")
        clients = database.fetch_advisor_clients(user_email) 
        
        if not clients:
            st.info("No active clients found. Use the 'Activate Client' tab to start your first project.")
        else:
            df = pd.DataFrame(clients)
            display_cols = [c for c in df.columns if c in ['full_name', 'email', 'created_at', 'status']]
            st.dataframe(df[display_cols] if display_cols else df, use_container_width=True)

    # === TAB 2: MEDIA LOCKER (FIXED) ===
    with tab2:
        st.subheader("Global Media Archive")
        st.markdown("Manage digital access for your clients. Toggle **Release** to unlock audio for the heir.")
        
        # 1. Fetch Projects
        projects = database.get_advisor_projects_for_media(user_email)
        
        if not projects:
            st.info("No media projects found yet.")
        else:
            for p in projects:
                with st.expander(f"📁 {p.get('heir_name', 'Unknown')} - {p.get('created_at', 'Undated')}"):
                    c1, c2 = st.columns([3, 1])
                    
                    with c1:
                        st.write(f"**Story Content:** {str(p.get('content', ''))[:100]}...")
                        if p.get('audio_ref'):
                            st.audio(p.get('audio_ref'))
                        elif p.get('tracking_number') and "http" in str(p.get('tracking_number')):
                             st.audio(p.get('tracking_number'))
                        else:
                            st.caption("No audio recording available.")

                    with c2:
                        # 2. Release Toggle
                        is_released = p.get('audio_released', False)
                        
                        # Use a unique key for each toggle
                        if st.toggle("🔓 Release to Heir", value=is_released, key=f"tog_{p['id']}"):
                            if not is_released:
                                database.toggle_media_release(p['id'], True)
                                st.toast("Audio Unlocked!")
                                if audit_engine:
                                    audit_engine.log_event(user_email, "Media Released", metadata={"project_id": p['id']})
                                time.sleep(0.5)
                                st.rerun()
                        else:
                            if is_released:
                                database.toggle_media_release(p['id'], False)
                                st.toast("Audio Locked.")
                                time.sleep(0.5)
                                st.rerun()

    # === TAB 3: ACTIVATE CLIENT ===
    with tab3:
        st.subheader("Start a New Family Archive")
        
        if credits > 0:
            st.success(f"✅ You have {credits} credit(s) available.")
        else:
            st.warning("⚠️ Cost: 1 Credit ($99). Balance: 0.")

        with st.form("activate_client_form"):
            st.write("Enter the details of the **Senior (Interviewee)** or the **Heir (Manager)**.")
            c_name = st.text_input("Client Name (The Senior)")
            c_phone = st.text_input("Client Phone", placeholder="(615) ...")
            c_email = st.text_input("Client Email")
            
            submitted = st.form_submit_button("🚀 Launch Legacy Project")
            
            if submitted:
                if credits < 1:
                    st.error("Insufficient Credits.")
                elif not c_email:
                    st.error("Client Email is required.")
                else:
                    with st.spinner("Provisioning Vault & Notifying Heir..."):
                        success, msg = database.create_sponsored_user(
                            advisor_email=user_email,
                            client_name=c_name,
                            client_email=c_email,
                            client_phone=c_phone
                        )
                        
                        if success:
                            new_balance = credits - 1
                            database.update_user_credits(user_email, new_balance)
                            
                            email_engine.send_heir_welcome_email(
                                to_email=c_email,
                                advisor_firm=firm_name,
                                advisor_name=advisor_full_name
                            )
                            
                            if audit_engine:
                                audit_engine.log_event(user_email, "Client Activated", metadata={"client_email": c_email, "credit_spent": 1})
                            
                            st.success(f"🎉 Project Activated for {c_name}! Invitation sent to {c_email}.")
                            time.sleep(2)
                            st.rerun()
                        else:
                            st.error(f"Activation Failed: {msg}")

    st.divider()

    # --- 4. FIRM SETTINGS (FIXED) ---
    with st.expander("⚙️ Firm Settings & Branding"):
        st.write("Update how your firm name appears on client letters and emails.")
        
        current_firm_name = profile.get("advisor_firm", "")
        col_s1, col_s2 = st.columns([3, 1])
        with col_s1:
            new_firm_name = st.text_input("Firm Name", value=current_firm_name, key="setting_firm_name")
        
        with col_s2:
            st.write("") 
            st.write("") 
            if st.button("Save Branding", use_container_width=True):
                if new_firm_name:
                    if database.update_advisor_firm_name(user_email, new_firm_name):
                        st.success("✅ Branding Updated!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Save Failed. Please try again.")
                else:
                    st.warning("Firm name cannot be empty.")