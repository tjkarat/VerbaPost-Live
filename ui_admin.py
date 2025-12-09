import streamlit as st
import pandas as pd
import json
import base64
import requests
import time
from datetime import datetime

# --- ROBUST IMPORTS ---
# We wrap these in try/except blocks so the Admin panel doesn't crash 
# just because one module is missing.
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

# --- SAFE IMPORT: Address Standard ---
# This prevents a crash if the address model changes or is missing
try:
    from address_standard import StandardAddress
except ImportError:
    # Fallback class if the real one is missing
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
    """
    Simple password gate for the admin panel.
    Checks against secrets.toml or defaults to 'admin'.
    """
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
    if "user_email" in st.session_state:
        st.caption(f"Logged in as: {st.session_state.user_email}")
    
    # 2. Header / Actions
    c_top, c_logout = st.columns([4, 1])
    with c_logout:
        if st.button("Log Out"):
            st.session_state.admin_logged_in = False
            st.session_state.app_mode = "store"
            st.rerun()

    # 3. Dashboard Tabs
    tab_overview, tab_manage, tab_promo = st.tabs(["📊 Live Feed", "🛠️ Order Management", "🎟️ Promo Codes"])

    # --- TAB: LIVE FEED (With Health Checks) ---
    with tab_overview:
        # --- SYSTEM HEALTH DASHBOARD ---
        st.subheader("System Health")
        c1, c2, c3, c4, c5 = st.columns(5)
        
        with c1:
            if database: st.success("✅ Database") 
            else: st.error("❌ DB Missing")
        
        with c2:
            # Check Stripe
            has_stripe = False
            if secrets_manager:
                if secrets_manager.get_secret("stripe.secret_key") or secrets_manager.get_secret("STRIPE_SECRET_KEY"):
                    has_stripe = True
            if has_stripe: st.success("✅ Stripe")
            else: st.warning("⚠️ Stripe Key")

        with c3:
            # Check PostGrid
            has_pg = False
            if secrets_manager:
                if secrets_manager.get_secret("postgrid.api_key") or secrets_manager.get_secret("POSTGRID_API_KEY"):
                    has_pg = True
            if has_pg: st.success("✅ PostGrid")
            else: st.warning("⚠️ PostGrid Key")

        with c4:
            # Check OpenAI
            has_ai = False
            if secrets_manager:
                if secrets_manager.get_secret("openai.api_key") or secrets_manager.get_secret("OPENAI_API_KEY"):
                    has_ai = True
            if has_ai: st.success("✅ OpenAI")
            else: st.warning("⚠️ OpenAI Key")

        with c5:
            # Check Geocodio
            has_geo = False
            if secrets_manager:
                if secrets_manager.get_secret("geocodio.api_key") or secrets_manager.get_secret("GEOCODIO_API_KEY"):
                    has_geo = True
            if has_geo: st.success("✅ Geocodio")
            else: st.warning("⚠️ Geo Key")

        st.divider()

        # --- RECENT ORDERS ---
        st.subheader("All Orders (Newest First)")
        if database:
            try:
                drafts = database.fetch_all_drafts() # Fetch ALL
                if drafts:
                    df = pd.DataFrame(drafts)
                    # Show useful columns first
                    cols = ["ID", "Date", "Status", "Tier", "Email", "Price"]
                    existing_cols = [c for c in cols if c in df.columns]
                    st.dataframe(df[existing_cols], use_container_width=True, height=500)
                else:
                    st.info("Database empty.")
            except Exception as e:
                st.error(f"Failed to load data: {e}")

    # --- TAB: ORDER MANAGEMENT (Fix Failed Orders) ---
    with tab_manage:
        st.subheader("🛠️ Fix & Fulfill")
        
        filter_opt = st.radio("Show Orders:", ["Failed / Errors Only", "Manual Queue (Santa/Heirloom)", "All Orders"], horizontal=True)
        
        if database:
            try:
                all_drafts = database.fetch_all_drafts()
                
                # --- FILTER LOGIC ---
                if filter_opt == "Failed / Errors Only":
                    queue = [d for d in all_drafts if d.get('Status') in ['Failed', 'Error', 'Payment Failed']]
                    if not queue: st.success("✅ No failed orders found!")
                    
                elif filter_opt == "Manual Queue (Santa/Heirloom)":
                    queue = [d for d in all_drafts if d.get('Tier') in ['Heirloom', 'Santa']]
                    if not queue: st.info("No manual orders pending.")
                    
                else: # All
                    queue = all_drafts[:50] # Limit to 50 for performance
                    st.caption("Showing last 50 orders for performance.")

                # --- DISPLAY CARDS ---
                for row in queue:
                    with st.expander(f"#{row['ID']} | {row['Tier']} | {row['Email']} | Status: {row['Status']}"):
                        c1, c2 = st.columns([2, 1])
                        
                        with c1:
                            st.markdown(f"**Created:** {row['Date']}")
                            st.text_area("Content", row['Content'], height=100, disabled=True, key=f"txt_{row['ID']}")
                            st.code(f"To: {row['Recipient']}\nFrom: {row['Sender']}", language="json")
                        
                        with c2:
                            st.write("**Actions:**")
                            
                            # 1. Regenerate PDF
                            if st.button("📄 View PDF", key=f"pdf_{row['ID']}"):
                                try:
                                    to_d = json.loads(row['Recipient']) if row['Recipient'] else {}
                                    from_d = json.loads(row['Sender']) if row['Sender'] else {}
                                    to_std = StandardAddress.from_dict(to_d)
                                    from_std = StandardAddress.from_dict(from_d)
                                    
                                    if letter_format:
                                        pdf_bytes = letter_format.create_pdf(
                                            row['Content'], 
                                            to_std.to_pdf_string(), 
                                            from_std.to_pdf_string(), 
                                            is_heirloom=("Heirloom" in row['Tier']), 
                                            is_santa=("Santa" in row['Tier'])
                                        )
                                        if pdf_bytes:
                                            b64 = base64.b64encode(pdf_bytes).decode()
                                            st.markdown(f'<a href="data:application/pdf;base64,{b64}" download="letter_{row["ID"]}.pdf" style="background-color:#4CAF50;color:white;padding:8px;text-decoration:none;border-radius:4px;">⬇️ Download PDF</a>', unsafe_allow_html=True)
                                        else:
                                            st.error("PDF generation failed (empty).")
                                except Exception as e:
                                    st.error(f"PDF Error: {e}")

                            # 2. Force Status Update
                            new_stat = st.selectbox("Set Status", ["Completed", "Failed", "Refunded"], key=f"stat_{row['ID']}")
                            if st.button("Update Status", key=f"upd_{row['ID']}"):
                                database.update_draft_data(row['ID'], status=new_stat)
                                st.toast(f"Updated order #{row['ID']} to {new_stat}")
                                time.sleep(1); st.rerun()
            except Exception as e:
                st.error(f"Error loading queue: {e}")

    # --- TAB: PROMO CODES (With Usage Stats) ---
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
                        time.sleep(1)
                        st.rerun()
                    else: st.error(msg)
            
            st.write("---")
            st.markdown("### Active Codes")
            
            # --- FIX: VISIBLE TABLE LOGIC ---
            try:
                stats = promo_engine.get_all_codes_with_usage()
                if stats and len(stats) > 0: 
                    st.dataframe(stats, use_container_width=True)
                else:
                    st.info("No promo codes found (or database connection failed).")
            except Exception as e:
                st.error(f"Failed to fetch promo stats: {e}")
        else:
            st.error("Promo Engine module missing.")