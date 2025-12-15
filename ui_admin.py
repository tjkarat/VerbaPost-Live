import streamlit as st
import pandas as pd
from datetime import datetime
import json
import base64
import os

# --- ROBUST IMPORTS ---
# We use try/except to prevent the entire admin console from crashing
# if a single module (like the printer or payment engine) is offline.
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
                # 1. Check Secrets Manager first
                admin_secret = None
                if secrets_manager:
                    admin_secret = secrets_manager.get_secret("admin.password")
                
                # 2. Fallback to raw secrets
                if not admin_secret:
                    try:
                        admin_secret = st.secrets.get("admin", {}).get("password")
                    except:
                        pass # proceed to fallback
                
                # 3. Emergency Fallback (remove in high-security envs)
                if not admin_secret:
                    admin_secret = "admin123" 
                
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
    
    # 1. Database Check (SQLAlchemy Engine)
    with col1:
        try:
            if database and hasattr(database, 'get_engine'):
                engine = database.get_engine()
                if engine:
                    st.metric("Database", "Online 🟢")
                else:
                    st.metric("Database", "Offline 🔴")
            else:
                st.metric("Database", "Not Loaded 🟡")
        except Exception as e:
            st.metric("Database", "Error 🔴")
            st.caption(str(e)[:20])

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
            if mailer and secrets_manager:
                key = secrets_manager.get_secret("postgrid.api_key")
                st.metric("PostGrid", "Configured 🟢" if key else "Missing Key 🟡")
            else:
                st.metric("PostGrid", "Offline 🔴")
        except:
            st.metric("PostGrid", "Error 🔴")

    # 4. Email Check
    with col4:
        try:
            if secrets_manager:
                key = secrets_manager.get_secret("resend.api_key") or secrets_manager.get_secret("email.password")
                st.metric("Email", "Configured 🟢" if key else "Missing Key 🟡")
            else:
                st.metric("Email", "Error 🔴")
        except:
            st.metric("Email", "Error 🔴")

    # 5. Stripe Check
    with col5:
        try:
            if secrets_manager:
                key = secrets_manager.get_secret("stripe.secret_key")
                st.metric("Stripe", "Configured 🟢" if key else "Missing Key 🟡")
            else:
                st.metric("Stripe", "Error 🔴")
        except:
            st.metric("Stripe", "Error 🔴")

# --- PROMO CODE MANAGER ---
def render_promo_manager():
    st.subheader("🎟️ Promo Code Manager")
    
    # View Active Codes
    if database:
        try:
            with database.get_db_session() as db:
                # Check if model exists before querying to prevent crash
                if hasattr(database, "PromoCode"):
                    codes = db.query(database.PromoCode).all()
                    if codes:
                        data = []
                        for c in codes:
                            data.append({
                                "Code": c.code,
                                "Max Uses": c.max_uses,
                                "Active": c.active,
                                "Created": c.created_at.strftime("%Y-%m-%d")
                            })
                        df = pd.DataFrame(data)
                        st.dataframe(df, use_container_width=True)
                    else:
                        st.info("No active promo codes.")
                else:
                    st.error("PromoCode model not defined in database.py")
        except Exception as e:
            st.error(f"Fetch Error: {e}")
    else:
        st.error("Database module not loaded")

    # Create New Code
    with st.expander("➕ Create New Code"):
        with st.form("new_promo"):
            c1, c2, c3 = st.columns(3)
            code = c1.text_input("Code (e.g., WELCOME10)").upper()
            val = c2.number_input("Discount Value ($)", min_value=0.0, step=0.5, value=5.0)
            max_uses = c3.number_input("Max Uses", min_value=1, value=100)
            
            if st.form_submit_button("Create Code"):
                if database and code:
                    try:
                        with database.get_db_session() as db:
                            new_code = database.PromoCode(
                                code=code,
                                max_uses=max_uses,
                                active=True
                                # Value logic would go here depending on DB schema
                            )
                            db.add(new_code)
                            # Implicit commit via context manager or needs explicit commit
                            db.commit()
                        st.success(f"✅ Created code: {code}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")

# --- ORDER MANAGER ---
def render_order_manager():
    st.subheader("📦 Order Management")
    
    filter_status = st.selectbox("Filter Status", ["All", "Paid", "Pending Payment", "Draft", "Completed"], index=0)
    
    if not database:
        st.error("Database not available")
        return
        
    try:
        # Fetch orders from database using ORM
        with database.get_db_session() as db:
            query = db.query(database.LetterDraft).order_by(database.LetterDraft.created_at.desc()).limit(50)
            
            if filter_status != "All":
                query = query.filter(database.LetterDraft.status == filter_status)
            
            orders = query.all()
            
            if not orders:
                st.info("No orders found matching criteria.")
                return
            
            # Convert to DataFrame for display
            data = []
            for order in orders:
                data.append({
                    "ID": order.id,
                    "Date": order.created_at.strftime("%Y-%m-%d %H:%M"),
                    "Email": order.user_email,
                    "Tier": order.tier,
                    "Status": order.status,
                    "Price": order.price
                })
            
            df = pd.DataFrame(data)
            st.dataframe(df[["ID", "Date", "Email", "Tier", "Status", "Price"]], use_container_width=True)
            
            # --- ACTION PANEL ---
            st.divider()
            st.markdown("### 🔧 Order Actions")
            
            selected_id = st.selectbox("Select Order ID to Manage", df["ID"].tolist())
            
            if selected_id:
                # Fetch full order details again to ensure freshness
                order = db.query(database.LetterDraft).filter(database.LetterDraft.id == selected_id).first()
                
                if not order:
                    st.error("Order not found")
                    return
                
                # Display Details
                with st.expander("📋 View Full Order Details", expanded=False):
                    st.json({
                        "ID": order.id,
                        "Email": order.user_email,
                        "Tier": order.tier,
                        "Status": order.status,
                        "Price": order.price,
                        "Content": order.transcription[:200] + "..." if order.transcription and len(order.transcription) > 200 else order.transcription,
                        "Created": str(order.created_at)
                    })
                
                # Parse JSON addresses safely
                try:
                    to_addr = json.loads(order.recipient_json) if order.recipient_json else {}
                    from_addr = json.loads(order.sender_json) if order.sender_json else {}
                except:
                    to_addr = {}
                    from_addr = {}
                
                # --- EDIT SECTION ---
                with st.expander("✏️ Edit Order Details", expanded=False):
                    with st.form(f"edit_form_{selected_id}"):
                        st.warning(f"Editing Order #{selected_id}")
                        
                        c1, c2 = st.columns(2)
                        with c1:
                            st.markdown("**Recipient**")
                            rn = st.text_input("Name", value=to_addr.get('name', ''))
                            ra1 = st.text_input("Street", value=to_addr.get('street', ''))
                            rc = st.text_input("City", value=to_addr.get('city', ''))
                            rs = st.text_input("State", value=to_addr.get('state', ''))
                            rz = st.text_input("Zip", value=to_addr.get('zip', ''))
                        
                        with c2:
                            st.markdown("**Content**")
                            new_content = st.text_area("Body Text", value=order.transcription or "", height=200)
                        
                        if st.form_submit_button("💾 Save Changes"):
                            # Update in database
                            new_to_addr = {'name': rn, 'street': ra1, 'city': rc, 'state': rs, 'zip': rz}
                            
                            # Update logic using DB function
                            success = database.update_draft_data(
                                selected_id,
                                to_addr=new_to_addr,
                                content=new_content
                            )
                            if success:
                                st.success("✅ Order updated!")
                                st.rerun()
                            else:
                                st.error("Failed to update order")
                
                # --- ACTIONS ---
                st.markdown("#### 🚀 Quick Actions")
                col1, col2, col3 = st.columns(3)
                
                # Action 1: Generate PDF
                with col1:
                    if st.button("📄 View PDF", use_container_width=True):
                        if letter_format and order.transcription:
                            try:
                                pdf_bytes = letter_format.create_pdf(
                                    order.transcription,
                                    to_addr,
                                    from_addr,
                                    tier=order.tier or "Standard"
                                )
                                
                                # Safety cast
                                pdf_bytes = bytes(pdf_bytes)
                                
                                # Display
                                b64 = base64.b64encode(pdf_bytes).decode('utf-8')
                                st.markdown(f'<embed src="data:application/pdf;base64,{b64}" width="100%" height="500" type="application/pdf">', unsafe_allow_html=True)
                                st.download_button("⬇️ Download PDF", pdf_bytes, f"order_{selected_id}.pdf", "application/pdf")
                            except Exception as e:
                                st.error(f"PDF Error: {e}")
                        else:
                            st.warning("No content to generate PDF")
                
                # Action 2: Mark as Completed
                with col2:
                    if st.button("✅ Mark Completed", use_container_width=True):
                        success = database.update_draft_data(selected_id, status="Completed")
                        if success:
                            st.success("Status updated!")
                            st.rerun()
                        else:
                            st.error("Update failed")
                
                # Action 3: Delete Order
                with col3:
                    if st.button("🗑️ Delete", use_container_width=True, type="primary"):
                        if database.delete_draft(selected_id):
                            st.success(f"Deleted order #{selected_id}")
                            st.rerun()
                        else:
                            st.error("Delete failed")
                
    except Exception as e:
        st.error(f"Database Error: {e}")

# --- PRIVACY & CLEANUP ---
def render_privacy_tools():
    st.subheader("🗑️ Data Privacy & Cleanup")
    st.warning("⚠️ These actions are destructive. Proceed with caution.")
    
    with st.expander("🔍 What does Privacy Wipe do?"):
        st.markdown("""
        This action will:
        - Delete letter content (transcription field) from old drafts
        - Keep metadata (dates, emails, status) for accounting
        - **Cannot be undone**
        """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        days_old = st.number_input("Delete drafts older than (days)", min_value=30, value=90)
    
    with col2:
        st.metric("Action", "Privacy Wipe")
    
    if st.button("🚨 RUN PRIVACY WIPE", type="primary", use_container_width=True):
        confirmation = st.checkbox("⚠️ I understand this will permanently delete letter content")
        
        if confirmation and database:
            try:
                # Get drafts to wipe
                with database.get_db_session() as db:
                    from datetime import timedelta
                    cutoff_date = datetime.utcnow() - timedelta(days=days_old)
                    
                    drafts = db.query(database.LetterDraft).filter(
                        database.LetterDraft.created_at < cutoff_date,
                        database.LetterDraft.status.in_(["Completed", "Paid"])
                    ).all()
                    
                    count = 0
                    for draft in drafts:
                        draft.transcription = "[CONTENT DELETED FOR PRIVACY]"
                        count += 1
                    
                    db.commit()
                
                st.success(f"✅ Privacy wipe completed. {count} drafts cleaned.")
            except Exception as e:
                st.error(f"Procedure Failed: {e}")
        elif not confirmation:
            st.warning("Please check the confirmation box")

# --- SYSTEM LOGS ---
def render_system_logs():
    st.subheader("📜 Audit Logs")
    
    if not database:
        st.error("Database not available")
        return
    
    try:
        with database.get_db_session() as db:
            # Check if audit_events table exists using SQL inspection
            from sqlalchemy import inspect
            inspector = inspect(db.bind)
            tables = inspector.get_table_names()
            
            if "audit_events" not in tables:
                st.info("📋 Audit logging table not yet created.")
                return
            
            # Fetch logs using raw SQL for simplicity if model missing
            logs = db.execute("SELECT * FROM audit_events ORDER BY created_at DESC LIMIT 100").fetchall()
            
            if logs:
                st.dataframe(pd.DataFrame(logs))
            else:
                st.info("No logs found.")
                
    except Exception as e:
        st.error(f"Log Fetch Error: {e}")

# --- MAIN RENDERER ---
def render_admin_page():
    if not check_admin_auth():
        return

    st.title("⚙️ VerbaPost Operations")
    
    # Sidebar Navigation
    admin_tab = st.sidebar.radio("Console Section", [
        "📊 Dashboard", 
        "📦 Orders & Fulfillment", 
        "🎟️ Promo Codes", 
        "🗑️ Privacy Tools",
        "📜 System Logs"
    ])
    
    if admin_tab == "📊 Dashboard":
        render_health_dashboard()
        
    elif admin_tab == "📦 Orders & Fulfillment":
        render_order_manager()

    elif admin_tab == "🎟️ Promo Codes":
        render_promo_manager()

    elif admin_tab == "🗑️ Privacy Tools":
        render_privacy_tools()

    elif admin_tab == "📜 System Logs":
        render_system_logs()

    # Logout Button
    st.markdown("---")
    if st.button("🔴 Logout Admin", use_container_width=True):
        st.session_state.admin_authenticated = False
        st.rerun()