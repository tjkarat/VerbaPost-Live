import streamlit as st
from streamlit_drawable_canvas import st_canvas
import os
import tempfile
import json
import base64
import numpy as np
from PIL import Image

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
try: import analytics
except: analytics = None

# --- CONFIG ---
YOUR_APP_URL = "https://verbapost.streamlit.app/"

def reset_app():
    st.session_state.app_mode = "splash" 
    st.session_state.audio_path = None
    st.session_state.transcribed_text = ""
    st.session_state.payment_complete = False
    st.session_state.sig_data = None
    st.session_state.to_addr = {}
    st.session_state.from_addr = {}
    st.session_state.civic_targets = []
    st.query_params.clear()

def render_hero(title, subtitle):
    # ADDED class='custom-hero' so CSS in main.py can target this specific box
    st.markdown(f"""
    <div class="custom-hero" style="background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); 
                padding: 40px; border-radius: 15px; text-align: center; 
                margin-bottom: 30px; box-shadow: 0 8px 16px rgba(0,0,0,0.1);">
        <h1 style="margin: 0; font-size: 3rem; font-weight: 700; color: white !important;">{title}</h1>
        <div style="font-size: 1.2rem; opacity: 0.9; margin-top: 10px; color: white !important;">{subtitle}</div>
    </div>
    """, unsafe_allow_html=True)

def show_santa_animation():
    st.markdown("""<div class="santa-sled">🎅🛷</div>""", unsafe_allow_html=True)

# --- PAGE: LEGAL ---
def render_legal_page():
    render_hero("Legal Center", "Terms & Privacy")
    
    with st.container(border=True):
        st.subheader("Terms of Service")
        st.markdown("""
        **1. Acceptance of Terms**
        By accessing and using VerbaPost, you accept and agree to be bound by the terms and provision of this agreement.
        
        **2. Service Description**
        VerbaPost provides a service to convert audio and digital text into physical mail. We utilize third-party APIs (PostGrid, Lob) for the printing and mailing process.
        
        **3. User Content**
        You are responsible for the content of your letters. We do not endorse, support, or guarantee the completeness, truthfulness, accuracy, or reliability of any content posted via the Service.
        
        **4. Refunds**
        Refunds are generally not provided once a letter has been processed for printing. However, if a technical error occurs on our end preventing the generation of your letter, a full refund will be issued.
        """)
        
        st.divider()
        
        st.subheader("Privacy Policy")
        st.markdown("""
        **1. Information Collection**
        We collect personal information such as your name, address, and email address when you register. We also process the audio and text content of the letters you send.
        
        **2. Data Usage**
        - **Fulfillment:** Your address and letter content are sent to our printing partners solely for the purpose of mailing.
        - **AI Processing:** Audio files are processed using OpenAI's Whisper API. We do not use your data to train AI models.
        
        **3. Data Security**
        We implement security measures designed to protect your information. Payment data is handled securely by Stripe; we never store your full credit card number.
        
        **4. Contact**
        For privacy concerns or to request data deletion, contact support@verbapost.com.
        """)

    if st.button("← Return to Home", type="primary"):
        st.session_state.app_mode = "splash"
        st.rerun()

# --- PAGE: STORE ---
def render_store_page():
    render_hero("Select Service", "Choose your letter type")
    
    # --- ADMIN LINK ---
    u_email = st.session_state.get("user_email", "")
    admin_target = ""
    if "admin" in st.secrets:
        admin_target = st.secrets["admin"].get("email", "")
    
    admin_target = str(admin_target).strip().lower()
    user_clean = str(u_email).strip().lower()

    if user_clean and user_clean == admin_target:
        if st.button("🔐 Open Admin Console", type="secondary"):
            st.session_state.app_mode = "admin"
            st.rerun()

    c1, c2 = st.columns([2, 1])
    with c1:
        with st.container(border=True):
            st.subheader("Available Packages")
            tier_options = {
                "Standard": "⚡ Standard ($2.99) - Machine generated, window envelope.",
                "Heirloom": "🏺 Heirloom ($5.99) - Handwriting font, thick paper, real stamp.",
                "Civic": "🏛️ Civic ($6.99) - Write to Congress. We find your Reps automatically.",
                "Santa": "🎅 Santa ($9.99) - Direct from North Pole. Festive background."
            }
            sel = st.radio("Select Tier", list(tier_options.keys()), format_func=lambda x: tier_options[x])
            tier_code = sel
            prices = {"Standard": 2.99, "Heirloom": 5.99, "Civic": 6.99, "Santa": 9.99}
            price = prices[tier_code]
            
            if tier_code == "Santa":
                st.info("🎅 **Santa Special:** Includes a magical North Pole background.")
            elif tier_code == "Civic":
                st.info("🏛️ **Civic Action:** Dictate one letter, we mail all your Reps.")

    with c2:
        with st.container(border=True):
            st.subheader("Checkout")
            st.metric("Total", f"${price}")
            
            if st.button(f"Pay ${price} & Start", type="primary", use_container_width=True):
                if database: database.save_draft(u_email, "", tier_code, price)
                link = f"{YOUR_APP_URL}?tier={tier_code}&session_id={{CHECKOUT_SESSION_ID}}"
                url, sess_id = payment_engine.create_checkout_session(tier_code, int(price*100), link, YOUR_APP_URL)
                
                if url:
                    st.markdown(f"""<a href="{url}" target="_blank" style="text-decoration:none;"><div style="background-color:#6772e5; color:white; padding:12px; border-radius:4px; text-align:center; font-weight:bold;">👉 Pay Now via Stripe</div></a>""", unsafe_allow_html=True)
                    # --- PAGE: WORKSPACE (Address Logic) ---
def render_workspace_page():
    tier = st.session_state.get("locked_tier", "Standard")
    render_hero("Compose Letter", f"{tier} Edition")
    
    # 1. FETCH USER PROFILE
    u_email = st.session_state.get("user_email")
    user_addr = {}
    if database and u_email:
        p = database.get_user_profile(u_email)
        if p:
            user_addr = {"name": p.full_name, "street": p.address_line1, "city": p.address_city, "state": p.address_state, "zip": p.address_zip}

    with st.container(border=True):
        st.subheader("📍 Addressing")
        
        if tier == "Santa":
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**To (Child)**")
                to_name = st.text_input("Child's Name", key="w_to_name")
                to_street = st.text_input("Street", key="w_to_street")
                c_x, c_y, c_z = st.columns(3)
                to_city = c_x.text_input("City", key="w_to_city")
                to_state = c_y.text_input("State", key="w_to_state")
                to_zip = c_z.text_input("Zip", key="w_to_zip")
            with c2:
                st.markdown("**From**")
                st.success("🎅 Locked: North Pole")
                from_name="Santa Claus"; from_street="123 Elf Road"; from_city="North Pole"; from_state="NP"; from_zip="88888"

        elif tier == "Civic":
            has_valid_addr = user_addr.get("street") and user_addr.get("zip")
            if has_valid_addr:
                st.success(f"✅ Using registered address: {user_addr.get('street')}")
                from_name = user_addr.get("name")
                from_street = user_addr.get("street")
                from_city = user_addr.get("city")
                from_state = user_addr.get("state")
                from_zip = user_addr.get("zip")
            else:
                st.warning("Please enter your address for Rep lookup.")
                from_name = st.text_input("Your Name", key="w_civic_name")
                from_street = st.text_input("Street", key="w_civic_street")
                c_a, c_b, c_c = st.columns(3)
                from_city = c_a.text_input("City", key="w_civic_city")
                from_state = c_b.text_input("State", key="w_civic_state")
                from_zip = c_c.text_input("Zip", key="w_civic_zip")
            to_name="Civic"; to_street="Civic"; to_city="Civic"; to_state="TN"; to_zip="00000"

        else: # Standard/Heirloom
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
                def_n = user_addr.get("name", ""); def_s = user_addr.get("street", ""); def_c = user_addr.get("city", ""); def_st = user_addr.get("state", ""); def_z = user_addr.get("zip", "")
                from_name = st.text_input("Name", value=def_n, key="w_from_name")
                from_street = st.text_input("Street", value=def_s, key="w_from_street")
                c_a, c_b, c_c = st.columns(3)
                from_city = c_a.text_input("City", value=def_c, key="w_from_city")
                from_state = c_b.text_input("State", value=def_st, key="w_from_state")
                from_zip = c_c.text_input("Zip", value=def_z, key="w_from_zip")

        if st.button("Save Addresses"):
             st.session_state.to_addr = {"name": to_name, "street": to_street, "city": to_city, "state": to_state, "zip": to_zip}
             st.session_state.from_addr = {"name": from_name, "street": from_street, "city": from_city, "state": from_state, "zip": from_zip}
             st.toast("Addresses Saved!")

    st.write("---")
    
    is_ready = False
    if tier == "Civic" and st.session_state.get("from_addr", {}).get("zip"): is_ready = True
    elif st.session_state.get("to_addr", {}).get("name"): is_ready = True
    
    c_sig, c_mic = st.columns(2)
    with c_sig:
        st.write("✍️ **Signature**")
        if tier == "Santa":
             st.info("Signed by Santa")
             st.session_state.sig_data = None
        else:
             canvas = st_canvas(stroke_width=2, stroke_color="#000", background_color="#fff", height=150, width=400, key="canvas")
             if canvas.image_data is not None: st.session_state.sig_data = canvas.image_data
             
    with c_mic:
        st.write("🎤 **Dictation**")
        if not is_ready:
            st.warning("⚠️ Please Fill & Save Addresses Above First")
        else:
            audio = st.audio_input("Record")
            if audio:
                if ai_engine:
                    with st.spinner("Transcribing..."):
                        text = ai_engine.transcribe_audio(audio)
                        st.session_state.transcribed_text = text
                        st.session_state.app_mode = "review"
                        st.rerun()

def render_review_page():
    render_hero("Review Letter", "Finalize and Send")
    
    st.info("Please review the text below. You can edit it if the AI made a mistake.")
    txt = st.text_area("Body Content", st.session_state.get("transcribed_text", ""), height=300)
    st.session_state.transcribed_text = txt 
    
    if st.button("🚀 Send Letter", type="primary"):
        tier = st.session_state.get("locked_tier", "Standard")
        u_email = st.session_state.get("user_email")
        
        # 1. GENERATE PDF
        to_data = st.session_state.get("to_addr", {})
        from_data = st.session_state.get("from_addr", {})
        
        to_str = f"{to_data.get('name','')}\n{to_data.get('street','')}\n{to_data.get('city','')}, {to_data.get('state','')} {to_data.get('zip','')}"
        from_str = f"{from_data.get('name','')}\n{from_data.get('street','')}\n{from_data.get('city','')}, {from_data.get('state','')} {from_data.get('zip','')}"
        
        # 2. PROCESS SIGNATURE
        sig_path = None
        is_santa = (tier == "Santa")
        
        if not is_santa and st.session_state.get("sig_data") is not None:
            try:
                img_data = st.session_state.sig_data
                if isinstance(img_data, np.ndarray):
                    img = Image.fromarray(img_data.astype('uint8'), 'RGBA')
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_sig:
                        img.save(tmp_sig.name)
                        sig_path = tmp_sig.name
            except Exception as e:
                print(f"Sig Error: {e}")

        # 3. GENERATE PDF
        if letter_format:
            pdf_bytes = letter_format.create_pdf(
                txt, 
                to_str, 
                from_str, 
                is_heirloom=("Heirloom" in tier),
                is_santa=is_santa,
                signature_path=sig_path
            )
            
            if sig_path and os.path.exists(sig_path):
                os.remove(sig_path)
            
            # 4. SEND (STANDARD)
            postgrid_success = False
            if tier == "Standard" and mailer:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    tmp.write(pdf_bytes)
                    tmp_path = tmp.name
                
                pg_to = {
                    'name': to_data.get('name'), 'address_line1': to_data.get('street'),
                    'address_city': to_data.get('city'), 'address_state': to_data.get('state'), 'address_zip': to_data.get('zip')
                }
                pg_from = {
                    'name': from_data.get('name'), 'address_line1': from_data.get('street'),
                    'address_city': from_data.get('city'), 'address_state': from_data.get('state'), 'address_zip': from_data.get('zip')
                }
                
                resp = mailer.send_letter(tmp_path, pg_to, pg_from)
                os.remove(tmp_path)
                if resp and resp.get("id"):
                    postgrid_success = True
                    st.toast(f"PostGrid ID: {resp.get('id')}")
            
            # 5. SAVE DB
            if database:
                final_status = "Completed" if postgrid_success else "Pending Admin"
                database.save_draft(
                    u_email, txt, tier, "0.00", 
                    to_addr=to_data, from_addr=from_data, 
                    status=final_status
                )
        
        show_santa_animation()
        st.success("Letter Queued for Delivery!")
        
        if st.button("🏁 Finish & Return Home"): 
            reset_app()
            st.rerun()

# --- MAIN CONTROLLER ---
def show_main_app():
    if analytics: analytics.inject_ga()
    
    mode = st.session_state.get("app_mode", "splash")
    
    if "session_id" in st.query_params:
        st.session_state.app_mode = "workspace"
        st.session_state.payment_complete = True
        if "tier" in st.query_params: st.session_state.locked_tier = st.query_params["tier"]
        st.query_params.clear()
        st.rerun()

    if mode == "splash": 
        import ui_splash
        ui_splash.show_splash()
    elif mode == "login": 
        import ui_login
        import auth_engine
        ui_login.show_login(
            lambda e,p: _handle_login(auth_engine, e,p), 
            lambda e,p,n,a,c,s,z,l: _handle_signup(auth_engine, e,p,n,a,c,s,z,l)
        )
    elif mode == "store": render_store_page()
    elif mode == "workspace": render_workspace_page()
    elif mode == "review": render_review_page()
    elif mode == "legal": render_legal_page()
    
    elif mode == "admin":
        import ui_admin
        ui_admin.show_admin()

    elif mode == "forgot_password":
        import ui_login
        import auth_engine
        ui_login.show_forgot_password(lambda e: auth_engine.send_password_reset(e))
    elif mode == "reset_verify":
        import ui_login
        import auth_engine
        ui_login.show_reset_verify(lambda e,t,n: auth_engine.reset_password_with_token(e,t,n))

    with st.sidebar:
        if st.button("🏠 Home"): reset_app(); st.rerun()
        if st.session_state.get("user_email"):
            st.write(f"User: {st.session_state.user_email}")
            if st.button("Logout"):
                st.session_state.clear()
                st.rerun()

# --- AUTH CALLBACKS ---
def _handle_login(auth, email, password):
    res, err = auth.sign_in(email, password)
    if res and res.user:
        st.session_state.user = res.user
        st.session_state.user_email = res.user.email
        st.session_state.app_mode = "store"
        st.rerun()
    else:
        st.session_state.auth_error = err

def _handle_signup(auth, email, password, name, addr, city, state, zip_c, lang):
    res, err = auth.sign_up(email, password, name, addr, city, state, zip_c, lang)
    if res and res.user:
        st.success("Account Created! Please log in.")
        st.session_state.app_mode = "login"
    else:
        st.session_state.auth_error = err