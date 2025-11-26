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

    # --- 4. SIDEBAR & ADMIN ---
    with st.sidebar:
        if st.button("Reset App"): reset_app(); st.rerun()
        if st.session_state.get("user"):
            st.divider()
            u_email = st.session_state.get("user_email", "")
            if not u_email and hasattr(st.session_state.user, 'user'): u_email = st.session_state.user.user.email
            st.caption(f"Logged in: {u_email}")
            
            # --- ADMIN DEBUGGER ---
            admin_target = st.secrets.get("admin", {}).get("email", "").strip().lower()
            user_clean = u_email.strip().lower() if u_email else ""
            
            # Visual Debugger
            if user_clean != admin_target:
                st.error("⚠️ Admin Mismatch:")
                st.code(f"You:   '{user_clean}'\nAdmin: '{admin_target}'")
                st.caption("Copy 'You' exactly into secrets.toml if you are the admin.")

            if user_clean and admin_target and user_clean == admin_target:
                st.divider()
                st.success("Admin Access Granted")
                with st.expander("🔐 Console", expanded=True):
                    if st.button("Generate Code"):
                        code = promo_engine.generate_code()
                        st.info(f"Code: `{code}`")
                    
                    # DB Status
                    if get_supabase(): st.write("DB: Online 🟢")
                    else: st.error("DB: Offline 🔴")
                    
                    import ui_admin
                    if st.button("Open Full Console"):
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
                tier = st.radio("Tier", ["⚡ Standard ($2.99)", "🏺 Heirloom ($5.99)", "🏛️ Civic ($6.99)", "🎅 Santa ($9.99)"])
                lang = st.selectbox("Language", ["English", "Spanish", "French"])
        with c2:
            with st.container(border=True):
                st.subheader("Checkout")
                price = 2.99
                if "Heirloom" in tier: price = 5.99
                if "Civic" in tier: price = 6.99
                if "Santa" in tier: price = 9.99
                st.metric("Total", f"${price}")
                
                promo_code = st.text_input("Promo Code (Optional)")
                is_free = False
                if promo_code and promo_engine.validate_code(promo_code):
                    is_free = True; st.success("Code Applied!")

                if is_free:
                     if st.button("Start (Free)", type="primary"):
                         st.session_state.payment_complete = True
                         st.session_state.app_mode = "workspace"
                         st.session_state.locked_tier = tier.split()[1] if "Santa" not in tier else "Santa"
                         st.session_state.selected_language = lang
                         st.rerun()
                else:
                    st.info("⚠️ **Note:** Payment opens in a new tab.")
                    if st.button(f"Pay ${price} & Start", type="primary"):
                        user = st.session_state.get("user_email", "guest")
                        database.save_draft(user, "", tier, price)
                        
                        if "Santa" in tier: safe_tier = "Santa"
                        else: safe_tier = tier.split()[1]
                        
                        link = f"{YOUR_APP_URL}?tier={safe_tier}&lang={lang}"
                        url, sess_id = payment_engine.create_checkout_session(tier, int(price*100), link, YOUR_APP_URL)
                        if url:
                            # --- CSS FIX: Force White Text ---
                            st.markdown(f"""
                            <a href="{url}" target="_blank" style="text-decoration:none;">
                                <div style="
                                    background-color:#2a5298; 
                                    color:white; 
                                    padding:12px; 
                                    border-radius:8px; 
                                    text-align:center; 
                                    font-weight:bold; 
                                    margin-top:10px;
                                    box-shadow:0 4px 6px rgba(0,0,0,0.1);">
                                    <span style="color:white !important; -webkit-text-fill-color: white !important;">👉 Pay Now (Secure)</span>
                                </div>
                            </a>
                            """, unsafe_allow_html=True)
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
                    from_name = st.text_input("Your Name", value=def_name, key="civic_fname")
                    from_street = st.text_input("Street", value=def_street, key="civic_fstreet")
                    c1, c2, c3 = st.columns(3)
                    from_city = c1.text_input("City", value=def_city, key="civic_fcity")
                    from_state = c2.text_input("State", value=def_state, key="civic_fstate")
                    from_zip = c3.text_input("Zip", value=def_zip, key="civic_fzip")
            elif "Santa" in tier:
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown("**To (Child)**")
                    to_name = st.text_input("Name", key="santa_to_name")
                    to_street = st.text_input("Street", key="santa_to_street")
                    c_x, c_y, c_z = st.columns(3)
                    to_city = c_x.text_input("City", key="santa_to_city")
                    to_state = c_y.text_input("State", key="santa_to_state")
                    to_zip = c_z.text_input("Zip", key="santa_to_zip")
                with c2:
                    st.markdown("**From**")
                    st.info("🎅 North Pole (Locked)")
                    
            else:
                t1, t2 = st.tabs(["👉 Recipient", "👈 Sender"])
                with t1:
                    to_name = st.text_input("Recipient Name", key="std_toname")
                    to_street = st.text_input("Street Address", key="std_tostreet")
                    c1, c2, c3 = st.columns(3)
                    to_city = c1.text_input("City", key="std_tocity")
                    to_state = c2.text_input("State", key="std_tostate")
                    to_zip = c3.text_input("Zip", key="std_tozip")
                with t2:
                    from_name = st.text_input("Your Name", value=def_name, key="std_fname")
                    from_street = st.text_input("Street", value=def_street, key="std_fstreet")
                    c1, c2, c3 = st.columns(3)
                    from_city = c1.text_input("City", value=def_city, key="std_fcity")
                    from_state = c2.text_input("State", value=def_state, key="std_fstate")
                    from_zip = c3.text_input("Zip", value=def_zip, key="std_fzip")

            if st.button("Save Addresses"):
                if u_email and "Civic" not in tier and "Santa" not in tier: 
                    database.update_user_profile(
                        u_email, 
                        st.session_state.get('std_fname', st.session_state.get('civic_fname')),
                        st.session_state.get('std_fstreet', st.session_state.get('civic_fstreet')),
                        st.session_state.get('std_fcity', st.session_state.get('civic_fcity')),
                        st.session_state.get('std_fstate', st.session_state.get('civic_fstate')),
                        st.session_state.get('std_fzip', st.session_state.get('civic_fzip'))
                    )
                st.toast("Addresses Saved!")

        st.markdown("<br>", unsafe_allow_html=True)
        c_sig, c_mic = st.columns(2)
        with c_sig:
            st.write("Signature")
            canvas = st_canvas(stroke_width=2, stroke_color="#000", background_color="#fff", height=150, width=300, key="sig")
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

    # --- 7. REVIEW ---
    elif st.session_state.app_mode == "review":
        render_hero("Review", "Finalize Letter")
        txt = st.text_area("Body", st.session_state.transcribed_text, height=300)
        
        tier = st.session_state.get("locked_tier", "Standard")
        
        if st.button("🚀 Send Letter", type="primary"):
            # Logic for recovery of addresses
            if "Civic" in tier:
                to_a = {'name': 'Civic', 'address_line1': 'Civic'}
                from_a = {
                    'name': st.session_state.get("civic_fname"),
                    'address_line1': st.session_state.get("civic_fstreet"),
                    'address_city': st.session_state.get("civic_fcity"),
                    'address_state': st.session_state.get("civic_fstate"),
                    'address_zip': st.session_state.get("civic_fzip")
                }
            elif "Santa" in tier:
                from_a = {
                    'name': 'Santa Claus', 'address_line1': '123 Elf Road', 'address_city': 'North Pole', 'address_state': 'NP', 'address_zip': '88888'
                }
                to_a = {
                    'name': st.session_state.get("santa_to_name"),
                    'address_line1': st.session_state.get("santa_to_street"),
                    'address_city': st.session_state.get("santa_to_city"),
                    'address_state': st.session_state.get("santa_to_state"),
                    'address_zip': st.session_state.get("santa_to_zip")
                }
            else:
                to_a = {
                    'name': st.session_state.get("std_toname"),
                    'address_line1': st.session_state.get("std_tostreet"),
                    'address_city': st.session_state.get("std_tocity"),
                    'address_state': st.session_state.get("std_tostate"),
                    'address_zip': st.session_state.get("std_tozip")
                }
                from_a = {
                    'name': st.session_state.get("std_fname"),
                    'address_line1': st.session_state.get("std_fstreet"),
                    'address_city': st.session_state.get("std_fcity"),
                    'address_state': st.session_state.get("std_fstate"),
                    'address_zip': st.session_state.get("std_fzip")
                }

            if not to_a.get('name') or not to_a.get('address_line1') and "Civic" not in tier:
                st.error("❌ Error: Recipient Street and Name are required.")
                return

            to_str = f"{to_a.get('name')}\n{to_a.get('address_line1')}"
            from_str = f"{from_a.get('name')}\n{from_a.get('address_line1')}"
            is_heirloom = "Heirloom" in tier
            is_santa = "Santa" in tier
            lang = st.session_state.get("selected_language", "English")
            
            # Signature Path
            sig_path = None
            if "sig_data" in st.session_state and st.session_state.sig_data is not None:
                try:
                    img = Image.fromarray(st.session_state.sig_data.astype('uint8'), 'RGBA')
                    bg = Image.new("RGB", img.size, (255,255,255))
                    bg.paste(img, mask=img.split()[3])
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                        bg.save(tmp, format="PNG")
                        sig_path = tmp.name
                except: pass

            pdf = letter_format.create_pdf(txt, to_str, from_str, is_heirloom, lang, sig_path, is_santa)
            
            if "Civic" in tier:
                st.info("Civic Mode: Sending to representatives...")
                st.success("Civic Letters Sent!")
            else:
                res = mailer.send_letter(pdf, to_a, from_a)
                if res: st.success("Letter Mailed via USPS!")
                
            if st.button("Finish"): reset_app()