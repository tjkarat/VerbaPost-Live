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

def show_admin():
    st.title("🔐 Admin Console")
    
    u_email = "Unknown"
    if st.session_state.get("user"):
        u = st.session_state.user
        if isinstance(u, dict): u_email = u.get("email", "Unknown")
        elif hasattr(u, "email"): u_email = u.email
        elif hasattr(u, "user"): u_email = u.user.email
            
    st.info(f"Logged in as: {u_email}")
    
    # Stats
    c1, c2, c3 = st.columns(3)
    with c1: st.metric("System", "Online 🟢")
    with c2: st.metric("Database", "Connected 🟢" if database else "Offline 🔴")
    
    email_status = "Configured 🟢" if "email" in st.secrets else "Missing 🔴"
    with c3: st.metric("Email", email_status)

    st.divider()
    
    tab_orders, tab_promo, tab_danger = st.tabs(["📦 Order Fulfillment", "🎟️ Promo Codes", "⚠️ Maintenance"])

    with tab_orders:
        st.subheader("Recent Letters")
        if database:
            data = database.fetch_all_drafts()
            if data:
                df = pd.DataFrame(data).sort_values(by="ID", ascending=False)
                
                def highlight_status(val):
                    color = 'lightgreen' if val == 'completed' else 'lightcoral'
                    return f'background-color: {color}'
                
                try:
                    st.dataframe(df[["ID", "Tier", "Email", "Date", "Status"]].style.map(highlight_status, subset=['Status']), use_container_width=True)
                except:
                    st.dataframe(df[["ID", "Tier", "Email", "Date", "Status"]], use_container_width=True)
                
                st.divider()
                st.subheader("🖨️ Process Order")
                
                # FIX: min_value=0 to allow selecting the first order
                selected_id = st.number_input("Enter Order ID:", min_value=0, step=1, key="admin_order_id_input")
                
                if st.button("Load Order Details"):
                    # Find letter
                    letter = next((item for item in data if item["ID"] == selected_id), None)
                    
                    if letter:
                        st.session_state.admin_active_letter = letter # Persist selection
                    else:
                        st.error("Order ID not found.")

                # Check if a letter is selected and display it
                if "admin_active_letter" in st.session_state and st.session_state.admin_active_letter:
                    letter = st.session_state.admin_active_letter
                    
                    # Only show if ID matches input (avoids stale data)
                    if letter["ID"] == selected_id:
                        st.success(f"Processing Order #{letter['ID']} ({letter['Tier']})")
                        
                        # Parse Data
                        try:
                            to_data = json.loads(letter["Recipient"])
                            recip_name = to_data.get('name', 'Unknown')
                            to_str = f"{recip_name}\n{to_data.get('street','')}\n{to_data.get('city','')}, {to_data.get('state','')} {to_data.get('zip','')}"
                        except: 
                            to_str = "Error parsing recipient"
                            recip_name = "Unknown"

                        try:
                            from_data = json.loads(letter["Sender"])
                            from_str = f"{from_data.get('name','')}\n{from_data.get('street','')}\n{from_data.get('city','')}, {from_data.get('state','')} {from_data.get('zip','')}"
                        except: from_str = f"From: {letter['Email']}"

                        sig_path = None
                        if letter.get("Signature") and len(str(letter["Signature"])) > 50:
                            try:
                                sig_bytes = base64.b64decode(letter["Signature"])
                                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                                    tmp.write(sig_bytes)
                                    sig_path = tmp.name
                            except: pass

                        c1, c2 = st.columns(2)
                        with c1:
                            st.text_area("Content", letter["Content"], height=200, disabled=True)
                            st.info(f"**To:**\n{to_str}")
                        
                        with c2:
                            # PDF Generation
                            if letter_format:
                                is_santa = "Santa" in letter["Tier"]
                                pdf_bytes = letter_format.create_pdf(
                                    letter["Content"], 
                                    to_str, 
                                    from_str, 
                                    is_heirloom="Heirloom" in letter["Tier"],
                                    language="English",
                                    signature_path=sig_path,
                                    is_santa=is_santa
                                )
                                
                                date_str = datetime.now().strftime("%Y-%m-%d")
                                safe_name = "".join(c for c in recip_name if c.isalnum())
                                fname = f"Order_{letter['ID']}_{safe_name}_{date_str}.pdf"
                                
                                b64_pdf = base64.b64encode(pdf_bytes).decode()
                                href = f'<a href="data:application/pdf;base64,{b64_pdf}" download="{fname}" style="text-decoration:none; color:white; background-color:#2a5298; padding:10px; border-radius:5px; display:block; text-align:center;">⬇️ Download PDF</a>'
                                st.markdown(href, unsafe_allow_html=True)
                                
                                if sig_path: os.remove(sig_path)
                            
                            st.write("")
                            st.write("")

                            if st.button("✅ Mark Complete & Notify"):
                                if database and hasattr(database, 'update_status'):
                                    database.update_status(letter['ID'], "completed")
                                
                                if mailer:
                                    # Notify Admin
                                    mailer.send_email(
                                        "support@verbapost.com", 
                                        f"Order #{letter['ID']} Completed", 
                                        f"Order for {recip_name} has been processed."
                                    )
                                    # Notify Customer
                                    mailer.send_email(
                                        letter['Email'], 
                                        "Your VerbaPost Letter is Sent! 📮", 
                                        f"Hi,\n\nYour letter to {recip_name} has been printed and mailed.\n\nThank you!"
                                    )
                                    st.success("Notifications Sent!")
                                st.rerun()

            else:
                st.info("No orders found.")
        else:
            st.warning("Database not connected.")

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

    st.markdown("---")
    # FIX: Ensure this button correctly sets state before rerunning
    if st.button("⬅️ Return to Main App"):
        st.session_state.app_mode = "store"
        st.rerun()