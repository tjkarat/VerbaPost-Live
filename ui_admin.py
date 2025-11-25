import streamlit as st
import pandas as pd
import resend

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
try: import mailer
except ImportError: mailer = None

def show_admin():
    st.title("🔐 Admin Console")
    
    # --- DIAGNOSTICS ROW ---
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Database", "✅ Connected" if database else "❌ Missing")
    c2.metric("Mailer", "✅ Active" if mailer else "❌ Missing")
    c3.metric("Promos", "✅ Active" if promo_engine else "❌ Missing")
    c4.metric("GA4", "✅ Active" if analytics else "❌ Missing")
    
    st.divider()

    # --- TABS ---
    tab_mail, tab_debug_mail, tab_promos = st.tabs(["🖨️ Mailroom", "📧 Mail Debugger", "🎟️ Promos"])
    
    # --- TAB 1: MAILROOM ---
    with tab_mail:
        st.subheader("Pending Letters")
        if database:
            letters = database.fetch_pending_letters()
            if letters:
                df = pd.DataFrame(letters)
                # Safe Column Selection
                cols = ["created_at", "user_email", "tier", "status", "price"]
                valid_cols = [c for c in cols if c in df.columns]
                st.dataframe(df[valid_cols], use_container_width=True)
                
                st.write("---")
                st.subheader("🖨️ Print Manager")
                
                letter_options = {
                    row['id']: f"{row.get('created_at', '?')} - {row.get('user_email', 'Unknown')} ({row.get('tier', '?')})" 
                    for row in letters
                }
                selected_id = st.selectbox("Select Letter", list(letter_options.keys()), format_func=lambda x: letter_options[x])
                
                if selected_id and letter_format:
                    letter_data = next((item for item in letters if item["id"] == selected_id), None)
                    if letter_data:
                        pdf_bytes = letter_format.create_pdf(
                            body_text=letter_data.get("body_text", ""),
                            recipient_info="Recipient Info",
                            sender_info="Sender Info",
                            is_heirloom=("Heirloom" in letter_data.get("tier", ""))
                        )
                        st.download_button("📄 Download PDF", pdf_bytes, f"letter_{selected_id}.pdf", "application/pdf", type="primary")
                        if st.button("Mark as Sent"):
                            database.mark_as_sent(selected_id)
                            st.success("Updated!")
                            st.rerun()
            else:
                st.info("📭 No pending letters.")

    # --- TAB 2: MAIL DEBUGGER (THE FIX) ---
    with tab_debug_mail:
        st.subheader("📧 Email System Diagnostic")
        
        # 1. Check Secrets
        try:
            key = st.secrets["resend"]["api_key"]
            st.success(f"✅ API Key Detected: `...{key[-4:]}`")
        except:
            st.error("❌ Resend API Key missing from secrets.toml")
            st.stop()

        # 2. Test Form
        st.write("Use this to send a real test email and see the server response.")
        
        c1, c2 = st.columns(2)
        from_email = c1.text_input("From Address", value="onboarding@resend.dev")
        to_email = c2.text_input("To Address", value="tjkarat@gmail.com")
        
        st.info("📝 **Note:** Unless you have verified 'verbapost.com' in the Resend Dashboard, you MUST use `onboarding@resend.dev` as the From Address.")
        
        if st.button("🚀 Send Test Email", type="primary"):
            try:
                resend.api_key = st.secrets["resend"]["api_key"]
                
                r = resend.Emails.send({
                    "from": from_email,
                    "to": to_email,
                    "subject": "🔔 VerbaPost Debug Test",
                    "html": "<h1>It Works!</h1><p>This is a test from the Admin Console.</p>"
                })
                
                st.success("✅ Email Sent Successfully!")
                with st.expander("View Server Response", expanded=True):
                    st.json(r)
                    
            except Exception as e:
                st.error("❌ Sending Failed")
                st.error(f"Error Details: {e}")
                st.caption("Tip: If error is '403 Forbidden', check if your domain is verified.")

    # --- TAB 3: PROMOS ---
    with tab_promos:
        c1, c2 = st.columns([1, 2])
        with c1:
            st.subheader("Create Code")
            new_code = st.text_input("New Code")
            if st.button("Create"):
                if promo_engine:
                    s, m = promo_engine.create_code(new_code)
                    if s: st.success("Created!")
                    else: st.error(m)
        with c2:
            if promo_engine:
                try:
                    data = promo_engine.get_all_codes_with_usage()
                    if data: st.dataframe(pd.DataFrame(data), use_container_width=True)
                except: st.warning("No data or DB error")