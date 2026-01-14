import streamlit as st
import pandas as pd
import time
import base64
import os
import requests
from sqlalchemy import text

# --- MODULE IMPORTS ---
try: import database
except ImportError: database = None
try: import letter_format
except ImportError: letter_format = None
try: import audit_engine
except ImportError: audit_engine = None
try: import secrets_manager
except ImportError: secrets_manager = None
try: import ai_engine
except ImportError: ai_engine = None
try: import email_engine
except ImportError: email_engine = None

# --- HELPER FUNCTIONS ---

def get_orphaned_calls():
    """
    Compares Twilio logs vs Database (Drafts AND Projects) to find missing stories.
    """
    if not ai_engine or not database: return []
    
    # 1. Fetch from Twilio
    twilio_calls = ai_engine.get_all_twilio_recordings(limit=50)
    if not twilio_calls: return []
    
    # 2. Fetch from DB (Check BOTH tables)
    known_sids = []
    try:
        with database.get_db_session() as session:
            # Check Standard Drafts
            sql_drafts = text("SELECT call_sid FROM letter_drafts WHERE call_sid IS NOT NULL")
            res_drafts = session.execute(sql_drafts).fetchall()
            known_sids.extend([row[0] for row in res_drafts])

            # Check Heirloom Projects
            sql_projects = text("SELECT call_sid FROM projects WHERE call_sid IS NOT NULL")
            res_projects = session.execute(sql_projects).fetchall()
            known_sids.extend([row[0] for row in res_projects])
            
    except Exception as e:
        st.error(f"DB Error: {e}")
        return []

    # 3. Find Orphans
    orphans = []
    for call in twilio_calls:
        if call['sid'] not in known_sids:
            orphans.append(call)
            
    return orphans

def manual_credit_grant(advisor_email, amount):
    """
    Manually adds credits to an advisor.
    """
    if not database: return False
    try:
        with database.get_db_session() as session:
            # Check if advisor exists
            sql_check = text("SELECT credits FROM advisors WHERE email = :email")
            result = session.execute(sql_check, {"email": advisor_email}).fetchone()
            
            if not result:
                return False, "Advisor not found."
            
            current_credits = result[0] or 0
            new_total = current_credits + amount
            
            # Update
            sql_update = text("UPDATE advisors SET credits = :new_val WHERE email = :email")
            session.execute(sql_update, {"new_val": new_total, "email": advisor_email})
            session.commit()
            return True, new_total
    except Exception as e:
        return False, str(e)

def check_service_health():
    """Diagnoses connection to critical B2B services."""
    health_report = []

    # 1. DATABASE CHECK
    try:
        if database and database.get_db_session():
            health_report.append(("✅", "Database (Supabase)", "Connected"))
        else:
            health_report.append(("❌", "Database", "Connection Failed"))
    except Exception as e:
        health_report.append(("❌", "Database", f"Error: {str(e)}"))

    # 2. OPENAI CHECK
    api_key = secrets_manager.get_secret("openai.api_key") if secrets_manager else os.environ.get("OPENAI_API_KEY")
    if api_key:
        health_report.append(("✅", "OpenAI", "Key Present"))
    else:
        health_report.append(("⚠️", "OpenAI", "Key Missing"))

    # 3. TWILIO CHECK
    sid = secrets_manager.get_secret("twilio.account_sid") if secrets_manager else os.environ.get("TWILIO_ACCOUNT_SID")
    if sid:
        health_report.append(("✅", "Twilio", "Key Present"))
    else:
        health_report.append(("❌", "Twilio", "Key Missing"))

    return health_report

# --- MAIN RENDER ---

def render_admin_page():
    st.title("⚙️ Admin Console (B2B)")
    
    # NAVIGATION
    tabs = st.tabs([
        "🖨️ Fulfillment", 
        "📢 Marketing", 
        "👻 Ghost Calls", 
        "💰 Credits", 
        "❤️ Health"
    ])

    # --- TAB 1: MANUAL FULFILLMENT ---
    with tabs[0]:
        st.subheader("Ready for Print")
        if st.button("Refresh Queue"): st.rerun()
        
        if database:
            try:
                # Raw SQL to fetch printable items
                with database.get_db_session() as session:
                    sql = text("""
                        SELECT id, user_email, content, status 
                        FROM letter_drafts 
                        WHERE status IN ('Pending Approval', 'Approved')
                    """)
                    items = session.execute(sql).fetchall()
                
                if not items:
                    st.info("Queue is empty.")
                
                for item in items:
                    with st.expander(f"🖨️ {item.user_email} - {item.status}"):
                        st.write(item.content)
                        
                        # Generate PDF Button
                        if st.button("⬇️ Generate PDF", key=f"pdf_{item.id}"):
                            if letter_format:
                                pdf_bytes = letter_format.create_pdf(item.content, {}, {}, "Standard")
                                b64 = base64.b64encode(pdf_bytes).decode('latin-1')
                                href = f'<a href="data:application/pdf;base64,{b64}" download="letter.pdf">Download PDF</a>'
                                st.markdown(href, unsafe_allow_html=True)
                        
                        # Mark Sent Button
                        if st.button("✅ Mark as Mailed", key=f"sent_{item.id}"):
                             with database.get_db_session() as session:
                                 # Update Status
                                 upd_sql = text("UPDATE letter_drafts SET status = 'Sent' WHERE id = :id")
                                 session.execute(upd_sql, {"id": item.id})
                                 session.commit()
                                 
                                 # --- 📧 EMAIL INJECTION: THE RECEIPT ---
                                 if email_engine:
                                     subject = "Your Keepsake has been mailed!"
                                     html = f"""
                                     <p>Great news! Your family story has been printed and mailed.</p>
                                     <p>Look for it in your mailbox soon.</p>
                                     """
                                     email_engine.send_email(item.user_email, subject, html)
                                     st.toast(f"Shipping alert sent to {item.user_email}")
                                 # ---------------------------------------
                                 
                                 st.success("Order Closed.")
                                 time.sleep(1)
                                 st.rerun()

            except Exception as e:
                st.error(f"Queue Error: {e}")

    # --- TAB 2: MARKETING STUDIO ---
    with tabs[1]:
        st.subheader("📢 Direct Marketing Writer")
        st.markdown("Create a one-off letter using the **Vintage TrueType** font engine.")
        
        c1, c2 = st.columns(2)
        with c1:
            m_name = st.text_input("Recipient Name", "Future Client")
            m_addr = st.text_area("Recipient Address", "123 Wealth Way\nNashville, TN 37203")
        with c2:
            m_from = st.text_area("Return Address", "VerbaPost HQ\n123 Innovation Dr\nFranklin, TN")
            m_tier = st.selectbox("Style / Font", ["Vintage", "Standard", "Civic"])
            
        m_body = st.text_area("Letter Body", height=300, value="Dear Client,\n\nWe would like to invite you...")
        
        if st.button("📄 Generate PDF Preview", type="primary"):
            if letter_format:
                to_obj = {"name": m_name, "street": m_addr.split("\n")[0], "city": "City", "state": "ST", "zip": "00000"} 
                from_obj = {"name": "VerbaPost", "address_line1": m_from}
                
                pdf_bytes = letter_format.create_pdf(
                    body_text=m_body,
                    to_addr=to_obj,
                    from_addr=from_obj,
                    tier=m_tier
                )
                
                b64_pdf = base64.b64encode(pdf_bytes).decode('latin-1')
                pdf_display = f'<iframe src="data:application/pdf;base64,{b64_pdf}" width="100%" height="500" type="application/pdf"></iframe>'
                st.markdown(pdf_display, unsafe_allow_html=True)
            else:
                st.error("Letter Format Engine missing.")

    # --- TAB 3: GHOST CALLS ---
    with tabs[2]:
        st.subheader("👻 Orphaned Recording Scanner")
        
        if st.button("🔍 Scan Twilio Logs"):
            with st.spinner("Comparing Twilio Logs vs Database..."):
                orphans = get_orphaned_calls()
                
                if not orphans:
                    st.success("✅ No orphans found! All calls are accounted for.")
                else:
                    st.warning(f"⚠️ Found {len(orphans)} orphaned recordings.")
                    for o in orphans:
                        with st.expander(f"Orphan: {o['date_created']} ({o['duration']}s)"):
                            st.write(f"**SID:** `{o['sid']}`")
                            media_url = f"https://api.twilio.com{o['uri'].replace('.json', '.mp3')}"
                            st.audio(media_url)

    # --- TAB 4: GRANT CREDITS ---
    with tabs[3]:
        st.subheader("💰 The Central Bank")
        
        c_email = st.text_input("Advisor Email")
        c_amount = st.number_input("Credits to Add", min_value=1, value=1, step=1)
        
        if st.button("💸 Inject Credits"):
            success, msg = manual_credit_grant(c_email, int(c_amount))
            if success:
                st.success(f"SUCCESS! New Balance: {msg}")
                if audit_engine:
                    audit_engine.log_event("admin", "manual_credit_grant", metadata={"target": c_email, "amount": c_amount})
            else:
                st.error(f"Failed: {msg}")

    # --- TAB 5: HEALTH ---
    with tabs[4]:
        st.subheader("System Diagnostics")
        if st.button("Run Health Check"):
            with st.spinner("Pinging services..."):
                results = check_service_health()
                for status, service, msg in results:
                    st.markdown(f"**{status} {service}**: {msg}")