import streamlit as st
import pandas as pd

# --- SAFETY IMPORTS ---
try: import database
except ImportError: database = None
try: import letter_format
except ImportError: letter_format = None
try: import ai_engine
except ImportError: ai_engine = None
try: import analytics
except ImportError: analytics = None
try: import promo_engine
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
                # 1. Convert to DataFrame
                df = pd.DataFrame(letters)
                
                # 2. CRITICAL FIX: Ensure columns exist before selecting them
                # This prevents the "KeyError" crash if DB has old/bad data
                expected_cols = ["created_at", "user_email", "tier", "status", "price"]
                for col in expected_cols:
                    if col not in df.columns:
                        df[col] = "Unknown" # Fill missing data with a placeholder
                
                # 3. Display Safe DataFrame
                st.dataframe(
                    df[["created_at", "user_email", "tier", "status", "price"]], 
                    use_container_width=True
                )
                
                st.write("---")
                
                # 4. Print Manager
                st.subheader("🖨️ Print Manager")
                
                # Use .get() for safe dictionary access
                letter_options = {
                    row['id']: f"{row.get('created_at', '?')} - {row.get('user_email', 'Unknown')} ({row.get('tier', '?')})" 
                    for row in letters
                }
                
                selected_id = st.selectbox("Select Letter to Print", options=list(letter_options.keys()), format_func=lambda x: letter_options[x])
                
                if selected_id:
                    letter_data = next((item for item in letters if item["id"] == selected_id), None)
                    
                    if letter_data and letter_format:
                        pdf_bytes = letter_format.create_pdf(
                            body_text=letter_data.get("body_text", ""),
                            recipient_info=f"{letter_data.get('recipient_name', '')}\n{letter_data.get('recipient_street', '')}", 
                            sender_info="VerbaPost Sender",      
                            is_heirloom=("Heirloom" in letter_data.get("tier", ""))
                        )
                        
                        st.download_button(
                            label="📄 Download PDF",
                            data=pdf_bytes,
                            file_name=f"letter_{selected_id}.pdf",
                            mime="application/pdf",
                            type="primary"
                        )
                        
                        if st.button("Mark as Sent"):
                            database.mark_as_sent(selected_id)
                            st.success("Status Updated!")
                            st.rerun()
            else:
                st.info("📭 No pending letters found.")
        else:
            st.error("Database connection missing.")

    # --- TAB 2: PROMO CODES ---
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
                else:
                    st.error("Promo Engine missing")
        
        with c2:
            st.subheader("Active Codes & Usage")
            if promo_engine:
                try:
                    data = promo_engine.get_all_codes_with_usage()
                    if data:
                        st.dataframe(pd.DataFrame(data), use_container_width=True)
                    else:
                        st.info("No codes found.")
                except Exception as e:
                    st.warning(f"Could not load logs. Did you run the SQL? Error: {e}")

    # --- TAB 3: USERS ---
    with tab_users:
        st.info("User metrics coming soon.")