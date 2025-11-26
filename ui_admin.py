import streamlit as st
import pandas as pd
import tempfile
import os
import json
import base64

# Try imports to prevent crashing if modules missing
try: import database
except: database = None
try: import promo_engine
except: promo_engine = None
try: import letter_format
except: letter_format = None

def show_admin():
    st.title("🔐 Admin Console")
    
    u_email = "Unknown"
    if st.session_state.get("user"):
        u = st.session_state.user
        if isinstance(u, dict): u_email = u.get("email", "Unknown")
        elif hasattr(u, "email"): u_email = u.email
        elif hasattr(u, "user"): u_email = u.user.email
            
    st.info(f"Logged in as: {u_email}")
    
    # --- SYSTEM STATUS INDICATORS ---
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.metric("System", "Online 🟢")
    with c2: st.metric("Database", "Connected 🟢" if database else "Offline 🔴")
    with c3: st.metric("Stripe", "Configured 🟢" if "stripe" in st.secrets else "Missing 🔴")
    
    # EMAIL STATUS CHECK
    email_status = "Missing 🔴"
    if "email" in st.secrets and "smtp_server" in st.secrets["email"]:
        email_status = "Configured 🟢"
    with c4: st.metric("Email Relay", email_status)

    st.divider()
    
    # --- TABS ---
    tab_orders, tab_promo, tab_debug = st.tabs(["📦 Order Fulfillment", "🎟️ Promo Codes", "🐞 Debug"])

    # --- TAB 1: FULFILLMENT ---
    with tab_orders:
        st.subheader("Recent Letters")
        if database:
            data = database.fetch_all_drafts()
            if data:
                df = pd.DataFrame(data)
                # Show simplified table
                st.dataframe(df[["ID", "Tier", "Email", "Date", "Status"]], use_container_width=True)
                
                st.divider()
                st.subheader("🖨️ Print / Process Letter")
                
                # ID Selector
                selected_id = st.number_input("Enter Letter ID to Process:", min_value=1, step=1)
                
                # Find the specific letter
                letter = next((item for item in data if item["ID"] == selected_id), None)
                
                if letter:
                    st.success(f"Selected: Order #{letter['ID']} ({letter['Tier']})")
                    
                    # Parse Addresses
                    try:
                        to_data = json.loads(letter["Recipient"])
                        to_str = f"{to_data.get('name','')}\n{to_data.get('street','')}\n{to_data.get('city','')}, {to_data.get('state','')} {to_data.get('zip','')}"
                    except: to_str = "Error parsing recipient"

                    try:
                        from_data = json.loads(letter["Sender"])
                        from_str = f"{from_data.get('name','')}\n{from_data.get('street','')}\n{from_data.get('city','')}, {from_data.get('state','')} {from_data.get('zip','')}"
                    except: from_str = f"From: {letter['Email']}"

                    # Decode Signature if present
                    sig_path = None
                    if letter.get("Signature") and len(str(letter["Signature"])) > 50:
                        try:
                            sig_bytes = base64.b64decode(letter["Signature"])
                            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                                tmp.write(sig_bytes)
                                sig_path = tmp.name
                        except: pass

                    c_view, c_action = st.columns(2)
                    with c_view:
                        st.markdown("**Letter Content:**")
                        st.text_area("Body", letter["Content"], height=200, disabled=True)
                        st.caption(f"**Recipient:**\n{to_str}")
                    
                    with c_action:
                        st.markdown("**Actions**")
                        # PDF GENERATION
                        if letter_format:
                            is_santa = "Santa" in letter["Tier"]
                            try:
                                pdf_bytes = letter_format.create_pdf(
                                    letter["Content"], 
                                    to_str, 
                                    from_str, 
                                    is_heirloom="Heirloom" in letter["Tier"],
                                    language="English",
                                    signature_path=sig_path,
                                    is_santa=is_santa
                                )
                                
                                # Create Download Link
                                b64_pdf = base64.b64encode(pdf_bytes).decode()
                                href = f'<a href="data:application/pdf;base64,{b64_pdf}" download="Order_{letter["ID"]}.pdf" style="text-decoration:none; color:white; background-color:#4CAF50; padding:10px; border-radius:5px; display:block; text-align:center;">⬇️ Download PDF</a>'
                                st.markdown(href, unsafe_allow_html=True)
                            except Exception as e:
                                st.error(f"PDF Error: {e}")
                            finally:
                                if sig_path: os.remove(sig_path)
                        else:
                            st.error("Letter Format module missing.")
                else:
                    st.info("Enter a valid ID above.")
            else:
                st.info("No drafts found in database.")
        else:
            st.warning("Database not connected.")

    # --- TAB 2: PROMO ---
    with tab_promo:
        st.subheader("Generate Single-Use Code")
        if promo_engine:
            if st.button("Generate Code"):
                code = promo_engine.generate_code()
                st.success(f"New Code: `{code}`")
        else: st.warning("Promo engine not loaded.")

    # --- TAB 3: DEBUG ---
    with tab_debug:
        st.write("**Secrets Check:**")
        st.write(f"Has Stripe: {'stripe' in st.secrets}")
        st.write(f"Has Admin: {'admin' in st.secrets}")
        st.write(f"Has Email: {'email' in st.secrets}")

    st.markdown("---")
    if st.button("⬅️ Return to Main App"):
        st.session_state.app_mode = "splash"
        st.rerun()