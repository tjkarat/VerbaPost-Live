import streamlit as st
import time

# --- CONFIG ---
st.set_page_config(page_title="VerbaPost", page_icon="📮", layout="centered", initial_sidebar_state="expanded")
st.markdown("""<style>[data-testid="stSidebar"] {display: block !important;} .main .block-container {padding-top: 2rem;}</style>""", unsafe_allow_html=True)

# --- IMPORTS ---
try: import ui_main, ui_login, ui_admin, ui_legal, ui_legacy, payment_engine, audit_engine, analytics, seo_injector
except ImportError as e: st.error(f"System Error: {e}"); st.stop()
try: import ui_splash
except: ui_splash = None

# --- INIT ---
if analytics and hasattr(analytics, 'inject_ga'): analytics.inject_ga()
if seo_injector and hasattr(seo_injector, 'inject_meta_tags'): seo_injector.inject_meta_tags()
if 'authenticated' not in st.session_state: st.session_state.authenticated = False

# --- GLOBAL SIDEBAR ---
# Ensure Admin Console is reachable
if hasattr(ui_main, 'render_sidebar'): ui_main.render_sidebar()

# --- PAYMENT HANDLER ---
if "session_id" in st.query_params:
    sid = st.query_params["session_id"]
    with st.spinner("Verifying..."):
        status, email = payment_engine.verify_session(sid)
        if status == "paid":
            st.success("✅ Payment Confirmed!"); st.session_state.paid_order = True
            
            if st.session_state.get("locked_tier") == "Legacy": 
                st.query_params["view"] = "legacy"
            else: 
                st.session_state.app_mode = "workspace"
                if "view" in st.query_params: del st.query_params["view"]
            
            if audit_engine: audit_engine.log_event(email, "PAYMENT_SUCCESS", sid)
            time.sleep(0.5); st.rerun()
        else:
            st.error("Payment failed."); st.query_params.clear()

# --- ROUTING ---
view = st.query_params.get("view")

if view == "admin": ui_admin.show_admin()
elif view == "legacy": ui_legacy.render_legacy_page()
elif view == "legal": ui_legal.render_legal()
elif view == "login": st.session_state.auth_view = "login"; ui_login.render_login()
elif view == "signup": st.session_state.auth_view = "signup"; ui_login.render_login()
else:
    # Main App vs Splash logic
    if st.session_state.authenticated or st.session_state.get("paid_order"):
        if st.session_state.get("app_mode") == "splash": st.session_state.app_mode = "store"
        ui_main.render_main()
    else:
        if ui_splash: ui_splash.render_splash()