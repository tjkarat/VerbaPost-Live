import streamlit as st
import pandas as pd
import tempfile
import os
import json

try: import database
except: database = None
try: import promo_engine
except: promo_engine = None
try: import letter_format
except: letter_format = None

def show_admin():
    st.title("🔐 Admin Console")
    
    # User check (same as before)
    # ...

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
                    
                    # Parse JSON addresses
                    try:
                        to_a = json.loads(letter["Recipient"])
                        # Construct readable string
                        to_str = f"{to_a.get('name')}\n{to_a.get('address_line1')}\n{to_a.get('address_city')}, {to_a.get('address_state')} {to_a.get('address_zip')}"
                    except: to_str = "Error parsing recipient data"

                    try:
                        from_a = json.loads(letter["Sender"])
                        from_str = f"From: {from_a.get('name')}\n{from_a.get('address_line1')}"
                    except: from_str = f"From: {letter['Email']}"

                    c_view, c_action = st.columns(2)
                    with c_view:
                        st.markdown("**Letter Content:**")
                        st.text_area("Body", letter["Content"], height=200, disabled=True)
                        st.markdown("**Addresses:**")
                        st.text(f"TO:\n{to_str}")
                    
                    with c_action:
                        st.markdown("**Generate PDF**")
                        if st.button("Generate & Download PDF"):
                            if letter_format:
                                # Generate PDF using stored data
                                pdf_bytes = letter_format.create_pdf(
                                    letter["Content"], 
                                    to_str, 
                                    from_str, 
                                    is_heirloom="Heirloom" in letter["Tier"],
                                    language="English"
                                )
                                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                                    tmp.write(pdf_bytes)
                                    tmp_path = tmp.name
                                    
                                with open(tmp_path, "rb") as f:
                                    st.download_button("⬇️ Download PDF", f, f"Order_{letter['ID']}.pdf", "application/pdf")
                            else: st.error("Letter Format module missing.")
                else: st.info("Enter an ID above.")
            else: st.info("No drafts found.")
        else: st.warning("Database not connected.")

    # (Promo tab same as before)
    # ...