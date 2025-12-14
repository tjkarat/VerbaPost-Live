import streamlit as st
import pandas as pd
from datetime import datetime
import json

# --- ROBUST IMPORTS ---
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

# FIX: Import secrets_manager since it exists
try:
    import secrets_manager
except ImportError:
    secrets_manager = None

# --- ADMIN AUTHENTICATION ---
def check_admin_auth():
    """
    Simple Admin Authentication Guard.
    """
    if st.session_state.get("admin_authenticated"):
        return True
    
    st.markdown("## 🛡️ Admin Console")
    
    with st.form("admin_login"):
        password = st.text_input("Enter Admin Key", type="password")
        if st.form_submit_button("Access Console"):
            # Check against secrets
            try:
                # FIX: Use secrets_manager if available, else raw secrets
                admin_secret = None
                if secrets_manager:
                    admin_secret = secrets_manager.get_secret("admin.password")
                
                if not admin_secret:
                    # Fallback to direct lookup
                    admin_secret = st.secrets.get("admin", {}).get("password")
                
                if password == admin_secret:
                    st.session_state.admin_authenticated = True
                    st.rerun()
                else:
                    st.error("Invalid Access Key")
            except Exception as e:
                st.error(f"Configuration Error: {e}")
                
    return False

# --- PROMO CODE MANAGER ---
def render_promo_manager():
    st.subheader("🎟️ Promo Code Manager")
    
    # Add New Code
    with st.expander("Create New Code"):
        with st.form("new_promo"):
            c1, c2 = st.columns(2)
            code = c1.text_input("Code (e.g., SAVE20)").upper()
            val = c2.number_input("Discount Value ($)", min_value=0.0, step=0.5)
            max_uses = st.number_input("Max Uses", min_value=1, value=100)
            
            if st.form_submit_button("Create Code"):
                if database and code:
                    try:
                        database.create_promo_code(code, val, max_uses)
                        st.success(f"Created code {code} for ${val} off.")
                    except Exception as e:
                        st.error(f"Error: {e}")

    # View Active Codes
    if database and hasattr(database, "supabase"):
        try:
            res = database.supabase.table("promo_codes").select("*").execute()
            if res.data:
                df = pd.DataFrame(res.data)
                st.dataframe(df)
            else:
                st.info("No active promo codes.")
        except Exception as e:
            st.error(f"Fetch Error: {e}")

# --- ORDER MANAGER ---
def render_order_manager():
    st.subheader("📦 Order Management")
    
    filter_status = st.selectbox("Filter Status", ["Paid", "Draft", "Shipped", "Error"])
    
    if database and hasattr(database, "supabase"):
        try:
            # Fetch recent drafts
            query = database.supabase.table("letter_drafts").select("*").order("created_at", desc=True).limit(50)
            if filter_status:
                query = query.eq("status", filter_status)
            
            response = query.execute()
            df = pd.DataFrame(response.data)
            
            if not df.empty:
                st.dataframe(df)
                
                # Retry Logic
                st.markdown("### 🔧 Actions")
                selected_id = st.selectbox("Select Order ID to Retry/View", df["id"].tolist())
                
                if st.button("Retry Fulfillment (Send to PostGrid)"):
                    order = df[df["id"] == selected_id].iloc[0]
                    # Logic to re-trigger mailer would go here
                    st.warning(f"Retrying order {selected_id} functionality is not fully implemented in this view.")
            else:
                st.info("No orders found matching criteria.")
                
        except Exception as e:
            st.error(f"Database Error: {e}")

# --- USER LOOKUP ---
def render_user_lookup():
    st.subheader("🔍 User Lookup")
    email_search = st.text_input("Search by Email")
    
    if email_search and database and hasattr(database, "supabase"):
        try:
            # Search Profiles
            res = database.supabase.table("user_profiles").select("*").eq("email", email_search).execute()
            if res.data:
                st.success("User Found")
                st.json(res.data[0])
                
                # Show their orders
                st.markdown("#### User Orders")
                orders = database.supabase.table("letter_drafts").select("*").eq("user_email", email_search).execute()
                if orders.data:
                    st.dataframe(pd.DataFrame(orders.data))
                else:
                    st.info("No orders for this user.")
            else:
                st.warning("User not found.")
        except Exception as e:
            st.error(f"Search failed: {e}")

# --- MAIN RENDERER ---
def render_admin_page():
    if not check_admin_auth():
        return

    st.title("⚙️ VerbaPost Operation Center")
    
    # Sidebar Navigation
    admin_tab = st.sidebar.radio("Console Section", [
        "Dashboard", 
        "Orders", 
        "Users", 
        "Promo Codes", 
        "System Logs"
    ])
    
    if admin_tab == "Dashboard":
        st.markdown("### 📊 System Overview")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("System Status", "Online 🟢")
        with c2:
            # Placeholder for real metrics
            st.metric("Pending Orders", "0")
        with c3:
            st.metric("Total Users", "Unknown")
            
        st.info("Select a module from the sidebar to manage specific data.")

    elif admin_tab == "Orders":
        render_order_manager()

    elif admin_tab == "Users":
        render_user_lookup()

    elif admin_tab == "Promo Codes":
        render_promo_manager()

    elif admin_tab == "System Logs":
        st.subheader("📜 Audit Logs")
        if database and hasattr(database, "supabase"):
            try:
                logs = database.supabase.table("audit_events").select("*").order("created_at", desc=True).limit(50).execute()
                if logs.data:
                    st.dataframe(pd.DataFrame(logs.data))
                else:
                    st.info("No logs found.")
            except Exception as e:
                st.error(f"Log Fetch Error: {e}")

    # Logout Button
    st.markdown("---")
    if st.button("🔴 Logout Admin"):
        st.session_state.admin_authenticated = False
        st.rerun()