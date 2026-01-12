import streamlit as st
import database
import time

def render_parent_setup(project_id):
    # Fetch project context
    project = database.get_project_by_id(project_id)
    if not project:
        st.error("Invalid or expired link.")
        return

    st.markdown(f"""
        <div style='text-align: center;'>
            <h2 style='color: #1f2937;'>Family Archive Setup</h2>
            <p>Sponsored by <b>{project.get('firm_name')}</b></p>
        </div>
    """, unsafe_allow_html=True)

    st.info(f"Hi {project.get('parent_name')}, we are honored to help you preserve your history for {project.get('heir_name')}.")

    with st.form("setup_form"):
        st.markdown("### 📮 Where should we mail the physical keepsakes?")
        st.caption("We will mail a high-quality, physical transcript of your stories to your heir.")
        heir_street = st.text_input("Heir Street Address")
        c1, c2, c3 = st.columns([2, 1, 1])
        heir_city = c1.text_input("City")
        heir_state = c2.text_input("State")
        heir_zip = c3.text_input("Zip")

        st.markdown("### 📅 Schedule Your Interview Call")
        st.caption("Our legacy biographer will call you at this time. The session takes 15 minutes.")
        d = st.date_input("Select Date")
        t = st.time_input("Select Time")

        if st.form_submit_button("✅ Lock in My Session"):
            if not heir_street or not heir_zip:
                st.error("Please provide a mailing address.")
            else:
                database.update_project_details(
                    project_id, 
                    address={"street": heir_street, "city": heir_city, "state": heir_state, "zip": heir_zip},
                    scheduled_time=f"{d} {t}",
                    status="Scheduled"
                )
                st.success("All set! Your biographer will call you at the scheduled time.")
                st.balloons()
