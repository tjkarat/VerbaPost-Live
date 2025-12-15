import streamlit as st
import pandas as pd
from datetime import datetime
import json
import base64
import os

# --- ROBUST IMPORTS ---
try: import database
except ImportError: database = None
try: import payment_engine
except ImportError: payment_engine = None
try: import mailer
except ImportError: mailer = None
try: import secrets_manager
except ImportError: secrets_manager = None
try: import ai_engine
except ImportError: ai_engine = None
try: import letter_format
except ImportError: letter_format = None
try: import promo_engine
except ImportError: promo_engine = None

# --- ADMIN AUTHENTICATION ---
def check_admin_auth():
    """Admin Guard. Checks session state or prompts for key."""
    user_email = st.session_state.get("user_email", "")
    authorized_emails = ["admin@verbapost.com", "tjkarat@gmail.com"]
    if st.session_state.get("authenticated") and user_email in authorized_emails:
        return True
        
    if st.session_state.get("admin_authenticated"):
        return True
    
    st.markdown("## 🛡️ Admin Console")
    with st.form("admin_login"):
        password = st.text_input("Enter Admin Key", type="password")
        if st.form_submit_button("Access Console"):
            try:
                admin_secret = None
                if secrets_manager:
                    admin_secret = secrets_manager.get_secret("admin.password")
                if not admin_secret:
                    admin_secret = st.secrets.get("admin", {}).get("password", "admin123")
                if password == admin_secret:
                    st.session_state.admin_authenticated = True
                    st.rerun()
                else:
                    st.error("Invalid Access Key")
            except Exception as e:
                st.error(f"Configuration Error: {e}")
    return False

# --- HEALTH CHECKS ---
def render_health_dashboard():
    st.subheader("❤️ System Health")
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Database", "Online 🟢" if database and hasattr(database, 'get_engine') else "Offline 🔴")
    with col2:
        st.metric("OpenAI", "Ready 🟢" if st.secrets.get("openai", {}).get("api_key") else "Missing Key 🟡")
    with col3:
        st.metric("PostGrid", "Configured 🟢" if st.secrets.get("postgrid", {}).get("api_key") else "Missing Key 🟡")
    with c4:
        st.metric("Email", "Configured 🟢" if st.secrets.get("resend", {}).get("api_key") else "Missing Key 🟡")
    with c5:
        st.metric("Stripe", "Configured 🟢" if st.secrets.get("stripe", {}).get("secret_key") else "Missing Key 🟡")

# --- PROMO CODE MANAGER ---
def render_promo_manager():
    st.subheader("🎟️ Promo Code Manager")
    with st.expander("➕ Create New Code", expanded=False):
        with st.form("new_promo"):
            c1, c2 = st.columns(2)
            code = c1.text_input("Code (e.g., WELCOME10)").upper()
            max_uses = c2.number_input("Max Uses", min_value=1, value=100)
            if st.form_submit_button("Create Code"):
                if promo_engine:
                    success, msg = promo_engine.create_code(code, max_uses)
                    if success: st.success(msg); st.rerun()
                    else: st.error(msg)
                else: st.error("Promo Engine Missing")
    if promo_engine:
        promos = promo_engine.get_all_codes_with_usage()
        if promos: st.dataframe(pd.DataFrame(promos), use_container_width=True)
        else: st.info("No active promo codes.")

# --- ORDER MANAGER ---
def render_order_manager():
    st.subheader("📦 Order Management")
    if not database: st.error("Database not available"); return
    
    try:
        # FIX 5: Convert ORM objects to dicts INSIDE the session to prevent DetachedInstanceError
        orders_data = []
        with database.get_db_session() as db:
            drafts = db.query(database.LetterDraft).order_by(database.LetterDraft.created_at.desc()).all()
            for d in drafts:
                orders_data.append({
                    "ID": d.id,
                    "Date": d.created_at.strftime("%Y-%m-%d %H:%M"),
                    "Email": d.user_email,
                    "Tier": d.tier,
                    "Status": d.status,
                    "Price": d.price,
                    "Transcription": d.transcription
                })
        
        if not orders_data:
            st.info("No orders found.")
            return
        
        df = pd.DataFrame(orders_data)
        status_filter = st.selectbox("Filter by Status", ["All"] + list(df['Status'].unique()))
        if status_filter != "All": df = df[df['Status'] == status_filter]
        
        st.dataframe(df[["ID", "Date", "Email", "Tier", "Status", "Price"]], use_container_width=True, hide_index=True)
        st.divider()
        st.markdown("### 🔧 Actions")
        c1, c2 = st.columns([1, 2])
        with c1: target_id = st.text_input("Draft ID")
        with c2: 
            st.write("")
            if st.button("🗑️ Delete Draft", type="primary"):
                if target_id and database.delete_draft(target_id): st.success(f"Deleted {target_id}"); st.rerun()
            if st.button("✅ Mark Paid (Force)"):
                if target_id and database.update_draft_data(target_id, status="PAID"): st.success("Updated"); st.rerun()
                
    except Exception as e:
        st.error(f"Error displaying orders: {e}")

# --- MAIN RENDERER ---
def render_admin_page():
    if not check_admin_auth(): return
    st.title("⚙️ VerbaPost Operations")
    
    # NAVIGATION VIA TABS (Fixes sidebar issue)
    tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "📦 Orders", "🎟️ Promos"])
    
    with tab1:
        render_health_dashboard()
        st.divider()
        if st.checkbox("Show System Logs"):
            if database:
                try:
                    with database.get_db_session() as db:
                        res = db.execute("SELECT * FROM audit_events ORDER BY created_at DESC LIMIT 20").fetchall()
                        st.dataframe(pd.DataFrame(res))
                except: st.caption("No logs available")
        
    with tab2:
        render_order_manager()

    with tab3:
        render_promo_manager()

    st.markdown("---")
    if st.button("🔴 Close Admin Console", use_container_width=True):
        st.session_state.app_mode = "store"
        st.rerun()