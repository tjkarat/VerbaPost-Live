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

# --- 1. IMPORTS ---
try: import ui_splash
except ImportError: ui_splash = None
try: import ui_login
except ImportError: ui_login = None
try: import ui_admin
except ImportError: ui_admin = None
try: import ui_legal
except ImportError: ui_legal = None

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

# --- 2. CONFIG ---
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

# --- 3. SESSION ---
def reset_app(full_logout=False):
    recovered = st.query_params.get("draft_id")
    u_email = st.session_state.get("user_email")
    keys = ["audio_path", "transcribed_text", "payment_complete", "sig_data", "to_addr", 
            "civic_targets", "bulk_targets", "bulk_paid_qty", "is_intl", "is_certified", 
            "letter_sent_success", "locked_tier", "w_to_name", "w_to_street", "w_to_street2", 
            "w_to_city", "w_to_state", "w_to_zip", "w_to_country", "addr_book_idx", 
            "last_tracking_num", "campaign_errors", "current_stripe_id", "current_draft_id",
            "pending_stripe_url"]
    for k in keys: 
        if k in st.session_state: del st.session_state[k]
    st.session_state.to_addr = {}
    if full_logout:
        if "user_email" in st.session_state: del st.session_state.user_email
        st.session_state.app_mode = "splash"
    else:
        if recovered:
            st.session_state.current_draft_id = recovered; st.session_state.app_mode = "workspace" 
        elif u_email: st.session_state.app_mode = "store"
        else: st.session_state.app_mode = "splash"

# --- 4. COMPONENTS ---
def render_hero(title, subtitle):
    st.markdown(f"""<div class="custom-hero" style="background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); padding: 40px; border-radius: 15px; text-align: center; margin-bottom: 30px;"><h1 style="margin: 0; font-size: 3rem; color: white !important;">{title}</h1><div style="font-size: 1.2rem; color: white !important;">{subtitle}</div></div>""", unsafe_allow_html=True)

def render_sidebar():
    with st.sidebar:
        st.header("VerbaPost 📮")
        st.markdown("---")
        u_email = st.session_state.get("user_email")
        if u_email:
            st.success(f"👤 {u_email}")
            admin_target = "tjkarat@gmail.com"
            if secrets_manager: 
                s = secrets_manager.get_secret("admin.email")
                if s: admin_target = s
            if str(u_email).lower().strip() == str(admin_target).lower().strip():
                if st.button("🔐 Admin"): st.session_state.app_mode = "admin"; st.rerun()
            if st.button("🚪 Logout"): reset_app(True); st.rerun()
        else:
            if st.button("🔑 Login"): st.session_state.app_mode = "login"; st.rerun()
        st.markdown("---")
        if st.session_state.get("app_mode") in ["workspace", "review"] and u_email:
             if st.button("🛒 Store"): st.session_state.app_mode = "store"; st.rerun()
        if st.button("⚖️ Legal"): st.session_state.app_mode = "legal"; st.rerun()

# --- 5. STORE ---
def render_store_page():
    if not st.session_state.get("user_email"):
        st.warning("⚠️ Please log in."); st.button("Login", on_click=lambda: st.session_state.update(app_mode="login")); return

    render_hero("Select Service", "Choose your letter type")
    c1, c2 = st.columns([2, 1])
    with c1:
        tier_labels = {"Standard": "⚡ Standard ($2.99)", "Heirloom": "🏺 Heirloom ($5.99)", "Civic": "🏛️ Civic ($6.99)", "Santa": "🎅 Santa ($9.99)", "Campaign": "📢 Campaign"}
        def_idx = 0
        stored = st.session_state.get("locked_tier")
        if stored in tier_labels: def_idx = list(tier_labels.keys()).index(stored)
        tier = st.radio("Select Tier", list(tier_labels.keys()), index=def_idx, format_func=lambda x: tier_labels[x])
        
        qty = 1
        if tier == "Campaign": qty = st.number_input("Recipients", 10, 5000, 50)
        is_intl = st.checkbox("International (+$2.00)") if tier in ["Standard", "Heirloom"] else False
        is_cert = st.checkbox("Certified (+$12.00)") if tier in ["Standard", "Heirloom"] else False
        st.session_state.is_intl = is_intl; st.session_state.is_certified = is_cert

    with c2:
        code = st.text_input("Promo Code")
        disc = promo_engine.validate_code(code) if (promo_engine and code) else False
        if disc: st.success("✅ Applied!")
        price = pricing_engine.calculate_total(tier, is_intl, is_cert, qty) if (not disc and pricing_engine) else (0.00 if disc else 2.99)
        st.metric("Total", f"${price:.2f}")

        if disc:
            if st.button("🚀 Start (Free)", type="primary"):
                _create_draft(st.session_state.user_email, tier, price)
                st.session_state.payment_complete = True; st.session_state.locked_tier = tier
                st.session_state.bulk_paid_qty = qty; st.session_state.app_mode = "workspace"; st.rerun()
        else:
            if "pending_stripe_url" in st.session_state:
                st.success("✅ Link Ready!")
                st.markdown(f'''<a href="{st.session_state.pending_stripe_url}" target="_blank"><div style="background:#28a745;color:white;padding:12px;border-radius:8px;text-align:center;">👉 Pay Now (New Tab)</div></a>''', unsafe_allow_html=True)
                if st.button("Reset"): del st.session_state.pending_stripe_url; st.rerun()
            else:
                if st.button("💳 Pay Now", type="primary"):
                    d_id = _create_draft(st.session_state.user_email, tier, price)
                    link = f"{YOUR_APP_URL}?tier={tier}&session_id={{CHECKOUT_SESSION_ID}}"
                    if d_id: link += f"&draft_id={d_id}"
                    if is_intl: link += "&intl=1"
                    if is_cert: link += "&certified=1"
                    if tier == "Campaign": link += f"&qty={qty}"
                    
                    if payment_engine:
                        url, sid = payment_engine.create_checkout_session(f"VerbaPost {tier}", int(price*100), link, YOUR_APP_URL)
                        if url:
                            st.session_state.pending_stripe_url = url; st.rerun()
                        else: st.error("Payment Config Error")

def _create_draft(email, tier, price):
    d_id = st.session_state.get("current_draft_id")
    if d_id and database: database.update_draft_data(d_id, status="Draft", tier=tier, price=price)
    if not d_id and database:
        d_id = database.save_draft(email, "", tier, price)
        st.session_state.current_draft_id = d_id
        st.query_params["draft_id"] = str(d_id)
    return d_id

# --- 6. WORKSPACE ---
def render_workspace_page():
    tier = st.session_state.get("locked_tier", "Standard")
    render_hero("Compose Letter", f"{tier} Edition")
    
    with st.container(border=True):
        if tier == "Campaign":
            if not bulk_engine: st.error("Bulk Engine Missing")
            f = st.file_uploader("CSV", type=['csv'])
            if f and bulk_engine:
                c, err = bulk_engine.parse_csv(f)
                if err: st.error(err)
                elif len(c) > st.session_state.get("bulk_paid_qty", 1000): st.error("List too large.")
                else: 
                    st.success(f"{len(c)} contacts."); 
                    if st.button("Confirm"): st.session_state.bulk_targets = c; st.toast("Saved!")
        else:
            st.subheader("Addresses")
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**From**")
                if tier == "Santa": st.info("🎅 Santa Claus")
                else:
                    st.text_input("Name", key="w_from_name"); st.text_input("Street", key="w_from_street")
                    st.text_input("Apt/Suite", key="w_from_street2")
                    ca, cb = st.columns(2)
                    ca.text_input("City", key="w_from_city"); cb.text_input("State", key="w_from_state")
                    st.text_input("Zip", key="w_from_zip")
            with c2:
                st.markdown("**To**")
                if tier == "Civic":
                    st.info("🏛️ Auto-Rep Lookup")
                    if st.button("🔍 Find Reps") and civic_engine:
                        addr = f"{st.session_state.get('w_from_street')} {st.session_state.get('w_from_zip')}"
                        reps = civic_engine.get_reps(addr)
                        if reps: st.session_state.civic_targets = reps; st.success(f"Found {len(reps)}")
                        else: st.error("None found")
                else:
                    st.text_input("Name", key="w_to_name"); st.text_input("Street", key="w_to_street")
                    st.text_input("Apt/Suite", key="w_to_street2")
                    ca, cb = st.columns(2); ca.text_input("City", key="w_to_city"); cb.text_input("State", key="w_to_state")
                    st.text_input("Zip", key="w_to_zip")
            
            if st.button("Save Addresses"): _save_addrs(tier); st.toast("Saved!")

    st.write("---")
    c_sig, c_mic = st.columns(2)
    with c_sig:
        st.write("✍️ **Signature**")
        if tier != "Santa":
            # FIX: Width 300 for alignment
            canvas = st_canvas(stroke_width=2, height=150, width=300, key="sig")
            if canvas.image_data is not None: st.session_state.sig_data = canvas.image_data
    with c_mic:
        st.write("🎤 **Dictate**")
        audio = st.audio_input("Record")
        if audio and st.button("Transcribe"):
            if ai_engine:
                with st.spinner("Transcribing..."):
                    res = ai_engine.transcribe_audio(audio)
                    if res.startswith("Error"): st.error(res)
                    else: st.session_state.transcribed_text = res; st.session_state.app_mode = "review"; st.rerun()

def _save_addrs(tier):
    u = st.session_state.get("user_email")
    st.session_state.from_addr = {"name": st.session_state.get("w_from_name"), "street": st.session_state.get("w_from_street"), "city": st.session_state.get("w_from_city"), "state": st.session_state.get("w_from_state"), "zip": st.session_state.get("w_from_zip"), "country": "US", "email": u}
    st.session_state.to_addr = {"name": st.session_state.get("w_to_name"), "street": st.session_state.get("w_to_street"), "city": st.session_state.get("w_to_city"), "state": st.session_state.get("w_to_state"), "zip": st.session_state.get("w_to_zip"), "country": "US"}
    if database and st.session_state.get("current_draft_id"):
        database.update_draft_data(st.session_state.current_draft_id, st.session_state.to_addr, st.session_state.from_addr)

# --- 7. REVIEW ---
def render_review_page():
    render_hero("Review", "Finalize")
    if st.button("Back"): st.session_state.app_mode = "workspace"; st.rerun()
    
    txt = st.text_area("Body", st.session_state.get("transcribed_text", ""), height=300)
    st.session_state.transcribed_text = txt

    if st.button("Preview PDF"):
        if letter_format:
            to_s = f"{st.session_state.to_addr.get('name')}\n{st.session_state.to_addr.get('street')}"
            from_s = f"{st.session_state.from_addr.get('name')}"
            sig_path = None
            if st.session_state.get("sig_data") is not None:
                img = Image.fromarray(st.session_state.sig_data.astype('uint8'), 'RGBA')
                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as t: img.save(t.name); sig_path=t.name
            
            pdf = letter_format.create_pdf(txt, to_s, from_s, False, False, sig_path)
            if pdf:
                b64 = base64.b64encode(pdf).decode()
                st.markdown(f'<iframe src="data:application/pdf;base64,{b64}" width="100%" height="500"></iframe>', unsafe_allow_html=True)
            if sig_path: os.remove(sig_path)

    if st.button("Send Now", type="primary"):
        st.success("Sent!"); time.sleep(1); reset_app(); st.rerun()

# --- 8. MAIN ---
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