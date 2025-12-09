import streamlit as st
from streamlit_drawable_canvas import st_canvas
import os
import tempfile
import base64
import io
from PIL import Image

# --- IMPORTS ---
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

from address_standard import StandardAddress

# --- CONFIG ---
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

# --- HELPERS ---
def reset_app():
    """Restores session to a clean state while keeping login."""
    recovered_draft = st.query_params.get("draft_id")
    # Clean up session keys but keep user info
    keys = ["audio_path", "transcribed_text", "payment_complete", "sig_data", "to_addr", 
            "civic_targets", "bulk_targets", "bulk_paid_qty", "is_intl", "is_certified", 
            "letter_sent_success", "locked_tier", "w_to_name", "w_to_street", "w_to_street2", 
            "w_to_city", "w_to_state", "w_to_zip", "w_to_country", "addr_book_idx", 
            "last_tracking_num", "campaign_errors", "current_stripe_id", "current_draft_id"]
    for k in keys:
        if k in st.session_state: del st.session_state[k]
    st.session_state.to_addr = {}
    
    # Explicitly clear params per documentation "Success button explicitly clears st.query_params"
    if "draft_id" in st.query_params and not recovered_draft:
        st.query_params.clear()

    if recovered_draft:
        st.session_state.current_draft_id = recovered_draft
        st.session_state.app_mode = "workspace" 
        st.success("🔄 Session Restored!")
    elif st.session_state.get("user_email"): 
        st.session_state.app_mode = "store"
    else: 
        st.session_state.app_mode = "splash"

def render_hero(title, subtitle):
    # CSS FIX: Forces white text on blue background
    st.markdown(f"""
    <style>
        .custom-hero h1, .custom-hero div {{ color: white !important; }}
    </style>
    <div class="custom-hero" style="
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        padding: 30px; border-radius: 12px; text-align: center; margin-bottom: 25px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1); color: white;">
        <h1 style="margin: 0; font-size: 2.5rem; font-weight: 700;">{title}</h1>
        <div style="font-size: 1.1rem; opacity: 0.95; margin-top: 5px;">{subtitle}</div>
    </div>
    """, unsafe_allow_html=True)

def _save_addresses_from_widgets(tier, is_intl):
    # Capture sender
    if tier == "Santa":
        st.session_state.from_addr = {"name": "Santa Claus", "street": "123 Elf Road", "city": "North Pole", "state": "NP", "zip": "88888", "country": "NP"}
    else:
        st.session_state.from_addr = {
            "name": st.session_state.get("w_from_name"),
            "street": st.session_state.get("w_from_street"),
            "address_line2": st.session_state.get("w_from_street2", ""),
            "city": st.session_state.get("w_from_city"),
            "state": st.session_state.get("w_from_state"),
            "zip": st.session_state.get("w_from_zip"),
            "country": st.session_state.get("w_from_country", "US"),
            "email": st.session_state.get("user_email")
        }
    # Capture recipient
    if tier == "Civic":
        st.session_state.to_addr = {"name": "Civic Action", "street": "Capitol", "city": "DC", "state": "DC", "zip": "20000", "country": "US"}
    else:
        st.session_state.to_addr = {
            "name": st.session_state.get("w_to_name"),
            "street": st.session_state.get("w_to_street"),
            "address_line2": st.session_state.get("w_to_street2", ""),
            "city": st.session_state.get("w_to_city"),
            "state": st.session_state.get("w_to_state"),
            "zip": st.session_state.get("w_to_zip"),
            "country": st.session_state.get("w_to_country", "US")
        }

# --- PAGE: STORE ---
def render_store_page():
    u_email = st.session_state.get("user_email")
    if not u_email:
        st.warning("⚠️ Session Expired."); st.button("Login", on_click=lambda: st.session_state.update(app_mode="login")); return

    # --- RESTORED LOGIC: CHECK PAYMENT RETURN ---
    session_id = st.query_params.get("session_id")
    if session_id and not st.session_state.get("payment_complete"):
        with st.spinner("Verifying Payment..."):
            if payment_engine:
                success, details = payment_engine.verify_session(session_id)
                if success:
                    st.session_state.payment_complete = True
                    # Parse metadata from Stripe to restore state
                    meta = details.get('metadata', {})
                    st.session_state.locked_tier = meta.get('tier', 'Standard')
                    st.session_state.is_intl = (meta.get('intl') == '1')
                    st.session_state.is_certified = (meta.get('certified') == '1')
                    
                    # Log Audit
                    if audit_engine: audit_engine.log_event(u_email, "PAYMENT_SUCCESS", session_id, {"amount": details.get('amount_total')})
                    
                    st.success("Payment Confirmed! Redirecting...")
                    st.session_state.app_mode = "workspace"
                    st.rerun()
                else:
                    st.error("Payment Verification Failed.")
            else:
                st.error("Payment Engine Missing")

    render_hero("Select Service", "Choose your letter type")
    
    # Check Admin
    try:
        if secrets_manager and secrets_manager.get_secret("admin.email") == u_email.lower():
            if st.button("🔐 Admin Console", type="secondary"): st.session_state.app_mode = "admin"; st.rerun()
    except: pass

    c1, c2 = st.columns([2, 1])
    with c1:
        with st.container(border=True):
            st.subheader("Available Packages")
            tiers = ["Standard", "Heirloom", "Civic", "Santa", "Campaign"]
            labels = {"Standard": "⚡ Standard ($2.99)", "Heirloom": "🏺 Heirloom ($5.99)", "Civic": "🏛️ Civic ($6.99)", "Santa": "🎅 Santa ($9.99)", "Campaign": "📢 Campaign (Bulk)"}
            
            sel = st.radio("Select Tier", tiers, format_func=lambda x: labels[x], key="tier_sel")
            tier_code = sel
            
            qty = 1; price = 0.0
            if tier_code == "Campaign":
                qty = st.number_input("Recipients", 10, 5000, 50, 10)
                price = 2.99 + ((qty - 1) * 1.99)
                st.caption(f"Pricing: First letter $2.99, then $1.99/ea")
            else:
                price = {"Standard": 2.99, "Heirloom": 5.99, "Civic": 6.99, "Santa": 9.99}[tier_code]

            is_intl = False; is_certified = False
            if tier_code in ["Standard", "Heirloom"]:
                c_opt1, c_opt2 = st.columns(2)
                if c_opt1.checkbox("International? (+$2.00)"): price += 2.00; is_intl = True
                if c_opt2.checkbox("Certified Mail? (+$12.00)"): price += 12.00; is_certified = True
            
            st.session_state.is_intl = is_intl
            st.session_state.is_certified = is_certified

    with c2:
        with st.container(border=True):
            st.subheader("Checkout")
            code = st.text_input("Promo Code")
            discounted = False
            if code and promo_engine and promo_engine.validate_code(code): discounted = True; st.success("Code Applied!")
            
            st.metric("Total", f"${0.00 if discounted else price:.2f}")
            
            if st.button("🚀 Pay & Start", type="primary", use_container_width=True):
                # Ghost Draft prevention
                d_id = st.session_state.get("current_draft_id")
                if not d_id and database:
                     d_id = database.save_draft(u_email, "", tier_code, "0.00" if discounted else str(price))
                     st.session_state.current_draft_id = d_id
                     st.query_params["draft_id"] = str(d_id)
                elif d_id and database:
                     database.update_draft_data(d_id, status="Draft", tier=tier_code, price=str(price))

                if discounted:
                     if promo_engine: promo_engine.log_usage(code, u_email)
                     if audit_engine: audit_engine.log_event(u_email, "FREE_TIER", None, {"code": code})
                     st.session_state.payment_complete = True
                     st.session_state.locked_tier = tier_code
                     st.session_state.bulk_paid_qty = qty
                     st.session_state.app_mode = "workspace"
                     st.rerun()
                else:
                     link = f"{YOUR_APP_URL}?tier={tier_code}&session_id={{CHECKOUT_SESSION_ID}}&draft_id={d_id}"
                     if is_intl: link += "&intl=1"
                     if is_certified: link += "&certified=1"
                     if tier_code == "Campaign": link += f"&qty={qty}"
                     
                     if payment_engine:
                         meta = {"tier": tier_code, "intl": "1" if is_intl else "0", "certified": "1" if is_certified else "0"}
                         url, _ = payment_engine.create_checkout_session(f"VerbaPost {tier_code}", int(price*100), link, YOUR_APP_URL, metadata=meta)
                         if url: st.link_button("👉 Complete Payment", url)
                     else: st.error("Payment Engine Missing")

# --- PAGE: WORKSPACE ---
def render_workspace_page():
    tier = st.session_state.get("locked_tier", "Standard")
    render_hero("Compose Letter", f"{tier} Edition")
    
    # Pre-fill logic
    u_addr = {}
    if database:
        p = database.get_user_profile(st.session_state.user_email)
        if p: u_addr = {"name": p.full_name, "street": p.address_line1, "street2": getattr(p, "address_line2", ""), "city": p.address_city, "state": p.address_state, "zip": p.address_zip}

    with st.container(border=True):
        if tier == "Campaign":
            st.subheader("📂 Upload Mailing List")
            if not bulk_engine: st.error("Bulk Engine Missing"); return
            up = st.file_uploader("Upload CSV", type=['csv'])
            if up:
                contacts, err = bulk_engine.parse_csv(up)
                if err: st.error(err)
                else:
                    limit = st.session_state.get("bulk_paid_qty", 1000)
                    if len(contacts) > limit: st.warning(f"Truncating to {limit} recipients."); contacts = contacts[:limit]
                    st.success(f"Loaded {len(contacts)} contacts."); st.dataframe(contacts[:3])
                    if st.button("Confirm List"): st.session_state.bulk_targets = contacts; st.toast("Saved!")
        else:
            # ADDRESSING INPUTS
            if tier == "Santa": st.info("🎅 From: Santa Claus, North Pole")
            elif tier == "Civic": 
                st.subheader("🏛️ Your Representatives")
                c1, c2 = st.columns(2)
                fn = c1.text_input("Your Name", u_addr.get("name",""), key="w_from_name")
                fs = c1.text_input("Street", u_addr.get("street",""), key="w_from_street")
                fc = c2.text_input("City", u_addr.get("city",""), key="w_from_city")
                fz = c2.text_input("Zip", u_addr.get("zip",""), key="w_from_zip")
                st.session_state.w_from_state = u_addr.get("state",""); st.session_state.w_from_country = "US"
                
                if st.button("🔍 Find Reps") and civic_engine:
                    reps = civic_engine.get_reps(f"{fs}, {fc} {fz}")
                    if reps: st.session_state.civic_targets = reps; st.success(f"Found {len(reps)} Reps!")
                    else: st.error("No reps found.")
                
            else:
                st.subheader("📍 Addressing")
                with st.expander("✉️ Sender", expanded=False):
                    st.text_input("Name", u_addr.get("name",""), key="w_from_name")
                    st.text_input("Street", u_addr.get("street",""), key="w_from_street")
                    st.text_input("Apt/Suite", u_addr.get("street2",""), key="w_from_street2")
                    c1, c2, c3 = st.columns(3)
                    c1.text_input("City", u_addr.get("city",""), key="w_from_city")
                    c2.text_input("State", u_addr.get("state",""), key="w_from_state")
                    c3.text_input("Zip", u_addr.get("zip",""), key="w_from_zip")
                    st.session_state.w_from_country = "US"

            if tier != "Civic":
                st.markdown("**📮 Recipient**")
                if database:
                    cons = database.get_contacts(st.session_state.user_email)
                    if cons:
                         opts = ["-- Address Book --"] + [c.name for c in cons]
                         idx = st.selectbox("Quick Fill", range(len(opts)), format_func=lambda x: opts[x])
                         if idx > 0:
                             c = cons[idx-1]
                             st.session_state.w_to_name = c.name; st.session_state.w_to_street = c.street; st.session_state.w_to_city = c.city; st.session_state.w_to_state = c.state; st.session_state.w_to_zip = c.zip_code
                
                st.text_input("Name", key="w_to_name")
                st.text_input("Street", key="w_to_street")
                st.text_input("Apt/Suite", key="w_to_street2")
                c1, c2, c3 = st.columns(3)
                c1.text_input("City", key="w_to_city")
                c2.text_input("State", key="w_to_state")
                c3.text_input("Zip", key="w_to_zip")
                st.session_state.w_to_country = "US"

            if st.button("Save Addresses", type="primary"):
                _save_addresses_from_widgets(tier, st.session_state.get("is_intl"))
                st.toast("Addresses Saved!")

    st.divider()
    
    # INPUT & SIG
    c_sig, c_mic = st.columns(2)
    with c_sig:
        st.write("✍️ Signature")
        if tier == "Santa": st.info("Signed: Santa")
        else: 
            canvas = st_canvas(stroke_width=2, height=150, width=400, key="sig_can")
            if canvas.image_data is not None: st.session_state.sig_data = canvas.image_data

    with c_mic:
        st.write("🎤 Content")
        if ai_engine:
            audio = st.audio_input("Record")
            if audio:
                with st.spinner("Transcribing..."):
                    st.session_state.transcribed_text = ai_engine.transcribe_audio(audio)
                    st.session_state.app_mode = "review"; st.rerun()
            
            up = st.file_uploader("Or Upload Audio", type=['wav','mp3','m4a'])
            if up and st.button("Transcribe Upload"):
                 with tempfile.NamedTemporaryFile(delete=False, suffix="."+up.name.split('.')[-1]) as tmp:
                     tmp.write(up.getvalue()); tmp.close()
                     st.session_state.transcribed_text = ai_engine.transcribe_audio(tmp.name)
                     st.session_state.app_mode = "review"; st.rerun()
        else: st.error("AI Engine Missing")

# --- PAGE: REVIEW & SEND ---
def render_review_page():
    render_hero("Review Letter", "Finalize and Send")
    tier = st.session_state.get("locked_tier")
    
    if st.button("⬅️ Edit"): st.session_state.app_mode = "workspace"; st.rerun()

    # AI Tools
    c1, c2, c3, c4 = st.columns(4)
    if ai_engine:
        txt = st.session_state.get("transcribed_text", "")
        if c1.button("Fix Grammar"): st.session_state.transcribed_text = ai_engine.refine_text(txt, "Grammar"); st.rerun()
        if c2.button("Professional"): st.session_state.transcribed_text = ai_engine.refine_text(txt, "Professional"); st.rerun()
        if c3.button("Friendly"): st.session_state.transcribed_text = ai_engine.refine_text(txt, "Friendly"); st.rerun()
        if c4.button("Concise"): st.session_state.transcribed_text = ai_engine.refine_text(txt, "Concise"); st.rerun()

    txt = st.text_area("Body", key="transcribed_text", height=300)
    
    # PDF PREVIEW
    if st.button("👁️ Preview PDF"):
        if letter_format:
            to_addr = StandardAddress.from_dict(st.session_state.get("to_addr", {}))
            from_addr = StandardAddress.from_dict(st.session_state.get("from_addr", {}))
            
            sig_path = None
            if st.session_state.get("sig_data") is not None:
                img = Image.fromarray(st.session_state.sig_data.astype('uint8'), 'RGBA')
                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                    img.save(tmp.name); sig_path = tmp.name

            pdf = letter_format.create_pdf(txt, to_addr.to_pdf_string(), from_addr.to_pdf_string(), 
                                           is_heirloom=(tier=="Heirloom"), is_santa=(tier=="Santa"), signature_path=sig_path)
            
            if pdf:
                b64 = base64.b64encode(pdf).decode('utf-8')
                st.markdown(f'<embed src="data:application/pdf;base64,{b64}" width="100%" height="500" type="application/pdf">', unsafe_allow_html=True)
                st.download_button("⬇️ Download PDF", pdf, "proof.pdf", "application/pdf")
            
            if sig_path: os.remove(sig_path)
        else: st.error("PDF Engine Missing")

    # SEND LOGIC
    if not st.session_state.get("letter_sent_success"):
        if st.button("🚀 Send Letter", type="primary"):
            if len(txt) < 5: st.error("Letter too short."); return
            
            targets = []
            if tier == "Campaign": targets = st.session_state.get("bulk_targets", [])
            elif tier == "Civic": 
                for r in st.session_state.get("civic_targets", []):
                     t = r.get('address_obj'); t['country'] = 'US'; targets.append(t)
            else: targets.append(st.session_state.to_addr)

            with st.spinner("Processing..."):
                errs = []
                sig_db = None; sig_path = None
                if st.session_state.get("sig_data") is not None:
                    img = Image.fromarray(st.session_state.sig_data.astype('uint8'), 'RGBA')
                    buf = io.BytesIO(); img.save(buf, format="PNG"); sig_db = base64.b64encode(buf.getvalue()).decode()
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp: img.save(tmp.name); sig_path = tmp.name

                prog = st.progress(0)
                for i, tgt in enumerate(targets):
                    to_obj = StandardAddress.from_dict(tgt)
                    from_obj = StandardAddress.from_dict(st.session_state.from_addr)
                    pdf = letter_format.create_pdf(txt, to_obj.to_pdf_string(), from_obj.to_pdf_string(), (tier=="Heirloom"), (tier=="Santa"), sig_path)
                    
                    is_ok = False
                    if tier in ["Standard", "Civic", "Campaign"]:
                         if mailer:
                             with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tpdf: tpdf.write(pdf); tpdf.close(); tpath = tpdf.name
                             ok, resp = mailer.send_letter(tpath, tgt, st.session_state.from_addr, st.session_state.is_certified)
                             try: os.remove(tpath)
                             except: pass
                             if ok: is_ok = True
                             else: errs.append(f"Failed {tgt.get('name')}: {resp}")
                         else:
                             errs.append("System Error: Mailer Missing")
                    else:
                        is_ok = False

                    status = "Completed" if is_ok else "Pending Admin"
                    if not is_ok and tier in ["Standard", "Civic", "Campaign"]: status = "Failed/Retry"
                    
                    if database:
                        d_id = st.session_state.get("current_draft_id")
                        if tier == "Campaign" and i > 0: d_id = None 
                        
                        if d_id: database.update_draft_data(d_id, tgt, st.session_state.from_addr, content=txt, status=status)
                        else: database.save_draft(st.session_state.user_email, txt, tier, "0.00", to_addr=tgt, from_addr=st.session_state.from_addr, status=status, sig_data=sig_db)

                    prog.progress((i+1)/len(targets))
                
                if sig_path: os.remove(sig_path)
                
                if errs: st.error(f"{len(errs)} Failures"); st.write(errs)
                else: 
                    st.session_state.letter_sent_success = True
                    if tier in ["Santa", "Heirloom"] and mailer: mailer.send_admin_alert(st.session_state.user_email, txt, tier)
                    st.rerun()

    else:
        st.success("✅ Sent Successfully!")
        if st.button("Start New Letter"): reset_app(); st.rerun()

# --- ROUTER (FINAL) ---
def show_main_app():
    if "app_mode" not in st.session_state: reset_app()
    mode = st.session_state.app_mode
    
    if mode == "splash":
        try:
            import ui_splash
            # SAFE CALL: Check if function exists before calling, else fallback
            if hasattr(ui_splash, 'render_splash'):
                ui_splash.render_splash()
            elif hasattr(ui_splash, 'show_splash'):
                ui_splash.show_splash()
            else:
                # Fallback if the module exists but the function name is different
                st.title("VerbaPost (Debug)")
                st.write("Splash module loaded but render function not found.")
                if st.button("Login"): st.session_state.app_mode = "login"; st.rerun()
        except ImportError:
             st.title("Splash Missing"); st.button("Login", on_click=lambda: st.session_state.update(app_mode="login"))
    
    elif mode == "login":
        try: import ui_login; ui_login.render_login()
        except ImportError: st.error("Login Module Missing")
        
    elif mode == "store": render_store_page()
    elif mode == "workspace": render_workspace_page()
    elif mode == "review": render_review_page()
    elif mode == "admin":
        try: import ui_admin; ui_admin.render_admin()
        except: st.error("Admin Missing")
    elif mode == "legal": render_legal_page()
    else: render_store_page()