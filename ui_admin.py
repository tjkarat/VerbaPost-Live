import streamlit as st
import pandas as pd
import json
import base64
import requests
from datetime import datetime
from sqlalchemy import text

# --- IMPORTS ---
try: import database
except ImportError: database = None
try: import letter_format
except ImportError: letter_format = None
try: import promo_engine
except ImportError: promo_engine = None
try: import secrets_manager
except ImportError: secrets_manager = None
try: import mailer
except ImportError: mailer = None

def check_password():
    """Returns True if the user is logged in as admin."""
    if st.session_state.get("admin_logged_in"): return True
    
    pwd = st.text_input("Admin Password", type="password")
    
    correct_pwd = "admin" 
    if secrets_manager:
        fetched = secrets_manager.get_secret("ADMIN_PASSWORD")
        if fetched: correct_pwd = fetched
            
    if st.button("Login"):
        if pwd == correct_pwd:
            st.session_state.admin_logged_in = True
            st.rerun()
        else:
            st.error("Incorrect Password")
    return False

def check_service_health():
    """Checks connectivity to critical services."""
    health = {}
    
    # 1. Database Check
    try:
        if database and database.get_session():
            # Run a lightweight query
            with database.get_engine().connect() as conn:
                conn.execute(text("SELECT 1"))
            health["Database"] = True
        else:
            health["Database"] = False
    except: health["Database"] = False

    # 2. OpenAI Check (Key Presence)
    try:
        key = secrets_manager.get_secret("OPENAI_API_KEY")
        if key and key.startswith("sk-"): health["AI Engine"] = True
        else: health["AI Engine"] = False
    except: health["AI Engine"] = False

    # 3. Stripe Check (Key Presence)
    try:
        key = secrets_manager.get_secret("STRIPE_SECRET_KEY")
        if key and key.startswith("sk_"): health["Stripe"] = True
        else: health["Stripe"] = False
    except: health["Stripe"] = False

    # 4. Email / Resend Check
    try:
        key = secrets_manager.get_secret("email.password")
        if key and key.startswith("re_"): health["Email (Resend)"] = True
        else: health["Email (Resend)"] = False
    except: health["Email (Resend)"] = False
    
    return health

def show_admin():
    st.title("🔐 Admin Console")
    
    if not check_password():
        return

    if st.button("Logout"):
        st.session_state.admin_logged_in = False
        st.session_state.app_mode = "store"
        st.rerun()

    # --- TABS ---
    tab_overview, tab_drafts, tab_manual, tab_promo = st.tabs(["📊 Overview", "📝 Drafts & Fixes", "🖨️ Manual Fulfillment", "🎟️ Promo Codes"])

    # --- TAB 1: OVERVIEW ---
    with tab_overview:
        c_health, c_stats = st.columns([1, 2])
        
        with c_health:
            st.subheader("🔌 System Status")
            with st.container(border=True):
                status_map = check_service_health()
                for service, is_up in status_map.items():
                    icon = "✅" if is_up else "❌"
                    color = "green" if is_up else "red"
                    st.markdown(f"**{service}:** :{color}[{icon} {'Online' if is_up else 'Offline/Missing'}]")

        with c_stats:
            st.subheader("Business Metrics")
            if database:
                try:
                    drafts = database.fetch_all_drafts()
                    df = pd.DataFrame(drafts)
                    if not df.empty:
                        m1, m2, m3 = st.columns(3)
                        m1.metric("Total Orders", len(df))
                        m2.metric("Pending Admin", len(df[df['Status'] == 'Pending Admin']))
                        m3.metric("Completed", len(df[df['Status'] == 'Completed']))
                    else:
                        st.info("No data yet.")
                except Exception as e:
                    st.error(f"DB Error: {e}")

        st.divider()
        st.subheader("Recent Activity Log")
        if database:
            drafts = database.fetch_all_drafts()
            df = pd.DataFrame(drafts)
            if not df.empty:
                st.dataframe(df.head(15), use_container_width=True)

    # --- TAB 2: DRAFTS & FIXES ---
    with tab_drafts:
        st.subheader("Manage Orders")
        if database:
            drafts = database.fetch_all_drafts()
            if drafts:
                # Filter for Pending
                pending = [d for d in drafts if d['Status'] in ['Pending Admin', 'Failed/Retry']]
                
                if not pending:
                    st.success("No pending orders requiring attention.")
                
                for row in pending:
                    with st.expander(f"{row['Date']} - {row['Email']} ({row['Tier']})"):
                        c1, c2 = st.columns(2)
                        try: to_data = json.loads(row['Recipient']) if row['Recipient'] else {}
                        except: to_data = {}
                        
                        with c1:
                            st.write("Current Data:")
                            st.json(to_data)
                            
                        with c2:
                            st.write("Fix Address:")
                            with st.form(key=f"fix_form_{row['ID']}"):
                                n_name = st.text_input("Name", to_data.get('name',''))
                                n_str = st.text_input("Street", to_data.get('street','') or to_data.get('address_line1',''))
                                n_str2 = st.text_input("Apt/Suite", to_data.get('address_line2','') or to_data.get('street2',''))
                                n_city = st.text_input("City", to_data.get('city','') or to_data.get('address_city',''))
                                n_state = st.text_input("State", to_data.get('state','') or to_data.get('address_state',''))
                                n_zip = st.text_input("Zip", to_data.get('zip','') or to_data.get('address_zip',''))
                                
                                if st.form_submit_button("Update & Retry"):
                                    new_to = {
                                        "name": n_name, "street": n_str, "address_line2": n_str2,
                                        "city": n_city, "state": n_state, "zip": n_zip, "country": "US"
                                    }
                                    database.update_draft_data(row['ID'], to_addr=new_to, status="Retry")
                                    st.success("Updated!")
                                    st.rerun()

    # --- TAB 3: MANUAL FULFILLMENT ---
    with tab_manual:
        st.subheader("🖨️ Print Queue (Heirloom / Santa)")
        
        if database:
            all_drafts = database.fetch_all_drafts()
            manual_queue = [d for d in all_drafts if d['Status'] == 'Pending Admin' and d['Tier'] in ['Heirloom', 'Santa']]
            
            if not manual_queue:
                st.success("Queue empty! All manual letters processed.")
            
            for row in manual_queue:
                with st.container(border=True):
                    c_info, c_act = st.columns([3, 1])
                    with c_info:
                        st.markdown(f"**ID #{row['ID']}** | {row['Tier']} Letter")
                        st.caption(f"User: {row['Email']} | Date: {row['Date']}")
                    
                    with c_act:
                        if st.button(f"📄 Generate PDF", key=f"btn_pdf_{row['ID']}"):
                            try:
                                to_data = json.loads(row['Recipient']) if row['Recipient'] else {}
                                from_data = json.loads(row['Sender']) if row['Sender'] else {}
                                
                                # Address Construction (Standardized)
                                lines = [to_data.get('name', '')]
                                lines.append(to_data.get('street', '') or to_data.get('address_line1', ''))
                                line2 = to_data.get('address_line2') or to_data.get('street2')
                                if line2: lines.append(line2)
                                lines.append(f"{to_data.get('city', '')}, {to_data.get('state', '')} {to_data.get('zip', '')}")
                                if to_data.get('country', 'US') != 'US': lines.append(to_data.get('country'))
                                to_str = "\n".join(filter(None, lines))

                                f_lines = [from_data.get('name', '')]
                                f_lines.append(from_data.get('street', '') or from_data.get('address_line1', ''))
                                f_line2 = from_data.get('address_line2') or from_data.get('street2')
                                if f_line2: f_lines.append(f_line2)
                                f_lines.append(f"{from_data.get('city', '')}, {from_data.get('state', '')} {from_data.get('zip', '')}")
                                from_str = "\n".join(filter(None, f_lines))
                                
                                if letter_format:
                                    pdf_bytes = letter_format.create_pdf(
                                        row['Content'], to_str, from_str, 
                                        is_heirloom=("Heirloom" in row['Tier']),
                                        is_santa=("Santa" in row['Tier']),
                                        is_santa_sig=("Santa" in row['Tier'])
                                    )
                                    if pdf_bytes:
                                        b64 = base64.b64encode(pdf_bytes).decode()
                                        href = f'<a href="data:application/pdf;base64,{b64}" download="letter_{row["ID"]}.pdf" style="background-color:#4CAF50;color:white;padding:8px 12px;text-decoration:none;border-radius:4px;">📥 Download PDF</a>'
                                        st.markdown(href, unsafe_allow_html=True)
                                        
                                        if st.button(f"Mark #{row['ID']} Mailed"):
                                            database.update_draft_data(row['ID'], status="Completed")
                                            st.success("Completed!")
                                            st.rerun()
                            except Exception as e: st.error(f"Error: {e}")

        st.divider()
        st.subheader("📜 Historical Activity")
        if database:
            df_hist = pd.DataFrame(all_drafts)
            if not df_hist.empty:
                st.dataframe(df_hist.head(20), use_container_width=True)

    # --- TAB 4: PROMO CODES ---
    with tab_promo:
        st.subheader("Promo Codes")
        if promo_engine:
            c1, c2 = st.columns(2)
            with c1:
                with st.form("create_promo"):
                    new_code = st.text_input("New Code Name")
                    usage_limit = st.number_input("Max Uses", min_value=1, value=10)
                    if st.form_submit_button("Create Code"):
                        success, msg = promo_engine.create_code(new_code, usage_limit)
                        if success: st.success(msg)
                        else: st.error(msg)
            with c2:
                st.write("Active Codes")
                stats = promo_engine.get_all_codes_with_usage()
                if stats: st.dataframe(stats)