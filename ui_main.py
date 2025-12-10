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
import traceback

# --- 1. CRITICAL UI IMPORTS ---
try: import ui_splash
except ImportError: ui_splash = None
try: import ui_login
except ImportError: ui_login = None
try: import ui_admin
except ImportError: ui_admin = None
try: import ui_legal
except ImportError: ui_legal = None

# --- 2. HELPER IMPORTS & DIAGNOSTICS ---
dependency_errors = {}

try: import database
except ImportError as e: database = None; dependency_errors['database'] = str(e)

try: import ai_engine
except ImportError as e: ai_engine = None; dependency_errors['ai_engine'] = str(e)

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
    
    # Added "checkout_url" to clean up on reset
    keys = ["audio_path", "transcribed_text", "payment_complete", "sig_data", "to_addr", 
            "civic_targets", "bulk_targets", "bulk_paid_qty", "is_intl", "is_certified", 
            "letter_sent_success", "locked_tier", "w_to_name", "w_to_street", "w_to_street2", 
            "w_to_city", "w_to_state", "w_to_zip", "w_to_country", "addr_book_idx", 
            "last_tracking_num", "campaign_errors", "current_stripe_id", "current_draft_id",
            "checkout_url"] 
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
        st.warning("⚠️ Session Expired.")
        st.session_state.app_mode = "login"
        st.rerun()
        return False
    return True

# --- 5. SHARED UI COMPONENTS ---
def render_hero(title, subtitle):
    st.markdown(f"""<div class="custom-hero" style="background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); padding: 40px; border-radius: 15px; text-align: center; margin-bottom: 30px; box-shadow: 0 8px 16px rgba(0,0,0,0.1);"><h1 style="margin: 0; font-size: 3rem; font-weight: 700; color: white !important;">{title}</h1><div style="font-size: 1.2rem; opacity: 0.9; margin-top: 10px; color: white !important;">{subtitle}</div></div>""", unsafe_allow_html=True)

def render_sidebar():
    with st.sidebar:
        st.header("VerbaPost 📮")
        st.markdown("---")
        user_email = st.session_state.get("user_email")
        
        if user_email:
            st.success(f"👤 **Logged in as:**\n{user_email}")
            
            # Admin Check
            admin_target = "tjkarat@gmail.com"
            if secrets_manager:
                sec = secrets_manager.get_secret("admin.email")
                if sec: admin_target = sec
            
            if str(user_email).lower().strip() == str(admin_target).lower().strip():
                if st.button("🔐 Admin Console", type="primary", use_container_width=True):
                    st.session_state.app_mode = "admin"
                    st.rerun()

            if st.button("🚪 Log Out", type="secondary", use_container_width=True):
                reset_app(full_logout=True)
                st.rerun()
        else:
            st.info("👤 **Guest User**")
            if st.button("🔑 Log In / Sign Up", type="primary", use_container_width=True):
                st.session_state.app_mode = "login"
                st.rerun()

        st.markdown("---")
        mode = st.session_state.get("app_mode", "splash")
        if mode in ["workspace", "review"] and user_email:
             if st.button("🛒 Store (New Letter)", icon="🛍️", use_container_width=True):
                 st.session_state.app_mode = "store"
                 st.rerun()

        st.markdown("### Support")
        if st.button("⚖️ Legal & Privacy", use_container_width=True):
            st.session_state.app_mode = "legal"
            st.rerun()
        st.caption("v3.1.9 Stripe Fix")

# --- 6. PAGE: STORE ---
def render_store_page():
    u_email = st.session_state.get("user_email", "")
    if not u_email:
        st.warning("⚠️ Session Expired. Please log in to continue.")
        if st.button("Go to Login"):
            st.session_state.app_mode = "login"
            st.rerun()
        return

    render_hero("Select Service", "Choose your letter type")
    
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
            
            # Use on_change to clear checkout url if tier changes
            def _clear_checkout():
                if "checkout_url" in st.session_state: del st.session_state.checkout_url
                
            sel = st.radio("Select Tier", list(tier_labels.keys()), format_func=lambda x: tier_labels[x], on_change=_clear_checkout)
            tier_code = sel
            st.info(tier_desc[tier_code])
            
            qty = 1
            if tier_code == "Campaign":
                qty = st.number_input("Recipients", 10, 5000, 50, 10, on_change=_clear_checkout)
                st.caption(f"Pricing: First $2.99, then $1.99/ea")

            is_intl = False; is_certified = False
            if tier_code in ["Standard", "Heirloom"]:
                c_opt1, c_opt2 = st.columns(2)
                if c_opt1.checkbox("International (+$2.00)", on_change=_clear_checkout): is_intl = True
                if c_opt2.checkbox("Certified Mail (+$12.00)", on_change=_clear_checkout): is_certified = True

            st.session_state.is_intl = is_intl
            st.session_state.is_certified = is_certified

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
                    final_price = pricing_engine.calculate_total(tier_code, is_intl, is_certified, qty)
                else:
                    final_price = 2.99 
            
            st.metric("Total", f"${final_price:.2f}")
            
            btn_txt = "🚀 Start (Free)" if discounted else f"Pay ${final_price:.2f} & Start"
            
            # BUTTON LOGIC
            if st.button(btn_txt, type="primary", use_container_width=True):
                d_id = _handle_draft_creation(u_email, tier_code, final_price)

                if discounted:
                    if promo_engine: promo_engine.log_usage(code, u_email)
                    st.session_state.payment_complete = True
                    st.session_state.locked_tier = tier_code
                    st.session_state.bulk_paid_qty = qty
                    st.session_state.app_mode = "workspace"
                    st.rerun()
                else:
                    link = f"{YOUR_APP_URL}?tier={tier_code}&session_id={{CHECKOUT_SESSION_ID}}"
                    if d_id: link += f"&draft_id={d_id}"
                    if is_intl: link += "&intl=1"
                    if is_certified: link += "&certified=1"
                    if tier_code == "Campaign": link += f"&qty={qty}"
                    
                    if payment_engine:
                        # PERSISTENCE FIX: Store the URL so it survives re-renders
                        url, _ = payment_engine.create_checkout_session(f"VerbaPost {tier_code}", int(final_price*100), link, YOUR_APP_URL)
                        if url: 
                            st.session_state.checkout_url = url
            
            # RENDER PAY BUTTON (Outside the if block to ensure it stays visible)
            if st.session_state.get("checkout_url"):
                url = st.session_state.checkout_url
                st.success("Payment Link Ready!")
                # Changed target to _blank to avoid iframe blocking issues
                st.markdown(f'<a href="{url}" target="_blank"><button style="width:100%;padding:10px;background:#635bff;color:white;border:none;border-radius:5px;cursor:pointer;font-weight:bold;font-size:16px;">👉 Click to Pay Now</button></a>', unsafe_allow_html=True)

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

# --- 7. PAGE: WORKSPACE ---
def render_workspace_page():
    tier = st.session_state.get("locked_tier", "Standard")
    is_intl = st.session_state.get("is_intl", False)
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
            st.subheader("📍 Addressing")
            with st.form("address_form"):
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
                        st.info("🏛️ **Auto-Detect Representatives**")
                        zip_code = st.session_state.get("w_from_zip")
                        if not zip_code: st.warning("Enter your Zip Code in the 'From' section first.")
                        
                        if "civic_targets" in st.session_state:
                            for r in st.session_state.civic_targets: st.write(f"• {r['name']} ({r['title']})")
                    else:
                        if database:
                            cons = database.get_contacts(u_email)
                            if cons:
                                sel = st.selectbox("Address Book", ["-- Quick Fill --"] + [x.name for x in cons])
                        
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

                if st.form_submit_button("Save Addresses", type="primary"):
                    if tier == "Civic" and civic_engine and st.session_state.w_from_zip:
                        full_addr = f"{st.session_state.w_from_street} {st.session_state.w_from_city} {st.session_state.w_from_state} {st.session_state.w_from_zip}"
                        reps = civic_engine.get_reps(full_addr)
                        if reps: st.session_state.civic_targets = reps
                    
                    _save_addrs(tier)
                    st.toast("Address Saved!")

    st.write("---")
    c_sig, c_mic = st.columns(2)
    with c_sig:
        st.write("✍️ **Signature**")
        if tier == "Santa": st.info("Signed by Santa")
        else: 
            canvas = st_canvas(stroke_width=2, height=150, width=400, key="sig")
            if canvas.image_data is not None: st.session_state.sig_data = canvas.image_data
    
    with c_mic:
        st.write("🎤 **Input**")
        st.info("Record audio or upload a file, then click Transcribe")
        
        tab_record, tab_upload = st.tabs(["🎙️ Record", "📁 Upload"])
        
        with tab_record:
            audio_recorded = st.audio_input("Record your message")
            if audio_recorded:
                st.success(f"✅ Recording captured ({len(audio_recorded.getvalue())} bytes)")
                
                if st.button("🔄 Transcribe Recording", type="primary", key="btn_transcribe_rec"):
                    if not ai_engine:
                        err_msg = dependency_errors.get('ai_engine', 'Unknown Import Error')
                        st.error(f"⚠️ AI Engine not available. Reason: {err_msg}")
                    else:
                        with st.spinner("🎧 Transcribing... This may take 10-30 seconds"):
                            try:
                                # --- SAFE FILE HANDLING WRAPPER ---
                                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                                    tmp.write(audio_recorded.getvalue())
                                    tpath = tmp.name
                                
                                result = ai_engine.transcribe_audio(tpath)
                                
                                # Clean up immediately
                                if os.path.exists(tpath):
                                    try: os.remove(tpath)
                                    except: pass

                                if result and str(result).startswith("Error:"):
                                    st.error(result)
                                else:
                                    st.session_state.transcribed_text = result
                                    st.success(f"✅ Transcribed {len(result)} characters!")
                                    st.session_state.app_mode = "review"
                                    st.rerun()
                            except Exception as e:
                                st.error(f"Transcription failed: {str(e)}")
                                st.code(traceback.format_exc())
        
        with tab_upload:
            st.caption("Supported: MP3, WAV, M4A (Max 25MB)")
            uploaded_file = st.file_uploader("Choose audio file", type=['mp3', 'wav', 'm4a'])
            
            if uploaded_file:
                st.success(f"✅ File uploaded: {uploaded_file.name} ({len(uploaded_file.getvalue()) / 1024 / 1024:.2f} MB)")
                
                if st.button("🔄 Transcribe File", type="primary", use_container_width=True):
                    if not ai_engine:
                        err_msg = dependency_errors.get('ai_engine', 'Unknown Import Error')
                        st.error(f"⚠️ AI Engine not available. Reason: {err_msg}")
                    else:
                        with st.spinner("🎧 Transcribing... This may take 10-30 seconds"):
                            try:
                                # --- SAFE FILE HANDLING WRAPPER ---
                                with tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded_file.name.split('.')[-1]}") as tmp:
                                    tmp.write(uploaded_file.getvalue())
                                    tpath = tmp.name
                                
                                result = ai_engine.transcribe_audio(tpath)
                                
                                # Clean up immediately
                                if os.path.exists(tpath):
                                    try: os.remove(tpath)
                                    except: pass

                                if result and str(result).startswith("Error:"):
                                    st.error(result)
                                else:
                                    st.session_state.transcribed_text = result
                                    st.success(f"✅ Transcribed {len(result)} characters!")
                                    st.session_state.app_mode = "review"
                                    st.rerun()
                            except Exception as e:
                                st.error(f"Transcription failed: {str(e)}")
                                st.code(traceback.format_exc())

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
            "state": st.session_state.get("w_to_state"), "zip": st.session_state.get("w_to_zip"),
            "country": st.session_state.get("w_to_country", "US")
        }
    
    d_id = st.session_state.get("current_draft_id")
    if d_id and database: database.update_draft_data(d_id, st.session_state.to_addr, st.session_state.from_addr)

def render_review_page():
    render_hero("Review", "Finalize & Send")
    if st.button("⬅️ Edit"): st.session_state.app_mode = "workspace"; st.rerun()
    
    tier = st.session_state.get("locked_tier", "Standard")
    if tier != "Campaign" and not st.session_state.get("to_addr"): _save_addrs(tier)

    # AI Tools
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
        def _fmt(d): return f"{d.get('name','')}\n{d.get('street','')}\n{d.get('city','')}, {d.get('state','')} {d.get('zip','')}"
        
        to_s = _fmt(st.session_state.get("to_addr", {}))
        from_s = _fmt(st.session_state.get("from_addr", {}))
        
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