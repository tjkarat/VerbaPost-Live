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

def render_dashboard():
    # 1. AUTH CHECK
    if not st.session_state.get("authenticated") or not st.session_state.get("is_partner"):
        st.error("Access Denied: Partner Portal")
        return

    user_email = st.session_state.get("user_email")
    
    # 2. HEADER & METRICS
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
            # Display as DataFrame for professional look
            df = pd.DataFrame(clients)
            # Clean up columns for display
            display_df = df[['client_name', 'client_phone', 'status', 'created_at']].copy()
            display_df.columns = ["Client Name", "Phone", "Status", "Date Added"]
            st.dataframe(display_df, use_container_width=True, hide_index=True)
            
            # Action Buttons per Client
            st.markdown("### ⚡ Quick Actions")
            selected_client = st.selectbox("Select Client", [c['client_name'] for c in clients])
            
            if selected_client:
                # Find client object
                c_obj = next((c for c in clients if c['client_name'] == selected_client), None)
                if c_obj:
                    col_call, col_view = st.columns(2)
                    with col_call:
                        if st.button(f"📞 Call {selected_client} Now"):
                            if ai_engine:
                                with st.spinner(f"Dialing {c_obj['client_phone']}..."):
                                    # Trigger Call
                                    sid, err = ai_engine.trigger_outbound_call(
                                        c_obj['client_phone'],
                                        "+16156567667", # VerbaPost Number
                                        parent_name=c_obj['client_name'],
                                        topic="your childhood home" # Default topic
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
        
        # 1. Select Client to Review
        review_client = st.selectbox("Select Client for Review", ["Select..."] + [c['client_name'] for c in clients])
        
        if review_client != "Select...":
            # 2. Fetch Stories
            stories = database.get_client_stories(user_email, review_client)
            
            if not stories:
                st.warning("No recorded stories found for this client.")
                if st.button("🔄 Refresh Stories"):
                    # Here we would trigger the 'fetch from Twilio' logic logic
                    st.toast("Checking Twilio logs...")
            else:
                for story in stories:
                    with st.expander(f"Draft {story['created_at'].strftime('%Y-%m-%d')} | {story['status']}", expanded=True):
                        # Editor
                        new_content = st.text_area("Edit Transcript", value=story['content'], height=300, key=f"edit_{story['id']}")
                        
                        c_save, c_approve = st.columns([1, 2])
                        with c_save:
                            if st.button("💾 Save Draft", key=f"save_{story['id']}"):
                                database.update_draft_data(story['id'], content=new_content)
                                st.toast("Draft Saved")
                        
                        with c_approve:
                            # THE FINRA/MANUAL FORK
                            if st.button("✅ Approve for Print ($99 Package)", key=f"appr_{story['id']}", type="primary"):
                                # 1. Mark as "Queued (Manual)" - Bypasses API
                                # 2. Set Price to $99 (Compliance)
                                # 3. Generate PDF for Admin to download later
                                
                                database.update_draft_data(
                                    story['id'], 
                                    content=new_content, 
                                    status="Queued (Manual)", 
                                    price=99.00,
                                    tier="Legacy Partner"
                                )
                                st.success("Approved! This letter is now in the Manual Fulfillment Queue.")
                                time.sleep(2)
                                st.rerun()

if __name__ == "__main__":
    render_dashboard()
