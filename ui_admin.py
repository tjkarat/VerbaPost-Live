import streamlit as st
import pandas as pd
import resend

# --- SAFETY IMPORTS ---
# These prevent the app from crashing if a specific module is missing or broken
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
    """Helper to find the API Key in either [resend] or [email] sections"""
    try:
        if "resend" in st.secrets:
            return st.secrets["resend"]["api_key"]
        elif "email" in st.secrets:
            return st.secrets["email"]["password"]
    except:
        return None
    return None

def show_admin():
    st.title("🔐 Admin Console")
    
    # --- DIAGNOSTICS ROW ---
    # Quick status check of all system components
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
                # 1. Show Data Table
                df = pd.DataFrame(letters)
                # Safe Column Selection (Handling potential missing columns in old data)
                cols = ["created_at", "user_email", "tier", "status", "price"]
                valid_cols = [c for c in cols if c in df.columns]
                st.dataframe(df[valid_cols], use_container_width=True)
                
                st.write("---")
                
                # 2. Print & Ship Manager
                st.subheader("🖨️ Print & Ship Manager")
                
                # Create readable labels for dropdown: "Date - Email (Tier)"
                letter_options = {
                    row['id']: f"{row.get('created_at', '?')} - {row.get('user_email', 'Unknown')} ({row.get('tier', '?')})" 
                    for row in letters
                }
                
                selected_id = st.selectbox("Select Letter to Process", list(letter_options.keys()), format_func=lambda x: letter_options[x])
                
                if selected_id and letter_format:
                    # Get the specific letter object
                    letter_data = next((item for item in letters if item["id"] == selected_id), None)
                    
                    if letter_data:
                        # A. Format Recipient String for PDF
                        r_name = letter_data.get('recipient_name') or "Recipient"
                        r_street = letter_data.get('recipient_street') or "Street Address"
                        r_city = letter_data.get('recipient_city') or ""
                        r_state = letter_data.get('recipient_state') or ""
                        r_zip = letter_data.get('recipient_zip') or ""
                        
                        recip_str = f"{r_name}\n{r_street}\n{r_city}, {r_state} {r_zip}"
                        
                        # B. Generate PDF Bytes
                        pdf_bytes = letter_format.create_pdf(
                            body_text=letter_data.get("body_text", ""),
                            recipient_info=recip_str,
                            sender_info="VerbaPost Sender",
                            is_heirloom=("Heirloom" in letter_data.get("tier", ""))
                        )
                        
                        # C. Action Buttons
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
                            if st.button("Mark as Sent & Notify User"):
                                # 1. Update Database
                                database.mark_as_sent(selected_id)
                                
                                # 2. Send Email Notification
                                if mailer:
                                    u_email = letter_data.get('user_email')
                                    with st.spinner(f"Emailing {u_email}..."):
                                        # Returns (success_bool, message_str)
                                        success, msg = mailer.send_shipping_confirmation(u_email, letter_data)
                                        
                                        if success:
                                            st.success("✅ Status Updated & Email Sent!")
                                            st.caption(f"Server ID: {msg}")
                                            st.rerun()
                                        else:
                                            st.warning("⚠️ Status Updated, but Email Failed.")
                                            st.error(f"Email Error: {msg}")
                                else:
                                    st.success("✅ Status Updated (Mailer Module Missing)")
                                    st.rerun()
            else:
                st.info("📭 No pending letters found.")
        else:
            st.error("Database connection missing.")

    # --- TAB 2: MAIL DEBUGGER ---
    with tab_debug_mail:
        st.subheader("📧 Email System Diagnostic")
        
        # 1. Find Key using helper
        api_key = get_resend_key()
        
        if api_key:
            st.success(f"✅ API Key Found! (Ends in `...{api_key[-4:]}`)")
            resend.api_key = api_key
            
            # 2. Test Form
            c1, c2 = st.columns(2)
            # Try to get sender from secrets, or fallback
            default_sender = "onboarding@resend.dev"
            if "email" in st.secrets and "sender_email" in st.secrets["email"]:
                default_sender = st.secrets["email"]["sender_email"]
                
            from_email = c1.text_input("From Address", value=default_sender)
            to_email = c2.text_input("To Address", value="tjkarat@gmail.com")
            
            if st.button("🚀 Send Test Email", type="primary"):
                try:
                    r = resend.Emails.send({
                        "from": from_email,
                        "to": to_email,
                        "subject": "🔔 VerbaPost Connection Test",
                        "html": "<h1>Connection Successful!</h1><p>Your API Key is working correctly.</p>"
                    })
                    st.success("✅ Email Sent Successfully!")
                    with st.expander("View Server Response"):
                        st.json(r)
                except Exception as e:
                    st.error("❌ Sending Failed")
                    st.error(f"Error Details: {e}")
        else:
            st.error("❌ API Key Missing. Checked [resend] and [email] sections.")
            st.info("Please ensure your secrets.toml has [email] password defined.")

    # --- TAB 3: PROMOS ---
    with tab_promos:
        c1, c2 = st.columns([1, 2])
        
        with c1:
            st.subheader("Create Code")
            new_code = st.text_input("New Code (e.g. VIP100)")
            if st.button("Create Code"):
                if promo_engine:
                    success, msg = promo_engine.create_code(new_code)
                    if success: st.success(f"Created {new_code}!")
                    else: st.error(msg)
                    st.rerun()
                else:
                    st.error("Promo Engine missing")
        
        with c2:
            st.subheader("Active Codes")
            if promo_engine:
                try:
                    data = promo_engine.get_all_codes_with_usage()
                    if data:
                        st.dataframe(pd.DataFrame(data), use_container_width=True)
                    else:
                        st.info("No codes found.")
                except Exception as e:
                    st.warning(f"Could not load logs. Error: {e}")