import streamlit as st
import pandas as pd
import database
import time
import os

# Try importing engines (graceful degradation)
try: import promo_engine
except ImportError: promo_engine = None
try: import audit_engine
except ImportError: audit_engine = None

def check_password():
    """Simple admin auth guard."""
    # In production, use environment variables or database for admin list
    admin_email = st.session_state.get("user_email")
    allowed_admins = ["tjkarat@gmail.com", "admin@verbapost.com"]
    
    if admin_email not in allowed_admins:
        st.error("⛔ Access Denied")
        st.stop()
        
    # Optional: Add secondary password check here if needed

def render_health_dashboard():
    st.markdown("### 🏥 System Health")
    # FIX: Defined exactly 3 columns, matching usage below
    c1, c2, c3 = st.columns(3)
    
    # Database Check
    try:
        with database.get_db_session() as db:
            db.execute("SELECT 1")
        c1.metric("Database", "Online", delta_color="normal")
    except:
        c1.metric("Database", "Offline", delta_color="inverse")
        
    # File System (Write Check)
    try:
        with open("/tmp/health_check.txt", "w") as f:
            f.write("test")
        c2.metric("File System", "Writable", delta_color="normal")
    except:
        c2.metric("File System", "Read-Only", delta_color="inverse")
        
    # API Dependencies
    # (Mock checks for now)
    c3.metric("Stripe/PostGrid", "Configured")

def render_order_manager():
    st.markdown("### 📦 Order Manager")
    
    filter_status = st.selectbox("Filter Status", ["All", "Paid", "Sent", "Draft", "Error"])
    
    if st.button("Refresh Orders"):
        st.rerun()

    try:
        with database.get_db_session() as db:
            query = db.query(database.LetterDraft).order_by(
                database.LetterDraft.created_at.desc()
            ).limit(100)
            
            if filter_status != "All":
                query = query.filter(database.LetterDraft.status == filter_status)
            
            orders = query.all()
            
            if not orders:
                st.info("No orders found matching criteria.")
                return

            # CRITICAL FIX: Convert SQLAlchemy objects to Dicts for DataFrame
            data = []
            for o in orders:
                data.append({
                    "ID": o.id,
                    "Date": o.created_at.strftime("%Y-%m-%d %H:%M"),
                    "User": o.user_email,
                    "Tier": o.tier,
                    "Status": o.status,
                    "Price": f"${o.price:.2f}" if o.price else "$0.00",
                    "Tracking": o.tracking_number
                })
            
            df = pd.DataFrame(data)
            st.dataframe(df, use_container_width=True)
            
    except Exception as e:
        st.error(f"Error loading orders: {e}")

def render_promo_manager():
    st.markdown("### 🎟️ Promo Codes")
    if not promo_engine:
        st.warning("Promo Engine not loaded.")
        return

    c1, c2 = st.columns(2)
    with c1:
        new_code = st.text_input("New Code").upper()
        amount = st.number_input("Discount ($)", 1.0, 100.0, 5.0)
        max_uses = st.number_input("Max Uses", 1, 1000, 100)
        if st.button("Create Code"):
            success, msg = promo_engine.create_code(new_code, amount, max_uses)
            if success: st.success(msg)
            else: st.error(msg)
            
    with c2:
        # List active codes
        # (Implementation requires promo_engine.get_all_codes logic)
        st.info("Existing codes list would appear here.")

def render_audit_logs():
    st.markdown("### 🛡️ Audit Logs")
    if not audit_engine:
        st.warning("Audit Engine not loaded.")
        return
        
    # Placeholder for log viewing
    st.info("Log viewer under construction.")

def render_admin_page():
    check_password()
    
    st.title("⚙️ VerbaPost Admin Console")
    
    tabs = st.tabs(["🏥 Health", "📦 Orders", "🎟️ Promos", "🛡️ Logs"])
    
    with tabs[0]:
        render_health_dashboard()
    with tabs[1]:
        render_order_manager()
    with tabs[2]:
        render_promo_manager()
    with tabs[3]:
        render_audit_logs()

    if st.button("⬅️ Exit Admin"):
        st.session_state.app_mode = "store"
        st.rerun()