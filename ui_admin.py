import streamlit as st
import pandas as pd
import time
from datetime import datetime

# --- DIRECT IMPORT ---
import database
import secrets_manager

def render_admin_page():
    # --- AUTH CHECK ---
    admin_email = secrets_manager.get_secret("admin.email")
    admin_pass = secrets_manager.get_secret("admin.password")
    
    # Bypass login if already authenticated in session
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
    
    # Top Bar
    c_exit, c_refresh = st.columns([1, 6])
    with c_exit:
        if st.button("⬅️ Exit"):
            st.session_state.app_mode = "splash"
            st.rerun()
    with c_refresh:
        if st.button("🔄 Refresh Data"):
            st.rerun()

    # RESTORED ALL 5 TABS
    tab_health, tab_orders, tab_promos, tab_users, tab_logs = st.tabs([
        "🏥 Health", "📦 Orders", "🎟️ Promos", "👥 Users", "📜 Logs"
    ])

    # --- TAB 1: SYSTEM HEALTH (VALIDATION) ---
    with tab_health:
        st.subheader("🔌 Connection Diagnostics")
        
        # 1. Database Check
        try:
            with database.get_db_session() as db:
                # Use text() for safe execution
                from sqlalchemy import text
                db.execute(text("SELECT 1"))
            db_status = "✅ Online (Read/Write)"
            db_color = "green"
        except Exception as e:
            db_status = f"❌ Error: {str(e)[:100]}..."
            db_color = "red"

        # 2. Key Validation
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

    # --- TAB 2: ORDERS ---
    with tab_orders:
        st.subheader("Order Manager")
        try:
            with database.get_db_session() as db:
                query = db.query(database.LetterDraft).order_by(database.LetterDraft.created_at.desc()).limit(50)
                orders = query.all()
                
                if not orders:
                    st.info("No orders found.")
                else:
                    data = []
                    for o in orders:
                        data.append({
                            "ID": o.id,
                            "Date": o.created_at.strftime("%Y-%m-%d %H:%M"),
                            "User": o.user_email,
                            "Tier": o.tier,
                            "Status": o.status,
                            "Price": f"${o.price:.2f}"
                        })
                    st.dataframe(pd.DataFrame(data), use_container_width=True)
                    
                    # Detail View
                    oid = st.number_input("Inspect Order ID", min_value=0, step=1)
                    if oid:
                        sel = db.query(database.LetterDraft).filter(database.LetterDraft.id == oid).first()
                        if sel:
                            st.json({
                                "content": sel.content,
                                "recipient": sel.recipient_data,
                                "sender": sel.sender_data
                            })
        except Exception as e:
            st.error(f"Error loading orders: {e}")

    # --- TAB 3: PROMO CODES ---
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

    # --- TAB 4: USERS (RESTORED) ---
    with tab_users:
        st.subheader("User Profiles")
        try:
            with database.get_db_session() as db:
                users = db.query(database.UserProfile).limit(50).all()
                if users:
                    u_data = [{
                        "Email": u.email,
                        "Name": u.full_name,
                        "City": u.address_city,
                        "State": u.address_state,
                        "Joined": u.created_at.strftime("%Y-%m-%d")
                    } for u in users]
                    st.dataframe(pd.DataFrame(u_data), use_container_width=True)
                else:
                    st.info("No users found.")
        except Exception as e:
            st.error(f"Error loading users: {e}")

    # --- TAB 5: LOGS (RESTORED) ---
    with tab_logs:
        st.subheader("System Logs")
        try:
            with database.get_db_session() as db:
                logs = db.query(database.AuditEvent).order_by(database.AuditEvent.timestamp.desc()).limit(50).all()
                if logs:
                    l_data = [{
                        "Time": l.timestamp.strftime("%H:%M:%S"),
                        "Event": l.event_type,
                        "User": l.user_email,
                        "Details": l.details
                    } for l in logs]
                    st.dataframe(pd.DataFrame(l_data), use_container_width=True)
                else:
                    st.info("No logs found.")
        except Exception as e:
            st.error(f"Error loading logs: {e}")

# Safety Alias
render_admin = render_admin_page