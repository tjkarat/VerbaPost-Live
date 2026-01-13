import streamlit as st
import database
import json

# --- IMPORTS ---
try: import payment_engine
except ImportError: payment_engine = None
try: import secrets_manager
except ImportError: secrets_manager = None

def render_dashboard():
    """
    The 'Quarterback' Dashboard for Wealth Managers.
    Includes Payment Gating: Advisors must have credits to authorize gifts.
    """
    user_email = st.session_state.get("user_email")
    advisor = database.get_or_create_advisor(user_email)
    
    credits = advisor.get('credits', 0)
    
    # 1. HEADER & GLOBAL STATS
    st.title("🏛️ VerbaPost | Advisor Quarterback")
    st.caption(f"Connected as {user_email} | {advisor.get('firm_name', 'Unregistered Firm')}")

    # 2. STATS BAR
    clients = database.get_clients(user_email)
    pending = database.get_pending_approvals(user_email)
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Available Credits", credits, delta_color="normal")
    c2.metric("Active Projects", len(clients))
    c3.metric("Pending Approval", len(pending))
    c4.metric("Heir Retention", "100%")

    # 3. PRIMARY TABS
    tab_auth, tab_roster, tab_queue, tab_settings = st.tabs([
        "🚀 Authorize Gift", "👥 Client Roster", "📝 Approval Queue", "⚙️ Firm Settings"
    ])

    # --- TAB: AUTHORIZATION ---
    with tab_auth:
        st.subheader("Authorize a Legacy Package")
        
        # --- THE PAYWALL GATE ---
        if credits < 1:
            st.warning("⚠️ Insufficient Credits. You need 1 Credit ($99) to activate a new family project.")
            
            st.markdown("""
            <div style="background-color: #f9fafb; padding: 20px; border-radius: 10px; border: 1px solid #e5e7eb; text-align: center;">
                <h3 style="color: #1f2937; margin:0;">Purchase Client Activation</h3>
                <p style="color: #6b7280;">Includes Concierge Interview, Transcription, Hosting, and 1 Physical Keepsake.</p>
                <h2 style="color: #059669; font-size: 40px; margin: 10px 0;">$99</h2>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("💳 Purchase Credit ($99)", type="primary", use_container_width=True):
                if payment_engine:
                    # FIX: Use a B2B Price ID or dynamic Amount
                    # Assuming standard checkout session logic
                    url = payment_engine.create_checkout_session(
                        line_items=[{
                            "price_data": {
                                "currency": "usd",
                                "product_data": {"name": "Legacy Client Activation"},
                                "unit_amount": 9900, # $99.00
                            },
                            "quantity": 1,
                        }],
                        user_email=user_email,
                        mode="payment",
                        draft_id="ADVISOR_CREDIT" # Metadata flag
                    )
                    if url: st.link_button("👉 Proceed to Secure Checkout", url)
                    else: st.error("Payment Error.")
                else:
                    st.error("Payment Engine Missing.")
            
            st.info("Once purchased, you will be redirected here to enter client details.")
            
        else:
            # --- THE AUTHORIZATION FORM (Only shown if Credit > 0) ---
            st.success(f"✅ Credit Available ({credits}). Fill out the form below to consume 1 credit.")
            
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

                if st.form_submit_button("🚀 Consume Credit & Generate Link"):
                    if not p_name or not p_phone or not h_name or not h_email:
                        st.error("Please fill out all required fields.")
                    else:
                        # 1. Deduct Credit
                        if database.deduct_advisor_credit(user_email, 1):
                            # 2. Create Project
                            database.add_client(user_email, p_name, p_phone, address_dict={}) 
                            proj_id = database.create_hybrid_project(user_email, p_name, p_phone, h_name, prompt)
                            
                            if proj_id:
                                st.success("✅ Authorized! Send this link to the heir:")
                                # Simplified link logic; assumes user will login with heir email
                                st.code(f"https://app.verbapost.com/?role=heir") 
                                st.info(f"Tell them to log in with: {h_email}")
                                st.balloons()
                                # Refresh to update credit counter
                                # st.rerun() 
                        else:
                            st.error("Transaction Error: Could not deduct credit.")

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
        
        if not pending:
            st.info("No transcripts currently waiting for review.")
        else:
            for p in pending:
                pid = p.get('id')
                p_parent = p.get('parent_name', 'Unknown')
                p_heir = p.get('heir_name', 'Unknown')
                content = p.get('content', '')
                
                with st.expander(f"Review: {p_parent} to {p_heir}"):
                    edited_content = st.text_area("Final Edit", value=content, height=300, key=f"edit_{pid}")
                    
                    if st.button("✅ Approve for Physical Mail", key=f"appr_{pid}", type="primary"):
                        database.update_project_details(pid, content=edited_content, status="Approved")
                        st.success("Dispatched to printing!")
                        st.rerun()

    # --- TAB: FIRM SETTINGS ---
    with tab_settings:
        st.subheader("Firm Branding")
        with st.form("firm_details"):
            new_firm = st.text_input("Firm Name", value=advisor.get('firm_name', ''))
            if st.form_submit_button("💾 Save Profile"):
                 st.info("Feature coming soon.")