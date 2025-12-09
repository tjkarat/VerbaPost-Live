import streamlit as st
from streamlit_drawable_canvas import st_canvas
import os
import tempfile
import base64
import io
import time
from PIL import Image

# --- 1. CRITICAL: LOAD CORE DEFINITIONS FIRST ---
try:
    from address_standard import StandardAddress
except ImportError:
    from dataclasses import dataclass
    from typing import Optional, Dict, Any
    @dataclass
    class StandardAddress:
        name: str
        street: str
        address_line2: Optional[str] = ""
        city: str = ""
        state: str = ""
        zip_code: str = ""
        country: str = "US"
        def to_postgrid_payload(self): return {}
        def to_pdf_string(self): return f"{self.name}\n{self.street}"
        @classmethod
        def from_dict(cls, d): return cls(name=d.get('name',''), street=d.get('street',''))

# --- 2. LOAD MODULES ---
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

# --- 3. CONFIGURATION ---
DEFAULT_URL = "https://verbapost.streamlit.app/"
YOUR_APP_URL = DEFAULT_URL
try:
    if secrets_manager:
        val = secrets_manager.get_secret("BASE_URL")
        if val: YOUR_APP_URL = val
except: pass
YOUR_APP_URL = YOUR_APP_URL.rstrip("/")

COUNTRIES = {
    "US": "United States", "CA": "Canada", "GB": "United Kingdom", "FR": "France",
    "DE": "Germany", "IT": "Italy", "ES": "Spain", "AU": "Australia", "MX": "Mexico",
    "JP": "Japan", "BR": "Brazil", "IN": "India"
}

# --- 4. SESSION & HELPERS ---
def reset_app():
    recovered = st.query_params.get("draft_id")
    keys = ["audio_path", "transcribed_text", "payment_complete", "sig_data", "to_addr", 
            "civic_targets", "bulk_targets", "bulk_paid_qty", "is_intl", "is_certified", 
            "letter_sent_success", "locked_tier", "w_to_name", "w_to_street", "w_to_street2", 
            "w_to_city", "w_to_state", "w_to_zip", "w_to_country", "addr_book_idx", 
            "last_tracking_num", "campaign_errors", "current_stripe_id", "current_draft_id"]
    for k in keys:
        if k in st.session_state: del st.session_state[k]
    st.session_state.to_addr = {}
    
    if "draft_id" in st.query_params and not recovered:
        st.query_params.clear()

    if recovered:
        st.session_state.current_draft_id = recovered
        st.session_state.app_mode = "workspace" 
        st.success("🔄 Session Restored!")
    elif st.session_state.get("user_email"): 
        st.session_state.app_mode = "store"
    else: 
        st.session_state.app_mode = "splash"

def check_session():
    if "user_email" not in st.session_state or not st.session_state.user_email:
        st.warning("Session Expired. Please log in.")
        st.session_state.app_mode = "login"
        st.rerun()
        return False
    return True

def render_hero(title, subtitle):
    st.markdown(f"""
    <style>
        .custom-hero h1, .custom-hero div {{ color: white !important; }}
    </style>
    <div class="custom-hero" style="
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        padding: 30px; border-radius: 12px; text-align: center; margin-bottom: 25px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1); color: white !important;">
        <h1 style="margin: 0; font-size: 2.5rem; font-weight: 700; color: white !important;">{title}</h1>
        <div style="font-size: 1.1rem; opacity: 0.95; margin-top: 5px; color: white !important;">{subtitle}</div>
    </div>
    """, unsafe_allow_html=True)

def render_legal_page():
    try: import ui_legal; ui_legal.show_legal()
    except: st.error("Legal page unavailable.")

# --- 5. AUTH HANDLERS ---
def handle_login(email, password):
    if auth_engine:
        res, err = auth_engine.sign_in(email, password)
        if res and res.user:
            st.session_state.user_email = res.user.email
            st.session_state.app_mode = "store"
            st.success("Welcome back!")
            time.sleep(0.5)
            st.rerun()
        else: st.error(f"Login failed: {err}")

def handle_signup(email, password, name, street, street2, city, state, zip_code, country, language):
    if auth_engine:
        res, err = auth_engine.sign_up(email, password, name, street, street2, city, state, zip_code, country, language)
        if res and res.user:
            st.session_state.user_email = res.user.email
            st.session_state.app_mode = "store"
            st.success("Account created!")
            time.sleep(0.5)
            st.rerun()
        else: return res, err
    return None, "Auth Engine Missing"

def _save_addresses_from_widgets(tier, is_intl):
    u_email = st.session_state.get("user_email")
    if tier == "Santa":
        st.session_state.from_addr = {"name": "Santa Claus", "street": "123 Elf Road", "city": "North Pole", "state": "NP", "zip": "88888", "country": "NP"}
    else:
        st.session_state.from_addr = {
            "name": st.session_state.get("w_from_name"), "street": st.session_state.get("w_from_street"),
            "address_line2": st.session_state.get("w_from_street2", ""), "city": st.session_state.get("w_from_city"),
            "state": st.session_state.get("w_from_state"), "zip": st.session_state.get("w_from_zip"),
            "country": st.session_state.get("w_from_country", "US"), "email": u_email
        }
    
    if tier == "Civic":
        st.session_state.to_addr = {"name": "Civic Action", "street": "Capitol", "city": "DC", "state": "DC", "zip": "20000", "country": "US"}
    else:
        st.session_state.to_addr = {
            "name": st.session_state.get("w_to_name"), "street": st.session_state.get("w_to_street"),
            "address_line2": st.session_state.get("w_to_street2", ""), "city": st.session_state.get("w_to_city"),
            "state": st.session_state.get("w_to_state"), "zip": st.session_state.get("w_to_zip"),
            "country": st.session_state.get("w_to_country", "US")
        }

# --- 6. PAGE: STORE ---
def render_store_page():
    
    # --- CRITICAL FIX: HANDLE PAYMENT RETURN BEFORE SESSION CHECK ---
    # This prevents the redirect-to-login loop by re-hydrating the session from Stripe data.
    sess_id = st.query_params.get("session_id")
    if sess_id and not st.session_state.get("payment_complete"):
        with st.spinner("Verifying Payment..."):
            if payment_engine:
                success, details = payment_engine.verify_session(sess_id)
                if success:
                    st.session_state.payment_complete = True
                    
                    # RESTORE USER EMAIL FROM STRIPE DATA
                    if not st.session_state.get("user_email"):
                        try:
                            recovered_email = details.get("customer_details", {}).get("email")
                            if recovered_email:
                                st.session_state.user_email = recovered_email
                        except: pass
                    
                    # Log & Redirect
                    if audit_engine: audit_engine.log_event(st.session_state.get("user_email"), "PAYMENT_SUCCESS", sess_id, {"amount": details.get('amount_total')})
                    st.success("Payment Received! Loading Workspace...")
                    st.session_state.app_mode = "workspace"
                    st.rerun()
                else: 
                    st.error("Payment Verification Failed")
                    # If verification fails, we fall through to the login check below

    # Now run the login check
    if not check_session(): return
    u_email = st.session_state.user_email

    render_hero("Select Service", "Choose your letter type")
    
    try:
        if secrets_manager and secrets_manager.get_secret("admin.email") == u_email.lower():
            if st.button("🔐 Admin Console", type="secondary"): st.session_state.app_mode = "admin"; st.rerun()
    except: pass

    c1, c2 = st.columns([2, 1])
    with c1:
        with st.container(border=True):
            st.subheader("Available Packages")
            tier_options = ["Standard", "Heirloom", "Civic", "Santa", "Campaign"]
            tier_labels = {"Standard": "⚡ Standard ($2.99)", "Heirloom": "🏺 Heirloom ($5.99)", "Civic": "🏛️ Civic ($6.99)", "Santa": "🎅 Santa ($9.99)", "Campaign": "📢 Campaign"}
            sel = st.radio("Select Tier", tier_options, format_func=lambda x: tier_labels[x])
            tier_code = sel
            
            qty = 1; price = 0.0
            if tier_code == "Campaign":
                qty = st.number_input("Recipients", 10, 5000, 50, 10)
                price = 2.99 + ((qty - 1) * 1.99)
            else:
                price = {"Standard": 2.99, "Heirloom": 5.99, "Civic": 6.99, "Santa": 9.99}[tier_code]

            is_intl = False; is_certified = False
            if tier_code in ["Standard", "Heirloom"]:
                c1a, c1b = st.columns(2)
                if c1a.checkbox("International? (+$2.00)"): price += 2.00; is_intl = True
                if c1b.checkbox("Certified? (+$12.00)"): price += 12.00; is_certified = True
            
            st.session_state.locked_tier = tier_code
            st.session_state.is_intl = is_intl
            st.session_state.is_certified = is_certified
            st.session_state.bulk_paid_qty = qty

    with c2:
        with st.container(border=True):
            st.subheader("Checkout")
            code = st.text_input("Promo Code")
            discounted = False
            if promo_engine and code and promo_engine.validate_code(code): discounted = True; st.success("Applied!")
            
            st.metric("Total", f"${0.00 if discounted else price:.2f}")
            
            if st.button("🚀 Pay & Start", type="primary", use_container_width=True):
                d_id = st.session_state.get("current_draft_id")
                # Save draft BEFORE payment logic
                if database:
                    if d_id: database.update_draft_data(d_id, status="Draft", tier=tier_code, price="0.00" if discounted else str(price))
                    else: 
                        d_id = database.save_draft(u_email, "", tier_code, "0.00" if discounted else str(price))
                        st.session_state.current_draft_id = d_id
                        st.query_params["draft_id"] = str(d_id)

                if discounted:
                    if promo_engine: promo_engine.log_usage(code, u_email)
                    st.session_state.payment_complete = True
                    st.session_state.app_mode = "workspace"
                    st.rerun()
                else:
                    link = f"{YOUR_APP_URL}?tier={tier_code}&session_id={{CHECKOUT_SESSION_ID}}&draft_id={d_id}"
                    if is_intl: link += "&intl=1"
                    if is_certified: link += "&certified=1"
                    
                    if payment_engine:
                        # Standard call without metadata to avoid TypeError
                        url, _ = payment_engine.create_checkout_session(f"VerbaPost {tier_code}", int(price*100), link, YOUR_APP_URL)
                        if url: st.markdown(f'<a href="{url}" target="_self" style="text-decoration:none;"><button style="width:100%;padding:10px;background:#6772e5;color:white;border:none;border-radius:5px;cursor:pointer;">👉 Pay with Stripe</button></a>', unsafe_allow_html=True)
                    else: st.error("Payment Engine Missing")

# --- 7. PAGE: WORKSPACE ---
def render_workspace_page():
    if not check_session(): return
    tier = st.session_state.get("locked_tier", "Standard")
    render_hero("Compose Letter", f"{tier} Edition")
    
    u_email = st.session_state.get("user_email")
    u_addr = {}
    if database:
        p = database.get_user_profile(u_email)
        if p: u_addr = {"name": p.full_name, "street": p.address_line1, "street2": getattr(p, "address_line2", ""), "city": p.address_city, "state": p.address_state, "zip": p.address_zip}
        if "w_from_name" not in st.session_state: st.session_state.w_from_name = u_addr.get("name","")
        if "w_from_street" not in st.session_state: st.session_state.w_from_street = u_addr.get("street","")
        if "w_from_street2" not in st.session_state: st.session_state.w_from_street2 = u_addr.get("street2","")
        if "w_from_city" not in st.session_state: st.session_state.w_from_city = u_addr.get("city","")
        if "w_from_state" not in st.session_state: st.session_state.w_from_state = u_addr.get("state","")
        if "w_from_zip" not in st.session_state: st.session_state.w_from_zip = u_addr.get("zip","")

    with st.container(border=True):
        if tier == "Campaign":
            st.subheader("Upload CSV")
            if not bulk_engine: st.error("Bulk Engine Missing"); return
            up = st.file_uploader("CSV File", type=['csv'])
            if up:
                contacts, err = bulk_engine.parse_csv(up)
                if err: st.error(err)
                else:
                    limit = st.session_state.get("bulk_paid_qty", 1000)
                    if len(contacts) > limit: contacts = contacts[:limit]; st.warning(f"Truncated to {limit}")
                    st.success(f"{len(contacts)} contacts loaded.")
                    if st.button("Confirm"): st.session_state.bulk_targets = contacts; st.toast("Saved!")
        
        elif tier == "Santa":
            st.info("🎅 From: Santa Claus, North Pole")
            st.text_input("Child's Name", key="w_to_name")
            st.text_input("Street", key="w_to_street")
            c1,c2 = st.columns(2)
            c1.text_input("City", key="w_to_city"); c2.text_input("Zip", key="w_to_zip")
            st.text_input("State", key="w_to_state")
            if st.button("Save Address", type="primary"): 
                _save_addresses_from_widgets(tier, False); st.toast("Saved!")

        elif tier == "Civic":
            st.subheader("Your Reps")
            st.text_input("Your Street", key="w_from_street")
            st.text_input("Zip", key="w_from_zip")
            if st.button("Find Reps") and civic_engine:
                addr = f"{st.session_state.w_from_street} {st.session_state.w_from_zip}"
                reps = civic_engine.get_reps(addr)
                if reps: st.session_state.civic_targets = reps; st.success(f"Found {len(reps)} Reps")
                else: st.error("No reps found")

        else:
            with st.expander("Sender Info", expanded=False):
                st.text_input("Name", key="w_from_name")
                st.text_input("Street", key="w_from_street")
                st.text_input("City", key="w_from_city")
                st.text_input("State", key="w_from_state")
                st.text_input("Zip", key="w_from_zip")
            
            st.markdown("**Recipient**")
            if database:
                cons = database.get_contacts(u_email)
                if cons:
                    opts = ["-- Book --"] + [c.name for c in cons]
                    idx = st.selectbox("Quick Fill", range(len(opts)), format_func=lambda x: opts[x], key="addr_book_idx")
                    if idx > 0:
                        c = cons[idx-1]
                        st.session_state.w_to_name = c.name; st.session_state.w_to_street = c.street; st.session_state.w_to_city = c.city; st.session_state.w_to_state = c.state; st.session_state.w_to_zip = c.zip_code
            
            st.text_input("Name", key="w_to_name")
            st.text_input("Street", key="w_to_street")
            st.text_input("City", key="w_to_city")
            st.text_input("State", key="w_to_state")
            st.text_input("Zip", key="w_to_zip")
            
            if st.button("Save Addresses", type="primary"):
                _save_addresses_from_widgets(tier, st.session_state.get("is_intl", False))
                st.toast("Saved!")

    st.write("---")
    c1, c2 = st.columns(2)
    with c1:
        st.write("✍️ **Signature**")
        if tier != "Santa":
            canvas = st_canvas(stroke_width=2, height=150, width=400, key="sig")
            if canvas.image_data is not None: st.session_state.sig_data = canvas.image_data
    with c2:
        st.write("🎤 **Dictation**")
        if ai_engine:
            audio = st.audio_input("Record")
            if audio:
                with st.spinner("Thinking..."): st.session_state.transcribed_text = ai_engine.transcribe_audio(audio); st.session_state.app_mode="review"; st.rerun()

# --- 8. PAGE: REVIEW ---
def render_review_page():
    if not check_session(): return
    render_hero("Review", "Finalize")
    if st.button("⬅️ Edit"): st.session_state.app_mode = "workspace"; st.rerun()
    
    tier = st.session_state.get("locked_tier", "Standard")
    if tier != "Campaign" and not st.session_state.get("to_addr"): _save_addresses_from_widgets(tier, False)

    txt = st.text_area("Body", key="transcribed_text", height=300)
    
    if st.button("👁️ Preview PDF"):
        if letter_format:
            to_obj = StandardAddress.from_dict(st.session_state.get("to_addr", {}))
            from_obj = StandardAddress.from_dict(st.session_state.get("from_addr", {}))
            
            sig_path = None
            if st.session_state.get("sig_data") is not None:
                img = Image.fromarray(st.session_state.sig_data.astype('uint8'), 'RGBA')
                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp: img.save(tmp.name); sig_path = tmp.name
            
            pdf = letter_format.create_pdf(txt, to_obj.to_pdf_string(), from_obj.to_pdf_string(), (tier=="Heirloom"), (tier=="Santa"), sig_path)
            
            if pdf:
                b64 = base64.b64encode(pdf).decode()
                st.markdown(f'<embed src="data:application/pdf;base64,{b64}" width="100%" height="500" type="application/pdf">', unsafe_allow_html=True)
            if sig_path: os.remove(sig_path)

    if st.button("🚀 Send Letter", type="primary"):
        if len(txt) < 5: st.error("Too short"); return
        targets = []
        if tier == "Campaign": targets = st.session_state.get("bulk_targets", [])
        elif tier == "Civic": 
            for r in st.session_state.get("civic_targets", []): targets.append(r['address_obj'])
        else: targets.append(st.session_state.to_addr)
        
        with st.spinner("Sending..."):
            errs = []
            sig_path = None
            if st.session_state.get("sig_data") is not None:
                img = Image.fromarray(st.session_state.sig_data.astype('uint8'), 'RGBA')
                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp: img.save(tmp.name); sig_path = tmp.name
            
            for i, tgt in enumerate(targets):
                to_obj = StandardAddress.from_dict(tgt)
                from_obj = StandardAddress.from_dict(st.session_state.from_addr)
                pdf = letter_format.create_pdf(txt, to_obj.to_pdf_string(), from_obj.to_pdf_string(), (tier=="Heirloom"), (tier=="Santa"), sig_path)
                
                is_ok = False
                if tier in ["Standard", "Civic", "Campaign"] and mailer:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tpdf: tpdf.write(pdf); tpdf.close(); tpath=tpdf.name
                    ok, res = mailer.send_letter(tpath, tgt, st.session_state.from_addr, st.session_state.get("is_certified", False))
                    try: os.remove(tpath)
                    except: pass
                    if ok: is_ok = True
                    else: errs.append(f"Fail: {res}")
                
                status = "Completed" if is_ok else "Pending Admin"
                if not is_ok and tier in ["Standard", "Civic", "Campaign"]: status = "Failed"
                
                if database:
                    d_id = st.session_state.get("current_draft_id") if i==0 else None
                    if d_id: database.update_draft_data(d_id, tgt, st.session_state.from_addr, content=txt, status=status)
                    else: database.save_draft(st.session_state.user_email, txt, tier, "0.00", to_addr=tgt, from_addr=st.session_state.from_addr, status=status)
            
            if sig_path: os.remove(sig_path)
            
            if errs: st.error("Errors occurred"); st.write(errs)
            else: 
                st.success("✅ Sent!")
                if tier in ["Santa", "Heirloom"] and mailer: mailer.send_admin_alert(st.session_state.user_email, txt, tier)
                if st.button("New Letter"): reset_app(); st.rerun()

# --- 9. MAIN ROUTER ---
def show_main_app():
    if "app_mode" not in st.session_state: reset_app()
    mode = st.session_state.app_mode
    
    if mode == "splash":
        try: import ui_splash; ui_splash.show_splash()
        except: st.error("Splash Missing"); st.button("Login", on_click=lambda: st.session_state.update(app_mode="login"))
    elif mode == "login":
        try: import ui_login; ui_login.show_login(handle_login, handle_signup)
        except: st.error("Login Missing")
    elif mode == "store": render_store_page()
    elif mode == "workspace": render_workspace_page()
    elif mode == "review": render_review_page()
    elif mode == "admin":
        try: import ui_admin; ui_admin.show_admin()
        except: st.error("Admin Missing")
    elif mode == "legal": render_legal_page()
    else: render_store_page()