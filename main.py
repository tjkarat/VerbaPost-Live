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
    try:
        if module_name == "ui_splash": import ui_splash as m; return m
        if module_name == "ui_login": import ui_login as m; return m
        if module_name == "ui_main": import ui_main as m; return m
        if module_name == "ui_admin": import ui_admin as m; return m
        if module_name == "ui_legal": import ui_legal as m; return m
        if module_name == "ui_legacy": import ui_legacy as m; return m
        if module_name == "ui_heirloom": import ui_heirloom as m; return m
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
    # --- SYSTEM HEALTH CHECK ---
    import module_validator
    is_healthy, error_log = module_validator.validate_critical_modules()
    
    if not is_healthy:
        st.error("🚨 SYSTEM CRITICAL FAILURE")
        st.warning("The application cannot start because critical components are missing.")
        with st.expander("View Error Log", expanded=True):
            for err in error_log:
                st.code(err, language="text")
        st.stop() # Halts execution immediately
    # ------------------------------------

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
        db = get_module("database")
        
        status = "error"
        result = {}
        user_email = st.session_state.get("user_email")
        
        if pay_eng:
            try:
                # Retrieve Full Stripe Object
                raw_obj = pay_eng.verify_session(session_id)
                
                if hasattr(raw_obj, 'payment_status'):
                    if raw_obj.payment_status == 'paid' or raw_obj.status == 'complete':
                        status = "paid"
                        result = raw_obj
                        # Retrieve email from Stripe customer data if local session lost
                        if not user_email:
                            user_email = raw_obj.customer_email
            except Exception as e:
                logger.error(f"Verify Error: {e}")

        # --- SUCCESS PATH ---
        if status == "paid":
            
            # [CRITICAL START] IDEMPOTENCY CHECK
            # Prevents double-fulfillment on page refresh
            if db:
                is_new_transaction = db.record_stripe_fulfillment(session_id)
                if not is_new_transaction:
                    st.markdown("""
                        <div class="success-box">
                            <div class="success-title">✅ Order Retrieved</div>
                            <p>This transaction has already been processed.</p>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    if st.button("🏠 Return Home", type="primary", use_container_width=True):
                        st.query_params.clear()
                        st.session_state.app_mode = "store"
                        st.rerun()
                    return
            # [CRITICAL END]
            
            # RESTORE SESSION (Critical for Heirloom Redirect)
            st.session_state.authenticated = True
            st.session_state.user_email = user_email
            
            # --- DETECT SUBSCRIPTION ---
            ref_id = getattr(result, 'client_reference_id', '')
            meta_id = ""
            if hasattr(result, 'metadata') and result.metadata:
                meta_id = result.metadata.get('draft_id', '')
                
            is_subscription = (ref_id == "SUBSCRIPTION_INIT") or (meta_id == "SUBSCRIPTION_INIT")
            if not is_subscription:
                is_subscription = st.session_state.get("pending_subscription", False)

            # === PATH A: SUBSCRIPTION UNLOCK ===
            if is_subscription:
                if db and user_email:
                    db.update_user_credits(user_email, 4)
                    # Sync local profile
                    if "user_profile" in st.session_state:
                        st.session_state.user_profile["credits"] = 4
                    else:
                        st.session_state.user_profile = db.get_user_profile(user_email)
                
                # Clear URL params
                st.query_params.clear()
                
                st.markdown(f"""
                    <div class="success-box">
                        <div class="success-title">🔓 Archive Unlocked!</div>
                        <p>Welcome to the <b>Family Archive</b>.</p>
                        <p>Your subscription is active. 4 Credits have been added.</p>
                    </div>
                """, unsafe_allow_html=True)
                
                st.balloons()
                
                if st.button("🎙️ Enter The Archive", type="primary", use_container_width=True):
                    st.session_state.app_mode = "heirloom"
                    st.rerun()
                return

            # === PATH B: STANDARD LETTER FULFILLMENT ===
            else:
                tier = st.session_state.get("locked_tier", "Letter")
                
                # Idempotent Send Check
                if "postgrid_ref" not in st.session_state:
                    mailer = get_module("mailer")
                    lf = get_module("letter_format")
                    add_std = get_module("address_standard")
                    audit = get_module("audit_engine")
                    
                    if mailer and lf and add_std and "letter_body" in st.session_state:
                        try:
                            body = st.session_state.get("letter_body", "")
                            std_to = add_std.StandardAddress.from_dict(st.session_state.get("addr_to", {}))
                            std_from = add_std.StandardAddress.from_dict(st.session_state.get("addr_from", {}))
                            pdf_bytes = lf.create_pdf(body, std_to, std_from, tier, signature_text=st.session_state.get("signature_text"))
                            
                            # Send
                            ref_id = mailer.send_letter(pdf_bytes, std_to, std_from, description=f"VerbaPost {tier}")
                            
                            if ref_id:
                                st.session_state.postgrid_ref = ref_id
                                # Update DB
                                d_id = st.session_state.get("current_draft_id")
                                if d_id and db:
                                    db.update_draft_data(d_id, status="Sent", tracking_number=ref_id)
                                # Log
                                if audit:
                                    audit.log_event(user_email, "ORDER_FULFILLED", session_id, {"postgrid_id": ref_id})

                        except Exception as e:
                            logger.error(f"Fulfillment Error: {e}")

                order_ref = st.session_state.get("postgrid_ref", "Pending...")
                st.markdown(f"""
                    <div class="success-box">
                        <div class="success-title">✅ Payment Confirmed!</div>
                        <p>Your <b>{tier}</b> has been securely generated and sent to our mailing center.</p>
                        <p>Order Reference: <span class="tracking-code">{order_ref}</span></p>
                    </div>
                """, unsafe_allow_html=True)
                
                try:
                    lf = get_module("letter_format")
                    add_std = get_module("address_standard")
                    if lf and add_std:
                        body = st.session_state.get("letter_body", "")
                        std_to = add_std.StandardAddress.from_dict(st.session_state.get("addr_to", {}))
                        std_from = add_std.StandardAddress.from_dict(st.session_state.get("addr_from", {}))
                        final_pdf = lf.create_pdf(body, std_to, std_from, tier, signature_text=st.session_state.get("signature_text"))
                        st.download_button("⬇️ Download Receipt & Copy", data=final_pdf, file_name=f"VerbaPost_{order_ref}.pdf", mime="application/pdf", use_container_width=True)
                except: pass
                
                st.balloons()
                if st.button("🏠 Start Another Letter", type="primary", use_container_width=True):
                    st.query_params.clear()
                    st.session_state.app_mode = "store"
                    st.rerun()
                return

    # 4. PASSWORD RESET (RESTORED!)
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
        # 8. NAVIGATION LABELS (UPDATED)
        if st.button("✉️ Write a Letter", use_container_width=True):
            st.query_params.clear()
            st.session_state.app_mode = "store"
            st.rerun()
            
        # --- NEW LEGACY LINK ---
        if st.button("🕊️ Legacy Service", use_container_width=True, help="Certified End-of-Life & Legal Correspondence"):
            st.query_params.clear()
            st.session_state.app_mode = "legacy"
            st.rerun()
            
        if st.button("📚 Family Stories", use_container_width=True):
            st.query_params.clear()
            st.session_state.app_mode = "heirloom"
            st.rerun()
        st.markdown("---")
        
        # Admin Logic (Button renamed to 'Account Settings' per request, but goes to Admin)
        is_admin = st.session_state.get("admin_authenticated", False)
        if secrets_manager:
            admin_email = secrets_manager.get_secret("admin.email")
            if is_admin or (current_email and admin_email and current_email.strip() == admin_email.strip()):
                 if st.button("🔒 Account Settings", use_container_width=True):
                    st.session_state.app_mode = "admin"
                    st.rerun()

    # 7. ROUTER (FIXED: Unwrapped expressions to prevent 'None' at bottom)
    if mode == "splash":
        m = get_module("ui_splash")
        if m: m.render_splash_page()
    elif mode == "login":
        m = get_module("ui_login")
        if m: m.render_login_page()
    elif mode in ["store", "workspace", "review"]:
        m = get_module("ui_main")
        if m: m.render_main()
    elif mode == "heirloom":
        m = get_module("ui_heirloom")
        if m: m.render_dashboard()
    elif mode == "admin":
        m = get_module("ui_admin")
        if m: m.render_admin_page()
    elif mode == "legacy":
        m = get_module("ui_legacy")
        if m: m.render_legacy_page()
    elif mode == "legal":
        m = get_module("ui_legal")
        if m: m.render_legal_page()
    else:
        m = get_module("ui_splash")
        if m: m.render_splash_page()

if __name__ == "__main__":
    main()