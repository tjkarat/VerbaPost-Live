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
    
    # 1. Stats
    c1, c2, c3 = st.columns(3)
    with c1: st.metric("System", "Online 🟢")
    with c2: st.metric("Database", "Connected 🟢" if database else "Offline 🔴")
    with c3: st.metric("Stripe", "Configured 🟢" if "stripe" in st.secrets else "Missing 🔴")

    st.divider()
    tab_orders, tab_promo = st.tabs(["📦 Order Fulfillment", "🎟️ Promo Codes"])

    with tab_orders:
        st.subheader("Recent Letters")
        if database:
            data = database.fetch_all_drafts()
            if data:
                df = pd.DataFrame(data)
                st.dataframe(df[["ID", "Tier", "Email", "Date", "Status"]], use_container_width=True)
                
                st.divider()
                st.subheader("🖨️ Print / Process Letter")
                selected_id = st.number_input("Enter Letter ID to Process:", min_value=1, step=1)
                
                letter = next((item for item in data if item["ID"] == selected_id), None)
                
                if letter:
                    st.success(f"Selected: Order #{letter['ID']} ({letter['Tier']})")
                    
                    # --- FIX: Parse JSON Addresses ---
                    try:
                        to_data = json.loads(letter["Recipient"])
                        to_str = f"{to_data.get('name', '')}\n{to_data.get('address_line1', '')}\n{to_data.get('address_city', '')}, {to_data.get('address_state', '')} {to_data.get('address_zip', '')}"
                    except: to_str = "Error parsing recipient"

                    try:
                        from_data = json.loads(letter["Sender"])
                        from_str = f"{from_data.get('name', '')}\n{from_data.get('address_line1', '')}\n{from_data.get('address_city', '')}, {from_data.get('address_state', '')} {from_data.get('address_zip', '')}"
                    except: from_str = f"From: {letter['Email']}"

                    # --- FIX: Decode Signature ---
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
                        st.markdown("**Recipient:**")
                        st.code(to_str)
                    
                    with c_action:
                        st.markdown("**Generate PDF**")
                        if st.button("Generate & Download PDF"):
                            if letter_format:
                                pdf_bytes = letter_format.create_pdf(
                                    letter["Content"], 
                                    to_str, 
                                    from_str, 
                                    is_heirloom="Heirloom" in letter["Tier"],
                                    language="English",
                                    signature_path=sig_path
                                )
                                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                                    tmp.write(pdf_bytes)
                                    tmp_path = tmp.name
                                    
                                with open(tmp_path, "rb") as f:
                                    st.download_button("⬇️ Download PDF", f, f"Order_{letter['ID']}.pdf", "application/pdf")
                                
                                # Cleanup
                                if sig_path: os.remove(sig_path)
                            else: st.error("Letter Format module missing.")
                else: st.info("Enter an ID above.")
            else: st.info("No drafts found.")
        else: st.warning("Database not connected.")

    with tab_promo:
        # ... promo code logic ...
        pass
    
    if st.button("⬅️ Return to Main App"):
        st.session_state.current_view = "splash"
        st.rerun()