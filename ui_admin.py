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

def get_resend_key():
    try:
        if "resend" in st.secrets: return st.secrets["resend"]["api_key"]
        elif "email" in st.secrets: return st.secrets["email"]["password"]
    except: return None

def show_admin():
    st.title("🔐 Admin Console")
    
    # --- DIAGNOSTICS ---
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Database", "✅ Connected" if database else "❌ Missing")
    c2.metric("Mailer", "✅ Active" if mailer else "❌ Missing")
    c3.metric("Promos", "✅ Active" if promo_engine else "❌ Missing")
    c4.metric("GA4", "✅ Active" if analytics else "❌ Missing")
    
    st.divider()

    tab_mail, tab_debug, tab_promos = st.tabs(["🖨️ Mailroom", "📧 Debugger", "🎟️ Promos"])
    
    # --- MAILROOM ---
    with tab_mail:
        st.subheader("Pending Letters")
        if database:
            letters = database.fetch_pending_letters()
            if letters:
                df = pd.DataFrame(letters)
                cols = ["created_at", "user_email", "tier", "status", "price"]
                valid = [c for c in cols if c in df.columns]
                st.dataframe(df[valid], use_container_width=True)
                
                st.write("---")
                st.subheader("🖨️ Print & Ship Manager")
                
                # Create readable labels for dropdown
                letter_options = {
                    row['id']: f"{row.get('created_at', '?')} - {row.get('user_email', 'Unknown')} ({row.get('tier', '?')})" 
                    for row in letters
                }
                selected_id = st.selectbox("Select Letter", list(letter_options.keys()), format_func=lambda x: letter_options[x])
                
                if selected_id and letter_format:
                    letter_data = next((i for i in letters if i["id"] == selected_id), None)
                    
                    if letter_data:
                        # 1. Generate PDF
                        # We try to get recipient info, fallback to "Unknown" if missing
                        r_name = letter_data.get('recipient_name') or "Recipient"
                        r_street = letter_data.get('recipient_street') or "Street Address"
                        recip_str = f"{r_name}\n{r_street}\n{letter_data.get('recipient_city','')}, {letter_data.get('recipient_state','')} {letter_data.get('recipient_zip','')}"
                        
                        pdf_bytes = letter_format.create_pdf(
                            body_text=letter_data.get("body_text", ""),
                            recipient_info=recip_str,
                            sender_info="VerbaPost Sender",
                            is_heirloom=("Heirloom" in letter_data.get("tier", ""))
                        )
                        
                        c_down, c_ship = st.columns(2)
                        with c_down:
                            st.download_button(
                                label="📄 Download PDF",
                                data=pdf_bytes,
                                file_name=f"letter_{selected_id}.pdf",
                                mime="application/pdf",
                                type="primary"
                            )
                        
                        with c_ship:
                            # THE NEW BUTTON LOGIC (Correctly Indented)
                            if st.button("Mark as Sent & Notify User"):
                                # 1. Update DB
                                database.mark_as_sent(selected_id)
                                
                                # 2. Send Email
                                if mailer:
                                    with st.spinner("Sending email..."):
                                        u_email = letter_data.get('user_email')
                                        mailer.send_shipping_confirmation(u_email, letter_data)
                                        st.success("✅ Updated & Notified!")
                                        st.rerun()
                                else:
                                    st.success("✅ Updated (Email skipped)")
                                    st.rerun()
            else:
                st.info("📭 No pending letters.")

    # --- DEBUGGER ---
    with tab_debug:
        st.subheader("📧 Email Diagnostic")
        key = get_resend_key()
        if key:
            st.success(f"API Key Found: `...{key[-4:]}`")
            resend.api_key = key
            
            c1, c2 = st.columns(2)
            default_sender = "onboarding@resend.dev"
            if "email" in st.secrets and "sender_email" in st.secrets["email"]:
                default_sender = st.secrets["email"]["sender_email"]
                
            f_mail = c1.text_input("From", value=default_sender)
            t_mail = c2.text_input("To", value="tjkarat@gmail.com")
            
            if st.button("Send Test"):
                try:
                    r = resend.Emails.send({
                        "from": f_mail, "to": t_mail,
                        "subject": "Debug Test", "html": "<p>It works!</p>"
                    })
                    st.success("Sent!")
                    st.json(r)
                except Exception as e: st.error(f"Error: {e}")
        else:
            st.error("Missing API Key")

    # --- PROMOS ---
    with tab_promos:
        c1, c2 = st.columns([1, 2])
        with c1:
            new_code = st.text_input("New Code")
            if st.button("Create"):
                if promo_engine:
                    s, m = promo_engine.create_code(new_code)
                    if s: st.success("Created!")
                    else: st.error(m)
        with c2:
            if promo_engine:
                try:
                    d = promo_engine.get_all_codes_with_usage()
                    if d: st.dataframe(pd.DataFrame(d), use_container_width=True)
                except: st.warning("No data")