import streamlit as st
from streamlit_drawable_canvas import st_canvas
import os
import tempfile
import json
import base64
import numpy as np
from PIL import Image
import io
import time
import logging

# --- 1. ROBUST UI IMPORTS ---
try: import ui_splash
except ImportError: ui_splash = None
try: import ui_login
except ImportError: ui_login = None
try: import ui_admin
except ImportError: ui_admin = None
try: import ui_legal
except ImportError: ui_legal = None

# --- 2. HELPER IMPORTS ---
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
try: import bulk_engine
except ImportError: bulk_engine = None
try: import audit_engine 
except ImportError: audit_engine = None
try: import auth_engine
except ImportError: auth_engine = None
try: import pricing_engine 
except ImportError: pricing_engine = None

# --- 3. CONFIGURATION ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEFAULT_URL = "https://verbapost.streamlit.app/"
YOUR_APP_URL = DEFAULT_URL
try:
    if secrets_manager:
        found_url = secrets_manager.get_secret("BASE_URL")
        if found_url: YOUR_APP_URL = found_url.rstrip("/")
except: pass

COUNTRIES = {
    "US": "United States", "CA": "Canada", "GB": "United Kingdom", "FR": "France",
    "DE": "Germany", "IT": "Italy", "ES": "Spain", "AU": "Australia", "MX": "Mexico",
    "JP": "Japan", "BR": "Brazil", "IN": "India"
}

# --- 4. SESSION MANAGEMENT ---
def reset_app(full_logout=False):
    recovered = st.query_params.get("draft_id")
    u_email = st.session_state.get("user_email")
    keys = ["audio_path", "transcribed_text", "payment_complete", "sig_data", "to_addr", 
            "civic_targets", "bulk_targets", "bulk_paid_qty", "is_intl", "is_certified", 
            "letter_sent_success", "locked_tier", "w_to_name", "w_to_street", "w_to_street2", 
            "w_to_city", "w_to_state", "w_to_zip", "w_to_country", "addr_book_idx", 
            "last_tracking_num", "campaign_errors", "current_stripe_id", "current_draft_id",
            "pending_stripe_url", "last_selected_contact", "addr_book_sel"] 
    for k in keys: 
        if k in st.session_state: del st.session_state[k]
    st.session_state.to_addr = {}
    if full_logout:
        if "user_email" in st.session_state: del st.session_state.user_email
        st.session_state.app_mode = "splash"
    else:
        if recovered:
            st.session_state.current_draft_id = recovered
            st.session_state.app_mode = "workspace" 
            st.success("🔄 Session Restored!")
        elif u_email: st.session_state.app_mode = "store"
        else: st.session_state.app_mode = "splash"

# --- 5. UI COMPONENTS ---
def render_hero(title, subtitle):
    st.markdown(f"""
    <div class="custom-hero" style="background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); padding: 40px; border-radius: 15px; text-align: center; margin-bottom: 30px; box-shadow: 0 8px 16px rgba(0,0,0,0.1); max-width: 100%; box-sizing: border-box;">
        <h1 style="margin: 0; font-size: 3rem; font-weight: 700; color: white !important;">{title}</h1>
        <div style="font-size: 1.2rem; opacity: 0.9; margin-top: 10px; color: white !important;">{subtitle}</div>
    </div>""", unsafe_allow_html=True)

def render_sidebar():
    with st.sidebar:
        st.header("VerbaPost 📮")
        st.markdown("---")
        user_email = st.session_state.get("user_email")
        if user_email:
            st.success(f"👤 **Logged in as:**\n{user_email}")
            admin_target = "tjkarat@gmail.com"
            if secrets_manager:
                sec = secrets_manager.get_secret("admin.email")
                if sec: admin_target = sec
            if str(user_email).lower().strip() == str(admin_target).lower().strip():
                if st.button("🔐 Admin Console", type="primary", use_container_width=True):
                    st.session_state.app_mode = "admin"; st.rerun()
            if st.button("🚪 Log Out", type="secondary", use_container_width=True):
                reset_app(full_logout=True); st.rerun()
        else:
            st.info("👤 **Guest User**")
            if st.button("🔑 Log In / Sign Up", type="primary", use_container_width=True):
                st.session_state.app_mode = "login"; st.rerun()
        st.markdown("---")
        mode = st.session_state.get("app_mode", "splash")
        if mode in ["workspace", "review"] and user_email:
             if st.button("🛒 Store (New Letter)", use_container_width=True):
                 st.session_state.app_mode = "store"; st.rerun()
        st.caption("v3.1.10 (Full Feature)")

# --- 6. PAGE: STORE ---
def render_store_page():
    u_email = st.session_state.get("user_email", "")
    if not u_email:
        st.warning("⚠️ Session Expired. Please log in to continue."); 
        if st.button("Go to Login"): st.session_state.app_mode = "login"; st.rerun()
        return

    render_hero("Select Service", "Choose your letter type")
    c1, c2 = st.columns([2, 1])
    with c1:
        with st.container(border=True):
            st.subheader("Available Packages")
            tier_labels = {"Standard": "⚡ Standard ($2.99)", "Heirloom": "🏺 Heirloom ($5.99)", "Civic": "🏛️ Civic ($6.99)", "Santa": "🎅 Santa ($9.99)", "Campaign": "📢 Campaign (Bulk)"}
            default_idx = 0
            stored_tier = st.session_state.get("locked_tier")
            if stored_tier and stored_tier in list(tier_labels.keys()): default_idx = list(tier_labels.keys()).index(stored_tier)
            sel = st.radio("Select Tier", list(tier_labels.keys()), index=default_idx, format_func=lambda x: tier_labels[x])
            tier_code = sel
            qty = 1
            if tier_code == "Campaign":
                qty = st.number_input("Recipients", 10, 5000, 50, 10)
                st.caption(f"Pricing: First $2.99, then $1.99/ea")
            is_intl = False; is_certified = False
            if tier_code in ["Standard", "Heirloom"]:
                c_opt1, c_opt2 = st.columns(2)
                if c_opt1.checkbox("International (+$2.00)"): is_intl = True
                if c_opt2.checkbox("Certified Mail (+$12.00)"): is_certified = True
            st.session_state.is_intl = is_intl; st.session_state.is_certified = is_certified

    with c2:
        with st.container(border=True):
            st.subheader("Checkout")
            discounted = False
            code = st.text_input("Promo Code")
            if promo_engine and code and promo_engine.validate_code(code): discounted = True; st.success("✅ Applied!")
            final_price = 0.00
            if not discounted:
                if pricing_engine: final_price = pricing_engine.calculate_total(tier_code, is_intl, is_certified, qty)
                else: final_price = 2.99 
            st.metric("Total", f"${final_price:.2f}")
            if discounted:
                if st.button("🚀 Start (Free)", type="primary", use_container_width=True):
                    _handle_draft_creation(u_email, tier_code, final_price)
                    if promo_engine: promo_engine.log_usage(code, u_email)
                    if audit_engine: audit_engine.log_event(u_email, "PROMO_USED", "FREE", {"code": code})
                    st.session_state.payment_complete = True
                    st.session_state.locked_tier = tier_code
                    st.session_state.bulk_paid_qty = qty
                    st.session_state.app_mode = "workspace"; st.rerun()
            else:
                if "pending_stripe_url" in st.session_state:
                    url = st.session_state.pending_stripe_url
                    st.success("✅ Link Generated!")
                    st.markdown(f'<a href="{url}" target="_blank" style="text-decoration: none;"><div style="display: block; width: 100%; padding: 14px; background: linear-gradient(135deg, #28a745 0%, #218838 100%); color: white; text-align: center; border-radius: 8px; font-weight: bold; font-size: 1.1rem; margin-top: 10px;">👉 Pay Now (Opens New Tab)</div></a>', unsafe_allow_html=True)
                    if st.button("Cancel / Reset"): del st.session_state.pending_stripe_url; st.rerun()
                else:
                    if st.button("💳 Generate Payment Link", type="primary", use_container_width=True):
                        d_id = _handle_draft_creation(u_email, tier_code, final_price)
                        link = f"{YOUR_APP_URL}?tier={tier_code}&session_id={{CHECKOUT_SESSION_ID}}"
                        if d_id: link += f"&draft_id={d_id}"
                        if is_intl: link += "&intl=1"
                        if is_certified: link += "&certified=1"
                        if tier_code == "Campaign": link += f"&qty={qty}"
                        if payment_engine:
                            url, sess_id = payment_engine.create_checkout_session(f"VerbaPost {tier_code}", int(final_price*100), link, YOUR_APP_URL)
                            if url:
                                if audit_engine: audit_engine.log_event(u_email, "CHECKOUT_STARTED", sess_id, {"tier": tier_code})
                                st.session_state.pending_stripe_url = url; st.rerun()
                            else: st.error("⚠️ Stripe Config Missing")

def _handle_draft_creation(email, tier, price):
    d_id = st.session_state.get("current_draft_id")
    success = False
    if d_id and database: success = database.update_draft_data(d_id, status="Draft", tier=tier, price=price)
    if not success and database:
        d_id = database.save_draft(email, "", tier, price)
        st.session_state.current_draft_id = d_id
        st.query_params["draft_id"] = str(d_id)
    return d_id

# --- 7. PAGE: WORKSPACE ---
def render_workspace_page():
    tier = st.session_state.get("locked_tier", "Standard")
    is_intl = st.session_state.get("is_intl", False)
    if "transcribed_text" not in st.session_state: st.session_state.transcribed_text = ""

    render_hero("Compose Letter", f"{tier} Edition")
    u_email = st.session_state.get("user_email")
    if database and u_email:
        p = database.get_user_profile(u_email)
        if p and "w_from_name" not in st.session_state:
            st.session_state.w_from_name = p.full_name
            st.session_state.w_from_street = p.address_line1
            st.session_state.w_from_city = p.address_city
            st.session_state.w_from_state = p.address_state
            st.session_state.w_from_zip = p.address_zip

    with st.container(border=True):
        if tier == "Campaign":
            st.subheader("📂 Upload Mailing List")
            if not bulk_engine: st.error("Bulk Engine Missing")
            f = st.file_uploader("CSV", type=['csv'])
            if f:
                c, err = bulk_engine.parse_csv(f)
                if err: st.error(err)
                else:
                    limit = st.session_state.get("bulk_paid_qty", 1000)
                    if len(c) > limit: st.error(f"🛑 List size ({len(c)}) exceeds paid quantity ({limit})."); st.session_state.bulk_targets = []
                    else:
                        st.success(f"✅ {len(c)} contacts loaded.")
                        if st.button("Confirm List"): st.session_state.bulk_targets = c; st.toast("Saved!")
        else:
            st.subheader("📍 Addressing")
            if database and tier != "Civic":
                contacts = database.get_contacts(u_email)
                if contacts:
                    contact_names = ["-- Quick Fill --"] + [c.name for c in contacts]
                    def on_contact_change():
                        selected_name = st.session_state.get("addr_book_sel")
                        if selected_name and selected_name != "-- Quick Fill --":
                            match = next((c for c in contacts if c.name == selected_name), None)
                            if match:
                                st.session_state.w_to_name = match.name
                                st.session_state.w_to_street = match.street
                                st.session_state.w_to_street2 = match.street2 or ""
                                st.session_state.w_to_city = match.city
                                st.session_state.w_to_state = match.state
                                st.session_state.w_to_zip = match.zip_code
                                st.session_state.w_to_country = match.country
                    st.selectbox("📒 Address Book", contact_names, key="addr_book_sel", on_change=on_contact_change)

            with st.form("addressing_form"):
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown("**From**")
                    if tier == "Santa": st.info("🎅 Santa Claus")
                    else:
                        st.text_input("Name", key="w_from_name")
                        st.text_input("Street", key="w_from_street")
                        st.text_input("Apt/Suite", key="w_from_street2")
                        ca, cb = st.columns(2)
                        ca.text_input("City", key="w_from_city")
                        cb.text_input("State", key="w_from_state")
                        st.text_input("Zip", key="w_from_zip")
                        st.session_state.w_from_country = "US"
                with c2:
                    st.markdown("**To**")
                    if tier == "Civic":
                        st.info("🏛️ **Auto-Detect Representatives**")
                        if "civic_targets" in st.session_state:
                            for r in st.session_state.civic_targets: st.write(f"• {r['name']} ({r['title']})")
                    else:
                        st.text_input("Name", key="w_to_name")
                        st.text_input("Street", key="w_to_street")
                        st.text_input("Apt/Suite", key="w_to_street2")
                        if is_intl:
                            st.selectbox("Country", list(COUNTRIES.keys()), key="w_to_country")
                            st.text_input("City", key="w_to_city"); st.text_input("State", key="w_to_state"); st.text_input("Postal Code", key="w_to_zip")
                        else:
                            ca, cb = st.columns(2)
                            ca.text_input("City", key="w_to_city"); cb.text_input("State", key="w_to_state"); st.text_input("Zip", key="w_to_zip")
                            st.session_state.w_to_country = "US"
                if st.form_submit_button("Save Addresses"): _save_addrs(tier); st.toast("Saved!")
            
            if tier == "Civic" and civic_engine:
                 if st.button("🔍 Find My Reps"):
                    zip_code = st.session_state.get("w_from_zip")
                    if zip_code:
                        with st.spinner("Searching..."):
                            reps = civic_engine.get_reps(f"{st.session_state.w_from_street} {st.session_state.w_from_city} {st.session_state.w_from_state} {zip_code}")
                            if reps: st.session_state.civic_targets = reps; st.success(f"Found {len(reps)} Reps!"); st.rerun()
                            else: st.error("No representatives found.")

    st.write("---")
    c_sig, c_mic = st.columns(2)
    with c_sig:
        st.write("✍️ **Signature**")
        if tier == "Santa": st.info("Signed by Santa")
        else:
            canvas = st_canvas(stroke_width=2, height=150, width=300, key="sig")
            if canvas.image_data is not None: st.session_state.sig_data = canvas.image_data
    
    with c_mic:
        st.write("🎤 **Input**")
        t1, t2 = st.tabs(["Record", "Upload"])
        with t1:
            st.info("Instructions: Click mic, speak, click stop.")
            audio = st.audio_input("Record")
            if audio:
                if st.button("Transcribe Recording", key="btn_rec"):
                    if ai_engine:
                        with st.spinner("Processing (CPU)..."): 
                            res = ai_engine.transcribe_audio(audio)
                            if not res or len(str(res).strip()) == 0: st.warning("⚠️ No speech detected.")
                            elif str(res).startswith("Error:") or str(res).startswith("[Error"): st.error(res)
                            else:
                                st.session_state.transcribed_text = res
                                st.session_state.app_mode = "review"
                                st.success("Success!")
                                time.sleep(0.1); st.rerun()

        with t2:
            st.info("Upload MP3, WAV, or M4A.")
            up = st.file_uploader("Audio File", type=['mp3','wav','m4a'])
            if up:
                if st.button("Transcribe File", key="btn_up"):
                    if ai_engine:
                        with st.spinner("Processing..."):
                            res = ai_engine.transcribe_audio(up)
                            if not res or len(str(res).strip()) == 0: st.warning("⚠️ No speech detected.")
                            elif str(res).startswith("Error:") or str(res).startswith("[Error"): st.error(res)
                            else:
                                st.session_state.transcribed_text = res
                                st.session_state.app_mode = "review"
                                time.sleep(0.1); st.rerun()

def _save_addrs(tier):
    u = st.session_state.get("user_email")
    if tier == "Santa": 
        st.session_state.from_addr = {"name": "Santa Claus", "street": "123 Elf Road", "city": "North Pole", "state": "NP", "zip": "88888", "country": "NP"}
    else:
        st.session_state.from_addr = {
            "name": st.session_state.get("w_from_name"), "street": st.session_state.get("w_from_street"),
            "address_line2": st.session_state.get("w_from_street2"), "city": st.session_state.get("w_from_city"),
            "state": st.session_state.get("w_from_state"), "zip": st.session_state.get("w_from_zip"), "country": "US", "email": u
        }
    if tier == "Civic":
        st.session_state.to_addr = {"name": "Civic Action", "street": "Capitol", "city": "DC", "state": "DC", "zip": "20000", "country": "US"}
    else:
        st.session_state.to_addr = {
            "name": st.session_state.get("w_to_name"), "street": st.session_state.get("w_to_street"),
            "address_line2": st.session_state.get("w_to_street2"), "city": st.session_state.get("w_to_city"),
            "state": st.session_state.get("w_to_state"), "zip": st.session_state.get("w_to_zip"), "country": st.session_state.get("w_to_country", "US")
        }
    
    if database and tier != "Civic" and st.session_state.get("w_to_name"):
        try: database.add_contact(u, st.session_state.w_to_name, st.session_state.w_to_street, st.session_state.w_to_street2, st.session_state.w_to_city, st.session_state.w_to_state, st.session_state.w_to_zip)
        except Exception: pass

    if mailer and st.session_state.to_addr.get('country') == "US":
        try:
            with st.spinner("Verifying Address..."):
                valid, data = mailer.verify_address_data(st.session_state.to_addr.get('street'), st.session_state.to_addr.get('address_line2'), st.session_state.to_addr.get('city'), st.session_state.to_addr.get('state'), st.session_state.to_addr.get('zip'), "US")
                if valid and data: st.session_state.to_addr.update({'street': data.get('line1'), 'city': data.get('city'), 'state': data.get('state'), 'zip': data.get('zip')}); st.success("✅ Address Verified")
        except: pass

    d_id = st.session_state.get("current_draft_id")
    if d_id and database: database.update_draft_data(d_id, st.session_state.to_addr, st.session_state.from_addr)

# --- 8. PAGE: REVIEW (Fixed) ---
def render_review_page():
    render_hero("Review", "Finalize & Send")
    if st.button("⬅️ Edit"): st.session_state.app_mode = "workspace"; st.rerun()
    
    tier = st.session_state.get("locked_tier", "Standard")
    if tier != "Campaign" and not st.session_state.get("to_addr"): _save_addrs(tier)

    c1, c2, c3, c4 = st.columns(4)
    # Ensure text exists
    current_text = st.session_state.get("transcribed_text", "")
    
    def _ai_fix(style):
        if ai_engine:
            with st.spinner("Rewriting..."): 
                st.session_state.transcribed_text = ai_engine.refine_text(current_text, style)
                st.rerun()
    
    if c1.button("Grammar"): _ai_fix("Grammar")
    if c2.button("Professional"): _ai_fix("Professional")
    if c3.button("Friendly"): _ai_fix("Friendly")
    if c4.button("Concise"): _ai_fix("Concise")

    # CRITICAL FIX: Explicitly bind value to state AND key
    # This forces the text area to show what is in session_state, fixing the "Blank Box" bug.
    new_text = st.text_area("Body", value=current_text, height=300, key="txt_body_input")
    
    # Update state if user types manually
    if new_text != current_text:
        st.session_state.transcribed_text = new_text

    st.markdown("### 📄 Letter Preview")
    
    if not current_text:
        st.warning("Please enter some text.")
    else:
        try:
            # FIX: Ensure To/From exist before PDF generation
            to_s = ""
            from_s = ""
            if st.session_state.get("to_addr"):
                d = st.session_state.to_addr
                to_s = f"{d.get('name','')}\n{d.get('street','')}\n{d.get('city','')}, {d.get('state','')} {d.get('zip','')}"
            if st.session_state.get("from_addr"):
                d = st.session_state.from_addr
                from_s = f"{d.get('name','')}\n{d.get('street','')}\n{d.get('city','')}, {d.get('state','')} {d.get('zip','')}"

            sig_path = None
            if st.session_state.get("sig_data") is not None:
                img = Image.fromarray(st.session_state.sig_data.astype('uint8'), 'RGBA')
                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp: img.save(tmp.name); sig_path=tmp.name
            
            if letter_format:
                # Use current_text (from state) so it matches what is in the box
                pdf_bytes = letter_format.create_pdf(current_text, to_s, from_s, (tier=="Heirloom"), (tier=="Santa"), sig_path)
                
                if pdf_bytes and len(pdf_bytes) > 100:
                    st.download_button(
                        label="⬇️ Download PDF Proof",
                        data=pdf_bytes,
                        file_name="letter_preview.pdf",
                        mime="application/pdf",
                        type="primary",
                        use_container_width=True
                    )
                else: st.error("Failed to generate PDF content.")
            if sig_path: 
                try: os.remove(sig_path); except: pass
        except Exception as e:
            st.error(f"Preview Failed: {e}")

    if st.button("🚀 Send Letter", type="primary"):
        # Pre-Flight Check
        to_check = st.session_state.get("to_addr", {})
        if tier != "Campaign" and tier != "Civic":
            if not to_check.get("city") or not to_check.get("zip"):
                st.error("❌ Recipient Address Incomplete!")
                return

        targets = []
        if tier == "Campaign": targets = st.session_state.get("bulk_targets", [])
        elif tier == "Civic": 
            for r in st.session_state.get("civic_targets", []):
                t = r.get('address_obj'); 
                if t: t['country']='US'; targets.append(t)
        else: targets.append(st.session_state.to_addr)
        
        if not targets: st.error("No recipients found."); return

        with st.spinner("Sending..."):
            errs = []
            for tgt in targets:
                if not tgt.get('city'): continue 
                
                def _fmt(d): return f"{d.get('name','')}\n{d.get('street','')}\n{d.get('city','')}, {d.get('state','')} {d.get('zip','')}"
                to_s = _fmt(tgt)
                from_s = _fmt(st.session_state.from_addr)
                
                sig_path = None
                if st.session_state.get("sig_data") is not None:
                    img = Image.fromarray(st.session_state.sig_data.astype('uint8'), 'RGBA')
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp: img.save(tmp.name); sig_path=tmp.name
                
                pdf = letter_format.create_pdf(st.session_state.transcribed_text, to_s, from_s, (tier=="Heirloom"), (tier=="Santa"), sig_path)
                if sig_path: 
                    try: os.remove(sig_path); except: pass

                is_ok = False
                if mailer:
                    pg_to = {'name': tgt.get('name'), 'address_line1': tgt.get('street'), 'address_line2': tgt.get('address_line2', ''), 'address_city': tgt.get('city'), 'address_state': tgt.get('state'), 'address_zip': tgt.get('zip'), 'country_code': 'US'}
                    pg_from = {'name': st.session_state.from_addr.get('name'), 'address_line1': st.session_state.from_addr.get('street'), 'address_line2': st.session_state.from_addr.get('address_line2', ''), 'address_city': st.session_state.from_addr.get('city'), 'address_state': st.session_state.from_addr.get('state'), 'address_zip': st.session_state.from_addr.get('zip'), 'country_code': 'US'}
                    try:
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tpdf: tpdf.write(pdf); tpath=tpdf.name
                        ok, res = mailer.send_letter(tpath, pg_to, pg_from, st.session_state.get("is_certified", False))
                        if ok: is_ok=True
                        else: errs.append(f"Failed {tgt.get('name')}: {res}")
                    except Exception as e: errs.append(str(e))
                    finally:
                        if os.path.exists(tpath): 
                            try: os.remove(tpath); except: pass

                if database:
                    status = "Completed" if is_ok else "Failed"
                    database.save_draft(st.session_state.user_email, st.session_state.transcribed_text, tier, "PAID", tgt, st.session_state.from_addr, status)

            if not errs:
                st.success("✅ All Sent!"); st.session_state.letter_sent_success = True
                if st.button("Start New"): reset_app(); st.rerun()
            else: st.error("Errors occurred"); st.write(errs)

def show_main_app():
    if analytics: analytics.inject_ga()
    render_sidebar()
    mode = st.session_state.get("app_mode", "splash")
    if mode == "splash" and ui_splash: ui_splash.show_splash()
    elif mode == "login" and ui_login and auth_engine: ui_login.show_login(auth_engine.sign_in, auth_engine.sign_up)
    elif mode == "store": render_store_page()
    elif mode == "workspace": render_workspace_page()
    elif mode == "review": render_review_page()
    elif mode == "admin" and ui_admin: ui_admin.show_admin()
    elif mode == "legal" and ui_legal: ui_legal.show_legal()
    else: st.session_state.app_mode = "store"; st.rerun()

def _h_login(auth, e, p):
    res, err = auth.sign_in(e, p)
    if res and res.user: st.session_state.user_email = res.user.email; st.session_state.app_mode = "store"; st.rerun()
    else: st.error(err)

def _h_signup(auth, e, p, n, a, a2, c, s, z, cn, l):
    res, err = auth.sign_up(e, p, n, a, a2, c, s, z, cn, l)
    if res and res.user: st.success("Created! Please Log In."); st.session_state.app_mode = "login"
    else: st.error(err)