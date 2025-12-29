import streamlit as st
import pandas as pd
import time
import json
import os
import requests
import ast
from datetime import datetime
import base64

# --- THIRD PARTY SDKs FOR HEALTH CHECKS ---
import stripe
import openai
from twilio.rest import Client as TwilioClient

# --- DIRECT IMPORT ---
import database
import secrets_manager

# Import Engines
try: import mailer
except ImportError: mailer = None
try: import letter_format
except ImportError: letter_format = None
try: import address_standard
except ImportError: address_standard = None
try: import ai_engine  
except ImportError: ai_engine = None
try: import audit_engine
except ImportError: audit_engine = None

# --- HEALTH CHECK HELPERS ---
def check_connection(service_name, check_func):
    """Generic wrapper for health checks."""
    try:
        check_func()
        return "✅ Online", "green"
    except Exception as e:
        msg = str(e)
        if "403" in msg or "401" in msg or "Restricted" in msg:
            return "⚠️ Online (Restricted)", "orange"
        return f"❌ Error: {msg[:100]}", "red"

def run_system_health_checks():
    """Runs connectivity tests for all external services."""
    results = []

    # 1. DATABASE
    def check_db():
        with database.get_db_session() as db:
            from sqlalchemy import text
            db.execute(text("SELECT 1"))
    status, color = check_connection("Database (Supabase)", check_db)
    results.append({"Service": "Database (Supabase)", "Status": status, "Color": color})

    # 2. STRIPE
    def check_stripe():
        k = secrets_manager.get_secret("stripe.secret_key")
        if not k: raise Exception("Missing Key")
        stripe.api_key = k
        stripe.Balance.retrieve()
    status, color = check_connection("Stripe Payments", check_stripe)
    results.append({"Service": "Stripe Payments", "Status": status, "Color": color})

    # 3. OPENAI
    def check_openai():
        k = secrets_manager.get_secret("openai.api_key")
        if not k: raise Exception("Missing Key")
        client = openai.OpenAI(api_key=k)
        client.models.list() 
    status, color = check_connection("OpenAI (Intelligence)", check_openai)
    results.append({"Service": "OpenAI (Intelligence)", "Status": status, "Color": color})

    # 4. TWILIO
    def check_twilio():
        sid = secrets_manager.get_secret("twilio.account_sid")
        token = secrets_manager.get_secret("twilio.auth_token")
        if not sid or not token: raise Exception("Missing Credentials")
        client = TwilioClient(sid, token)
        client.api.v2010.accounts(sid).fetch()
    status, color = check_connection("Twilio (Voice)", check_twilio)
    results.append({"Service": "Twilio (Voice)", "Status": status, "Color": color})

    # 5. POSTGRID
    def check_postgrid():
        k = secrets_manager.get_secret("postgrid.api_key") or secrets_manager.get_secret("POSTGRID_API_KEY")
        if not k: raise Exception("Missing Key")
        # Corrected endpoint to match mailer.py logic
        r = requests.get("https://api.postgrid.com/print-mail/v1/letters?limit=1", headers={"x-api-key": k})
        if r.status_code not in [200, 201]: raise Exception(f"API {r.status_code} - {r.text}")
    status, color = check_connection("PostGrid (Fulfillment)", check_postgrid)
    results.append({"Service": "PostGrid (Fulfillment)", "Status": status, "Color": color})

    # 6. GEOCODIO
    def check_geocodio():
        k = secrets_manager.get_secret("geocodio.api_key") or secrets_manager.get_secret("GEOCODIO_API_KEY")
        if not k: raise Exception("Missing Key")
        r = requests.get(f"https://api.geocod.io/v1.7/geocode?q=1600+Pennsylvania+Ave+NW,Washington,DC&api_key={k}")
        if r.status_code != 200: raise Exception(f"API {r.status_code}")
    status, color = check_connection("Geocodio (Civic)", check_geocodio)
    results.append({"Service": "Geocodio (Civic)", "Status": status, "Color": color})

    # 7. RESEND
    def check_resend():
        k_raw = secrets_manager.get_secret("email.password") or secrets_manager.get_secret("RESEND_API_KEY")
        if not k_raw: raise Exception("Missing Key")
        k = str(k_raw).strip().replace("'", "").replace('"', "")
        if not k.startswith("re_"): raise Exception("Invalid Key Format (must start with re_)")
        headers = {"Authorization": f"Bearer {k}", "Content-Type": "application/json"}
        r_dom = requests.get("https://api.resend.com/domains", headers=headers)
        if r_dom.status_code == 403: return "⚠️ Online (Restricted)"
        if r_dom.status_code != 200: raise Exception(f"API {r_dom.status_code}: {r_dom.text}")
            
    status, color = check_connection("Resend (Email)", check_resend)
    results.append({"Service": "Resend (Email)", "Status": status, "Color": color})

    return results

def render_admin_page():
    # --- AUTH CHECK ---
    admin_email = os.environ.get("ADMIN_EMAIL") or secrets_manager.get_secret("admin.email")
    
    if not st.session_state.get("admin_authenticated"):
        st.markdown("## 🛡️ Admin Access")
        with st.form("admin_login"):
            email = st.text_input("Admin Email")
            pwd = st.text_input("Password", type="password")
            if st.form_submit_button("Unlock Console"):
                stored_pass = os.environ.get("ADMIN_PASSWORD") or secrets_manager.get_secret("admin.password")
                if email.strip() == admin_email and pwd.strip() == stored_pass:
                    st.session_state.admin_authenticated = True
                    st.rerun()
                else:
                    st.error("Invalid Credentials")
        return

    # --- DASHBOARD ---
    st.title("⚙️ VerbaPost Admin Console")
    
    c_exit, c_refresh = st.columns([1, 6])
    with c_exit:
        if st.button("⬅️ Exit"):
            st.session_state.app_mode = "splash"
            st.rerun()
    with c_refresh:
        if st.button("🔄 Refresh Data"):
            st.rerun()

    # --- TABS (RESTORED) ---
    tab_print, tab_orders, tab_recordings, tab_promos, tab_users, tab_logs, tab_health = st.tabs([
        "🖨️ Manual Print", "📦 Orders & Repair", "🎙️ Recordings", "🎟️ Promos", "👥 Users", "📜 Logs", "🏥 Health"
    ])

    # --- TAB 1: MANUAL PRINT QUEUE ---
    with tab_print:
        st.subheader("🖨️ Manual Fulfillment Queue")
        st.info("Items here were submitted via 'Manual Mode'. Download PDF, Print, then Mark as Mailed.")
        
        if database:
            with database.get_db_session() as db:
                queued_items = db.query(database.LetterDraft).filter(
                    database.LetterDraft.status == "Queued (Manual)"
                ).order_by(database.LetterDraft.created_at.desc()).all()
                
                if not queued_items:
                    st.success("🎉 Print queue is empty!")
                else:
                    st.write(f"**Pending items:** {len(queued_items)}")
                    for item in queued_items:
                        with st.expander(f"📄 {item.tier} | {item.created_at.strftime('%Y-%m-%d')} | {item.user_email}"):
                            c1, c2 = st.columns([2, 1])
                            with c1:
                                try:
                                    to_dict = ast.literal_eval(item.to_addr) if item.to_addr else {}
                                    from_dict = ast.literal_eval(item.from_addr) if item.from_addr else {}
                                except:
                                    to_dict, from_dict = {}, {}
                                
                                if st.button(f"⬇️ Generate PDF for #{item.id}", key=f"pdf_{item.id}"):
                                    if letter_format and address_standard:
                                        try:
                                            std_to = address_standard.StandardAddress.from_dict(to_dict)
                                            std_from = address_standard.StandardAddress.from_dict(from_dict)
                                            pdf_bytes = letter_format.create_pdf(item.content, std_to, std_from, tier=item.tier)
                                            b64 = base64.b64encode(pdf_bytes).decode()
                                            href = f'<a href="data:application/pdf;base64,{b64}" download="VerbaPost_{item.id}.pdf">Click here to Download PDF</a>'
                                            st.markdown(href, unsafe_allow_html=True)
                                        except Exception as e: st.error(f"PDF Gen Error: {e}")

                            with c2:
                                st.markdown("<br>", unsafe_allow_html=True)
                                manual_track = st.text_input("Tracking # (Optional)", key=f"trk_{item.id}")
                                if st.button("✅ Mark as Mailed", key=f"done_{item.id}", type="primary"):
                                    item.status = "Sent (Manual)"
                                    if manual_track:
                                        item.tracking_number = manual_track
                                    db.commit()
                                    st.toast("Marked as Sent!")
                                    time.sleep(1)
                                    st.rerun()

    # --- TAB 2: ORDERS & REPAIR ---
    with tab_orders:
        st.subheader("Order Manager & Repair Station")
        try:
            all_orders = database.get_all_orders()
            if all_orders:
                # Render Data Table
                data = []
                for o in all_orders:
                    raw_date = o.get('created_at')
                    date_str = raw_date.strftime("%Y-%m-%d %H:%M") if raw_date else "Unknown"
                    price_val = o.get('price')
                    price_str = f"${float(price_val):.2f}" if price_val is not None else "$0.00"
                    
                    data.append({
                        "ID": str(o.get('id')), 
                        "Date": date_str,
                        "User": o.get('user_email'),
                        "Tier": o.get('tier'),
                        "Status": o.get('status'),
                        "Price": price_str
                    })
                
                st.dataframe(pd.DataFrame(data), use_container_width=True, height=300)
                
                # REPAIR STATION
                st.divider()
                st.markdown("### 🛠️ Repair & Retry")
                st.info("Select an order to fix the address or content, then force it back into the queue.")
                
                order_opts = [f"{x['ID']} ({x['Status']})" for x in data]
                selected_order_str = st.selectbox("Select Order to Fix", ["Select..."] + order_opts)
                
                if selected_order_str and selected_order_str != "Select...":
                    selected_uuid = selected_order_str.split(" ")[0]
                    
                    with database.get_db_session() as db:
                        record = db.query(database.LetterDraft).filter(database.LetterDraft.id == selected_uuid).first()
                        if record:
                            st.markdown(f"**Editing Order:** `{selected_uuid}`")
                            
                            try: t_addr = ast.literal_eval(record.to_addr) if hasattr(record, 'to_addr') and record.to_addr else {}
                            except: t_addr = {}
                            
                            c1, c2 = st.columns(2)
                            with c1:
                                new_name = st.text_input("Recipient Name", value=t_addr.get('name', ''), key="rep_name")
                                new_street = st.text_input("Street", value=t_addr.get('address_line1', '') or t_addr.get('street', ''), key="rep_street")
                                new_line2 = st.text_input("Line 2 (Apt/Suite)", value=t_addr.get('address_line2', ''), key="rep_line2")
                            with c2:
                                new_city = st.text_input("City", value=t_addr.get('city', ''), key="rep_city")
                                new_state = st.text_input("State", value=t_addr.get('state', ''), key="rep_state")
                                new_zip = st.text_input("Zip Code", value=t_addr.get('zip_code', '') or t_addr.get('zip', ''), key="rep_zip")
                            
                            new_content = st.text_area("Letter Body", value=record.content, height=150, key="rep_body")
                            
                            if st.button("💾 Update & Retry Order", type="primary"):
                                updated_to = {
                                    "name": new_name, 
                                    "address_line1": new_street, 
                                    "address_line2": new_line2,
                                    "city": new_city, 
                                    "state": new_state, 
                                    "zip_code": new_zip
                                }
                                record.to_addr = str(updated_to)
                                record.content = new_content
                                record.status = "Queued (Manual)" 
                                db.commit()
                                st.success("Order Updated and moved to Manual Print Queue!")
                                time.sleep(1)
                                st.rerun()
        except Exception as e: st.error(f"Error fetching orders: {e}")

    # --- TAB 3: RECORDINGS ---
    with tab_recordings:
        st.subheader("🎙️ Recording Management")
        if st.button("🔎 Scan Twilio Servers", use_container_width=True):
            if ai_engine and hasattr(ai_engine, 'get_all_twilio_recordings'):
                with st.spinner("Fetching audio logs..."):
                    raw_recordings = ai_engine.get_all_twilio_recordings(limit=50)
                    users = database.get_all_users()
                    known_nums = { "".join(filter(str.isdigit, str(u.get('parent_phone', ''))))[-10:] for u in users if u.get('parent_phone') }
                    
                    if raw_recordings:
                        rec_data = []
                        for r in raw_recordings:
                            caller_norm = "".join(filter(str.isdigit, str(r.get('from', ''))))[-10:]
                            is_ghost = caller_norm not in known_nums
                            rec_data.append({
                                "SID": r.get('sid'),
                                "Date": r.get('date_created'),
                                "From": r.get('from', 'Unknown'),
                                "Duration": f"{r.get('duration')}s",
                                "Type": "👻 GHOST" if is_ghost else "👤 USER",
                                "URL": r.get('uri')
                            })
                        st.session_state.active_recordings = rec_data
                    else: st.success("✅ No recordings on server.")
            else: st.error("AI Engine update required.")

        if st.session_state.get("active_recordings"):
            df_recs = pd.DataFrame(st.session_state.active_recordings)
            st.dataframe(df_recs[['Type', 'Date', 'From', 'Duration', 'SID']], use_container_width=True)

    # --- TAB 4: PROMOS ---
    with tab_promos:
        st.subheader("Manage Discounts")
        with st.expander("➕ Create New Code"):
            with st.form("new_promo"):
                c_code = st.text_input("Code").upper()
                c_val = st.number_input("Discount ($)", min_value=0.0)
                if st.form_submit_button("Create"):
                    if database.create_promo_code(c_code, c_val):
                        st.success(f"Created {c_code}"); time.sleep(1); st.rerun()
        
        promos = database.get_all_promos()
        if promos:
            st.dataframe(pd.DataFrame(promos), use_container_width=True)
        else:
            st.info("No promo codes found.")

    # --- TAB 5: USERS ---
    with tab_users:
        st.subheader("User Profiles")
        users = database.get_all_users()
        if users:
            safe_users = []
            for u in users:
                safe_users.append({
                    "Name": u.get("full_name"),
                    "Email": u.get("email"),
                    "Parent Phone": u.get("parent_phone", "--"),
                    "Credits": u.get("credits_remaining")
                })
            st.dataframe(pd.DataFrame(safe_users), use_container_width=True)

    # --- TAB 6: LOGS ---
    with tab_logs:
        st.subheader("System Logs")
        if audit_engine:
            logs = audit_engine.get_audit_logs(limit=100)
            if logs: st.dataframe(pd.DataFrame(logs), use_container_width=True)
            else: st.info("No logs found.")
        else: st.warning("Audit Engine not loaded.")
        
    # --- TAB 7: HEALTH ---
    with tab_health:
        st.subheader("🔌 Connection Diagnostics")
        if st.button("Run Diagnostics"):
            with st.spinner("Pinging services..."):
                health_data = run_system_health_checks()
                cols = st.columns(3)
                for i, item in enumerate(health_data):
                    with cols[i % 3]:
                        st.markdown(f"**{item['Service']}**")
                        st.markdown(f":{item['Color']}[{item['Status']}]")
                        st.markdown("---")

render_admin = render_admin_page