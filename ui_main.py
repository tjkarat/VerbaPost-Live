import streamlit as st
import os
import tempfile
import json
import base64
import numpy as np
from PIL import Image
import io
import time
import logging

# --- 1. CONFIGURATION ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- 2. DEFENSIVE IMPORTS ---
def safe_import(module_name):
    try:
        return __import__(module_name)
    except Exception as e:
        logger.error(f"Failed to load {module_name}: {e}")
        return None

ui_splash = safe_import("ui_splash")
ui_login = safe_import("ui_login")
ui_admin = safe_import("ui_admin")
ui_legal = safe_import("ui_legal")

database = safe_import("database")
ai_engine = safe_import("ai_engine")
payment_engine = safe_import("payment_engine")
letter_format = safe_import("letter_format")
mailer = safe_import("mailer")
analytics = safe_import("analytics")
promo_engine = safe_import("promo_engine")
secrets_manager = safe_import("secrets_manager")
civic_engine = safe_import("civic_engine")
bulk_engine = safe_import("bulk_engine")
audit_engine = safe_import("audit_engine")
auth_engine = safe_import("auth_engine")
pricing_engine = safe_import("pricing_engine")

try: from address_standard import StandardAddress
except Exception: StandardAddress = None

# --- 3. APP SETUP ---
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
    
    keys = ["audio_path", "transcribed_text", "payment_complete", "sig_data", "sig_text", 
            "to_addr", "from_addr", "civic_targets", "bulk_targets", "bulk_paid_qty", 
            "is_intl", "is_certified", "letter_sent_success", "locked_tier", 
            "w_to_name", "w_to_street", "w_to_street2", "w_to_city", "w_to_state", "w_to_zip", "w_to_country", 
            "w_from_name", "w_from_street", "w_from_city", "w_from_state", "w_from_zip",
            "addr_book_idx", "last_tracking_num", "campaign_errors", "current_stripe_id", "current_draft_id"]
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
        elif u_email: 
            st.session_state.app_mode = "store"
        else: 
            st.session_state.app_mode = "splash"

def check_session():
    if st.query_params.get("session_id"): return True
    if "user_email" not in st.session_state or not st.session_state.user_email:
        st.warning("⚠️ Session Expired. Please log in.")
        st.session_state.app_mode = "login"
        st.rerun()
        return False
    return True

# --- 5. UI COMPONENTS ---
def render_hero(title, subtitle):
    st.markdown(f"""<div class="custom-hero" style="background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); padding: 40px; border-radius: 15px; text-align: center; margin-bottom: 30px; box-shadow: 0 8px 16px rgba(0,0,0,0.1);"><h1 style="margin: 0; font-size: 3rem; font-weight: 700; color: white !important;">{title}</h1><div style="font-size: 1.2rem; opacity: 0.9; margin-top: 10px; color: white !important;">{subtitle}</div></div>""", unsafe_allow_html=True)

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
             if st.button("🛒 Store (New Letter)", icon="🛍️", use_container_width=True):
                 st.session_state.app_mode = "store"; st.rerun()

        st.markdown("### Support")
        if st.button("⚖️ Legal & Privacy", use_container_width=True):
            st.session_state.app_mode = "legal"; st.rerun()
        st.caption("v3.0.5 Stable")

# --- 6. PAGE: STORE ---
def render_store_page():
    u_email = st.session_state.get("user_email", "")
    if not u_email:
        st.warning("⚠️ Session Expired. Please log in to continue.")
        if st.button("Go to Login"):
            st.session_state.app_mode = "login"; st.rerun()
        return

    render_hero("Select Service", "Choose your letter type")
    
    if not database:
        st.error("⚠️ Database connection failed. Please contact support.")
    
    c1, c2 = st.columns([2, 1])
    with c1:
        with st.container(border=True):
            st.subheader("Available Packages")
            tier_labels = {"Standard": "⚡ Standard ($2.99)", "Heirloom": "🏺 Heirloom ($5.99)", "Civic": "🏛️ Civic ($6.99)", "Santa": "🎅 Santa ($9.99)", "Campaign": "📢 Campaign (Bulk)"}
            tier_desc = {
                "Standard": "Professional print on standard paper. Mailed USPS First Class.",
                "Heirloom": "Heavyweight archival stock with wet-ink style font.",
                "Civic": "We identify your local reps and mail them physical letters.",
                "Santa": "Magical letter from North Pole, signed by Santa.",
                "Campaign": "Upload CSV. We mail everyone at once."
            }
            sel = st.radio("Select Tier", list(tier_labels.keys()), format_func=lambda x: tier_labels[x])
            st.info(tier_desc.get(sel, ""))
            st.session_state.locked_tier = sel
            
            qty = 1
            if sel == "Campaign": qty = st.number_input("Recipients", 10, 5000, 50, 10)
            
            st.session_state.is_intl = False; st.session_state.is_certified = False
            if sel in ["Standard", "Heirloom"]:
                c_opt1, c_opt2 = st.columns(2)
                st.session_state.is_intl = c_opt1.checkbox("International (+$2.00)")
                st.session_state.is_certified = c_opt2.checkbox("Certified Mail (+$12.00)")

    with c2:
        with st.container(border=True):
            st.subheader("Checkout")
            discounted = False
            code = st.text_input("Promo Code")
            if promo_engine and code and promo_engine.validate_code(code): 
                discounted = True; st.success("✅ Applied!")
            
            final_price = 0.00
            if not discounted:
                if pricing_engine:
                    final_price = pricing_engine.calculate_total(sel, st.session_state.is_intl, st.session_state.is_certified, qty)
                else:
                    final_price = 2.99 
            
            st.metric("Total", f"${final_price:.2f}")
            
            btn_txt = "🚀 Start (Free)" if discounted else f"Pay ${final_price:.2f} & Start"
            
            if st.button(btn_txt, type="primary", use_container_width=True, disabled=(not database)):
                d_id = _handle_draft_creation(u_email, sel, final_price)

                if discounted:
                    if promo_engine: promo_engine.log_usage(code, u_email)
                    st.session_state.payment_complete = True
                    st.session_state.locked_tier = sel
                    st.session_state.bulk_paid_qty = qty
                    st.session_state.app_mode = "workspace"; st.rerun()
                else:
                    link = f"{YOUR_APP_URL}?tier={sel}&session_id={{CHECKOUT_SESSION_ID}}"
                    if d_id: link += f"&draft_id={d_id}"
                    if st.session_state.is_intl: link += "&intl=1"
                    if st.session_state.is_certified: link += "&certified=1"
                    if sel == "Campaign": link += f"&qty={qty}"
                    
                    if payment_engine:
                        # Use DEBUG create session to catch errors
                        url, _ = payment_engine.create_checkout_session(f"VerbaPost {sel}", int(final_price*100), link, YOUR_APP_URL)
                        if url: 
                            st.markdown(f'<a href="{url}" target="_self"><button style="width:100%;padding:10px;background:#635bff;color:white;border:none;border-radius:5px;cursor:pointer;">👉 Pay Now</button></a>', unsafe_allow_html=True)
                        else:
                            st.error("Stripe Link Generation Failed. Check Debug Logs.")

def _handle_draft_creation(email, tier, price):
    d_id = st.session_state.get("current_draft_id")
    success = False
    
    if d_id and database:
        success = database.update_draft_data(d_id, status="Draft", tier=tier, price=price)
    
    if not success and database:
        d_id = database.save_draft(email, "", tier, price)
        st.session_state.current_draft_id = d_id
        st.query_params["draft_id"] = str(d_id)
        if success is False: st.warning("⚠️ Session recovered (Previous draft was missing).")
        
    return d_id

# --- 7. PAGE: WORKSPACE (FULL) ---
def render_workspace_page():
    # --- CRITICAL FIX: LAZY IMPORT CANVAS ---
    # This prevents the white screen crash on app load
    try: 
        from streamlit_drawable_canvas import st_canvas
    except Exception: 
        st_canvas = None

    tier = st.session_state.get("locked_tier", "Standard")
    is_intl = st.session_state.get("is_intl", False)
    render_hero("Compose Letter", f"{tier} Edition")
    
    u_email = st.session_state.get("user_email")
    
    # --- 1. ADDRESS SYNC LOGIC ---
    if database and u_email:
        p = database.get_user_profile(u_email)
        if p and "w_from_name" not in st.session_state:
            st.session_state.w_from_name = p.full_name
            st.session_state.w_from_street = p.address_line1
            st.session_state.w_from_city = p.address_city
            st.session_state.w_from_state = p.address_state
            st.session_state.w_from_zip = p.address_zip

    if "to_addr" in st.session_state and st.session_state.to_addr and "w_to_name" not in st.session_state:
        data = st.session_state.to_addr
        st.session_state.w_to_name = data.get("name", "")
        st.session_state.w_to_street = data.get("street", "")
        st.session_state.w_to_street2 = data.get("address_line2", "")
        st.session_state.w_to_city = data.get("city", "")
        st.session_state.w_to_state = data.get("state", "")
        st.session_state.w_to_zip = data.get("zip", "")
        st.session_state.w_to_country = data.get("country", "US")

    with st.container(border=True):
        if tier == "Campaign":
            # --- CAMPAIGN LOGIC ---
            st.subheader("📂 Upload Mailing List")
            if not bulk_engine: st.error("Bulk Engine Missing")
            f = st.file_uploader("CSV (Name, Street, City, State, Zip)", type=['csv'])
            if f:
                c, err = bulk_engine.parse_csv(f)
                if err: st.error(err)
                else:
                    limit = st.session_state.get("bulk_paid_qty", 1000)
                    if len(c) > limit: 
                        st.error(f"🛑 List size ({len(c)}) exceeds paid quantity ({limit}). Please reduce list or upgrade.")
                        st.session_state.bulk_targets = []
                    else:
                        st.success(f"✅ {len(c)} contacts loaded.")
                        if st.button("Confirm List"): st.session_state.bulk_targets = c; st.toast("Saved!")
        else:
            # --- STANDARD ADDRESSING ---
            st.subheader("📍 Addressing")
            c1, c2 = st.columns(2)
            
            with c1: # FROM
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

            with c2: # TO
                st.markdown("**To**")
                if tier == "Civic":
                    # --- CIVIC LOGIC ---
                    st.info("🏛️ **Auto-Detect Representatives**")
                    zip_code = st.session_state.get("w_from_zip")
                    if not zip_code: st.warning("Enter your Zip Code in the 'From' section first.")
                    elif civic_engine:
                        if st.button("🔍 Find My Reps"):
                            with st.spinner("Searching..."):
                                reps = civic_engine.get_reps(f"{st.session_state.w_from_street} {st.session_state.w_from_city} {st.session_state.w_from_state} {zip_code}")
                                if reps: 
                                    st.session_state.civic_targets = reps
                                    st.success(f"Found {len(reps)} Reps!")
                                else: st.error("No representatives found for this address.")
                    
                    if "civic_targets" in st.session_state:
                        for r in st.session_state.civic_targets: st.write(f"• {r['name']} ({r['title']})")

                else:
                    # --- ADDRESS BOOK ---
                    if database:
                        cons = database.get_contacts(u_email)
                        if cons:
                            names = ["-- Quick Fill --"] + [x.name for x in cons]
                            sel = st.selectbox("Address Book", names)
                            if sel != "-- Quick Fill --":
                                c = next(x for x in cons if x.name == sel)
                                st.session_state.w_to_name = c.name
                                st.session_state.w_to_street = c.street
                                st.session_state.w_to_city = c.city
                                st.session_state.w_to_state = c.state
                                st.session_state.w_to_zip = c.zip_code
                                st.rerun()

                    st.text_input("Name", key="w_to_name")
                    st.text_input("Street", key="w_to_street")
                    st.text_input("Apt/Suite", key="w_to_street2")
                    
                    if is_intl:
                        st.selectbox("Country", list(COUNTRIES.keys()), key="w_to_country")
                        st.text_input("City", key="w_to_city")
                        st.text_input("State/Prov", key="w_to_state")
                        st.text_input("Postal Code", key="w_to_zip")
                    else:
                        ca, cb = st.columns(2)
                        ca.text_input("City", key="w_to_city")
                        cb.text_input("State", key="w_to_state")
                        st.text_input("Zip", key="w_to_zip")
                        st.session_state.w_to_country = "US"

            if st.button("Save Addresses", type="primary"):
                _save_addrs(tier)
                st.toast("✅ Addresses Saved!")

    st.write("---")
    # Dictation / Signature
    c_sig, c_mic = st.columns(2)
    with c_sig:
        st.write("✍️ **Signature**")
        if tier == "Santa": st.info("Signed by Santa")
        else:
            # --- FALLBACK SIGNATURE ---
            use_text_sig = st.checkbox("Type signature instead?", value=False)
            
            if use_text_sig:
                sig_text = st.text_input("Type your name to sign", key="txt_sig_input")
                if sig_text: 
                    st.session_state.sig_data = None 
                    st.session_state.sig_text = sig_text
            elif st_canvas: 
                try:
                    canvas = st_canvas(stroke_width=2, height=150, width=400, key="sig")
                    if canvas.image_data is not None: st.session_state.sig_data = canvas.image_data
                except Exception: 
                    st.warning("Canvas Error - Please use 'Type signature' checkbox above.")
            else:
                st.warning("Signature component unavailable.")
    
    with c_mic:
        st.write("🎤 **Input**")
        t1, t2 = st.tabs(["Record", "Upload"])
        with t1:
            st.info("💡 **Instructions:**\n1. Click **Start Recording**\n2. Speak your letter clearly\n3. Click **Stop Recording**\n4. Wait a moment for AI transcription")
            
            try:
                audio = st.audio_input("Record")
                if audio and ai_engine:
                    with st.spinner("Thinking..."): 
                        st.session_state.transcribed_text = ai_engine.transcribe_audio(audio)
                        st.session_state.app_mode = "review"; st.rerun()
            except AttributeError:
                st.info("Your Streamlit version doesn't support built-in recording yet. Please use Upload.")

        with t2:
            up = st.file_uploader("Audio File", type=['mp3','wav','m4a'])
            if up and st.button("Transcribe"):
                if ai_engine:
                    with st.spinner("Processing..."):
                        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{up.name.split('.')[-1]}") as tmp:
                            tmp.write(up.getvalue()); tpath=tmp.name
                        try:
                            st.session_state.transcribed_text = ai_engine.transcribe_audio(tpath)
                            st.session_state.app_mode = "review"; st.rerun()
                        finally:
                            if os.path.exists(tpath): 
                                try: os.remove(tpath)
                                except: pass

def _save_addrs(tier):
    u = st.session_state.get("user_email")
    if tier == "Santa": 
        st.session_state.from_addr = {
            "name": "Santa Claus", "street": "123 Elf Road", "city": "North Pole", "state": "NP", "zip": "88888", "country": "NP"
        }
    else:
        st.session_state.from_addr = {
            "name": st.session_state.get("w_from_name"), "street": st.session_state.get("w_from_street"),
            "address_line2": st.session_state.get("w_from_street2"), "city": st.session_state.get("w_from_city"),
            "state": st.session_state.get("w_from_state"), "zip": st.session_state.get("w_from_zip"), "country": "US", "email": u
        }
    
    if tier == "Civic":
        st.session_state.to_addr = {
            "name": "Civic Action", "street": "Capitol", "city": "DC", "state": "DC", "zip": "20000", "country": "US"
        }
    else:
        st.session_state.to_addr = {
            "name": st.session_state.get("w_to_name"), "street": st.session_state.get("w_to_street"),
            "address_line2": st.session_state.get("w_to_street2"), "city": st.session_state.get("w_to_city"),
            "state": st.session_state.get("w_to_state"), "zip": st.session_state.get("w_to_zip"), "country": "US"
        }
    
    d_id = st.session_state.get("current_draft_id")
    if d_id and database: database.update_draft_data(d_id, st.session_state.to_addr, st.session_state.from_addr)

def render_review_page():
    render_hero("Review", "Finalize & Send")
    if st.button("⬅️ Edit"): st.session_state.app_mode = "workspace"; st.rerun()
    
    tier = st.session_state.get("locked_tier", "Standard")
    if tier != "Campaign" and not st.session_state.get("to_addr"): _save_addrs(tier)

    c1, c2, c3, c4 = st.columns(4)
    txt = st.session_state.get("transcribed_text", "")
    
    def _ai_fix(style):
        if ai_engine:
            with st.spinner("Rewriting..."): 
                st.session_state.transcribed_text = ai_engine.refine_text(txt, style); st.rerun()
    
    if c1.button("Grammar"): _ai_fix("Grammar")
    if c2.button("Professional"): _ai_fix("Professional")
    if c3.button("Friendly"): _ai_fix("Friendly")
    if c4.button("Concise"): _ai_fix("Concise")

    st.text_area("Body", key="transcribed_text", height=300)
    
    if st.button("👁️ Preview PDF"):
        def _fmt_prev(d): return f"{d.get('name','')}\n{d.get('street','')}\n{d.get('city','')}, {d.get('state','')} {d.get('zip','')}"
        
        to_s = _fmt_prev(st.session_state.get("to_addr", {}))
        from_s = _fmt_prev(st.session_state.get("from_addr", {}))
        
        sig_path = None
        if st.session_state.get("sig_data") is not None:
            img = Image.fromarray(st.session_state.sig_data.astype('uint8'), 'RGBA')
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp: img.save(tmp.name); sig_path=tmp.name
        
        if letter_format:
            pdf = letter_format.create_pdf(st.session_state.transcribed_text, to_s, from_s, (tier=="Heirloom"), (tier=="Santa"), sig_path)
            if pdf:
                b64 = base64.b64encode(pdf).decode()
                st.markdown(f'<iframe src="data:application/pdf;base64,{b64}" width="100%" height="500"></iframe>', unsafe_allow_html=True)
        
        if sig_path: 
            try: os.remove(sig_path)
            except: pass

    if st.button("🚀 Send Letter", type="primary"):
        targets = []
        if tier == "Campaign": targets = st.session_state.get("bulk_targets", [])
        elif tier == "Civic": 
            for r in st.session_state.get("civic_targets", []):
                t = r.get('address_obj')
                if t: t['country']='US'; targets.append(t)
        else: targets.append(st.session_state.to_addr)
        
        if not targets: st.error("No recipients found."); return

        with st.spinner("Sending..."):
            errs = []
            for tgt in targets:
                if StandardAddress and isinstance(tgt, StandardAddress):
                    tgt = {
                        "name": tgt.name, "street": tgt.street, "address_line2": tgt.address_line2,
                        "city": tgt.city, "state": tgt.state, "zip": tgt.zip_code, "country": tgt.country
                    }

                def _fmt(d): return f"{d.get('name','')}\n{d.get('street','')}\n{d.get('city','')}, {d.get('state','')} {d.get('zip','')}"
                to_s = _fmt(tgt); from_s = _fmt(st.session_state.from_addr)
                
                sig_path = None
                if st.session_state.get("sig_data") is not None:
                    img = Image.fromarray(st.session_state.sig_data.astype('uint8'), 'RGBA')
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp: img.save(tmp.name); sig_path=tmp.name
                
                pdf = letter_format.create_pdf(st.session_state.transcribed_text, to_s, from_s, (tier=="Heirloom"), (tier=="Santa"), sig_path)
                if sig_path: 
                    try: os.remove(sig_path)
                    except: pass

                is_ok = False
                if mailer:
                    pg_to = {
                        'name': tgt.get('name'), 
                        'address_line1': tgt.get('street') or tgt.get('address_line1') or tgt.get('line1') or tgt.get('address'),
                        'address_line2': tgt.get('address_line2', ''),
                        'address_city': tgt.get('city'), 
                        'address_state': tgt.get('state'), 
                        'address_zip': tgt.get('zip'), 
                        'country_code': 'US'
                    }
                    pg_from = {
                        'name': st.session_state.from_addr.get('name'), 
                        'address_line1': st.session_state.from_addr.get('street'), 
                        'address_line2': st.session_state.from_addr.get('address_line2', ''),
                        'address_city': st.session_state.from_addr.get('city'), 
                        'address_state': st.session_state.from_addr.get('state'), 
                        'address_zip': st.session_state.from_addr.get('zip'), 
                        'country_code': 'US'
                    }
                    
                    try:
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tpdf:
                            tpdf.write(pdf); tpath=tpdf.name
                        
                        ok, res = mailer.send_letter(tpath, pg_to, pg_from, st.session_state.get("is_certified", False))
                        if ok: is_ok=True
                        else: errs.append(f"Failed {tgt.get('name')}: {res}")
                    finally:
                        if os.path.exists(tpath): 
                            try: os.remove(tpath)
                            except: pass

                if database:
                    status = "Completed" if is_ok else "Failed"
                    database.save_draft(st.session_state.user_email, st.session_state.transcribed_text, tier, "PAID", tgt, st.session_state.from_addr, status)

            if not errs:
                st.success("✅ All Sent!")
                st.session_state.letter_sent_success = True
                if st.button("Start New"): reset_app(); st.rerun()
            else:
                st.error("Errors occurred"); st.write(errs)

# --- 8. MAIN ROUTER ---
def show_main_app():
    if analytics: analytics.inject_ga()
    render_sidebar()
    mode = st.session_state.get("app_mode", "splash")
    
    if mode == "splash": 
        if ui_splash: ui_splash.show_splash()
        else: st.error("Splash Missing")
    elif mode == "login":
        if ui_login: 
            import auth_engine
            ui_login.show_login(
                lambda e,p: _h_login(auth_engine, e,p), 
                lambda e,p,n,a,a2,c,s,z,cn,l: _h_signup(auth_engine, e,p,n,a,a2,c,s,z,cn,l)
            )
    elif mode == "store": render_store_page()
    elif mode == "workspace": render_workspace_page()
    elif mode == "review": render_review_page()
    elif mode == "admin": 
        if ui_admin: ui_admin.show_admin()
    elif mode == "legal":
        try: import ui_legal; ui_legal.show_legal()
        except: st.info("Legal unavailable")
    else:
        st.session_state.app_mode = "store"; st.rerun()

def _h_login(auth, e, p):
    res, err = auth.sign_in(e, p)
    if res and res.user: st.session_state.user_email = res.user.email; st.session_state.app_mode = "store"; st.rerun()
    else: st.error(err)

def _h_signup(auth, e, p, n, a, a2, c, s, z, cn, l):
    res, err = auth.sign_up(e, p, n, a, a2, c, s, z, cn, l)
    if res and res.user: st.success("Created! Please Log In."); st.session_state.app_mode = "login"
    else: st.error(err)