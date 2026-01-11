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
    page_title="VerbaPost | Client Retention", 
    page_icon="⚖️", 
    layout="centered",
    initial_sidebar_state="collapsed",
    menu_items={
        'Get Help': 'mailto:support@verbapost.com',
        'About': "# VerbaPost \n Legacy retention for estate planning."
    }
)

# --- CSS STYLING ---
st.markdown("""
<style>
    [data-testid="stSidebarNav"] {display: none !important;}
    .block-container {padding-top: 1rem !important;}
    button[kind="primary"] {
        background-color: #0f172a !important; /* Navy Blue for Legal/Trust */
        border-color: #0f172a !important;
        color: white !important; 
        font-weight: 600;
    }
    .stDeployButton {display:none;}
    /* HIDE STREAMLIT HEADER ANCHORS */
    a.anchor-link {display: none !important;}
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
            "ui_partner": "ui_partner",
            "payment_engine": "payment_engine",
            "database": "database",
            "analytics": "analytics",
            "auth_engine": "auth_engine",
            "storage_engine": "storage_engine",
            "seo_injector": "seo_injector"
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

# --- LOAD SEO INJECTOR ---
try: import seo_injector
except ImportError: seo_injector = None

# --- HELPER: PARTNER CHECK (B2B Logic) ---
def check_partner_status(email):
    """Checks if the user is a Lawyer/Partner via Database."""
    if not email: return False
    db = get_module("database")
    if db and hasattr(db, "get_user_profile"):
        try:
            profile = db.get_user_profile(email)
            if isinstance(profile, dict): return profile.get("is_partner", False)
            return getattr(profile, "is_partner", False)
        except Exception as e:
            logger.error(f"Partner Check Error: {e}")
            return False
    return False

# --- MAIN LOGIC ---
def main():
    # 0. PLAYER ROUTE (Secure Audio Playback)
    if "play" in st.query_params:
        audio_ref = st.query_params["play"]
        storage = get_module("storage_engine")
        
        if audio_ref and storage:
            try:
                signed_url = storage.get_signed_url(audio_ref)
                if signed_url:
                    st.markdown("<br><br>", unsafe_allow_html=True)
                    st.title("🎧 Listen to Story")
                    st.caption("VerbaPost Family Archive")
                    st.audio(signed_url)
                    st.divider()
                    if st.button("🏠 Go to VerbaPost Home", use_container_width=True):
                        st.query_params.clear()
                        st.rerun()
                    return
                else:
                    st.error("Audio file unavailable or expired.")
            except Exception as e:
                logger.error(f"Player Error: {e}")
                st.error("Could not load audio player.")
        
        if st.button("Back"):
             st.query_params.clear()
             st.rerun()
        return

    # --- START NORMAL APP FLOW ---

    # 1. AUTH LISTENER
    if auth_listener:
        auth_listener.listen_for_oauth()

    if "type" in st.query_params and st.query_params["type"] == "oauth_callback":
        token = st.query_params.get("access_token")
        if token:
            auth_eng = get_module("auth_engine")
            if auth_eng:
                with st.spinner("Verifying Account..."):
                    email, err = auth_eng.verify_oauth_token(token)
                    if email:
                        st.session_state.authenticated = True
                        st.session_state.user_email = email
                        
                        # --- FIX: IMMEDIATE PARTNER CHECK ---
                        # Determine role immediately after auth to force correct routing
                        is_partner = check_partner_status(email)
                        st.session_state.is_partner = is_partner
                        
                        if is_partner:
                            st.session_state.app_mode = "partner"
                            st.session_state.system_mode = "partner"
                        else:
                            # Default to Heirloom for B2C, or redirect_to if set
                            target = st.session_state.get("redirect_to", "heirloom")
                            st.session_state.app_mode = target

                        st.query_params.clear()
                        st.rerun()
                    else:
                        st.error(f"Authentication Failed: {err}")

    # 2. ROLE & MODE DETECTION
    if st.session_state.get("authenticated") and "is_partner" not in st.session_state:
        st.session_state.is_partner = check_partner_status(st.session_state.user_email)

    # 3. SEO INJECTION (FIXED)
    current_system_mode = "archive"
    if st.session_state.get("is_partner"):
        current_system_mode = "partner"
    else:
        current_system_mode = st.query_params.get("mode", "archive").lower()
    
    st.session_state.system_mode = current_system_mode
    
    # CALL THE FIXED INJECTOR
    if seo_injector: 
        seo_injector.inject_meta_tags(current_system_mode)
    
    analytics = get_module("analytics")
    if analytics: analytics.inject_ga()

    # 4. Handle Stripe/Payment Returns
    if "session_id" in st.query_params:
        handle_payment_return(st.query_params["session_id"])

    # 5. ROUTING LOGIC
    if "app_mode" not in st.session_state:
        nav_target = st.query_params.get("nav")
        
        # --- EXPLICIT PARTNER ROUTING ---
        if nav_target == "partner":
            if st.session_state.get("authenticated"):
                st.session_state.app_mode = "partner"
            else:
                st.session_state.app_mode = "login"
                st.session_state.redirect_to = "partner"
        
        # --- ADMIN ---
        elif nav_target == "admin":
             st.session_state.app_mode = "admin"
             
        # --- LOGIN ---
        elif nav_target == "login":
            st.session_state.app_mode = "login"
            if st.session_state.system_mode == "archive": st.session_state.redirect_to = "heirloom"
            elif st.session_state.system_mode == "utility": st.session_state.redirect_to = "main"
            else: st.session_state.redirect_to = "partner"

        # --- HEIRLOOM (B2C) ---
        elif nav_target == "heirloom":
            if st.session_state.get("authenticated"): st.session_state.app_mode = "heirloom"
            else:
                st.session_state.app_mode = "login"
                st.session_state.redirect_to = "heirloom"

        # --- STORE (B2C) ---
        elif nav_target == "store":
            if st.session_state.get("authenticated"): st.session_state.app_mode = "main"
            else:
                st.session_state.app_mode = "login"
                st.session_state.redirect_to = "main"

        # --- OTHER ---
        elif nav_target == "legal": st.session_state.app_mode = "legal"
        elif nav_target == "blog": st.session_state.app_mode = "blog"

        # --- DEFAULT FALLBACK ---
        elif st.session_state.get("is_partner"):
             st.session_state.app_mode = "partner"
        else:
             st.session_state.app_mode = "splash"
            
    # 6. LAZY SUBSCRIPTION CHECK
    if st.session_state.get("authenticated") and not st.session_state.get("is_partner") and not st.session_state.get("credits_synced"):
        pay_eng = get_module("payment_engine")
        user_email = st.session_state.get("user_email")
        if pay_eng and user_email:
            try:
                if pay_eng.check_subscription_status(user_email):
                    st.toast("🔄 Monthly Credits Refilled!")
            except Exception as e:
                logger.error(f"Lazy Sync Error: {e}")
        st.session_state.credits_synced = True

    # 7. SIDEBAR NAVIGATION
    if not st.session_state.get("is_partner"):
        render_sidebar(st.session_state.system_mode)

    # 8. EXECUTE CONTROLLER
    current_page = st.session_state.app_mode
    
    route_map = {
        "login":     ("ui_login", "render_login_page"),
        "legal":     ("ui_legal", "render_legal_page"),
        "admin":     ("ui_admin", "render_admin_page"),
        "splash":    ("ui_splash", "render_splash_page"), 
        
        # B2B Route
        "partner":   ("ui_partner", "render_dashboard"),

        # B2C Routes
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
            if current_page == "partner":
                 st.info("🚧 Partner Portal is initializing...")
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
            if mode == "utility":
                if st.button("✉️ Letter Store", use_container_width=True):
                    st.session_state.system_mode = "utility"
                    st.query_params["mode"] = "utility"
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
                    st.session_state.system_mode = "utility"
                    st.query_params["mode"] = "utility"
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
                auth_eng = get_module("auth_engine")
                if auth_eng and hasattr(auth_eng, "sign_out"): auth_eng.sign_out()
                
                keys_to_clear = ["authenticated", "user_email", "credits_synced", "user_profile", "is_partner"]
                for key in keys_to_clear:
                    if key in st.session_state: del st.session_state[key]
                
                st.query_params.clear()
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
    db = get_module("database")
    pay_eng = get_module("payment_engine")
    current_mode = st.session_state.get("system_mode", "archive")

    if db and hasattr(db, "is_fulfillment_recorded"):
        if db.is_fulfillment_recorded(session_id):
             if st.session_state.get("system_mode") == "utility":
                 st.session_state.app_mode = "receipt"
             else:
                 st.session_state.app_mode = "heirloom"
             st.query_params.clear()
             st.query_params["mode"] = current_mode
             return

    is_new = True
    if db and hasattr(db, "record_stripe_fulfillment"):
        is_new = db.record_stripe_fulfillment(session_id)
        if not is_new: return

    if pay_eng:
        user_email = st.session_state.get("user_email")
        try:
            raw_obj = pay_eng.verify_session(session_id)
            if raw_obj:
                if not user_email and hasattr(raw_obj, 'customer_email'):
                    user_email = raw_obj.customer_email
                st.session_state.authenticated = True
                st.session_state.user_email = user_email

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
                    promo_code = raw_obj.metadata.get('promo_code', '') 

                if (ref_id == "SUBSCRIPTION_INIT") or (meta_id == "SUBSCRIPTION_INIT"):
                    if db and user_email: 
                        db.update_user_credits(user_email, 4)
                        if hasattr(raw_obj, 'subscription'):
                            try:
                                with db.get_db_session() as s:
                                    p = s.query(db.UserProfile).filter_by(email=user_email).first()
                                    if p: p.stripe_subscription_id = raw_obj.subscription
                            except: pass

                    if promo_code and db: db.record_promo_usage(promo_code, user_email)

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
                    st.query_params["mode"] = "archive"
                    st.session_state.system_mode = "archive"
                    st.session_state.app_mode = "heirloom"
                    st.rerun()
                    return

                target_draft_id = None
                if meta_id: target_draft_id = str(meta_id)
                
                if not target_draft_id and db and user_email:
                    with db.get_db_session() as s:
                         fallback = s.query(db.LetterDraft).filter(
                             db.LetterDraft.user_email == user_email,
                             db.LetterDraft.status == "Pending Payment"
                         ).order_by(db.LetterDraft.created_at.desc()).first()
                         if not fallback:
                             cutoff = datetime.utcnow() - timedelta(hours=1)
                             fallback = s.query(db.LetterDraft).filter(
                                 db.LetterDraft.user_email == user_email,
                                 db.LetterDraft.created_at >= cutoff
                             ).order_by(db.LetterDraft.created_at.desc()).first()
                         if fallback: target_draft_id = str(fallback.id)

                if db and target_draft_id:
                    with db.get_db_session() as s:
                        d = s.query(db.LetterDraft).filter(db.LetterDraft.id == str(target_draft_id)).first()
                        if d:
                            d.status = "Paid/Writing"
                            st.session_state.paid_tier = d.tier
                            st.session_state.locked_tier = d.tier 
                            st.session_state.current_draft_id = str(target_draft_id)
                            
                            tracking_num = None
                            
                            if d.tier == "Vintage":
                                tracking_num = f"MANUAL_{str(uuid.uuid4())[:8].upper()}"
                                d.status = "Queued (Manual)"
                                d.tracking_number = tracking_num
                                if email_engine:
                                    email_engine.send_admin_alert("New Vintage Letter (Paid)", f"Draft: {target_draft_id}")
                            
                            elif mailer and letter_format:
                                try:
                                    to_addr = ast.literal_eval(d.to_addr) if d.to_addr else {}
                                    from_addr = ast.literal_eval(d.from_addr) if d.from_addr else {}
                                    pdf_bytes = letter_format.create_pdf(d.content, to_addr, from_addr, tier=d.tier)
                                    tracking_num = mailer.send_letter(
                                        pdf_bytes, to_addr, from_addr, 
                                        description=f"Paid Order {target_draft_id}"
                                    )
                                    if tracking_num:
                                        d.status = "Sent"
                                        d.tracking_number = tracking_num
                                except Exception as fulfillment_err:
                                    logger.error(f"Fulfillment Error: {fulfillment_err}")

                            s.commit() 
                            if promo_code: db.record_promo_usage(promo_code, user_email)

                            st.session_state.system_mode = "utility"
                            st.session_state.app_mode = "receipt"
                            st.query_params.clear()
                            st.query_params["mode"] = "utility"
                            st.rerun()
                            return
                
                st.query_params.clear()
                st.session_state.app_mode = "heirloom"
                st.rerun()

            else:
                st.error("⚠️ Payment verification failed or session expired.")
                st.query_params.clear()