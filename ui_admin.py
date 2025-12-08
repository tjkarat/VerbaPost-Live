import streamlit as st
import pandas as pd
import json
import base64
from datetime import datetime

# --- IMPORTS ---
try: import database
except ImportError: database = None
try: import letter_format
except ImportError: letter_format = None
try: import promo_engine
except ImportError: promo_engine = None
try: import secrets_manager
except ImportError: secrets_manager = None
try: import mailer
except ImportError: mailer = None

def check_password():
    """Returns True if the user is logged in as admin."""
    if st.session_state.get("admin_logged_in"): return True
    
    # Simple password protection for the admin route
    pwd = st.text_input("Admin Password", type="password")
    
    # In production, use a strong environment variable. 
    # Fallback to a simple default for dev.
    correct_pwd = "admin" 
    if secrets_manager:
        fetched = secrets_manager.get_secret("ADMIN_PASSWORD")
        if fetched: correct_pwd = fetched
            
    if st.button("Login"):
        if pwd == correct_pwd:
            st.session_state.admin_logged_in = True
            st.rerun()
        else:
            st.error("Incorrect Password")
    return False

def show_admin():
    st.title("🔐 Admin Console")
    
    if not check_password():
        return

    if st.button("Logout"):
        st.session_state.admin_logged_in = False
        st.session_state.app_mode = "store"
        st.rerun()

    # --- TABS ---
    tab_overview, tab_drafts, tab_manual, tab_promo = st.tabs(["📊 Overview", "📝 Drafts & Fixes", "🖨️ Manual Fulfillment", "🎟️ Promo Codes"])

    # --- TAB 1: OVERVIEW ---
    with tab_overview:
        st.subheader("System Health")
        if database:
            try:
                # Basic Stats
                drafts = database.fetch_all_drafts()
                df = pd.DataFrame(drafts)
                if not df.empty:
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Total Drafts", len(df))
                    c2.metric("Pending Admin", len(df[df['Status'] == 'Pending Admin']))
                    c3.metric("Completed", len(df[df['Status'] == 'Completed']))
                    
                    st.write("Recent Activity")
                    st.dataframe(df.head(10))
                else:
                    st.info("No drafts found in database.")
            except Exception as e:
                st.error(f"DB Error: {e}")
        else:
            st.error("Database module missing.")

    # --- TAB 2: DRAFTS & FIXES ---
    with tab_drafts:
        st.subheader("Manage Orders")
        if database:
            drafts = database.fetch_all_drafts()
            if drafts:
                # Filter for Pending
                pending = [d for d in drafts if d['Status'] in ['Pending Admin', 'Failed/Retry']]
                
                if not pending:
                    st.success("No pending orders requiring attention.")
                
                for row in pending:
                    with st.expander(f"{row['Date']} - {row['Email']} ({row['Tier']})"):
                        c1, c2 = st.columns(2)
                        
                        # Parse JSONs safely
                        try: to_data = json.loads(row['Recipient']) if row['Recipient'] else {}
                        except: to_data = {}
                        try: from_data = json.loads(row['Sender']) if row['Sender'] else {}
                        except: from_data = {}
                        
                        with c1:
                            st.write("Current Recipient Data:")
                            st.json(to_data)
                            
                        with c2:
                            st.write("Fix Address:")
                            with st.form(key=f"fix_form_{row['ID']}"):
                                n_name = st.text_input("Name", to_data.get('name',''))
                                n_str = st.text_input("Street", to_data.get('street','') or to_data.get('address_line1',''))
                                # Standardize on address_line2
                                n_str2 = st.text_input("Apt/Suite", to_data.get('address_line2','') or to_data.get('street2',''))
                                n_city = st.text_input("City", to_data.get('city','') or to_data.get('address_city',''))
                                n_state = st.text_input("State", to_data.get('state','') or to_data.get('address_state',''))
                                n_zip = st.text_input("Zip", to_data.get('zip','') or to_data.get('address_zip',''))
                                
                                if st.form_submit_button("Update & Retry"):
                                    # Update DB
                                    new_to = {
                                        "name": n_name, "street": n_str, "address_line2": n_str2,
                                        "city": n_city, "state": n_state, "zip": n_zip, "country": "US"
                                    }
                                    database.update_draft_data(row['ID'], to_addr=new_to, status="Retry")
                                    st.success("Updated! Run retry logic manually or waiting for job.")
                                    st.rerun()

    # --- TAB 3: MANUAL FULFILLMENT (PDF GENERATION) ---
    with tab_manual:
        st.subheader("🖨️ Print Queue (Heirloom / Santa)")
        st.info("Use this to generate PDFs for orders that need manual printing (Heirloom/Santa).")
        
        if database:
            all_drafts = database.fetch_all_drafts()
            # Filter for Heirloom or Santa that are "Pending Admin"
            manual_queue = [d for d in all_drafts if d['Status'] == 'Pending Admin' and d['Tier'] in ['Heirloom', 'Santa']]
            
            if not manual_queue:
                st.write("Queue empty.")
            
            for row in manual_queue:
                st.markdown(f"**ID {row['ID']}** | {row['Email']} | {row['Tier']}")
                
                if st.button(f"Generate PDF #{row['ID']}", key=f"btn_pdf_{row['ID']}"):
                    try:
                        # 1. Parse JSON safely
                        to_data = json.loads(row['Recipient']) if row['Recipient'] else {}
                        from_data = json.loads(row['Sender']) if row['Sender'] else {}
                        
                        # 2. FIX: Construct Address Block (The New Standard)
                        # This ensures Apt/Suite is included safely
                        lines = [to_data.get('name', '')]
                        lines.append(to_data.get('street', '') or to_data.get('address_line1', ''))
                        
                        # Check both keys for safety
                        line2 = to_data.get('address_line2') or to_data.get('street2')
                        if line2: lines.append(line2)
                        
                        lines.append(f"{to_data.get('city', '')}, {to_data.get('state', '')} {to_data.get('zip', '')}")
                        if to_data.get('country', 'US') != 'US': 
                            lines.append(to_data.get('country'))
                        
                        to_str = "\n".join(filter(None, lines))

                        # 3. Same for Sender
                        f_lines = [from_data.get('name', '')]
                        f_lines.append(from_data.get('street', '') or from_data.get('address_line1', ''))
                        f_line2 = from_data.get('address_line2') or from_data.get('street2')
                        if f_line2: f_lines.append(f_line2)
                        f_lines.append(f"{from_data.get('city', '')}, {from_data.get('state', '')} {from_data.get('zip', '')}")
                        from_str = "\n".join(filter(None, f_lines))
                        
                        # 4. Handle Signature
                        sig_path = None
                        # (Admin PDF generation usually doesn't need the temp file path for sigs unless strictly required, 
                        # but if we stored base64 in DB, we'd need to decode it here. 
                        # For simplicity, we assume Heirloom/Santa uses font signatures or Santa signature.)

                        # 5. Generate PDF
                        if letter_format:
                            pdf_bytes = letter_format.create_pdf(
                                row['Content'], 
                                to_str, 
                                from_str, 
                                is_heirloom=("Heirloom" in row['Tier']),
                                is_santa=("Santa" in row['Tier']),
                                is_santa_sig=("Santa" in row['Tier']) # Pass flag to force Santa sig
                            )
                            
                            if pdf_bytes:
                                b64 = base64.b64encode(pdf_bytes).decode()
                                href = f'<a href="data:application/pdf;base64,{b64}" download="letter_{row["ID"]}.pdf">📥 Download PDF</a>'
                                st.markdown(href, unsafe_allow_html=True)
                                
                                # Mark as Completed
                                if st.button(f"Mark #{row['ID']} Mailed"):
                                    database.update_draft_data(row['ID'], status="Completed")
                                    st.success("Marked as Completed!")
                                    st.rerun()
                            else:
                                st.error("PDF Generation failed (Empty bytes).")
                        else:
                            st.error("Letter Format module missing.")

                    except Exception as e:
                        st.error(f"Admin PDF Error: {e}")

    # --- TAB 4: PROMO CODES ---
    with tab_promo:
        st.subheader("Promo Codes")
        if promo_engine:
            c1, c2 = st.columns(2)
            with c1:
                with st.form("create_promo"):
                    new_code = st.text_input("New Code Name (e.g. SUMMER25)")
                    usage_limit = st.number_input("Max Uses", min_value=1, value=10, step=1)
                    
                    if st.form_submit_button("Create Code"):
                        success, msg = promo_engine.create_code(new_code, usage_limit)
                        if success: st.success(msg)
                        else: st.error(msg)
                        
            with c2:
                st.write("Active Codes & Usage")
                stats = promo_engine.get_all_codes_with_usage()
                if stats: 
                    st.dataframe(stats)
                else:
                    st.info("No active codes.")
        else:
            st.warning("Promo Engine missing.")