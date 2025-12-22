import streamlit as st
import time
import os
import hashlib
import requests
from datetime import datetime

# --- CRITICAL IMPORTS ---
import database 

# --- ENGINE IMPORTS ---
try: import ai_engine
except ImportError: ai_engine = None
try: import payment_engine
except ImportError: payment_engine = None
try: import mailer
except ImportError: mailer = None
try: import letter_format
except ImportError: letter_format = None
try: import address_standard
except ImportError: address_standard = None
try: import pricing_engine
except ImportError: pricing_engine = None
try: import bulk_engine
except ImportError: bulk_engine = None
try: import audit_engine
except ImportError: audit_engine = None
try: import civic_engine
except ImportError: civic_engine = None
try: import promo_engine
except ImportError: promo_engine = None
try: import secrets_manager
except ImportError: secrets_manager = None

# --- HELPER: EMAIL ALERT ---
def _send_alert_email(to_email, subject, html_body):
    """Sends receipts and admin alerts via Resend."""
    try:
        k_raw = secrets_manager.get_secret("email.password") or secrets_manager.get_secret("RESEND_API_KEY")
        if not k_raw: return False
        api_key = str(k_raw).strip().replace("'", "").replace('"', "")
        payload = {
            "from": "VerbaPost <receipts@verbapost.com>",
            "to": [to_email],
            "subject": subject,
            "html": html_body
        }
        requests.post("https://api.resend.com/emails", json=payload, headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"})
        return True
    except Exception as e:
        print(f"Email Alert Failed: {e}")
        return False

# --- HELPER: SAFE PROFILE GETTER ---
def get_profile_field(profile, field, default=""):
    if not profile: return default
    if isinstance(profile, dict): return profile.get(field, default)
    return getattr(profile, field, default)

def _ensure_profile_loaded():
    if st.session_state.get("authenticated"):
        needs_load = not st.session_state.get("profile_synced") or not st.session_state.get("from_name")
        if needs_load:
            try:
                email = st.session_state.get("user_email")
                profile = database.get_user_profile(email)
                if profile:
                    st.session_state.user_profile = profile
                    st.session_state.from_name = get_profile_field(profile, "full_name")
                    st.session_state.from_street = get_profile_field(profile, "address_line1") or get_profile_field(profile, "street")
                    st.session_state.from_city = get_profile_field(profile, "address_city")
                    st.session_state.from_state = get_profile_field(profile, "address_state")
                    st.session_state.from_zip = get_profile_field(profile, "address_zip")
                    st.session_state.profile_synced = True 
                    st.rerun() 
            except Exception: pass

# --- CSS INJECTOR ---
def inject_custom_css(text_size=16):
    import base64
    font_face_css = ""
    try:
        with open("type_right.ttf", "rb") as f:
            b64_font = base64.b64encode(f.read()).decode()
        font_face_css = f"""
            @font-face {{
                font-family: 'TypeRight';
                src: url('data:font/ttf;base64,{b64_font}') format('truetype');
            }}
        """
    except FileNotFoundError: font_face_css = ""

    st.markdown(f"""
        <style>
        {font_face_css}
        .stTextArea textarea {{
            font-family: 'TypeRight', 'Courier New', Courier, monospace !important;
            font-size: {text_size}px !important;
            line-height: 1.6 !important;
            background-color: #fdfbf7; 
            color: #333;
        }}
        .price-card {{ background-color: #ffffff; border-radius: 12px; padding: 20px 15px; text-align: center; border: 1px solid #e0e0e0; height: 220px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); display: flex; flex-direction: column; justify-content: flex-start; gap: 5px; }}
        .price-header {{ font-weight: 700; font-size: 1.4rem; color: #1f2937; margin-bottom: 2px; height: 35px; display: flex; align-items: center; justify-content: center; }}
        .price-sub {{ font-size: 0.75rem; font-weight: 600; color: #9ca3af; text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 5px; }}
        .price-tag {{ font-size: 2.4rem; font-weight: 800; color: #d93025; margin: 5px 0; }}
        .price-desc {{ font-size: 0.9rem; color: #4b5563; line-height: 1.3; margin-top: auto; padding-bottom: 5px; min-height: 50px; }}
        .success-box {{ background-color: #ecfdf5; border: 1px solid #10b981; padding: 20px; border-radius: 10px; text-align: center; margin-bottom: 20px; }}
        .success-title {{ color: #047857; font-size: 24px; font-weight: bold; margin-bottom: 10px; }}
        .tracking-code {{ font-family: monospace; font-size: 20px; color: #d93025; background: #fff; padding: 5px 10px; border-radius: 4px; border: 1px dashed #ccc; }}
        </style>
    """, unsafe_allow_html=True)

def load_address_book():
    if not st.session_state.get("authenticated"): return {}
    try:
        contacts = database.get_contacts(st.session_state.get("user_email"))
        result = {}
        for c in contacts:
            label = f"{c.get('name', 'Unknown')} ({c.get('street', '')[:10]}...)"
            result[label] = c
        return result
    except: return {}

def _save_new_contact(contact_data):
    try:
        if not st.session_state.get("authenticated"): return
        user_email = st.session_state.get("user_email")
        if hasattr(database, "save_contact"):
            database.save_contact(user_email, contact_data)
            return True
    except: return False

# --- CALLBACKS ---
def cb_buy_tier(tier, base_price, user_email, is_certified=False):
    if payment_engine:
        total_price = base_price
        if is_certified: total_price += 12.00
        if "promo_val" in st.session_state: total_price = max(0.0, total_price - st.session_state.promo_val)
        
        d_id = database.save_draft(user_email, "", tier, total_price) if database else None
        
        if total_price <= 0:
            st.session_state.paid_tier = tier
            st.session_state.current_draft_id = d_id
            st.session_state.app_mode = "workspace"
            # Clear promo
            if "promo_val" in st.session_state: del st.session_state.promo_val
            st.rerun()
            return

        url = payment_engine.create_checkout_session(
            line_items=[{
                "price_data": {
                    "currency": "usd",
                    "product_data": {"name": f"VerbaPost - {tier} {'(Certified)' if is_certified else ''}"},
                    "unit_amount": int(total_price * 100),
                },
                "quantity": 1,
            }],
            user_email=user_email,
            draft_id=d_id 
        )
        if url: 
            st.session_state.pending_stripe_url = url
        else:
            st.error("Payment Gateway Error")

# --- PAGE RENDERERS ---

def render_store_page():
    inject_custom_css(16)
    u_email = st.session_state.get("user_email", "")
    
    # RESET STATE ON ENTRY
    if "paid_tier" in st.session_state: del st.session_state.paid_tier
    if "receipt_data" in st.session_state: del st.session_state.receipt_data
    if "pending_stripe_url" in st.session_state: del st.session_state.pending_stripe_url
    
    if not u_email:
        st.warning("⚠️ Session Expired. Please log in.")
        if st.button("Go to Login"): st.session_state.app_mode = "login"; st.rerun()
        return

    # RESUME CHECK
    if database:
        try:
            with database.get_db_session() as session:
                draft = session.query(database.LetterDraft).filter(
                    database.LetterDraft.user_email == u_email,
                    database.LetterDraft.status == "Paid/Writing"
                ).order_by(database.LetterDraft.created_at.desc()).first()
                if draft:
                    st.info(f"👋 **Welcome Back!** You have a prepaid **{draft.tier}** letter waiting.")
                    if st.button("Resume Writing"):
                        st.session_state.paid_tier = draft.tier
                        st.session_state.current_draft_id = draft.id
                        st.session_state.letter_body = draft.content if draft.content else ""
                        st.session_state.app_mode = "workspace"
                        st.rerun()
                    st.markdown("---")
        except: pass

    st.markdown("## 📮 Select & Pay")
    
    mode = st.radio("Mode", ["Single Letter", "Bulk Campaign"], horizontal=True, label_visibility="collapsed")
    if mode == "Bulk Campaign":
        render_campaign_uploader()
        return

    st.info("ℹ️ **Process:** Select Tier ➝ Pay Securely ➝ Write Letter ➝ We Mail It.")

    if promo_engine:
        with st.expander("🎟️ Have a Promo Code?"):
            c1, c2 = st.columns([3,1])
            raw_code = c1.text_input("Code", label_visibility="collapsed", placeholder="Enter Code")
            if c2.button("Apply"):
                valid, val = promo_engine.validate_code(raw_code)
                if valid:
                    st.session_state.promo_val = val
                    st.success(f"Applied! ${val} off")
                    st.rerun()
                else: st.error(val)

    discount = st.session_state.get("promo_val", 0.0)
    is_cert = st.checkbox("Add Certified Mail Tracking (+$12.00)")
    extra = 12.00 if is_cert else 0.0
    
    p_std = max(0.0, 2.99 + extra - discount)
    p_vin = max(0.0, 5.99 + extra - discount)
    p_civ = max(0.0, 6.99 + extra - discount)

    c1, c2, c3 = st.columns(3)
    def html_card(title, qty_text, price, desc):
        return f"""
        <div class="price-card">
            <div class="price-header">{title}</div>
            <div class="price-sub">{qty_text}</div>
            <div class="price-tag">${price:.2f}</div>
            <div class="price-desc">{desc}</div>
        </div>
        """
    with c1: st.markdown(html_card("Standard", "ONE LETTER", p_std, "Premium paper. #10 Envelope."), unsafe_allow_html=True)
    with c2: st.markdown(html_card("Vintage", "ONE LETTER", p_vin, "Heavy cream paper. Wax seal."), unsafe_allow_html=True)
    with c3: st.markdown(html_card("Civic", "3 LETTERS", p_civ, "Write to Congress."), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True) 
    b1, b2, b3 = st.columns(3)
    
    with b1: 
        if st.button("Buy Standard", key="btn_std", use_container_width=True):
            cb_buy_tier("Standard", 2.99, u_email, is_cert)
    with b2: 
        if st.button("Buy Vintage", key="btn_vint", use_container_width=True):
            cb_buy_tier("Vintage", 5.99, u_email, is_cert)
    with b3: 
        if st.button("Buy Civic", key="btn_civic", use_container_width=True):
            cb_buy_tier("Civic", 6.99, u_email, is_cert)
            
    if "pending_stripe_url" in st.session_state:
        st.link_button("👉 Click Here to Complete Payment", st.session_state.pending_stripe_url, type="primary", use_container_width=True)


def render_campaign_uploader():
    st.markdown("### 📁 Upload Recipient List (CSV)")
    st.info("📢 **Campaign Mode:** Upload a CSV to send letters to hundreds of people.")
    st.markdown("**Format Required:** `name, street, city, state, zip`")
    uploaded_file = st.file_uploader("Upload CSV", type=["csv"])
    if uploaded_file:
        contacts = bulk_engine.parse_csv(uploaded_file)
        if not contacts:
            st.error("❌ Could not parse CSV. Please check the format.")
            return
        st.success(f"✅ Loaded {len(contacts)} recipients.")
        st.dataframe(contacts[:5])
        total = pricing_engine.calculate_total("Campaign", qty=len(contacts))
        st.metric("Estimated Total", f"${total}")
        if st.button("Proceed with Campaign"):
            st.info("Campaign mode requires custom checkout logic. (Placeholder)")

def render_workspace_page():
    paid_tier = st.session_state.get("paid_tier")
    if not paid_tier:
        st.error("⛔ Access Denied: Payment required.")
        if st.button("Back to Store"): st.session_state.app_mode = "store"; st.rerun()
        return

    _ensure_profile_loaded()
    col_slide, col_gap = st.columns([1, 2])
    with col_slide: text_size = st.slider("Text Size", 12, 24, 16)
    inject_custom_css(text_size)

    st.markdown(f"## 📝 Writing: {paid_tier}")
    st.caption("✅ Payment Confirmed. Write your letter below.")

    with st.expander("📍 Step 1: Addressing", expanded=True):
        if st.session_state.get("authenticated") and paid_tier != "Civic":
            addr_opts = load_address_book()
            if addr_opts:
                sel = st.selectbox("📂 Load Contact", ["Select..."] + list(addr_opts.keys()))
                if sel != "Select..." and sel != st.session_state.get("last_load"):
                    d = addr_opts[sel]
                    st.session_state.to_name = d.get('name', '')
                    st.session_state.to_street = d.get('street', '') or d.get('address_line1', '')
                    st.session_state.to_city = d.get('city', '')
                    st.session_state.to_state = d.get('state', '')
                    st.session_state.to_zip = d.get('zip_code', '') 
                    st.session_state.last_load = sel
                    st.rerun()

        c_to, c_from = st.columns(2)
        with c_to:
            st.markdown("**To (Recipient)**")
            if paid_tier == "Civic" and civic_engine:
                st.info("We will find your reps automatically.")
                if st.button("Find Reps"):
                    # Civic Logic Placeholder - restored from previous
                    pass
            else:
                st.text_input("Name", key="to_name")
                st.text_input("Street", key="to_street")
                st.text_input("City", key="to_city")
                c_s, c_z = st.columns(2)
                c_s.text_input("State", key="to_state")
                c_z.text_input("Zip", key="to_zip")

        with c_from:
            st.markdown("**From (You)**")
            st.text_input("Name", key="from_name")
            st.text_input("Street", key="from_street")
            st.text_input("City", key="from_city")
            c_fs, c_fz = st.columns(2)
            c_fs.text_input("State", key="from_state")
            c_fz.text_input("Zip", key="from_zip")

    st.divider()

    st.markdown("## ✍️ Step 2: Write")
    
    tab_type, tab_rec = st.tabs(["⌨️ TYPE", "🎙️ SPEAK"])
    
    with tab_type:
        current_text = st.session_state.get("letter_body", "")
        new_text = st.text_area("Letter Body", value=current_text, height=400, label_visibility="collapsed")
        
        # Auto-save Logic
        if new_text != current_text:
            st.session_state.letter_body = new_text
            if time.time() - st.session_state.get("last_autosave", 0) > 3:
                d_id = st.session_state.get("current_draft_id")
                if d_id and database:
                    database.update_draft_data(d_id, content=new_text, status="Paid/Writing")
                    st.session_state.last_autosave = time.time()
                    st.caption("💾 Auto-saved")

        c_p, c_u = st.columns([1,1])
        with c_p:
            if st.button("✨ AI Polish"):
                if new_text and ai_engine:
                     with st.spinner("Polishing..."):
                         polished = ai_engine.refine_text(new_text)
                         st.session_state.letter_body = polished
                         st.rerun()
        with c_u:
            if st.button("💾 Save Draft"):
                d_id = st.session_state.get("current_draft_id")
                if d_id and database:
                    database.update_draft_data(d_id, content=new_text, status="Paid/Writing")
                    st.toast("Saved!")

    with tab_rec:
        audio_val = st.audio_input("Record", label_visibility="collapsed")
        if audio_val:
            audio_bytes = audio_val.getvalue()
            h = hashlib.md5(audio_bytes).hexdigest()
            if h != st.session_state.get("last_processed_audio_hash"):
                if ai_engine:
                    st.info("⏳ Processing...")
                    tmp = f"/tmp/{int(time.time())}.wav"
                    with open(tmp, "wb") as f: f.write(audio_bytes)
                    txt = ai_engine.transcribe_audio(tmp)
                    if txt:
                        st.session_state.letter_body = (st.session_state.letter_body + "\n\n" + txt).strip()
                        st.session_state.last_processed_audio_hash = h
                        st.rerun()

    st.divider()

    if st.button(f"🚀 Send {paid_tier} Letter", type="primary", use_container_width=True):
        if not new_text.strip():
            st.error("Letter body is empty.")
            return
        if paid_tier != "Civic" and not st.session_state.get("to_street"):
            st.error("Recipient address missing.")
            return

        to_addr = {
            "name": st.session_state.get("to_name"),
            "address_line1": st.session_state.get("to_street"),
            "city": st.session_state.get("to_city"),
            "state": st.session_state.get("to_state"),
            "zip_code": st.session_state.get("to_zip")
        }
        from_addr = {
            "name": st.session_state.get("from_name"),
            "address_line1": st.session_state.get("from_street"),
            "city": st.session_state.get("from_city"),
            "state": st.session_state.get("from_state"),
            "zip_code": st.session_state.get("from_zip")
        }
        
        if paid_tier != "Civic": _save_new_contact(to_addr)

        pdf_bytes = b""
        if letter_format:
            pdf_bytes = letter_format.create_pdf(new_text, to_addr, from_addr, tier=paid_tier)

        tracking_ref = "PENDING"
        u_email = st.session_state.get("user_email")
        
        with st.spinner("Processing..."):
            # VINTAGE
            if paid_tier == "Vintage":
                tracking_ref = f"VINTAGE-{int(time.time())}"
                d_id = st.session_state.get("current_draft_id")
                if d_id and database:
                    database.update_draft_data(d_id, status="Pending Manual Fulfillment", content=new_text, tracking_number=tracking_ref)
                _send_alert_email("support@verbapost.com", f"ACTION REQUIRED: Vintage Order {tracking_ref}", f"<p>User: {u_email}</p>")
                _send_alert_email(u_email, "Receipt: Your Vintage Letter", f"<h3>Order Received</h3><p>Ref: {tracking_ref}</p>")

            # STANDARD
            else:
                if mailer:
                    tracking_ref = mailer.send_letter(pdf_bytes, to_addr, from_addr, description=f"VerbaPost {paid_tier}", tier=paid_tier)
                if tracking_ref:
                    d_id = st.session_state.get("current_draft_id")
                    if d_id and database:
                        database.update_draft_data(d_id, status="Sent", content=new_text, tracking_number=tracking_ref)
                    _send_alert_email(u_email, f"Receipt: Order {tracking_ref}", f"<h3>Sent!</h3><p>Tracking: {tracking_ref}</p>")
            
            if tracking_ref:
                # [CRITICAL FIX: BURN THE TOKEN & REDIRECT]
                st.session_state.receipt_data = {
                    "ref": tracking_ref,
                    "pdf": pdf_bytes
                }
                del st.session_state.paid_tier # User can NO LONGER access workspace
                st.session_state.app_mode = "receipt"
                st.rerun()
            else:
                st.error("❌ Fulfillment Error.")

def render_receipt_page():
    data = st.session_state.get("receipt_data", {})
    if not data:
        st.error("No receipt found.")
        if st.button("Go Home"): st.session_state.app_mode = "store"; st.rerun()
        return

    st.balloons()
    st.markdown(f"""
        <div class="success-box">
            <div class="success-title">✅ Letter Sent!</div>
            <p>Your letter has been dispatched securely.</p>
            <p>Tracking Reference: <span class="tracking-code">{data.get('ref')}</span></p>
        </div>
    """, unsafe_allow_html=True)
    
    if data.get('pdf'):
        st.download_button("⬇️ Download Final Copy", data['pdf'], "letter_copy.pdf", "application/pdf", use_container_width=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    if st.button("✉️ Send Another Letter (Return to Store)", type="primary", use_container_width=True):
        st.session_state.app_mode = "store"
        st.rerun()

def render_application():
    if "app_mode" not in st.session_state: st.session_state.app_mode = "splash"
    mode = st.session_state.app_mode
    if mode == "splash":
        if ui_splash: ui_splash.render_splash_page()
    elif mode == "login":
        if ui_login: ui_login.render_login_page()
    elif mode == "store":
        render_store_page()
    elif mode == "workspace":
        render_workspace_page()
    elif mode == "receipt":
        render_receipt_page()
    elif mode == "heirloom": 
        if ui_heirloom: ui_heirloom.render_dashboard()
    elif mode == "admin":
        if ui_admin: ui_admin.render_admin_page()
    elif mode == "legacy":
        if ui_legacy: ui_legacy.render_legacy_page()
    else:
        st.session_state.app_mode = "splash"
        st.rerun()

def render_main(): render_application()

if __name__ == "__main__":
    render_main()