import streamlit as st
import pandas as pd
import tempfile
import os
import json
import base64
from datetime import datetime
from sqlalchemy import text

try: import database
except: database = None
try: import promo_engine
except: promo_engine = None
try: import letter_format
except: letter_format = None
try: import mailer
except: mailer = None

def generate_admin_pdf(letter, is_santa=False, is_heirloom=False):
    """Helper to generate PDF bytes"""
    try:
        # Robust Data Parsing
        raw_to = letter.get("Recipient", "{}")
        raw_from = letter.get("Sender", "{}")
        
        to_data = json.loads(raw_to) if isinstance(raw_to, str) else raw_to
        from_data = json.loads(raw_from) if isinstance(raw_from, str) else raw_from
        
        if not isinstance(to_data, dict): to_data = {}
        if not isinstance(from_data, dict): from_data = {}

        to_str = f"{to_data.get('name','')}\n{to_data.get('street','')}\n{to_data.get('city','')}, {to_data.get('state','')} {to_data.get('zip','')}"
        from_str = "Santa Claus" if is_santa else f"{from_data.get('name','')}\n{from_data.get('street','')}"

        if letter_format:
            return letter_format.create_pdf(
                letter.get("Content", ""), 
                to_str, 
                from_str, 
                is_heirloom=is_heirloom,
                is_santa=is_santa
            )
        else:
            st.error("Letter Format module missing")
            return None
    except Exception as e:
        st.error(f"PDF Generation Error: {e}")
        return None

def show_admin():
    st.title("🔐 Admin Console")
    
    # -- HEADER & AUTH --
    u_email = st.session_state.get("user", {}).email if hasattr(st.session_state.get("user"), "email") else "Unknown"
    st.info(f"Logged in as: {u_email}")
    
    if st.button("⬅️ Return to App"):
        st.session_state.app_mode = "store"
        st.rerun()

    # -- TABS --
    tab_orders, tab_santa, tab_heirloom, tab_maint, tab_promo, tab_danger = st.tabs(["📦 Standard", "🎅 Santa", "🏺 Heirloom", "🛠️ Maint", "🎟️ Promo", "⚠️ Danger"])

    # --- TAB 1: STANDARD ---
    with tab_orders:
        st.subheader("Standard Orders")
        if database:
            data = database.fetch_all_drafts()
            if data:
                # Filter safely
                std_orders = [d for d in data if d.get("Tier") and ("Standard" in d["Tier"] or "Civic" in d["Tier"])]
                if std_orders:
                    st.dataframe(pd.DataFrame(std_orders))
                else:
                    st.info("No standard orders.")
            else: st.info("No data.")

# --- TAB 2: SANTA ---
    with tab_santa:
        st.subheader("🎅 Santa Fulfillment (Debug Mode)")
        if database:
            data = database.fetch_all_drafts()
            santa_orders = [d for d in data if d.get("Tier") and "Santa" in d["Tier"]]
            
            if santa_orders:
                st.dataframe(pd.DataFrame(santa_orders)[["ID", "Email", "Date", "Status"]])
                
                # SELECT ORDER
                s_id = st.selectbox("Select Order ID", [d["ID"] for d in santa_orders], key="santa_sel")
                target_letter = next((d for d in santa_orders if d["ID"] == s_id), None)
                
                if target_letter:
                    st.divider()
                    c1, c2 = st.columns(2)
                    
                    # 1. ORIGINAL DOWNLOAD BUTTON
                    with c1:
                        if st.button("Generate & Download PDF", key="gen_pdf_btn"):
                            with st.spinner("Generating..."):
                                try:
                                    pdf_bytes = generate_admin_pdf(target_letter, is_santa=True)
                                    if pdf_bytes:
                                        if isinstance(pdf_bytes, str): pdf_bytes = pdf_bytes.encode('latin-1')
                                        b64 = base64.b64encode(pdf_bytes).decode()
                                        fname = f"Santa_Order_{s_id}.pdf"
                                        href = f'<a href="data:application/pdf;base64,{b64}" download="{fname}" style="background-color:#d32f2f; color:white; padding:10px; border-radius:5px; text-decoration:none; display:block; text-align:center;">⬇️ Download PDF</a>'
                                        st.markdown(href, unsafe_allow_html=True)
                                    else:
                                        st.error("PDF Generation returned None.")
                                except Exception as e:
                                    st.error(f"Generation Failed: {e}")

                    # 2. NEW DEBUG BUTTON (Use this to find the error)
                    with c2:
                        if st.button("🐞 Debug PDF Generation"):
                            st.write("### Debug Log")
                            try:
                                st.info("1. Inspecting Data...")
                                st.json(target_letter)
                                
                                st.info("2. Attempting PDF Generation...")
                                # Call the function directly here to catch the crash
                                import letter_format
                                
                                # Manually parse data like the helper does to see if parsing fails
                                raw_to = target_letter.get("Recipient", "{}")
                                st.write(f"Raw Recipient Data Type: {type(raw_to)}")
                                
                                # Attempt generation
                                pdf_bytes = generate_admin_pdf(target_letter, is_santa=True)
                                
                                if pdf_bytes:
                                    st.success(f"✅ Success! PDF Size: {len(pdf_bytes)} bytes")
                                else:
                                    st.error("❌ Generator returned None (Check Console Logs)")
                                    
                            except Exception as e:
                                st.error("❌ CRITICAL ERROR CAUGHT")
                                st.exception(e) # This prints the red traceback box
                                
                    st.divider()
                    # 3. Mark Completed Button
                    if st.button(f"Mark Order #{s_id} Completed", key=f"btn_santa_{s_id}"):
                        database.update_status(s_id, "Completed")
                        st.success("Marked Completed!")
                        st.rerun()
            else: st.info("No Santa orders.")
    
    # --- TAB 3: HEIRLOOM ---
    with tab_heirloom:
        st.subheader("🏺 Heirloom Fulfillment")
        if database:
            data = database.fetch_all_drafts()
            heirloom_orders = [d for d in data if d.get("Tier") and "Heirloom" in d["Tier"]]
            
            if heirloom_orders:
                st.dataframe(pd.DataFrame(heirloom_orders)[["ID", "Email", "Date", "Status"]])
                
                h_id = st.selectbox("Select Order ID", [d["ID"] for d in heirloom_orders], key="heir_sel")
                target_h = next((d for d in heirloom_orders if d["ID"] == h_id), None)
                
                if target_h:
                    pdf_bytes = generate_admin_pdf(target_h, is_heirloom=True)
                    if pdf_bytes:
                        try:
                            if isinstance(pdf_bytes, str):
                                pdf_bytes = pdf_bytes.encode('latin-1')
                                
                            b64 = base64.b64encode(pdf_bytes).decode()
                            fname = f"Heirloom_Order_{h_id}.pdf"
                            href = f'<a href="data:application/pdf;base64,{b64}" download="{fname}" style="background-color:#8B4513; color:white; padding:10px; border-radius:5px; text-decoration:none; display:block; text-align:center;">⬇️ Download PDF</a>'
                            st.markdown(href, unsafe_allow_html=True)
                        except Exception as e:
                            st.error(f"Encoding Error: {e}")

                    st.divider()
                    if st.button(f"Mark Order #{h_id} Completed", key=f"btn_heir_{h_id}"):
                        database.update_status(h_id, "Completed")
                        st.success("Marked Completed!")
                        st.rerun()
            else: st.info("No Heirloom orders.")

    # --- TAB 4: MAINT ---
    with tab_maint:
        st.subheader("System Health")
        if database:
            try:
                database.get_session().execute(text("SELECT 1")).fetchone()
                st.success("✅ Database Connected")
            except Exception as e: st.error(f"❌ DB Error: {e}")
        
        pg_key = st.secrets.get("postgrid", {}).get("api_key")
        if pg_key: st.success("✅ PostGrid Key Found")
        else: st.error("❌ PostGrid Key Missing")

    # --- TAB 5/6: EXTRAS ---
    with tab_promo:
        if promo_engine and st.button("Generate Code"):
             st.success(f"Code: `{promo_engine.generate_code()}`")
    
    with tab_danger:
        if st.button("TRUNCATE ALL DATA"):
             if database: database.clear_all_drafts(); st.success("Wiped."); st.rerun()