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
    if not ai_engine or not database: return []
    twilio_calls = ai_engine.get_all_twilio_recordings(limit=50)
    if not twilio_calls: return []
    known_sids = []
    try:
        with database.get_db_session() as session:
            sql_drafts = text("SELECT call_sid FROM letter_drafts WHERE call_sid IS NOT NULL")
            res_drafts = session.execute(sql_drafts).fetchall()
            known_sids.extend([row[0] for row in res_drafts])
            sql_projects = text("SELECT call_sid FROM projects WHERE call_sid IS NOT NULL")
            res_projects = session.execute(sql_projects).fetchall()
            known_sids.extend([row[0] for row in res_projects])
    except Exception as e:
        st.error(f"DB Error: {e}")
        return []
    orphans = []
    for call in twilio_calls:
        if call['sid'] not in known_sids: orphans.append(call)
    return orphans

# --- FIX: SANITIZED INPUT & DUAL WRITE ---
def manual_credit_grant(advisor_email, amount):
    if not database: return False
    
    # SANITIZE INPUT
    advisor_email = advisor_email.strip().lower()
    
    try:
        with database.get_db_session() as session:
            new_val = 0
            found = False
            debug_msg = []
            
            # 1. Update User Profiles (The One Advisor Portal Reads)
            sql_check = text("SELECT credits FROM user_profiles WHERE email = :email")
            result = session.execute(sql_check, {"email": advisor_email}).fetchone()
            if result:
                found = True
                new_val = (result[0] or 0) + amount
                sql_update = text("UPDATE user_profiles SET credits = :new_val WHERE email = :email")
                session.execute(sql_update, {"new_val": new_val, "email": advisor_email})
                debug_msg.append(f"Profile updated to {new_val}")
            
            # 2. Update Legacy Advisors Table (Safety Net)
            sql_check_adv = text("SELECT credits FROM advisors WHERE email = :email")
            result_adv = session.execute(sql_check_adv, {"email": advisor_email}).fetchone()
            if result_adv:
                found = True
                new_val_adv = (result_adv[0] or 0) + amount
                sql_update_adv = text("UPDATE advisors SET credits = :new_val WHERE email = :email")
                session.execute(sql_update_adv, {"new_val": new_val_adv, "email": advisor_email})
                debug_msg.append(f"Legacy Advisor updated to {new_val_adv}")
            
            session.commit()
            
            if found:
                return True, f"Success! {', '.join(debug_msg)}"
            else:
                return False, f"User {advisor_email} not found in any table."
            
    except Exception as e: return False, str(e)

def check_service_health():
    health_report = []
    try:
        if database and database.get_db_session():
            health_report.append(("✅", "Database (Supabase)", "Connected"))
        else:
            health_report.append(("❌", "Database", "Connection Failed"))
    except Exception as e:
        health_report.append(("❌", "Database", f"Error: {str(e)}"))
    api_key = secrets_manager.get_secret("openai.api_key") if secrets_manager else os.environ.get("OPENAI_API_KEY")
    if api_key: health_report.append(("✅", "OpenAI", "Key Present"))
    else: health_report.append(("⚠️", "OpenAI", "Key Missing"))
    sid = secrets_manager.get_secret("twilio.account_sid") if secrets_manager else os.environ.get("TWILIO_ACCOUNT_SID")
    if sid: health_report.append(("✅", "Twilio", "Key Present"))
    else: health_report.append(("❌", "Twilio", "Key Missing"))
    return health_report

# --- MAIN RENDER ---

def render_admin_page():
    st.title("⚙️ Admin Console (B2B)")
    tabs = st.tabs(["🖨️ Master Queue", "📢 Marketing", "👻 Ghost Calls", "💰 Credits", "❤️ Health"])

    # --- TAB 1: MASTER QUEUE ---
    with tabs[0]:
        st.subheader("Ready for Print")
        if st.button("Refresh Queue"): st.rerun()
        if database:
            try:
                queue_items = []
                with database.get_db_session() as session:
                    # 1. Store Items
                    sql_store = text("SELECT id, user_email, content, status FROM letter_drafts WHERE status IN ('Pending Approval', 'Approved')")
                    store_items = session.execute(sql_store).fetchall()
                    for item in store_items:
                        queue_items.append({
                            "type": "Store", "id": item.id, "email": item.user_email, "content": item.content,
                            "status": item.status, "meta": {} 
                        })

                    # 2. Heirloom Projects (UPDATED: Fetch created_at)
                    sql_b2b = text("""
                        SELECT p.id, p.advisor_email, p.content, p.status, p.heir_name, p.created_at, c.name as parent_name, a.firm_name
                        FROM projects p
                        JOIN clients c ON p.client_id = c.id
                        JOIN advisors a ON p.advisor_email = a.email
                        WHERE p.status = 'Approved'
                    """)
                    b2b_items = session.execute(sql_b2b).fetchall()
                    for item in b2b_items:
                        # Format Date
                        date_str = item.created_at.strftime("%B %d, %Y") if item.created_at else "Undated"
                        
                        queue_items.append({
                            "type": "Heirloom", "id": item.id, "email": f"{item.heir_name} (via {item.advisor_email})",
                            "content": item.content, "status": item.status,
                            "meta": {
                                "storyteller": item.parent_name, "firm_name": item.firm_name,
                                "heir_name": item.heir_name, "interview_date": date_str 
                            }
                        })
                
                if not queue_items: st.info("Queue is empty.")
                
                for item in queue_items:
                    icon = "🏰" if item['type'] == "Heirloom" else "🛒"
                    with st.expander(f"{icon} {item['type']} | {item['email']}"):
                        st.text_area("Content", item['content'], height=100, disabled=True)
                        c1, c2 = st.columns(2)
                        
                        if c1.button("⬇️ Generate PDF", key=f"pdf_{item['type']}_{item['id']}"):
                            if letter_format:
                                # --- 🔴 FIX: PDF ARGUMENTS ALIGNED TO LETTER_FORMAT.PY ---
                                # letter_format.create_pdf signature:
                                # (body_text, to_addr, from_addr, advisor_firm, audio_url)
                                
                                tier = "Heirloom" if item['type'] == "Heirloom" else "Standard"
                                firm_name = item['meta'].get('firm_name', 'VerbaPost')
                                storyteller = item['meta'].get('storyteller', 'The Family')
                                
                                # Map Data Correctly
                                pdf_bytes = letter_format.create_pdf(
                                    body_text=item['content'], 
                                    to_addr={}, # Admin handles addressing manually
                                    from_addr={'name': storyteller}, # Passes Storyteller Name
                                    advisor_firm=firm_name, # Passes Firm Name
                                    audio_url=str(item['id']) if tier == "Heirloom" else None
                                )
                                
                                b64 = base64.b64encode(pdf_bytes).decode('latin-1')
                                href = f'<a href="data:application/pdf;base64,{b64}" download="letter_{item["id"]}.pdf">Download Print File</a>'
                                st.markdown(href, unsafe_allow_html=True)
                        
                        if c2.button("✅ Mark as Mailed", key=f"sent_{item['type']}_{item['id']}"):
                             with database.get_db_session() as session:
                                 table = "projects" if item['type'] == "Heirloom" else "letter_drafts"
                                 upd_sql = text(f"UPDATE {table} SET status = 'Sent' WHERE id = :id")
                                 session.execute(upd_sql, {"id": item['id']})
                                 session.commit()
                                 st.success("Order Closed.")
                                 time.sleep(1)
                                 st.rerun()
            except Exception as e: st.error(f"Queue Error: {e}")

    # --- TAB 2: MARKETING ---
    with tabs[1]:
        st.subheader("📢 Direct Marketing Writer")
        c1, c2 = st.columns(2)
        with c1:
            m_name = st.text_input("Recipient Name", "Future Client")
            m_addr = st.text_area("Recipient Address", "123 Wealth Way\nNashville, TN 37203")
        with c2:
            m_from = st.text_area("Return Address", "VerbaPost HQ\nFranklin, TN")
            m_tier = st.selectbox("Style", ["Vintage", "Standard"]) # UI Only
        m_body = st.text_area("Letter Body", height=300, value="Dear Client...")
        
        if st.button("Generate Preview"):
            if letter_format:
                # --- 🔴 FIX: MARKETING PDF CALL ---
                to_obj = {"name": m_name, "street": m_addr.split("\n")[0], "city": "City", "state": "TN", "zip": "00000"} 
                from_obj = {"name": "VerbaPost", "address_line1": m_from}
                
                # Pass "Vintage" as advisor_firm if needed for styling, or fixed string
                pdf_bytes = letter_format.create_pdf(
                    body_text=m_body, 
                    to_addr=to_obj, 
                    from_addr=from_obj,
                    advisor_firm="VerbaPost Marketing"
                )
                
                b64_pdf = base64.b64encode(pdf_bytes).decode('latin-1')
                pdf_display = f'<iframe src="data:application/pdf;base64,{b64_pdf}" width="100%" height="500"></iframe>'
                st.markdown(pdf_display, unsafe_allow_html=True)

    # --- TAB 3: GHOSTS ---
    with tabs[2]:
        st.subheader("👻 Orphaned Recordings")
        if st.button("🔍 Scan Twilio Logs"):
            orphans = get_orphaned_calls()
            if not orphans: st.success("✅ All calls accounted for.")
            else:
                for o in orphans:
                    with st.expander(f"Orphan: {o['date_created']}"):
                        st.write(f"SID: {o['sid']}")
                        st.audio(f"https://api.twilio.com{o['uri'][:-5]}.mp3")

    # --- TAB 4: CREDITS ---
    with tabs[3]:
        st.subheader("💰 The Central Bank")
        c_email = st.text_input("Advisor Email")
        c_amount = st.number_input("Credits to Add", 1)
        if st.button("💸 Inject"):
            # --- SANITIZATION ---
            c_email = c_email.strip().lower()
            success, msg = manual_credit_grant(c_email, int(c_amount))
            if success: st.success(f"Updated: {msg}")
            else: st.error(f"Failed: {msg}")

    # --- TAB 5: HEALTH ---
    with tabs[4]:
        st.subheader("Diagnostics")
        if st.button("Run Check"):
            for s, n, m in check_service_health(): st.markdown(f"**{s} {n}**: {m}")