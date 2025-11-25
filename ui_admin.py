import streamlit as st
import pandas as pd

# --- SAFETY IMPORTS ---
try: import database
except ImportError: database = None
try: import letter_format
except ImportError: letter_format = None
try: import analytics
except ImportError: analytics = None
try: import promo_engine  # <--- NEW IMPORT
except ImportError: promo_engine = None

def show_admin():
    st.title("🔐 Admin Console")
    
    # --- DIAGNOSTICS ROW ---
    c1, c2, c3 = st.columns(3)
    c1.metric("Database", "✅ Connected" if database else "❌ Missing")
    c2.metric("Promos", "✅ Active" if promo_engine else "❌ Missing")
    c3.metric("GA4", "✅ Active" if analytics else "❌ Missing")
    
    st.divider()

    # --- TABS ---
    tab_mail, tab_promos, tab_users = st.tabs(["🖨️ Mailroom", "🎟️ Promos", "👥 Users"])
    
    # --- TAB 1: MAILROOM ---
    with tab_mail:
        st.subheader("Pending Letters")
        if database:
            letters = database.fetch_pending_letters()
            if letters:
                st.dataframe(pd.DataFrame(letters)[["created_at", "user_email", "tier", "status"]], use_container_width=True)
                
                # Print Manager
                st.write("---")
                st.subheader("Print Manager")
                letter_options = {
                    row['id']: f"{row.get('created_at', '?')} - {row.get('user_email', '?')} ({row.get('tier', '?')})" 
                    for row in letters
                }
                selected_id = st.selectbox("Select Letter", list(letter_options.keys()), format_func=lambda x: letter_options[x])
                
                if selected_id and letter_format:
                    letter_data = next((i for i in letters if i["id"] == selected_id), None)
                    if letter_data:
                        pdf_bytes = letter_format.create_pdf(
                            body_text=letter_data.get("body_text", ""),
                            recipient_info="Recipient Info",
                            sender_info="VerbaPost",
                            is_heirloom=("Heirloom" in letter_data.get("tier", ""))
                        )
                        st.download_button("Download PDF", pdf_bytes, f"letter_{selected_id}.pdf", "application/pdf")
                        if st.button("Mark Sent"):
                            database.mark_as_sent(selected_id)
                            st.rerun()
            else:
                st.info("No letters pending.")

    # --- TAB 2: PROMOS (NEW) ---
    with tab_promos:
        c1, c2 = st.columns([1, 2])
        
        with c1:
            st.subheader("Create Code")
            new_code = st.text_input("New Code (e.g. VIP100)")
            if st.button("Create Code", type="primary"):
                if promo_engine:
                    success, msg = promo_engine.create_code(new_code)
                    if success: st.success(f"Created {new_code}!")
                    else: st.error(msg)
                    st.rerun()
        
        with c2:
            st.subheader("Active Codes & Usage")
            if promo_engine:
                data = promo_engine.get_all_codes_with_usage()
                if data:
                    st.dataframe(pd.DataFrame(data), use_container_width=True)
                else:
                    st.info("No codes found.")

    with tab_users:
        st.info("User List Coming Soon")