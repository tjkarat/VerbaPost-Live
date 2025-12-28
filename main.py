import streamlit as st
import time
import os
import logging

# --- LOGGING SETUP ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- 1. CONFIGURATION ---
st.set_page_config(
    page_title="VerbaPost",
    page_icon="📮",
    layout="centered",
    initial_sidebar_state="collapsed",
    menu_items={
        'Get Help': 'mailto:support@verbapost.com',
        'About': "# VerbaPost \n Real mail, real legacy."
    }
)

# --- CSS STYLING (Global) ---
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
    .stDeployButton {display:none;}
    meta { display: block; }
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
            "analytics": "analytics"
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

# --- SEO INJECTOR (Dynamic) ---
def inject_dynamic_seo(mode):
    """
    Injects specific metadata based on the active mode (Archive vs Utility).
    """
    if mode == "archive":
        meta_title = "VerbaPost | The Family Archive"
        meta_desc = "Preserve your family's legacy. We interview your loved ones over the phone and mail you physical keepsake letters."
    else:
        meta_title = "VerbaPost | Send Mail Online"
        meta_desc = "The easiest way to send physical letters from your screen. No stamps, no printers. Just write and send."

    # Using st.markdown to inject raw HTML into the head area implicitly
    seo_html = f"""
        <meta name="description" content="{meta_desc}">
        <meta property="og:type" content="website">
        <meta property="og:title" content="{meta_title}">
        <meta property="og:description" content="{meta_desc}">
        <meta property="og:site_name" content="VerbaPost">
        <meta property="twitter:card" content="summary_large_image">
        <meta property="twitter:title" content="{meta_title}">
        <meta property="twitter:description" content="{meta_desc}">
    """
    st.markdown(seo_html, unsafe_allow_html=True)


# --- MAIN LOGIC ---
def main():
    # 1. System Health Check
    import module_validator
    is_healthy, error_log = module_validator.validate_critical_modules()
    if not is_healthy:
        st.error(f"SYSTEM CRITICAL FAILURE: {error_log}")
        st.stop()

    # 2. DETERMINE SYSTEM MODE (The Hard Router)
    # Options: 'archive' (Default) or 'utility'
    params = st.query_params
    system_mode = params.get("mode", "archive").lower()
    
    # Validation
    if system_mode not in ["archive", "utility"]:
        system_mode = "archive"
    
    # Persist system mode
    st.session_state.system_mode = system_mode
    
    # Inject SEO based on mode
    inject_dynamic_seo(system_mode)
    
    # Analytics (Global)
    analytics = get_module("analytics")
    if analytics: analytics.inject_ga()

    # 3. Handle Stripe/Payment Returns
    if "session_id" in params:
        handle_payment_return(params["session_id"], system_mode)

    # 4. Default Routing Logic
    if "app_mode" not in st.session_state:
        # Default is always splash unless deep linked mode suggests otherwise
        st.session_state.app_mode = "splash"

    # 5. SIDEBAR NAVIGATION (Exclusive Split)
    render_sidebar(system_mode)

    # 6. EXECUTE CONTROLLER
    current_page = st.session_state.app_mode
    
    # --- ROUTE MAP ---
    # Map: 'mode_name': ('file_name', 'function_name')
    route_map = {
        # Shared Routes
        "login":     ("ui_login", "render_login_page"),
        "legal":     ("ui_legal", "render_legal_page"),
        "admin":     ("ui_admin", "render_admin_page"),
        "splash":    ("ui_splash", "render_splash_page"), 

        # Utility Routes (Exclusive)
        "main":      ("ui_main", "render_store_page"),
        "workspace": ("ui_main", "render_workspace_page"),
        "receipt":   ("ui_main", "render_receipt_page"),
        "legacy":    ("ui_legacy", "render_legacy_page"),

        # Archive Routes (Exclusive)
        "heirloom":  ("ui_heirloom", "render_dashboard"),
        "blog":      ("ui_blog", "render_blog_page")
    }

    # --- CROSS-MODE PROTECTION ---
    # Prevent Utility users from seeing Archive pages and vice versa.
    # Only enforce if logged in, otherwise let Splash/Login handle flow.
    
    utility_only = ["main", "workspace", "receipt", "legacy"]
    archive_only = ["heirloom"]

    if st.session_state.get("authenticated"):
        if system_mode == "utility" and current_page in archive_only:
            st.session_state.app_mode = "main"
            st.rerun()
        elif system_mode == "archive" and current_page in utility_only:
            st.session_state.app_mode = "heirloom"
            st.rerun()

    # Execution
    if current_page in route_map:
        module_name, function_name = route_map[current_page]
        mod = get_module(module_name)
        
        if mod and hasattr(mod, function_name):
            # Execute the UI function
            getattr(mod, function_name)()
        else:
            st.error(f"404: Route {current_page} not found.")
            st.session_state.app_mode = "splash"
            st.rerun()
    else:
        # Fallback for unknown states
        st.error(f"Unknown Route: {current_page}")
        st.session_state.app_mode = "splash"
        st.rerun()

def render_sidebar(mode):
    """
    Renders sidebar elements based on mode.
    """
    with st.sidebar:
        st.header("VerbaPost" if mode == "utility" else "The Archive")
        
        # --- NAVIGATION ---
        # If logged in, show context-aware buttons
        if st.session_state.get("authenticated"):
            if mode == "utility":
                if st.button("📮 Letter Store", use_container_width=True):
                    st.session_state.app_mode = "main"
                    st.rerun()
                
                # [REMOVED CERTIFIED MAIL BUTTON]

            elif mode == "archive":
                if st.button("📚 Family Archive", use_container_width=True):
                    st.session_state.app_mode = "heirloom"
                    st.rerun()

        st.markdown("---")

        # --- AUTHENTICATION & ADMIN ---
        if not st.session_state.get("authenticated"):
            if st.button("🔐 Login / Sign Up", use_container_width=True):
                st.session_state.app_mode = "login"
                st.session_state.redirect_to = "heirloom" if mode == "archive" else "main"
                st.rerun()
        else:
            user_email = st.session_state.get("user_email")
            st.caption(f"Logged in as: {user_email}")
            if st.button("🚪 Sign Out", use_container_width=True):
                st.session_state.authenticated = False
                st.session_state.user_email = None
                st.session_state.app_mode = "splash"
                st.rerun()
            
            # Admin Link (Strict Hiding)
            admin_email = None
            if secrets_manager:
                admin_email = secrets_manager.get_secret("admin.email")
            if not admin_email and "admin" in st.secrets:
                admin_email = st.secrets["admin"]["email"]
                
            if user_email and admin_email and user_email.strip() == admin_email.strip():
                st.divider()
                if st.button("⚡ Admin Console", use_container_width=True):
                    st.session_state.app_mode = "admin"
                    st.rerun()

def handle_payment_return(session_id, system_mode):
    """
    Handles Stripe callbacks. Consolidates logic to keep main() clean.
    """
    db = get_module("database")
    pay_eng = get_module("payment_engine")
    
    # Idempotency (Prevent Double-Processing)
    if db and hasattr(db, "record_stripe_fulfillment"):
        if not db.record_stripe_fulfillment(session_id):
            return # Already handled

    if pay_eng:
        user_email = st.session_state.get("user_email")
        try:
            raw_obj = pay_eng.verify_session(session_id)
            if hasattr(raw_obj, 'payment_status') and raw_obj.payment_status == 'paid':
                
                # Recover Email from Stripe if session expired locally
                if not user_email and hasattr(raw_obj, 'customer_email'):
                    user_email = raw_obj.customer_email
                
                st.session_state.authenticated = True
                st.session_state.user_email = user_email

                # Check Metadata
                meta_id = None
                ref_id = getattr(raw_obj, 'client_reference_id', '')
                if hasattr(raw_obj, 'metadata') and raw_obj.metadata:
                    meta_id = raw_obj.metadata.get('draft_id', '')

                # 1. SUBSCRIPTION (Archive Mode)
                is_annual = (ref_id == "SUBSCRIPTION_INIT") or (meta_id == "SUBSCRIPTION_INIT")
                if is_annual:
                    if db and user_email: 
                        # Update credits in database
                        db.update_user_credits(user_email, 48)
                    st.query_params.clear()
                    st.session_state.app_mode = "heirloom"
                    st.rerun()
                    return

                # 2. SINGLE LETTER (Utility Mode)
                if db and meta_id:
                    with db.get_db_session() as s:
                        d = s.query(db.LetterDraft).filter(db.LetterDraft.id == meta_id).first()
                        if d:
                            d.status = "Paid/Writing"
                            # If it was a Legacy (Certified) letter, store that state
                            st.session_state.paid_tier = d.tier
                            st.session_state.current_draft_id = meta_id
                            s.commit()
                
                # Redirect based on mode
                st.query_params.clear()
                if system_mode == "utility":
                    st.session_state.app_mode = "workspace"
                else:
                    st.session_state.app_mode = "heirloom"
                st.rerun()
        except Exception as e:
            logger.error(f"Payment Verification Error: {e}")

if __name__ == "__main__":
    main()