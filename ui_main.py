import streamlit as st
from streamlit_drawable_canvas import st_canvas
import os
from datetime import datetime
import re

# --- STANDARD IMPORTS ---
import ai_engine 
import database
import letter_format
import mailer
import payment_engine
import analytics
import promo_engine
import auth_ui # NEW: Router for all authentication views

# --- CONFIG ---
YOUR_APP_URL = "https://verbapost.streamlit.app/" 
COST_STANDARD = 2.99
COST_HEIRLOOM = 5.99
COST_CIVIC = 6.99

# --- HELPER: SUPABASE ---
@st.cache_resource
def get_supabase():
    from supabase import create_client
    try:
        if "SUPABASE_URL" not in st.secrets: return None
        return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except: return None

def reset_app():
    st.session_state.app_mode = "splash" 
    st.session_state.audio_path = None
    st.session_state.transcribed_text = ""
    st.session_state.payment_complete = False
    st.session_state.stripe_url = None
    st.session_state.sig_data = None
    st.query_params.clear()

def render_hero(title, subtitle):
    st.markdown(f"""<div class="hero-banner"><div class="hero-title">{title}</div><div class="hero-subtitle">{subtitle}</div></div>""", unsafe_allow_html=True)

# --- AUTH CALLBACKS (For stabilized button logic) ---

def login_callback(email, password):
    sb = get_supabase()
    if not sb: st.error("❌ Connection Failed. Check Secrets."); return
    try:
        res = sb.auth.sign_in_with_password({"email": email, "password": password})
        st.session_state.user = res
        st.session_state.user_email = email 
        reset_app()
        st.session_state.app_mode = "store"
        st.rerun()
    except Exception as e: st.error(f"Login failed: {e}")

def signup_callback(email, password):
    sb = get_supabase()
    if not sb: st.error("❌ Connection Failed. Check Secrets."); return
    try:
        sb.auth.sign_up({"email": email, "password": password})
        st.success("Check email for confirmation.")
    except Exception as e: st.error(f"Signup failed: {e}")

# --- PAGE: LEGAL ---
def render_legal_page():
    render_hero("Legal Center", "Transparency & Trust")
    tab_tos, tab_privacy = st.tabs(["📜 Terms of Service", "🔒 Privacy Policy"])
    with tab_tos:
        with st.container(border=True):
            st.subheader("1. Service Usage")
            st.write("You agree NOT to use VerbaPost to send threatening, abusive, or illegal content via US Mail.")
    with tab_privacy:
        with st.container(border=True):
            st.subheader("Data Handling")
            st.write("We process your voice data solely for transcription.")

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("← Return to Home", type="primary", use_container_width=True):
        st.session_state.app_mode = "splash"
        st.rerun()

# --- MAIN LOGIC ---
def show_main_app():
    if 'analytics' in globals(): analytics.inject_ga()

    # Defaults
    if "app_mode" not in st.session_state: st.session_state.app_mode = "store"
    if "processed_ids" not in st.session_state: st.session_state.processed_ids = []

    # --- 1. STRIPE RETURN HANDLER ---
    qp = st.query_params
    if "session_id" in qp:
        session_id = qp["session_id"]
        if session_id not in st.session_state.processed_ids:
            if payment_engine.check_payment_status(session_id):
                st.session_state.payment_complete = True
                st.session_state.processed_ids.append(session_id)
                st.toast("✅ Payment Confirmed!")
                
                if "tier" in qp: st.session_state.locked_tier = qp["tier"]
                if "lang" in qp: st.session_state.selected_language = qp["lang"]
                
                st.session_state.app_mode = "workspace"
                st.query_params.clear()
                st.rerun()
            else:
                st.error("Payment verification failed.")
        else:
            if st.session_state.payment_complete: st.session_state.app_mode = "workspace"

    # --- 2. ROUTING ---
    if st.session_state.app_mode == "legal": render_legal_page(); return

    if st.session_state.app_mode in ["forgot_password", "verify_reset"]:
        # Calls the router for non-main auth views
        auth_ui.route_auth_page(st.session_state.app_mode)
        return

    # --- 3. LOGIN PAGE (Stabilized) ---
    if st.session_state.app_mode == "login":
        st.markdown("<h1 style='text-align: center;'>Welcome Back</h1>", unsafe_allow_html=True)
        
        # Simpler layout to avoid indentation errors
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            with st.container(border=True):
                email = st.text_input("Email Address", key="login_email")
                password = st.text_input("Password", type="password", key="login_password")
                
                # Buttons now use Callbacks for stability
                st.button("Log In", type="primary", use_container_width=True, 
                          on_click=login_callback, args=(st.session_state.login_email, st.session_state.login_password))
                st.button("Sign Up", use_container_width=True, 
                          on_click=signup_callback, args=(st.session_state.login_email, st.session_state.login_password))
                
                if st.button("Forgot Password?", type="secondary", use_container_width=True):
                    st.session_state.app_mode = "forgot_password"
                    st.rerun()

        if st.button("← Back"): st.session_state.app_mode = "splash"; st.rerun()
        return

    # --- 4. SIDEBAR & ADMIN ---
    with st.sidebar:
        if st.button("Reset App"): reset_app(); st.rerun()
        if st.session_state.get("user"):
            st.divider()
            u_email = st.session_state.get("user_email", "")
            if not u_email and hasattr(st.session_state.user, 'user'): u_email = st.session_state.user.user.email
            st.caption(f"Logged in: {u_email}")
            
            # --- ADMIN CHECK ---
            admin_target = st.secrets.get("admin", {}).get("email", "").strip().lower()
            user_clean = u_email.strip().lower() if u_email else ""

            if user_clean and admin_target and user_clean == admin_target:
                st.divider()
                st.success("Admin Access Granted")
                with st.expander("🔐 Console", expanded=True):
                    if st.button("Generate Code"):
                        code = promo_engine.generate_code()
                        st.info(f"Code: `{code}`")
                    if get_supabase(): st.write("DB: Online 🟢")
                    else: st.error("DB: Offline 🔴")
            
            if st.button("Legal / Terms"): st.session_state.app_mode = "legal"; st.rerun()
            if st.button("Sign Out"): st.session_state.pop("user", None); reset_app(); st.session_state.app_mode = "splash"; st.rerun()

    # --- 5. THE STORE ---
    if st.session_state.app_mode == "store":
        render_hero("Select Service", "Choose your letter type.")
        # ... (Rest of store logic is assumed correct) ...
        pass # Placeholder for brevity

    # --- 6. THE WORKSPACE ---
    elif st.session_state.app_mode == "workspace":
        render_hero("Compose", "Dictate & Send")
        # ... (Rest of workspace logic is assumed correct) ...
        pass # Placeholder for brevity

    # --- 7. REVIEW ---
    elif st.session_state.app_mode == "review":
        render_hero("Review", "Finalize Letter")
        # ... (Rest of review logic is assumed correct) ...
        pass # Placeholder for brevity