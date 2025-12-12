import streamlit as st
import pandas as pd
import json
import base64
import requests
import time
import tempfile
import os
from datetime import datetime

# --- ROBUST IMPORTS ---
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
try: import civic_engine
except ImportError: civic_engine = None

# Fallback Class
try:
    from address_standard import StandardAddress
except ImportError:
    from dataclasses import dataclass
    @dataclass
    class StandardAddress:
        name: str; street: str; address_line2: str = ""; city: str = ""; state: str = ""; zip_code: str = ""; country: str = "US"
        def to_postgrid_payload(self):
             return {'name': self.name, 'address_line1': self.street, 'address_line2': self.address_line2, 'address_city': self.city, 'address_state': self.state, 'address_zip': self.zip_code, 'country_code': self.country}
        def to_pdf_string(self): return f"{self.name}\n{self.street}"
        @classmethod
        def from_dict(cls, d): return cls(name=d.get('name',''), street=d.get('street',''))

def check_password():
    if st.session_state.get("admin_logged_in"): return True
    st.info("🔒 Admin Access Required")
    pwd = st.text_input("Enter Admin Password", type="password", key="admin_pwd")
    
    # 1. Check Secrets
    correct_pwd = secrets_manager.get_secret("admin.password")
    # 2. Fallback default
    if not correct_pwd: correct_pwd = "admin" 
    
    if st.button("Login"):
        if pwd == correct_pwd:
            st.session_state.admin_logged_in = True
            st.rerun()
        else:
            st.error("Incorrect Password")
    return False

def show_admin():
    if not check_password(): return

    st.title("🔐 VerbaPost Admin")
    tab_orders, tab_promo, tab_health = st.tabs(["📦 Orders", "🏷️ Promo Codes", "❤️ System Health"])

    # --- TAB: ORDERS ---
    with tab_orders:
        if st.button("🔄 Refresh List"): st.rerun()
        
        if database:
            try:
                data = database.fetch_all_drafts()
                if not data:
                    st.info("No orders found.")
                else:
                    df = pd.DataFrame(data)
                    # Show recent orders first
                    st.dataframe(df[["ID", "Date", "Email", "Tier", "Status", "Price"]], use_container_width=True)
                    
                    st.markdown("### 🔍 Order Inspector")
                    selected_id = st.selectbox("Select Order ID to Manage", df["ID"].tolist())
                    
                    if selected_id:
                        row = df[df["ID"] == selected_id].iloc[0]
                        
                        # --- 1. EDIT & RESEND SECTION ---
                        with st.expander("✏️ Edit & Resend (Fix Errors)", expanded=True):
                            st.warning(f"Editing Order #{selected_id}")
                            
                            # Parse JSONs
                            try: r_json = json.loads(row['Recipient']) if row['Recipient'] else {}
                            except: r_json = {}
                            try: s_json = json.loads(row['Sender']) if row['Sender'] else {}
                            except: s_json = {}
                            
                            with st.form(f"edit_form_{selected_id}"):
                                c1, c2 = st.columns(2)
                                with c1:
                                    st.markdown("**Recipient**")
                                    rn = st.text_input("Name", r_json.get('name',''))
                                    ra1 = st.text_input("Street", r_json.get('street') or r_json.get('address_line1',''))
                                    ra2 = st.text_input("Line 2", r_json.get('address_line2',''))
                                    rc = st.text_input("City", r_json.get('city') or r_json.get('address_city',''))
                                    rs = st.text_input("State", r_json.get('state') or r_json.get('address_state',''))
                                    rz = st.text_input("Zip", r_json.get('zip') or r_json.get('address_zip',''))
                                
                                with c2:
                                    st.markdown("**Content**")
                                    new_content = st.text_area("Body Text", row['Content'], height=200)
                                    
                                if st.form_submit_button("💾 Save Changes & Update DB"):
                                    # Construct new JSON
                                    new_r = {
                                        'name': rn, 'street': ra1, 'address_line2': ra2,
                                        'city': rc, 'state': rs, 'zip': rz, 'country': 'US'
                                    }
                                    # Standardize for DB
                                    database.update_draft_data(
                                        selected_id, 
                                        to_addr=new_r, 
                                        content=new_content
                                    )
                                    st.success("Database Updated!")
                                    time.sleep(1)
                                    st.rerun()

                            # RESEND ACTION
                            st.markdown("#### 🚀 Actions")
                            col_resend, col_pdf = st.columns(2)
                            
                            with col_resend:
                                if st.button("📨 Retry PostGrid Submission", type="primary"):
                                    # 1. Re-fetch fresh data
                                    r_obj = StandardAddress(rn, ra1, ra2, rc, rs, rz)
                                    # 2. Generate PDF
                                    to_s = r_obj.to_pdf_string() + f"\n{rc}, {rs} {rz}"
                                    # Mock Sender string for PDF
                                    from_s = "VerbaPost User" # Simplified for admin retry
                                    
                                    pdf_bytes = letter_format.create_pdf(new_content, to_s, from_s, is_heirloom=(row['Tier']=="Heirloom"))
                                    
                                    # 3. Send
                                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tpdf:
                                        tpdf.write(pdf_bytes)
                                        tpath = tpdf.name
                                    
                                    try:
                                        # Convert StandardAddress to PostGrid Payload format
                                        pg_to = r_obj.to_postgrid_payload()
                                        # Admin Override Sender
                                        pg_from = {
                                            'name': s_json.get('name','VerbaPost'),
                                            'address_line1': s_json.get('street',''),
                                            'address_city': s_json.get('city',''),
                                            'address_state': s_json.get('state',''),
                                            'address_zip': s_json.get('zip',''),
                                            'country_code': 'US'
                                        }
                                        
                                        ok, msg = mailer.send_letter(tpath, pg_to, pg_from)
                                        if ok:
                                            st.success(f"✅ Sent! ID: {msg.get('id')}")
                                            database.update_draft_data(selected_id, status="Completed")
                                        else:
                                            st.error(f"❌ Failed: {msg}")
                                    finally:
                                        os.remove(tpath)

                        # --- 2. EXISTING TOOLS ---
                        st.json(row.to_dict())
                        
                        # Regenerate PDF (Local Download)
                        if st.button("📄 Download Current PDF"):
                             try:
                                r_json = json.loads(row['Recipient']) if row['Recipient'] else {}
                                s_json = json.loads(row['Sender']) if row['Sender'] else {}
                                content = row['Content'] or "[Empty]"
                                
                                to_addr = f"{r_json.get('name','')}\n{r_json.get('street','')}"
                                from_addr = f"{s_json.get('name','')}\n{s_json.get('street','')}"
                                
                                if letter_format:
                                    pdf_bytes = letter_format.create_pdf(content, to_addr, from_addr, is_heirloom=(row['Tier']=="Heirloom"))
                                    if pdf_bytes:
                                        b64 = base64.b64encode(pdf_bytes).decode()
                                        href = f'<a href="data:application/pdf;base64,{b64}" download="order_{row["ID"]}.pdf">⬇️ Click to Download</a>'
                                        st.markdown(href, unsafe_allow_html=True)
                             except Exception as e: st.error(f"PDF Error: {e}")

                        # Mark Sent
                        if st.button("✅ Mark as Completed Manually"):
                            database.update_draft_data(row['ID'], status="Completed")
                            st.success("Updated!")
                            time.sleep(1); st.rerun()

                        # Delete
                        if st.button("🗑️ Delete Order", key=f"del_{row['ID']}"):
                            if database.delete_draft(row['ID']):
                                st.success(f"Deleted #{row['ID']}")
                                time.sleep(1); st.rerun()

            except Exception as e:
                st.error(f"Error loading queue: {e}")

    # --- TAB: PROMO CODES ---
    with tab_promo:
        st.subheader("Manage Codes")
        if promo_engine:
            with st.form("new_promo"):
                c_code, c_limit = st.columns([2, 1])
                new_code = c_code.text_input("Code (e.g. SAVE20)")
                limit = c_limit.number_input("Max Uses", 1, 1000, 100)
                if st.form_submit_button("Create Code"):
                    ok, msg = promo_engine.create_code(new_code, limit)
                    if ok: 
                        st.success(msg)
                        time.sleep(1); st.rerun()
                    else: st.error(msg)
            
            st.write("---")
            try:
                stats = promo_engine.get_all_codes_with_usage()
                if stats and len(stats) > 0: 
                    st.dataframe(stats, use_container_width=True)
                else:
                    st.info("No promo codes found.")
            except Exception as e:
                st.error(f"Failed to fetch promo stats: {e}")

    # --- TAB: SYSTEM HEALTH ---
    with tab_health:
        st.subheader("🚦 Service Status")
        
        # 1. API Keys Presence Check
        st.markdown("#### Configuration Check (secrets.toml)")
        
        cols = st.columns(3)
        services = [
            ("Database (Supabase)", "SUPABASE_URL"),
            ("Payments (Stripe)", "stripe.secret_key"),
            ("Mailing (PostGrid)", "postgrid.api_key"),
            ("AI (OpenAI)", "openai.api_key"),
            ("Civic (Geocodio)", "geocodio.api_key"),
            ("Admin (Email)", "admin.email")
        ]
        
        for i, (name, key) in enumerate(services):
            val = secrets_manager.get_secret(key)
            # Special check for dot notation keys if direct lookup fails
            if not val and "." in key:
                parts = key.split(".")
                try: val = st.secrets[parts[0]][parts[1]]
                except: pass
            
            status = "✅ Connected" if val else "❌ Missing"
            cols[i % 3].metric(name, status)

        st.markdown("---")
        
        # 2. Live Connectivity Test
        st.markdown("#### Live Connectivity")
        if st.button("Run Deep Connectivity Test"):
            with st.spinner("Pinging services..."):
                
                # Database Test
                try:
                    if database and database.get_engine():
                        with database.get_db_session() as session:
                            session.execute(database.text("SELECT 1"))
                        st.success("✅ Database: Connection Active (SQLAlchemy)")
                    else:
                        st.error("❌ Database: Connection Failed")
                except Exception as e:
                    st.error(f"❌ Database Error: {e}")

                # PostGrid Test (Key Check + Import)
                if mailer:
                    pg_key = mailer.get_postgrid_key()
                    if pg_key:
                        st.success(f"✅ PostGrid: Client Initialized (Key: ...{pg_key[-4:]})")
                    else:
                        st.error("❌ PostGrid: Missing API Key")
                else:
                    st.error("❌ Mailer Module Not Loaded")
                
                # Geocodio Test
                geo_key = secrets_manager.get_secret("geocodio.api_key")
                if geo_key:
                     st.success("✅ Geocodio: Key Detected")
                else:
                     st.warning("⚠️ Geocodio: Missing (Civic features will fail)")