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

# --- ROBUST IMPORTS ---
# We use generic Exception catching to prevent "Torch" or "AI" crashes 
# from breaking the entire router.
try: import ui_splash
except Exception as e: ui_splash = None; logger.error(f"Splash Import Error: {e}")

try: import ui_login
except Exception as e: ui_login = None; logger.error(f"Login Import Error: {e}")

try: import ui_main
except Exception as e: ui_main = None; logger.error(f"Main UI Import Error: {e}")

try: import ui_admin
except Exception as e: ui_admin = None; logger.error(f"Admin Import Error: {e}")

try: import ui_legal
except Exception as e: ui_legal = None; logger.error(f"Legal Import Error: {e}")

try: import ui_legacy
except Exception as e: ui_legacy = None; logger.error(f"Legacy Import Error: {e}")

try: import payment_engine
except Exception as e: payment_engine = None; logger.error(f"Payment Engine Import Error: {e}")

try: import auth_engine
except Exception as e: auth_engine = None; logger.error(f"Auth Engine Import Error: {e}")

try: import audit_engine
except Exception as e: audit_engine = None; logger.error(f"Audit Engine Import Error: {e}")

try: import seo_injector
except Exception as e: seo_injector = None; logger.error(f"SEO Import Error: {e}")

try: import email_engine
except Exception as e: email_engine = None; logger.error(f"Email Engine Import Error: {e}")

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
    .stStatusWidget {border: 1px solid #e0e0e0; border-radius: 8px; padding: 15px;}
</style>
""", unsafe_allow_html=True)

# --- MAIN APP LOGIC ---
def main():
    if seo_injector: seo_injector.inject_meta()

    # 1. HANDLE PAYMENT RETURNS (STRIPE REDIRECT)
    params = st.query_params
    if "session_id" in params:
        session_id = params["session_id"]
        
        # UI Container for Verification Status
        with st.container():
            st.markdown("### 🔐 Verifying Order...")
            
            # ATTEMPT VERIFICATION
            status = "error"
            if payment_engine:
                try:
                    status = payment_engine.verify_session(session_id)
                except Exception as e:
                    logger.error(f"Verify Crash: {e}")
            
            # SUCCESS HANDLER
            if status == "paid":
                st.success("✅ Payment Confirmed!")
                st.session_state.paid_success = True
                
                # A. Get User
                current_user = st.session_state.get("user_email", "guest")
                if auth_engine and st.session_state.get("authenticated"):
                    current_user = st.session_state.get("user_email")

                # B. Audit Log
                if audit_engine:
                    audit_engine.log_event("PAYMENT_SUCCESS", current_user, f"Session: {session_id}")

                # C. Generate Mock Tracking (Placeholder)
                import random
                track_num = f"94055{random.randint(10000000,99999999)}"
                st.session_state.tracking_number = track_num

                # D. SEND EMAIL (CRITICAL FIX)
                if email_engine:
                    # Heuristic: If we are on splash but paid $15.99, it's Legacy.
                    # Ideally, we read this from the Stripe Session metadata, but this works for now.
                    tier_sold = "Standard"
                    if st.session_state.get("last_mode") == "legacy":
                        tier_sold = "Legacy"
                    
                    email_engine.send_confirmation(current_user, track_num, tier=tier_sold)

                # E. ROUTE USER
                time.sleep(1)
                st.query_params.clear()
                
                # If state was wiped, guess based on Context or Default to Workspace
                if st.session_state.get("last_mode") == "legacy":
                    st.session_state.app_mode = "legacy"
                else:
                    # Default for standard users
                    st.session_state.app_mode = "workspace"
                
                st.rerun()

            # PENDING/PROCESSING HANDLER
            elif status == "open":
                st.info("⏳ Payment is processing... Please wait.")
                time.sleep(2)
                st.rerun()

            # FAILURE/RACE CONDITION HANDLER
            else:
                st.warning("⚠️ Could not verify instantly.")
                st.markdown("This happens if the bank connection is slow. Your money is safe.")
                
                c1, c2 = st.columns(2)
                with c1:
                    # The Magic Button: Re-runs the check without full page reload
                    if st.button("🔄 Click to Verify Again", type="primary"):
                        st.rerun()
                with c2:
                    st.link_button("💬 Support", "mailto:support@verbapost.com")

                # Stop execution here so we don't render the Splash page underneath the error
                st.stop()

    # 2. PASSWORD RESET
    elif "type" in params and params["type"] == "recovery":
        st.session_state.app_mode = "login"

    # 3. INIT STATE (If wiped by Torch crash)
    if "app_mode" not in st.session_state:
        st.session_state.app_mode = "splash"
    
    # 4. SIDEBAR NAVIGATION
    with st.sidebar:
        st.header("VerbaPost System")
        st.markdown("---")
        if st.button("🏠 Home / Splash", use_container_width=True):
            st.session_state.app_mode = "splash"
            st.rerun()
        st.markdown("### 🛠️ Administration")
        if st.button("🔐 Admin Console", key="sidebar_admin_btn", use_container_width=True):
            st.session_state.app_mode = "admin"
            st.rerun()
        st.markdown("---")
        st.caption(f"v3.3.4 | {st.session_state.app_mode}")

    # 5. ROUTING SWITCHBOARD
    mode = st.session_state.app_mode
    
    if mode == "splash":
        if ui_splash: ui_splash.render_splash_page()
    elif mode == "login":
        if ui_login: ui_login.render_login_page()
    elif mode == "legacy":
        if ui_legacy: ui_legacy.render_legacy_page()
    elif mode == "legal":
        if ui_legal: ui_legal.render_legal_page()
    elif mode == "admin":
        if ui_admin: ui_admin.render_admin_page()
    elif mode in ["store", "workspace", "review"]:
        if ui_main: ui_main.render_main()
    else:
        # Fallback if state is weird
        if ui_splash: ui_splash.render_splash_page()

if __name__ == "__main__":
    main()