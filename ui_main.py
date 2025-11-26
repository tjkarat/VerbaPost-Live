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

    if st.button("← Return to Home", type="primary", key="legal_back"):
        st.session_state.app_mode = "splash"
        st.rerun()

# --- PAGE: SPLASH ---
def render_splash_page():
    if os.path.exists("logo.png"):
        c1, c2, c3 = st.columns([1, 4, 1]) 
        with c2:
            st.markdown('<div style="margin-top: 2rem; margin-bottom: 2rem;">', unsafe_allow_html=True)
            st.image("logo.png", use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown("""
    <div style="text-align: center; margin-bottom: 30px;">
        <h3 style="color: #2d3748; font-weight: 600;">Turn your voice into a real letter.</h3>
        <p style="font-size: 1.2rem; color: #555; margin-top: 15px; line-height: 1.6;">
            Texts are trivial. Emails are ignored.<br><b style="color: #2a5298;">REAL LETTERS GET OPENED.</b>
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        if st.button("🔐 Log In / Sign Up to Start", type="primary", use_container_width=True):
            st.session_state.app_mode = "login"
            st.rerun()

    st.divider()
    c1, c2, c3 = st.columns(3)
    with c1: st.markdown("### 🎙️ 1. Dictate"); st.caption("You speak. AI types.")
    with c2: st.markdown("### ✍️ 2. Sign"); st.caption("Sign on your screen.")
    with c3: st.markdown("### 📮 3. We Mail"); st.caption("Printed, stamped, & sent.")

    st.divider()
    st.subheader("Pricing")
    p1, p2, p3, p4 = st.columns(4)
    with p1: st.container(border=True).metric("⚡ Standard", "$2.99", "Machine Postage")
    with p2: st.container(border=True).metric("🏺 Heirloom", "$5.99", "Real Stamp")
    with p3: st.container(border=True).metric("🏛️ Civic", "$6.99", "3 Letters")
    with p4: st.container(border=True).metric("🎅 Santa", "$9.99", "North Pole")

    st.markdown("---")
    if st.button("Legal / Terms", type="secondary"):
        st.session_state.app_mode = "legal"
        st.rerun()

# --- PAGE: LOGIN / FORGOT PASSWORD ---
def render_login_page():
    # --- HANDLE FORGOT PASSWORD MODE ---
    if st.session_state.get("show_reset"):
        st.markdown("<h2 style='text-align: center;'>Reset Password</h2>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            with st.container(border=True):
                if not st.session_state.get("reset_sent"):
                    # Step 1: Ask for Email
                    email = st.text_input("Enter your email address")
                    if st.button("Send Reset Code", type="primary"):
                        sb = get_supabase()
                        if sb:
                            try:
                                sb.auth.reset_password_email(email)
                                st.session_state.reset_email = email
                                st.session_state.reset_sent = True
                                st.success("Code sent! Check your email.")
                                st.rerun()
                            except Exception as e: st.error(f"Error: {e}")
                    if st.button("Cancel"):
                        st.session_state.show_reset = False
                        st.rerun()
                else:
                    # Step 2: Verify Token
                    st.info(f"Enter code sent to {st.session_state.get('reset_email')}")
                    token = st.text_input("6-Digit Code")
                    new_pass = st.text_input("New Password", type="password")
                    if st.button("Update Password", type="primary"):
                        sb = get_supabase()
                        try:
                            # Verify the OTP type 'recovery'
                            res = sb.auth.verify_otp({"email": st.session_state.reset_email, "token": token, "type": "recovery"})
                            if res.user:
                                sb.auth.update_user({"password": new_pass})
                                st.success("Password Updated! Please Log In.")
                                st.session_state.show_reset = False
                                st.session_state.reset_sent = False
                                st.rerun()
                        except Exception as e: st.error(f"Verification Failed: {e}")
        return

    # --- NORMAL LOGIN ---
    st.markdown("<h2 style='text-align: center;'>Welcome</h2>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        with st.container(border=True):
            tab_login, tab_signup = st.tabs(["Log In", "Sign Up"])
            
            with tab_login:
                l_email = st.text_input("Email", key="l_email")
                l_pass = st.text_input("Password", type="password", key="l_pass")
                if st.button("Log In", type="primary", use_container_width=True):
                    sb = get_supabase()
                    if not sb: st.error("System Error: Database connection missing.")
                    else:
                        try:
                            res = sb.auth.sign_in_with_password({"email": l_email, "password": l_pass})
                            st.session_state.user = res
                            st.session_state.user_email = l_email
                            st.session_state.app_mode = "store"
                            st.rerun()
                        except Exception as e: st.error(f"Login failed: {e}")
            
            with tab_signup:
                s_email = st.text_input("Email", key="s_email")
                s_pass = st.text_input("Password", type="password", key="s_pass")
                if st.button("Create Account", type="primary", use_container_width=True):
                    sb = get_supabase()
                    if not sb: st.error("System Error.")
                    else:
                        try:
                            sb.auth.sign_up({"email": s_email, "password": s_pass})
                            st.success("Success! Please check your email.")
                        except Exception as e: st.error(f"Signup failed: {e}")
            
            st.divider()
            if st.button("Forgot Password?", type="secondary"):
                st.session_state.show_reset = True
                st.rerun()

    if st.button("← Back"): st.session_state.app_mode = "splash"; st.rerun()

# --- PAGE: STORE ---
def render_store_page():
    render_hero("Select Service", "Choose your letter type")
    
    if st.session_state.get("user"):
        u_email = st.session_state.get("user_email", "")
        # Admin Check logic...
        # (Omitted for brevity, use previous admin logic block here)

    c1, c2 = st.columns([2, 1])
    with c1:
        with st.container(border=True):
            st.subheader("Options")
            tier_display = {"Standard": "⚡ Standard ($2.99)", "Heirloom": "🏺 Heirloom ($5.99)", "Civic": "🏛️ Civic ($6.99)", "Santa": "🎅 Santa ($9.99)"}
            selected_option = st.radio("Select Tier", list(tier_display.keys()), format_func=lambda x: tier_display[x])
            
            if "Standard" in selected_option: tier_code="Standard"; st.info("Premium paper, #10 window envelope.")
            elif "Heirloom" in selected_option: tier_code="Heirloom"; st.info("Hand-addressed envelope, physical stamp.")
            elif "Civic" in selected_option: tier_code="Civic"; st.info("3 letters to your representatives.")
            elif "Santa" in selected_option: tier_code="Santa"; st.success("Festive background, North Pole return address.")
            else: tier_code="Standard"

            lang = st.selectbox("Language", ["English", "Spanish", "French"])
            prices = {"Standard": 2.99, "Heirloom": 5.99, "Civic": 6.99, "Santa": 9.99}
            price = prices[tier_code]

    with c2:
        with st.container(border=True):
            st.subheader("Checkout")
            st.metric("Total", f"${price}")
            
            promo = st.text_input("Promo Code (Optional)")
            is_free = False
            if promo and promo_engine and promo_engine.validate_code(promo):
                is_free = True; st.success("Code Applied!")
            
            if is_free:
                if st.button("Start (Free)", type="primary"):
                    st.session_state.payment_complete = True
                    st.session_state.locked_tier = tier_code
                    st.session_state.selected_language = lang
                    st.session_state.app_mode = "workspace"
                    st.rerun()
            else:
                st.info("⚠️ **Note:** Payment opens in a new tab.")
                if st.button(f"Pay ${price} & Start", type="primary"):
                    u_email = st.session_state.get("user_email", "guest")
                    if database: database.save_draft(u_email, "", tier_code, price)
                    
                    link = f"{YOUR_APP_URL}?tier={tier_code}&lang={lang}&session_id={{CHECKOUT_SESSION_ID}}"
                    url, sess_id = payment_engine.create_checkout_session(tier_code, int(price*100), link, YOUR_APP_URL)
                    if url: 
                        st.markdown(f"""
                        <a href="{url}" target="_blank" style="text-decoration: none !important;">
                            <div style="background-color:#2a5298;color:white;padding:12px;text-align:center;border-radius:8px;font-weight:bold;margin-top:10px;box-shadow:0 4px 6px rgba(0,0,0,0.1);">
                                <span style="color:white !important; -webkit-text-fill-color: white !important;">👉 Pay Now (Secure)</span>
                            </div>
                        </a>
                        """, unsafe_allow_html=True)
                    else: st.error("Payment System Offline")

# --- PAGE: WORKSPACE (FIXED SANTA LOGIC) ---
def render_workspace_page():
    tier = st.session_state.get("locked_tier", "Standard")
    is_civic = "Civic" in tier
    is_santa = "Santa" in tier
    render_hero("Compose", f"{tier} Edition")
    
    u_email = st.session_state.get("user_email")
    d = st.session_state.draft if "draft" in st.session_state else {}

    # --- AUTO-POPULATE VARIABLES ---
    from_name, from_street, from_city, from_state, from_zip = "", "", "", "", ""
    
    # If Santa, FORCE North Pole
    if is_santa:
        from_name="Santa Claus"
        from_street="123 Elf Road"
        from_city="North Pole"
        from_state="NP"
        from_zip="88888"
    # If Database available, load user defaults
    elif database and u_email:
        profile = database.get_user_profile(u_email)
        if profile:
            from_name = profile.full_name or ""
            from_street = profile.address_line1 or ""
            from_city = profile.address_city or ""
            from_state = profile.address_state or ""
            from_zip = profile.address_zip or ""

    with st.container(border=True):
        st.subheader("📍 Addressing")
        
        if is_santa:
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**To (Child)**")
                to_name = st.text_input("Name", key="w_to_name")
                to_street = st.text_input("Street", key="w_to_street")
                c_x, c_y, c_z = st.columns(3)
                to_city = c_x.text_input("City", key="w_to_city")
                to_state = c_y.text_input("State", key="w_to_state")
                to_zip = c_z.text_input("Zip", key="w_to_zip")
            with c2:
                st.markdown("**From**")
                st.info("🎅 North Pole (Locked)")
                # LOCKED INPUTS
                st.text_input("Sender", value=from_name, disabled=True)
                st.text_input("Street", value=from_street, disabled=True)
                c_a, c_b, c_c = st.columns(3)
                c_a.text_input("City", value=from_city, disabled=True)
                c_b.text_input("State", value=from_state, disabled=True)
                c_c.text_input("Zip", value=from_zip, disabled=True)
        
        else:
            # Standard / Civic
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**To**")
                to_name = st.text_input("Name", key="w_to_name")
                to_street = st.text_input("Street", key="w_to_street")
                c_x, c_y, c_z = st.columns(3)
                to_city = c_x.text_input("City", key="w_to_city")
                to_state = c_y.text_input("State", key="w_to_state")
                to_zip = c_z.text_input("Zip", key="w_to_zip")
            with c2:
                st.markdown("**From**")
                from_name_in = st.text_input("Name", value=from_name, key="w_from_name")
                from_street_in = st.text_input("Street", value=from_street, key="w_from_street")
                c_a, c_b, c_c = st.columns(3)
                from_city_in = c_a.text_input("City", value=from_city, key="w_from_city")
                from_state_in = c_b.text_input("State", value=from_state, key="w_from_state")
                from_zip_in = c_c.text_input("Zip", value=from_zip, key="w_from_zip")
                
                # Update vars for saving
                from_name, from_street, from_city, from_state, from_zip = from_name_in, from_street_in, from_city_in, from_state_in, from_zip_in

        if st.button("Save Addresses"):
            if database and u_email and not is_santa: 
                database.update_user_profile(u_email, from_name, from_street, from_city, from_state, from_zip)
            
            # Save to session
            st.session_state.to_addr = {"name": to_name, "street": to_street, "city": to_city, "state": to_state, "zip": to_zip}
            st.session_state.from_addr = {"name": from_name, "street": from_street, "city": from_city, "state": from_state, "zip": from_zip}
                
            st.toast("Addresses Saved!")

    st.write("---")
    c_sig, c_mic = st.columns(2)
    with c_sig:
        st.write("✍️ **Signature**")
        # SANTA AUTO-SIGN LOGIC
        if is_santa:
             st.info("Signature will be 'Santa Claus'")
             st.session_state.sig_data = None
        else:
             # FIXED SYNTAX
             canvas = st_canvas(stroke_width=2, stroke_color="#000", background_color="#fff", height=150, width=400, key="canvas")
             if canvas.image_data is not None: st.session_state.sig_data = canvas.image_data
             
    with c_mic:
        st.write("🎤 **Dictation**")
        audio = st.audio_input("Record")
        if audio:
            with st.status("Transcribing..."):
                if ai_engine:
                    text = ai_engine.transcribe_audio(audio)
                    st.session_state.transcribed_text = text
                    st.session_state.app_mode = "review"
                    st.rerun()

def render_review_page():
    render_hero("Review", "Finalize Letter")
    txt = st.text_area("Body", st.session_state.get("transcribed_text", ""), height=300)
    
    if st.button("🚀 Send Letter", type="primary"):
        tier = st.session_state.get("locked_tier", "Standard")
        to_a = st.session_state.get("to_addr", {})
        from_a = st.session_state.get("from_addr", {})
        
        if not to_a.get("name"): st