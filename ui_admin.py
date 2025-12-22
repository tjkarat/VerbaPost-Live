import streamlit as st
import pandas as pd
import time
import json
import os
import requests
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

    # 7. RESEND (FIXED SANITIZATION & LOGGING)
    def check_resend():
        k_raw = secrets_manager.get_secret("email.password") or secrets_manager.get_secret("RESEND_API_KEY")
        if not k_raw: raise Exception("Missing Key")
        
        # Strip whitespace and quotes
        k = str(k_raw).strip().replace("'", "").replace('"', "")
        if not k.startswith("re_"): raise Exception("Invalid Key Format (must start with re_)")

        headers = {"Authorization": f"Bearer {k}", "Content-Type": "application/json"}
        # 'domains' is a safe read-only endpoint to check auth
        r_dom = requests.get("https://api.resend.com/domains", headers=headers)
        
        if r_dom.status_code == 403: return "⚠️ Online (Restricted)"
        if r_dom.status_code != 200: 
            raise Exception(f"API {r_dom.status_code}: {r_dom.text}")
            
    status, color = check_connection("Resend (Email)", check_resend)
    results.append({"Service": "Resend (Email)", "Status": status, "Color": color})

    return results

def render_admin_page():
    # --- AUTH CHECK ---
    admin_email = os.environ.get("ADMIN_EMAIL") or secrets_manager.get_secret("admin.email")
    admin_pass = os.environ.get("ADMIN_PASSWORD") or secrets_manager.get_secret("admin.password")
    
    if not st.session_state.get("admin_authenticated"):
        st.markdown("## 🛡️ Admin Access")
        with st.form("admin_login"):
            email = st.text_input("Admin Email")
            pwd = st.text_input("Password", type="password")
            if st.form_submit_button("Unlock Console"):
                if email.strip() == admin_email and pwd.strip() == admin_pass:
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

    tab_health, tab_orders, tab_recordings, tab_promos, tab_users, tab_logs = st.tabs([
        "🏥 Health", "📦 Orders", "🎙️ Recordings", "🎟️ Promos", "👥 Users", "📜 Logs"
    ])

    # --- TAB 1: HEALTH ---
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

    # --- TAB 2: ORDERS (REPAIR STATION & VINTAGE) ---
    with tab_orders:
        st.subheader("Order Manager")
        try:
            # 1. Fetch from DB
            all_orders = database.get_all_orders()
            
            # --- VINTAGE ALERT ---
            vintage_pending = [o for o in all_orders if o.get('status') == "Pending Manual Fulfillment"]
            if vintage_pending:
                st.error(f"🚨 {len(vintage_pending)} VINTAGE ORDERS REQUIRE MANUAL ACTION")
                st.dataframe(pd.DataFrame(vintage_pending)[['id', 'created_at', 'user_email', 'status', 'tier']], use_container_width=True)
            
            if all_orders:
                total_orders = len(all_orders)
                st.metric("Total Order Count", total_orders)
                
                # 2. Render Data Table
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
                
                df_orders = pd.DataFrame(data)
                st.dataframe(df_orders, use_container_width=True, height=400)
                
                # 3. ACTION STATION
                st.divider()
                st.markdown("### 🛠️ Repair, Export & Processing")
                st.info("Select an order to export PDF (Vintage) or force re-send (Standard).")
                
                c_sel, c_act = st.columns([3, 1])
                with c_sel:
                    # Dropdown for easier selection
                    order_opts = [f"{x['ID']} ({x['Status']})" for x in data]
                    selected_order_str = st.selectbox("Select Order to Fix/Process", ["Select..."] + order_opts)
                
                if selected_order_str and selected_order_str != "Select...":
                    selected_uuid = selected_order_str.split(" ")[0]
                    
                    # Fetch details for the selected order
                    with database.get_db_session() as db:
                        # Try Draft table first (pending items), then Letters (sent items)
                        record = db.query(database.LetterDraft).filter(database.LetterDraft.id == selected_uuid).first()
                        if not record:
                            record = db.query(database.Letter).filter(database.Letter.id == selected_uuid).first()
                            
                        if record:
                            st.markdown(f"**Processing Order:** `{selected_uuid}`")
                            
                            # --- VINTAGE WORKFLOW ---
                            if getattr(record, 'tier', '') == "Vintage" or record.status == "Pending Manual Fulfillment":
                                st.info("📜 **Vintage/Manual Workflow Detected**")
                                import ast
                                to_obj = {}
                                from_obj = {}
                                try: 
                                    raw_to = getattr(record, 'to_addr', "{}")
                                    if raw_to: to_obj = ast.literal_eval(raw_to)
                                except: pass
                                
                                try:
                                    raw_from = getattr(record, 'from_addr', "{}")
                                    if raw_from: from_obj = ast.literal_eval(raw_from)
                                except: pass
                                
                                pdf_bytes = b""
                                if letter_format:
                                    pdf_bytes = letter_format.create_pdf(record.content, to_obj, from_obj, tier="Vintage")
                                
                                c1, c2 = st.columns(2)
                                with c1:
                                    if pdf_bytes:
                                        st.download_button(label="⬇️ Download PDF (For Wax Seal)", data=pdf_bytes, file_name=f"VINTAGE_{selected_uuid}.pdf", mime="application/pdf")
                                    else: st.error("PDF Gen Failed")
                                    
                                with c2:
                                    manual_tracking = st.text_input("Manual Tracking Number", key="man_track")
                                    if st.button("✅ Mark Shipped (Manual)"):
                                        if manual_tracking:
                                            record.status = "Sent (Manual)"
                                            record.tracking_number = manual_tracking
                                            db.commit()
                                            st.success("Order Updated!"); time.sleep(1); st.rerun()
                                        else: st.error("Please enter a tracking number first.")

                            # --- STANDARD WORKFLOW (REPAIR) ---
                            else:
                                st.markdown("#### Edit Recipient Data & Re-Dispatch")
                                import ast
                                try: t_addr = ast.literal_eval(record.to_addr)
                                except: t_addr = {}
                                
                                c1, c2 = st.columns(2)
                                with c1:
                                    new_name = st.text_input("Recipient Name", value=t_addr.get('name', ''), key="rep_name")
                                    new_city = st.text_input("City", value=t_addr.get('city', ''), key="rep_city")
                                with c2:
                                    new_street = st.text_input("Street", value=t_addr.get('address_line1', ''), key="rep_street")
                                    new_zip = st.text_input("Zip", value=t_addr.get('zip_code', ''), key="rep_zip")
                                
                                new_content = st.text_area("Letter Body", value=record.content, height=150, key="rep_body")
                                
                                if st.button("🚀 Update & Force Dispatch"):
                                    updated_to = {"name": new_name, "address_line1": new_street, "city": new_city, "state": t_addr.get('state', 'NA'), "zip": new_zip}
                                    record.to_addr = str(updated_to)
                                    record.content = new_content
                                    db.commit()
                                    if mailer and letter_format:
                                        try: f_addr = ast.literal_eval(record.from_addr)
                                        except: f_addr = {"name": "VerbaPost"}
                                        pdf = letter_format.create_pdf(new_content, updated_to, f_addr)
                                        res = mailer.send_letter(pdf, updated_to, f_addr, description=f"Repair {selected_uuid}")
                                        if res: 
                                            record.status = "Sent"; record.tracking_number = res; db.commit()
                                            st.success("Dispatched!"); st.rerun()
        except Exception as e: st.error(f"Error fetching orders: {e}")

    # --- TAB 3: RECORDINGS (FULL CONSOLE) ---
    with tab_recordings:
        st.subheader("🎙️ Recording Management Console")
        st.info("Direct access to Twilio recordings, metadata, and deletion controls.")
        
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
                                "URL": r.get('uri'),
                                "CallID": r.get('call_sid')
                            })
                        st.session_state.active_recordings = rec_data
                    else: st.success("✅ No recordings on server.")
            else: st.error("AI Engine update required.")

        if st.session_state.get("active_recordings"):
            df_recs = pd.DataFrame(st.session_state.active_recordings)
            st.dataframe(df_recs[['Type', 'Date', 'From', 'Duration', 'SID']], use_container_width=True)
            
            st.divider()
            st.markdown("### 🛠️ Recording Actions")
            sel_sid = st.selectbox("Select SID to Manage", [r['SID'] for r in st.session_state.active_recordings])
            target = next((item for item in st.session_state.active_recordings if item["SID"] == sel_sid), None)
            
            if target:
                c1, c2, c3 = st.columns([1,1,1])
                with c1: st.markdown(f"**From:** {target['From']}\n**Date:** {target['Date']}")
                with c2: st.link_button("🔈 Listen / Download", target['URL'], use_container_width=True)
                with c3:
                    if st.button("🗑️ Delete from Twilio", type="primary", use_container_width=True):
                        if ai_engine.delete_twilio_recording(sel_sid):
                            st.success("Permanently Deleted."); time.sleep(1); st.rerun()

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
        
        # --- FIXED PROMO LOGIC: COUNT ACTUAL USAGE ---
        promos = database.get_all_promos()
        if promos:
            with database.get_db_session() as session:
                from sqlalchemy import func
                usage_query = session.query(database.PromoLog.code, func.count(database.PromoLog.id)).group_by(database.PromoLog.code).all()
                usage_map = {row[0].upper(): row[1] for row in usage_query}
            
            for p in promos:
                code_key = p.get('code', '').upper()
                p['Actual Usage'] = usage_map.get(code_key, 0)
            
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

render_admin = render_admin_page