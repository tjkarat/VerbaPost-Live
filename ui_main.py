import streamlit as st
import os
import tempfile
import logging
import hashlib
import time
from PIL import Image

# --- IMPORTS ---
try:
    import ui_splash
    import ui_login
    import ui_admin
    import ui_legal
    import ui_legacy
    import ui_onboarding
    import database
    import ai_engine
    import payment_engine
    import letter_format
    import mailer
    import analytics
    import promo_engine
    import secrets_manager
    import civic_engine
    import bulk_engine
    import audit_engine
    import auth_engine
    import pricing_engine
except ImportError:
    pass

# --- CONFIGURATION ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

COUNTRIES = {
    "US": "United States", "CA": "Canada", "GB": "United Kingdom", 
    "FR": "France", "DE": "Germany", "AU": "Australia"
}

# --- HELPER FUNCTIONS ---

def inject_mobile_styles():
    """
    Mobile-first CSS Enhancements.
    """
    st.markdown("""
    <style>
        @media (max-width: 768px) {
            .stTextInput input { font-size: 16px !important; }
            .stButton button { width: 100% !important; padding: 12px !important; }
            div[data-testid="stExpander"] { width: 100% !important; }
        }
        .custom-hero, .custom-hero *, .price-card, .price-card * {
            color: #FFFFFF !important;
        }
    </style>
    """, unsafe_allow_html=True)

def _get_user_profile_defaults(email):
    """Fetches user profile for auto-fill."""
    if not database: return {}
    try:
        u = database.get_user(email)
        if u:
            return {
                "w_from_name": u.full_name,
                "w_from_street": u.address_line1,
                "w_from_city": u.address_city,
                "w_from_state": u.address_state,
                "w_from_zip": u.address_zip
            }
    except Exception:
        pass
    return {}

def render_sidebar():
    """
    Renders the sidebar navigation with Admin Console access.
    """
    with st.sidebar:
        st.markdown("<div style='text-align: center; margin-bottom: 20px;'><h1>📮<br>VerbaPost</h1></div>", unsafe_allow_html=True)
        st.markdown("---")
        
        # User Status
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
        
        # --- ADMIN LINK LOGIC ---
        try:
            # 1. Fallback list
            admin_emails = ["tjkarat@gmail.com"]
            
            # 2. Add from secrets
            if secrets_manager:
                sec_email = secrets_manager.get_secret("admin.email")
                if sec_email: admin_emails.append(sec_email)
            
            current = st.session_state.get("user_email", "").strip().lower()
            
            if st.session_state.get("authenticated") and current in [a.lower() for a in admin_emails]:
                st.write("")
                st.markdown("---")
                with st.expander("🛡️ Admin Console"):
                     if st.button("Open Dashboard", use_container_width=True):
                         st.session_state.app_mode = "admin"
                         st.query_params["view"] = "admin"
                         st.rerun()
        except Exception:
            pass
            
        st.markdown("---")
        st.caption("v4.0 (Production)")

def _render_hero(title, subtitle):
    st.markdown(f"""
    <div class="custom-hero" style="background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); padding: 30px 20px; border-radius: 15px; text-align: center; margin-bottom: 25px; box-shadow: 0 8px 16px rgba(0,0,0,0.1);">
        <h1 style="margin: 0; font-size: 2.5rem; font-weight: 700; color: white;">{title}</h1>
        <div style="font-size: 1.1rem; opacity: 0.95; margin-top: 8px; color: white;">{subtitle}</div>
    </div>""", unsafe_allow_html=True)

def _save_addresses(tier):
    u = st.session_state.get("user_email")
    
    # 1. From Address
    st.session_state.from_addr = {
        "name": st.session_state.w_from_name,
        "street": st.session_state.w_from_street,
        "city": st.session_state.w_from_city,
        "state": st.session_state.w_from_state,
        "zip": st.session_state.w_from_zip,
        "country": "US"
    }
    if tier == "Santa": 
        st.session_state.from_addr = {"name": "Santa Claus", "street": "123 Elf Road", "city": "North Pole", "state": "NP", "zip": "88888", "country": "NP"}

    # 2. To Address
    st.session_state.to_addr = {
        "name": st.session_state.w_to_name,
        "street": st.session_state.w_to_street,
        "city": st.session_state.w_to_city,
        "state": st.session_state.w_to_state,
        "zip": st.session_state.w_to_zip,
        "country": "US"
    }
    if tier == "Civic":
        st.session_state.to_addr = {"name": "Civic Action", "street": "Capitol", "city": "DC", "state": "DC", "zip": "20000", "country": "US"}

    # 3. Address Book Save
    if st.session_state.get("save_contact_opt") and database:
        database.add_contact(u, st.session_state.w_to_name, st.session_state.w_to_street, "", st.session_state.w_to_city, st.session_state.w_to_state, st.session_state.w_to_zip)
    
    # 4. Draft Update
    if database and st.session_state.get("current_draft_id"):
        database.update_draft_data(st.session_state.current_draft_id, st.session_state.to_addr, st.session_state.from_addr)

def _process_sending(tier):
    if not st.session_state.to_addr.get("city") and tier not in ["Civic", "Campaign"]:
        st.error("Address incomplete. Please fix in step 1."); return

    with st.spinner("Processing Order..."):
        targets = []
        if tier == "Civic": 
            for r in st.session_state.civic_targets:
                if r.get('address_obj'): targets.append(r['address_obj'])
        else: 
            targets.append(st.session_state.to_addr)
        
        for tgt in targets:
            # Generate PDF Strings
            to_s = f"{tgt.get('name')}\n{tgt.get('street')}\n{tgt.get('city')}, {tgt.get('state')} {tgt.get('zip')}"
            from_s = f"{st.session_state.from_addr.get('name')}\n{st.session_state.from_addr.get('street')}\n{st.session_state.from_addr.get('city')}, {st.session_state.from_addr.get('state')} {st.session_state.from_addr.get('zip')}"
            
            pdf = letter_format.create_pdf(st.session_state.transcribed_text, to_s, from_s, (tier=="Heirloom"), (tier=="Santa"))
            
            final_status = "Manual Queue"
            
            # PostGrid Sending
            if tier not in ["Heirloom", "Santa"] and mailer:
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as t: 
                    t.write(pdf)
                    tpath = t.name
                
                pg_to = {'name': tgt.get('name'), 'line1': tgt.get('street'), 'city': tgt.get('city'), 'state': tgt.get('state'), 'zip': tgt.get('zip'), 'country': 'US'}
                pg_from = {'name': st.session_state.from_addr.get('name'), 'line1': st.session_state.from_addr.get('street'), 'city': st.session_state.from_addr.get('city'), 'state': st.session_state.from_addr.get('state'), 'zip': st.session_state.from_addr.get('zip'), 'country': 'US'}
                
                ok, res = mailer.send_letter(tpath, pg_to, pg_from, f"VerbaPost {tier}")
                if ok: final_status = "Completed"
                
                try: os.remove(tpath)
                except: pass
            
            if database: 
                database.save_draft(st.session_state.user_email, st.session_state.transcribed_text, tier, "PAID", tgt, st.session_state.from_addr, final_status)
        
        st.success("✅ Order Received Successfully!")
        st.session_state.letter_sent_success = True
        st.rerun()

# --- PAGES ---

def render_store_page():
    if ui_onboarding: ui_onboarding.show_contextual_help("store")
    _render_hero("Select Service", "Choose your letter type")
    
    c1, c2 = st.columns([2, 1])
    with c1:
        sel = st.radio("Tier", ["Standard ($2.99)", "Heirloom ($5.99)", "Civic ($6.99)", "Santa ($9.99)", "Campaign (Bulk)"])
        tier = sel.split(" ")[0]
        qty = 1
        if tier == "Campaign": qty = st.number_input("Qty", 10, 5000, 50)
    
    with c2:
        price = pricing_engine.calculate_total(tier, qty=qty) if pricing_engine else 2.99
        st.metric("Total", f"${price:.2f}")
        
        if st.button("💳 Pay & Start", type="primary", use_container_width=True):
            # Create Draft
            d_id = None
            if database:
                d_id = database.save_draft(st.session_state.get("user_email", "guest"), "", tier, price)
            
            # Generate Link
            if payment_engine:
                url, sid = payment_engine.create_checkout_session(
                    f"VerbaPost {tier}", 
                    int(price*100), 
                    f"{st.secrets['general']['BASE_URL']}?session_id={{CHECKOUT_SESSION_ID}}&tier={tier}", 
                    st.secrets['general']['BASE_URL']
                )
                if url: st.link_button("Pay Now", url, type="primary", use_container_width=True)

def render_workspace_page():
    if ui_onboarding: ui_onboarding.show_contextual_help("workspace")
    tier = st.session_state.get("locked_tier", "Standard")
    _render_hero(f"Workspace: {tier}", "Compose your letter")
    
    t1, t2 = st.tabs(["🏠 Addressing", "✍️ Write"])
    
    with t1:
        # Auto-Populate
        if not st.session_state.get("w_from_name"):
            defaults = _get_user_profile_defaults(st.session_state.get("user_email"))
            for k,v in defaults.items(): st.session_state[k] = v
            
        with st.form("addr_form"):
            c1, c2 = st.columns(2)
            c1.markdown("From")
            c2.markdown("To")
            
            st.session_state.w_from_name = c1.text_input("Name", key="w_from_name")
            st.session_state.w_from_street = c1.text_input("Street", key="w_from_street")
            st.session_state.w_from_city = c1.text_input("City", key="w_from_city")
            st.session_state.w_from_state = c1.text_input("State", key="w_from_state")
            st.session_state.w_from_zip = c1.text_input("Zip", key="w_from_zip")
            
            st.session_state.w_to_name = c2.text_input("Name", key="w_to_name")
            st.session_state.w_to_street = c2.text_input("Street", key="w_to_street")
            st.session_state.w_to_city = c2.text_input("City", key="w_to_city")
            st.session_state.w_to_state = c2.text_input("State", key="w_to_state")
            st.session_state.w_to_zip = c2.text_input("Zip", key="w_to_zip")
            
            st.checkbox("Save Contact to Book", key="save_contact_opt")
            
            if st.form_submit_button("✅ Save Addresses"):
                _save_addresses(tier)
                st.success("Saved!")

    with t2:
        st.info("Record your message or type below.")
        audio = st.audio_input("Record")
        if audio and ai_engine:
            with st.spinner("Transcribing..."):
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as t: 
                    t.write(audio.getvalue())
                    path=t.name
                
                st.session_state.transcribed_text = ai_engine.transcribe_audio(path)
                st.rerun()
        
        txt = st.text_area("Body Text", st.session_state.get("transcribed_text", ""), height=300)
        if txt: st.session_state.transcribed_text = txt
        
    if st.button("➡️ Review & Send", type="primary", use_container_width=True):
        st.session_state.app_mode = "review"
        st.rerun()

def render_review_page():
    _render_hero("Review", "Finalize & Send")
    
    st.write(st.session_state.get("transcribed_text"))
    st.caption("Standard USPS First Class")
    
    if st.button("🚀 Send Letter", type="primary", use_container_width=True):
        _process_sending(st.session_state.get("locked_tier", "Standard"))

# --- MAIN ROUTER ---
def render_main():
    inject_mobile_styles()
    
    # NOTE: Sidebar is called in main.py, so we do NOT call it here to avoid DuplicateID crash.
    
    if analytics: 
        try: analytics.inject_ga()
        except: pass
    
    mode = st.session_state.get("app_mode", "splash")
    
    # Route to Views
    if mode == "store": render_store_page()
    elif mode == "workspace": render_workspace_page()
    elif mode == "review": render_review_page()
    elif mode == "legacy" and ui_legacy: ui_legacy.render_legacy_page()
    else: 
        # Fallback
        if st.session_state.get("authenticated"):
            st.session_state.app_mode = "store"
            render_store_page()
        else:
            if ui_splash: ui_splash.render_splash()