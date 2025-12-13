import streamlit as st
from streamlit_drawable_canvas import st_canvas
import os, tempfile, json, base64, io, time, logging, hashlib
import numpy as np
from PIL import Image

# --- 1. ROBUST IMPORTS (Condensed) ---
try: import ui_splash; except ImportError: ui_splash = None
try: import ui_login; except ImportError: ui_login = None
try: import ui_admin; except ImportError: ui_admin = None
try: import ui_legal; except ImportError: ui_legal = None
try: import ui_help; except ImportError: ui_help = None
try: import ui_onboarding; except ImportError: ui_onboarding = None
try: import database; except ImportError: database = None
try: import ai_engine; except ImportError: ai_engine = None
try: import payment_engine; except ImportError: payment_engine = None
try: import letter_format; except ImportError: letter_format = None
try: import mailer; except ImportError: mailer = None
try: import analytics; except ImportError: analytics = None
try: import promo_engine; except ImportError: promo_engine = None
try: import secrets_manager; except ImportError: secrets_manager = None
try: import civic_engine; except ImportError: civic_engine = None
try: import bulk_engine; except ImportError: bulk_engine = None
try: import audit_engine; except ImportError: audit_engine = None
try: import auth_engine; except ImportError: auth_engine = None
try: import pricing_engine; except ImportError: pricing_engine = None

# --- 2. CONFIGURATION ---
logging.basicConfig(level=logging.INFO); logger = logging.getLogger(__name__)
DEFAULT_URL = "https://verbapost.streamlit.app/"
YOUR_APP_URL = DEFAULT_URL
try:
    if secrets_manager:
        found = secrets_manager.get_secret("BASE_URL")
        if found: YOUR_APP_URL = found.rstrip("/")
except: pass

COUNTRIES = {"US": "United States", "CA": "Canada", "GB": "United Kingdom", "FR": "France", "DE": "Germany", "IT": "Italy", "ES": "Spain", "AU": "Australia", "MX": "Mexico", "JP": "Japan", "BR": "Brazil", "IN": "India"}

# --- 3. HELPER FUNCTIONS: UI & STYLES ---
def inject_mobile_styles():
    st.markdown("""<style>
        @media (max-width: 768px) { .stTextInput input { font-size: 16px !important; } .stButton button { width: 100% !important; padding: 12px !important; } div[data-testid="stExpander"] { width: 100% !important; } }
        .custom-hero, .custom-hero *, .price-card, .price-card * { color: #FFFFFF !important; }
    </style>""", unsafe_allow_html=True)

def _render_hero(title, subtitle):
    st.markdown(f"""<div class="custom-hero" style="background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); padding: 30px 20px; border-radius: 15px; text-align: center; margin-bottom: 25px; box-shadow: 0 8px 16px rgba(0,0,0,0.1); max-width: 100%; box-sizing: border-box;"><h1 style="margin: 0; font-size: clamp(1.8rem, 5vw, 3rem); font-weight: 700; line-height: 1.1;">{title}</h1><div style="font-size: clamp(0.9rem, 3vw, 1.2rem); opacity: 0.95; margin-top: 8px;">{subtitle}</div></div>""", unsafe_allow_html=True)

def render_address_intervention(user_input, recommended):
    st.warning("⚠️ We found a better match for that address.")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**You Entered:**")
        st.text(f"{user_input.get('line1')}\n{user_input.get('line2') or ''}\n{user_input.get('city')}, {user_input.get('state')} {user_input.get('zip')}")
        if st.button("Use My Version (Risky)", key="btn_keep_mine"):
            st.session_state.recipient_address = user_input
            st.session_state.show_address_fix = False; st.rerun()
    with c2:
        st.markdown("**USPS Recommended:**")
        st.markdown(f"<div style='background-color:#e6ffe6; padding:10px; border-radius:5px; border:1px solid #b3ffb3; color:#006600;'>{recommended.get('line1')}<br>{recommended.get('line2') or ''}<br>{recommended.get('city')}, {recommended.get('state')} {recommended.get('zip')}</div>", unsafe_allow_html=True)
        if st.button("✅ Use Recommended", type="primary", key="btn_use_rec"):
            st.session_state.recipient_address = recommended
            st.session_state.w_to_street = recommended.get('line1')
            st.session_state.w_to_street2 = recommended.get('line2')
            st.session_state.w_to_city = recommended.get('city')
            st.session_state.w_to_state = recommended.get('state')
            st.session_state.w_to_zip = recommended.get('zip')
            st.session_state.show_address_fix = False; st.rerun()

def _render_address_book_selector(u_email):
    if not database: return
    contacts = database.get_contacts(u_email)
    if contacts:
        names = ["-- Quick Fill --"] + [c.name for c in contacts]
        def on_change():
            sel = st.session_state.get("addr_book_sel")
            if sel and sel != "-- Quick Fill --":
                match = next((c for c in contacts if c.name == sel), None)
                if match:
                    st.session_state.w_to_name = match.name; st.session_state.w_to_street = match.street; st.session_state.w_to_street2 = match.street2 or ""
                    st.session_state.w_to_city = match.city; st.session_state.w_to_state = match.state; st.session_state.w_to_zip = match.zip_code; st.session_state.w_to_country = match.country
        st.selectbox("📒 Address Book", names, key="addr_book_sel", on_change=on_change)

def _render_address_form(tier, is_intl):
    # Auto-fill Return Address
    if not st.session_state.get("w_from_name"):
        defaults = _get_user_profile_defaults(st.session_state.get("user_email"))
        if defaults:
            for k, v in defaults.items(): 
                if v: st.session_state[k] = v

    with st.form("addressing_form"):
        st.markdown("### 🏠 Return Address")
        if tier == "Santa": st.info("🎅 Sender: Santa Claus (North Pole)")
        else:
            c1, c2 = st.columns(2)
            with c1:
                st.text_input("Name", key="w_from_name", placeholder="Your Name")
                st.text_input("Street", key="w_from_street", placeholder="123 Main St")
            with c2:
                st.text_input("City", key="w_from_city", placeholder="City")
                st.text_input("State", key="w_from_state", placeholder="State")
                st.text_input("Zip", key="w_from_zip", placeholder="Zip")
            st.session_state.w_from_country = "US"

        st.markdown("---")
        st.markdown("### 📨 Recipient")
        if tier == "Civic": st.info("🏛️ Destination: Your Representatives (Auto-detected)")
        else:
            c1, c2 = st.columns(2)
            with c1:
                st.text_input("Recipient Name", key="w_to_name", placeholder="Grandma")
                st.text_input("Recipient Street", key="w_to_street", placeholder="456 Maple Ave")
            with c2:
                if is_intl:
                    st.selectbox("Country", list(COUNTRIES.keys()), key="w_to_country")
                    st.text_input("City", key="w_to_city"); st.text_input("State/Prov", key="w_to_state"); st.text_input("Postal Code", key="w_to_zip")
                else:
                    st.text_input("Recipient City", key="w_to_city"); st.text_input("Recipient State", key="w_to_state"); st.text_input("Recipient Zip", key="w_to_zip")
                    st.session_state.w_to_country = "US"
            st.checkbox("Save to Address Book", key="save_contact_opt", value=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        if st.form_submit_button("✅ Save Addresses", type="primary"):
            _save_addresses_to_state(tier)
            st.toast("Addresses Saved!")

# --- 4. HELPER FUNCTIONS: STATE & LOGIC ---
def _get_user_profile_defaults(email):
    if not database: return {}
    try:
        user = database.get_user(email)
        if user:
            return {"w_from_name": user.full_name, "w_from_street": user.address_line1, "w_from_street2": user.address_line2, "w_from_city": user.address_city, "w_from_state": user.address_state, "w_from_zip": user.address_zip, "w_from_country": user.address_country or "US"}
    except: pass
    return {}

def _save_addresses_to_state(tier):
    u = st.session_state.get("user_email")
    # From Address
    if tier == "Santa": st.session_state.from_addr = {"name": "Santa Claus", "street": "123 Elf Road", "city": "North Pole", "state": "NP", "zip": "88888", "country": "NP"}
    else: st.session_state.from_addr = {"name": st.session_state.get("w_from_name"), "street": st.session_state.get("w_from_street"), "address_line2": st.session_state.get("w_from_street2"), "city": st.session_state.get("w_from_city"), "state": st.session_state.get("w_from_state"), "zip": st.session_state.get("w_from_zip"), "country": "US", "email": u}
    # To Address
    if tier == "Civic": st.session_state.to_addr = {"name": "Civic Action", "street": "Capitol", "city": "DC", "state": "DC", "zip": "20000", "country": "US"}
    else: st.session_state.to_addr = {"name": st.session_state.get("w_to_name"), "street": st.session_state.get("w_to_street"), "address_line2": st.session_state.get("w_to_street2"), "city": st.session_state.get("w_to_city"), "state": st.session_state.get("w_to_state"), "zip": st.session_state.get("w_to_zip"), "country": st.session_state.get("w_to_country", "US")}
    # DB Sync
    if st.session_state.get("save_contact_opt", True) and database and tier != "Civic" and st.session_state.get("w_to_name"):
        try: database.add_contact(u, st.session_state.w_to_name, st.session_state.w_to_street, st.session_state.w_to_street2, st.session_state.w_to_city, st.session_state.w_to_state, st.session_state.w_to_zip)
        except: pass
    d_id = st.session_state.get("current_draft_id")
    if d_id and database: database.update_draft_data(d_id, st.session_state.to_addr, st.session_state.from_addr)

def _handle_draft_creation(email, tier, price):
    d_id = st.session_state.get("current_draft_id")
    if d_id and database: database.update_draft_data(d_id, status="Draft", tier=tier, price=price)
    else:
        if database:
            d_id = database.save_draft(email, "", tier, price)
            st.session_state.current_draft_id = d_id
            st.query_params["draft_id"] = str(d_id)
    return d_id

def reset_app(full_logout=False):
    st.query_params.clear()
    u_email = st.session_state.get("user_email")
    keys = ["audio_path", "transcribed_text", "payment_complete", "sig_data", "to_addr", "civic_targets", "bulk_targets", "bulk_paid_qty", "is_intl", "is_certified", "letter_sent_success", "locked_tier", "w_to_name", "w_to_street", "w_to_street2", "w_to_city", "w_to_state", "w_to_zip", "w_to_country", "addr_book_idx", "last_tracking_num", "campaign_errors", "current_stripe_id", "current_draft_id", "pending_stripe_url", "last_selected_contact", "addr_book_sel", "save_contact_opt", "last_send_hash", "tracked_payment_success", "tutorial_completed", "show_tutorial", "tutorial_step", "temp_user_addr", "temp_rec_addr", "show_address_fix"] 
    for k in keys: 
        if k in st.session_state: del st.session_state[k]
    st.session_state.to_addr = {}
    if full_logout:
        if "user_email" in st.session_state: del st.session_state.user_email
        st.session_state.app_mode = "splash"
    else:
        st.session_state.app_mode = "store" if u_email else "splash"

def _process_sending_logic(tier):
    # 1. Idempotency
    draft_id = st.session_state.get("current_draft_id", "0")
    idemp_key = hashlib.sha256(f"{draft_id}_{tier}_{len(st.session_state.transcribed_text)}".encode()).hexdigest()
    if st.session_state.get("last_send_hash") == idemp_key:
        st.warning("⚠️ This letter has already been queued."); return

    # 2. Validation & Targets
    if tier not in ["Campaign", "Civic"] and (not st.session_state.to_addr.get("city") or not st.session_state.to_addr.get("zip")):
        st.error("❌ Recipient Incomplete."); return
    
    targets = []
    if tier == "Campaign": targets = st.session_state.get("bulk_targets", [])
    elif tier == "Civic": 
        for r in st.session_state.get("civic_targets", []):
            if r.get('address_obj'): targets.append(r['address_obj'])
    else: targets.append(st.session_state.to_addr)
    
    if not targets: st.error("No recipients found."); return

    # 3. Processing
    with st.spinner("Processing Order..."):
        msg = """<h3 style="margin:0; color: #d35400;">🏺 Preparing Hand-Crafted Letter</h3>""" if tier in ["Heirloom", "Santa"] else """<h3 style="margin:0; color: #2a5298;">📮 Preparing Your Letter</h3>"""
        st.markdown(f"""<div style="text-align: center; padding: 20px; background-color: #f0f2f6; border-radius: 10px; margin-bottom: 20px;">{msg}</div>""", unsafe_allow_html=True)

        errs = []
        for tgt in targets:
            if not tgt.get('city'): continue 
            # PDF Gen
            to_s = f"{tgt.get('name','')}\n{tgt.get('street','')}\n{tgt.get('city','')}, {tgt.get('state','')} {tgt.get('zip','')}"
            from_s = f"{st.session_state.from_addr.get('name','')}\n{st.session_state.from_addr.get('street','')}\n{st.session_state.from_addr.get('city','')}, {st.session_state.from_addr.get('state','')} {st.session_state.from_addr.get('zip','')}"
            sig_path = None
            if st.session_state.get("sig_data") is not None:
                img = Image.fromarray(st.session_state.sig_data.astype('uint8'), 'RGBA')
                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp: img.save(tmp.name); sig_path = tmp.name
            
            pdf = letter_format.create_pdf(st.session_state.transcribed_text, to_s, from_s, (tier=="Heirloom"), (tier=="Santa"), sig_path)
            if sig_path: 
                try: os.remove(sig_path)
                except: pass

            final_status = "Failed"
            # Branch A: Manual (Heirloom/Santa)
            if tier in ["Heirloom", "Santa"]:
                time.sleep(1.5); final_status = "Manual Queue"
            # Branch B: Automated (PostGrid)
            elif mailer:
                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tpdf: tpdf.write(pdf); tpath = tpdf.name
                    pg_to = {'name': tgt.get('name'), 'line1': tgt.get('street'), 'line2': tgt.get('address_line2', ''), 'city': tgt.get('city'), 'state': tgt.get('state'), 'zip': tgt.get('zip'), 'country': 'US'}
                    pg_from = {'name': st.session_state.from_addr.get('name'), 'line1': st.session_state.from_addr.get('street'), 'line2': st.session_state.from_addr.get('address_line2', ''), 'city': st.session_state.from_addr.get('city'), 'state': st.session_state.from_addr.get('state'), 'zip': st.session_state.from_addr.get('zip'), 'country': 'US'}
                    
                    send_ok, send_res = mailer.send_letter(tpath, pg_to, pg_from, description=f"VerbaPost {tier}", is_certified=st.session_state.get("is_certified", False))
                    if send_ok: final_status = "Completed"
                    else: errs.append(f"Failed {tgt.get('name')}: {send_res}")
                except Exception as e: errs.append(f"Exception: {e}")
                finally:
                    if os.path.exists(tpath): os.remove(tpath)
            else: errs.append("Mailer module missing")

            if database:
                database.save_draft(st.session_state.user_email, st.session_state.transcribed_text, tier, "PAID", tgt, st.session_state.from_addr, final_status)

        if not errs:
            st.success("✅ Request Received!"); st.session_state.last_send_hash = idemp_key; st.session_state.letter_sent_success = True; st.rerun()
        else: st.error(f"Errors: {errs}")

# --- 5. PAGE RENDERERS ---
def render_sidebar():
    with st.sidebar:
        st.markdown("<div style='text-align: center; margin-bottom: 20px;'><h1>📮<br>VerbaPost</h1></div>", unsafe_allow_html=True)
        st.markdown("---")
        if st.session_state.get("authenticated"):
            st.info(f"👤 {st.session_state.get('user_email')}")
            if st.button("Log Out", use_container_width=True): st.session_state.clear(); st.rerun()
        else:
            st.info("👤 Guest User")
            if st.button("🔑 Log In / Sign Up", type="primary", use_container_width=True): st.session_state.app_mode = "login"; st.session_state.auth_view = "login"; st.rerun()
        
        try:
            admin_email = st.secrets.get("admin", {}).get("email", "").strip().lower()
            if st.session_state.get("authenticated") and st.session_state.get("user_email") == admin_email:
                st.write(""); st.markdown("---")
                with st.expander("🛡️ Admin Console"):
                     if st.button("Open Dashboard"): st.session_state.app_mode = "admin"; st.rerun()
        except: pass
        st.markdown("---"); st.caption("v3.3.2 (Clean)")

def render_store_page():
    if ui_onboarding: ui_onboarding.show_contextual_help("store")
    if not st.session_state.get("user_email"):
        st.warning("⚠️ Session Expired."); st.button("Go to Login", on_click=lambda: st.session_state.update(app_mode="login")); return

    _render_hero("Select Service", "Choose your letter type")
    c1, c2 = st.columns([2, 1])
    with c1:
        with st.container(border=True):
            st.subheader("Available Packages")
            labels = {"Standard": "⚡ Standard ($2.99)", "Heirloom": "🏺 Heirloom ($5.99)", "Civic": "🏛️ Civic ($6.99)", "Santa": "🎅 Santa ($9.99)", "Campaign": "📢 Campaign"}
            descs = {"Standard": "Professional print on standard paper.", "Heirloom": "Heavyweight archival stock with wet-ink style.", "Civic": "Write Congress.", "Santa": "Signed by Santa.", "Campaign": "Bulk Mail."}
            tier = st.radio("Select Tier", list(labels.keys()), format_func=lambda x: labels[x])
            st.session_state.locked_tier = tier; st.info(descs[tier])
            
            qty = 1
            if tier == "Campaign": qty = st.number_input("Recipients", 10, 5000, 50, 10)
            is_intl = False; is_certified = False
            if tier in ["Standard", "Heirloom"]:
                cc1, cc2 = st.columns(2)
                if cc1.checkbox("International (+$2.00)"): is_intl = True
                if cc2.checkbox("Certified (+$12.00)"): is_certified = True
            st.session_state.is_intl = is_intl; st.session_state.is_certified = is_certified

    with c2:
        with st.container(border=True):
            st.subheader("Checkout")
            code = st.text_input("Promo Code")
            discounted = False
            if promo_engine and code and promo_engine.validate_code(code): discounted = True; st.success("✅ Applied!")
            
            price = pricing_engine.calculate_total(tier, is_intl, is_certified, qty) if pricing_engine else 2.99
            st.metric("Total", f"${price:.2f}")
            
            if discounted:
                if st.button("🚀 Start (Free)", type="primary"):
                    _handle_draft_creation(st.session_state.user_email, tier, price)
                    st.session_state.payment_complete = True; st.session_state.app_mode = "workspace"; st.rerun()
            else:
                if st.button("💳 Generate Link", type="primary"):
                    d_id = _handle_draft_creation(st.session_state.user_email, tier, price)
                    link = f"{YOUR_APP_URL}?tier={tier}&session_id={{CHECKOUT_SESSION_ID}}&draft_id={d_id}"
                    if payment_engine:
                        url, _ = payment_engine.create_checkout_session(f"VerbaPost {tier}", int(price*100), link, YOUR_APP_URL)
                        if url: st.session_state.pending_stripe_url = url; st.rerun()
                        else: st.error("Stripe Error")
                if "pending_stripe_url" in st.session_state:
                    st.markdown(f'[👉 Pay Now]({st.session_state.pending_stripe_url})'); st.button("Reset", on_click=lambda: st.session_state.pop("pending_stripe_url"))

def render_workspace_page():
    if ui_onboarding: ui_onboarding.show_contextual_help("workspace")
    _render_hero("Workspace", "Compose your letter")
    tier = st.session_state.get("locked_tier", "Standard")
    
    if st.session_state.get("show_address_fix"):
        render_address_intervention(st.session_state.temp_user_addr, st.session_state.temp_rec_addr); return

    t1, t2 = st.tabs(["🏠 1. Addressing", "✍️ 2. Write / Dictate"])
    
    # Tab 1: Addressing
    with t1:
        _render_address_book_selector(st.session_state.get("user_email"))
        if tier == "Civic": st.info("Just need Return Address for Civic letters.")
        _render_address_form(tier, st.session_state.get("is_intl", False))
        
        if tier not in ["Civic", "Campaign"]:
            st.write("")
            if st.button("🔍 Verify Recipient Address"):
                raw = {"line1": st.session_state.get("w_to_street"), "line2": st.session_state.get("w_to_street2"), "city": st.session_state.get("w_to_city"), "state": st.session_state.get("w_to_state"), "zip": st.session_state.get("w_to_zip"), "country": "US"}
                if mailer:
                    with st.spinner("Checking..."):
                        status, clean, errs = mailer.verify_address_details(raw)
                    if status in ["verified", "corrected"]:
                        if status == "corrected": st.session_state.temp_user_addr = raw; st.session_state.temp_rec_addr = clean; st.session_state.show_address_fix = True; st.rerun()
                        else: st.success("Valid! ✅")
                    else: st.error(f"Invalid: {errs}")

    # Tab 2: Compose
    with t2:
        st.markdown("### Choose Method")
        with st.expander("🎙️ Record Voice", expanded=True):
            st.info("1. Click Mic. 2. Speak. 3. Click Done. 4. Transcribe.")
            audio = st.audio_input("Rec")
            if audio and st.button("📝 Transcribe Recording"):
                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp: tmp.write(audio.getvalue()); tmp_path = tmp.name
                if ai_engine: st.session_state.transcribed_text = ai_engine.transcribe_audio(tmp_path)
                st.rerun()
        
        with st.expander("📂 Upload File"):
            f = st.file_uploader("Audio", type=["mp3", "wav", "m4a"])
            if f and st.button("Transcribe File"):
                with tempfile.NamedTemporaryFile(delete=False, suffix=f".{f.name.split('.')[-1]}") as tmp: tmp.write(f.getvalue()); tmp_path = tmp.name
                if ai_engine: st.session_state.transcribed_text = ai_engine.transcribe_audio(tmp_path)
                st.rerun()

        st.markdown("#### ⌨️ Or Type")
        cols = st.columns(4)
        curr = st.session_state.get("transcribed_text", "")
        if ai_engine:
            if cols[0].button("Grammar"): st.session_state.transcribed_text = ai_engine.refine_text(curr, "Grammar"); st.rerun()
            if cols[1].button("Professional"): st.session_state.transcribed_text = ai_engine.refine_text(curr, "Professional"); st.rerun()
            if cols[2].button("Friendly"): st.session_state.transcribed_text = ai_engine.refine_text(curr, "Friendly"); st.rerun()
            if cols[3].button("Concise"): st.session_state.transcribed_text = ai_engine.refine_text(curr, "Concise"); st.rerun()
        
        new_val = st.text_area("Body", value=curr, height=300)
        if new_val != curr: st.session_state.transcribed_text = new_val

    st.markdown("---")
    if st.button("➡️ Review & Send", type="primary", use_container_width=True):
        st.session_state.app_mode = "review"; st.rerun()

def render_review_page():
    _render_hero("Review", "Finalize")
    if st.session_state.get("letter_sent_success"):
        st.success("✅ Sent!"); st.balloons(); 
        if st.button("Start New"): reset_app(); st.rerun()
        return

    if st.button("⬅️ Edit"): st.session_state.app_mode = "workspace"; st.rerun()
    st.text_area("Final Text", value=st.session_state.get("transcribed_text",""), disabled=True)
    
    if st.button("🚀 Send Letter", type="primary"):
        _process_sending_logic(st.session_state.get("locked_tier", "Standard"))

# --- 6. ROUTER ---
def show_main_app():
    inject_mobile_styles(); render_sidebar()
    mode = st.session_state.get("app_mode", "splash")
    if mode == "splash" and ui_splash: ui_splash.show_splash()
    elif mode == "login" and ui_login and auth_engine: ui_login.show_login(auth_engine.sign_in, auth_engine.sign_up)
    elif mode == "store": render_store_page()
    elif mode == "workspace": render_workspace_page()
    elif mode == "review": render_review_page()
    elif mode == "admin" and ui_admin: ui_admin.show_admin()
    elif mode == "legal" and ui_legal: ui_legal.show_legal()
    elif mode == "help" and ui_help: ui_help.show_help()
    else: 
        st.session_state.app_mode = "store" if st.session_state.get("authenticated") else "splash"; st.rerun()