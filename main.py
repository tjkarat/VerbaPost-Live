import streamlit as st
import time
import sys
import logging

# --- CONFIG ---
# CHANGED: initial_sidebar_state set to "collapsed" for cleaner mobile entry
st.set_page_config(page_title="VerbaPost", page_icon="📮", layout="centered", initial_sidebar_state="collapsed")
st.markdown("""<style>[data-testid="stSidebar"] {display: block !important;} .main .block-container {padding-top: 2rem;}</style>""", unsafe_allow_html=True)

# --- SAFE IMPORTER ---
def safe_import(module_name):
    try:
        __import__(module_name)
        return sys.modules[module_name]
    except ImportError:
        return None
    except Exception as e:
        st.error(f"❌ Critical Error loading '{module_name}': {e}")
        return None

# Load Modules
ui_main = safe_import("ui_main")
ui_login = safe_import("ui_login")
ui_admin = safe_import("ui_admin")
ui_legal = safe_import("ui_legal")
ui_legacy = safe_import("ui_legacy")
ui_splash = safe_import("ui_splash")
payment_engine = safe_import("payment_engine")
audit_engine = safe_import("audit_engine")
analytics = safe_import("analytics")
seo_injector = safe_import("seo_injector")

# --- INIT ---
if 'authenticated' not in st.session_state: st.session_state.authenticated = False
if 'app_mode' not in st.session_state: st.session_state.app_mode = "splash"

# Analytics/SEO
if analytics and hasattr(analytics, 'inject_ga'): 
    try: analytics.inject_ga()
    except: pass
if seo_injector and hasattr(seo_injector, 'inject_meta_tags'): 
    try: seo_injector.inject_meta_tags()
    except: pass

# --- GLOBAL SIDEBAR ---
# Only render sidebar content if we are NOT in splash mode (optional polish)
# or just render it standardly.
if ui_main and hasattr(ui_main, 'render_sidebar'):
    try: ui_main.render_sidebar()
    except Exception: pass

# --- PAYMENT RETURN ---
if "session_id" in st.query_params:
    sid = st.query_params["session_id"]
    with st.spinner("Verifying..."):
        status = "failed"
        email = None
        if payment_engine:
            try: status, email = payment_engine.verify_session(sid)
            except: pass
        
        if status == "paid":
            st.success("✅ Payment Successful!")
            st.session_state.paid_order = True
            
            if audit_engine: 
                try: audit_engine.log_event(email, "PAYMENT_SUCCESS", sid)
                except: pass
            
            if st.session_state.get("locked_tier") == "Legacy":
                st.query_params["view"] = "legacy"
            else:
                st.session_state.app_mode = "workspace"
            
            st.query_params.clear()
            time.sleep(0.5)
            st.rerun()
        else:
            st.error("Payment Failed.")
            st.query_params.clear()

# --- ROUTER ---
view = st.query_params.get("view")

if view == "admin" and ui_admin: ui_admin.show_admin()
elif view == "legacy" and ui_legacy: ui_legacy.render_legacy_page()
elif view == "legal" and ui_legal: ui_legal.render_legal()
elif view in ["login", "signup"] and ui_login:
    st.session_state.auth_view = view
    ui_login.render_login()
else:
    # Main App Flow
    if st.session_state.authenticated or st.session_state.get("paid_order"):
        if st.session_state.app_mode == "splash": st.session_state.app_mode = "store"
        if ui_main: ui_main.render_main()
    else:
        if ui_splash: ui_splash.render_splash()