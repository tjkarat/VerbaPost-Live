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
    # Preserve login state
    user = st.session_state.get("user")
    user_email = st.session_state.get("user_email")
    
    # Reset app state variables
    st.session_state.app_mode = "store"
    st.session_state.audio_path = None
    st.session_state.transcribed_text = ""
    st.session_state.payment_complete = False
    st.session_state.stripe_url = None
    st.session_state.sig_data = None
    st.query_params.clear()
    
    # Restore login state
    if user: 
        st.session_state.user = user
    if user_email: 
        st.session_state.user_email = user_email

def render_hero(title, subtitle):
    st.markdown(f"""<div class="hero-banner"><div class="hero-title">{title}</div><div class="hero-subtitle">{subtitle}</div></div>""", unsafe_allow_html=True)

# --- PAGE: LEGAL (Needs to be moved to ui_legal.py later) ---
def render_legal_page():
    render_hero("Legal Center", "Transparency & Trust")
    tab_tos, tab_privacy = st.tabs(["📜 Terms of Service", "🔒 Privacy Policy"])
    with tab_tos:
        with st.container(border=True):
            st.subheader("1. Service Usage")
            st.write("You agree NOT to use VerbaPost to send threatening, abusive, or illegal content.")
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
    # Note: app_mode should be initialized in the main router (web_app.py)
    if "app_mode" not in st.session_state: st.session_state.app_mode = "store"
    if "processed_ids" not in st.session_state: st.session_state.processed_ids = []

    # --- STRIPE HANDLER ---
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
    # Note: Splash, Login, and Admin routing are handled by web_app.py

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

    # --- LOGIN ---
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

    # --- SIDEBAR & ADMIN ---
    # NOTE: The sidebar button logic is handled in web_app.py, but this UI renders when web_app.py
    # calls ui_main.show_main_app().
    with st.sidebar:
        
        # === TEMPORARY DEBUG CODE ===
        if st.session_state.get("user"):
            st.sidebar.markdown("---")
            st.sidebar.error("🚨 ADMIN DEBUG VALUES 🚨")
            try:
                # 1. Get Admin Email
                admin_target = st.secrets.get("admin", {}).get("email", "N/A")
                admin_clean = admin_target.strip().lower()
                
                # 2. Get User Email
                user_raw = st.session_state.user.user.email
                user_clean = user_raw.strip().lower()
                
                # 3. Display Comparison
                st.sidebar.write(f"Secret Admin: **{repr(admin_clean)}**")
                st.sidebar.write(f"Logged-in User: **{repr(user_clean)}**")
                st.sidebar.write(f"Match Check: **{user_clean == admin_clean}**")
            except Exception as e:
                st.sidebar.write(f"Error reading emails: {e}")
            st.sidebar.markdown("---")
        # === END TEMPORARY DEBUG CODE ===

        if st.button("Reset App"): reset_app(); st.rerun()
        if st.session_state.get("user"):
            st.divider()
            u_email = st.session_state.get("user_email", "")
            if not u_email and hasattr(st.session_state.user, 'user'): u_email = st.session_state.user.user.email
            
            st.caption(f"User: {u_email}")
            
            # ADMIN CHECK (Logic for the button that takes you to admin page)
            admin_secret = st.secrets.get("admin", {}).get("email", "").strip().lower()
            user_clean = u_email.strip().lower() if u_email else ""
            
            is_admin = (user_clean and admin_secret and user_clean == admin_secret)

            if is_admin:
                st.markdown("---")
                # ADMIN BUTTON ONLY: This button changes the view state for the web_app.py router
                if st.button("🔐 Admin Panel", type="primary", use_container_width=True):
                    st.session_state.current_view = "admin"
                    st.rerun()
                # Status display is safe to keep here
                with st.expander("ℹ️ Status", expanded=True):
                    st.write("Admin Privileges: Enabled")
                    if get_supabase(): st.write("DB: Online 🟢")
                    else: st.error("DB: Offline 🔴")
            
            if st.button("Legal / Terms"): st.session_state.app_mode = "legal"; st.rerun()
            if st.button("Sign Out"): 
                st.session_state.pop("user", None)
                st.session_state.pop("user_email", None)
                reset_app() 
                st.session_state.app_mode = "splash"
                st.rerun()

    # --- STORE ---
    if st.session_state.app_mode == "store":
        render_hero("Select Service", "Choose your letter type.")
        c1, c2 = st.columns([2, 1])
        with c1:
            with st.container(border=True):
                st.subheader("Options")
                tier = st.radio("Tier", ["⚡ Standard ($2.99)", "🏺 Heirloom ($5.99)", "🏛️ Civic ($6.99)"])
                lang = st.selectbox("Language", ["English", "Spanish", "French"])
        with c2:
            with st.container(border=True):
                st.subheader("Checkout")
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
                        st.success("✅ Promo Code Applied! Total: $0.00")
                    else:
                        st.error("❌ Invalid or Expired Code")
                
                st.info("⚠️ **Note:** Payment opens in a new tab.")
                
                if valid_promo:
                    if st.button("Start (Free)", type="primary", use_container_width=True):
                        if promo_engine.redeem_code(promo_code):
                            st.session_state.payment_complete = True
                            st.session_state.app_mode = "workspace"
                            st.session_state.locked_tier = tier.split()[1]
                            st.session_state.selected_language = lang
                            st.rerun()
                else:
                    if st.button(f"Pay ${price} & Start", type="primary", use_container_width=True):
                        user = st.session_state.get("user_email", "guest")
                        database.save_draft(user, "", tier, price)
                        safe_tier = tier.split()[1]
                        link = f"{YOUR_APP_URL}?tier={safe_tier}&lang={lang}"
                        url, sess_id = payment_engine.create_checkout_session(tier, int(price*100), link, YOUR_APP_URL)
                        if url: st.link_button("Click here to Pay", url, type="primary", use_container_width=True)
                        else: st.error("Payment System Offline")

    # --- WORKSPACE ---
    elif st.session_state.app_mode == "workspace":
        tier = st.session_state.get("locked_tier", "Standard")
        render_hero("Compose", f"{tier} Edition")
        
        u_email = st.session_state.get("user_email")
        saved = database.get_user_profile(u_email) if u_email else None
        
        def_name = saved.full_name if saved else ""
        def_street = saved.address_line1 if saved else ""
        def_city = saved.address_city if saved else ""
        def_state = saved.address_state if saved else ""
        def_zip = saved.address_zip if saved else ""

        with st.container(border=True):
            st.subheader("Addressing")
            if "Civic" in tier:
                st.info("🏛️ **Civic Mode:** We auto-detect reps based on your address.")
                with st.expander("📍 Your Return Address", expanded=True):
                    # FIX: Unique keys for Civic Mode inputs
                    from_name = st.text_input("Your Name", value=def_name, key="civic_fname")
                    from_street = st.text_input("Street", value=def_street, key="civic_fstreet")
                    c1, c2, c3 = st.columns(3)
                    from_city = c1.text_input("City", value=def_city, key="civic_fcity")
                    from_state = c2.text_input("State", value=def_state, key="civic_fstate")
                    from_zip = c3.text_input("Zip", value=def_zip, key="civic_fzip")
                    to_name, to_street, to_city, to_state, to_zip = "Civic", "Civic", "Civic", "TN", "00000"
            else:
                t1, t2 = st.tabs(["👉 Recipient", "👈 Sender"])
                with t1:
                    # FIX: Unique keys for Standard Recipient
                    to_name = st.text_input("Recipient Name", key="std_toname")
                    to_street = st.text_input("Street Address", key="std_tostreet")
                    c1, c2, c3 = st.columns(3)
                    to_city = c1.text_input("City", key="std_tocity")
                    to_state = c2.text_input("State", key="std_tostate")
                    to_zip = c3.text_input("Zip", key="std_tozip")
                with t2:
                    # FIX: Unique keys for Standard Sender
                    from_name = st.text_input("Your Name", value=def_name, key="std_fname")
                    from_street = st.text_input("Street", value=def_street, key="std_fstreet")
                    c1, c2, c3 = st.columns(3)
                    from_city = c1.text_input("City", value=def_city, key="std_fcity")
                    from_state = c2.text_input("State", value=def_state, key="std_fstate")
                    from_zip = c3.text_input("Zip", value=def_zip, key="std_fzip")

            if st.button("Save Addresses"):
                # Use session state keys for saving
                if u_email: 
                    database.update_user_profile(
                        u_email, 
                        st.session_state.get('std_fname', st.session_state.get('civic_fname')),
                        st.session_state.get('std_fstreet', st.session_state.get('civic_fstreet')),
                        st.session_state.get('std_fcity', st.session_state.get('civic_fcity')),
                        st.session_state.get('std_fstate', st.session_state.get('civic_fstate')),
                        st.session_state.get('std_fzip', st.session_state.get('civic_fzip'))
                    )
                st.session_state.to_addr = {'name': to_name, 'street': to_street, 'city': to_city, 'state': to_state, 'zip': to_zip}
                st.session_state.from_addr = {'name': from_name, 'street': from_street, 'city': from_city, 'state': from_state, 'zip': from_zip}
                st.toast("Addresses Saved!")

        st.markdown("<br>", unsafe_allow_html=True)
        c_sig, c_mic = st.columns(2)
        with c_sig:
            st.write("Signature")
            canvas = st_canvas(fill_color="rgba(255, 165, 0, 0.3)", stroke_width=2, stroke_color="#000", background_color="#fff", height=150, width=300, key="sig")
            if canvas.image_data is not None: st.session_state.sig_data = canvas.image_data
        with c_mic:
            st.write("Dictate Body")
            st.info("👆 **Click microphone to start. Click red square to stop.**")
            audio = st.audio_input("Record")
            if audio:
                with st.status("Transcribing..."):
                    path = "temp.wav"
                    with open(path, "wb") as f: f.write(audio.getvalue())
                    text = ai_engine.transcribe_audio(path)
                    st.session_state.transcribed_text = text
                    st.session_state.app_mode = "review"
                    st.rerun()

    # --- REVIEW ---
    elif st.session_state.app_mode == "review":
        render_hero("Review", "Finalize Letter")
        txt = st.text_area("Body", st.session_state.transcribed_text, height=300)
        if st.button("🚀 Send Letter", type="primary"):
            to_a = st.session_state.get("to_addr", {})
            from_a = st.session_state.get("from_addr", {})
            
            to_str = f"{to_a.get('name')}\n{to_a.get('street')}\n{to_a.get('city')}, {to_a.get('state')} {to_a.get('zip')}"
            from_str = f"{from_a.get('name')}\n{from_a.get('street')}\n{from_a.get('city')}, {from_a.get('state')} {from_a.get('zip')}"
            
            # Get args
            tier = st.session_state.get("locked_tier", "Standard")
            is_heirloom = "Heirloom" in tier
            lang = st.session_state.get("selected_language", "English")

            pdf = letter_format.create_pdf(txt, to_str, from_str, is_heirloom, lang) 
            
            if "Civic" in tier:
                st.info("Civic Mode: Sending to reps...")
            else:
                mailer.send_letter(pdf, to_a, from_a)
                st.success("Letter Sent!")
                
            if st.button("Finish"): reset_app()