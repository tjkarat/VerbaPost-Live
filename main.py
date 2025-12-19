import streamlit as st
import time
import os
import logging

# --- LOGGING SETUP ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="VerbaPost",
    page_icon="📮",
    layout="centered",
    initial_sidebar_state="collapsed",
    menu_items={
        'Get Help': 'mailto:support@verbapost.com',
        'Report a bug': "mailto:support@verbapost.com",
        'About': "# VerbaPost \n Send real mail from your screen."
    }
)

# --- CSS STYLING ---
st.markdown("""
<style>
    [data-testid="stSidebarNav"] {display: none !important;}
    .block-container {padding-top: 1rem !important;}
    button[kind="primary"] {
        background-color: #d93025 !important;
        border-color: #d93025 !important;
        color: white !important; 
        font-weight: 600;
    }
    .success-box {
        background-color: #ecfdf5; 
        border: 1px solid #10b981; 
        padding: 20px; 
        border-radius: 10px; 
        text-align: center;
        margin-bottom: 20px;
    }
    .success-title { color: #047857; font-size: 24px; font-weight: bold; margin-bottom: 10px; }
    .tracking-code { font-family: monospace; font-size: 20px; color: #d93025; background: #fff; padding: 5px 10px; border-radius: 4px; border: 1px dashed #ccc;}
</style>
""", unsafe_allow_html=True)

# --- LAZY MODULE LOADER ---
def get_module(module_name):
    """Safely imports modules to prevent crashes."""
    try:
        if module_name == "ui_splash": import ui_splash as m; return m
        if module_name == "ui_login": import ui_login as m; return m
        if module_name == "ui_main": import ui_main as m; return m
        if module_name == "ui_admin": import ui_admin as m; return m
        if module_name == "ui_legal": import ui_legal as m; return m
        if module_name == "ui_legacy": import ui_legacy as m; return m
        if module_name == "payment_engine": import payment_engine as m; return m
        if module_name == "email_engine": import email_engine as m; return m
        if module_name == "audit_engine": import audit_engine as m; return m
        if module_name == "auth_engine": import auth_engine as m; return m
        if module_name == "seo_injector": import seo_injector as m; return m
        if module_name == "analytics": import analytics as m; return m
        if module_name == "mailer": import mailer as m; return m
        if module_name == "letter_format": import letter_format as m; return m
        if module_name == "address_standard": import address_standard as m; return m
        if module_name == "database": import database as m; return m
    except Exception as e:
        logger.error(f"Failed to load {module_name}: {e}")
        return None

# --- SECRET MANAGER IMPORT ---
try: import secrets_manager
except Exception: secrets_manager = None

# --- MAIN LOGIC ---
def main():
    # 1. SEO & ANALYTICS
    seo = get_module("seo_injector")
    if seo: seo.inject_meta()
    analytics = get_module("analytics")
    if analytics: analytics.inject_ga()

    params = st.query_params

    # 2. ADMIN BACKDOOR
    if params.get("view") == "admin":
        st.session_state.app_mode = "admin"

    # 3. HANDLE PAYMENT RETURN
    if "session_id" in params:
        session_id = params["session_id"]
        pay_eng = get_module("payment_engine")
        
        status = "error"
        if pay_eng:
            try:
                raw_result = pay_eng.verify_session(session_id)
                result = {}
                if isinstance(raw_result, dict):
                    result = raw_result
                elif isinstance(raw_result, str) and raw_result == "paid":
                    result = {"paid": True, "email": st.session_state.get("user_email")}
                
                if result.get('paid'):
                    status = "paid"
                    user_email = result.get('email')
                elif result.get('status') == 'open':
                    status = "open"
            except Exception as e:
                logger.error(f"Verify Error: {e}")

        # --- SUCCESS PATH ---
        if status == "paid":
            tier = st.session_state.get("locked_tier", "Letter")
            
            # --- CRITICAL FIX: BYPASS SINGLE LETTER LOGIC FOR CAMPAIGNS ---
            if tier == "Campaign":
                st.session_state.campaign_paid = True
                # We do NOT return here. We let the script continue so render_application()
                # can load ui_main and show the Bulk Campaign Dashboard.
                # Just remove the query param to avoid re-triggering checks endlessly
                # (Streamlit doesn't easily allow query param deletion without rerun, 
                # but we rely on internal state now)
            
            else:
                # SINGLE LETTER FULFILLMENT (Original Logic)
                if "postgrid_ref" not in st.session_state:
                    mailer = get_module("mailer")
                    lf = get_module("letter_format")
                    add_std = get_module("address_standard")
                    db = get_module("database")
                    audit = get_module("audit_engine")
                    
                    if mailer and lf and add_std and "letter_body" in st.session_state:
                        try:
                            # Re-construct PDF
                            body = st.session_state.get("letter_body", "")
                            std_to = add_std.StandardAddress.from_dict(st.session_state.get("addr_to", {}))
                            std_from = add_std.StandardAddress.from_dict(st.session_state.get("addr_from", {}))
                            pdf_bytes = lf.create_pdf(body, std_to, std_from, tier, signature_text=st.session_state.get("signature_text"))
                            
                            # Send to PostGrid
                            ref_id = mailer.send_letter(pdf_bytes, std_to, std_from, description=f"VerbaPost {tier}")
                            
                            if ref_id:
                                st.session_state.postgrid_ref = ref_id
                                
                                # Update DB
                                d_id = st.session_state.get("current_draft_id")
                                if d_id and db:
                                    db.update_draft_data(d_id, status="Sent", tracking_number=ref_id)
                                
                                # Log to Audit
                                if audit:
                                    audit.log_event(
                                        user_email=user_email, 
                                        event_type="ORDER_FULFILLED", 
                                        session_id=session_id,
                                        details={"tier": tier, "postgrid_id": ref_id}
                                    )

                            else:
                                st.error("Letter generated but mailing API failed. Admin notified.")
                                if audit: audit.log_event(user_email, "FULFILLMENT_FAILED", session_id, {"reason": "PostGrid API Error"})
                                
                        except Exception as e:
                            logger.error(f"Fulfillment Error: {e}")

                order_ref = st.session_state.get("postgrid_ref", "Pending...")

                st.markdown(f"""
                    <div class="success-box">
                        <div class="success-title">✅ Payment Confirmed!</div>
                        <p>Your <b>{tier}</b> has been securely generated and sent to our mailing center.</p>
                        <p>Order Reference: <span class="tracking-code">{order_ref}</span></p>
                        <p><small>A confirmation email has been sent to <b>{user_email}</b></small></p>
                    </div>
                """, unsafe_allow_html=True)
                st.balloons()

                if st.button("🏠 Start Another Letter", type="primary", use_container_width=True):
                    st.query_params.clear()
                    keys_to_keep = ["authenticated", "user_email", "user_name", "user_role", "admin_authenticated"]
                    for key in list(st.session_state.keys()):
                        if key not in keys_to_keep:
                            del st.session_state[key]
                    st.rerun()
                return

        elif status == "open":
            st.info("⏳ Payment processing...")
            time.sleep(2)
            st.rerun()
        else:
            if params.get("session_id"):
                # Clean invalid sessions to prevent loops
                pass

    # 4. PASSWORD RESET
    elif params.get("type") == "recovery":
        st.session_state.app_mode = "login"

    # 5. INIT STATE
    if "app_mode" not in st.session_state:
        st.session_state.app_mode = "splash"
        
    mode = st.session_state.app_mode
    current_email = st.session_state.get("user_email")

    # 6. SIDEBAR
    with st.sidebar:
        st.header("VerbaPost System")
        if st.button("🏠 Home", use_container_width=True):
            st.query_params.clear()
            st.session_state.app_mode = "splash"
            st.rerun()
            
        # UPDATED: Swapped Heirloom for Legacy Service
        if st.button("🕊️ Legacy Service (End of Life)", use_container_width=True):
            st.query_params.clear()
            st.session_state.app_mode = "legacy"
            st.rerun()
            
        st.markdown("---")
        
        # Admin Logic
        admin_email = None
        if secrets_manager:
            raw_admin = secrets_manager.get_secret("admin.email")
            if raw_admin: admin_email = raw_admin.lower().strip()
        
        is_admin = st.session_state.get("admin_authenticated", False)
        if is_admin or (current_email and admin_email and current_email == admin_email):
            st.markdown("### 🛠️ Administration")
            if st.button("🔐 Admin Console", key="sidebar_admin_btn", use_container_width=True):
                st.query_params.clear()
                st.session_state.app_mode = "admin"
                st.rerun()
        st.caption(f"v3.4.1 | {st.session_state.app_mode}")

    # 7. ROUTER
    view_param = st.query_params.get("view", "store")
    if view_param == "heirloom":
        try:
            import ui_heirloom
            ui_heirloom.render_dashboard()
            st.stop() 
        except ImportError: st.error("Heirloom module not found.")

    if mode == "splash":
        m = get_module("ui_splash")
        if m: m.render_splash_page()
    elif mode == "legacy":
        m = get_module("ui_legacy")
        if m: m.render_legacy_page()
    elif mode == "login":
        m = get_module("ui_login")
        if m: m.render_login_page()
    elif mode == "admin":
        m = get_module("ui_admin")
        if m: m.render_admin_page()
    elif mode == "legal":
        m = get_module("ui_legal")
        if m: m.render_legal_page()
    elif mode in ["store", "workspace", "review"]:
        m = get_module("ui_main")
        if m: m.render_main()
    else:
        m = get_module("ui_splash")
        if m: m.render_splash_page()

if __name__ == "__main__":
    main()