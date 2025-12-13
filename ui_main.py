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
import hashlib

# --- 1. ROBUST UI IMPORTS ---
try: import ui_splash
except ImportError: ui_splash = None
try: import ui_login
except ImportError: ui_login = None
try: import ui_admin
except ImportError: ui_admin = None
try: import ui_legal
except ImportError: ui_legal = None
try: import ui_help
except ImportError: ui_help = None
# NEW: Onboarding Import
try: import ui_onboarding
except ImportError: ui_onboarding = None

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
        if found_url: 
            YOUR_APP_URL = found_url.rstrip("/")
except: 
    pass

COUNTRIES = {
    "US": "United States", "CA": "Canada", "GB": "United Kingdom", "FR": "France", 
    "DE": "Germany", "IT": "Italy", "ES": "Spain", "AU": "Australia", 
    "MX": "Mexico", "JP": "Japan", "BR": "Brazil", "IN": "India"
}

# --- 4. HELPER FUNCTIONS ---

def inject_mobile_styles():
    """
    Mobile-first CSS Enhancements
    """
    st.markdown("""
    <style>
        /* Mobile Input Fixes */
        @media (max-width: 768px) {
            .stTextInput input { font-size: 16px !important; } /* Prevents iOS zoom */
            .stButton button { width: 100% !important; padding: 12px !important; }
            div[data-testid="stExpander"] { width: 100% !important; }
        }
        
        /* Force white text in Hero */
        .custom-hero, .custom-hero *, 
        .price-card, .price-card * {
            color: #FFFFFF !important;
        }
    </style>
    """, unsafe_allow_html=True)

def _render_hero(title, subtitle):
    # CSS FIX: We inject a specific style block to override Streamlit's global h1 colors
    st.markdown(f"""
    <div class="custom-hero" style="background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); padding: 30px 20px; border-radius: 15px; text-align: center; margin-bottom: 25px; box-shadow: 0 8px 16px rgba(0,0,0,0.1); max-width: 100%; box-sizing: border-box;">
        <h1 style="margin: 0; font-size: clamp(1.8rem, 5vw, 3rem); font-weight: 700; line-height: 1.1; text-shadow: 0 2px 4px rgba(0,0,0,0.3);">{title}</h1>
        <div style="font-size: clamp(0.9rem, 3vw, 1.2rem); opacity: 0.95; margin-top: 8px;">{subtitle}</div>
    </div>""", unsafe_allow_html=True)

def _save_addresses_to_state(tier):
    u = st.session_state.get("user_email")
    
    if tier == "Santa": 
        st.session_state.from_addr = {
            "name": "Santa Claus", "street": "123 Elf Road", "city": "North Pole", 
            "state": "NP", "zip": "88888", "country": "NP"
        }
    else:
        st.session_state.from_addr = {
            "name": st.session_state.get("w_from_name"), 
            "street": st.session_state.get("w_from_street"),
            "address_line2": st.session_state.get("w_from_street2"), 
            "city": st.session_state.get("w_from_city"),
            "state": st.session_state.get("w_from_state"), 
            "zip": st.session_state.get("w_from_zip"), 
            "country": "US", "email": u
        }

    if tier == "Civic":
        st.session_state.to_addr = {
            "name": "Civic Action", "street": "Capitol", "city": "DC", 
            "state": "DC", "zip": "20000", "country": "US"
        }
    else:
        st.session_state.to_addr = {
            "name": st.session_state.get("w_to_name"), 
            "street": st.session_state.get("w_to_street"),
            "address_line2": st.session_state.get("w_to_street2"), 
            "city": st.session_state.get("w_to_city"),
            "state": st.session_state.get("w_to_state"), 
            "zip": st.session_state.get("w_to_zip"),
            "country": st.session_state.get("w_to_country", "US")
        }
    
    should_save = st.session_state.get("save_contact_opt", True)
    if should_save and database and tier != "Civic" and st.session_state.get("w_to_name"):
        try:
            database.add_contact(
                u, st.session_state.w_to_name, st.session_state.w_to_street, 
                st.session_state.w_to_street2, st.session_state.w_to_city, 
                st.session_state.w_to_state, st.session_state.w_to_zip
            )
        except Exception: pass

    # Basic check (PostGrid logic is separate now)
    d_id = st.session_state.get("current_draft_id")
    if d_id and database: 
        database.update_draft_data(d_id, st.session_state.to_addr, st.session_state.from_addr)

def _render_address_book_selector(u_email):
    if not database: return
    contacts = database.get_contacts(u_email)
    if contacts:
        contact_names = ["-- Quick Fill --"] + [c.name for c in contacts]
        def on_contact_change():
            selected = st.session_state.get("addr_book_sel")
            if selected and selected != "-- Quick Fill --":
                match = next((c for c in contacts if c.name == selected), None)
                if match:
                    st.session_state.w_to_name = match.name
                    st.session_state.w_to_street = match.street
                    st.session_state.w_to_street2 = match.street2 or ""
                    st.session_state.w_to_city = match.city
                    st.session_state.w_to_state = match.state
                    st.session_state.w_to_zip = match.zip_code
                    st.session_state.w_to_country = match.country

        st.selectbox("📒 Address Book", contact_names, key="addr_book_sel", on_change=on_contact_change)

def _render_address_form(tier, is_intl):
    with st.form("addressing_form"):
        # SMART ADDRESS FORM: No more accordions, just clean layout
        
        # 1. FROM ADDRESS
        st.markdown("### 🏠 Return Address")
        if tier == "Santa": 
            st.info("🎅 Sender: Santa Claus (North Pole)")
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

        # 2. TO ADDRESS
        st.markdown("### 📨 Recipient")
        if tier == "Civic":
            st.info("🏛️ **Destination: Your Representatives**")
            st.caption("We use your Return Zip Code to find officials automatically.")
            if "civic_targets" in st.session_state:
                for r in st.session_state.civic_targets: 
                    st.write(f"• {r['name']} ({r['title']})")
        else:
            c1, c2 = st.columns(2)
            with c1:
                st.text_input("Recipient Name", key="w_to_name", placeholder="Grandma")
                st.text_input("Recipient Street", key="w_to_street", placeholder="456 Maple Ave")
            with c2:
                if is_intl:
                    st.selectbox("Country", list(COUNTRIES.keys()), key="w_to_country")
                    st.text_input("City", key="w_to_city")
                    st.text_input("State/Prov", key="w_to_state")
                    st.text_input("Postal Code", key="w_to_zip")
                else:
                    st.text_input("Recipient City", key="w_to_city")
                    st.text_input("Recipient State", key="w_to_state")
                    st.text_input("Recipient Zip", key="w_to_zip")
                    st.session_state.w_to_country = "US"
            
            st.checkbox("Save to Address Book", key="save_contact_opt", value=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        if st.form_submit_button("✅ Save & Continue", type="secondary"):
            _save_addresses_to_state(tier)
            st.toast("Addresses Saved!")

def _process_sending_logic(tier):
    # Idempotency
    draft_id = st.session_state.get("current_draft_id", "0")
    idemp_key = hashlib.sha256(f"{draft_id}_{tier}_{len(st.session_state.transcribed_text)}".encode()).hexdigest()
    if st.session_state.get("last_send_hash") == idemp_key:
        st.warning("⚠️ This letter has already been queued for sending.")
        return

    to_check = st.session_state.get("to_addr", {})
    if tier != "Campaign" and tier != "Civic":
        if not to_check.get("city") or not to_check.get("zip"):
            st.error("❌ Recipient Address Incomplete!")
            return

    targets = []
    if tier == "Campaign": targets = st.session_state.get("bulk_targets", [])
    elif tier == "Civic": 
        for r in st.session_state.get("civic_targets", []):
            if r.get('address_obj'): targets.append(r['address_obj'])
    else: targets.append(st.session_state.to_addr)
    
    if not targets: st.error("No recipients found."); return

    # --- LOADING UX ---
    with st.spinner("Processing..."):
        if tier in ["Heirloom", "Santa"]:
            msg = """
            <h3 style="margin:0; color: #d35400;">🏺 Preparing Hand-Crafted Letter</h3>
            <p>✓ Generating PDF Proof...</p>
            <p>✓ Routing to Artisan Fulfillment Team...</p>
            <p>✓ Queuing for Manual Assembly...</p>
            """
        else:
            msg = """
            <h3 style="margin:0; color: #2a5298;">📮 Preparing Your Letter</h3>
            <p>✓ Generating PDF...</p>
            <p>✓ Uploading to print facility...</p>
            <p>✓ Scheduling USPS pickup...</p>
            """
            
        st.markdown(f"""
        <div style="text-align: center; padding: 20px; background-color: #f0f2f6; border-radius: 10px; margin-bottom: 20px;">
            {msg}
            <p style="color: #666; font-size: 0.9em; margin-top: 10px;">Almost done! This takes about 10 seconds.</p>
        </div>
        """, unsafe_allow_html=True)

        errs = []
        for tgt in targets:
            if not tgt.get('city'): continue 
            
            def _fmt(d): return f"{d.get('name','')}\n{d.get('street','')}\n{d.get('city','')}, {d.get('state','')} {d.get('zip','')}"
            to_s = _fmt(tgt)
            from_s = _fmt(st.session_state.from_addr)
            
            sig_path = None
            if st.session_state.get("sig_data") is not None:
                img = Image.fromarray(st.session_state.sig_data.astype('uint8'), 'RGBA')
                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp: 
                    img.save(tmp.name); sig_path=tmp.name
            
            pdf = letter_format.create_pdf(st.session_state.transcribed_text, to_s, from_s, (tier=="Heirloom"), (tier=="Santa"), sig_path)
            if sig_path: 
                try: os.remove(sig_path)
                except: pass

            is_ok = False
            
            # --- PATH A: MANUAL FULFILLMENT (Heirloom/Santa) ---
            if tier in ["Heirloom", "Santa"]:
                time.sleep(1.5) # UX Pause
                is_ok = True
                final_status = "Manual Queue"
            
            # --- PATH B: AUTOMATED (Standard/Civic) ---
            elif mailer:
                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tpdf:
                        tpdf.write(pdf); tpath = tpdf.name
                    
                    pg_to = {'name': tgt.get('name'), 'address_line1': tgt.get('street'), 'address_line2': tgt.get('address_line2', ''), 'address_city': tgt.get('city'), 'address_state': tgt.get('state'), 'address_zip': tgt.get('zip'), 'country_code': 'US'}
                    pg_from = {'name': st.session_state.from_addr.get('name'), 'address_line1': st.session_state.from_addr.get('street'), 'address_line2': st.session_state.from_addr.get('address_line2', ''), 'address_city': st.session_state.from_addr.get('city'), 'address_state': st.session_state.from_addr.get('state'), 'address_zip': st.session_state.from_addr.get('zip'), 'country_code': 'US'}

                    send_ok, send_res = mailer.send_letter(tpath, pg_to, pg_from, st.session_state.get("is_certified", False))
                    
                    if send_ok: 
                        is_ok = True
                        final_status = "Completed"
                    else: 
                        errs.append(f"Failed {tgt.get('name')}: {send_res}")
                        final_status = "Failed"
                except Exception as e: 
                    errs.append(f"Mailer Exception: {str(e)}")
                    final_status = "Failed"
                finally:
                    if os.path.exists(tpath): os.remove(tpath)
            else:
                final_status = "Failed"
                errs.append("Mailer module missing")

            if database:
                database.save_draft(st.session_state.user_email, st.session_state.transcribed_text, tier, "PAID", tgt, st.session_state.from_addr, final_status)

        if not errs:
            st.success("✅ Request Received!")
            st.session_state.last_send_hash = idemp_key
            st.session_state.letter_sent_success = True
            
            user = st.session_state.get("user_email")
            if analytics: analytics.track_event(user, "letter_sent", {"count": len(targets), "tier": tier, "mode": "manual" if tier in ["Heirloom", "Santa"] else "auto"})
            
            notif_type = "letter_received_manual" if tier in ["Heirloom", "Santa"] else "letter_sent"
            if mailer: mailer.send_customer_notification(user, notif_type, {"recipient": targets[0].get('name'), "count": len(targets)})
            
            st.rerun()
        else: st.error("Errors occurred"); st.write(errs)

# --- 5. SESSION MANAGEMENT ---
def reset_app(full_logout=False):
    st.query_params.clear()
    u_email = st.session_state.get("user_email")
    keys = ["audio_path", "transcribed_text", "payment_complete", "sig_data", "to_addr", "civic_targets", "bulk_targets", "bulk_paid_qty", "is_intl", "is_certified", "letter_sent_success", "locked_tier", "w_to_name", "w_to_street", "w_to_street2", "w_to_city", "w_to_state", "w_to_zip", "w_to_country", "addr_book_idx", "last_tracking_num", "campaign_errors", "current_stripe_id", "current_draft_id", "pending_stripe_url", "last_selected_contact", "addr_book_sel", "save_contact_opt", "last_send_hash", "tracked_payment_success", "tutorial_completed", "show_tutorial", "tutorial_step"] 
    for k in keys: 
        if k in st.session_state: del st.session_state[k]
    st.session_state.to_addr = {}
    if full_logout:
        if "user_email" in st.session_state: del st.session_state.user_email
        st.session_state.app_mode = "splash"
    else:
        if u_email: st.session_state.app_mode = "store"
        else: st.session_state.app_mode = "splash"

# --- 6. RENDER SIDEBAR ---
def render_sidebar():
    with st.sidebar:
        st.markdown("<div style='text-align: center; margin-bottom: 20px;'><h1>📮<br>VerbaPost</h1></div>", unsafe_allow_html=True)
        st.markdown("---")
        if st.session_state.get("authenticated"):
            u_email = st.session_state.get("user_email", "User")
            st.info(f"👤 {u_email}")
            if st.button("Log Out", use_container_width=True):
                st.session_state.clear()
                st.rerun()
        else:
            st.info("👤 Guest User")
            if st.button("🔑 Log In / Sign Up", type="primary", use_container_width=True):
                st.session_state.app_mode = "login"
                st.session_state.auth_view = "login"
                st.rerun()
        
        # Admin Link
        try:
            admin_email = st.secrets.get("admin", {}).get("email", "").strip().lower()
            current_email = st.session_state.get("user_email", "").strip().lower()
            if st.session_state.get("authenticated") and current_email == admin_email and admin_email != "":
                st.write(""); st.write(""); st.markdown("---")
                with st.expander("🛡️ Admin Console"):
                     if st.button("Open Dashboard", use_container_width=True):
                         st.session_state.app_mode = "admin"; st.rerun()
        except: pass
        st.markdown("---"); st.caption("v3.2.1 (Stable)")

# --- 7. PAGE: STORE ---
def render_store_page():
    if ui_onboarding: ui_onboarding.show_contextual_help("store")
    global YOUR_APP_URL
    u_email = st.session_state.get("user_email", "")
    if not u_email:
        st.warning("⚠️ Session Expired. Please log in to continue.")
        if st.button("Go to Login"):
            st.session_state.app_mode = "login"; st.rerun()
        return

    _render_hero("Select Service", "Choose your letter type")
    c1, c2 = st.columns([2, 1])
    with c1:
        with st.container(border=True):
            st.subheader("Available Packages")
            tier_labels = {"Standard": "⚡ Standard ($2.99)", "Heirloom": "🏺 Heirloom ($5.99)", "Civic": "🏛️ Civic ($6.99)", "Santa": "🎅 Santa ($9.99)", "Campaign": "📢 Campaign (Bulk)"}
            tier_desc = {"Standard": "Professional print on standard paper. Mailed USPS First Class.", "Heirloom": "Heavyweight archival stock with wet-ink style font.", "Civic": "We identify your local reps and mail them physical letters.", "Santa": "Magical letter from North Pole, signed by Santa.", "Campaign": "Upload CSV. We mail everyone at once."}
            default_idx = 0
            stored_tier = st.session_state.get("locked_tier")
            if stored_tier and stored_tier in list(tier_labels.keys()):
                default_idx = list(tier_labels.keys()).index(stored_tier)
            sel = st.radio("Select Tier", list(tier_labels.keys()), index=default_idx, format_func=lambda x: tier_labels[x])
            tier_code = sel
            st.info(tier_desc[tier_code])
            qty = 1
            if tier_code == "Campaign":
                qty = st.number_input("Recipients", 10, 5000, 50, 10)
                st.caption(f"Pricing: First $2.99, then $1.99/ea")
            is_intl = False
            is_certified = False
            if tier_code in ["Standard", "Heirloom"]:
                c_opt1, c_opt2 = st.columns(2)
                if c_opt1.checkbox("International (+$2.00)"): is_intl = True
                if c_opt2.checkbox("Certified Mail (+$12.00)"): is_certified = True
            st.session_state.is_intl = is_intl
            st.session_state.is_certified = is_certified

    with c2:
        with st.container(border=True):
            st.subheader("Checkout")
            discounted = False
            code = st.text_input("Promo Code")
            if promo_engine and code and promo_engine.validate_code(code): 
                discounted = True
                st.success("✅ Applied!")
            
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
                    st.session_state.app_mode = "workspace"
                    st.rerun()
            else:
                if "pending_stripe_url" in st.session_state:
                    url = st.session_state.pending_stripe_url
                    st.success("✅ Link Generated!")
                    st.markdown(f'<a href="{url}" target="_blank" style="text-decoration: none;"><div style="display: block; width: 100%; padding: 14px; background: linear-gradient(135deg, #28a745 0%, #218838 100%); color: white; text-align: center; border-radius: 8px; font-weight: bold; font-size: 1.1rem; margin-top: 10px;">👉 Pay Now (Opens New Tab)</div></a>', unsafe_allow_html=True)
                    if st.button("Cancel / Reset"):
                        del st.session_state.pending_stripe_url
                        st.rerun()
                else:
                    if st.button("💳 Generate Payment Link", type="primary", use_container_width=True):
                        try:
                            d_id = _handle_draft_creation(u_email, tier_code, final_price)
                            link = f"{YOUR_APP_URL}?tier={tier_code}&session_id={{CHECKOUT_SESSION_ID}}"
                            if d_id: link += f"&draft_id={d_id}"
                            if is_intl: link += "&intl=1"
                            if is_certified: link += "&certified=1"
                            if tier_code == "Campaign": link += f"&qty={qty}"
                            if payment_engine:
                                with st.spinner("Generating secure payment link..."):
                                    url, sess_id = payment_engine.create_checkout_session(f"VerbaPost {tier_code}", int(final_price*100), link, YOUR_APP_URL)
                                    if url:
                                        if audit_engine: audit_engine.log_event(u_email, "CHECKOUT_STARTED", sess_id, {"tier": tier_code})
                                        st.session_state.pending_stripe_url = url
                                        st.rerun()
                                    else: st.error("⚠️ Stripe Error: Could not generate link.")
                            else: st.error("⚠️ Payment Engine Missing")
                        except Exception as e:
                            st.error(f"❌ System Crash: {str(e)}")

def _handle_draft_creation(email, tier, price):
    d_id = st.session_state.get("current_draft_id")
    success = False
    if d_id and database:
        success = database.update_draft_data(d_id, status="Draft", tier=tier, price=price)
    if not success and database:
        d_id = database.save_draft(email, "", tier, price)
        st.session_state.current_draft_id = d_id
        st.query_params["draft_id"] = str(d_id)
    return d_id

def render_address_intervention(user_input, recommended):
    st.warning("⚠️ We found a better match for that address.")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**You Entered:**")
        st.text(f"{user_input.get('line1')}\n{user_input.get('line2') or ''}\n{user_input.get('city')}, {user_input.get('state')} {user_input.get('zip')}")
        if st.button("Use My Version (Risky)", key="btn_keep_mine"):
            st.session_state.recipient_address = user_input
            st.session_state.address_verified = True
            st.rerun()
    with c2:
        st.markdown("**USPS Recommended:**")
        st.markdown(f"<div style='background-color:#e6ffe6; padding:10px; border-radius:5px; border:1px solid #b3ffb3; color:#006600;'>{recommended.get('line1')}<br>{recommended.get('line2') or ''}<br>{recommended.get('city')}, {recommended.get('state')} {recommended.get('zip')}</div>", unsafe_allow_html=True)
        if st.button("✅ Use Recommended", type="primary", key="btn_use_rec"):
            st.session_state.recipient_address = recommended
            st.session_state.address_verified = True
            st.rerun()

# --- 8. PAGE: WORKSPACE (RESTORED) ---
def render_workspace_page():
    if ui_onboarding: ui_onboarding.show_contextual_help("workspace")
    _render_hero("Workspace", "Compose your letter")
    
    tier = st.session_state.get("locked_tier", "Standard")
    
    # 1. Address Verification Logic (Intervention)
    if st.session_state.get("show_address_fix"):
        render_address_intervention(st.session_state.temp_user_addr, st.session_state.temp_rec_addr)
        return

    # 2. Main Workspace Layout
    t1, t2 = st.tabs(["✍️ Write / Dictate", "🏠 Addressing"])
    
    # TAB 1: COMPOSE
    with t1:
        st.info("💡 You can type below, upload an audio file, or record your voice.")
        
        # Audio Upload
        aud_file = st.file_uploader("📂 Upload Audio (MP3, WAV, M4A)", type=["mp3", "wav", "m4a", "ogg"])
        if aud_file:
            if st.button("📝 Transcribe Uploaded File", type="primary"):
                if ai_engine:
                    with st.spinner("Transcribing..."):
                        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{aud_file.name.split('.')[-1]}") as tmp:
                            tmp.write(aud_file.getvalue()); tmp_path = tmp.name
                        try:
                            text = ai_engine.transcribe_audio(tmp_path)
                            st.session_state.transcribed_text = text
                            if os.path.exists(tmp_path): os.remove(tmp_path)
                            st.success("Done!")
                            st.rerun()
                        except Exception as e: st.error(f"Error: {e}")
        
        # Audio Recorder
        audio_bytes = st.audio_input("🎤 Record Voice")
        if audio_bytes:
            if st.button("📝 Transcribe Recording"):
                if ai_engine:
                    with st.spinner("Transcribing..."):
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                            tmp.write(audio_bytes.getvalue()); tmp_path = tmp.name
                        try:
                            text = ai_engine.transcribe_audio(tmp_path)
                            st.session_state.transcribed_text = text
                            if os.path.exists(tmp_path): os.remove(tmp_path)
                            st.rerun()
                        except Exception as e: st.error(f"Error: {e}")

        # Text Editor
        val = st.session_state.get("transcribed_text", "")
        new_val = st.text_area("Your Message", value=val, height=300)
        if new_val != val: st.session_state.transcribed_text = new_val

    # TAB 2: ADDRESSING
    with t2:
        if tier == "Civic":
            st.info("For Civic letters, we just need your Return Address to find your representatives.")
        
        # Show Address Form
        _render_address_form(tier, st.session_state.get("is_intl", False))
        
        # Address Verification Trigger (on 'Next' or manual button)
        # Note: The actual button is inside _render_address_form ("Save & Continue")
        # But we need to handle the verification result if that button was clicked.
        # The _save_addresses_to_state function handles the basic save.
        # We can add a "Verify Recipient" button here if desired, or rely on the form submit.
        
        # Let's add the explicit verify button here for "Bring Your Own Address"
        if tier not in ["Civic", "Campaign"]:
            if st.button("🔍 Verify Recipient Address"):
                raw = {
                    "line1": st.session_state.get("w_to_street"),
                    "line2": st.session_state.get("w_to_street2"),
                    "city": st.session_state.get("w_to_city"),
                    "state": st.session_state.get("w_to_state"),
                    "zip": st.session_state.get("w_to_zip"),
                    "country": "US"
                }
                if mailer:
                    status, clean, errs = mailer.verify_address_details(raw)
                    if status == "corrected":
                        st.session_state.temp_user_addr = raw
                        st.session_state.temp_rec_addr = clean
                        st.session_state.show_address_fix = True
                        st.rerun()
                    elif status == "verified":
                        st.success("Address is valid! ✅")
                    else:
                        st.error(f"Invalid Address: {errs}")

    st.markdown("---")
    if st.button("➡️ Review & Send", type="primary", use_container_width=True):
        if not st.session_state.get("transcribed_text"):
            st.error("Please write or transcribe your letter first.")
        else:
            st.session_state.app_mode = "review"
            st.rerun()

# --- 9. PAGE: REVIEW ---
def render_review_page():
    if ui_onboarding: ui_onboarding.show_contextual_help("review")
    
    _render_hero("Review", "Finalize & Send")
    if st.session_state.get("letter_sent_success"):
        st.success("✅ Letter Sent Successfully!")
        st.balloons()
        st.markdown("### Next Steps")
        if st.button("📮 Start New Letter", type="primary", use_container_width=True):
            reset_app()
            st.rerun()
        return

    if st.button("⬅️ Edit"): 
        st.session_state.app_mode = "workspace"
        st.rerun()
    tier = st.session_state.get("locked_tier", "Standard")
    if tier != "Campaign" and not st.session_state.get("to_addr"): _save_addresses_to_state(tier)

    c1, c2, c3, c4 = st.columns(4)
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

    new_text = st.text_area("Body", value=current_text, height=300, key="txt_body_input")
    if new_text != current_text: st.session_state.transcribed_text = new_text

    st.markdown("### 📄 Letter Preview")
    
    if tier == "Civic" and st.session_state.get("civic_targets"):
        st.info("🏛️ Sending to:")
        for t in st.session_state.civic_targets:
            st.write(f"- {t['name']} ({t['title']})")
            
    if not current_text: st.warning("Please enter some text before generating a preview.")
    else:
        try:
            to_s = ""; from_s = ""
            if tier == "Civic" and st.session_state.get("civic_targets"):
                first_rep = st.session_state.civic_targets[0]
                d = first_rep.get('address_obj', st.session_state.to_addr)
                to_s = f"{d.get('name','')}\n{d.get('street','')}\n{d.get('city','')}, {d.get('state','')} {d.get('zip','')}"
            elif st.session_state.get("to_addr"):
                d = st.session_state.to_addr
                to_s = f"{d.get('name','')}\n{d.get('street','')}\n{d.get('city','')}, {d.get('state','')} {d.get('zip','')}"

            if st.session_state.get("from_addr"):
                d = st.session_state.from_addr
                from_s = f"{d.get('name','')}\n{d.get('street','')}\n{d.get('city','')}, {d.get('state','')} {d.get('zip','')}"
            
            sig_path = None
            if st.session_state.get("sig_data") is not None:
                img = Image.fromarray(st.session_state.sig_data.astype('uint8'), 'RGBA')
                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp: 
                    img.save(tmp.name); sig_path=tmp.name
            
            if letter_format:
                pdf_bytes = letter_format.create_pdf(current_text, to_s, from_s, (tier=="Heirloom"), (tier=="Santa"), sig_path)
                if pdf_bytes and len(pdf_bytes) > 100:
                    st.download_button(label="⬇️ Download PDF Proof", data=pdf_bytes, file_name="letter_preview.pdf", mime="application/pdf", type="primary", use_container_width=True)
                else: st.error("Failed to generate PDF content.")
            if sig_path: 
                try: os.remove(sig_path)
                except: pass
        except Exception as e: st.error(f"Preview Failed: {e}")

    if st.button("🚀 Send Letter", type="primary"):
        _process_sending_logic(tier)

# --- 10. MAIN ROUTER ---
def show_main_app():
    inject_mobile_styles()
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
    elif mode == "help" and ui_help: ui_help.show_help()
    else: 
        st.session_state.app_mode = "store"
        st.rerun()