import streamlit as st
import pandas as pd
import time
import json
import os
import requests
from datetime import datetime

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
        # Soften errors for permission-restricted keys
        if "403" in msg or "401" in msg:
            return "⚠️ Online (Restricted)", "orange"
        return f"❌ Error: {msg[:50]}...", "red"

def run_system_health_checks():
    """Runs connectivity tests for all external services."""
    results = []

    # 1. DATABASE
    def check_db():
        with database.get_db_session() as db:
            from sqlalchemy import text
            db.execute(text("SELECT 1"))
    status, color = check_connection("Database", check_db)
    results.append({"Service": "Database (Supabase)", "Status": status, "Color": color})

    # 2. STRIPE
    def check_stripe():
        k = secrets_manager.get_secret("stripe.secret_key")
        if not k: raise Exception("Missing Key")
        stripe.api_key = k
        stripe.Balance.retrieve()
    status, color = check_connection("Stripe", check_stripe)
    results.append({"Service": "Stripe Payments", "Status": status, "Color": color})

    # 3. OPENAI (FIXED: Removed invalid 'limit' param)
    def check_openai():
        k = secrets_manager.get_secret("openai.api_key")
        if not k: raise Exception("Missing Key")
        client = openai.OpenAI(api_key=k)
        client.models.list() 
    status, color = check_connection("OpenAI", check_openai)
    results.append({"Service": "OpenAI (Intelligence)", "Status": status, "Color": color})

    # 4. TWILIO
    def check_twilio():
        sid = secrets_manager.get_secret("twilio.account_sid")
        token = secrets_manager.get_secret("twilio.auth_token")
        if not sid or not token: raise Exception("Missing Credentials")
        client = TwilioClient(sid, token)
        client.api.v2010.accounts(sid).fetch()
    status, color = check_connection("Twilio", check_twilio)
    results.append({"Service": "Twilio (Voice)", "Status": status, "Color": color})

    # 5. POSTGRID (FIXED: Aligned URL with mailer.py)
    def check_postgrid():
        k = secrets_manager.get_secret("postgrid.api_key") or secrets_manager.get_secret("POSTGRID_API_KEY")
        if not k: raise Exception("Missing Key")
        # Standard check that matches the mailer's base URL
        r = requests.get("https://api.postgrid.com/v1/letters?limit=1", headers={"x-api-key": k})
        if r.status_code not in [200, 201]: raise Exception(f"API {r.status_code}")
    status, color = check_connection("PostGrid (Mail)", check_postgrid)
    results.append({"Service": "PostGrid (Fulfillment)", "Status": status, "Color": color})

    # 6. GEOCODIO
    def check_geocodio():
        k = secrets_manager.get_secret("geocodio.api_key") or secrets_manager.get_secret("GEOCODIO_API_KEY")
        if not k: raise Exception("Missing Key")
        r = requests.get(f"https://api.geocod.io/v1.7/geocode?q=1600+Pennsylvania+Ave+NW,Washington,DC&api_key={k}")
        if r.status_code != 200: raise Exception(f"API {r.status_code}")
    status, color = check_connection("Geocodio (Civic)", check_geocodio)
    results.append({"Service": "Geocodio (Civic)", "Status": status, "Color": color})

    # 7. RESEND (FIXED: Whitespace stripper)
    def check_resend():
        k_raw = secrets_manager.get_secret("email.password") or secrets_manager.get_secret("RESEND_API_KEY")
        if not k_raw: raise Exception("Missing Key")
        
        # STRIP WHITESPACE to prevent 400 Bad Request
        k = k_raw.strip()
        
        headers = {"Authorization": f"Bearer {k}"}
        # Check domains endpoint to verify auth
        r_dom = requests.get("https://api.resend.com/domains", headers=headers)
        
        # 403 is acceptable for 'Sending-Only' keys
        if r_dom.status_code == 403:
            return 
        if r_dom.status_code != 200: 
            raise Exception(f"API {r_dom.status_code}")
            
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

    # --- TAB 2: ORDERS ---
    with tab_orders:
        st.subheader("Order Manager")
        try:
            all_orders = database.get_all_orders()
            if all_orders:
                total_orders = len(all_orders)
                PAGE_SIZE = 50
                col_pg1, col_pg2 = st.columns([1, 3])
                with col_pg1:
                    total_pages = max(1, (total_orders // PAGE_SIZE) + (1 if total_orders % PAGE_SIZE > 0 else 0))
                    page_num = st.number_input("Page", min_value=1, max_value=total_pages, value=1)
                
                start_idx = (page_num - 1) * PAGE_SIZE
                end_idx = min(start_idx + PAGE_SIZE, total_orders)
                with col_pg2:
                    st.caption(f"Showing orders {start_idx + 1} to {end_idx} of {total_orders}")

                current_batch = all_orders[start_idx:end_idx]
                data = []
                for o in current_batch:
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
                st.dataframe(pd.DataFrame(data), use_container_width=True)
                
                st.divider()
                st.markdown("### 🛠️ Repair & Fulfillment")
                oid = st.text_input("Enter Order UUID to Fix/Retry") 
                if oid:
                    pass 
            else:
                st.info("No orders found in database.")
        except Exception as e:
            st.error(f"Error fetching orders: {e}")

    # --- TAB 3: GHOST CALLS ---
    with tab_ghosts:
        st.subheader("👻 Unclaimed Heirloom Calls")
        if not ai_engine:
            st.error("AI Engine missing.")
        else:
            if st.button("Scan Twilio Logs"):
                with st.spinner("Fetching logs..."):
                    try:
                        if hasattr(ai_engine, "fetch_voice_logs"):
                             calls = ai_engine.fetch_voice_logs()
                        else:
                             calls = []
                        
                        if not calls:
                            st.warning("Twilio returned 0 calls.")
                        else:
                            users = database.get_all_users()
                            known_numbers = set()
                            for u in users:
                                p = u.get('parent_phone')
                                if p:
                                    clean = "".join(filter(lambda x: x.isdigit() or x == '+', str(p)))
                                    known_numbers.add(clean)
                                    if clean.startswith("+1"): known_numbers.add(clean[2:])
                            
                            ghosts = []
                            for c in calls:
                                c_from = c.get('From', "Unknown")
                                is_known = False
                                for k in known_numbers:
                                    if k in str(c_from):
                                        is_known = True
                                        break
                                if not is_known:
                                    ghosts.append({
                                        "Caller ID": c_from,
                                        "Time": c.get('Date', "?"),
                                        "Duration": c.get('Duration', "0s"),
                                        "Status": c.get('Status', "Unknown")
                                    })
                            if ghosts: st.dataframe(pd.DataFrame(ghosts), use_container_width=True)
                            else: st.success("No ghost calls found.")
                    except Exception as e:
                        st.error(f"Error scanning calls: {e}")

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
        if promos: st.dataframe(pd.DataFrame(promos), use_container_width=True)

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
            logs = audit_engine.get_recent_logs(limit=100)
            if logs: st.dataframe(pd.DataFrame(logs), use_container_width=True)
            else: st.info("No logs found.")
        else: st.warning("Audit Engine not loaded.")

# Safety Alias
render_admin = render_admin_page