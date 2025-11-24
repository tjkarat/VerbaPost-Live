import streamlit as st
from streamlit_drawable_canvas import st_canvas
import os
from datetime import datetime
import re

# --- IMPORTS ---
try:
    import ai_engine 
    import database
    import letter_format
    import mailer
    import payment_engine
    import analytics
    import promo_engine
except ImportError: pass

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
    st.session_state.app_mode = "store"
    st.session_state.audio_path = None
    st.session_state.transcribed_text = ""
    st.session_state.payment_complete = False
    st.session_state.stripe_url = None
    st.session_state.sig_data = None
    st.query_params.clear()

def render_hero(title, subtitle):
    st.markdown(f"""<div class="hero-banner"><div class="hero-title">{title}</div><div class="hero-subtitle">{subtitle}</div></div>""", unsafe_allow_html=True)

# --- NEW: PROFESSIONAL LEGAL PAGE ---
def render_legal_page():
    render_hero("Legal Center", "Transparency & Trust")
    
    # Use Tabs for a clean look
    tab_tos, tab_privacy = st.tabs(["📜 Terms of Service", "🔒 Privacy Policy"])
    
    with tab_tos:
        with st.container(border=True):
            st.subheader("1. Acceptance of Terms")
            st.write("By accessing and using VerbaPost, you accept and agree to be bound by the terms and provision of this agreement.")
            
            st.subheader("2. Service Usage")
            st.write("VerbaPost provides a service to convert dictated or typed content into physical mail. You agree NOT to use this service to send:")
            st.markdown("""
            * Threatening, abusive, or harassing content.
            * Illegal substances or material soliciting illegal acts.
            * Fraudulent or deceptive mail (mail fraud).
            """)
            
            st.subheader("3. Payments & Refunds")
            st.write("Payments are processed securely via Stripe. Once a letter has been handed off to our printing partners or the USPS, it cannot be cancelled or refunded.")
            
            st.subheader("4. Limitation of Liability")
            st.write("VerbaPost is not liable for delays, loss, or damage caused by the United States Postal Service (USPS) or incorrect addresses provided by the user.")

    with tab_privacy:
        with st.container(border=True):
            st.subheader("1. Data Collection")
            st.write("We collect only the information necessary to process your letter:")
            st.markdown("""
            * **Voice Data:** Transcribed via AI and stored only until the letter is generated.
            * **Addresses:** Stored securely to facilitate mailing.
            * **Payment:** Processed via Stripe; we do not store your full credit card number.
            """)
            
            st.subheader("2. Data Usage")
            st.write("Your data is used strictly for the generation and mailing of your physical document. We do **not** sell your data to third parties.")
            
            st.subheader("3. Security")
            st.write("We use industry-standard encryption (SSL) for data transmission. Our database is secured via Supabase with Row Level Security (RLS).")

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
    
    if st.session_state.app_mode == "legal":
        render_legal_page()
        return

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
            if st.button("Cancel"):
                st.session_state.app_mode = "login"
                st.rerun()
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

    # --- 3. LOGIN / SIGNUP ---
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
            if not u_email and hasattr(st.session_state.user, 'user'):
                u_email = st.session_state.user.user.email
            
            st.caption(f"User: {u_email}")
            
            # Admin Logic (Robust)
            admin_target = st.secrets.get("admin", {}).get("email", "").strip().lower()
            user_clean = u_email.strip().lower() if u_email else ""

            if user_clean and admin_target and user_clean == admin_target:
                st.markdown("---")
                with st.expander("🔐 Admin Console", expanded=True):
                    st.write("**Promo Codes**")
                    if st.button("Generate Code"):
                        code = promo_engine.generate_code()
                        st.info(f"Code: `{code}`")
                    st.write("**System Status**")
                    if get_supabase(): st.write("DB: Online 🟢")
                    else: st.error("DB: Offline 🔴")

            if st.button("Sign Out"):
                st.session_state.pop("user", None)
                reset_app()
                st.session_state.app_mode = "splash"
                st.rerun()

    # --- 5. THE STORE ---
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
                
                if st.button(f"Pay ${price} & Start", type="primary", use_container_width=True):
                    user = st.session_state.get("user_email", "guest")
                    database.save_draft(user, "", tier, price)
                    
                    safe_tier = tier.split()[1]
                    success_link = f"{YOUR_APP_URL}?tier={safe_tier}&lang={lang}"
                    
                    url, sess_id = payment_engine.create_checkout_session(tier, int(price*100), success_link, YOUR_APP_URL)
                    
                    if url: 
                        st.info("Redirecting...")
                        st.link_button("Click to Pay Securely", url, type="primary", use_container_width=True)
                    else: 
                        st.error("Payment System Offline")

    # --- 6. THE WORKSPACE ---
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
                    from_name = st.text_input("Your Name", value=def_name)
                    from_street = st.text_input("Street", value=def_street)
                    c1, c2, c3 = st.columns(3)
                    from_city = c1.text_input("City", value=def_city)
                    from_state = c2.text_input("State", value=def_state)
                    from_zip = c3.text_input("Zip", value=def_zip)
                    to_name, to_street, to_city, to_state, to_zip = "Civic", "Civic", "Civic", "TN", "00000"
            else:
                t1, t2 = st.tabs(["👉 Recipient", "👈 Sender"])
                with t1:
                    to_name = st.text_input("Recipient Name")
                    to_street = st.text_input("Street Address")
                    c1, c2, c3 = st.columns(3)
                    to_city = c1.text_input("City")
                    to_state = c2.text_input("State")
                    to_zip = c3.text_input("Zip")
                with t2:
                    from_name = st.text_input("Your Name", value=def_name)
                    from_street = st.text_input("Street", value=def_street)
                    c1, c2, c3 = st.columns(3)
                    from_city = c1.text_input("City", value=def_city)
                    from_state = c2.text_input("State", value=def_state)
                    from_zip = c3.text_input("Zip", value=def_zip)

            if st.button("Save Addresses"):
                if u_email: database.update_user_profile(u_email, from_name, from_street, from_city, from_state, from_zip)
                st.session_state.to_addr = {'name': to_name, 'street': to_street, 'city': to_city, 'state': to_state, 'zip': to_zip}
                st.session_state.from_addr = {'name': from_name, 'street': from_street, 'city': from_city, 'state': from_state, 'zip': from_zip}
                st.toast("Saved!")

        st.markdown("<br>", unsafe_allow_html=True)
        c_sig, c_mic = st.columns(2)
        with c_sig:
            st.write("Signature")
            canvas = st_canvas(fill_color="rgba