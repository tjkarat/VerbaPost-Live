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

# --- PAGE: LEGAL ---
def render_legal_page():
    render_hero("Legal Center", "Transparency & Trust")
    tab_tos, tab_privacy = st.tabs(["📜 Terms of Service", "🔒 Privacy Policy"])
    with tab_tos:
        with st.container(border=True):
            st.subheader("1. Service Usage")
            st.write("You agree NOT to use VerbaPost to send threatening, abusive, or illegal content via US Mail.")
            st.subheader("2. Refunds")
            st.write("Once a letter has been processed by our printing partners, it cannot be cancelled.")

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

    # --- STRIPE RETURN HANDLER ---
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

    # --- ROUTING ---
    if st.session_state.app_mode == "legal": render_legal_page(); return

    # --- AUTH FLOWS (Omitted for brevity in this final printout) ---
    if st.session_state.app_mode == "forgot_password":
        render_hero("Recovery", "Reset Password")
        # ... logic ...
        return

    if st.session_state.app_mode == "verify_reset":
        render_hero("Verify", "Check Email")
        # ... logic ...
        return

    if st.session_state.app_mode == "login":
        st.markdown("<h1 style='text-align: center;'>Welcome</h1>", unsafe_allow_html=True)
        # ... login form logic ...
        return

    # --- 4. SIDEBAR & ADMIN (Logic moved to main flow for stability) ---
    
    # Prepare email variables for comparison
    u_email = st.session_state.get("user_email", "")
    if not u_email and st.session_state.get("user") and hasattr(st.session_state.user, 'user'):
        u_email = st.session_state.user.user.email
    
    admin_target = st.secrets.get("admin", {}).get("email", "MISSING").strip().lower()
    user_clean = u_email.strip().lower() if u_email else ""

    # --- 5. THE STORE ---
    if st.session_state.app_mode == "store":
        render_hero("Select Service", "Choose your letter type.")
        
        # --- TEMP DEBUGGER: Admin Status (Displayed in the main card) ---
        if user_clean and user_clean != admin_target:
            st.error("❌ Admin Check Failed.")
            st.code(f"You:   '{user_clean}'\nAdmin: '{admin_target}'")
        elif user_clean and user_clean == admin_target:
             st.success("✅ Admin Access Granted!")
             
        c1, c2 = st.columns([2, 1])
        with c1:
            with st.container(border=True):
                st.subheader("1. Customize")
                tier = st.radio("Tier", ["⚡ Standard ($2.99)", "🏺 Heirloom ($5.99)", "🏛️ Civic ($6.99)"])
                lang = st.selectbox("Language", ["English", "Spanish", "French"])
        with c2:
            with st.container(border=True):
                st.subheader("2. Checkout")
                price = 2.99
                if "Heirloom" in tier: price = 5.99
                if "Civic" in tier: price = 6.99
                st.metric("Total", f"${price}")
                
                promo_code = st.text_input("Promo Code (Optional)")
                valid_promo = False
                
                if promo_code:
                    if promo_engine.validate_code(promo_code):
                        valid_promo = True
                        price = 0.00
                        st.success("✅ Code Applied! Total: $0.00")
                    else:
                        st.error("❌ Invalid or Expired Code")
                
                st.info("⚠️ **Note:** Payment opens in a new tab.")
                
                if st.button(f"Pay ${price} & Start", type="primary", use_container_width=True):
                    user = st.session_state.get("user_email", "guest")
                    database.save_draft(user, "", tier, price)
                    safe_tier = tier.split()[1]
                    link = f"{YOUR_APP_URL}?tier={safe_tier}&lang={lang}"
                    url, sess_id = payment_engine.create_checkout_session(tier, int(price*100), link, YOUR_APP_URL)
                    if url: st.link_button("Click here to Pay", url, type="primary", use_container_width=True)
                    else: st.error("Payment System Offline")

    # --- 6. THE WORKSPACE / REVIEW / ETC. ---
    elif st.session_state.app_mode in ["workspace", "review", "finalizing"]:
        st.write("Final logic flow here...")