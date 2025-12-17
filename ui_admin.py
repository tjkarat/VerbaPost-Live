import streamlit as st
import pandas as pd
import time
import json
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
    # --- AUTH CHECK ---
    admin_email = secrets_manager.get_secret("admin.email")
    admin_pass = secrets_manager.get_secret("admin.password")
    
    if not st.session_state.get("admin_authenticated"):
        st.markdown("## 🛡️ Admin Access")
        with st.form("admin_login"):
            email = st.text_input("Admin Email")
            pwd = st.text_input("Password", type="password")
            if st.form_submit_button("Unlock Console"):
                if email == admin_email and pwd == admin_pass:
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

        def check_key(key_names):
            val = None
            for k in key_names:
                val = secrets_manager.get_secret(k)
                if val: break
            if val:
                masked = f"{val[:4]}...{val[-4:]}" if len(val) > 8 else "****"
                return f"✅ Configured ({masked})"
            return "❌ Missing"

        stripe_s = check_key(["stripe.secret_key", "STRIPE_SECRET_KEY"])
        postgrid_s = check_key(["postgrid.api_key", "POSTGRID_API_KEY"])
        openai_s = check_key(["openai.api_key", "OPENAI_API_KEY"])
        geo_s = check_key(["geocodio.api_key", "GEOCODIO_API_KEY"])
        email_s = check_key(["email.password", "RESEND_API_KEY"])

        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"**Database:** :{db_color}[{db_status}]")
            st.markdown(f"**Civic (Geocodio):** {geo_s}")
            st.markdown(f"**AI (OpenAI):** {openai_s}")
        with c2:
            st.markdown(f"**Payments (Stripe):** {stripe_s}")
            st.markdown(f"**Mail (PostGrid):** {postgrid_s}")
            st.markdown(f"**Email (Resend):** {email_s}")

    # --- TAB 2: ORDERS (FIXED) ---
    with tab_orders:
        st.subheader("Order Manager")
        try:
            with database.get_db_session() as db:
                query = db.query(database.LetterDraft).order_by(database.LetterDraft.created_at.desc()).limit(50)
                orders = query.all()
                
                if orders:
                    data = []
                    for o in orders:
                        # FIX: Handle missing dates safely
                        if o.created_at:
                            date_str = o.created_at.strftime("%Y-%m-%d %H:%M")
                        else:
                            date_str = "Unknown Date"

                        data.append({
                            "ID": o.id,
                            "Date": date_str,
                            "User": o.user_email,
                            "Tier": o.tier,
                            "Status": o.status,
                            "Price": f"${o.price:.2f}" if o.price else "$0.00"
                        })
                    st.dataframe(pd.DataFrame(data), use_container_width=True)
                    
                    st.divider()
                    st.markdown("### 🛠️ Repair & Fulfillment")
                    oid = st.number_input("Enter Order ID to Fix/Retry", min_value=0, step=1)
                else:
                    st.info("No orders found.")
                    oid = None
                    
                if oid:
                    sel = db.query(database.LetterDraft).filter(database.LetterDraft.id == oid).first()
                    if sel:
                        st.info(f"Editing Order #{oid} ({sel.status})")
                        
                        json_template = """{
  "name": "John Doe",
  "street": "123 Main St Apt 4B",
  "city": "New York",
  "state": "NY",
  "zip_code": "10001",
  "country": "US"
}"""
                        c_left, c_right = st.columns([1.5, 1])
                        
                        with c_left:
                            st.markdown("#### 1. Data Repair")
                            st.caption("Recipient (To)")
                            # FIX: Handle missing JSON data
                            r_val = json.dumps(sel.recipient_data, indent=2) if hasattr(sel, 'recipient_data') and sel.recipient_data else "{}"
                            new_r = st.text_area("Recipient JSON", r_val, height=200, label_visibility="collapsed")
                            
                            st.caption("Sender (From)")
                            s_val = json.dumps(sel.sender_data, indent=2) if hasattr(sel, 'sender_data') and sel.sender_data else "{}"
                            new_s = st.text_area("Sender JSON", s_val, height=200, label_visibility="collapsed")
                            
                            if st.button("💾 Save Changes", use_container_width=True):
                                try:
                                    sel.recipient_data = json.loads(new_r)
                                    sel.sender_data = json.loads(new_s)
                                    db.commit()
                                    st.success("Data Updated!")
                                    time.sleep(1)
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"JSON Error: {e}")

                        with c_right:
                            st.markdown("#### 📖 Format Guide")
                            st.info("Copy this format if data is missing (NULL).")
                            st.code(json_template, language="json")
                            st.markdown("---")
                            st.markdown("#### 2. Force Send")
                            st.warning("Only use this if PostGrid failed but payment succeeded.")
                            
                            if st.button("🚀 Force Send to PostGrid", type="primary"):
                                if not mailer or not letter_format or not address_standard:
                                    st.error("Engines missing")
                                else:
                                    with st.spinner("Generating & Sending..."):
                                        try:
                                            to_obj = address_standard.StandardAddress.from_dict(sel.recipient_data)
                                            from_obj = address_standard.StandardAddress.from_dict(sel.sender_data)
                                            
                                            pdf_bytes = letter_format.create_pdf(
                                                sel.content, 
                                                to_obj, 
                                                from_obj, 
                                                sel.tier
                                            )
                                            
                                            ref = f"admin_retry_{oid}_{int(time.time())}"
                                            tracking = mailer.send_letter(
                                                pdf_bytes, 
                                                to_obj, 
                                                from_obj, 
                                                ref_id=ref, 
                                                color=True, 
                                                certified=(sel.price > 10)
                                            )
                                            
                                            st.success(f"✅ Sent! Tracking: {tracking}")
                                            sel.status = "Completed (Admin Retry)"
                                            sel.tracking_number = tracking
                                            db.commit()
                                            
                                        except Exception as ex:
                                            st.error(f"Send Failed: {ex}")

                    else:
                        st.warning("Order ID not found.")

        except Exception as e:
            st.error(f"Error loading orders: {e}")

    # --- TAB 3: PROMOS ---
    with tab_promos:
        st.subheader("Manage Discounts")
        with st.expander("➕ Create New Code"):
            with st.form("new_promo"):
                c_code = st.text_input("Code").upper()
                c_val = st.number_input("Discount ($)", min_value=0.0)
                c_max = st.number_input("Max Uses", min_value=1, value=100)
                if st.form_submit_button("Create"):
                    try:
                        with database.get_db_session() as db:
                            new_p = database.PromoCode(code=c_code, discount_amount=c_val, max_uses=c_max)
                            db.add(new_p)
                            st.success(f"Created {c_code}")
                            time.sleep(1)
                            st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")

        try:
            with database.get_db_session() as db:
                codes = db.query(database.PromoCode).all()
                if codes:
                    df = pd.DataFrame([{
                        "Code": c.code, 
                        "Discount": f"${c.discount_amount}", 
                        "Uses": f"{c.current_uses}/{c.max_uses}", 
                        "Active": c.active
                    } for c in codes])
                    st.dataframe(df, use_container_width=True)
                else:
                    st.info("No active codes.")
        except Exception as e:
            st.error(f"Error loading promos: {e}")

    # --- TAB 4: USERS ---
    with tab_users:
        st.subheader("User Profiles")
        try:
            with database.get_db_session() as db:
                users = db.query(database.UserProfile).limit(50).all()
                if users:
                    u_data = []
                    for u in users:
                        joined = u.created_at.strftime("%Y-%m-%d") if u.created_at else "Unknown"
                        u_data.append({
                            "Email": u.email,
                            "Name": u.full_name,
                            "City": u.address_city,
                            "State": u.address_state,
                            "Joined": joined
                        })
                    st.dataframe(pd.DataFrame(u_data), use_container_width=True)
        except Exception as e:
            st.error(f"Error loading users: {e}")

    # --- TAB 5: LOGS ---
    with tab_logs:
        st.subheader("System Logs")
        try:
            with database.get_db_session() as db:
                logs = db.query(database.AuditEvent).order_by(database.AuditEvent.timestamp.desc()).limit(50).all()
                if logs:
                    l_data = []
                    for l in logs:
                        ts = l.timestamp.strftime("%H:%M:%S") if l.timestamp else "--:--"
                        l_data.append({
                            "Time": ts,
                            "Event": l.event_type,
                            "User": l.user_email,
                            "Details": l.details
                        })
                    st.dataframe(pd.DataFrame(l_data), use_container_width=True)
        except Exception as e:
            st.error(f"Error loading logs: {e}")

# Safety Alias
render_admin = render_admin_page