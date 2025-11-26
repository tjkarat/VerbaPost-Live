import streamlit as st
import pandas as pd
import tempfile
import os

# Imports
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

    # --- TAB 1: FULFILLMENT ---
    with tab_orders:
        st.subheader("Recent Letters")
        if database:
            data = database.fetch_all_drafts()
            if data:
                df = pd.DataFrame(data)
                # Show main table
                st.dataframe(df[["ID", "Tier", "Email", "Date", "Status"]], use_container_width=True)
                
                st.divider()
                st.subheader("🖨️ Print / Process Letter")
                
                # Selector
                selected_id = st.number_input("Enter Letter ID to Process:", min_value=1, step=1)
                
                # Find selected letter
                letter = next((item for item in data if item["ID"] == selected_id), None)
                
                if letter:
                    st.success(f"Selected: Order #{letter['ID']} ({letter['Tier']})")
                    
                    c_view, c_action = st.columns(2)
                    with c_view:
                        st.markdown("**Letter Content:**")
                        st.text_area("Transcription", letter["Content"], height=200, disabled=True)
                    
                    with c_action:
                        st.markdown("**Generate PDF**")
                        recip_addr = st.text_area("Recipient Address (Override)", "Recipient Name\n123 Street\nCity, State Zip")
                        
                        if st.button("Generate & Download PDF"):
                            if letter_format:
                                try:
                                    # FIX: Changed 'lang' to 'language' to match letter_format.py
                                    pdf_bytes = letter_format.create_pdf(
                                        letter["Content"], 
                                        recip_addr, 
                                        f"From: {letter['Email']}", 
                                        is_heirloom=("Heirloom" in letter["Tier"]),
                                        language="English" 
                                    )
                                    
                                    # Create temp file for download
                                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                                        tmp.write(pdf_bytes)
                                        tmp_path = tmp.name
                                        
                                    with open(tmp_path, "rb") as f:
                                        st.download_button(
                                            label="⬇️ Download PDF",
                                            data=f,
                                            file_name=f"Order_{letter['ID']}.pdf",
                                            mime="application/pdf"
                                        )
                                except Exception as e:
                                    st.error(f"PDF Generation Error: {e}")
                            else:
                                st.error("Letter Format module missing.")
                else:
                    st.info("Enter an ID above to view details.")
            else:
                st.info("No drafts found.")
        else:
            st.warning("Database not connected.")

    # --- TAB 2: PROMO CODES ---
    with tab_promo:
        st.subheader("Generate Single-Use Code")
        if promo_engine:
            if st.button("Generate Code"):
                code = promo_engine.generate_code()
                st.success(f"New Code: `{code}`")
        else: st.warning("Promo engine not loaded.")

    st.markdown("---")
    if st.button("⬅️ Return to Main App"):
        st.session_state.current_view = "splash"
        st.rerun()