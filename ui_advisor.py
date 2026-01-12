import streamlit as st
import time
import json
import logging

# --- MODULE IMPORTS ---
try: import database
except ImportError: database = None
try: import ai_engine
except ImportError: ai_engine = None

logger = logging.getLogger(__name__)

def render_dashboard():
    # 1. SECURITY CHECK
    if not st.session_state.get("authenticated"):
        st.session_state.app_mode = "splash"
        st.rerun()

    # 2. ADVISOR CONTEXT
    user_email = st.session_state.get("user_email")
    
    if database:
        advisor = database.get_or_create_advisor(user_email)
        credits = advisor.get('credits', 0) if advisor else 0
        firm_name = advisor.get('firm_name', 'Unregistered Firm')
        full_name = advisor.get('full_name', 'Advisor')
    else:
        advisor = {}
        credits = 0
        firm_name = "System Error"
        full_name = "Advisor"

    # 3. HEADER
    st.title("VerbaPost | Wealth Retention")
    st.caption(f"{firm_name} ({user_email})")
    
    # 4. KPI CARDS
    c1, c2, c3 = st.columns(3)
    c1.metric("Retention Credits", credits)
    c2.metric("Active Clients", "0") 
    c3.metric("Pending Approval", "0") 

    st.divider()

    # 5. TABS
    tab_roster, tab_approval, tab_settings = st.tabs(["👥 Client Roster", "📝 Approval Queue", "⚙️ Firm Settings"])

    with tab_roster:
        st.subheader("Client Management")
        
        # Add Client Form
        with st.expander("➕ Add New Client"):
            with st.form("add_client_form"):
                c_name = st.text_input("Client Name")
                c_phone = st.text_input("Phone Number")
                c_addr = st.text_input("Mailing Address")
                c_city = st.text_input("City")
                col_s, col_z = st.columns(2)
                c_state = col_s.text_input("State")
                c_zip = col_z.text_input("Zip")
                
                if st.form_submit_button("Add to Roster"):
                    if database:
                        addr_obj = {"street": c_addr, "city": c_city, "state": c_state, "zip": c_zip}
                        if database.add_client(user_email, c_name, c_phone, addr_obj):
                            # --- AUDIT LOGGING RESTORED ---
                            database.save_audit_log({
                                "user_email": user_email,
                                "event_type": "B2B_ADD_CLIENT",
                                "description": f"Added client {c_name}",
                                "details": f"Phone: {c_phone}"
                            })
                            st.success(f"Added {c_name}")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("Database Error")
        
        # View Clients
        if database:
            clients = database.get_clients(user_email)
            if not clients:
                st.info("No clients found.")
            else:
                for c in clients:
                    with st.container(border=True):
                        c1, c2 = st.columns([3, 1])
                        with c1:
                            st.markdown(f"**{c.get('name')}**")
                            st.caption(f"Phone: {c.get('phone')} | Status: {c.get('status')}")
                        with c2:
                            if st.button("🎙️ Start Interview", key=f"start_{c.get('id')}", use_container_width=True):
                                proj_id = database.create_project(user_email, c.get('id'))
                                if proj_id:
                                    if ai_engine:
                                        with st.spinner("Dialing..."):
                                            sid, err = ai_engine.trigger_outbound_call(
                                                to_phone=c.get('phone'),
                                                advisor_name=full_name,
                                                firm_name=firm_name,
                                                project_id=proj_id
                                            )
                                            if sid:
                                                # --- AUDIT LOGGING RESTORED ---
                                                database.save_audit_log({
                                                    "user_email": user_email,
                                                    "event_type": "B2B_INTERVIEW_START",
                                                    "description": f"Called {c.get('name')}",
                                                    "details": f"SID: {sid}, ProjID: {proj_id}"
                                                })
                                                st.success("Call Initiated!")
                                            else:
                                                st.error(f"Call Failed: {err}")
                                else:
                                    st.error("Failed to create project.")

    with tab_settings:
        st.text_input("Firm Name", value=advisor.get('firm_name', ''))
        st.button("Save Settings")
        
        st.divider()
        if st.button("Sign Out"):
            st.session_state.authenticated = False
            st.rerun()