import streamlit as st
import pandas as pd
import tempfile
import os
import json
import base64
from datetime import datetime

try: import database
except: database = None
try: import promo_engine
except: promo_engine = None
try: import letter_format
except: letter_format = None
try: import mailer
except: mailer = None

def generate_admin_pdf(order_list, target_id, is_santa=False, is_heirloom=False):
    """Helper to generate PDF and download link"""
    letter = next((item for item in order_list if item["ID"] == target_id), None)
    if letter:
        try:
            # Parse JSON addresses safely
            to_data = json.loads(letter["Recipient"]) if isinstance(letter["Recipient"], str) else letter["Recipient"]
            from_data = json.loads(letter["Sender"]) if isinstance(letter["Sender"], str) else letter["Sender"]
            
            # Ensure they are dicts
            if not isinstance(to_data, dict): to_data = {}
            if not isinstance(from_data, dict): from_data = {}

            # Format strings
            to_str = f"{to_data.get('name','')}\n{to_data.get('street','')}\n{to_data.get('city','')}, {to_data.get('state','')} {to_data.get('zip','')}"
            
            if is_santa:
                from_str = "Santa Claus\n123 Elf Road\nNorth Pole, 88888"
            else:
                from_str = f"{from_data.get('name','')}\n{from_data.get('street','')}\n{from_data.get('city','')}, {from_data.get('state','')} {from_data.get('zip','')}"

            # Generate
            if letter_format:
                pdf_bytes = letter_format.create_pdf(
                    letter["Content"], 
                    to_str, 
                    from_str, 
                    is_heirloom=is_heirloom,
                    is_santa=is_santa
                )
                
                b64 = base64.b64encode(pdf_bytes).decode()
                fname = f"Order_{target_id}.pdf"
                href = f'<a href="data:application/pdf;base64,{b64}" download="{fname}" style="background-color:#4CAF50; color:white; padding:10px; border-radius:5px; text-decoration:none; display:inline-block; margin-top:10px;">⬇️ Download PDF</a>'
                st.markdown(href, unsafe_allow_html=True)
                
                st.write("")
                if st.button(f"Mark Order #{target_id} as Completed"):
                    if database: database.update_status(target_id, "Completed")
                    st.success("Updated!")
                    st.rerun()
        except Exception as e:
            st.error(f"Error generating PDF: {e}")
    else:
        st.error("Order ID not found in this list.")def show_admin():
    st.title("🔐 Admin Console")
    
    u_email = "Unknown"
    if st.session_state.get("user"):
        u = st.session_state.user
        if isinstance(u, dict): u_email = u.get("email", "Unknown")
        elif hasattr(u, "email"): u_email = u.email
        elif hasattr(u, "user"): u_email = u.user.email
            
    st.info(f"Logged in as: {u_email}")
    
    if st.button("⬅️ Return to App"):
        st.session_state.app_mode = "store"
        st.rerun()
    
    # Stats
    c1, c2, c3 = st.columns(3)
    with c1: st.metric("System", "Online 🟢")
    with c2: st.metric("Database", "Connected 🟢" if database else "Offline 🔴")
    
    email_status = "Configured 🟢" if "email" in st.secrets else "Missing 🔴"
    with c3: st.metric("Email", email_status)

    st.divider()
    
    tab_orders, tab_santa, tab_heirloom, tab_maint, tab_promo, tab_danger = st.tabs(["📦 Standard Orders", "🎅 Santa Export", "🏺 Heirloom Export", "🛠️ Maintenance", "🎟️ Promo Codes", "⚠️ Danger Zone"])

    with tab_orders:
        st.subheader("Recent Standard Letters")
        if database:
            data = database.fetch_all_drafts()
            if data:
                # Filter for Standard/Civic orders
                std_orders = [d for d in data if "Standard" in d["Tier"] or "Civic" in d["Tier"]]
                
                if std_orders:
                    df = pd.DataFrame(std_orders).sort_values(by="ID", ascending=False)
                    # Helper for highlighting
                    def highlight_status(val):
                        color = 'lightgreen' if val == 'completed' else 'lightcoral'
                        return f'background-color: {color}'
                    try:
                        st.dataframe(df[["ID", "Tier", "Email", "Date", "Status"]].style.map(highlight_status, subset=['Status']), use_container_width=True)
                    except:
                        st.dataframe(df[["ID", "Tier", "Email", "Date", "Status"]], use_container_width=True)
                else:
                    st.info("No standard orders found.")
            else:
                st.info("No orders found.")
        else:
            st.warning("Database not connected.")

    with tab_santa:
        st.subheader("🎅 Santa Fulfillment")
        if database:
            data = database.fetch_all_drafts()
            santa_orders = [d for d in data if "Santa" in d["Tier"]]
            
            if santa_orders:
                st.dataframe(pd.DataFrame(santa_orders)[["ID", "Email", "Date", "Status"]])
                sel_id = st.number_input("Santa Order ID:", min_value=0, step=1, key="santa_id")
                
                if st.button("Generate Santa PDF"):
                    generate_admin_pdf(santa_orders, sel_id, is_santa=True)
            else:
                st.info("No Santa orders.")

    with tab_heirloom:
        st.subheader("🏺 Heirloom Fulfillment")
        st.info("Heirloom letters require manual printing on premium paper.")
        if database:
            data = database.fetch_all_drafts()
            heirloom_orders = [d for d in data if "Heirloom" in d["Tier"]]
            
            if heirloom_orders:
                st.dataframe(pd.DataFrame(heirloom_orders)[["ID", "Email", "Date", "Status"]])
                sel_h_id = st.number_input("Heirloom Order ID:", min_value=0, step=1, key="heirloom_id")
                
                if st.button("Generate Heirloom PDF"):
                    generate_admin_pdf(heirloom_orders, sel_h_id, is_heirloom=True)
            else:
                st.info("No Heirloom orders.")

    with tab_maint:
        st.subheader("System Health Check")
        
        # Database Check
        if database:
            try:
                # Simple query to test connection
                res = database.get_session().execute("SELECT 1").fetchone()
                st.success("✅ Database Connected")
            except Exception as e:
                st.error(f"❌ Database Error: {e}")
        else:
            st.error("❌ Database Module Missing")

        # Email Check
        email_key = st.secrets.get("email", {}).get("password") or st.secrets.get("resend", {}).get("api_key")
        if email_key:
            st.success("✅ Email Key Found")
        else:
            st.error("❌ Email Key Missing")

        # PostGrid Check
        pg_key = st.secrets.get("postgrid", {}).get("api_key")
        if pg_key:
            st.success("✅ PostGrid Key Found")
        else:
            st.error("❌ PostGrid Key Missing")

    with tab_promo:
        if promo_engine and st.button("Generate New Code"):
             code = promo_engine.generate_code()
             st.success(f"New Code: `{code}`")

    with tab_danger:
        st.warning("⚠️ Danger Zone")
        if st.button("TRUNCATE DATABASE (DELETE ALL)", type="primary"):
             if database and hasattr(database, 'clear_all_drafts'):
                 database.clear_all_drafts()
                 st.success("Database Wiped.")
                 st.rerun()
             else:
                 st.error("Function missing.")