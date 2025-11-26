import streamlit as st
from streamlit_drawable_canvas import st_canvas
import os
import tempfile
from PIL import Image
import json
import base64
from io import BytesIO

# --- IMPORTS ---
try: import database
except: database = None
try: import ai_engine
except: ai_engine = None
try: import payment_engine
except: payment_engine = None
try: import promo_engine
except: promo_engine = None
try: import civic_engine
except: civic_engine = None
try: import letter_format
except: letter_format = None
try: import mailer
except: mailer = None

# --- CONFIG ---
YOUR_APP_URL = "https://verbapost.streamlit.app/" 

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
    st.markdown(f"""
    <style>#hero-container h1, #hero-container div {{ color: #FFFFFF !important; }}</style>
    <div id="hero-container" style="background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); 
                padding: 40px; border-radius: 15px; text-align: center; 
                margin-bottom: 30px; box-shadow: 0 8px 16px rgba(0,0,0,0.1);">
        <h1 style="margin: 0; font-size: 3rem; font-weight: 700;">{title}</h1>
        <div style="font-size: 1.2rem; opacity: 0.9; margin-top: 10px;">{subtitle}</div>
    </div>
    """, unsafe_allow_html=True)

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
            st.write("We process your voice data solely for transcription. We do not sell your personal information.")

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
            if st.session_state.payment_complete:
                st.session_state.app_mode = "workspace"

    # --- 2. ROUTING ---
    if st.session_state.app_mode == "legal": render_legal_page(); return

    if st.session_state.app_mode == "forgot_password":
        render_hero("Recovery", "Reset Password")
        with st.container(border=True):
            email = st.text_input("Enter your email address")
            if st.button("Send Reset Code", type="primary"):
                sb = get_supabase()
                if sb:
                    try:
                        sb.auth.reset_password_email(email)
                        st.session_state.reset_email = email
                        st.session_state.app_mode = "verify_reset"
                        st.rerun()
                    except Exception as e: st.error(f"Error: {e}")
            if st.button("Cancel"): st.session_state.app_mode = "login"; st.rerun()
        return

    if st.session_state.app_mode == "verify_reset":
        render_hero("Verify", "Check Email")
        with st.container(border=True):
            st.info(f"Code sent to {st.session_state.get('reset_email')}")
            code = st.text_input("Enter Code (6-8 digits)")
            new_pass = st.text_input("New Password", type="password")
            if st.button("Update Password", type="primary"):
                sb = get_supabase()
                try:
                    res = sb.auth.verify_otp({"email": st.session_state.reset_email, "token": code, "type": "recovery"})
                    if res.user:
                        sb.auth.update_user({"password": new_pass})
                        st.success("Password updated! Login now.")
                        st.session_state.app_mode = "login"
                        st.rerun()
                except Exception as e: st.error(f"Error: {e}")
        return

    # --- 3. LOGIN ---
    if st.session_state.app_mode == "login":
        st.markdown("<h1 style='text-align: center;'>Welcome</h1>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns([1,2,1])
        with c2:
            with st.container(border=True):
                email = st.text_input("Email")
                password = st.text_input("Password", type="password")
                if st.button("Log In", type="primary", use_container_width=True):
                    sb = get_supabase()
                    try:
                        res = sb.auth.sign_in_with_password({"email": email, "password": password})
                        st.session_state.user = res
                        st.session_state.user_email = email 
                        reset_app()
                        st.session_state.app_mode = "store"
                        st.rerun()
                    except Exception as e: st.error(f"Login failed: {e}")
                if st.button("Sign Up", use_container_width=True):
                    sb = get_supabase()
                    try:
                        sb.auth.sign_up({"email": email, "password": password})
                        st.success("Check email for confirmation.")
                    except Exception as e: st.error(f"Signup failed: {e}")
                if st.button("Forgot Password?", type="secondary", use_container_width=True):
                    st.session_state.app_mode = "forgot_password"; st.rerun()
        if st.button("← Back"): st.session_state.app_mode = "splash"; st.rerun()
        return

    # --- 4. SIDEBAR & ADMIN (BYPASS) ---
    with st.sidebar:
        if st.button("Reset App"): reset_app(); st.rerun()
        if st.session_state.get("user"):
            st.divider()
            u_email = st.session_state.get("user_email", "")
            if not u_email and hasattr(st.session_state.user, 'user'): u_email = st.session_state.user.user.email
            st.caption(f"Logged in: {u_email}")
            
            # --- ADMIN CHECK (The Fix) ---
            user_clean = str(u_email).strip().lower()
            
            # 1. Check Secrets (Standard)
            try: admin_secret = st.secrets["admin"]["email"].strip().lower()
            except: admin_secret = ""

            # 2. Check Hardcoded Override (The Fix)
            is_admin = False
            if user_clean == "tjkarat@gmail.com": is_admin = True # Hardcoded override
            elif admin_secret and user_clean == admin_secret: is_admin = True
            
            if is_admin:
                st.divider()
                st.success("Admin Access Granted")
                with st.expander("🔐 Console", expanded=True):
                    # Show DB Status
                    if get_supabase(): st.write("DB: Online 🟢")
                    else: st.error("DB: Offline 🔴")
                    
                    # Import Admin Module
                    import ui_admin
                    if st.button("Open Dashboard"):
                         ui_admin.show_admin()
            
            if st.button("Legal / Terms"): st.session_state.app_mode = "legal"; st.rerun()
            if st.button("Sign Out"): st.session_state.pop("user", None); reset_app(); st.session_state.app_mode = "splash"; st.rerun()

    # --- 5. THE STORE ---
    if st.session_state.app_mode == "store":
        render_hero("Select Service", "Choose your letter type.")
        c1, c2 = st.columns([2, 1])
        with c1:
            with st.container(border=True):
                st.subheader("Options")
                tier_display = {
                    "Standard": "⚡ Standard ($2.99) - Machine postage.",
                    "Heirloom": "🏺 Heirloom ($5.99) - Handwritten & Stamp.",
                    "Civic": "🏛️ Civic ($6.99) - 3 Letters to Congress.",
                    "Santa": "🎅 Santa ($9.99) - From North Pole!" 
                }
                selected_option = st.radio("Select Tier", list(tier_display.keys()), format_func=lambda x: tier_display[x])
                
                if selected_option == "Standard": st.info("Premium paper, window envelope, First Class Mail.")
                elif selected_option == "Heirloom": st.info("Hand-addressed envelope with a physical stamp.")
                elif selected_option == "Civic": st.info("Auto-sends to your 2 Senators and 1 Rep.")
                elif selected_option == "Santa": st.success("Festive background, North Pole return address.")

                lang = st.selectbox("Language", ["English", "Spanish", "French"])
                
                prices = {"Standard": 2.99, "Heirloom": 5.99, "Civic": 6.99, "Santa": 9.99}
                price = prices[selected_option]
                tier_code = selected_option 

        with c2:
            with st.container(border=True):
                st.subheader("Checkout")
                st.metric("Total", f"${price}")
                
                promo_code = st.text_input("Promo Code (Optional)")
                is_free = False
                if promo_code and promo_engine and promo_engine.validate_code(promo_code):
                    is_free = True; st.success("✅ Code Applied!"); price = 0.00
                
                st.info("⚠️ **Note:** Payment opens in a new tab.")
                
                if is_free:
                     if st.button("Start (Free)", type="primary"):
                         st.session_state.payment_complete = True
                         st.session_state.locked_tier = tier_