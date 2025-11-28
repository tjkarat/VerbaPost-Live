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
try: import promo_engine
except: promo_engine = None

# --- HELPER: GENERATE PDF BYTES ---
def generate_admin_pdf(content, to_data, from_data, is_santa=False, is_heirloom=False, sig_data_str=None):
    try:
        to_str = f"{to_data.get('name','')}\n{to_data.get('street','')}\n{to_data.get('city','')}, {to_data.get('state','')} {to_data.get('zip','')}"
        
        # Handle Santa Sender
        if is_santa:
            from_str = "Santa Claus"
        else:
            from_str = f"{from_data.get('name','')}\n{from_data.get('street','')}\n{from_data.get('city','')}, {from_data.get('state','')} {from_data.get('zip','')}"

        # Signature Decoding
        sig_path = None
        if sig_data_str and len(sig_data_str) > 50:
            try:
                # Basic check to ensure it's base64
                if not sig_data_str.startswith("["): 
                    sig_bytes = base64.b64decode(sig_data_str)
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                        tmp.write(sig_bytes)
                        sig_path = tmp.name
            except: pass

        if letter_format:
            pdf_bytes = letter_format.create_pdf(
                content, 
                to_str, 
                from_str, 
                is_heirloom=is_heirloom,
                is_santa=is_santa,
                signature_path=sig_path
            )
            if sig_path and os.path.exists(sig_path): os.remove(sig_path)
            return pdf_bytes
        return None
    except Exception as e:
        st.error(f"PDF Generation Error: {e}")
        return None

def show_admin():
    # UPDATED TITLE TO V2.2
    st.title("🔐 Admin Console (v2.2)")
    
    u_email = st.session_state.get("user_email") or st.session_state.get("user", {}).email
    st.info(f"Logged in as: {u_email}")
    
    if st.button("⬅️ Return to App"):
        st.session_state.app_mode = "store"
        st.rerun()

    tab_orders, tab_santa, tab_heirloom, tab_maint, tab_promo, tab_danger = st.tabs(
        ["📦 Standard/Fix", "🎅 Santa", "🏺 Heirloom", "🛠️ Maint", "🎟️ Promo", "⚠️ Danger"]
    )

    # --- TAB 1: STANDARD ORDERS ---
    with tab_orders:
        st.subheader("Standard & Civic Orders")
        
        if database:
            data = database.fetch_all_drafts()
            std_orders = [d for d in data if d.get("Tier") and ("Standard" in d["Tier"] or "Civic" in d["Tier"])]
            
            if std_orders:
                df = pd.DataFrame(std_orders)
                st.dataframe(df[["ID", "Email", "Status", "Date", "Tier", "Price"]])
                
                st.divider()
                st.markdown("### 🔧 Fix & Resubmit")
                
                order_opts = {d["ID"]: f"ID {d['ID']} ({d['Status']}) - {d['Email']}" for d in std_orders}
                selected_id = st.selectbox("Select Order to Manage", options=list(order_opts.keys()), format_func=lambda x: order_opts[x])
                
                if selected_id:
                    order = next((d for d in std_orders if d["ID"] == selected_id), None)
                    
                    try: to_j = json.loads(order["Recipient"]) if isinstance(order["Recipient"], str) else order["Recipient"]
                    except: to_j = {}
                    try: from_j = json.loads(order["Sender"]) if isinstance(order["Sender"], str) else order["Sender"]
                    except: from_j = {}
                    
                    st.warning(f"Editing Order #{selected_id}")
                    
                    with st.form("fix_resubmit_form"):
                        c1, c2 = st.columns(2)
                        with c1:
                            st.markdown("RECIPIENT")
                            r_name = st.text_input("To Name", to_j.get("name",""))
                            r_str = st.text_input("To Street", to_j.get("street",""))
                            r_city = st.text_input("To City", to_j.get("city",""))
                            r_state = st.text_input("To State", to_j.get("state",""))
                            r_zip = st.text_input("To Zip", to_j.get("zip",""))
                            r_ctry = st.text_input("To Country", to_j.get("country","US"))
                            
                        with c2:
                            st.markdown("SENDER")
                            s_name = st.text_input("From Name", from_j.get("name",""))
                            s_str = st.text_input("From Street", from_j.get("street",""))
                            s_city = st.text_input("From City", from_j.get("city",""))
                            s_state = st.text_input("From State", from_j.get("state",""))
                            s_zip = st.text_input("From Zip", from_j.get("zip",""))
                            s_ctry = st.text_input("From Country", from_j.get("country","US"))

                        st.markdown("**Content Preview:**")
                        st.caption(order["Content"][:100] + "...")
                        
                        submitted = st.form_submit_button("💾 Update & Resend to PostGrid")
                        
                        if submitted:
                            new_to = {"name": r_name, "street": r_str, "city": r_city, "state": r_state, "zip": r_zip, "country": r_ctry}
                            new_from = {"name": s_name, "street": s_str, "city": s_city, "state": s_state, "zip": s_zip, "country": s_ctry}
                            
                            pdf_bytes = generate_admin_pdf(
                                order["Content"], new_to, new_from, 
                                is_santa=False, is_heirloom=False, 
                                sig_data_str=order.get("Signature")
                            )
                            
                            if mailer and pdf_bytes:
                                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                                    tmp.write(pdf_bytes); tmp_path = tmp.name
                                
                                pg_to = {
                                    'name': new_to['name'], 'address_line1': new_to['street'], 
                                    'address_city': new_to['city'], 'address_state': new_to['state'], 
                                    'address_zip': new_to['zip'], 'country_code': new_to['country']
                                }
                                pg_from = {
                                    'name': new_from['name'], 'address_line1': new_from['street'], 
                                    'address_city': new_from['city'], 'address_state': new_from['state'], 
                                    'address_zip': new_from['zip'], 'country_code': new_from['country']
                                }
                                
                                resp = mailer.send_letter(tmp_path, pg_to, pg_from)
                                os.remove(tmp_path)
                                
                                if resp and resp.get("id"):
                                    st.success(f"✅ Sent! ID: {resp.get('id')}")
                                    database.update_draft_data(selected_id, new_to, new_from, status="Completed")
                                    st.rerun()
                                else:
                                    st.error("❌ PostGrid Failed. Check logs.")
                            else:
                                st.error("Mailer module missing or PDF failed.")
            else:
                st.info("No standard orders found.")

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
                    try: to_j = json.loads(target_letter["Recipient"]) if isinstance(target_letter["Recipient"], str) else target_letter["Recipient"]
                    except: to_j = {}
                    
                    if st.button("Generate PDF", key="santa_gen"):
                        pdf_bytes = generate_admin_pdf(target_letter["Content"], to_j, {}, is_santa=True)
                        if pdf_bytes:
                            b64 = base64.b64encode(pdf_bytes).decode()
                            href = f'<a href="data:application/pdf;base64,{b64}" download="Santa_Order_{s_id}.pdf">⬇️ Download PDF</a>'
                            st.markdown(href, unsafe_allow_html=True)
                    
                    if st.button("Mark Completed", key="santa_mark"):
                        database.update_draft_data(s_id, None, None, status="Completed")
                        st.success("Updated!"); st.rerun()

    # --- TAB 3: HEIRLOOM (UPDATED) ---
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
                    try: to_j = json.loads(target_h["Recipient"]) if isinstance(target_h["Recipient"], str) else target_h["Recipient"]
                    except: to_j = {}
                    try: from_j = json.loads(target_h["Sender"]) if isinstance(target_h["Sender"], str) else target_h["Sender"]
                    except: from_j = {}

                    if st.button("Generate PDF", key="heir_gen"):
                        pdf_bytes = generate_admin_pdf(
                            target_h["Content"], to_j, from_j, is_heirloom=True, 
                            sig_data_str=target_h.get("Signature")
                        )
                        if pdf_bytes:
                            b64 = base64.b64encode(pdf_bytes).decode()
                            href = f'<a href="data:application/pdf;base64,{b64}" download="Heirloom_Order_{h_id}.pdf">⬇️ Download PDF</a>'
                            st.markdown(href, unsafe_allow_html=True)
                            
                    # --- ADDED BUTTON FOR HEIRLOOM ---
                    if st.button("Mark Completed", key="heir_mark"):
                        database.update_draft_data(h_id, None, None, status="Completed")
                        st.success("Order marked as Completed!")
                        st.rerun()

    # --- TAB 4: MAINT ---
    with tab_maint:
        st.subheader("System Health")
        if database:
            try:
                database.get_session().execute(text("SELECT 1")).fetchone()
                st.success("✅ Database Connected")
            except Exception as e: st.error(f"❌ DB Error: {e}")
        
        if secrets_manager.get_secret("postgrid.api_key"): st.success("✅ PostGrid Key Found")
        else: st.error("❌ PostGrid Key Missing")

        if secrets_manager.get_secret("email.password"): st.success("✅ Email Configured")
        else: st.error("❌ Email Password Missing")
        
        stripe_k = secrets_manager.get_secret("stripe.secret_key") or secrets_manager.get_secret("STRIPE_SECRET_KEY")
        if stripe_k: st.success("✅ Stripe Key Found")
        else: st.error("❌ Stripe Key Missing")

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

    # --- TAB 6: DANGER ---
    with tab_danger:
        if st.button("TRUNCATE ALL DATA"):
             # CAUTION: Ensure you really want this
             # database.clear_all_drafts() 
             st.warning("Feature disabled for safety.")