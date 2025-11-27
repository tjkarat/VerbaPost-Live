import streamlit as st
import pandas as pd
import tempfile
import os
import json
import base64
from datetime import datetime

try: import database
except: database = None
try: import letter_format
except: letter_format = None
try: import mailer
except: mailer = None

def show_admin():
    st.title("🔐 Admin Console")
    
    tab_orders, tab_santa, tab_danger = st.tabs(["📦 Standard Orders", "🎅 Santa Export", "⚠️ Maintenance"])

    # --- STANDARD ORDERS ---
    with tab_orders:
        st.subheader("PostGrid / Lob Fulfillment")
        if database:
            data = database.fetch_all_drafts()
            if data:
                # Filter out Santa
                std_orders = [d for d in data if "Santa" not in d["Tier"]]
                st.dataframe(pd.DataFrame(std_orders))
                # ... (Keep existing logic for Standard) ...
            else:
                st.info("No orders.")

    # --- SANTA EXPORT ---
    with tab_santa:
        st.subheader("🎅 Santa Letter Fulfillment")
        st.info("Santa letters are meant to be printed and mailed by hand. Download the PDF below.")
        
        if database:
            data = database.fetch_all_drafts()
            santa_orders = [d for d in data if "Santa" in d["Tier"]]
            
            if santa_orders:
                st.dataframe(pd.DataFrame(santa_orders)[["ID", "Email", "Date", "Status"]])
                
                sel_id = st.number_input("Santa Order ID:", min_value=0, step=1)
                
                if st.button("Generate Santa PDF"):
                    letter = next((item for item in santa_orders if item["ID"] == sel_id), None)
                    if letter:
                        # Parse
                        try:
                            to_data = json.loads(letter["Recipient"])
                            recip_str = f"{to_data.get('name')}\n{to_data.get('street')}\n{to_data.get('city')}, {to_data.get('state')} {to_data.get('zip')}"
                        except: recip_str = "Error Parsing Address"
                        
                        pdf_bytes = letter_format.create_pdf(
                            letter["Content"], 
                            recip_str, 
                            "North Pole", 
                            is_heirloom=False,
                            is_santa=True
                        )
                        
                        b64 = base64.b64encode(pdf_bytes).decode()
                        href = f'<a href="data:application/pdf;base64,{b64}" download="Santa_Letter_{sel_id}.pdf" style="background-color:#d32f2f; color:white; padding:10px; border-radius:5px; text-decoration:none;">⬇️ Download PDF</a>'
                        st.markdown(href, unsafe_allow_html=True)
                        
                        st.write("")
                        if st.button("Mark 'Mailed' (No API Call)"):
                            if database: database.update_status(sel_id, "Completed")
                            st.success("Marked as mailed!")
                            st.rerun()
                    else:
                        st.error("ID not found in Santa orders.")
            else:
                st.info("No Santa orders yet.")

    with tab_danger:
        if st.button("Return to App"):
            st.session_state.app_mode = "store"
            st.rerun()