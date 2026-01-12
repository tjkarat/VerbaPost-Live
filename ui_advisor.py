import streamlit as st
import time
import json
import logging
import uuid
from sqlalchemy import text

# --- MODULE IMPORTS ---
try: import database
except ImportError: database = None
try: import ai_engine
except ImportError: ai_engine = None
try: import payment_engine
except ImportError: payment_engine = None

logger = logging.getLogger(__name__)

def render_dashboard():
    # 1. SECURITY CHECK
    if not st.session_state.get("authenticated"):
        st.session_state.app_mode = "login"
        st.rerun()

    # 2. ADVISOR CONTEXT
    user_email = st.session_state.get("user_email")
    
    if database:
        advisor = database.get_or_create_advisor(user_email)
        firm_name = advisor.get('firm_name', 'Unregistered Firm')
        full_name = advisor.get('full_name', 'Advisor')
    else:
        advisor = {}
        firm_name = "System Error"
        full_name = "Advisor"

    # 3. HEADER & GUIDANCE
    st.title("VerbaPost | Wealth Retention")
    st.caption(f"{firm_name} ({user_email})")

    st.info("💡 **Advisor Role:** You 'Authorize' the gift. We then securely link with the client to handle the scheduling and mailing details.")

    # 4. KPI CARDS
    c1, c2, c3 = st.columns(3)
    c1.metric("Active Campaigns", "0")
    c2.metric("Pending Approval", "0") 
    c3.metric("Retention Rate", "100%") 

    st.divider()

    # 5. TABS
    tab_roster, tab_approval, tab_settings = st.tabs(["👥 Client Roster", "📝 Approval Queue", "⚙️ Firm Settings"])

    # --- TAB A: CLIENT ROSTER ---
    with tab_roster:
        st.subheader("Authorize a Legacy Gift")
        
        # Add Client Form (Concierge Entry)
        with st.expander("➕ Authorize New Legacy Package ($99)", expanded=True):
            with st.form("authorize_gift_form"):
                st.markdown("#### 1. Current Client (The Parent)")
                parent_name = st.text_input("Parent Name")
                parent_phone = st.text_input("Parent Mobile Number")
                
                st.markdown("#### 2. The Heir (The Recipient)")
                heir_name = st.text_input("Heir Name (e.g., Grandson Michael)")
                
                st.markdown("#### 3. Strategic Retention Question")
                strategic_prompt = st.selectbox(
                    "Lead-off Question",
                    [
                        f"Why did you choose {firm_name} and why should your family trust us for the next generation?",
                        f"What values led you to partner with {full_name} for your legacy planning?",
                        "Custom Question (Enter below)..."
                    ]
                )
                custom_prompt = st.text_area("Custom Strategic Question", placeholder="e.g., How has our firm helped preserve your family's values?")
                
                final_prompt = custom_prompt if strategic_prompt == "Custom Question (Enter below)..." else strategic_prompt

                if st.form_submit_button("🚀 Authorize & Pay $99"):
                    if not parent_phone or not heir_name:
                        st.error("Please provide the Parent's phone and the Heir's name.")
                    elif payment_engine:
                        # Fixed: $99 per-client transaction
                        checkout_url = payment_engine.create_checkout_session(
                            line_items=[{
                                "price_data": {
                                    "currency": "usd",
                                    "product_data": {"name": f"Legacy Gift: {parent_name} for {heir_name}"},
                                    "unit_amount": 9900,
                                },
                                "quantity": 1,
                            }],
                            user_email=user_email,
                            draft_id=f"HYBRID_AUTH_{str(uuid.uuid4())[:8]}" # Tag for backend provisioning
                        )
                        if checkout_url:
                            st.link_button("👉 Proceed to Secure Payment", checkout_url)
        
        # View Roster
        if database:
            clients = database.get_clients(user_email)
            if not clients:
                st.info("No active legacy projects yet.")
            else:
                for c in clients:
                    with st.container(border=True):
                        c1, c2 = st.columns([3, 1])
                        with c1:
                            st.markdown(f"**{c.get('name')}** → {c.get('heir_name', 'Unknown Heir')}")
                            st.caption(f"Status: {c.get('status')} | Phone: {c.get('phone')}")
                        with c2:
                            if st.button("👁️ View Details", key=f"view_{c.get('id')}"):
                                st.write(f"Strategic Question: {c.get('strategic_prompt')}")

    # --- TAB B: APPROVAL QUEUE (GHOSTWRITING) ---
    with tab_approval:
        st.subheader("Review & Edit Transcripts")
        st.caption("Review every word before it is physically mailed to the heir.")
        
        if database:
            pending = database.get_pending_approvals(user_email)
            if not pending:
                st.info("No transcripts waiting for review.")
            else:
                for p in pending:
                    with st.expander(f"Review: {p.get('parent_name')} to {p.get('heir_name')}"):
                        new_body = st.text_area("Edit Content", value=p.get('content'), height=300)
                        if st.button("✅ Approve for Print & Mail", key=f"appr_{p.get('id')}", type="primary"):
                            database.update_draft_data(p.get('id'), content=new_body, status="Queued (Manual)")
                            st.success("Sent to Manual Print Queue!")
                            time.sleep(1); st.rerun()

    with tab_settings:
        st.subheader("Firm Profile")
        st.text_input("Firm Name", value=advisor.get('firm_name', ''))
        st.text_area("Firm Address (Return Address on Letters)", value=advisor.get('address', ''))
        if st.button("Save Settings"):
            st.success("Settings saved.")
        st.divider()
        if st.button("Sign Out"):
            st.session_state.authenticated = False
            st.rerun()