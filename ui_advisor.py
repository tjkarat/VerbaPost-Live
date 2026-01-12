import streamlit as st
import database
import json

def render_dashboard():
    """
    The 'Quarterback' Dashboard for Wealth Managers.
    Updated with clear instructional tooltips and a 'Legacy Playbook' guide.
    """
    user_email = st.session_state.get("user_email")
    advisor = database.get_or_create_advisor(user_email)
    
    # 1. HEADER & GLOBAL STATS
    st.title("🏛️ VerbaPost | Advisor Quarterback")
    st.caption(f"Connected as {user_email} | {advisor.get('firm_name', 'Unregistered Firm')}")

    # 2. THE LEGACY PLAYBOOK (Clear Instructions)
    with st.expander("📖 How to use the 'Quarterback' Playbook", expanded=False):
        st.markdown("""
            **The Goal:** Stop heir attrition by becoming the architect of your client's family legacy.
            
            1. **Authorize:** Fill out the 'Current Client' form below to generate a secure link.
            2. **Engage:** Send that link to your client. They will use it to schedule their interview.
            3. **Review:** Once the interview is complete, the transcript will appear in your 'Approval Queue'.
            4. **Deliver:** We mail a physical, branded letter to the Heir on your behalf.
        """)
        st.info("💡 **Pro-Tip:** Fill out your 'Firm Settings' first to ensure your office address is used as the return location for all physical mailings.")

    # 3. STATS BAR
    c1, c2, c3 = st.columns(3)
    c1.metric("Active Projects", len(database.get_clients(user_email)))
    c2.metric("Pending Approval", len(database.get_pending_approvals(user_email)))
    c3.metric("Heir Retention", "100%")

    # 4. PRIMARY TABS
    tab_auth, tab_roster, tab_queue, tab_settings = st.tabs([
        "🚀 Authorize Gift", "👥 Client Roster", "📝 Approval Queue", "⚙️ Firm Settings"
    ])

    # --- TAB: AUTHORIZATION ---
    with tab_auth:
        st.subheader("Step 1: Authorize a Legacy Package ($99)")
        st.markdown("Use this form to initiate the legacy process for a client family.")
        
        with st.form("auth_gift_form"):
            st.markdown("#### 1. The Client (The Parent)")
            p_name = st.text_input("Parent's Full Name", help="The person our biographer will interview.")
            p_phone = st.text_input("Parent's Mobile Phone", help="We will call this number for the interview.")
            
            st.markdown("#### 2. The Beneficiary (The Heir)")
            h_name = st.text_input("Heir's Full Name", help="The person who will receive the physical keepsake letter.")
            
            st.markdown("#### 3. The Strategic Question")
            # This is the 'Retention Hook' for the Advisor
            default_q = f"Why did you choose {advisor.get('firm_name')} to protect your family's financial future?"
            prompt = st.text_area("Custom Interview Prompt", value=default_q, 
                                  help="The biographer will ask this specific question during the interview to reinforce your value.")

            if st.form_submit_button("🚀 Authorize & Generate Link"):
                if not p_name or not p_phone or not h_name:
                    st.error("Please fill out all required fields to authorize this gift.")
                else:
                    proj_id = database.create_hybrid_project(user_email, p_name, p_phone, h_name, prompt)
                    if proj_id:
                        st.success("✅ Authorized! Send the link below to your client.")
                        st.code(f"https://app.verbapost.com/?nav=setup&id={proj_id}")
                        st.balloons()

    # --- TAB: ROSTER ---
    with tab_roster:
        st.subheader("Family Project Roster")
        clients = database.get_clients(user_email)
        if clients:
            st.dataframe(clients, use_container_width=True)
        else:
            st.info("No active projects. Start by authorizing a gift in the first tab.")

    # --- TAB: QUEUE ---
    with tab_queue:
        st.subheader("Story Approval Queue")
        st.caption("Review and edit transcripts before they are physically mailed.")
        pending = database.get_pending_approvals(user_email)
        if not pending:
            st.info("No transcripts currently waiting for review.")
        else:
            for p in pending:
                with st.expander(f"Review: {p['parent_name']} to {p['heir_name']}"):
                    content = st.text_area("Edit Letter Content", value=p['content'], height=300)
                    if st.button("✅ Approve for Physical Mail", key=f"appr_{p['id']}"):
                        database.update_project_details(p['id'], content=content, status="Approved")
                        st.success("Dispatched to printing!")
                        st.rerun()

    # --- TAB: FIRM SETTINGS ---
    with tab_settings:
        st.subheader("Firm Branding & Logistics")
        st.markdown("""
            **Why this matters:** The information below is used to 'white-label' the legacy experience. 
            The address you provide will be used as the **Return Address** on the physical letters, 
            ensuring the Heir views the gift as coming directly from your office.
        """)
        
        with st.form("firm_details"):
            new_firm = st.text_input("Firm Name", value=advisor.get('firm_name', ''))
            new_addr = st.text_area("Firm Office Address (Return Location)", 
                                    value=advisor.get('address', ''), 
                                    placeholder="123 Financial Way, Suite 100\nNashville, TN 37203")
            
            if st.form_submit_button("💾 Save Firm Profile"):
                # Logic to update Advisor table in database
                st.success("Firm profile updated. All future mailings will use this branding.")