import streamlit as st
from streamlit_drawable_canvas import st_canvas
import os
import tempfile
import base64
import io
import time
from PIL import Image

# --- 1. CRITICAL: LOAD CORE DEFINITIONS FIRST ---
# This prevents the 'KeyError: address_standard' crash by defining the class locally if the file isn't ready
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

# --- 2. LOAD MODULES (DEFENSIVE) ---
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
    """Restores session to a clean state while keeping login."""
    recovered = st.query_params.get("draft_id")
    # Clean up session keys but keep user info
    keys = ["audio_path", "transcribed_text", "payment_complete", "sig_data", "to_addr", 
            "civic_targets", "bulk_targets", "bulk_paid_qty", "is_intl", "is_certified", 
            "letter_sent_success", "locked_tier", "w_to_name", "w_to_street", "w_to_street2", 
            "w_to_city", "w_to_state", "w_to_zip", "w_to_country", "addr_book_idx", 
            "last_tracking_num", "campaign_errors", "current_stripe_id", "current_draft_id",
            "w_from_name", "w_from_street", "w_from_city", "w_from_state", "w_from_zip"]
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
    """CRITICAL GUARD: Ensures user_email exists before rendering protected pages."""
    if "user_email" not in st.session_state or not st.session_state.user_email:
        st.warning("Session Expired. Please log in.")
        st.session_state.app_mode = "login"
        st.rerun()
        return False
    return True

def render_hero(title, subtitle):
    # Aggressive CSS to fix black font issue
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

# --- 5. AUTH HANDLERS (The Bridge) ---
# ui_login.py expects these specific signatures and return types

def handle_login(email, password):
    """
    Called by ui_login.py for existing users.
    NOTE: ui_login DOES NOT check return value. We must handle redirect here.
    """
    if auth_engine:
        res, err = auth_engine.sign_in(email, password)
        if res and res.user:
            st.session_state.user_email = res.user.email
            st.session_state.app_mode = "store"
            st.success("Welcome back!")
            time.sleep(0.5)
            st.rerun()
        else: 
            st.error(f"Login failed: {err}")

def handle_signup(email, password, name, street, street2, city, state, zip_code, country, language):
    """
    Called by ui_login.py for new users.
    NOTE: ui_login DOES check return value (res, err). We must return it.
    """
    if auth_engine:
        res, err = auth_engine.sign_up(email, password, name, street, street2, city, state, zip_code, country, language)
        if res and res.user:
            st.session_state.user_email = res.user.email
            st.session_state.app_mode = "store"
            # ui_login handles the success message, but we set the state
            return res, None 
        else: 
            return None, err
    return None, "Auth Engine Missing"

# --- 6. PAGE: STORE ---
def render_store_page():
    # Payment Verification Loop (Zombie Proofing)
    sess_id = st.query_params.get("session_id")
    
    # If returning from payment, handle it BEFORE checking session
    # This prevents the "redirect to login" loop if session was lost
    if sess_id and not st.session_state.get("payment_complete"):
        with st.spinner("Verifying Payment..."):
            if payment_engine:
                success, details = payment_engine.verify_session(sess_id)
                if success:
                    st.session_state.payment_complete = True
                    
                    # AUTO-LOGIN from Stripe Data if session lost
                    if not st.session_state.get("user_email"):
                        try:
                            cust_email = details.get("customer_details", {}).get("email")
                            if cust_email: st.session_state.user_email = cust_email
                        except: pass

                    if audit_engine: audit_engine.log_event(st.session_state.get("user_email"), "PAYMENT_SUCCESS", sess_id, {"amount": details.get('amount_total')})
                    st.success("Payment Received!")
                    st.session_state.app_mode = "workspace"
                    st.rerun()
                else: 
                    st.error("Payment Verification Failed")

    # Now verify login
    if not check_session(): return
    u_email = st.session_state.user_email

    render_hero("Select Service", "Choose your letter type")
    
    # Admin Check
    try:
        if secrets_manager:
            admin_target = secrets_manager.get_secret("admin.email")
            if admin_target and str(u_email).lower() == str(admin_target).lower():
                if st.button("🔐 Admin Console", type="secondary"): st.session_state.app_mode = "admin"; st.rerun()
    except: pass

    c1, c2 = st.columns([2, 1])
    with c1:
        with st.container(border=True):
            st.subheader("Available Packages")
            tier_options = ["Standard", "Heirloom", "Civic", "Santa", "Campaign"]
            tier_labels = {"Standard": "⚡ Standard ($2.99)", "Heirloom": "🏺 Heirloom ($5.99)", "Civic": "🏛️ Civic ($6.99)", "Santa": "🎅 Santa ($9.99)", "Campaign": "📢 Campaign (Bulk)"}
            
            # Smart default selection
            pre_sel = 0
            if "target_marketing_tier" in st.session_state:
                t = st.session_state.target_marketing_tier
                if t in tier_options: pre_sel = tier_options.index(t)

            sel = st.radio("Select Tier", tier_options, format_func=lambda x: tier_labels[x], index=pre_sel)
            tier_code = sel
            
            # Pricing Logic
            qty = 1; price = 0.0
            if tier_code == "Campaign":
                qty = st.number_input("Number of Recipients", 10, 5000, 50, 10)
                price = 2.99 + ((qty - 1) * 1.99)
                st.caption(f"Pricing: First letter $2.99, then $1.99/ea")
            else:
                prices = {"Standard": 2.99, "Heirloom": 5.99, "Civic": 6.99, "Santa": 9.99}
                price = prices[tier_code]

            is_intl = False; is_certified = False
            if tier_code in ["Standard", "Heirloom"]:
                c1a, c1b = st.columns(2)
                if c1a.checkbox("Send Internationally? (+$2.00)"): price += 2.00; is_intl = True
                if c1b.checkbox("📜 Certified Mail (+$12.00)"): price += 12.00; is_certified = True; st.caption("Includes tracking.")
            
            st.session_state.locked_tier = tier_code
            st.session_state.is_intl = is_intl
            st.session_state.is_certified = is_certified
            st.session_state.bulk_paid_qty = qty

    with c2:
        with st.container(border=True):
            st.subheader("Checkout")
            code = st.text_input("Promo Code")
            discounted = False
            if promo_engine and code:
                if promo_engine.validate_code(code): discounted = True; st.success("✅ Applied!")
            
            if discounted:
                st.metric("Total", "$0.00", delta=f"-${price:.2f} off")
                if st.button("🚀 Start (Free)", type="primary", use_container_width=True):
                    if promo_engine: promo_engine.log_usage(code, u_email)
                    
                    # Create DB Row
                    d_id = st.session_state.get("current_draft_id")
                    if d_id and database: database.update_draft_data(d_id, status="Draft", content="", tier=tier_code, price="0.00")
                    elif database: 
                        d_id = database.save_draft(u_email, "", tier_code, "0.00")
                        st.session_state.current_draft_id = d_id
                        st.query_params["draft_id"] = str(d_id)

                    if audit_engine: audit_engine.log_event(u_email, "FREE_TIER_STARTED", None, {"code": code})
                    st.session_state.payment_complete = True
                    st.session_state.app_mode = "workspace"
                    st.rerun()
            else:
                st.metric("Total", f"${price:.2f}")
                if st.button(f"Pay ${price:.2f} & Start", type="primary", use_container_width=True):
                    # Save State
                    d_id = st.session_state.get("current_draft_id")
                    if d_id and database: database.update_draft_data(d_id, status="Draft", tier=tier_code, price=price)
                    elif database: 
                        d_id = database.save_draft(u_email, "", tier_code, price)
                        st.session_state.current_draft_id = d_id
                        st.query_params["draft_id"] = str(d_id)
                    
                    link = f"{YOUR_APP_URL}?tier={tier_code}&session_id={{CHECKOUT_SESSION_ID}}&draft_id={d_id}"
                    if is_intl: link += "&intl=1"
                    if is_certified: link += "&certified=1"
                    if tier_code == "Campaign": link += f"&qty={qty}"
                    
                    if payment_engine:
                        # SAFE CALL: No metadata argument to ensure compatibility
                        url, sess_id = payment_engine.create_checkout_session(f"VerbaPost {tier_code}", int(price*100), link, YOUR_APP_URL)
                        if url: st.markdown(f'<a href="{url}" target="_self" style="text-decoration:none;"><button style="width:100%;padding:10px;background:#6772e5;color:white;border:none;border-radius:5px;cursor:pointer;">👉 Pay with Stripe</button></a>', unsafe_allow_html=True)
                    else: st.error("Payment Engine Missing")

# --- 7. PAGE: WORKSPACE ---
def render_workspace_page():
    if not check_session(): return
    tier = st.session_state.get("locked_tier", "Standard")
    render_hero("Compose Letter", f"{tier} Edition")
    
    # Pre-fetch user data
    u_email = st.session_state.get("user_email")
    u_addr = {}
    if database:
        p = database.get_user_profile(u_email)
        if p: 
            u_addr = {"name": p.full_name, "street": p.address_line1, "street2": getattr(p, "address_line2", ""), "city": p.address_city, "state": p.address_state, "zip": p.address_zip, "country": getattr(p, "country", "US")}
            # Apply defaults if empty
            if "w_from_name" not in st.session_state: st.session_state.w_from_name = u_addr.get("name","")
            if "w_from_street" not in st.session_state: st.session_state.w_from_street = u_addr.get("street","")
            if "w_from_street2" not in st.session_state: st.session_state.w_from_street2 = u_addr.get("street2","")
            if "w_from_city" not in st.session_state: st.session_state.w_from_city = u_addr.get("city","")
            if "w_from_state" not in st.session_state: st.session_state.w_from_state = u_addr.get("state","")
            if "w_from_zip" not in st.session_state: st.session_state.w_from_zip = u_addr.get("zip","")

    with st.container(border=True):
        
        # --- CAMPAIGN TIER ---
        if tier == "Campaign":
            st.subheader("Upload Mailing List")
            if not bulk_engine: st.error("Bulk Engine Missing"); return
            up = st.file_uploader("CSV File", type=['csv'])
            if up:
                contacts, err = bulk_engine.parse_csv(up)
                if err: st.error(err)
                else:
                    limit = st.session_state.get("bulk_paid_qty", 1000)
                    if len(contacts) > limit: contacts = contacts[:limit]; st.warning(f"Truncated to {limit}")
                    st.success(f"{len(contacts)} contacts loaded.")
                    st.dataframe(contacts[:5])
                    if st.button("Confirm"): st.session_state.bulk_targets = contacts; st.toast("Saved!")
        
        # --- SANTA TIER ---
        elif tier == "Santa":
            st.info("🎅 **From:** Santa Claus, North Pole (Locked)")
            st.subheader("📍 Addressing")
            st.markdown("**📮 To (Recipient)**")
            st.text_input("Child's Name", key="w_to_name")
            st.text_input("Street Address", key="w_to_street")
            st.text_input("Apt / Suite (Optional)", key="w_to_street2")
            c1, c2, c3 = st.columns([2, 1, 1])
            c1.text_input("City", key="w_to_city")
            c2.text_input("State", key="w_to_state")
            c3.text_input("Zip", key="w_to_zip")
            st.session_state.w_to_country = "US"
            
            if st.button("Save Address", type="primary"):
                st.session_state.from_addr = {"name": "Santa Claus", "street": "123 Elf Road", "city": "North Pole", "state": "NP", "zip": "88888", "country": "NP"}
                st.session_state.to_addr = {
                    "name": st.session_state.w_to_name, "street": st.session_state.w_to_street,
                    "address_line2": st.session_state.w_to_street2, "city": st.session_state.w_to_city,
                    "state": st.session_state.w_to_state, "zip": st.session_state.w_to_zip, "country": "US"
                }
                st.toast("Address Saved!")

        # --- CIVIC TIER ---
        elif tier == "Civic":
            st.subheader("🏛️ Your Representatives")
            with st.expander("📍 Voting Address (From Profile)", expanded=False):
                st.text_input("Your Name", key="w_from_name")
                st.text_input("Street", key="w_from_street")
                st.text_input("City", key="w_from_city")
                st.text_input("State", key="w_from_state")
                st.text_input("Zip", key="w_from_zip")
                st.session_state.w_from_country = "US"
                if st.button("Search Again"):
                    if "civic_targets" in st.session_state: del st.session_state.civic_targets
                    st.rerun()

            if "civic_targets" not in st.session_state:
                full = f"{st.session_state.get('w_from_street')} {st.session_state.get('w_from_city')} {st.session_state.get('w_from_zip')}"
                if len(full) > 10 and civic_engine:
                    if st.button("Find Reps"):
                        with st.spinner("Looking up districts..."):
                            reps = civic_engine.get_reps(full)
                            if reps: st.session_state.civic_targets = reps; st.rerun()
                            else: st.error("No reps found.")
            
            if "civic_targets" in st.session_state:
                st.success(f"✅ Found {len(st.session_state.civic_targets)} Elected Officials")
                for r in st.session_state.civic_targets: st.write(f"🏛️ {r['name']} ({r['title']})")

        # --- STANDARD / HEIRLOOM ---
        else:
            st.subheader("📍 Addressing")
            with st.expander(f"✉️ Sender: {u_addr.get('name', '')}", expanded=False):
                st.text_input("Sender Name", key="w_from_name")
                st.text_input("Sender Street", key="w_from_street")
                st.text_input("Sender Apt/Suite", key="w_from_street2")
                c1, c2 = st.columns([1, 2])
                try: idx = list(COUNTRIES.keys()).index(u_addr.get('country','US'))
                except: idx = 0
                c1.selectbox("From Country", list(COUNTRIES.keys()), index=idx, key="w_from_country")
                c2.text_input("Sender City", key="w_from_city")
                c3, c4 = st.columns(2)
                c3.text_input("State", key="w_from_state")
                c4.text_input("Zip", key="w_from_zip")

            st.markdown("---")
            st.markdown("**📮 To (Recipient)**")
            if database:
                cons = database.get_contacts(u_email)
                if cons:
                    opts = ["-- Select from Address Book --"] + [c.name for c in cons]
                    idx = st.selectbox("Quick Fill", range(len(opts)), format_func=lambda x: opts[x], key="addr_book_idx")
                    if idx > 0:
                        c = cons[idx-1]
                        st.session_state.w_to_name = c.name; st.session_state.w_to_street = c.street; st.session_state.w_to_street2 = getattr(c, 'street2', ''); st.session_state.w_to_city = c.city; st.session_state.w_to_state = c.state; st.session_state.w_to_zip = c.zip_code; st.session_state.w_to_country = c.country

            st.text_input("Recipient Name", key="w_to_name")
            st.text_input("Recipient Street", key="w_to_street")
            st.text_input("Recipient Apt/Suite", key="w_to_street2")
            
            if st.session_state.get("is_intl"):
                c1, c2 = st.columns([1, 2])
                c1.selectbox("Country", list(COUNTRIES.keys()), key="w_to_country")
                c2.text_input("City", key="w_to_city")
                c3, c4 = st.columns(2)
                c3.text_input("State/Province", key="w_to_state")
                c4.text_input("Postal Code", key="w_to_zip")
            else:
                c1, c2, c3 = st.columns(3)
                c1.text_input("City", key="w_to_city")
                c2.text_input("State", key="w_to_state")
                c3.text_input("Zip", key="w_to_zip")
                st.session_state.w_to_country = "US"

            st.markdown("<br>", unsafe_allow_html=True)
            c_save1, c_save2 = st.columns([1, 2])
            
            if c_save1.button("Save Addresses", type="primary"):
                check_name = st.session_state.get("w_to_name", "")
                if not check_name: st.error("Please enter a name.")
                else:
                    st.session_state.from_addr = {
                        "name": st.session_state.w_from_name, "street": st.session_state.w_from_street, "address_line2": st.session_state.w_from_street2,
                        "city": st.session_state.w_from_city, "state": st.session_state.w_from_state, "zip": st.session_state.w_from_zip, "country": st.session_state.w_from_country, "email": u_email
                    }
                    st.session_state.to_addr = {
                        "name": st.session_state.w_to_name, "street": st.session_state.w_to_street, "address_line2": st.session_state.w_to_street2,
                        "city": st.session_state.w_to_city, "state": st.session_state.w_to_state, "zip": st.session_state.w_to_zip, "country": st.session_state.w_to_country
                    }
                    # Update DB
                    d_id = st.session_state.get("current_draft_id")
                    if d_id and database: database.update_draft_data(d_id, st.session_state.to_addr, st.session_state.from_addr)
                    st.toast("Addresses Saved!")

            if c_save2.button("💾 Save to Address Book"):
                if st.session_state.w_to_name and st.session_state.w_to_street:
                    database.add_contact(u_email, st.session_state.w_to_name, st.session_state.w_to_street, st.session_state.w_to_street2, st.session_state.w_to_city, st.session_state.w_to_state, st.session_state.w_to_zip, st.session_state.w_to_country)
                    st.success("Saved!")
                    st.rerun()
                else: st.error("Enter Name & Street first")

    st.write("---")
    c1, c2 = st.columns(2)
    with c1:
        st.write("✍️ **Signature**")
        if tier == "Santa": st.info("Signed by Santa")
        else: 
            canvas = st_canvas(stroke_width=2, height=150, width=400, key="sig")
            if canvas.image_data is not None: st.session_state.sig_data = canvas.image_data
    with c2:
        st.write("🎤 **Dictation**")
        if ai_engine:
            audio = st.audio_input("Record")
            if audio:
                with st.spinner("Thinking..."): st.session_state.transcribed_text = ai_engine.transcribe_audio(audio); st.session_state.app_mode="review"; st.rerun()
            
            up = st.file_uploader("Upload", type=['wav','mp3'])
            if up and st.button("Transcribe"):
                with tempfile.NamedTemporaryFile(delete=False, suffix="."+up.name.split('.')[-1]) as tmp:
                    tmp.write(up.getvalue()); st.session_state.transcribed_text = ai_engine.transcribe_audio(tmp.name); st.session_state.app_mode = "review"; st.rerun()

# --- 8. PAGE: REVIEW ---
def render_review_page():
    if not check_session(): return
    render_hero("Review", "Finalize")
    if st.button("⬅️ Edit"): st.session_state.app_mode = "workspace"; st.rerun()
    
    tier = st.session_state.get("locked_tier", "Standard")
    # Auto-Save Check
    if tier != "Campaign" and not st.session_state.get("to_addr"): 
        st.warning("⚠️ Addresses not saved properly.")

    c1, c2, c3, c4 = st.columns(4)
    txt = st.session_state.get("transcribed_text", "")
    if ai_engine:
        if c1.button("Grammar"): st.session_state.transcribed_text = ai_engine.refine_text(txt, "Grammar"); st.rerun()
        if c2.button("Professional"): st.session_state.transcribed_text = ai_engine.refine_text(txt, "Professional"); st.rerun()
        if c3.button("Friendly"): st.session_state.transcribed_text = ai_engine.refine_text(txt, "Friendly"); st.rerun()
        if c4.button("Concise"): st.session_state.transcribed_text = ai_engine.refine_text(txt, "Concise"); st.rerun()
    
    txt = st.text_area("Body", key="transcribed_text", height=300)
    
    # PDF Preview
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
                st.download_button("⬇️ Download PDF", pdf, "proof.pdf", "application/pdf")
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
                st.session_state.letter_sent_success = True
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