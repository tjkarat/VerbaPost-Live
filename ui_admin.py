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
        if st.button("🔄 Refresh System Data"):
            st.rerun()

    # Tabs
    tab_health, tab_orders, tab_promos, tab_logs = st.tabs(["🏥 System Health", "📦 Orders", "🎟️ Promos", "📜 Logs"])

    # --- TAB 1: SYSTEM HEALTH (VALIDATION) ---
    with tab_health:
        st.subheader("🔌 Connection Diagnostics")
        
        # 1. Database Connection Check
        try:
            with database.get_db_session() as db:
                db.execute(database.text("SELECT 1"))
            db_status = "✅ Online (Read/Write)"
            db_color = "green"
        except Exception as e:
            db_status = f"❌ Error: {str(e)[:100]}..."
            db_color = "red"

        # 2. API Key Validation Helper
        def check_key(key_names):
            val = None
            for k in key_names:
                val = secrets_manager.get_secret(k)
                if val: break
            if val:
                masked = f"{val[:4]}...{val[-4:]}" if len(val) > 8 else "****"
                return f"✅ Configured ({masked})"
            return "❌ Missing"

        # Check specific keys
        openai_status = check_key(["openai.api_key", "OPENAI_API_KEY"])
        geo_status = check_key(["geocodio.api_key", "GEOCODIO_API_KEY"])
        email_status = check_key(["email.password", "RESEND_API_KEY"])
        stripe_status = check_key(["stripe.secret_key", "STRIPE_SECRET_KEY"])
        postgrid_status = check_key(["postgrid.api_key", "POSTGRID_API_KEY"])

        # Display Metrics
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("### 🗄️ Database")
            st.markdown(f":{db_color}[**{db_status}**]")
            st.caption("Must be Port 5432 for SQLAlchemy")
            
            st.markdown("### 🗺️ Civic Engine (Geocodio)")
            st.write(f"Key Status: {geo_status}")

            st.markdown("### 🤖 AI Engine (OpenAI)")
            st.write(f"Key Status: {openai_status}")

        with c2:
            st.markdown("### 💳 Payments (Stripe)")
            st.write(f"Key Status: {stripe_status}")

            st.markdown("### 📬 Mailer (PostGrid)")
            st.write(f"Key Status: {postgrid_status}")
            
            st.markdown("### 📧 Email (Resend)")
            st.write(f"Key Status: {email_status}")

    # --- TAB 2: ORDERS ---
    with tab_orders:
        st.subheader("Order Manager")
        try:
            with database.get_db_session() as db:
                # Fetch recent drafts
                query = db.query(database.LetterDraft).order_by(database.LetterDraft.created_at.desc()).limit(50)
                orders = query.all()
                
                if not orders:
                    st.info("No orders found in database.")
                else:
                    data = []
                    for o in orders:
                        data.append({
                            "ID": o.id,
                            "Created": o.created_at.strftime("%Y-%m-%d %H:%M"),
                            "User": o.user_email,
                            "Tier": o.tier,
                            "Status": o.status,
                            "Price": f"${o.price:.2f}"
                        })
                    st.dataframe(pd.DataFrame(data), use_container_width=True)
        except Exception as e:
            st.error(f"Failed to load orders: {e}")

    # --- TAB 3: PROMO CODES ---
    with tab_promos:
        st.subheader("Manage Discounts")
        
        with st.expander("➕ Create New Code"):
            with st.form("new_promo"):
                c_code = st.text_input("Code (e.g. SAVE20)").upper()
                c_val = st.number_input("Discount ($)", min_value=0.0, step=0.5)
                c_max = st.number_input("Max Uses", min_value=1, value=100)
                
                if st.form_submit_button("Create"):
                    if promo_engine:
                        success, msg = promo_engine.create_code(c_code, c_max) # Note: Need to update engine signature if needed
                        # Manually insert for safety if engine fails
                        try:
                            with database.get_db_session() as db:
                                new_p = database.PromoCode(code=c_code, discount_amount=c_val, max_uses=c_max)
                                db.add(new_p)
                                st.success(f"Created {c_code}")
                                time.sleep(1)
                                st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")
                    else:
                        st.error("Promo Engine Missing")

        # List Codes
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
                    st.info("No codes found.")
        except:
            st.warning("Could not load promo codes.")

# Safety Alias
render_admin = render_admin_page