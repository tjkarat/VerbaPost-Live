import streamlit as st
from streamlit_drawable_canvas import st_canvas
import os
from PIL import Image
from datetime import datetime
import urllib.parse
import io
import zipfile
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from supabase import create_client, Client

# --- CONFIG ---
MAX_BYTES_THRESHOLD = 35 * 1024 * 1024 
YOUR_APP_URL = "https://verbapost.streamlit.app" 
COST_STANDARD = 2.99
COST_HEIRLOOM = 5.99
COST_CIVIC = 6.99
SUPPORT_EMAIL = "support@verbapost.com"

# --- HELPER: INIT SUPABASE ---
@st.cache_resource
def get_supabase():
    try:
        # Debug check (prints to Manage App -> Logs, not screen)
        if "SUPABASE_URL" not in st.secrets:
            print("❌ MISSING SECRET: SUPABASE_URL")
            return None
            
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception as e:
        print(f"Supabase Connection Error: {e}")
        return None

def reset_app():
    # SOFT RESET
    st.session_state.app_mode = "store"
    st.session_state.audio_path = None
    st.session_state.transcribed_text = ""
    st.session_state.payment_complete = False
    st.session_state.stripe_url = None
    st.session_state.sig_data = None
    
    # Clear addresses (keep email/user)
    addr_keys = ["to_name", "to_street", "to_city", "to_state", "to_zip", 
                 "from_name", "from_street", "from_city", "from_state", "from_zip"]
    for k in addr_keys:
        st.session_state[k] = ""
        
    st.query_params.clear()
    st.rerun()

def render_hero(title, subtitle):
    st.markdown(f"""
        <div class="hero-banner">
            <div class="hero-title">{title}</div>
            <div class="hero-subtitle">{subtitle}</div>
        </div>
    """, unsafe_allow_html=True)

# --- AUTH FLOWS ---
def render_forgot_password_page():
    render_hero("Recover Account", "Let's get you back in.")
    with st.container(border=True):
        st.write("Enter your email address. We will send you a **6-digit code**.")
        email = st.text_input("Email Address")
        if st.button("Send Code", type="primary"):
            if email:
                supabase = get_supabase()
                if not supabase:
                    st.error("System Error: Database connection failed. Check Secrets.")
                    return
                try:
                    supabase.auth.reset_password_email(email)
                    st.session_state['reset_email'] = email
                    st.session_state['app_mode'] = 'verify_reset_code'
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
            else:
                st.warning("Please enter an email.")
        if st.button("Back"):
            reset_app()

def render_verify_reset_code():
    render_hero("Verify Code", "Check your email inbox.")
    with st.container(border=True):
        st.info(f"We sent a code to **{st.session_state.get('reset_email')}**")
        code = st.text_input("6-Digit Code", max_chars=6)
        new_password = st.text_input("New Password", type="password")
        if st.button("Verify & Update Password", type="primary"):
            if not code or len(new_password) < 6:
                st.error("Invalid input.")
                return
            supabase = get_supabase()
            if not supabase:
                 st.error("System Error: Database connection failed.")
                 return
            email = st.session_state.get('reset_email')
            try:
                session = supabase.auth.verify_otp({"email": email, "token": code, "type": "recovery"})
                if session.user:
                    supabase.auth.update_user({"password": new_password})
                    st.success("✅ Password Updated! Logging you in...")
                    st.session_state['user'] = session
                    st.session_state['app_mode'] = "workspace"
                    st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")
        if st.button("Cancel"):
            reset_app()

def show_main_app():
    # --- LAZY IMPORTS ---
    import ai_engine 
    import database
    import letter_format
    import mailer
    import zipcodes
    import payment_engine
    import civic_engine
    import promo_engine
    import analytics

    analytics.inject_ga()

    # --- SAFETY CHECK ---
    defaults = {
        "app_mode": "store",
        "audio_path": None,
        "transcribed_text": "",
        "payment_complete": False,
        "processed_ids": [],
        "stripe_url": None,
        "locked_tier": "Standard",
        "sig_data": None,
        "selected_language": "English"
    }
    for k, v in defaults.items():
        if k not in st.session_state: st.session_state[k] = v

    # --- ROUTING ---
    if st.session_state.app_mode == "forgot_password":
        render_forgot_password_page()
        return

    if st.session_state.app_mode == "verify_reset_code":
        render_verify_reset_code()
        return

    # --- NEW: LEGAL PAGE (Fixes the White Screen) ---
    if st.session_state.app_mode == "legal":
        render_hero("Legal", "Terms & Privacy")
        with st.container(border=True):
            st.markdown("### Privacy Policy")
            st.write("We value your privacy. Your letters are processed securely and deleted from local cache after sending.")
            st.markdown("### Terms of Service")
            st.write("By using VerbaPost, you agree not to send threatening or illegal content via US Mail.")
            
            st.write("")
            if st.button("← Back to Home", type="primary"):
                st.session_state.app_mode = "splash"
                st.rerun()
        return 

    # ==================================================
    #  PHASE 0: LOGIN / SIGNUP SCREEN
    # ==================================================
    if st.session_state.app_mode == "login":
        st.write("")
        st.markdown("<h1 style='text-align: center; margin-bottom: 20px;'>Welcome Back</h1>", unsafe_allow_html=True)
        
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            with st.container(border=True):
                email = st.text_input("Email Address")
                password = st.text_input("Password", type="password")
                
                st.write("") # Spacer
                
                b1, b2 = st.columns(2)
                with b1:
                    if st.button("Log In", type="primary", use_container_width=True):
                        supabase = get_supabase()
                        if not supabase:
                            st.error("❌ Connection Failed. Check Secrets.")
                        else:
                            try:
                                res = supabase.auth.sign_in_with_password({"email": email, "password": password})
                                st.session_state.user = res
                                st.session_state.app_mode = "workspace"
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {e}")
                with b2:
                    if st.button("Sign Up", use_container_width=True):
                        supabase = get_supabase()
                        if not supabase:
                            st.error("❌ Connection Failed. Check Secrets.")
                        else:
                            try:
                                res = supabase.auth.sign_up({"email": email, "password": password})
                                st.success("Account created! Check email.")
                            except Exception as e:
                                st.error(f"Error: {e}")

                st.write("")        
                if st.button("Forgot Password?", type="secondary", use_container_width=True):
                    st.session_state.app_mode = "forgot_password"
                    st.rerun()
                    
        c_back1, c_back2, c_back3 = st.columns([1, 1, 1])
        with c_back2:
            if st.button("← Back to Home", use_container_width=True):
                 st.session_state.app_mode = "splash"
                 st.rerun()
        return

    # --- STRIPE RETURN CHECK ---
    qp = st.query_params
    if "session_id" in qp:
        session_id = qp["session_id"]
        if session_id not in st.session_state.processed_ids:
            if payment_engine.check_payment_status(session_id):
                st.session_state.payment_complete = True
                st.session_state.processed_ids.append(session_id)
                st.toast("✅ Payment Confirmed!")
                st.session_state.app_mode = "workspace"
                if "tier" in qp: st.session_state.locked_tier = qp["tier"]
                if "lang" in qp: st.session_state.selected_language = qp["lang"]
                keys_to_restore = ["to_name", "to_street", "to_city", "to_state", "to_zip", 
                                   "from_name", "from_street", "from_city", "from_state", "from_zip"]
                for key in keys_to_restore:
                    if key in qp: st.session_state[key] = qp[key]
            else:
                st.error("Payment verification failed.")
        st.query_params.clear() 

    # ==========================================
    #  SIDEBAR
    # ==========================================
    with st.sidebar:
        st.subheader("Menu")
        if st.button("🔄 Restart App", type="secondary"):
            reset_app()
        if st.session_state.get("user"):
            st.divider()
            try:
                u_email = st.session_state.user.user.email 
            except:
                u_email = st.session_state.user.email

            st.caption(f"Logged in: {u_email}")
            if st.button("Sign Out"):
                st.session_state.pop("user")
                reset_app()

    # ==================================================
    #  PHASE 1: THE STORE
    # ==================================================
    if st.session_state.app_mode == "store":
        render_hero("VerbaPost", "Voice to Letter. Mailed physically.")
        
        col1, col2 = st.columns([2, 1])
        with col1:
            with st.container(border=True):
                st.subheader("1. Customize")
                c_tier, c_lang = st.columns(2)
                with c_tier:
                    service_tier = st.radio("Service Tier", 
                        [f"⚡ Standard (${COST_STANDARD})", f"🏺 Heirloom (${COST_HEIRLOOM})", f"🏛️ Civic (${COST_CIVIC})"],
                        index=0
                    )
                with c_lang:
                    options = ["English", "Japanese", "Chinese", "Korean"]
                    idx = options.index(st.session_state.selected_language) if st.session_state.selected_language in options else 0
                    language = st.selectbox("Language", options, index=idx)
        
        with col2:
            with st.container(border=True):
                st.subheader("2. Checkout")
                if "Standard" in service_tier: price = COST_STANDARD; tier_name = "Standard"
                elif "Heirloom" in service_tier: price = COST_HEIRLOOM; tier_name = "Heirloom"
                elif "Civic" in service_tier: price = COST_CIVIC; tier_name = "Civic"
                
                promo_code = st.text_input("Promo Code (Optional)")
                valid_promo = False
                
                if promo_code:
                    if promo_engine.validate_code(promo_code):
                        valid_promo = True; price = 0.00
                        st.success("✅ Code Applied!")
                    else: st.error("Invalid Code")

                st.markdown(f"### Total: **${price}**")
                
                if valid_promo:
                    if st.button("Start (Free)", type="primary"):
                        if promo_engine.redeem_code(promo_code):
                            st.session_state.payment_complete = True
                            st.session_state.app_mode = "workspace"
                            st.session_state.locked_tier = tier_name
                            st.session_state.selected_language = language
                            st.rerun()
                else:
                    current_config = f"{service_tier}_{price}_{language}"
                    if "stripe_url" not in st.session_state or st.session_state.get("last_config") != current_config:
                         success_link = f"{YOUR_APP_URL}?tier={tier_name}&lang={language}"
                         user_email = st.session_state.get("user_email", "guest@verbapost.com")
                         draft_id = database.save_draft(user_email, "", "", "", "", "")
                         if draft_id:
                             success_link += f"&letter_id={draft_id}"
                             url, session_id = payment_engine.create_checkout_session(
                                f"VerbaPost {service_tier}", int(price * 100), success_link, YOUR_APP_URL
                            )
                             st.session_state.stripe_url = url
                             st.session_state.stripe_session_id = session_id
                             st.session_state.last_config = current_config
                    
                    if st.session_state.stripe_url:
                        st.link_button(f"Pay ${price} & Begin", st.session_state.stripe_url, type="primary")

    # ==================================================
    #  PHASE 2: THE WORKSPACE
    # ==================================================
    elif st.session_state.app_mode == "workspace":
        tier = st.session_state.get("locked_tier")
        render_hero("Compose Letter", f"{tier} Edition")

        with st.container(border=True):
            st.subheader("1. Addressing")
            with st.form("address_form"):
                col_to, col_from = st.tabs(["👉 Recipient", "👈 Sender"])
                def get_val(key): return st.session_state.get(key, "")

                with col_to:
                    if "Civic" in tier:
                        st.info("🏛️ Representatives will be auto-detected from your address.")
                    else:
                        to_name = st.text_input("Full Name", value=get_val("to_name"))
                        to_street = st.text_input("Street Address", value=get_val("to_street"))
                        c1, c2, c3 = st.columns([2, 1, 1])
                        to_city = c1.text_input("City", value=get_val("to_city"))
                        to_state = c2.text_input("State", value=get_val("to_state"))
                        to_zip = c3.text_input("Zip", value=get_val("to_zip"))

                with col_from:
                    from_name = st.text_input("Your Name", value=get_val("from_name"))
                    from_street = st.text_input("Your Street", value=get_val("from_street"))
                    from_city = st.text_input("Your City", value=get_val("from_city"))
                    c1, c2, c3 = st.columns([2, 1, 1])
                    from_state = c2.text_input("Your State", value=get_val("from_state"))
                    from_zip = c3.text_input("Your Zip", value=get_val("from_zip"))
                
                if "Civic" in tier:
                     to_name, to_street, to_city, to_state, to_zip = "Civic", "Civic", "Civic", "TN", "00000"

                if st.form_submit_button("Save Addresses"):
                    st.session_state.to_name = to_name; st.session_state.to_street = to_street
                    st.session_state.to_city = to_city; st.session_state.to_state = to_state
                    st.session_state.to_zip = to_zip; st.session_state.from_name = from_name
                    st.session_state.from_street = from_street; st.session_state.from_city = from_city
                    st.session_state.from_state = from_state; st.session_state.from_zip = from_zip
                    st.toast("Saved!")

        st.markdown("<br>", unsafe_allow_html=True)

        c_sign, c_rec = st.columns(2)
        with c_sign:
            with st.container(border=True):
                st.subheader("2. Signature")
                canvas_result = st_canvas(
                    fill_color="rgba(255, 165, 0, 0.3)", stroke_width=2, stroke_color="#000",
                    background_color="#fff", height=150, width=300, drawing_mode="freedraw", key="sig"
                )
                if canvas_result.image_data is not None: st.session_state.sig_data = canvas_result.image_data

        with c_rec:
            with st.container(border=True):
                st.subheader("3. Dictate")
                st.write("Tap the mic to start.")
                audio_val = st.audio_input("Record Letter")
                
                if audio_val:
                    with st.status("Transcribing...", expanded=True):
                        path = "temp.wav"
                        with open(path, "wb") as f: f.write(audio_val.getvalue())
                        st.session_state.audio_path = path
                        try:
                            text = ai_engine.transcribe_audio(path)
                            st.session_state.transcribed_text = text
                            st.session_state.app_mode = "review"
                            st.rerun()
                        except Exception as e: st.error(f"Error: {e}")

    # ==================================================
    #  PHASE 3: REVIEW
    # ==================================================
    elif st.session_state.app_mode == "review":
        render_hero("Review", "Polish your letter before sending.")
        with st.container(border=True):
            if not st.session_state.get("transcribed_text"): st.session_state.transcribed_text = ""
            edited = st.text_area("Edit Content:", value=st.session_state.transcribed_text, height=400)
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("← Discard & Re-record", type="secondary"):
                    st.session_state.app_mode = "workspace"
                    st.rerun()
            with col2:
                if st.button("Finalize & Send 🚀", type="primary"):
                    st.session_state.transcribed_text = edited
                    st.session_state.app_mode = "finalizing"
                    st.rerun()

    # ==================================================
    #  PHASE 4: FINALIZE
    # ==================================================
    elif st.session_state.app_mode == "finalizing":
        render_hero("Sending...", "We are processing your letter.")
        with st.container(border=True):
            locked_tier = st.session_state.get("locked_tier", "Standard")
            locked_lang = st.session_state.get("selected_language", "English")
            is_civic = "Civic" in locked_tier; is_heirloom = "Heirloom" in locked_tier
            
            to_addr = {
                'name': st.session_state.get("to_name"),
                'address_line1': st.session_state.get("to_street"),
                'address_city': st.session_state.get("to_city"),
                'address_state': st.session_state.get("to_state"),
                'address_zip': st.session_state.get("to_zip")
            }
            from_addr = {
                'name': st.session_state.get("from_name"),
                'address_line1': st.session_state.get("from_street"),
                'address_city': st.session_state.get("from_city"),
                'address_state': st.session_state.get("from_state"),
                'address_zip': st.session_state.get("from_zip")
            }

            sig_path = None
            if st.session_state.get("sig_data") is not None:
                try:
                    img = Image.fromarray(st.session_state.sig_data.astype('uint8'), 'RGBA')
                    sig_path = "temp_signature.png"
                    img.save(sig_path)
                except: pass

            with st.status("Generating PDF & Sending...", expanded=True):
                today_str = datetime.now().strftime("%Y-%m-%d")
                safe_name = re.sub(r'[^a-zA-Z0-9]', '', to_addr['name']) or "Recipient"
                filename_pdf = f"VerbaPost_{safe_name}_{today_str}.pdf"

                if is_civic:
                    st.info("Civic mailing logic here.")
                else:
                    pdf_path = letter_format.create_pdf(
                        st.session_state.transcribed_text, 
                        f"{to_addr['name']}\n{to_addr['address_line1']}...", 
                        f"{from_addr['name']}\n{from_addr['address_line1']}...", 
                        is_heirloom, locked_lang, filename_pdf, sig_path
                    )
                    
                    if not is_heirloom:
                         res = mailer.send_letter(pdf_path, to_addr, from_addr)
                         if res: st.success("Mailed via Lob!")
                    else:
                         st.success("Added to Heirloom Queue.")

                    with open(pdf_path, "rb") as f:
                        st.download_button("Download PDF Copy", f, filename_pdf)

            if st.button("Start New Letter"): reset_app()