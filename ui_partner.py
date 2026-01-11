import streamlit as st
import pandas as pd
import time
from datetime import datetime

# --- IMPORTS ---
try: import database
except ImportError: database = None
try: import ai_engine
except ImportError: ai_engine = None
try: import letter_format
except ImportError: letter_format = None
try: import email_engine
except ImportError: email_engine = None

def render_dashboard():
    # 1. DECISION TREE: Portal vs. Lead Form
    if st.session_state.get("authenticated") and st.session_state.get("is_partner"):
        render_partner_portal()
    else:
        render_lead_capture_form()

def render_lead_capture_form():
    """
    State A: Marketing Landing Page for prospective partners.
    """
    st.title("🤝 VerbaPost Partner Program")
    st.markdown("### Client Retention for the Great Wealth Transfer")
    
    st.info("We help Estate Planning Attorneys and Wealth Managers offer **Emotional Legacy Services** to deepen client relationships.")

    with st.form("partner_lead_form"):
        st.markdown("#### Request a Demo / Partner Kit")
        c1, c2 = st.columns(2)
        name = c1.text_input("Name")
        firm = c2.text_input("Firm Name")
        email = c1.text_input("Work Email")
        role = st.selectbox("Role", ["Wealth Manager", "Estate Attorney", "Family Office", "Other"])
        msg = st.text_area("How can we help?")
        
        if st.form_submit_button("Request Information", type="primary"):
            if not email or not name:
                st.error("Please provide your name and email.")
            else:
                if email_engine:
                    email_engine.send_admin_alert(
                        trigger_event="New B2B Partner Lead",
                        details_html=f"<p>Name: {name}</p><p>Firm: {firm}</p><p>Email: {email}</p>"
                    )
                st.success("Thank you! Our partnership team will contact you shortly.")
    
    st.divider()
    st.markdown("### Why Partner?")
    st.markdown("🛡️ **Retention** | 🎁 **Differentiation** | 🗝️ **Trust**")
    
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("⬅️ Back to Main Site"):
        st.session_state.app_mode = "splash"
        st.rerun()

def render_partner_portal():
    """
    State B: The Functional Dashboard for active partners.
    RESTORING DROPPED FUNCTIONALITY.
    """
    user_email = st.session_state.get("user_email")
    
    # HEADER & METRICS
    st.title("🏛️ Partner Portal")
    st.markdown("**Firm:** Estate Law Group | **Compliance:** FINRA Rule 3220 ($99 Limit)")
    
    # Fetch Data
    clients = []
    if database:
        clients = database.get_partner_clients(user_email)
    
    # Tabs
    tab_roster, tab_add, tab_stories = st.tabs(["👥 Client Roster", "➕ Add Client", "📝 Review & Approve"])

    # --- TAB A: CLIENT ROSTER ---
    with tab_roster:
        if not clients:
            st.info("No clients found. Add your first client to begin.")
        else:
            # Display as DataFrame
            df = pd.DataFrame(clients)
            # Safe column renaming if data exists
            if not df.empty and 'client_name' in df.columns:
                display_df = df[['client_name', 'client_phone', 'status', 'created_at']].copy()
                display_df.columns = ["Client Name", "Phone", "Status", "Date Added"]
                st.dataframe(display_df, use_container_width=True, hide_index=True)
            
            # Action Buttons
            st.markdown("### ⚡ Quick Actions")
            selected_client = st.selectbox("Select Client", [c['client_name'] for c in clients])
            
            if selected_client:
                c_obj = next((c for c in clients if c['client_name'] == selected_client), None)
                if c_obj:
                    col_call, col_view = st.columns(2)
                    with col_call:
                        if st.button(f"📞 Call {selected_client} Now"):
                            if ai_engine:
                                with st.spinner(f"Dialing {c_obj['client_phone']}..."):
                                    sid, err = ai_engine.trigger_outbound_call(
                                        c_obj['client_phone'],
                                        "+16156567667",
                                        parent_name=c_obj['client_name'],
                                        topic="your childhood home"
                                    )
                                    if sid:
                                        st.success(f"Call Initiated! SID: {sid}")
                                        database.update_client_status(c_obj['id'], "Interviewing")
                                    else:
                                        st.error(f"Call Failed: {err}")
                    with col_view:
                        st.info(f"Current Status: **{c_obj['status']}**")

    # --- TAB B: ADD CLIENT ---
    with tab_add:
        st.markdown("#### New Legacy Package ($99)")
        with st.form("new_client_form"):
            c_name = st.text_input("Client Name (e.g. John Doe)")
            c_phone = st.text_input("Phone Number", placeholder="555-123-4567")
            c_notes = st.text_area("Internal Notes (Optional)")
            
            if st.form_submit_button("Add to Roster"):
                if database and c_name and c_phone:
                    if database.add_partner_client(user_email, c_name, c_phone, c_notes):
                        st.success(f"✅ {c_name} added to roster.")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Database Error.")
                else:
                    st.error("Name and Phone are required.")

    # --- TAB C: GHOSTWRITER (REVIEW) ---
    with tab_stories:
        st.markdown("### 🖋️ The Ghostwriter")
        st.caption("Review transcripts, edit for clarity, and approve for manual fulfillment.")
        
        # 1. Select Client
        client_opts = ["Select..."] + [c['client_name'] for c in clients]
        review_client = st.selectbox("Select Client for Review", client_opts)
        
        if review_client != "Select...":
            # 2. Fetch Stories
            stories = database.get_client_stories(user_email, review_client)
            
            if not stories:
                st.warning("No recorded stories found for this client.")
            else:
                for story in stories:
                    with st.expander(f"Draft {story.get('created_at')} | {story.get('status')}", expanded=True):
                        new_content = st.text_area("Edit Transcript", value=story.get('content',''), height=300, key=f"edit_{story['id']}")
                        
                        c_save, c_approve = st.columns([1, 2])
                        with c_save:
                            if st.button("💾 Save Draft", key=f"save_{story['id']}"):
                                database.update_draft_data(story['id'], content=new_content)
                                st.toast("Draft Saved")
                        
                        with c_approve:
                            # THE FINRA/MANUAL FORK
                            if st.button("✅ Approve for Print ($99 Package)", key=f"appr_{story['id']}", type="primary"):
                                database.update_draft_data(
                                    story['id'], 
                                    content=new_content, 
                                    status="Queued (Manual)", 
                                    price=99.00,
                                    tier="Legacy Partner"
                                )
                                st.success("Approved! Queued for Fulfillment.")
                                time.sleep(2)
                                st.rerun()