import streamlit as st
import pandas as pd
import time
from datetime import datetime

# --- DIRECT IMPORT (No Try/Except to force errors to show) ---
import database
import secrets_manager

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

    tab_health, tab_orders, tab_promos = st.tabs(["🏥 Health", "📦 Orders", "🎟️ Promos"])

    # --- TAB 1: SYSTEM HEALTH ---
    with tab_health:
        st.subheader("System Status")
        
        # 1. Database Check
        db_status = "🔴 Disconnected"
        try:
            if database.get_engine():
                db_status = "🟢 Connected (SQLAlchemy)"
        except Exception as e:
            db_status = f"🔴 Error: {str(e)}"
            
        # 2. Key Checks
        stripe_k = "🟢 Set" if secrets_manager.get_secret("stripe.secret_key") else "🔴 Missing"
        postgrid_k = "🟢 Set" if secrets_manager.get_secret("postgrid.api_key") else "🔴 Missing"
        
        # 3. Feature Keys (NEW)
        openai_k = "🟢 Set" if secrets_manager.get_secret("openai.api_key") else "🔴 Missing"
        geo_k = "🟢 Set" if (secrets_manager.get_secret("geocodio.api_key") or secrets_manager.get_secret("GEOCODIO_API_KEY")) else "🔴 Missing"
        email_k = "🟢 Set" if (secrets_manager.get_secret("email.password") or secrets_manager.get_secret("RESEND_API_KEY")) else "🔴 Missing"
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Database", db_status)
        c1.metric("Stripe Payments", stripe_k)
        
        c2.metric("PostGrid Mail", postgrid_k)
        c2.metric("Geocodio (Civic)", geo_k)
        
        c3.metric("OpenAI (AI)", openai_k)
        c3.metric("Resend (Email)", email_k)

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
                            "Date": o.created_at,
                            "User": o.user_email,
                            "Status": o.status,
                            "Tier": o.tier,
                            "Total": f"${o.price:.2f}"
                        })
                    st.dataframe(pd.DataFrame(data), use_container_width=True)
        except Exception as e:
            st.error(f"Database Error: {e}")

    # --- TAB 3: PROMO CODES ---
    with tab_promos:
        st.subheader("Manage Promo Codes")
        with st.expander("➕ Create New Code"):
            with st.form("new_promo"):
                nc = st.text_input("Code (e.g. SAVE50)").upper()
                na = st.number_input("Discount Amount ($)", min_value=0.0)
                if st.form_submit_button("Create Promo"):
                    try:
                        with database.get_db_session() as db:
                            new_p = database.PromoCode(code=nc, discount_amount=na, max_uses=100)
                            db.add(new_p)
                            st.success(f"Created code {nc}")
                            time.sleep(1)
                            st.rerun()
                    except Exception as e:
                        st.error(f"Failed: {e}")

        try:
            with database.get_db_session() as db:
                promos = db.query(database.PromoCode).all()
                if promos:
                    p_data = [{"Code": p.code, "Discount": p.discount_amount, "Uses": p.current_uses, "Active": p.active} for p in promos]
                    st.dataframe(p_data)
        except Exception as e:
            st.error(f"DB Error: {e}")

# Safety Alias
render_admin = render_admin_page