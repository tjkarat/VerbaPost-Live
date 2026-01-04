import streamlit as st
import time
import os
import logging
import ast
import uuid 
from datetime import datetime, timedelta

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
    .stDeployButton {display:none;}
    meta { display: block; }
</style>
""", unsafe_allow_html=True)

# --- ROBUST MODULE LOADER ---
def get_module(module_name):
    try:
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
            "auth_engine": "auth_engine"
        }
        if module_name in known_modules:
            return __import__(known_modules[module_name])
        return None
    except Exception as e:
        logger.error(f"Failed to load {module_name}: {e}")
        return None

try: import secrets_manager
except Exception: secrets_manager = None
try: import mailer
except ImportError: mailer = None
try: import letter_format
except ImportError: letter_format = None
try: import email_engine
except ImportError: email_engine = None
try: import auth_listener
except ImportError: auth_listener = None

# --- SEO INJECTOR ---
def inject_dynamic_seo(mode):
    if mode == "archive":
        meta_title = "VerbaPost | The Family Archive"
        meta_desc = "Preserve your family's legacy. We interview your loved ones over the phone and mail you physical keepsake letters."
    else:
        meta_title = "VerbaPost | Send Mail Online"
        meta_desc = "The easiest way to send physical letters from your screen. No stamps, no printers. Just write and send."

    seo_html = f"""
        <meta name="description" content="{meta_desc}">
        <meta property="og:type" content="website">
        <meta property="og:title" content="{meta_title}">
        <meta property="og:description" content="{meta_desc}">
    """
    st.markdown(seo_html, unsafe_allow_html=True)


# --- MAIN LOGIC ---
def main():
    # 0. AUTH LISTENER (OAuth Hash Handler)
    if auth_listener:
        auth_listener.listen_for_oauth()

    # --- NEW: OAUTH HANDSHAKE ---
    # Catches the reload AFTER auth_listener has converted hash to query params
    if "type" in st.query_params and st.query_params["type"] == "oauth_callback":
        token = st.query_params.get("access_token")
        
        if token:
            auth_eng = get_module("auth_engine")
            
            if auth_eng:
                # We use a spinner to indicate activity while verifying
                with st.spinner("Verifying Google Account..."):
                    email, err = auth_eng.verify_oauth_token(token)
                    
                    if email:
                        # SUCCESS! Log them in
                        st.session_state.authenticated = True
                        st.session_state.user_email = email
                        
                        # Clean the URL so token doesn't leak or re-trigger
                        st.query_params.clear()
                        
                        # Route to Heirloom (Archive) by default for Google Logins
                        st.session_state.app_mode = "heirloom"
                        st.rerun()
                    else:
                        st.error(f"Authentication Failed: {err}")
    # ---------------------------

    # 2. DETERMINE SYSTEM MODE
    if "system_mode" not in st.session_state:
        st.session_state.system_mode = st.query_params.get("mode", "archive").lower()
    
    system_mode = st.session_state.system_mode
    inject_dynamic_seo(system_mode)
    
    analytics = get_module("analytics")
    if analytics: analytics.inject_ga()

    # 3. Handle Stripe/Payment Returns
    if "session_id" in st.query_params:
        handle_payment_return(st.query_params["session_id"])

    # 4. Default Routing Logic
    if "app_mode" not in st.session_state:
        # Check URL for navigation targets
        nav_target = st.query_params.get("nav")
        
        # --- PUBLIC ROUTES (No Auth Required) ---
        if nav_target == "login":
            st.session_state.app_mode = "login"
            if system_mode == "archive":
                st.session_state.redirect_to = "heirloom"
            else:
                st.session_state.redirect_to = "main"

        elif nav_target == "legal":
             st.session_state.app_mode = "legal"
             
        elif nav_target == "blog":
             st.session_state.app_mode = "blog"

        # --- PROTECTED ROUTES (Auth Required) ---
        elif nav_target == "heirloom":
            if st.session_state.get("authenticated"):
                st.session_state.app_mode = "heirloom"
            else:
                st.session_state.app_mode = "login"
                st.session_state.redirect_to = "heirloom"

        elif nav_target == "store":
            if st.session_state.get("authenticated"):
                 st.session_state.app_mode = "main"
            else:
                st.session_state.app_mode = "login"
                st.session_state.redirect_to = "main"

        else:
            # Fallback to Splash
            st.session_state.app_mode = "splash"
            
    # 5. LAZY SUBSCRIPTION CHECK (Refills credits on login)
    if st.session_state.get("authenticated") and not st.session_state.get("credits_synced"):
        pay_eng = get_module("payment_engine")
        user_email = st.session_state.get("user_email")
        if pay_eng and user_email:
            try:
                # Calls Stripe and syncs local DB
                if pay_eng.check_subscription_status(user_email):
                    st.toast("🔄 Monthly Credits Refilled!")
            except Exception as e:
                logger.error(f"Lazy Sync Error: {e}")
        st.session_state.credits_synced = True

    # 6. SIDEBAR NAVIGATION
    render_sidebar(system_mode)

    # 7. EXECUTE CONTROLLER
    current_page = st.session_state.app_mode
    
    # --- ROUTE MAP ---
    route_map = {
        "login":     ("ui_login", "render_login_page"),
        "legal":     ("ui_legal", "render_legal_page"),
        "admin":     ("ui_admin", "render_admin_page"),
        "splash":    ("ui_splash", "render_splash_page"), 
        "main":      ("ui_main", "render_store_page"),
        "workspace": ("ui_main", "render_workspace_page"),
        "receipt":   ("ui_main", "render_receipt_page"),
        "review":    ("ui_main", "render_review_page"),
        "legacy":    ("ui_legacy", "render_legacy_page"),
        "heirloom":  ("ui_heirloom", "render_dashboard"),
        "blog":      ("ui_blog", "render_blog_page")
    }

    if current_page in route_map:
        module_name, function_name = route_map[current_page]
        mod = get_module(module_name)
        if mod and hasattr(mod, function_name):
            getattr(mod, function_name)()
        else:
            st.error(f"404: Route {current_page} not found.")
            st.session_state.app_mode = "splash"
            st.rerun()
    else:
        st.session_state.app_mode = "splash"
        st.rerun()

def render_sidebar(mode):
    with st.sidebar:
        st.header("VerbaPost" if mode == "utility" else "The Archive")
        
        if st.session_state.get("authenticated"):
            # --- NAVIGATION BUTTONS ---
            if mode == "utility":
                if st.button("✉️ Letter Store", use_container_width=True):
                    # SAFETY: Ensure mode is sticky in Session AND URL
                    st.session_state.system_mode = "utility"
                    st.query_params["mode"] = "utility" # <--- FIXED: Updates URL
                    st.session_state.app_mode = "main"
                    st.rerun()
                
                if st.button("🔄 Switch to Family Archive", use_container_width=True):
                    st.session_state.system_mode = "archive"
                    st.query_params["mode"] = "archive"
                    st.session_state.app_mode = "heirloom"
                    st.rerun()
                    
            elif mode == "archive":
                if st.button("📚 Family Archive", use_container_width=True):
                    st.session_state.app_mode = "heirloom"; st.rerun()
                
                if st.button("🔄 Switch to Letter Store", use_container_width=True):
                    # SAFETY: Update Session AND URL
                    st.session_state.system_mode = "utility"
                    st.query_params["mode"] = "utility" # <--- FIXED: Updates URL
                    st.session_state.app_mode = "main"
                    st.rerun()

        st.markdown("---")

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
                st.session_state.credits_synced = False
                st.session_state.app_mode = "splash"
                st.rerun()
            
            admin_email = None
            if secrets_manager: admin_email = secrets_manager.get_secret("admin.email")
            if not admin_email and hasattr(st, "secrets") and "admin" in st.secrets: 
                admin_email = st.secrets["admin"]["email"]
            
            if user_email and admin_email and user_email.strip() == admin_email.strip():
                st.divider()
                if st.button("⚡ Admin Console", use_container_width=True):
                    st.session_state.app_mode = "admin"; st.rerun()

def handle_payment_return(session_id):
    """
    Handles Stripe Callback with TYPE SAFE DRAFT RECOVERY & FULFILLMENT.
    """
    db = get_module("database")
    pay_eng = get_module("payment_engine")
    
    # Preserve current mode so clearing params doesn't reset us to Archive
    current_mode = st.session_state.get("system_mode", "archive")

    # 1. IDEMPOTENCY CHECK
    if db and hasattr(db, "is_fulfillment_recorded"):
        if db.is_fulfillment_recorded(session_id):
             logger.info(f"Payment {session_id} already recorded.")
             if st.session_state.get("system_mode") == "utility":
                 st.session_state.app_mode = "receipt"
             else:
                 st.session_state.app_mode = "heirloom"
             st.query_params.clear()
             st.query_params["mode"] = current_mode # Restore Mode
             return

    # 2. RECORD FULFILLMENT ATTEMPT
    is_new = True
    if db and hasattr(db, "record_stripe_fulfillment"):
        is_new = db.record_stripe_fulfillment(session_id)
        if not is_new: return

    if pay_eng:
        user_email = st.session_state.get("user_email")
        try:
            # 3. VERIFY SESSION
            raw_obj = pay_eng.verify_session(session_id)
            
            if raw_obj:
                # SUCCESS LOGIC
                if not user_email and hasattr(raw_obj, 'customer_email'):
                    user_email = raw_obj.customer_email
                
                st.session_state.authenticated = True
                st.session_state.user_email = user_email

                # Audit Log
                if db and hasattr(db, "save_audit_log"):
                    try:
                        db.save_audit_log({
                            "user_email": user_email or "Unknown",
                            "event_type": "PAYMENT_SUCCESS",
                            "description": "Stripe Payment Verified",
                            "stripe_session_id": session_id,
                            "details": f"Ref: {getattr(raw_obj, 'client_reference_id', 'N/A')}"
                        })
                    except: pass

                meta_id = None
                promo_code = None
                
                ref_id = getattr(raw_obj, 'client_reference_id', '')
                if hasattr(raw_obj, 'metadata') and raw_obj.metadata:
                    meta_id = raw_obj.metadata.get('draft_id', '')
                    promo_code = raw_obj.metadata.get('promo_code', '') # Extract Promo

                # A. Subscription
                if (ref_id == "SUBSCRIPTION_INIT") or (meta_id == "SUBSCRIPTION_INIT"):
                    if db and user_email: 
                        # REFILLED via update_subscription_state internally if we were strictly using payment_engine logic
                        # But for safety here we do explicit updates
                        db.update_user_credits(user_email, 4)
                        if hasattr(raw_obj, 'subscription'):
                            # Use new function to sync subscription state immediately
                            sub_id = raw_obj.subscription
                            # Note: To get end date we'd need to query subscription object again, 
                            # but check_subscription_status will catch it on next login anyway.
                            # Just storing ID is good for now.
                            try:
                                # Quick update for ID
                                with db.get_db_session() as s:
                                    p = s.query(db.UserProfile).filter_by(email=user_email).first()
                                    if p: p.stripe_subscription_id = sub_id
                            except: pass

                    # Log Promo Usage for Subscriptions
                    if promo_code and db:
                        db.record_promo_usage(promo_code, user_email)

                    # Send Welcome Email
                    if email_engine:
                        try:
                            email_engine.send_email(
                                to_email=user_email,
                                subject="Welcome to VerbaPost Archive",
                                html_content="<h3>Subscription Active!</h3><p>Your 4 credits have been added.</p>"
                            )
                        except Exception as e:
                            logger.error(f"Welcome Email Failed: {e}")

                    st.query_params.clear()
                    st.query_params["mode"] = "archive" # Restore Mode
                    st.session_state.system_mode = "archive"
                    st.session_state.app_mode = "heirloom"
                    st.rerun()
                    return

                # B. Single Letter (Utility)
                target_draft_id = None
                if meta_id:
                     target_draft_id = str(meta_id) # FIRST FORCE STRING
                
                # --- AGGRESSIVE RECOVERY LOGIC (Fix for Promo Code 404s) ---
                if not target_draft_id and db and user_email:
                    with db.get_db_session() as s:
                         # 1. Try 'Pending Payment' first
                         fallback = s.query(db.LetterDraft).filter(
                             db.LetterDraft.user_email == user_email,
                             db.LetterDraft.status == "Pending Payment"
                         ).order_by(db.LetterDraft.created_at.desc()).first()
                         
                         # 2. If fails, try ANY draft from last 1 hour
                         if not fallback:
                             cutoff = datetime.utcnow() - timedelta(hours=1)
                             fallback = s.query(db.LetterDraft).filter(
                                 db.LetterDraft.user_email == user_email,
                                 db.LetterDraft.created_at >= cutoff
                             ).order_by(db.LetterDraft.created_at.desc()).first()
                             
                         if fallback:
                             target_draft_id = str(fallback.id) # FORCE STRING AGAIN

                if db and target_draft_id:
                    with db.get_db_session() as s:
                        # FILTER WITH EXPLICIT STRING
                        d = s.query(db.LetterDraft).filter(db.LetterDraft.id == str(target_draft_id)).first()
                        if d:
                            d.status = "Paid/Writing"
                            st.session_state.paid_tier = d.tier
                            st.session_state.locked_tier = d.tier 
                            st.session_state.current_draft_id = str(target_draft_id)
                            
                            # --- FULFILLMENT LOGIC ---
                            tracking_num = None
                            
                            # --- FIX: ROUTE VINTAGE TO MANUAL QUEUE ---
                            if d.tier == "Vintage":
                                # MANUAL QUEUE
                                tracking_num = f"MANUAL_{str(uuid.uuid4())[:8].upper()}"
                                d.status = "Queued (Manual)"
                                d.tracking_number = tracking_num
                                logger.info(f"Paid Vintage Order {target_draft_id} sent to Manual Queue")
                                
                                # 1. NOTIFY ADMIN (NEW)
                                if email_engine:
                                    email_engine.send_admin_alert(
                                        trigger_event="New Vintage Letter (Paid)",
                                        details_html=f"""
                                        <p><strong>User:</strong> {user_email}</p>
                                        <p><strong>Draft ID:</strong> {target_draft_id}</p>
                                        <p><strong>Tracking:</strong> {tracking_num}</p>
                                        """
                                    )
                                
                                # 2. Send "Queued" Receipt to User
                                if email_engine:
                                    try:
                                        email_engine.send_email(
                                            to_email=user_email,
                                            subject=f"VerbaPost Receipt: Order #{target_draft_id}",
                                            html_content=f"<h3>Order Queued</h3><p>Your Vintage letter is in the manual print queue.</p><p>ID: {tracking_num}</p>"
                                        )
                                    except Exception as ex:
                                        logger.error(f"Queued Receipt Failed: {ex}")
                            
                            # --- STANDARD POSTGRID API ---
                            elif mailer and letter_format:
                                try:
                                    # Parse stored JSON strings
                                    to_addr = ast.literal_eval(d.to_addr) if d.to_addr else {}
                                    from_addr = ast.literal_eval(d.from_addr) if d.from_addr else {}
                                    
                                    # Create PDF
                                    pdf_bytes = letter_format.create_pdf(d.content, to_addr, from_addr, tier=d.tier)
                                    
                                    # Send to PostGrid
                                    tracking_num = mailer.send_letter(
                                        pdf_bytes, to_addr, from_addr, 
                                        description=f"Paid Order {target_draft_id}"
                                    )
                                    
                                    if tracking_num:
                                        d.status = "Sent"
                                        d.tracking_number = tracking_num
                                        
                                        # Send "Sent" Receipt
                                        if email_engine:
                                            try:
                                                email_engine.send_email(
                                                    to_email=user_email,
                                                    subject=f"VerbaPost Receipt: Order #{target_draft_id}",
                                                    html_content=f"""
                                                    <h3>Letter Sent Successfully!</h3>
                                                    <p>Your letter has been dispatched to the post office.</p>
                                                    <p><b>Tracking ID:</b> {tracking_num}</p>
                                                    <p>Thank you for using VerbaPost.</p>
                                                    """
                                                )
                                            except Exception as ex:
                                                logger.error(f"Receipt Email Failed: {ex}")
                                    else:
                                        logger.error("Mailing Failed during fulfillment.")
                                        
                                except Exception as fulfillment_err:
                                    logger.error(f"Fulfillment Error: {fulfillment_err}")

                            s.commit() 
                            
                            # RECORD PROMO USAGE FOR SINGLE LETTERS
                            if promo_code:
                                db.record_promo_usage(promo_code, user_email)

                            st.session_state.system_mode = "utility"
                            st.session_state.app_mode = "receipt"
                            st.query_params.clear()
                            st.query_params["mode"] = "utility" # Restore Mode
                            st.rerun()
                            return
                
                # If we absolutely cannot find the draft, go to Heirloom
                st.query_params.clear()
                st.session_state.app_mode = "heirloom"
                st.rerun()

            else:
                # FAILURE CASE
                st.error("⚠️ Payment verification failed or session expired.")
                st.query_params.clear()
                st.query_params["mode"] = current_mode # Restore Mode
                time.sleep(2)
                st.session_state.app_mode = "store"
                st.rerun()

        except Exception as e:
            logger.error(f"Payment Verification Crash: {e}")
            st.query_params.clear()
            st.query_params["mode"] = current_mode # Restore Mode
            st.rerun()

if __name__ == "__main__":
    main()