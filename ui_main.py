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

# --- INTERNATIONAL CONFIG ---
COUNTRIES = {
    "US": "United States", "CA": "Canada", "GB": "United Kingdom", "FR": "France",
    "DE": "Germany", "IT": "Italy", "ES": "Spain", "AU": "Australia", "MX": "Mexico",
    "JP": "Japan", "BR": "Brazil", "IN": "India"
}

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
    st.session_state.is_intl = False
    
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
    import ui_legal
    ui_legal.show_legal()

def render_store_page():
    render_hero("Select Service", "Choose your letter type")
    u_email = st.session_state.get("user_email", "")
    
    # --- ROBUST ADMIN CHECK ---
    is_admin = False
    try:
        if secrets_manager:
            admin_target = secrets_manager.get_secret("admin.email")
            if admin_target and str(u_email).lower() == str(admin_target).lower():
                is_admin = True
        if not is_admin and "admin" in st.secrets:
            admin_target = st.secrets["admin"].get("email")
            if admin_target and str(u_email).lower() == str(admin_target).lower():
                is_admin = True
    except: pass

    if is_admin:
        if st.button("🔐 Open Admin Console", type="secondary"):
            st.session_state.app_mode = "admin"; st.rerun()

    c1, c2 = st.columns([2, 1])
    with c1:
        with st.container(border=True):
            st.subheader("Available Packages")
            
            # --- TIER SETUP ---
            tier_options_list = ["Standard", "Heirloom", "Civic", "Santa"]
            tier_labels = {
                "Standard": "⚡ Standard ($2.99)",
                "Heirloom": "🏺 Heirloom ($5.99)",
                "Civic": "🏛️ Civic ($6.99)",
                "Santa": "🎅 Santa ($9.99)"
            }
            
            # --- DESCRIPTIONS ---
            tier_descriptions = {
                "Standard": "Your words professionally printed on standard paper and mailed via USPS First Class.",
                "Heirloom": "Printed on heavyweight archival stock with a wet-ink style font for a timeless look.",
                "Civic": "We automatically identify your local representatives and mail physical letters to them.",
                "Santa": "A magical letter from the North Pole on festive paper, signed by Santa Claus himself."
            }
            
            pre_selected_index = 0
            if "target_marketing_tier" in st.session_state:
                target = st.session_state.target_marketing_tier
                if target in tier_options_list:
                    pre_selected_index = tier_options_list.index(target)
            
            sel = st.radio(
                "Select Tier", 
                tier_options_list, 
                format_func=lambda x: tier_labels[x],
                index=pre_selected_index,
                key="tier_selection_radio" 
            )
            tier_code = sel
            
            # Show Description
            st.info(tier_descriptions[tier_code])
            
            prices = {"Standard": 2.99, "Heirloom": 5.99, "Civic": 6.99, "Santa": 9.99}
            price = prices[tier_code]

            # --- INTERNATIONAL TOGGLE ---
            is_intl = False
            if tier_code in ["Standard", "Heirloom"]:
                is_intl = st.checkbox("Send Internationally? (+$2.00)", key="intl_toggle_check")
                if is_intl:
                    price += 2.00
                    st.session_state.is_intl = True
                else:
                    st.session_state.is_intl = False
            else:
                st.session_state.is_intl = False

    with c2:
        with st.container(border=True):
            st.subheader("Checkout")
            discounted = False
            if promo_engine:
                code_input = st.text_input("Promo Code", key="promo_box")
                if code_input and promo_engine.validate_code(code_input):
                    discounted = True
                    st.success("✅ Code Applied!")
            
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
                st.metric("Total", f"${price:.2f}")
                if st.button(f"Pay ${price:.2f} & Start", type="primary", use_container_width=True):
                    if database: database.save_draft(u_email, "", tier_code, price)
                    
                    # --- STRIPE LINK BUILDER ---
                    link = f"{YOUR_APP_URL}?tier={tier_code}&session_id={{CHECKOUT_SESSION_ID}}"
                    if is_intl: link += "&intl=1"
                    
                    if payment_engine:
                        url, sess_id = payment_engine.create_checkout_session(tier_code, int(price*100), link, YOUR_APP_URL)
                        if url:
                            st.markdown(f"""<a href="{url}" target="_blank" style="text-decoration:none;"><div style="background-color:#6772e5; color:white; padding:12px; border-radius:4px; text-align:center; font-weight:bold;">👉 Pay Now via Stripe</div></a>""", unsafe_allow_html=True)

def render_workspace_page():
    tier = st.session_state.get("locked_tier", "Standard")
    is_intl = st.session_state.get("is_intl", False)
    
    title_suffix = " (International)" if is_intl else ""
    render_hero("Compose Letter", f"{tier} Edition{title_suffix}")
    
    # --- FETCH USER PROFILE FOR DEFAULTS ---
    u_email = st.session_state.get("user_email")
    user_addr = {}
    if database and u_email:
        p = database.get_user_profile(u_email)
        if p: 
            user_addr = {
                "name": p.full_name, "street": p.address_line1, 
                "city": p.address_city, "state": p.address_state, 
                "zip": p.address_zip,
                "country": getattr(p, "country", "US") 
            }

    with st.container(border=True):
        st.subheader("📍 Addressing")
        
        # --- 1. SENDER SECTION ---
        # Defaults
        def_n=user_addr.get("name",""); def_s=user_addr.get("street","")
        def_c=user_addr.get("city",""); def_st=user_addr.get("state","")
        def_z=user_addr.get("zip",""); def_cntry=user_addr.get("country","US")
        
        # SANTA EXCEPTION
        if tier == "Santa":
            st.info("🎅 **From:** Santa Claus, North Pole (Locked)")
            # We don't save these to widgets, just to state later
            st.session_state.w_santa_mode = True 
        
        # CIVIC EXCEPTION
        elif tier == "Civic":
             st.markdown("**(From) Your Voting Address**")
             st.text_input("Name", value=def_n, key="w_from_name")
             st.text_input("Street", value=def_s, key="w_from_street")
             c_a, c_b, c_c = st.columns([2, 1, 1])
             c_a.text_input("City", value=def_c, key="w_from_city")
             c_b.text_input("State", value=def_st, key="w_from_state")
             c_c.text_input("Zip", value=def_z, key="w_from_zip")
             # Hidden country field for Civic (always US)
             st.session_state.w_from_country = "US"
             st.caption("We use this to find your representatives.")

        # STANDARD/HEIRLOOM
        else:
            with st.expander(f"✉️ From: {def_n} (Click to Edit)", expanded=False):
                st.text_input("Sender Name", value=def_n, key="w_from_name")
                st.text_input("Sender Street", value=def_s, key="w_from_street")
                
                # Auto-select user's country
                try: c_idx = list(COUNTRIES.keys()).index(def_cntry)
                except: c_idx = 0
                
                c_scntry, c_scity = st.columns([1, 2])
                c_scntry.selectbox("From Country", list(COUNTRIES.keys()), format_func=lambda x: COUNTRIES[x], index=c_idx, key="w_from_country")
                c_scity.text_input("Sender City", value=def_c, key="w_from_city")

                c_sstate, c_szip = st.columns([1, 1])
                # Note: We rely on the session state update for labels to shift, might need rerun, but defaults work.
                c_sstate.text_input("State/Prov", value=def_st, key="w_from_state")
                c_szip.text_input("Zip/Postal", value=def_z, key="w_from_zip")

        # --- 2. RECIPIENT SECTION ---
        if tier != "Civic":
            st.markdown("---")
            st.markdown("**📮 To (Recipient)**")
            
            st.text_input("Recipient Name", key="w_to_name")
            st.text_input("Recipient Street", key="w_to_street")
            
            if is_intl:
                c_cntry, c_city = st.columns([1, 2])
                c_cntry.selectbox("Recipient Country", list(COUNTRIES.keys()), format_func=lambda x: COUNTRIES[x], index=0, key="w_to_country")
                c_city.text_input("Recipient City", key="w_to_city")
                c_state, c_zip = st.columns([1, 1])
                c_state.text_input("State/Province", key="w_to_state")
                c_zip.text_input("Postal Code", key="w_to_zip")
            else:
                c_city, c_state, c_zip = st.columns([2, 1, 1])
                c_city.text_input("City", key="w_to_city")
                c_state.text_input("State", key="w_to_state")
                c_zip.text_input("Zip", key="w_to_zip")
                # Implicit US
                st.session_state.w_to_country = "US"

        # --- SAVE BUTTON ---
        st.markdown("<br>", unsafe_allow_html=True)
        btn_label = "Save & Find Reps" if tier == "Civic" else "Save Addresses"
        
        if st.button(btn_label, type="primary"):
             # EXPLICIT SAVE (Legacy)
             _save_addresses_from_widgets(tier, is_intl)
             
             if tier == "Civic" and civic_engine:
                 with st.spinner("Searching Congressional Database..."):
                     # Re-grab from session to be safe
                     fs = st.session_state.w_from_street; fc = st.session_state.w_from_city
                     fst = st.session_state.w_from_state; fz = st.session_state.w_from_zip
                     search_addr = f"{fs}, {fc}, {fst} {fz}"
                     reps = civic_engine.get_reps(search_addr)
                     st.session_state.civic_targets = reps
                     if not reps: st.error("No reps found. Verify US address.")
                     else: st.rerun()
             st.toast("Addresses Saved!")

    st.write("---")
    
    # --- SIGNATURE & DICTATION ---
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

# --- HELPER: AUTO-SAVE LOGIC ---
def _save_addresses_from_widgets(tier, is_intl):
    """Pulls data from widgets (w_ prefix) and saves to main state dicts."""
    
    # 1. FROM ADDRESS
    if tier == "Santa":
        st.session_state.from_addr = {
            "name": "Santa Claus", "street": "123 Elf Road", 
            "city": "North Pole", "state": "NP", "zip": "88888", "country": "NP"
        }
    else:
        # Standard/Heirloom/Civic use widgets
        f_cntry = st.session_state.get("w_from_country", "US")
        st.session_state.from_addr = {
            "name": st.session_state.get("w_from_name"),
            "street": st.session_state.get("w_from_street"),
            "city": st.session_state.get("w_from_city"),
            "state": st.session_state.get("w_from_state"),
            "zip": st.session_state.get("w_from_zip"),
            "country": f_cntry
        }

    # 2. TO ADDRESS
    if tier == "Civic":
        st.session_state.to_addr = {
            "name": "Civic Action", "street": "Capitol", "city": "DC", "state": "DC", "zip": "20000", "country": "US"
        }
    else:
        t_cntry = st.session_state.get("w_to_country", "US")
        st.session_state.to_addr = {
            "name": st.session_state.get("w_to_name"),
            "street": st.session_state.get("w_to_street"),
            "city": st.session_state.get("w_to_city"),
            "state": st.session_state.get("w_to_state"),
            "zip": st.session_state.get("w_to_zip"),
            "country": t_cntry
        }

def render_review_page():
    render_hero("Review Letter", "Finalize and Send")
    if "letter_sent_success" not in st.session_state: st.session_state.letter_sent_success = False
    
    tier = st.session_state.get("locked_tier", "Standard")
    is_intl = st.session_state.get("is_intl", False)

    # --- THE FIX: AUTO-SAVE CHECK ---
    # If the user skipped the "Save" button, we run the save logic now.
    if not st.session_state.get("to_addr") or not st.session_state.get("from_addr"):
        _save_addresses_from_widgets(tier, is_intl)
    # --------------------------------

    if tier == "Civic" and "civic_targets" in st.session_state and st.session_state.civic_targets:
        st.info(f"🏛️ **This letter will be mailed to {len(st.session_state.civic_targets)} representatives:**")
        for r in st.session_state.civic_targets:
            st.markdown(f"- **{r['title']} {r['name']}**")
        st.write("---")

    txt = st.text_area("Body Content", st.session_state.get("transcribed_text", ""), height=300, disabled=st.session_state.letter_sent_success)
    st.session_state.transcribed_text = txt 
    
    if not st.session_state.letter_sent_success:
        if st.button("🚀 Send Letter", type="primary"):
            
            # LAST DITCH VALIDATION
            to_chk = st.session_state.get("to_addr", {})
            from_chk = st.session_state.get("from_addr", {})
            if not to_chk.get("street") and tier != "Civic":
                st.error("⚠️ Recipient Address missing. Please go back and enter details.")
                return
            if not from_chk.get("street") and tier != "Santa":
                st.error("⚠️ Sender Address missing. Please go back and enter details.")
                return

            with st.spinner("Processing & Mailing..."):
                u_email = st.session_state.get("user_email")
                from_data = st.session_state.from_addr
                
                # Signature Prep
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

                # Build Targets
                targets = []
                if tier == "Civic" and "civic_targets" in st.session_state:
                    for rep in st.session_state.civic_targets:
                        t = rep['address_obj']; t['country'] = 'US'; targets.append(t) 
                else:
                    targets.append(st.session_state.to_addr)

                # Loop Send
                for to_data in targets:
                    t_country = to_data.get('country', 'US')
                    cntry_line = f"\n{COUNTRIES.get(t_country, 'USA')}" if t_country != 'US' else ""
                    to_str = f"{to_data.get('name','')}\n{to_data.get('street','')}\n{to_data.get('city','')}, {to_data.get('state','')} {to_data.get('zip','')}{cntry_line}"
                    
                    if tier == "Santa": from_str = "Santa Claus"
                    else: 
                        f_country = from_data.get('country', 'US')
                        f_cntry_line = f"\n{COUNTRIES.get(f_country, 'USA')}" if f_country != 'US' else ""
                        from_str = f"{from_data.get('name','')}\n{from_data.get('street','')}\n{from_data.get('city','')}, {from_data.get('state','')} {from_data.get('zip','')}{f_cntry_line}"

                    if letter_format:
                        pdf_bytes = letter_format.create_pdf(txt, to_str, from_str, is_heirloom=("Heirloom" in tier), is_santa=is_santa, signature_path=sig_path)
                        
                        postgrid_success = False
                        if (tier == "Standard" or tier == "Civic") and mailer:
                            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                                tmp.write(pdf_bytes); tmp_path = tmp.name
                            
                            # MAP TO POSTGRID KEYS
                            pg_to = {
                                'name': to_data.get('name'), 'address_line1': to_data.get('street'), 
                                'address_city': to_data.get('city'), 'address_state': to_data.get('state'), 
                                'address_zip': to_data.get('zip'), 'country_code': to_data.get('country', 'US')
                            }
                            pg_from = {
                                'name': from_data.get('name'), 'address_line1': from_data.get('street'), 
                                'address_city': from_data.get('city'), 'address_state': from_data.get('state'), 
                                'address_zip': from_data.get('zip'), 'country_code': from_data.get('country', 'US')
                            }
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
        if st.button("🏁 Finish & Return Home"): 
             reset_app()
             st.rerun()

def show_main_app():
    if analytics: analytics.inject_ga()
    mode = st.session_state.get("app_mode", "splash")
    
    # Catch redirect from Stripe but handled in main.py already
    if "session_id" in st.query_params: 
        st.session_state.app_mode = "workspace" 
        st.session_state.payment_complete = True 
        st.query_params.clear() 
        st.rerun()

    if mode == "splash": import ui_splash; ui_splash.show_splash()
    elif mode == "login": 
        import ui_login; import auth_engine
        ui_login.show_login(
            lambda e,p: _handle_login(auth_engine, e,p), 
            lambda e,p,n,a,c,s,z,cntry,l: _handle_signup(auth_engine, e,p,n,a,c,s,z,cntry,l)
        )
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

def _handle_signup(auth, email, password, name, addr, city, state, zip_c, country, lang):
    res, err = auth.sign_up(email, password, name, addr, city, state, zip_c, country, lang)
    if res and res.user: st.success("Account Created! Please log in."); st.session_state.app_mode = "login"
    else: st.session_state.auth_error = err