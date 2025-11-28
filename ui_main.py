import streamlit as st
from streamlit_drawable_canvas import st_canvas
import os
import tempfile
import json
import base64
import numpy as np
from PIL import Image
import io

# --- IMPORTS ---
try: import database
except ImportError: database = None
try: import ai_engine
except ImportError: ai_engine = None
try: import payment_engine
except ImportError: payment_engine = None
try: import letter_format
except ImportError: letter_format = None
try: import mailer
except ImportError: mailer = None
try: import analytics
except ImportError: analytics = None
try: import promo_engine
except ImportError: promo_engine = None
try: import secrets_manager
except ImportError: secrets_manager = None
try: import civic_engine
except ImportError: civic_engine = None

# --- CONFIG ---
DEFAULT_URL = "https://verbapost.streamlit.app/"
YOUR_APP_URL = DEFAULT_URL

try:
    if secrets_manager:
        found_url = secrets_manager.get_secret("BASE_URL")
        if found_url: YOUR_APP_URL = found_url
except: pass

YOUR_APP_URL = YOUR_APP_URL.rstrip("/")

def reset_app():
    if st.session_state.get("user_email"):
        st.session_state.app_mode = "store"
    else:
        st.session_state.app_mode = "splash"
    
    st.session_state.audio_path = None
    st.session_state.transcribed_text = ""
    st.session_state.payment_complete = False
    st.session_state.sig_data = None
    st.session_state.to_addr = {}
    st.session_state.from_addr = {}
    st.session_state.civic_targets = []
    if "letter_sent_success" in st.session_state: del st.session_state.letter_sent_success
    st.query_params.clear()

def render_hero(title, subtitle):
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

def render_legal_page():
    render_hero("Legal Center", "Terms & Privacy")
    with st.container(border=True):
        st.subheader("Terms of Service")
        st.markdown("""
        **Last Updated: November 2024**
        **1. MANUAL HANDLING DISCLOSURE (NO PRIVACY)**
        For "Heirloom" and "Santa" Tiers: These require manual printing. VerbaPost staff will view your content. NO PRIVACY EXPECTED.
        **2. Automated Handling (Standard/Civic)**
        Standard and Civic letters are processed via API and not read by humans.
        **3. Delivery**
        VerbaPost acts as a fulfillment agent. We are not liable for USPS delays.
        """)
        st.divider()
        st.subheader("Privacy Policy")
        st.write("We retain data for 30 days. Payment is handled by Stripe.")
    
    if st.button("← Return to Home", type="primary"):
        reset_app(); st.rerun()

def render_store_page():
    render_hero("Select Service", "Choose your letter type")
    u_email = st.session_state.get("user_email", "")
    
    admin_target = ""
    try:
        if secrets_manager:
            admin_target = secrets_manager.get_secret("admin.email") or secrets_manager.get_secret("ADMIN_EMAIL")
        if not admin_target and "admin" in st.secrets:
            admin_target = st.secrets["admin"].get("email", "")
    except: pass

    if str(u_email).strip().lower() == str(admin_target).strip().lower() and admin_target:
        if st.button("🔐 Open Admin Console", type="secondary"):
            st.session_state.app_mode = "admin"; st.rerun()

    c1, c2 = st.columns([2, 1])
    with c1:
        with st.container(border=True):
            st.subheader("Available Packages")
            tier_options = {
                "Standard": "⚡ Standard ($2.99)",
                "Heirloom": "🏺 Heirloom ($5.99)",
                "Civic": "🏛️ Civic ($6.99)",
                "Santa": "🎅 Santa ($9.99)"
            }
            sel = st.radio("Select Tier", list(tier_options.keys()), format_func=lambda x: tier_options[x])
            tier_code = sel
            prices = {"Standard": 2.99, "Heirloom": 5.99, "Civic": 6.99, "Santa": 9.99}
            price = prices[tier_code]

    with c2:
        with st.container(border=True):
            st.subheader("Checkout")
            discounted = False
            if promo_engine:
                code_input = st.text_input("Promo Code", key="promo_box")
                if code_input:
                    if promo_engine.validate_code(code_input):
                        discounted = True
                        st.success("✅ Code Applied!")
                    else: st.error("❌ Invalid Code")
            
            if discounted:
                st.metric("Total", "$0.00", delta=f"-${price} off")
                if st.button("🚀 Start (Free)", type="primary", use_container_width=True):
                    if promo_engine: promo_engine.log_usage(code_input, u_email)
                    if database: database.save_draft(u_email, "", tier_code, "0.00")
                    st.session_state.payment_complete = True
                    st.session_state.locked_tier = tier_code
                    st.session_state.app_mode = "workspace"
                    st.rerun()
            else:
                st.metric("Total", f"${price}")
                if st.button(f"Pay ${price} & Start", type="primary", use_container_width=True):
                    if database: database.save_draft(u_email, "", tier_code, price)
                    link = f"{YOUR_APP_URL}?tier={tier_code}&session_id={{CHECKOUT_SESSION_ID}}"
                    if payment_engine:
                        url, sess_id = payment_engine.create_checkout_session(tier_code, int(price*100), link, YOUR_APP_URL)
                        if url:
                            st.markdown(f"""<a href="{url}" target="_blank" style="text-decoration:none;"><div style="background-color:#6772e5; color:white; padding:12px; border-radius:4px; text-align:center; font-weight:bold;">👉 Pay Now via Stripe</div></a>""", unsafe_allow_html=True)

def render_workspace_page():
    tier = st.session_state.get("locked_tier", "Standard")
    render_hero("Compose Letter", f"{tier} Edition")
    
    u_email = st.session_state.get("user_email")
    user_addr = {}
    if database and u_email:
        p = database.get_user_profile(u_email)
        if p: user_addr = {"name": p.full_name, "street": p.address_line1, "city": p.address_city, "state": p.address_state, "zip": p.address_zip}

    with st.container(border=True):
        st.subheader("📍 Addressing")
        
        # --- CIVIC LOGIC ---
        if tier == "Civic":
            c1, c2 = st.columns(2)
            with c2:
                st.markdown("**Your Address (Required for Lookup)**")
                def_n=user_addr.get("name",""); def_s=user_addr.get("street",""); def_c=user_addr.get("city",""); def_st=user_addr.get("state",""); def_z=user_addr.get("zip","")
                from_name = st.text_input("Name", value=def_n, key="w_from_name")
                from_street = st.text_input("Street", value=def_s, key="w_from_street")
                c_a, c_b, c_c = st.columns(3)
                from_city = c_a.text_input("City", value=def_c, key="w_from_city")
                from_state = c_b.text_input("State", value=def_st, key="w_from_state")
                from_zip = c_c.text_input("Zip", value=def_z, key="w_from_zip")
            
            with c1:
                st.markdown("**To: Your Representatives**")
                # Show existing targets if we have them
                if "civic_targets" in st.session_state and st.session_state.civic_targets:
                    st.success(f"✅ Found {len(st.session_state.civic_targets)} Reps:")
                    for r in st.session_state.civic_targets:
                        st.info(f"🏛️ **{r['title']}** {r['name']}")
                else:
                    st.info("Enter your address and click 'Save & Find Reps' to auto-discover your Congress people.")
                
                to_name="Civic Action"; to_street="Capitol"; to_city="DC"; to_state="DC"; to_zip="20000"

        elif tier == "Santa":
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
                def_n=user_addr.get("name",""); def_s=user_addr.get("street",""); def_c=user_addr.get("city",""); def_st=user_addr.get("state",""); def_z=user_addr.get("zip","")
                from_name = st.text_input("Name", value=def_n, key="w_from_name")
                from_street = st.text_input("Street", value=def_s, key="w_from_street")
                c_a, c_b, c_c = st.columns(3)
                from_city = c_a.text_input("City", value=def_c, key="w_from_city")
                from_state = c_b.text_input("State", value=def_st, key="w_from_state")
                from_zip = c_c.text_input("Zip", value=def_z, key="w_from_zip")

        # --- SAVE & LOOKUP BUTTON ---
        btn_label = "Save & Find Reps" if tier == "Civic" else "Save Addresses"
        if st.button(btn_label):
             st.session_state.to_addr = {"name": to_name, "street": to_street, "city": to_city, "state": to_state, "zip": to_zip}
             st.session_state.from_addr = {"name": from_name, "street": from_street, "city": from_city, "state": from_state, "zip": from_zip}
             
             # TRIGGER CIVIC LOOKUP HERE
             if tier == "Civic" and civic_engine and from_street and from_zip:
                 with st.spinner("Searching Congressional Database..."):
                     search_addr = f"{from_street}, {from_city}, {from_state} {from_zip}"
                     reps = civic_engine.get_reps(search_addr)
                     st.session_state.civic_targets = reps
                     if not reps: st.error("No reps found. Please verify address is in the US.")
                     else: st.rerun() # Rerun to show the green box above
             
             st.toast("Addresses Saved!")

    st.write("---")
    
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
    if "letter_sent_success" not in st.session_state: st.session_state.letter_sent_success = False
    
    tier = st.session_state.get("locked_tier", "Standard")
    
    # --- VISIBLE CIVIC CONFIRMATION ---
    if tier == "Civic" and "civic_targets" in st.session_state and st.session_state.civic_targets:
        st.info(f"🏛️ **This letter will be mailed to {len(st.session_state.civic_targets)} representatives:**")
        for r in st.session_state.civic_targets:
            st.markdown(f"- **{r['title']} {r['name']}**")
        st.write("---")

    txt = st.text_area("Body Content", st.session_state.get("transcribed_text", ""), height=300, disabled=st.session_state.letter_sent_success)
    st.session_state.transcribed_text = txt 
    
    if not st.session_state.letter_sent_success:
        if st.button("🚀 Send Letter", type="primary"):
            with st.spinner("Processing & Mailing..."):
                u_email = st.session_state.get("user_email")
                from_data = st.session_state.get("from_addr", {})
                
                # Signature
                sig_path = None; sig_db_value = None
                is_santa = (tier == "Santa")
                if not is_santa and st.session_state.get("sig_data") is not None:
                    try:
                        img_data = st.session_state.sig_data
                        img = Image.fromarray(img_data.astype('uint8'), 'RGBA')
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_sig:
                            img.save(tmp_sig.name); sig_path = tmp_sig.name
                        buf = io.BytesIO(); img.save(buf, format="PNG"); sig_db_value = base64.b64encode(buf.getvalue()).decode("utf-8")
                    except: pass

                # Determine Targets
                targets = []
                if tier == "Civic" and "civic_targets" in st.session_state:
                    for rep in st.session_state.civic_targets:
                        targets.append(rep['address_obj']) 
                else:
                    targets.append(st.session_state.get("to_addr", {}))

                # Loop Send
                for to_data in targets:
                    to_str = f"{to_data.get('name','')}\n{to_data.get('street','')}\n{to_data.get('city','')}, {to_data.get('state','')} {to_data.get('zip','')}"
                    if tier == "Santa": from_str = "Santa Claus"
                    else: from_str = f"{from_data.get('name','')}\n{from_data.get('street','')}\n{from_data.get('city','')}, {from_data.get('state','')} {from_data.get('zip','')}"

                    if letter_format:
                        pdf_bytes = letter_format.create_pdf(txt, to_str, from_str, is_heirloom=("Heirloom" in tier), is_santa=is_santa, signature_path=sig_path)
                        
                        postgrid_success = False
                        if (tier == "Standard" or tier == "Civic") and mailer:
                            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                                tmp.write(pdf_bytes); tmp_path = tmp.name
                            
                            pg_to = {
                                'name': to_data.get('name'), 
                                'address_line1': to_data.get('street'), 
                                'address_city': to_data.get('city'),
                                'address_state': to_data.get('state'), 
                                'address_zip': to_data.get('zip')
                            }
                            pg_from = {
                                'name': from_data.get('name'), 'address_line1': from_data.get('street'), 
                                'address_city': from_data.get('city'), 'address_state': from_data.get('state'), 'address_zip': from_data.get('zip')
                            }
                            print(f"DEBUG: Attempting PostGrid Send to {pg_to}")
                            resp = mailer.send_letter(tmp_path, pg_to, pg_from)
                            os.remove(tmp_path)
                            if resp and resp.get("id"): postgrid_success = True

                        if database:
                            final_status = "Pending Admin"
                            if tier == "Standard" or tier == "Civic":
                                final_status = "Completed" if postgrid_success else "Pending Admin"
                            database.save_draft(u_email, txt, tier, "0.00", to_addr=to_data, from_addr=from_data, status=final_status, sig_data=sig_db_value)

                if sig_path and os.path.exists(sig_path): os.remove(sig_path)
                st.session_state.letter_sent_success = True
                st.rerun()
    else:
        show_santa_animation()
        st.success("✅ Letters Queued for Delivery!")
        if st.button("🏁 Finish & Return Home"): reset_app(); st.rerun()

def show_main_app():
    if analytics: analytics.inject_ga()
    mode = st.session_state.get("app_mode", "splash")
    if "session_id" in st.query_params: st.session_state.app_mode = "workspace"; st.session_state.payment_complete = True; st.query_params.clear(); st.rerun()

    if mode == "splash": import ui_splash; ui_splash.show_splash()
    elif mode == "login": import ui_login; import auth_engine; ui_login.show_login(lambda e,p: _handle_login(auth_engine, e,p), lambda e,p,n,a,c,s,z,l: _handle_signup(auth_engine, e,p,n,a,c,s,z,l))
    elif mode == "forgot_password": import ui_login; import auth_engine; ui_login.show_forgot_password(lambda e: auth_engine.send_password_reset(e))
    elif mode == "reset_verify": import ui_login; import auth_engine; ui_login.show_reset_verify(lambda e,t,n: auth_engine.reset_password_with_token(e,t,n))
    elif mode == "store": render_store_page()
    elif mode == "workspace": render_workspace_page()
    elif mode == "review": render_review_page()
    elif mode == "legal": render_legal_page()
    elif mode == "admin": import ui_admin; ui_admin.show_admin()
    else: st.error(f"Error: Unknown App Mode '{mode}'"); st.button("Reset", on_click=reset_app)

    with st.sidebar:
        if st.button("🏠 Home"): reset_app(); st.rerun()
        if st.session_state.get("user_email"):
            st.write(f"User: {st.session_state.user_email}")
            if st.button("Logout"): st.session_state.clear(); st.rerun()

def _handle_login(auth, email, password):
    res, err = auth.sign_in(email, password)
    if res and res.user: st.session_state.user = res.user; st.session_state.user_email = res.user.email; st.session_state.app_mode = "store"; st.rerun()
    else: st.session_state.auth_error = err

def _handle_signup(auth, email, password, name, addr, city, state, zip_c, lang):
    res, err = auth.sign_up(email, password, name, addr, city, state, zip_c, lang)
    if res and res.user: st.success("Account Created! Please log in."); st.session_state.app_mode = "login"
    else: st.session_state.auth_error = err