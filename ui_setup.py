import streamlit as st
import database
import json
import time
from datetime import datetime

def render_parent_setup(project_id):
    """
    Branded entry point for the Parent (The Gift Recipient).
    No login required; secured by the unique Project UUID.
    """
    # 1. FETCH CONTEXT FROM DB
    # Uses the secure project_id from the URL parameter
    if not project_id:
        st.error("Invalid access link. Please contact your advisor's office.")
        return

    project = database.get_project_by_id(project_id)
    if not project:
        st.error("Legacy session not found. It may have expired or been completed.")
        return

    # 2. BRANDED HEADER
    # Fetches the firm name and advisor branding from the DB
    st.markdown(f"""
        <div style='text-align: center; padding-bottom: 20px;'>
            <h1 style='font-family: serif; color: #0f172a;'>The Family Archive</h1>
            <p style='color: #64748b; font-size: 1.1rem;'>A Legacy Gift from <b>{project.get('firm_name')}</b></p>
        </div>
    """, unsafe_allow_html=True)

    st.divider()

    # 3. CONTEXTUAL GREETING
    st.markdown(f"### Hello, {project.get('parent_name')} 👋")
    st.write(f"""
        Your advisor at **{project.get('firm_name')}** has authorized a legacy biographer to help 
        preserve your life stories and values for **{project.get('heir_name')}**.
    """)
    
    st.info(f"**The Result:** A physical, 'Vintage' letter containing your stories will be mailed to {project.get('heir_name')} with a return address from our office.")

    # 4. DATA COLLECTION FORM
    with st.form("parent_concierge_form"):
        st.markdown("#### 📮 1. Delivery Details")
        st.caption(f"Where should we mail the physical keepsakes for {project.get('heir_name')}?")
        
        # Collects the physical mailing address for the heir
        recipient_name = st.text_input("Heir's Full Name", value=project.get('heir_name'))
        street = st.text_input("Street Address")
        c1, c2, c3 = st.columns([2, 1, 1])
        city = c1.text_input("City")
        state = c2.text_input("State")
        zip_code = c3.text_input("Zip Code")

        st.markdown("---")
        
        st.markdown("#### 📅 2. Schedule Your Session")
        st.caption("Our automated biographer will call you at this time for a 15-minute story recording.")
        
        col_date, col_time = st.columns(2)
        target_date = col_date.date_input("Select a Date", min_value=datetime.today())
        target_time = col_time.time_input("Select a Time (Central Time)")

        # 5. SUBMISSION LOGIC
        if st.form_submit_button("🚀 Finalize My Legacy Session", use_container_width=True):
            if not street or not zip_code or not city:
                st.error("Please provide a complete mailing address.")
            else:
                # Construct the JSON address object for the DB
                address_data = {
                    "name": recipient_name,
                    "street": street,
                    "city": city,
                    "state": state,
                    "zip": zip_code
                }
                
                # Combine date and time for the DB
                scheduled_dt = datetime.combine(target_date, target_time)
                
                # Update project state to 'Scheduled'
                success = database.update_project_details(
                    project_id=project_id,
                    address=address_data,
                    scheduled_time=scheduled_dt,
                    status="Scheduled"
                )
                
                if success:
                    st.success("✅ Success! Your session is locked in.")
                    st.balloons()
                    st.markdown(f"""
                        <div style='background-color: #f8fafc; padding: 20px; border-radius: 8px; border: 1px solid #e2e8f0;'>
                            <p><b>Next Steps:</b></p>
                            <ul>
                                <li>We will call you at <b>{scheduled_dt.strftime('%A, %b %d at %I:%M %p')}</b>.</li>
                                <li>The call will come from our Nashville office.</li>
                                <li>No preparation is needed—just be ready to share!</li>
                            </ul>
                        </div>
                    """, unsafe_allow_html=True)
                else:
                    st.error("There was an issue saving your details. Please try again.")

    # 6. FIRM REASSURANCE
    st.markdown("---")
    st.caption(f"Questions? Contact {project.get('firm_name')} directly.")