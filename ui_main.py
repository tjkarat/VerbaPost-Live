import streamlit as st
from PIL import Image
import os, tempfile, logging, hashlib, time

# --- IMPORTS ---
try: import ui_splash, ui_login, ui_admin, ui_legal, ui_legacy, ui_onboarding, database, ai_engine, payment_engine, letter_format, mailer, analytics, promo_engine, secrets_manager, civic_engine, bulk_engine, audit_engine, auth_engine, pricing_engine
except: pass

logging.basicConfig(level=logging.INFO); logger = logging.getLogger(__name__)
COUNTRIES = {"US": "United States", "CA": "Canada", "GB": "UK", "FR": "France", "DE": "Germany", "AU": "Australia"}

# --- HELPERS ---
def inject_mobile_styles():
    st.markdown("""<style>@media (max-width: 768px) { .stTextInput input {font-size: 16px;} .stButton button {width: 100%;} }</style>""", unsafe_allow_html=True)

def _get_user_profile_defaults(email):
    if not database: return {}
    try:
        u = database.get_user(email)
        if u: return {"w_from_name": u.full_name, "w_from_street": u.address_line1, "w_from_city": u.address_city, "w_from_state": u.address_state, "w_from_zip": u.address_zip}
    except: pass
    return {}

def render_sidebar():
    with st.sidebar:
        st.markdown("<h1 style='text-align: center'>📮<br>VerbaPost</h1>", unsafe_allow_html=True)
        if st.session_state.get("authenticated"):
            st.info(f"👤 {st.session_state.get('user_email')}")
            if st.button("Log Out"): st.session_state.clear(); st.rerun()
        else:
            if st.button("Log In"): st.session_state.app_mode = "login"; st.session_state.auth_view="login"; st.rerun()
        
        # ADMIN CHECK
        try:
            admin = "tjkarat@gmail.com"
            if secrets_manager: admin = secrets_manager.get_secret("admin.email") or admin
            if st.session_state.get("user_email", "").lower() == admin.lower():
                st.markdown("---")
                if st.button("🛡️ Admin Console"): st.session_state.app_mode = "admin"; st.rerun()
        except: pass

def _save_addresses(tier):
    u = st.session_state.get("user_email")
    st.session_state.from_addr = {"name": st.session_state.w_from_name, "street": st.session_state.w_from_street, "city": st.session_state.w_from_city, "state": st.session_state.w_from_state, "zip": st.session_state.w_from_zip, "country": "US"}
    if tier == "Santa": st.session_state.from_addr = {"name": "Santa", "street": "123 Elf Rd", "city": "North Pole", "state": "NP", "zip": "88888", "country": "NP"}
    
    st.session_state.to_addr = {"name": st.session_state.w_to_name, "street": st.session_state.w_to_street, "city": st.session_state.w_to_city, "state": st.session_state.w_to_state, "zip": st.session_state.w_to_zip, "country": "US"}
    if tier == "Civic": st.session_state.to_addr = {"name": "Civic Action", "street": "Capitol", "city": "DC", "state": "DC", "zip": "20000"}

    if st.session_state.get("save_contact_opt") and database:
        database.add_contact(u, st.session_state.w_to_name, st.session_state.w_to_street, "", st.session_state.w_to_city, st.session_state.w_to_state, st.session_state.w_to_zip)
    
    if database and st.session_state.get("current_draft_id"):
        database.update_draft_data(st.session_state.current_draft_id, st.session_state.to_addr, st.session_state.from_addr)

def _process_sending(tier):
    if not st.session_state.to_addr.get("city") and tier not in ["Civic", "Campaign"]:
        st.error("Address incomplete."); return

    with st.spinner("Processing..."):
        targets = [st.session_state.to_addr]
        if tier == "Civic": targets = [r['address_obj'] for r in st.session_state.civic_targets]
        
        for tgt in targets:
            to_s = f"{tgt.get('name')}\n{tgt.get('street')}\n{tgt.get('city')}, {tgt.get('state')} {tgt.get('zip')}"
            from_s = f"{st.session_state.from_addr.get('name')}\n{st.session_state.from_addr.get('street')}\n{st.session_state.from_addr.get('city')}, {st.session_state.from_addr.get('state')} {st.session_state.from_addr.get('zip')}"
            
            pdf = letter_format.create_pdf(st.session_state.transcribed_text, to_s, from_s, (tier=="Heirloom"), (tier=="Santa"))
            
            status = "Manual Queue"
            if tier not in ["Heirloom", "Santa"] and mailer:
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as t: t.write(pdf); tpath = t.name
                pg_to = {'name': tgt.get('name'), 'line1': tgt.get('street'), 'city': tgt.get('city'), 'state': tgt.get('state'), 'zip': tgt.get('zip'), 'country': 'US'}
                pg_from = {'name': st.session_state.from_addr.get('name'), 'line1': st.session_state.from_addr.get('street'), 'city': st.session_state.from_addr.get('city'), 'state': st.session_state.from_addr.get('state'), 'zip': st.session_state.from_addr.get('zip'), 'country': 'US'}
                ok, res = mailer.send_letter(tpath, pg_to, pg_from, f"VerbaPost {tier}")
                if ok: status = "Completed"
                try: os.remove(tpath)
                except: pass
            
            if database: database.save_draft(st.session_state.user_email, st.session_state.transcribed_text, tier, "PAID", tgt, st.session_state.from_addr, status)
        
        st.success("✅ Sent!"); st.session_state.letter_sent_success = True; st.rerun()

# --- PAGES ---
def render_store_page():
    st.markdown("## Select Service")
    c1, c2 = st.columns([2, 1])
    with c1:
        sel = st.radio("Tier", ["Standard ($2.99)", "Heirloom ($5.99)", "Civic ($6.99)", "Santa ($9.99)", "Campaign (Bulk)"])
        tier = sel.split(" ")[0]
        qty = 1
        if tier == "Campaign": qty = st.number_input("Qty", 10, 5000, 50)
    with c2:
        price = pricing_engine.calculate_total(tier, qty=qty) if pricing_engine else 2.99
        st.metric("Total", f"${price:.2f}")
        if st.button("💳 Pay & Start", type="primary"):
            d_id = database.save_draft(st.session_state.get("user_email", "guest"), "", tier, price) if database else None
            url, sid = payment_engine.create_checkout_session(f"VP {tier}", int(price*100), f"{YOUR_APP_URL}?session_id={{CHECKOUT_SESSION_ID}}&tier={tier}", YOUR_APP_URL)
            if url: st.link_button("Pay Now", url)

def render_workspace_page():
    tier = st.session_state.get("locked_tier", "Standard")
    st.title(f"🎙️ Workspace: {tier}")
    
    t1, t2 = st.tabs(["🏠 Addressing", "✍️ Write"])
    with t1:
        if not st.session_state.get("w_from_name"):
            defaults = _get_user_profile_defaults(st.session_state.get("user_email"))
            for k,v in defaults.items(): st.session_state[k] = v
            
        with st.form("addr_form"):
            c1, c2 = st.columns(2)
            c1.markdown("From"); c2.markdown("To")
            st.session_state.w_from_name = c1.text_input("Name", key="w_from_name")
            st.session_state.w_from_street = c1.text_input("Street", key="w_from_street")
            st.session_state.w_from_zip = c1.text_input("Zip", key="w_from_zip")
            
            st.session_state.w_to_name = c2.text_input("Name", key="w_to_name")
            st.session_state.w_to_street = c2.text_input("Street", key="w_to_street")
            st.session_state.w_to_zip = c2.text_input("Zip", key="w_to_zip")
            st.checkbox("Save Contact", key="save_contact_opt")
            
            if st.form_submit_button("Save"): _save_addresses(tier); st.success("Saved!")

    with t2:
        audio = st.audio_input("Record")
        if audio and ai_engine:
            with st.spinner("Transcribing..."):
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as t: t.write(audio.getvalue()); path=t.name
                st.session_state.transcribed_text = ai_engine.transcribe_audio(path)
                st.rerun()
        
        txt = st.text_area("Body", st.session_state.get("transcribed_text", ""), height=300)
        if txt: st.session_state.transcribed_text = txt
        
    if st.button("Review & Send", type="primary"): st.session_state.app_mode = "review"; st.rerun()

def render_review_page():
    st.title("Review")
    st.write(st.session_state.get("transcribed_text"))
    if st.button("🚀 Send"): _process_sending(st.session_state.get("locked_tier"))

# --- MAIN ROUTER ---
def render_main():
    inject_mobile_styles()
    render_sidebar() # <--- ADMIN VISIBILITY FIX
    
    mode = st.session_state.get("app_mode", "splash")
    if mode == "admin" and ui_admin: ui_admin.show_admin(); return
    if mode == "login" and ui_login: ui_login.render_login(); return
    
    if mode == "store": render_store_page()
    elif mode == "workspace": render_workspace_page()
    elif mode == "review": render_review_page()
    elif mode == "legacy": ui_legacy.render_legacy_page()
    elif mode == "legal": ui_legal.render_legal()
    else: ui_splash.render_splash()