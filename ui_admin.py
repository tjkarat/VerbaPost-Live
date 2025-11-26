import streamlit as st
import pandas as pd
import tempfile
import os
import json
import base64

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
    
    # Stats
    c1, c2, c3 = st.columns(3)
    with c1: st.metric("System", "Online 🟢")
    with c2: st.metric("Database", "Connected 🟢" if database else "Offline 🔴")
    with c3: st.metric("Stripe", "Configured 🟢" if "stripe" in st.secrets else "Missing 🔴")

    st.divider()
    tab_orders, tab_promo = st.tabs(["📦 Order Fulfillment", "🎟️ Promo Codes"])

    # --- FULFILLMENT TAB ---
    with tab_orders:
        st.subheader("Recent Letters")
        if database:
            data = database.fetch_all_drafts()
            if data:
                df = pd.DataFrame(data)
                st.dataframe(df[["ID", "Tier", "Email", "Date", "Status"]], use_container_width=True)
                
                st.divider()
                st.subheader("🖨️ Print / Process Letter")
                
                # ID INPUT - NO RERUN TRIGGER
                selected_id = st.number_input("Enter Letter ID:", min_value=1, step=1)
                
                letter = next((item for item in data if item["ID"] == selected_id), None)
                
                if letter:
                    st.success(f"Selected: Order #{letter['ID']} ({letter['Tier']})")
                    
                    # Parse JSON
                    try:
                        to_data = json.loads(letter["Recipient"])
                        to_str = f"{to_data.get('name', '')}\n{to_data.get('street', '')}\n{to_data.get('city', '')}, {to_data.get('state', '')} {to_data.get('zip', '')}"
                    except: to_str = "Error parsing recipient"

                    try:
                        from_data = json.loads(letter["Sender"])
                        from_str = f"{from_data.get('name', '')}\n{from_data.get('street', '')}\n{from_data.get('city', '')}, {from_data.get('state', '')} {from_data.get('zip', '')}"
                    except: from_str = f"From: {letter['Email']}"

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
                        st.markdown("**Content:**")
                        st.text_area("Body", letter["Content"], height=200, disabled=True)
                    
                    with c_action:
                        st.markdown("**Generate PDF**")
                        # DOWNLOAD BUTTON IS SAFE - DOES NOT RERUN APP
                        if st.button("Generate PDF"):
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
                                
                                # Create download link manually to avoid rerun
                                b64_pdf = base64.b64encode(pdf_bytes).decode()
                                href = f'<a href="data:application/pdf;base64,{b64_pdf}" download="Order_{letter["ID"]}.pdf" style="text-decoration:none; color:white; background-color:#4CAF50; padding:10px; border-radius:5px;">⬇️ Download PDF</a>'
                                st.markdown(href, unsafe_allow_html=True)
                                
                                if sig_path: os.remove(sig_path)
                            else:
                                st.error("Letter Format module missing.")
                else:
                    st.info("Enter a valid ID above.")
            else:
                st.info("No drafts found.")
        else:
            st.warning("Database not connected.")

    # --- PROMO TAB ---
    with tab_promo:
        st.subheader("Generate Code")
        if promo_engine:
            if st.button("Generate New Code"):
                code = promo_engine.generate_code()
                st.success(f"New Code: `{code}`")

    st.markdown("---")
    # Explicit Return Button
    if st.button("⬅️ Return to Main App"):
        st.session_state.app_mode = "store" # Go to store, not splash
        st.rerun()