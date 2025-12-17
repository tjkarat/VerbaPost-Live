import streamlit as st
import pandas as pd
import time
import json
import os
from datetime import datetime

# --- DIRECT IMPORT ---
import database
import secrets_manager

# Import Engines
try: import mailer
except ImportError: mailer = None
try: import letter_format
except ImportError: letter_format = None
try: import address_standard
except ImportError: address_standard = None
try: import ai_engine  # Added for Ghost Call tracking
except ImportError: ai_engine = None

def render_admin_page():
    # --- AUTH CHECK ---
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

    # --- DASHBOARD ---
    st.title("⚙️ VerbaPost Admin Console")
    
    c_exit, c_refresh = st.columns([1, 6])
    with c_exit:
        if st.button("⬅️ Exit"):
            st.session_state.app_mode = "splash"
            st.rerun()
    with c_refresh:
        if st.button("🔄 Refresh Data"):
            st.rerun()

    # ADDED "📞 Ghost Calls" TAB
    tab_health, tab_orders, tab_ghosts, tab_promos, tab_users, tab_logs = st.tabs([
        "🏥 Health", "📦 Orders", "📞 Ghost Calls", "🎟️ Promos", "👥 Users", "📜 Logs"
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
        st.markdown(f"**Database:** :{db_color}[{db_status}]")

    # --- TAB 2: ORDERS ---
    with tab_orders:
        st.subheader("Order Manager")
        try:
            orders = database.get_all_orders()
            if orders:
                data = []
                for o in orders:
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
                st.markdown("### 🛠️ Repair & Fulfillment")
                oid = st.text_input("Enter Order UUID to Fix/Retry") 
                
                if oid:
                    with database.get_db_session() as db:
                        sel = db.query(database.LetterDraft).filter(database.LetterDraft.id == oid).first()
                        if not sel:
                            sel = db.query(database.Letter).filter(database.Letter.id == oid).first()
                            
                        if sel:
                            st.info(f"Editing: {sel.status}")
                            if st.button("🚀 Force Send (Retry)"):
                                if not mailer: st.error("Mailer Missing")
                                else:
                                    with st.spinner("Retrying..."):
                                        # Minimal Retry Logic
                                        user_p = database.get_user_profile(sel.user_email)
                                        to_obj = {
                                            "name": getattr(sel, 'to_name', user_p.get('full_name')),
                                            "address_line1": getattr(sel, 'to_street', user_p.get('address_line1')),
                                            "city": getattr(sel, 'to_city', user_p.get('address_city')),
                                            "state": getattr(sel, 'to_state', user_p.get('address_state')),
                                            "zip": getattr(sel, 'to_zip', user_p.get('address_zip'))
                                        }
                                        from_obj = {"name": "VerbaPost", "address_line1": "123 Memory Lane", "city": "Nashville", "state": "TN", "zip": "37203"}
                                        pdf = letter_format.create_pdf(sel.content, to_obj, from_obj, tier=getattr(sel, 'tier', 'Standard'))
                                        if mailer.send_letter(pdf, to_obj, from_obj):
                                            st.success("Sent!")
                                            sel.status = "Sent (Admin Retry)"
                                            db.commit()
                                        else: st.error("Failed.")
            else:
                st.info("No orders found.")
        except Exception as e:
            st.error(f"Error: {e}")

    # --- TAB 3: GHOST CALLS (NEW) ---
    with tab_ghosts:
        st.subheader("👻 Unclaimed Heirloom Calls")
        st.info("These are phone calls to your Twilio number that did NOT match any user's 'Parent Phone'.")
        
        if not ai_engine:
            st.error("AI Engine missing (Twilio connection required).")
        else:
            with st.spinner("Fetching logs from Twilio & Database..."):
                # 1. Get Twilio Logs
                calls = ai_engine.get_recent_call_logs(limit=20)
                
                # 2. Get Known User Phones
                users = database.get_all_users()
                known_numbers = set()
                for u in users:
                    p = u.get('parent_phone')
                    if p:
                        # Normalize: Remove spaces, dashes, parens
                        clean = "".join(filter(lambda x: x.isdigit() or x == '+', str(p)))
                        known_numbers.add(clean)
                        # Also add version without +1 for safety
                        if clean.startswith("+1"): known_numbers.add(clean[2:])
                
                # 3. Compare
                ghosts = []
                for c in calls:
                    c_from = str(c['from'])
                    # Strict Check
                    is_known = False
                    for k in known_numbers:
                        if k in c_from: # Loose matching (if known is substring of caller ID)
                            is_known = True
                            break
                    
                    if not is_known:
                        ghosts.append({
                            "Caller ID": c_from,
                            "Time": c['date'].strftime("%m/%d %H:%M") if c['date'] else "?",
                            "Duration": f"{c['duration']}s",
                            "Status": c['status'],
                            "Action": "UNCLAIMED"
                        })
                
                if ghosts:
                    st.dataframe(pd.DataFrame(ghosts), use_container_width=True)
                    st.warning(f"⚠️ Found {len(ghosts)} unclaimed calls. A user might have entered their parent's number incorrectly.")
                else:
                    st.success("✅ No ghost calls found. All recent calls match a user account.")

    # --- TAB 4: PROMOS ---
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
                    else: st.error("Failed.")
        promos = database.get_all_promos()
        if promos: st.dataframe(pd.DataFrame(promos), use_container_width=True)

    # --- TAB 5: USERS ---
    with tab_users:
        st.subheader("User Profiles")
        users = database.get_all_users()
        if users:
            # Mask emails slightly for privacy in screenshot
            safe_users = []
            for u in users:
                safe_users.append({
                    "Name": u.get("full_name"),
                    "Email": u.get("email"),
                    "Parent Phone": u.get("parent_phone", "--"),
                    "Credits": u.get("credits_remaining")
                })
            st.dataframe(pd.DataFrame(safe_users), use_container_width=True)

    # --- TAB 6: LOGS ---
    with tab_logs:
        st.subheader("System Logs")
        logs = database.get_system_logs()
        if logs: st.dataframe(pd.DataFrame(logs), use_container_width=True)

# Safety Alias
render_admin = render_admin_page