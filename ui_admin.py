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
                if not admin_email: 
                    st.error("Admin credentials not configured.")
                elif email.strip() == admin_email and pwd.strip() == admin_pass:
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

    tab_health, tab_orders, tab_ghosts, tab_promos, tab_users, tab_logs = st.tabs([
        "🏥 Health", "📦 Orders", "📞 Ghost Calls", "🎟️ Promos", "👥 Users", "📜 Logs"
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
                            st.markdown(f"**Processing Order:** `{selected_uuid}` | **Tier:** `{getattr(record, 'tier', 'Unknown')}`")
                            
                            # --- VINTAGE WORKFLOW ---
                            if getattr(record, 'tier', '') == "Vintage" or record.status == "Pending Manual Fulfillment":
                                st.info("📜 **Vintage/Manual Workflow Detected**")
                                
                                # Re-Generate PDF for Print
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
                                
                                # STEP A: DOWNLOAD
                                with c1:
                                    if pdf_bytes:
                                        st.download_button(
                                            label="⬇️ Download PDF (For Wax Seal)",
                                            data=pdf_bytes,
                                            file_name=f"VINTAGE_{selected_uuid}.pdf",
                                            mime="application/pdf",
                                            key="dl_vin"
                                        )
                                    else: st.error("PDF Gen Failed")
                                    
                                # STEP B: MARK SHIPPED
                                with c2:
                                    manual_tracking = st.text_input("Manual Tracking Number", key="man_track")
                                    if st.button("✅ Mark Shipped (Manual)"):
                                        if manual_tracking:
                                            record.status = "Sent (Manual)"
                                            record.tracking_number = manual_tracking
                                            db.commit()
                                            st.success("Order Updated!")
                                            time.sleep(1)
                                            st.rerun()
                                        else:
                                            st.error("Please enter a tracking number first.")

                            # --- STANDARD WORKFLOW (REPAIR) ---
                            else:
                                # Retrieve User Profile for Fallback Data
                                user_profile = database.get_user_profile(record.user_email) if record.user_email else {}

                                def safe_val(attr, profile_key, fallback=""):
                                    val = getattr(record, attr, None)
                                    if val: return val
                                    if user_profile: return user_profile.get(profile_key, fallback)
                                    return fallback

                                cur_name = safe_val('to_name', 'full_name', 'Recipient Name')
                                cur_city = safe_val('to_city', 'address_city', 'City')
                                cur_street = safe_val('to_street', 'address_line1', 'Street Address')
                                cur_state = safe_val('to_state', 'address_state', 'State')
                                cur_zip = safe_val('to_zip', 'address_zip', 'Zip')

                                # Allow Editing
                                c1, c2 = st.columns(2)
                                with c1:
                                    new_to_name = st.text_input("Recipient Name", value=cur_name, key="rep_name")
                                    new_to_city = st.text_input("City", value=cur_city, key="rep_city")
                                    new_to_zip = st.text_input("Zip", value=cur_zip, key="rep_zip")
                                with c2:
                                    new_to_street = st.text_input("Street", value=cur_street, key="rep_street")
                                    new_to_state = st.text_input("State", value=cur_state, key="rep_state")
                                    
                                new_content = st.text_area("Letter Body", value=record.content, height=150, key="rep_body")
                                
                                # Generate PDF Object for Retry
                                to_obj = { "name": new_to_name, "address_line1": new_to_street, "city": new_to_city, "state": new_to_state, "zip": new_to_zip }
                                from_obj = {"name": "VerbaPost", "address_line1": "1000 Main", "city": "Nash", "state": "TN", "zip": "37203"}
                                
                                if letter_format:
                                    pdf_bytes = letter_format.create_pdf(new_content, to_obj, from_obj, tier=getattr(record, 'tier', 'Standard'))
                                else: pdf_bytes = b""

                                col_export, col_send = st.columns(2)
                                
                                with col_export:
                                    if pdf_bytes:
                                        st.download_button("⬇️ Download PDF", pdf_bytes, f"order_{selected_uuid}.pdf", "application/pdf")

                                with col_send:
                                    if st.button("🚀 Update & Force PostGrid", type="primary"):
                                        record.status = "Repaired/Sending"
                                        record.content = new_content
                                        db.commit()
                                        
                                        if mailer and pdf_bytes:
                                            with st.spinner("Dispatching..."):
                                                res_id = mailer.send_letter(
                                                    pdf_bytes, 
                                                    to_obj, 
                                                    from_obj, 
                                                    description=f"Admin Fix {selected_uuid}",
                                                    tier=getattr(record, 'tier', 'Standard')
                                                )
                                                if res_id:
                                                    record.status = f"Sent (Admin): {res_id}"
                                                    db.commit()
                                                    st.success(f"✅ Sent! ID: {res_id}")
                                                    time.sleep(2); st.rerun()
                                                else:
                                                    st.error("Mailing Failed.")
                        else:
                            st.error("Record not found.")
            else:
                st.info("No orders found.")
        except Exception as e:
            st.error(f"Error fetching orders: {e}")

    # --- TAB 3: GHOST CALLS ---
    with tab_ghosts:
        st.subheader("👻 Unclaimed Heirloom Calls")
        st.info("Scans Twilio for calls that didn't match a user's 'Parent Phone'.")
        
        if st.button("Scan Twilio Logs"):
            if not ai_engine:
                st.error("AI Engine not loaded.")
            else:
                with st.spinner("Scanning logs..."):
                    # 1. Fetch recent raw calls from Twilio
                    if hasattr(ai_engine, 'get_recent_call_logs'):
                        raw_calls = ai_engine.get_recent_call_logs(limit=50)
                    else:
                        raw_calls = []

                    # 2. Fetch all known user parent phones
                    users = database.get_all_users()
                    known_numbers = set()
                    
                    for u in users:
                        p = u.get('parent_phone')
                        if p:
                            norm = "".join(filter(str.isdigit, str(p)))
                            if len(norm) > 10 and norm.startswith('1'): norm = norm[1:]
                            known_numbers.add(norm)
                    
                    # 3. Filter for Ghosts
                    ghosts = []
                    for c in raw_calls:
                        c_from = c.get('from', '')
                        norm_c = "".join(filter(str.isdigit, str(c_from)))
                        if len(norm_c) > 10 and norm_c.startswith('1'): norm_c = norm_c[1:]
                        
                        if norm_c and norm_c not in known_numbers:
                            ghosts.append({
                                "From": c_from,
                                "Normalized": norm_c,
                                "Date": c.get('date'),
                                "Duration": c.get('duration'),
                                "Status": c.get('status'),
                                "SID": c.get('sid')
                            })
                    
                    if ghosts:
                        st.warning(f"Found {len(ghosts)} Ghost Calls")
                        df_ghosts = pd.DataFrame(ghosts)
                        st.dataframe(df_ghosts[['From', 'Date', 'Duration', 'Status']], use_container_width=True)
                    else:
                        st.success("✅ Clean! No ghost calls found.")

    # --- TAB 4: PROMOS ---
    with tab_promos:
        st.subheader("Manage Discounts")
        with st.expander("➕ Create New Code"):
            with st.form("new_promo"):
                c_code = st.text_input("Code").upper()
                c_val = st.number_input("Discount ($)", min_value=0.0)
                if st.form_submit_button("Create"):
                    if database.create_promo_code(c_code, c_val):
                        st.success(f"Created {c_code}")
                        time.sleep(1); st.rerun()
                    else: st.error("Failed.")
        
        promos = database.get_all_promos()
        if promos:
            try:
                with database.get_db_session() as session:
                    logs = session.query(database.PromoLog).all()
                    usage_map = {}
                    for log in logs:
                        c = log.code.upper() if log.code else "UNKNOWN"
                        usage_map[c] = usage_map.get(c, 0) + 1
                    for p in promos:
                        code_key = p.get('code', '').upper()
                        p['verified_usage'] = usage_map.get(code_key, 0)
            except: pass
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

# Safety Alias
render_admin = render_admin_page