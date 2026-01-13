import streamlit as st
import database
import json

def render_dashboard():
    """
    The 'Quarterback' Dashboard for Wealth Managers.
    Allows authorizing new gifts and approving submitted stories.
    """
    user_email = st.session_state.get("user_email")
    advisor = database.get_or_create_advisor(user_email)
    
    # 1. HEADER & GLOBAL STATS
    st.title("🏛️ VerbaPost | Advisor Quarterback")
    st.caption(f"Connected as {user_email} | {advisor.get('firm_name', 'Unregistered Firm')}")

    # 2. STATS BAR
    # We need to fetch clients and pending approvals to populate these metrics
    clients = database.get_clients(user_email)
    pending = database.get_pending_approvals(user_email)
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Active Projects", len(clients))
    c2.metric("Pending Approval", len(pending))
    c3.metric("Heir Retention", "100%")

    # 3. PRIMARY TABS
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
            h_email = st.text_input("Heir's Email", help="We will send the invitation here.")
            
            st.markdown("#### 3. The Strategic Question")
            default_q = f"Why did you choose {advisor.get('firm_name', 'us')} to protect your family's financial future?"
            prompt = st.text_area("Custom Interview Prompt", value=default_q, 
                                  help="The biographer will ask this specific question.")

            if st.form_submit_button("🚀 Authorize & Generate Link"):
                if not p_name or not p_phone or not h_name or not h_email:
                    st.error("Please fill out all required fields.")
                else:
                    # Create Client & Project
                    # First, ensure client exists or create
                    database.add_client(user_email, p_name, p_phone, address_dict={}) # Minimal client record
                    # Create the project logic needs to be robust. 
                    # We'll use a specific helper function or repurpose create_hybrid_project
                    proj_id = database.create_hybrid_project(user_email, p_name, p_phone, h_name, prompt)
                    
                    if proj_id:
                        st.success("✅ Authorized! Send this link to the heir:")
                        st.code(f"https://app.verbapost.com/")
                        st.info(f"Tell them to log in with: {h_email}")
                        st.balloons()

    # --- TAB: ROSTER ---
    with tab_roster:
        st.subheader("Family Project Roster")
        if clients:
            st.dataframe(clients, use_container_width=True)
        else:
            st.info("No active projects.")

    # --- TAB: QUEUE (CRITICAL FLOW) ---
    with tab_queue:
        st.subheader("Story Approval Queue")
        st.caption("Review transcripts submitted by heirs. Click 'Approve' to send them to the print queue.")
        
        if not pending:
            st.info("No transcripts currently waiting for review.")
        else:
            for p in pending:
                pid = p.get('id')
                p_parent = p.get('parent_name', 'Unknown')
                p_heir = p.get('heir_name', 'Unknown')
                content = p.get('content', '')
                
                with st.expander(f"Review: {p_parent} to {p_heir}"):
                    edited_content = st.text_area("Final Edit (You can touch up typos)", value=content, height=300, key=f"edit_{pid}")
                    
                    if st.button("✅ Approve for Physical Mail", key=f"appr_{pid}", type="primary"):
                        # Update content and change status to 'Approved'
                        database.update_project_details(pid, content=edited_content, status="Approved")
                        st.success("Dispatched to printing!")
                        st.rerun()

    # --- TAB: FIRM SETTINGS ---
    with tab_settings:
        st.subheader("Firm Branding")
        with st.form("firm_details"):
            new_firm = st.text_input("Firm Name", value=advisor.get('firm_name', ''))
            
            if st.form_submit_button("💾 Save Profile"):
                # We need a db function to update advisor details. 
                # Assuming update_advisor_firm exists or using direct session update.
                # For now, simplistic feedback:
                st.warning("Feature requires DB update function.")