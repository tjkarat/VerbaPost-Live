import streamlit as st
import pandas as pd
from datetime import datetime
import json
import requests

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

try:
    import secrets_manager
except ImportError:
    secrets_manager = None

try:
    import ai_engine
except ImportError:
    ai_engine = None

# --- ADMIN AUTHENTICATION ---
def check_admin_auth():
    """
    Admin Guard. Checks session state or prompts for key.
    """
    if st.session_state.get("admin_authenticated"):
        return True
    
    st.markdown("## 🛡️ Admin Console")
    
    with st.form("admin_login"):
        password = st.text_input("Enter Admin Key", type="password")
        if st.form_submit_button("Access Console"):
            try:
                # 1. Check Secrets Manager
                admin_secret = None
                if secrets_manager:
                    admin_secret = secrets_manager.get_secret("admin.password")
                
                # 2. Fallback to raw secrets
                if not admin_secret:
                    admin_secret = st.secrets.get("admin", {}).get("password")
                
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
            if database and hasattr(database, "supabase"):
                # Simple ping query
                database.supabase.table("promo_codes").select("count", count="exact").limit(1).execute()
                st.metric("Database", "Online 🟢")
            else:
                st.metric("Database", "Offline 🔴")
        except:
            st.metric("Database", "Error 🔴")

    # 2. OpenAI Check
    with col2:
        try:
            if ai_engine and secrets_manager:
                key = secrets_manager.get_secret("openai.api_key")
                st.metric("OpenAI", "Ready 🟢" if key else "Missing Key 🟡")
            else:
                st.metric("OpenAI", "Offline 🔴")
        except:
            st.metric("OpenAI", "Error 🔴")

    # 3. PostGrid Check
    with col3:
        try:
            if mailer:
                # We can't easily ping API without spending money, so check config
                key = secrets_manager.get_secret("postgrid.api_key")
                st.metric("PostGrid", "Configured 🟢" if key else "Missing Key 🟡")
            else:
                st.metric("PostGrid", "Offline 🔴")
        except:
            st.metric("PostGrid", "Error 🔴")

    # 4. Email (Resend) Check
    with col4:
        try:
            key = secrets_manager.get_secret("resend.api_key") or secrets_manager.get_secret("email.password")
            st.metric("Email", "Configured 🟢" if key else "Missing Key 🟡")
        except:
            st.metric("Email", "Error 🔴")

    # 5. Geocodio Check
    with col5:
        try:
            key = secrets_manager.get_secret("geocodio.api_key")
            st.metric("Geocodio", "Configured 🟢" if key else "Missing Key 🟡")
        except:
            st.metric("Geocodio", "Error 🔴")

# --- PROMO CODE MANAGER ---
def render_promo_manager():
    st.subheader("🎟️ Promo Code Manager")
    
    # View Active Codes
    if database and hasattr(database, "supabase"):
        try:
            res = database.supabase.table("promo_codes").select("*").execute()
            if res.data:
                df = pd.DataFrame(res.data)
                st.dataframe(df, use_container_width=True)
            else:
                st.info("No active promo codes.")
        except Exception as e:
            st.error(f"Fetch Error: {e}")

    # Create New Code
    with st.expander("➕ Create New Code"):
        with st.form("new_promo"):
            c1, c2, c3 = st.columns(3)
            code = c1.text_input("Code (e.g., WELCOME10)").upper()
            val = c2.number_input("Discount Value ($)", min_value=0.0, step=0.5)
            max_uses = c3.number_input("Max Uses", min_value=1, value=100)
            
            if st.form_submit_button("Create Code"):
                if database and code:
                    try:
                        # Assuming create_promo_code exists in database.py, or direct insert
                        data = {"code": code, "value": val, "max_uses": max_uses, "used_count": 0}
                        database.supabase.table("promo_codes").insert(data).execute()
                        st.success(f"Created code {code} for ${val} off.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")

# --- ORDER MANAGER (Fix & Resubmit) ---
def render_order_manager():
    st.subheader("📦 Order Management")
    
    filter_status = st.selectbox("Filter Status", ["All", "Paid", "Pending Payment", "Shipped", "Error"], index=0)
    
    if database and hasattr(database, "supabase"):
        try:
            # Build Query
            query = database.supabase.table("letter_drafts").select("*").order("created_at", desc=True).limit(50)
            if filter_status != "All":
                query = query.eq("status", filter_status)
            
            response = query.execute()
            df = pd.DataFrame(response.data)
            
            if not df.empty:
                # Show key columns first
                display_cols = ["id", "created_at", "status", "user_email", "tracking_number", "tier"]
                # Filter columns that exist in dataframe
                valid_cols = [c for c in display_cols if c in df.columns]
                
                st.dataframe(df[valid_cols], use_container_width=True)
                
                # --- ACTION PANEL ---
                st.divider()
                st.markdown("### 🔧 Order Actions")
                
                col_sel, col_act = st.columns([2, 1])
                with col_sel:
                    selected_id = st.selectbox("Select Order ID to Manage", df["id"].tolist())
                
                # Fetch full details for selected order
                order = df[df["id"] == selected_id].iloc[0]
                
                with st.expander("View Full Order Details"):
                    st.json(order.to_dict())

                # Actions
                c1, c2, c3 = st.columns(3)
                
                # Action 1: Resubmit to PostGrid
                with c1:
                    if st.button("🚀 Resubmit to PostGrid"):
                        if mailer:
                            # Re-construct addresses
                            to_addr = order.get("to_address")
                            from_addr = order.get("from_address")
                            # We need PDF bytes. Ideally stored or regenerated.
                            # For safety, we warn if PDF is missing
                            st.warning("Regenerating PDF feature required for full retry.")
                            # Placeholder for actual logic call
                            st.info("Logic to call mailer.send_letter() goes here.")
                        else:
                            st.error("Mailer module missing.")

                # Action 2: Mark as Shipped/Done
                with c2:
                    if st.button("✅ Mark as Shipped"):
                        database.supabase.table("letter_drafts").update({"status": "Shipped"}).eq("id", selected_id).execute()
                        st.success("Status updated!")
                        st.rerun()

                # Action 3: Print / View PDF
                with c3:
                    if st.button("📄 View PDF"):
                        # If you stored base64 or url, display it
                        st.info("PDF view not stored in DB currently.")

            else:
                st.info("No orders found matching criteria.")
                
        except Exception as e:
            st.error(f"Database Error: {e}")

# --- PRIVACY & CLEANUP ---
def render_privacy_tools():
    st.subheader("🗑️ Data Privacy & Cleanup")
    st.warning("These actions are destructive. Proceed with caution.")
    
    if st.button("RUN PRIVACY WIPE (Delete Letter Contents)", type="primary"):
        confirmation = st.checkbox("I confirm I want to delete user letter bodies.")
        if confirmation:
            if database:
                try:
                    # Call Stored Procedure 'wipe_old_drafts'
                    database.supabase.rpc("wipe_old_drafts").execute()
                    st.success("Privacy wipe completed. Content columns cleared.")
                except Exception as e:
                    st.error(f"Procedure Failed: {e}")
            else:
                st.error("Database unavailable.")

# --- MAIN RENDERER ---
def render_admin_page():
    if not check_admin_auth():
        return

    st.title("⚙️ VerbaPost Operations")
    
    # Sidebar Navigation
    admin_tab = st.sidebar.radio("Console Section", [
        "Dashboard", 
        "Orders & Fulfillment", 
        "Promo Codes", 
        "Privacy Tools",
        "System Logs"
    ])
    
    if admin_tab == "Dashboard":
        render_health_dashboard()
        
    elif admin_tab == "Orders & Fulfillment":
        render_order_manager()

    elif admin_tab == "Promo Codes":
        render_promo_manager()

    elif admin_tab == "Privacy Tools":
        render_privacy_tools()

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