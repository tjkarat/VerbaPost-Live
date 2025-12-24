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

# --- ROBUST MODULE LOADER ---
def get_module(module_name):
    """
    Safely imports modules and logs specific errors if they fail.
    """
    try:
        # Static map ensures we don't try to import random strings
        known_modules = {
            "ui_splash": "ui_splash",
            "ui_login": "ui_login",
            "ui_main": "ui_main",
            "ui_admin": "ui_admin",
            "ui_legacy": "ui_legacy",
            "ui_heirloom": "ui_heirloom",
            "ui_legal": "ui_legal",
            "ui_blog": "ui_blog",
            "payment_engine": "payment_engine",
            "database": "database",
            "analytics": "analytics",
            "seo_injector": "seo_injector"
        }
        
        if module_name in known_modules:
            return __import__(known_modules[module_name])
        else:
            logger.warning(f"Module {module_name} not in known_modules map.")
            return None
            
    except ImportError as e:
        logger.error(f"Failed to load {module_name}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error loading {module_name}: {e}")
        return None

try: import secrets_manager
except Exception: secrets_manager = None

# --- MAIN LOGIC ---
def main():
    # 1. System Health Check
    import module_validator
    is_healthy, error_log = module_validator.validate_critical_modules()
    if not is_healthy:
        st.error(f"🚨 SYSTEM CRITICAL FAILURE: {error_log}")
        st.stop()

    # 2. Global Injections
    seo = get_module("seo_injector")
    if seo: seo.inject_meta()
    analytics = get_module("analytics")
    if analytics: analytics.inject_ga()

    # 3. Handle URL Parameters (Routing & Payment Returns)
    params = st.query_params

    # Admin Shortcut
    if params.get("view") == "admin":
        st.session_state.app_mode = "admin"

    # Blog Shortcut
    if params.get("view") == "blog":
        st.session_state.app_mode = "blog"

    # STRIPE RETURN HANDLER
    if "session_id" in params:
        session_id = params["session_id"]
        db = get_module("database")
        pay_eng = get_module("payment_engine")
        
        # A. Idempotency Check (Prevent Double-Processing)
        # We only proceed if this session_id hasn't been handled yet.
        processed = False
        if db and hasattr(db, "record_stripe_fulfillment"):
            if not db.record_stripe_fulfillment(session_id):
                # Already processed, but we should ensure the user isn't stuck.
                # If they are refreshing the success page, just let them stay or redirect home.
                processed = True
        
        if not processed and pay_eng:
            status = "error"
            result = {}
            user_email = st.session_state.get("user_email")

            try:
                raw_obj = pay_eng.verify_session(session_id)
                if hasattr(raw_obj, 'payment_status') and (raw_obj.payment_status == 'paid' or raw_obj.status == 'complete'):
                    status = "paid"
                    result = raw_obj
                    # Recover email from Stripe if session expired locally
                    if not user_email and hasattr(raw_obj, 'customer_email'):
                        user_email = raw_obj.customer_email
            except Exception as e:
                logger.error(f"Verify Error: {e}")

            if status == "paid":
                st.session_state.authenticated = True
                st.session_state.user_email = user_email
                
                # Extract Metadata
                meta_id = None
                ref_id = getattr(result, 'client_reference_id', '')
                if hasattr(result, 'metadata') and result.metadata:
                    meta_id = result.metadata.get('draft_id', '')

                # Case 1: Subscription
                is_annual = (ref_id == "SUBSCRIPTION_INIT") or (meta_id == "SUBSCRIPTION_INIT")
                if is_annual:
                    if db and user_email: db.update_user_credits(user_email, 48)
                    st.query_params.clear()
                    st.success("Annual Pass Activated!"); st.balloons()
                    if st.button("Enter Archive"): 
                        st.session_state.app_mode = "heirloom"
                        st.rerun()
                    return

                # Case 2: Letter Purchase
                paid_tier = "Standard"
                if db and meta_id:
                    try:
                        with db.get_db_session() as s:
                            d = s.query(db.LetterDraft).filter(db.LetterDraft.id == meta_id).first()
                            if d: 
                                paid_tier = d.tier
                                d.status = "Paid/Writing"
                                s.commit()
                    except Exception as e:
                        logger.error(f"DB Update Error: {e}")
                
                # SET STATE FOR EDITOR
                st.session_state.paid_tier = paid_tier
                st.session_state.current_draft_id = meta_id
                
                # CRITICAL: Force the routing to workspace
                st.session_state.app_mode = "workspace" 
                
                # Clear params and reload to apply state
                st.query_params.clear()
                st.rerun()

    # 4. Default Routing
    if "app_mode" not in st.session_state:
        st.session_state.app_mode = "splash"
        
    mode = st.session_state.app_mode

    # 5. Sidebar Navigation
    with st.sidebar:
        st.header("VerbaPost System")
        if st.button("✉️ Write a Letter", use_container_width=True):
            st.query_params.clear()
            st.session_state.app_mode = "main"
            st.rerun()
        if st.button("📚 Family Archive", use_container_width=True):
            st.query_params.clear()
            st.session_state.app_mode = "heirloom"
            st.rerun()
        st.markdown("---")
        
        # Admin Access Check
        admin_email = None
        if secrets_manager:
            admin_email = secrets_manager.get_secret("admin.email")
        if not admin_email and "admin" in st.secrets:
            admin_email = st.secrets["admin"]["email"]

        if st.session_state.get("authenticated") and st.session_state.get("user_email") == admin_email:
            if st.button("🔒 Account Settings", use_container_width=True):
                st.session_state.app_mode = "admin"
                st.rerun()

    # 6. ROUTING CONTROLLER (THE FIX)
    # We map the abstract "app_mode" strings to the concrete physical files
    # AND the function within them.
    
    # Map: 'mode_name': ('file_name', 'function_name')
    route_map = {
        "splash":    ("ui_splash", "render_splash_page"),
        "login":     ("ui_login", "render_login_page"),
        "main":      ("ui_main", "render_store_page"),       # Store
        "workspace": ("ui_main", "render_workspace_page"),   # Editor (Same file, diff function)
        "receipt":   ("ui_main", "render_receipt_page"),     # Receipt (Same file, diff function)
        "heirloom":  ("ui_heirloom", "render_dashboard"),
        "admin":     ("ui_admin", "render_admin_page"),
        "legacy":    ("ui_legacy", "render_legacy_page"),
        "legal":     ("ui_legal", "render_legal_page"),
        "blog":      ("ui_blog", "render_blog_page")
    }

    if mode in route_map:
        module_name, function_name = route_map[mode]
        
        # Load module
        mod = get_module(module_name)
        
        if mod and hasattr(mod, function_name):
            # Execute
            getattr(mod, function_name)()
        else:
            st.error(f"Routing Error: Could not find {function_name} in {module_name}")
            # Fallback
            m_splash = get_module("ui_splash")
            if m_splash: m_splash.render_splash_page()
    else:
        # Unknown mode, fallback to splash
        m_splash = get_module("ui_splash")
        if m_splash: m_splash.render_splash_page()

if __name__ == "__main__":
    main()