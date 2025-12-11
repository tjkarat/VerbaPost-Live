import streamlit as st
import pandas as pd
import json
import base64
import requests
import time
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
    tab_orders, tab_promo = st.tabs(["📦 Orders", "🏷️ Promo Codes"])

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
                    st.dataframe(df[["ID", "Date", "Email", "Tier", "Status", "Price"]], use_container_width=True)
                    
                    st.markdown("### 🔍 Order Inspector")
                    selected_id = st.selectbox("Select Order ID to Manage", df["ID"].tolist())
                    
                    if selected_id:
                        row = df[df["ID"] == selected_id].iloc[0]
                        st.json(row.to_dict())
                        
                        # Actions
                        c1, c2, c3 = st.columns(3)
                        
                        # 1. Regenerate PDF
                        with c1:
                            if st.button("📄 Generate PDF", key=f"pdf_{row['ID']}"):
                                try:
                                    r_json = json.loads(row['Recipient']) if row['Recipient'] else {}
                                    s_json = json.loads(row['Sender']) if row['Sender'] else {}
                                    content = row['Content'] or "[Empty]"
                                    
                                    # Create addresses
                                    to_addr = StandardAddress.from_dict(r_json).to_pdf_string()
                                    from_addr = StandardAddress.from_dict(s_json).to_pdf_string()
                                    
                                    is_heirloom = (row['Tier'] == "Heirloom")
                                    is_santa = (row['Tier'] == "Santa")
                                    
                                    if letter_format:
                                        pdf_bytes = letter_format.create_pdf(content, to_addr, from_addr, is_heirloom=is_heirloom, is_santa=is_santa)
                                        if pdf_bytes:
                                            b64 = base64.b64encode(pdf_bytes).decode()
                                            href = f'<a href="data:application/pdf;base64,{b64}" download="order_{row["ID"]}.pdf" style="background-color:#4CAF50;color:white;padding:8px 16px;text-decoration:none;border-radius:4px;">⬇️ Download PDF</a>'
                                            st.markdown(href, unsafe_allow_html=True)
                                except Exception as e:
                                    st.error(f"Generation Error: {e}")

                        # 2. Mark Sent
                        with c2:
                            if st.button("✅ Mark Sent", key=f"sent_{row['ID']}"):
                                database.update_draft_data(row['ID'], status="Completed")
                                st.success("Marked as Completed!")
                                time.sleep(1); st.rerun()

                        # 3. MANUAL DELETE (NEW)
                        with c3:
                            if st.button("🗑️ Delete Order", key=f"del_{row['ID']}", type="primary"):
                                if database.delete_draft(row['ID']):
                                    st.success(f"Order #{row['ID']} Deleted!")
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.error("Delete failed.")

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