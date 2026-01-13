import streamlit as st
import pandas as pd
import time
import base64

# --- MODULE IMPORTS ---
try: import database
except ImportError: database = None
try: import letter_format
except ImportError: letter_format = None
try: import audit_engine
except ImportError: audit_engine = None

def render_admin_page():
    """
    The B2B Admin Console.
    Primary Task: Fulfillment of 'Approved' Advisor Projects.
    """
    st.title("⚙️ Admin Console (B2B Mode)")
    
    # 1. TABS
    tab_print, tab_logs, tab_health = st.tabs(["🖨️ Manual Print Queue", "📊 System Logs", "❤️ Health"])

    # --- TAB: PRINT QUEUE ---
    with tab_print:
        st.subheader("Ready for Fulfillment")
        st.caption("These projects have been approved by the Advisor and are ready to print.")
        
        # 1. FETCH APPROVED PROJECTS
        # We need a specific DB query for this status
        if database:
            # Helper logic: We can write a raw query or add a helper in database.py
            # For this snippet, let's assume get_all_approved_projects exists or we mimic it
            with database.get_db_session() as session:
                # Import Project model locally to avoid circular import issues if placed at top
                from database import Project, Advisor
                
                # Fetch Approved
                items = session.query(Project).filter_by(status='Approved').all()
                
                if not items:
                    st.info("Queue is empty. No approved projects.")
                else:
                    for proj in items:
                        # Fetch Advisor for Footer
                        adv = session.query(Advisor).filter_by(email=proj.advisor_email).first()
                        firm_name = adv.firm_name if adv else "VerbaPost"
                        
                        with st.expander(f"🖨️ {proj.heir_name} (Sponsored by {firm_name})"):
                            st.text_area("Content Preview", value=proj.content, height=150, disabled=True)
                            
                            # GENERATE PDF BUTTON
                            if st.button(f"⬇️ Generate PDF", key=f"pdf_{proj.id}"):
                                if letter_format:
                                    # Create Mock Addresses for the PDF generator
                                    # In a real scenario, we'd pull these from the 'Client' table
                                    to_addr = {"name": proj.heir_name, "street": "See CRM", "city": "City", "state": "ST", "zip": "00000"}
                                    from_addr = {"name": firm_name, "street": "Advisor Office", "city": "City", "state": "ST", "zip": "00000"}
                                    
                                    pdf_bytes = letter_format.create_pdf(
                                        proj.content, 
                                        to_addr, 
                                        from_addr, 
                                        tier="Heirloom" 
                                        # Note: You might want to pass 'firm_name' to create_pdf 
                                        # if you updated letter_format.py to handle footers.
                                    )
                                    
                                    # Download Link
                                    b64 = base64.b64encode(pdf_bytes).decode()
                                    href = f'<a href="data:application/pdf;base64,{b64}" download="Letter_{proj.id}.pdf">Click to Download PDF</a>'
                                    st.markdown(href, unsafe_allow_html=True)
                                else:
                                    st.error("Letter Format Engine missing.")

                            # MARK AS SENT BUTTON
                            if st.button(f"✅ Mark as Sent", key=f"sent_{proj.id}"):
                                proj.status = "Sent"
                                session.commit()
                                st.success("Marked as Sent!")
                                time.sleep(1)
                                st.rerun()

    # --- TAB: LOGS ---
    with tab_logs:
        st.subheader("Audit Trail")
        if database:
            # Basic log viewer
            with database.get_db_session() as session:
                from database import AuditEvent
                logs = session.query(AuditEvent).order_by(AuditEvent.timestamp.desc()).limit(20).all()
                data = [{"Time": l.timestamp, "User": l.user_email, "Event": l.event_type} for l in logs]
                st.dataframe(data, use_container_width=True)

    # --- TAB: HEALTH ---
    with tab_health:
        st.subheader("System Status")
        st.success("System is running in B2B Mode.")