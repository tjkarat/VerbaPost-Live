import streamlit as st
import pandas as pd
import time
import json
import os
import requests
import ast
import logging 
from datetime import datetime
import base64

# --- THIRD PARTY SDKs ---
import stripe
import openai
from twilio.rest import Client as TwilioClient

# --- SILENCE CONSOLE SPAM ---
logging.getLogger("twilio").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

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

# --- HELPER: SALES SCRIPT ---
DEFAULT_PITCH = """Dear {first_name},

The "Great Wealth Transfer" is here. Over the next decade, $84 trillion will pass from Boomers to Gen X and Millennials.

Statistics show that 70% of heirs fire their parents' financial advisor within 12 months of receiving an inheritance. Why? Because the relationship was never established.

I built VerbaPost Wealth to solve this retention problem.

We provide a high-touch "Family Legacy" service that captures your clients' stories and values through AI-driven interviews and physical keepsake letters. It connects you to the next generation today, protecting your AUM tomorrow.

I would love to send you a sample of what we create.

Sincerely,

[Your Name]
Founder, VerbaPost
"""

# --- HELPER: ROBUST ADDRESS PARSER ---
def parse_address_data(raw_data):
    """
    Safely extracts address dictionary from DB string, handling both 
    JSON strings and Python string representations.
    """
    if not raw_data:
        return {}
    
    try:
        # Attempt 1: JSON
        return json.loads(raw_data)
    except:
        try:
            # Attempt 2: Python Literal (e.g. "{'name': '...'}")
            return ast.literal_eval(raw_data)
        except:
            return {}

def check_connection(service_name, check_func):
    try:
        check_func()
        return "✅ Online", "green"
    except Exception as e:
        msg = str(e)
        if "403" in msg or "401" in msg or "Restricted" in msg:
            return "⚠️ Online (Restricted)", "orange"
        return f"❌ Error: {msg[:100]}", "red"

def run_system_health_checks():
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

    # 5. GEOCODIO
    def check_geocodio():
        k = secrets_manager.get_secret("geocodio.api_key") or secrets_manager.get_secret("GEOCODIO_API_KEY")
        if not k: raise Exception("Missing Key")
        r = requests.get(f"https://api.geocod.io/v1.7/geocode?q=1600+Pennsylvania+Ave+NW,Washington,DC&api_key={k}")
        if r.status_code != 200: raise Exception(f"API {r.status_code}")
    status, color = check_connection("Geocodio (Civic)", check_geocodio)
    results.append({"Service": "Geocodio (Civic)", "Status": status, "Color": color})

    return results

def render_admin_page():
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

    st.title("⚙️ VerbaPost Admin Console")
    
    c_exit, c_refresh = st.columns([1, 6])
    with c_exit:
        if st.button("⬅️ Exit"):
            st.session_state.app_mode = "splash"
            st.rerun()
    with c_refresh:
        if st.button("🔄 Refresh Data"):
            st.rerun()

    # --- UPDATED TABS: ADDED OUTREACH ---
    tab_outreach, tab_print, tab_orders, tab_recordings, tab_promos, tab_users, tab_logs, tab_health = st.tabs([
        "📢 Sales Outreach", "🖨️ Manual Print", "📦 Orders", "🎙️ Recordings", "🎟️ Promos", "👥 Users", "📜 Logs", "🏥 Health"
    ])

    # --- TAB 1: SALES OUTREACH (NEW) ---
    with tab_outreach:
        st.subheader("B2B Sales Cannon")
        st.info("Draft a Vintage Letter for manual printing.")
        
        c1, c2 = st.columns([1, 1])
        with c1:
            target_firm = st.text_input("Firm Name", placeholder="e.g. Acme Wealth Mgmt")
            target_name = st.text_input("Advisor Name", placeholder="e.g. John Smith")
            
            # Auto-split name for script
            first_name = target_name.split(" ")[0] if target_name else "Advisor"
            
        with c2:
            target_street = st.text_input("Street Address")
            c_city, c_state, c_zip = st.columns([2, 1, 1])
            target_city = c_city.text_input("City")
            target_state = c_state.text_input("State")
            target_zip = c_zip.text_input("Zip")

        st.markdown("### 📝 Letter Content")
        script_body = st.text_area("Body", value=DEFAULT_PITCH.format(first_name=first_name), height=300)

        if st.button("📥 Queue for Manual Print", type="primary", use_container_width=True):
            if not target_street or not target_zip:
                st.error("Missing Address Info")
            else:
                try:
                    # 1. Prepare Addresses
                    to_addr = {
                        "name": target_name,
                        "company": target_firm,
                        "street": target_street,
                        "city": target_city,
                        "state": target_state,
                        "zip": target_zip
                    }
                    from_addr = {
                        "name": "VerbaPost Wealth",
                        "street": "123 Your HQ St", # UPDATE THIS IN CODE OR DB
                        "city": "Nashville",
                        "state": "TN",
                        "zip": "37203"
                    }
                    
                    # 2. Insert into DB as "Queued (Manual)"
                    # We inject directly into letter_drafts so it appears in Tab 2
                    with database.get_db_session() as db:
                        new_pitch = database.LetterDraft(
                            user_email=admin_email, # Admin owns this draft
                            content=script_body,
                            tier="Vintage",
                            status="Queued (Manual)",
                            recipient_data=json.dumps(to_addr),
                            sender_data=json.dumps(from_addr),
                            to_addr=json.dumps(to_addr),
                            from_addr=json.dumps(from_addr)
                        )
                        db.add(new_pitch)
                        db.commit()
                        
                        st.success(f"✅ Queued! Go to 'Manual Print' tab to download PDF.")
                        
                except Exception as e:
                    st.error(f"Queue Error: {e}")

    # --- TAB 2: MANUAL QUEUE ---
    with tab_print:
        st.subheader("🖨️ Manual Fulfillment Queue")
        st.info("Items here were submitted via 'Manual Mode'. Download PDF, Print, then Mark as Mailed.")
        
        if database:
            with database.get_db_session() as db:
                queued_items = db.query(database.LetterDraft).filter(
                    database.LetterDraft.status == "Queued (Manual)"
                ).order_by(database.LetterDraft.created_at.desc()).all()
                
                if not queued_items:
                    st.success("🎉 Print queue is empty! All manual orders have been cleared.")
                else:
                    st.write(f"**Pending items:** {len(queued_items)}")
                    for item in queued_items:
                        with st.expander(f"📄 {item.tier} | {item.created_at.strftime('%Y-%m-%d')} | {item.user_email}"):
                            c1, c2 = st.columns([2, 1])
                            
                            with c1:
                                st.caption("Content Preview:")
                                st.text(item.content[:150] + "...")
                                
                                # FIX: Robust Parsing
                                to_dict = parse_address_data(item.recipient_data or item.to_addr)
                                from_dict = parse_address_data(item.sender_data or item.from_addr)
                                
                                if st.button(f"⬇️ Generate PDF for #{item.id}", key=f"pdf_{item.id}"):
                                    if letter_format and address_standard:
                                        try:
                                            # Create Address Objects
                                            if to_dict:
                                                std_to = address_standard.StandardAddress.from_dict(to_dict)
                                            else:
                                                std_to = address_standard.StandardAddress(name="Unknown", street="Unknown", city="Unknown", state="NA", zip_code="00000")
                                                
                                            if from_dict:
                                                std_from = address_standard.StandardAddress.from_dict(from_dict)
                                            else:
                                                std_from = address_standard.StandardAddress(name="VerbaPost", street="123 Main", city="Nashville", state="TN", zip_code="37209")
                                            
                                            pdf_bytes = letter_format.create_pdf(
                                                item.content,
                                                std_to,
                                                std_from,
                                                tier=item.tier
                                            )
                                            b64 = base64.b64encode(pdf_bytes).decode()
                                            href = f'<a href="data:application/pdf;base64,{b64}" download="VerbaPost_{item.id}.pdf">Click here to Download PDF</a>'
                                            st.markdown(href, unsafe_allow_html=True)
                                        except Exception as e:
                                            st.error(f"PDF Gen Error: {e}")
                                    else:
                                        st.error("Missing Letter Format Module")

                            with c2:
                                st.markdown("<br>", unsafe_allow_html=True)
                                manual_track = st.text_input("Tracking # (Optional)", key=f"trk_{item.id}")
                                if st.button("✅ Mark as Mailed", key=f"done_{item.id}", type="primary"):
                                    item.status = "Sent (Manual)"
                                    if manual_track: item.tracking_number = manual_track
                                    db.commit()
                                    st.toast("Marked as Sent!")
                                    time.sleep(1)
                                    st.rerun()

    # --- TAB 3: REPAIR STATION ---
    with tab_orders:
        st.subheader("Order Manager")
        try:
            all_orders = database.get_all_orders()
            if all_orders:
                total_orders = len(all_orders)
                st.metric("Total Order Count", total_orders)
                
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
                
                st.divider()
                st.markdown("### 🛠️ Repair & Force Dispatch")
                st.info("Select a Standard order to fix addresses or force a re-send via PostGrid.")
                
                c_sel, c_act = st.columns([3, 1])
                with c_sel:
                    order_opts = [f"{x['ID']} ({x['Status']})" for x in data]
                    selected_order_str = st.selectbox("Select Order to Fix", ["Select..."] + order_opts)
                
                if selected_order_str and selected_order_str != "Select...":
                    selected_uuid_str = selected_order_str.split(" ")[0]
                    selected_id = str(selected_uuid_str)

                    with database.get_db_session() as db:
                        record = db.query(database.LetterDraft).filter(database.LetterDraft.id == selected_id).first()
                        if not record:
                            record = db.query(database.Letter).filter(database.Letter.id == selected_id).first()
                            
                        if record:
                            st.markdown(f"**Processing Order:** `{selected_id}`")
                            
                            t_addr = parse_address_data(getattr(record, 'recipient_data', None) or record.to_addr)
                            f_addr = parse_address_data(getattr(record, 'sender_data', None) or record.from_addr)
                            
                            st.markdown("#### Edit Recipient Data & Re-Dispatch")
                            c1, c2 = st.columns(2)
                            with c1:
                                new_name = st.text_input("Recipient Name", value=t_addr.get('name', ''), key="rep_name")
                                new_city = st.text_input("City", value=t_addr.get('city', ''), key="rep_city")
                            with c2:
                                new_street = st.text_input("Street", value=t_addr.get('address_line1', '') or t_addr.get('street', ''), key="rep_street")
                                new_zip = st.text_input("Zip", value=t_addr.get('zip_code', '') or t_addr.get('zip', ''), key="rep_zip")
                            
                            new_content = st.text_area("Letter Body", value=record.content, height=150, key="rep_body")
                            
                            col_api, col_man, col_save = st.columns(3)
                            updated_to = {"name": new_name, "address_line1": new_street, "city": new_city, "state": t_addr.get('state', 'NA'), "zip": new_zip}
                            updated_str = json.dumps(updated_to)

                            with col_api:
                                if st.button("🚀 Force API Dispatch", use_container_width=True):
                                    if len(new_zip) < 5 or not new_street:
                                        st.error("Invalid Address.")
                                    else:
                                        record.recipient_data = updated_str
                                        if hasattr(record, 'to_addr'): record.to_addr = updated_str
                                        record.content = new_content
                                        db.commit()
                                        
                                        if mailer and letter_format:
                                            pdf = letter_format.create_pdf(new_content, updated_to, f_addr)
                                            res = mailer.send_letter(pdf, updated_to, f_addr, description=f"Repair {selected_id}")
                                            if res: 
                                                record.status = "Sent"; record.tracking_number = res; db.commit()
                                                st.success("Dispatched!"); st.rerun()
                                            else: st.error("API Rejected Request")
                            
                            with col_man:
                                if st.button("🖨️ Move to Manual Queue", use_container_width=True):
                                    record.recipient_data = updated_str
                                    if hasattr(record, 'to_addr'): record.to_addr = updated_str
                                    record.content = new_content
                                    record.status = "Queued (Manual)"
                                    db.commit()
                                    st.success("Moved to Manual Print Queue!")
                                    time.sleep(1)
                                    st.rerun()
                                    
                            with col_save:
                                if st.button("💾 Save Changes Only", use_container_width=True):
                                    record.recipient_data = updated_str
                                    if hasattr(record, 'to_addr'): record.to_addr = updated_str
                                    record.content = new_content
                                    db.commit()
                                    st.success("Data Updated")

        except Exception as e: st.error(f"Error fetching orders: {e}")

    # --- TAB 4: RECORDINGS ---
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
            st.divider()
            st.markdown("### 🎧 Review & Action")
            rec_options = {f"{r['Date']} | {r['From']} | {r['SID']}": r for r in st.session_state.active_recordings}
            sel_rec_label = st.selectbox("Select Recording", ["Select..."] + list(rec_options.keys()))
            
            if sel_rec_label != "Select...":
                selected_rec = rec_options[sel_rec_label]
                sel_sid = selected_rec['SID']
                
                c_audio, c_del = st.columns([2, 1])
                with c_audio:
                    if st.button("▶️ Load Audio", key=f"load_{sel_sid}"):
                        sid = secrets_manager.get_secret("twilio.account_sid")
                        token = secrets_manager.get_secret("twilio.auth_token")
                        if sid and token:
                            try:
                                uri = selected_rec.get('URL', '').replace(".json", "").strip()
                                if not uri.startswith("http"): uri = f"https://api.twilio.com{uri}"
                                if not uri.endswith(".mp3"): mp3_url = f"{uri}.mp3"
                                else: mp3_url = uri
                                
                                r = requests.get(mp3_url, auth=(sid, token))
                                if r.status_code == 200: st.audio(r.content, format="audio/mp3")
                                else: st.error(f"Fetch Error: {r.status_code} (URL: {mp3_url})")
                            except Exception as e: st.error(f"Audio Error: {e}")
                        else: st.error("Twilio Credentials Missing")

                with c_del:
                    if st.button("🗑️ Permanently Delete", key=f"del_{sel_sid}", type="primary"):
                        sid = secrets_manager.get_secret("twilio.account_sid")
                        token = secrets_manager.get_secret("twilio.auth_token")
                        if sid and token:
                            try:
                                client = TwilioClient(sid, token)
                                client.recordings(sel_sid).delete()
                                st.success(f"Deleted {sel_sid}")
                                st.session_state.active_recordings = [r for r in st.session_state.active_recordings if r['SID'] != sel_sid]
                                time.sleep(1)
                                st.rerun()
                            except Exception as e: st.error(f"Delete Failed: {e}")
                        else: st.error("Twilio Credentials Missing")

    # --- TAB 5: PROMOS ---
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
        if promos: st.dataframe(pd.DataFrame(promos), use_container_width=True)
        else: st.info("No promo codes found.")

    # --- TAB 6: USERS & PARTNER PROVISIONING ---
    with tab_users:
        st.subheader("User & Partner Management")
        st.caption("Promote users to 'Partner' status to enable B2B features.")
        
        users = database.get_all_users()
        if users:
            # Create DataFrame
            safe_users = []
            for u in users:
                safe_users.append({
                    "Email": u.get("email"), 
                    "Name": u.get("full_name"), 
                    "Role": u.get("role", "user"),
                    "Credits": u.get("credits_remaining")
                })
            df_users = pd.DataFrame(safe_users)
            st.dataframe(df_users, use_container_width=True)
            
            st.divider()
            st.markdown("### 🔑 Provisioning")
            
            c_u, c_r, c_act = st.columns([3, 2, 1])
            with c_u:
                user_list = [f"{u['Email']} ({u['Role']})" for u in safe_users]
                selected_user_str = st.selectbox("Select User", ["Select..."] + user_list)
            
            with c_r:
                new_role = st.selectbox("Assign Role", ["user", "partner", "admin"])
                
            with c_act:
                st.write("") # Spacer
                if st.button("💾 Update Role", type="primary", use_container_width=True):
                    if selected_user_str and selected_user_str != "Select...":
                        target_email = selected_user_str.split(" ")[0]
                        if database.update_user_role(target_email, new_role):
                            st.success(f"Updated {target_email} to {new_role}")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("Update Failed")

    # --- TAB 7: LOGS ---
    with tab_logs:
        st.subheader("System Logs")
        if audit_engine:
            logs = audit_engine.get_audit_logs(limit=100)
            if logs: st.dataframe(pd.DataFrame(logs), use_container_width=True)
            else: st.info("No logs found.")
        else: st.warning("Audit Engine not loaded.")
        
    # --- TAB 8: HEALTH ---
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