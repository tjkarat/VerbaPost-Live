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
        headers = {"Authorization": f"Bearer {k}", "Content-Type": "application/json"}
        r_dom = requests.get("https://api.resend.com/domains", headers=headers)
        if r_dom.status_code == 403: return "⚠️ Online (Restricted)"
        if r_dom.status_code != 200: raise Exception(f"API {r_dom.status_code}")
            
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
            all_orders = database.get_all_orders()
            vintage_pending = [o for o in all_orders if o.get('status') == "Pending Manual Fulfillment"]
            if vintage_pending:
                st.error(f"🚨 {len(vintage_pending)} VINTAGE ORDERS REQUIRE MANUAL ACTION")
                st.dataframe(pd.DataFrame(vintage_pending)[['id', 'created_at', 'user_email', 'status', 'tier']], use_container_width=True)
            
            if all_orders:
                total_orders = len(all_orders)
                st.metric("Total Order Count", total_orders)
                data = []
                for o in all_orders:
                    raw_date = o.get('created_at')
                    date_str = raw_date.strftime("%Y-%m-%d %H:%M") if raw_date else "Unknown"
                    data.append({
                        "ID": str(o.get('id')), 
                        "Date": date_str,
                        "User": o.get('user_email'),
                        "Tier": o.get('tier'),
                        "Status": o.get('status'),
                        "Price": f"${float(o.get('price', 0)):.2f}"
                    })
                df_orders = pd.DataFrame(data)
                st.dataframe(df_orders, use_container_width=True, height=400)
                
                st.divider()
                st.markdown("### 🛠️ Repair, Export & Processing")
                order_opts = [f"{x['ID']} ({x['Status']})" for x in data]
                selected_order_str = st.selectbox("Select Order to Fix/Process", ["Select..."] + order_opts)
                
                if selected_order_str and selected_order_str != "Select...":
                    selected_uuid = selected_order_str.split(" ")[0]
                    with database.get_db_session() as db:
                        record = db.query(database.LetterDraft).filter(database.LetterDraft.id == selected_uuid).first()
                        if not record:
                            record = db.query(database.Letter).filter(database.Letter.id == selected_uuid).first()
                            
                        if record:
                            st.markdown(f"**Processing Order:** `{selected_uuid}`")
                            
                            # VINTAGE MANUAL WORKFLOW
                            if record.tier == "Vintage" or record.status == "Pending Manual Fulfillment":
                                st.info("📜 Vintage Workflow Active")
                                import ast
                                try: to_obj = ast.literal_eval(record.to_addr)
                                except: to_obj = {}
                                try: from_obj = ast.literal_eval(record.from_addr)
                                except: from_obj = {}
                                
                                pdf_bytes = letter_format.create_pdf(record.content, to_obj, from_obj, tier="Vintage") if letter_format else None
                                
                                c1, c2 = st.columns(2)
                                with c1:
                                    if pdf_bytes:
                                        st.download_button("⬇️ Download PDF (For Wax Seal)", pdf_bytes, f"VINTAGE_{selected_uuid}.pdf", "application/pdf")
                                with c2:
                                    manual_tracking = st.text_input("Manual Tracking Number")
                                    if st.button("✅ Mark Shipped (Manual)"):
                                        if manual_tracking:
                                            record.status = "Sent (Manual)"
                                            record.tracking_number = manual_tracking
                                            db.commit()
                                            st.success("Updated!"); time.sleep(1); st.rerun()

                            # STANDARD REPAIR WORKFLOW
                            else:
                                st.markdown("#### Edit Recipient Data")
                                import ast
                                try: t_addr = ast.literal_eval(record.to_addr)
                                except: t_addr = {}
                                
                                c1, c2 = st.columns(2)
                                with c1:
                                    new_name = st.text_input("Name", value=t_addr.get('name', ''))
                                    new_city = st.text_input("City", value=t_addr.get('city', ''))
                                with c2:
                                    new_street = st.text_input("Street", value=t_addr.get('address_line1', ''))
                                    new_zip = st.text_input("Zip", value=t_addr.get('zip_code', ''))
                                
                                if st.button("🚀 Update & Force PostGrid"):
                                    updated_to = {"name": new_name, "address_line1": new_street, "city": new_city, "state": "NA", "zip": new_zip}
                                    record.to_addr = str(updated_to)
                                    db.commit()
                                    if mailer:
                                        # Recalculate PDF for retry
                                        try: f_addr = ast.literal_eval(record.from_addr)
                                        except: f_addr = {}
                                        pdf = letter_format.create_pdf(record.content, updated_to, f_addr)
                                        res = mailer.send_letter(pdf, updated_to, f_addr, description=f"Repair {selected_uuid}")
                                        if res: 
                                            record.status = "Sent"; record.tracking_number = res; db.commit()
                                            st.success("Dispatched!"); st.rerun()
        except Exception as e: st.error(f"Error: {e}")

    # --- TAB 3: RECORDINGS (FULL CONSOLE) ---
    with tab_recordings:
        st.subheader("🎙️ Recording Management Console")
        st.info("Direct access to Twilio recordings, metadata, and deletion controls.")
        
        if st.button("🔎 Scan Twilio Servers", use_container_width=True):
            if ai_engine and hasattr(ai_engine, 'get_all_twilio_recordings'):
                with st.spinner("Fetching logs..."):
                    raw_recordings = ai_engine.get_all_twilio_recordings(limit=50)
                    users = database.get_all_users()
                    known_nums = { "".join(filter(str.isdigit, str(u.get('parent_phone', ''))))[-10:] for u in users if u.get('parent_phone') }
                    
                    if raw_recordings:
                        rec_data = []
                        for r in raw_recordings:
                            # Normalize caller phone for identification
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
            else: st.error("AI Engine update required: get_all_twilio_recordings() not found.")

        if st.session_state.get("active_recordings"):
            df = pd.DataFrame(st.session_state.active_recordings)
            st.dataframe(df[['Type', 'Date', 'From', 'Duration', 'SID']], use_container_width=True)
            
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
                        if ai_engine and hasattr(ai_engine, 'delete_twilio_recording'):
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
        
        promos = database.get_all_promos()
        if promos:
            st.dataframe(pd.DataFrame(promos), use_container_width=True)

    # --- TAB 5: USERS ---
    with tab_users:
        st.subheader("User Profiles")
        users = database.get_all_users()
        if users:
            safe_users = [{"Name": u.get("full_name"), "Email": u.get("email"), "Parent Phone": u.get("parent_phone", "--"), "Credits": u.get("credits_remaining")} for u in users]
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