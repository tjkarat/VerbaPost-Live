import streamlit as st
import pandas as pd
import time
import json
import os
from datetime import datetime

# --- DIRECT IMPORT ---
import database
import secrets_manager

# Import Engines for Retry Functionality
try: import mailer
except ImportError: mailer = None
try: import letter_format
except ImportError: letter_format = None
try: import address_standard
except ImportError: address_standard = None

def render_admin_page():
    # --- AUTH CHECK (Production Safe) ---
    # Prioritize Env Vars (GCP), Fallback to Secrets (QA)
    admin_email = os.environ.get("ADMIN_EMAIL") or secrets_manager.get_secret("admin.email")
    admin_pass = os.environ.get("ADMIN_PASSWORD") or secrets_manager.get_secret("admin.password")
    
    if not st.session_state.get("admin_authenticated"):
        st.markdown("## 🛡️ Admin Access")
        with st.form("admin_login"):
            email = st.text_input("Admin Email")
            pwd = st.text_input("Password", type="password")
            if st.form_submit_button("Unlock Console"):
                if not admin_email: 
                    st.error("Admin credentials not configured on server.")
                elif email.strip() == admin_email and pwd.strip() == admin_pass:
                    st.session_state.admin_authenticated = True
                    st.rerun()
                else:
                    st.error("Invalid Credentials")
        return

    # --- ADMIN DASHBOARD ---
    st.title("⚙️ VerbaPost Admin Console")
    
    c_exit, c_refresh = st.columns([1, 6])
    with c_exit:
        if st.button("⬅️ Exit"):
            st.session_state.app_mode = "splash"
            st.rerun()
    with c_refresh:
        if st.button("🔄 Refresh Data"):
            st.rerun()

    tab_health, tab_orders, tab_promos, tab_users, tab_logs = st.tabs([
        "🏥 Health", "📦 Orders", "🎟️ Promos", "👥 Users", "📜 Logs"
    ])

    # --- TAB 1: HEALTH ---
    with tab_health:
        st.subheader("🔌 Connection Diagnostics")
        try:
            with database.get_db_session() as db:
                from sqlalchemy import text
                db.execute(text("SELECT 1"))
            db_status = "✅ Online (Read/Write)"
            db_color = "green"
        except Exception as e:
            db_status = f"❌ Error: {str(e)[:100]}..."
            db_color = "red"

        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"**Database:** :{db_color}[{db_status}]")

    # --- TAB 2: ORDERS (RESTORED REPAIR TOOL) ---
    with tab_orders:
        st.subheader("Order Manager")
        
        # 1. VIEW ORDERS
        try:
            # Use the new clean function from database.py
            orders = database.get_all_orders()
            if orders:
                data = []
                for o in orders:
                    # Handle missing dates safely
                    raw_date = o.get('created_at')
                    date_str = raw_date.strftime("%Y-%m-%d %H:%M") if raw_date else "Unknown"

                    data.append({
                        "ID": o.get('id'),
                        "Date": date_str,
                        "User": o.get('user_email'),
                        "Tier": o.get('tier'),
                        "Status": o.get('status'),
                        "Price": f"${o.get('price', 0):.2f}"
                    })
                st.dataframe(pd.DataFrame(data), use_container_width=True)
                
                st.divider()
                
                # 2. THE RESTORED REPAIR TOOL
                st.markdown("### 🛠️ Repair & Fulfillment")
                oid = st.text_input("Enter Order UUID to Fix/Retry") 
            else:
                st.info("No orders found.")
                oid = None
                
            if oid:
                # We need direct session access for repairs
                with database.get_db_session() as db:
                    # Look in both tables
                    sel = db.query(database.LetterDraft).filter(database.LetterDraft.id == oid).first()
                    if not sel:
                        sel = db.query(database.Letter).filter(database.Letter.id == oid).first()
                        
                    if sel:
                        st.info(f"Editing Order: {sel.status}")
                        
                        c_left, c_right = st.columns([1.5, 1])
                        
                        with c_left:
                            st.markdown("#### 1. Data Repair")
                            current_content = getattr(sel, 'content', '') or ""
                            new_content = st.text_area("Letter Content", current_content, height=200)
                            
                            if st.button("💾 Save Content Changes"):
                                sel.content = new_content
                                db.commit()
                                st.success("Updated!")
                                time.sleep(1)
                                st.rerun()

                        with c_right:
                            st.markdown("#### 2. Force Actions")
                            st.warning("Only use if paid but failed.")
                            
                            if st.button("🚀 Force Send (Retry)"):
                                if not mailer: st.error("Mailer Missing"); st.stop()
                                
                                with st.spinner("Retrying..."):
                                    user_p = database.get_user_profile(sel.user_email)
                                    
                                    to_obj = {
                                        "name": getattr(sel, 'to_name', 'Valued Customer'),
                                        "address_line1": getattr(sel, 'to_street', 'See Profile'),
                                        "city": getattr(sel, 'to_city', ''),
                                        "state": getattr(sel, 'to_state', ''),
                                        "zip": getattr(sel, 'to_zip', '')
                                    }
                                    
                                    if not to_obj['address_line1'] or to_obj['address_line1'] == 'See Profile':
                                        to_obj = {
                                            "name": user_p.get('full_name'),
                                            "address_line1": user_p.get('address_line1'),
                                            "city": user_p.get('address_city'),
                                            "state": user_p.get('address_state'),
                                            "zip": user_p.get('address_zip')
                                        }

                                    from_obj = {
                                        "name": "VerbaPost Center",
                                        "address_line1": "123 Memory Lane",
                                        "city": "Nashville",
                                        "state": "TN",
                                        "zip": "37203"
                                    }

                                    pdf = letter_format.create_pdf(sel.content, to_obj, from_obj, tier=getattr(sel, 'tier', 'Standard'))
                                    res = mailer.send_letter(pdf, to_obj, from_obj)
                                    if res:
                                        st.success("Sent!")
                                        sel.status = "Sent (Admin Retry)"
                                        db.commit()
                                    else:
                                        st.error("Failed.")

        except Exception as e:
            st.error(f"Error loading orders: {e}")

    # --- TAB 3: PROMOS ---
    with tab_promos:
        st.subheader("Manage Discounts")
        with st.expander("➕ Create New Code"):
            with st.form("new_promo"):
                c_code = st.text_input("Code").upper()
                c_val = st.number_input("Discount ($)", min_value=0.0)
                if st.form_submit_button("Create"):
                    if database.create_promo_code(c_code, c_val):
                        st.success(f"Created {c_code}")
                        time.sleep(1); st.rerun()
                    else:
                        st.error("Failed to create promo.")

        promos = database.get_all_promos()
        if promos:
            st.dataframe(pd.DataFrame(promos), use_container_width=True)

    # --- TAB 4: USERS ---
    with tab_users:
        st.subheader("User Profiles")
        users = database.get_all_users()
        if users:
            st.dataframe(pd.DataFrame(users), use_container_width=True)

    # --- TAB 5: LOGS ---
    with tab_logs:
        st.subheader("System Logs")
        logs = database.get_system_logs()
        if logs:
            st.dataframe(pd.DataFrame(logs), use_container_width=True)

# Safety Alias
render_admin = render_admin_page