import streamlit as st
import pandas as pd
import json
import base64
import requests
from datetime import datetime
from sqlalchemy import text

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

# --- CRITICAL FIX: Safe Import for Address Standard ---
try:
    from address_standard import StandardAddress
except ImportError:
    # Fallback definition to prevent Admin Console crash
    from dataclasses import dataclass
    from typing import Optional, Dict, Any
    @dataclass
    class StandardAddress:
        name: str
        street: str
        address_line2: Optional[str] = ""
        city: str = ""
        state: str = ""
        zip_code: str = ""
        country: str = "US"
        def to_pdf_string(self): return f"{self.name}\n{self.street}"
        @classmethod
        def from_dict(cls, d): return cls(name=d.get('name',''), street=d.get('street',''))

def check_password():
    """Simple password gate for the admin panel."""
    if st.session_state.get("admin_logged_in"): return True
    
    st.info("🔒 Admin Access Required")
    pwd = st.text_input("Enter Admin Password", type="password", key="admin_pwd_input")
    
    # Get password from secrets or default to 'admin'
    correct_pwd = "admin" 
    if secrets_manager:
        fetched = secrets_manager.get_secret("ADMIN_PASSWORD") or secrets_manager.get_secret("admin.password")
        if fetched: correct_pwd = fetched
        
    if st.button("Unlock Console"):
        if pwd == correct_pwd:
            st.session_state.admin_logged_in = True
            st.rerun()
        else:
            st.error("❌ Incorrect Password")
    return False

def show_admin():
    # 1. Gatekeeper
    if not check_password(): return

    st.title("🔐 Admin Console")
    
    # 2. Header / Actions
    c_top, c_logout = st.columns([4, 1])
    with c_logout:
        if st.button("Log Out"):
            st.session_state.admin_logged_in = False
            st.session_state.app_mode = "store"
            st.rerun()

    # 3. Dashboard Tabs
    tab_overview, tab_manual, tab_promo = st.tabs(["📊 Overview", "🖨️ Manual Fulfillment", "🎟️ Promo Codes"])

    # --- TAB: OVERVIEW ---
    with tab_overview:
        st.subheader("System Health")
        # Simple health check indicators
        c1, c2, c3 = st.columns(3)
        with c1:
            if database: st.success("✅ Database") 
            else: st.error("❌ Database Missing")
        with c2:
            if secrets_manager and secrets_manager.get_secret("stripe.secret_key"): st.success("✅ Stripe Configured")
            else: st.warning("⚠️ Stripe Keys Missing")
        with c3:
            if secrets_manager and secrets_manager.get_secret("postgrid.api_key"): st.success("✅ PostGrid Configured")
            else: st.warning("⚠️ PostGrid Keys Missing")

        st.divider()
        
        # Database Stats
        if database:
            try:
                drafts = database.fetch_all_drafts()
                if drafts:
                    df = pd.DataFrame(drafts)
                    st.dataframe(df.tail(10), use_container_width=True)
                else:
                    st.info("No orders found in database.")
            except Exception as e:
                st.error(f"Failed to load data: {e}")

    # --- TAB: MANUAL FULFILLMENT ---
    with tab_manual:
        st.subheader("🖨️ Queue (Santa / Heirloom)")
        if database:
            try:
                all_drafts = database.fetch_all_drafts()
                # Filter for manual processing tiers
                manual_queue = [d for d in all_drafts if d.get('Tier') in ['Heirloom', 'Santa']]
                
                if not manual_queue:
                    st.success("🎉 Queue is empty! All caught up.")
                
                for row in manual_queue:
                    with st.expander(f"{row['Tier']} Order #{row['ID']} - {row['Email']}"):
                        c_info, c_act = st.columns([3, 1])
                        with c_info:
                            st.write(f"**Status:** {row['Status']}")
                            st.text_area("Content Preview", row['Content'], height=100, disabled=True, key=f"txt_{row['ID']}")
                        
                        with c_act:
                            # PDF Generation Button
                            if st.button("📄 Generate PDF", key=f"gen_{row['ID']}"):
                                try:
                                    # Parse addresses safely
                                    to_data = json.loads(row['Recipient']) if row['Recipient'] else {}
                                    from_data = json.loads(row['Sender']) if row['Sender'] else {}
                                    
                                    # Use the Safe StandardAddress class
                                    to_std = StandardAddress.from_dict(to_data)
                                    from_std = StandardAddress.from_dict(from_data)
                                    
                                    if letter_format:
                                        pdf_bytes = letter_format.create_pdf(
                                            row['Content'], 
                                            to_std.to_pdf_string(), 
                                            from_std.to_pdf_string(), 
                                            is_heirloom=("Heirloom" in row['Tier']), 
                                            is_santa=("Santa" in row['Tier'])
                                        )
                                        
                                        # Create Download Link
                                        b64 = base64.b64encode(pdf_bytes).decode()
                                        href = f'<a href="data:application/pdf;base64,{b64}" download="letter_{row["ID"]}.pdf" style="background-color:#4CAF50;color:white;padding:8px 16px;text-decoration:none;border-radius:4px;">⬇️ Download PDF</a>'
                                        st.markdown(href, unsafe_allow_html=True)
                                except Exception as e:
                                    st.error(f"Generation Error: {e}")

                            if st.button("✅ Mark Sent", key=f"sent_{row['ID']}"):
                                database.update_draft_data(row['ID'], status="Completed")
                                st.success("Marked as Completed!")
                                time.sleep(1)
                                st.rerun()

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
                    if ok: st.success(msg)
                    else: st.error(msg)
            
            # Show existing codes
            try:
                stats = promo_engine.get_all_codes_with_usage()
                if stats: st.dataframe(stats)
            except: pass