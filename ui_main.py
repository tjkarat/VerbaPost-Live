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
    # INJECT GLOBAL CSS HERE
    st.markdown("""
    <style>
        /* Force Dark Text Globally (Fixes invisible text) */
        .stApp, p, h1, h2, h3, h4, h5, h6, div, span, label, li {
            color: #2d3748 !important;
        }
        
        /* Exception: White Text for Hero Banner */
        #hero-container h1, #hero-container div { 
            color: #FFFFFF !important; 
        }
        
        /* Exception: White Text for Pay Button */
        .pay-btn span { 
            color: #FFFFFF !important;
            -webkit-text-fill-color: #FFFFFF !important; 
        }

        /* Force Sidebar Visible */
        [data-testid="stSidebar"] { display: block !important; }
    </style>
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
            st.subheader("1. Acceptance of Terms")
            st.write("By using VerbaPost, you agree to these terms.")
            st.subheader("2. Usage Policy")
            st.write("You agree NOT to use this service for illegal, threatening, or abusive content.")
            st.subheader("3. Refunds")
            st.write("Once a letter is processed, it cannot be cancelled or refunded.")

    with tab_privacy:
        with st.container(border=True):
            st.subheader("Data Handling")
            st.write("We process voice data solely for transcription. Address data is stored securely.")
            st.subheader("Security")
            st.write("All payments are processed via Stripe.")

    if st.button("← Return to Home", type="primary"):
        st.session_state.app_mode = "splash"
        st.rerun()

# --- PAGE: SPLASH ---
def render_splash_page():
    if os.path.exists("logo.png"):
        c1, c2, c3 = st.columns([3, 2, 3]) 
        with c2: st.image("logo.png", use_container_width=True)
    
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

# --- PAGE: LOGIN ---
def render_login_page():
    st.markdown("<h2 style='text-align: center;'>Welcome</h2>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        with st.container(border=True):
            tab_login, tab_signup = st.tabs(["Log In", "Sign Up"])
            
            with tab_login:
                st.subheader("Access Account")
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
                st.subheader("Create New Account")
                s_email = st.text_input("Email", key="s_email")
                s_pass = st.text_input("Password", type="password", key="s_pass")
                
                if st.button("Create Account", type="primary", use_container_width=True):
                    sb = get_supabase()
                    if not sb: st.error("System Error: Database connection missing.")
                    else:
                        try:
                            sb.auth.sign_up({"email": s_email, "password": s_pass})
                            st.success("Success! Please check your email to verify.")
                        except Exception as e: st.error(f"Signup failed: {e}")
            
            st.divider()
            if st.button("Forgot Password?", type="secondary"):
                st.session_state.app_mode = "forgot_password"
                st.rerun()

    if st.button("← Back"): st.session_state.app_mode = "splash"; st.rerun()

# --- PAGE: STORE ---
def render_store_page():
    render_hero("Select Service", "Choose your letter type")
    
    if st.session_state.get("user"):
        u_email = st.session_state.get("user_email", "")
        if not u_email and hasattr(st.session_state.user, 'user'): u_email = st.session_state.user.user.email
        admin_target = st.secrets.get("admin", {}).get("email", "").strip().lower()
        user_clean = str(u_email).strip().lower()
        
        if user_clean == admin_target:
             if st.button("🔐 Open Admin Console", type="secondary"):
                 import ui_admin
                 ui_admin.show_admin()
                 return

    c1, c2 = st.columns([2, 1])
    with c1:
        with st.container(border=True):
            st.subheader("Options")
            tier_display = {"Standard": "⚡ Standard ($2.99)", "Heirloom": "🏺 Heirloom ($5.99)", "Civic": "🏛️ Civic ($6.99)", "Santa": "🎅 Santa ($9.99)"}
            selected_option = st.radio("Select Tier", list(tier_display.keys()), format_func=lambda x: tier_display[x])
            
            if selected_option == "Standard": st.info("Premium paper, #10 window envelope, First Class Mail.")
            elif selected_option == "Heirloom": st.info("Hand-addressed envelope, physical stamp, premium feel.")
            elif selected_option == "Civic": st.info("3 letters sent to your 2 Senators and 1 Representative.")
            elif selected_option == "Santa": st.success("Festive background, North Pole return address.")

            lang = st.selectbox("Language", ["English", "Spanish", "French"])
            
            prices = {"Standard": 2.99, "Heirloom": 5.99, "Civic": 6.99, "Santa": 9.99}
            if "Standard" in selected_option: tier_code = "Standard"
            elif "Heirloom" in selected_option: tier_code = "Heirloom"
            elif "Civic" in selected_option: tier_code = "Civic"
            elif "Santa" in selected_option: tier_code = "Santa"
            else: tier_code = "Standard"
            
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
                        <a href="{url}" target="_blank" style="text-decoration: none !important;" class="pay-btn">
                            <div style="background-color:#2a5298; padding:12px; text-align:center; border-radius:8px; margin-top:10px; box-shadow:0 4px 6px rgba(0,0,0,0.1);">
                                <span style="font-weight: bold; font-size: 18px;">
                                    👉 Pay Now (Secure)
                                </span>
                            </div>
                        </a>
                        """, unsafe_allow_html=True)
                    else: st.error("Payment System Offline")

# --- PAGE: WORKSPACE ---
def render_workspace_page():
    tier = st.session_state.get("locked_tier", "Standard")
    is_civic = "Civic" in tier
    is_santa = "Santa" in tier
    render_hero("Compose", f"{tier} Edition")
    
    u_email = st.session_state.get("user_email")
    if database and u_email:
        profile = database.get_user_profile(u_email)
        def_name = profile.full_name if profile else ""
        def_street = profile.address_line1 if profile else ""
        def_city = profile.address_city if profile else ""
        def_state = profile.address_state if profile else ""
        def_zip = profile.address_zip if profile else ""
    else:
        def_name=def_street=def_city=def_state=def_zip=""

    d = st.session_state.draft if "draft" in st.session_state else {}

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
                from_name="Santa Claus"; from_street="123 Elf Road"; from_city="North Pole"; from_state="NP"; from_zip="88888"
        
        elif is_civic:
            st.info("Civic Mode: We auto-find your reps.")
            st.markdown("**Your Return Address**")
            from_name = st.text_input("Name", value=def_name, key="w_from_name")
            from_street = st.text_input("Street", value=def_street, key="w_from_street")
            c1, c2, c3 = st.columns(3)
            from_city = c1.text_input("City", value=def_city, key="w_from_city")
            from_state = c2.text_input("State", value=def_state, key="w_from_state")
            from_zip = c3.text_input("Zip", value=def_zip, key="w_from_zip")
            to_name="Civic"; to_street="Civic"; to_city="Civic"; to_state="TN"; to_zip="00000"

        else:
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
                from_name = st.text_input("Name", value=def_name, key="w_from_name")
                from_street = st.text_input("Street", value=def_street, key="w_from_street")
                c_a, c_b, c_c = st.columns(3)
                from_city = c_a.text_input("City", value=def_city, key="w_from_city")
                from_state = c_b.text_input("State", value=def_state, key="w_from_state")
                from_zip = c_c.text_input("Zip", value=def_zip, key="w_from_zip")

        if st.button("Save Addresses"):
            if database and u_email and not is_santa and not is_civic: 
                database.update_user_profile(u_email, from_name, from_street, from_city, from_state, from_zip)
            
            if is_santa:
                st.session_state.to_addr = {"name": to_name, "street": to_street, "city": to_city, "state": to_state, "zip": to_zip}
                st.session_state.from_addr = {"name": "Santa Claus", "street": "123 Elf Road", "city": "North Pole", "state": "NP", "zip": "88888"}
            elif is_civic:
                 st.session_state.from_addr = {"name": from_name, "street": from_street, "city": from_city, "state": from_state, "zip": from_zip}
                 st.session_state.to_addr = {"name": "Civic", "street": "Civic"}
            else:
                st.session_state.to_addr = {"name": to_name, "street": to_street, "city": to_city, "state": to_state, "zip": to_zip}
                st.session_state.from_addr = {"name": from_name, "street": from_street, "city": from_city, "state": from_state, "zip": from_zip}
                
            st.toast("Addresses Saved!")

    st.write("---")
    c_sig, c_mic = st.columns(2)
    with c_sig:
        st.write("✍️ **Signature**")
        # SANTA AUTO-SIGN LOGIC
        if is_santa:
             st.info("Signature will be 'Santa Claus' (Auto-generated)")
             st.session_state.sig_data = None
        else:
             # FIXED SYNTAX (underscore)
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
        
        if not to_a.get("name"): st.error("Recipient Name Missing!"); return

        is_heirloom = "Heirloom" in tier
        is_santa = "Santa" in tier
        lang = st.session_state.get("selected_language", "English")
        
        sig_path = None
        sig_storage = None
        # Skip signature logic for Santa
        if not is_santa and "sig_data" in st.session_state and st.session_state.sig_data is not None:
            try:
                img = Image.fromarray(st.session_state.sig_data.astype('uint8'), 'RGBA')
                bg = Image.new("RGB", img.size, (255,255,255))
                bg.paste(img, mask=img.split()[3])
                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                    bg.save(tmp, format="PNG")
                    sig_path = tmp.name
                buffered = BytesIO()
                bg.save(buffered, format="PNG")
                sig_storage = base64.b64encode(buffered.getvalue()).decode()
            except: pass

        to_str = f"{to_a.get('name')}\n{to_a.get('street')}\n{to_a.get('city')}..."
        from_str = f"{from_a.get('name')}\n{from_a.get('street')}..."

        if letter_format:
            pdf_bytes = letter_format.create_pdf(txt, to_str, from_str, is_heirloom, lang, sig_path, is_santa)
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(pdf_bytes)
                pdf_path = tmp.name
            
            res = None
            if not is_heirloom and not is_santa and mailer:
                pass
            
            u_email = st.session_state.get("user_email", "guest")
            status = "sent_api" if res else "pending"
            
            if database: 
                database.save_draft(u_email, txt, tier, 2.99, to_a, from_a, sig_storage, status)
            
            os.remove(pdf_path)
            if sig_path: os.remove(sig_path)
            
            st.session_state.letter_sent = True
            st.success("Letter Sent!")
            
            # FIXED FINISH BUTTON REDIRECT
            if st.button("Finish"): 
                reset_app()
                st.rerun()

# --- MAIN CONTROLLER ---
def show_main_app():
    if 'analytics' in globals(): analytics.inject_ga()

    # 1. Handle Routing
    mode = st.session_state.get("app_mode", "splash")

    # Stripe Return Check (TOP LEVEL PRIORITY)
    if "session_id" in st.query_params:
        st.session_state.app_mode = "workspace"
        st.session_state.payment_complete = True
        st.query_params.clear()
        st.rerun()

    # 2. Render Views
    if mode == "splash": render_splash_page()
    elif mode == "login": render_login_page()
    elif mode == "legal": render_legal_page()
    elif mode == "store": render_store_page()
    elif mode == "workspace": render_workspace_page()
    elif mode == "review": render_review_page()
    
    elif mode == "forgot_password":
         render_hero("Recovery", "Reset Password")
         if st.button("Back"): st.session_state.app_mode = "login"; st.rerun()

    # 3. Sidebar
    with st.sidebar:
        if st.button("Home"): reset_app(); st.rerun()
        if st.session_state.get("user"):
            st.divider()
            u_email = st.session_state.get("user_email", "")
            if not u_email and hasattr(st.session_state.user, 'user'): u_email = st.session_state.user.user.email
            st.caption(f"Logged in: {u_email}")
            
            admin_target = st.secrets.get("admin", {}).get("email", "").strip().lower()
            user_clean = str(u_email).strip().lower()
            
            if user_clean == admin_target:
                st.success("Admin Access")
                import ui_admin
                if st.button("Open Console"): ui_admin.show_admin()
            
            if st.button("Sign Out"): st.session_state.pop("user", None); reset_app(); st.rerun()