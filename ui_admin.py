import streamlit as st
import pandas as pd
import tempfile
import os
import json
import base64
import secrets_manager
from datetime import datetime
from sqlalchemy import text

# --- IMPORTS ---
try: import database
except: database = None
try: import letter_format
except: letter_format = None
try: import mailer
except: mailer = None
# FIX: Added promo_engine import here
try: import promo_engine
except: promo_engine = None

def generate_admin_pdf(letter, is_santa=False, is_heirloom=False):
    """Helper to generate PDF bytes"""
    try:
        raw_to = letter.get("Recipient", "{}")
        raw_from = letter.get("Sender", "{}")
        
        to_data = json.loads(raw_to) if isinstance(raw_to, str) else raw_to
        from_data = json.loads(raw_from) if isinstance(raw_from, str) else raw_from
        
        if not isinstance(to_data, dict): to_data = {}
        if not isinstance(from_data, dict): from_data = {}

        to_str = f"{to_data.get('name','')}\n{to_data.get('street','')}\n{to_data.get('city','')}, {to_data.get('state','')} {to_data.get('zip','')}"
        
        if is_santa:
            from_str = "Santa Claus"
        else:
            from_str = f"{from_data.get('name','')}\n{from_data.get('street','')}\n{from_data.get('city','')}, {from_data.get('state','')} {from_data.get('zip','')}"

        # Signature Decoding
        sig_path = None
        raw_sig = letter.get("Signature")
        if raw_sig and len(raw_sig) > 50:
            try:
                if not raw_sig.startswith("[[["): 
                    sig_bytes = base64.b64decode(raw_sig)
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                        tmp.write(sig_bytes)
                        sig_path = tmp.name
            except: pass

        if letter_format:
            pdf_data = letter_format.create_pdf(
                letter.get("Content", ""), 
                to_str, 
                from_str, 
                is_heirloom=is_heirloom,
                is_santa=is_santa,
                signature_path=sig_path
            )
            if sig_path and os.path.exists(sig_path): os.remove(sig_path)
            return pdf_data
        return None
    except Exception as e:
        st.error(f"PDF Generation Error: {e}")
        return None

def show_admin():
    st.title("🔐 Admin Console")
    
    u_email = st.session_state.get("user", {}).email if hasattr(st.session_state.get("user"), "email") else "Unknown"
    st.info(f"Logged in as: {u_email}")
    
    if st.button("⬅️ Return to App"):
        st.session_state.app_mode = "store"
        st.rerun()

    tab_orders, tab_santa, tab_heirloom, tab_maint, tab_promo, tab_danger = st.tabs(["📦 Standard", "🎅 Santa", "🏺 Heirloom", "🛠️ Maint", "🎟️ Promo", "⚠️ Danger"])

    # --- TAB 1: STANDARD ---
    with tab_orders:
        st.subheader("Standard Orders")
        if database:
            data = database.fetch_all_drafts()
            if data:
                std_orders = [d for d in data if d.get("Tier") and ("Standard" in d["Tier"] or "Civic" in d["Tier"])]
                if std_orders: st.dataframe(pd.DataFrame(std_orders))
                else: st.info("No standard orders.")
            else: st.info("No data.")

    # --- TAB 2: SANTA ---
    with tab_santa:
        st.subheader("🎅 Santa Fulfillment")
        if database:
            data = database.fetch_all_drafts()
            santa_orders = [d for d in data if d.get("Tier") and "Santa" in d["Tier"]]
            
            if santa_orders:
                st.dataframe(pd.DataFrame(santa_orders)[["ID", "Email", "Date", "Status"]])
                s_id = st.selectbox("Select Order ID", [d["ID"] for d in santa_orders], key="santa_sel")
                target_letter = next((d for d in santa_orders if d["ID"] == s_id), None)
                
                if target_letter:
                    if st.button("Generate PDF", key="santa_gen"):
                        pdf_bytes = generate_admin_pdf(target_letter, is_santa=True)
                        if pdf_bytes:
                            if isinstance(pdf_bytes, str): pdf_bytes = pdf_bytes.encode('latin-1', 'ignore')
                            b64 = base64.b64encode(pdf_bytes).decode()
                            href = f'<a href="data:application/pdf;base64,{b64}" download="Santa_Order_{s_id}.pdf">⬇️ Download PDF</a>'
                            st.markdown(href, unsafe_allow_html=True)
                    
                    if st.button("Mark Completed", key="santa_mark"):
                        database.update_status(s_id, "Completed")
                        st.success("Updated!"); st.rerun()

    # --- TAB 3: HEIRLOOM ---
    with tab_heirloom:
        st.subheader("🏺 Heirloom Fulfillment")
        if database:
            data = database.fetch_all_drafts()
            heir_orders = [d for d in data if d.get("Tier") and "Heirloom" in d["Tier"]]
            if heir_orders:
                st.dataframe(pd.DataFrame(heir_orders)[["ID", "Email", "Date", "Status"]])
                h_id = st.selectbox("Select Order ID", [d["ID"] for d in heir_orders], key="heir_sel")
                target_h = next((d for d in heir_orders if d["ID"] == h_id), None)
                
                if target_h:
                    if st.button("Generate PDF", key="heir_gen"):
                        pdf_bytes = generate_admin_pdf(target_h, is_heirloom=True)
                        if pdf_bytes:
                            if isinstance(pdf_bytes, str): pdf_bytes = pdf_bytes.encode('latin-1', 'ignore')
                            b64 = base64.b64encode(pdf_bytes).decode()
                            href = f'<a href="data:application/pdf;base64,{b64}" download="Heirloom_Order_{h_id}.pdf">⬇️ Download PDF</a>'
                            st.markdown(href, unsafe_allow_html=True)

   # --- TAB 4: MAINT ---
    with tab_maint:
        st.subheader("System Health")
        
        # 1. Database Check
        if database:
            try:
                database.get_session().execute(text("SELECT 1")).fetchone()
                st.success("✅ Database Connected")
            except Exception as e: st.error(f"❌ DB Error: {e}")
        
        # 2. PostGrid Check (Via Secrets Manager)
        # Checks [postgrid] api_key (Local) OR POSTGRID_API_KEY (GCP)
        if secrets_manager.get_secret("postgrid.api_key"):
            st.success("✅ PostGrid Key Found")
        else:
            st.error("❌ PostGrid Key Missing (Check secrets.toml or GCP Env Vars)")

        # 3. Email Check (Via Secrets Manager)
        # Checks [email] password (Local) OR EMAIL_PASSWORD (GCP)
        if secrets_manager.get_secret("email.password"):
            st.success("✅ Email Configured")
        else:
            st.error("❌ Email Password Missing (Check secrets.toml or GCP Env Vars)")
            
        # 4. Stripe Check
        if secrets_manager.get_secret("stripe.secret_key"):
             st.success("✅ Stripe Configured")
        else:
             st.error("❌ Stripe Key Missing")

    # --- TAB 5: PROMO ---
    with tab_promo:
        st.subheader("Promo Codes")
        if promo_engine:
            c1, c2 = st.columns(2)
            with c1:
                new_code = st.text_input("New Code")
                if st.button("Create Code"):
                    success, msg = promo_engine.create_code(new_code)
                    if success: st.success(msg)
                    else: st.error(msg)
            with c2:
                st.write("Usage Stats")
                stats = promo_engine.get_all_codes_with_usage()
                if stats: st.dataframe(stats)
        else:
            st.warning("Promo Engine not loaded.")

    # --- TAB 6: DANGER ---
    with tab_danger:
        if st.button("TRUNCATE ALL DATA"):
             if database: database.clear_all_drafts(); st.success("Wiped."); st.rerun()