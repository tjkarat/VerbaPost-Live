import streamlit as st
import pandas as pd
from datetime import datetime
import json
import base64
import os

# --- ROBUST IMPORTS ---
# We use try/except to prevent the entire admin console from crashing
try:
    import database
except ImportError:
    database = None

try:
    import payment_engine
except ImportError:
    payment_engine = None

try:
    import mailer
except ImportError:
    mailer = None

try:
    import secrets_manager
except ImportError:
    secrets_manager = None

try:
    import ai_engine
except ImportError:
    ai_engine = None

try:
    import letter_format
except ImportError:
    letter_format = None
    
try:
    import promo_engine
except ImportError:
    promo_engine = None

# --- ADMIN AUTHENTICATION ---
def check_admin_auth():
    """
    Admin Guard. Checks session state or prompts for key.
    """
    # 1. Check if already authenticated via main.py login
    user_email = st.session_state.get("user_email", "")
    # Add your email here to bypass the secondary password check
    authorized_emails = ["admin@verbapost.com", "tjkarat@gmail.com"]
    
    if st.session_state.get("authenticated") and user_email in authorized_emails:
        return True
        
    # 2. Fallback: Secondary Password Check (if not logged in as authorized user)
    if st.session_state.get("admin_authenticated"):
        return True
    
    st.markdown("## 🛡️ Admin Console")
    
    with st.form("admin_login"):
        password = st.text_input("Enter Admin Key", type="password")
        if st.form_submit_button("Access Console"):
            try:
                # Check Secrets
                admin_secret = None
                if secrets_manager:
                    admin_secret = secrets_manager.get_secret("admin.password")
                
                if not admin_secret:
                    # Fallback
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
    
    # 1. Database Check
    with col1:
        try:
            if database and hasattr(database, 'get_engine'):
                st.metric("Database", "Online 🟢")
            else:
                st.metric("Database", "Offline 🔴")
        except:
            st.metric("Database", "Error 🔴")

    # 2. OpenAI Check
    with col2:
        try:
            key = st.secrets.get("openai", {}).get("api_key")
            st.metric("OpenAI", "Ready 🟢" if key else "Missing Key 🟡")
        except:
            st.metric("OpenAI", "Error 🔴")

    # 3. PostGrid Check
    with col3:
        try:
            key = st.secrets.get("postgrid", {}).get("api_key")
            st.metric("PostGrid", "Configured 🟢" if key else "Missing Key 🟡")
        except:
            st.metric("PostGrid", "Error 🔴")

    # 4. Email Check
    with col4:
        try:
            key = st.secrets.get("resend", {}).get("api_key") or st.secrets.get("email", {}).get("password")
            st.metric("Email", "Configured 🟢" if key else "Missing Key 🟡")
        except:
            st.metric("Email", "Error 🔴")

    # 5. Stripe Check
    with col5:
        try:
            key = st.secrets.get("stripe", {}).get("secret_key")
            st.metric("Stripe", "Configured 🟢" if key else "Missing Key 🟡")
        except:
            st.metric("Stripe", "Error 🔴")

# --- PROMO CODE MANAGER ---
def render_promo_manager():
    st.subheader("🎟️ Promo Code Manager")
    
    # Create New Code
    with st.expander("➕ Create New Code", expanded=False):
        with st.form("new_promo"):
            c1, c2 = st.columns(2)
            code = c1.text_input("Code (e.g., WELCOME10)").upper()
            max_uses = c2.number_input("Max Uses", min_value=1, value=100)
            
            if st.form_submit_button("Create Code"):
                if promo_engine:
                    success, msg = promo_engine.create_code(code, max_uses)
                    if success:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
                else:
                    st.error("Promo Engine not loaded")

    # View Active Codes
    if promo_engine:
        promos = promo_engine.get_all_codes_with_usage()
        if promos:
            st.dataframe(pd.DataFrame(promos), use_container_width=True)
        else:
            st.info("No active promo codes.")
    else:
        st.warning("Promo Engine Missing")

# --- ORDER MANAGER ---
def render_order_manager():
    st.subheader("📦 Order Management")
    
    if not database:
        st.error("Database not available")
        return
        
    try:
        # Fetch orders from database
        orders = database.fetch_all_drafts()
        
        if not orders:
            st.info("No orders found.")
            return
        
        # Convert to DataFrame
        df = pd.DataFrame(orders)
        
        # Filter Options
        status_filter = st.selectbox("Filter by Status", ["All"] + list(df['Status'].unique()))
        if status_filter != "All":
            df = df[df['Status'] == status_filter]
        
        st.dataframe(
            df[["ID", "Date", "Email", "Tier", "Status", "Price"]], 
            use_container_width=True,
            hide_index=True
        )
        
        st.divider()
        st.markdown("### 🔧 Actions")
        
        c1, c2 = st.columns([1, 2])
        with c1:
            target_id = st.text_input("Draft ID")
        
        with c2:
            st.write("") # Spacing
            if st.button("🗑️ Delete Draft", type="primary"):
                if target_id and database.delete_draft(target_id):
                    st.success(f"Deleted Draft {target_id}")
                    st.rerun()
                else:
                    st.error("Failed to delete.")
                    
            if st.button("✅ Mark Paid (Force)"):
                if target_id and database.update_draft_data(target_id, status="PAID"):
                    st.success(f"Updated Draft {target_id}")
                    st.rerun()
            
    except Exception as e:
        st.error(f"Error displaying orders: {e}")

# --- MAIN RENDERER ---
def render_admin_page():
    if not check_admin_auth():
        return

    st.title("⚙️ VerbaPost Operations")
    
    # --- MOVED NAVIGATION TO TABS (Fixes Sidebar Issue) ---
    tab1, tab2, tab3 = st.tabs(["📊 Dashboard", "📦 Orders", "🎟️ Promos"])
    
    with tab1:
        render_health_dashboard()
        st.divider()
        # Log Viewer in Dashboard Tab
        if st.checkbox("Show System Logs"):
            if database:
                try:
                    with database.get_db_session() as db:
                        res = db.execute("SELECT * FROM audit_events ORDER BY created_at DESC LIMIT 20").fetchall()
                        st.dataframe(pd.DataFrame(res))
                except:
                    st.caption("No logs available")
        
    with tab2:
        render_order_manager()

    with tab3:
        render_promo_manager()

    # Logout Button (Bottom of page)
    st.markdown("---")
    if st.button("🔴 Close Admin Console", use_container_width=True):
        st.session_state.app_mode = "store"
        st.rerun()