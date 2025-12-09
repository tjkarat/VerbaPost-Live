import streamlit as st
from streamlit_drawable_canvas import st_canvas
import os
import tempfile
import base64
import time
import traceback
from PIL import Image

# --- 1. CORE MODULE LOADER (Prevents Import Crashes) ---
try: import ui_login
except ImportError: ui_login = None
try: import ui_splash
except ImportError: ui_splash = None
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

# --- 2. LOCAL DATA MODELS ---
try:
    from address_standard import StandardAddress
except ImportError:
    from dataclasses import dataclass
    @dataclass
    class StandardAddress:
        name: str; street: str; address_line2: str = ""; city: str = ""; state: str = ""; zip_code: str = ""; country: str = "US"
        def to_pdf_string(self): return f"{self.name}\n{self.street}"
        @classmethod
        def from_dict(cls, d): return cls(name=d.get('name',''), street=d.get('street',''))

# --- 3. CONFIGURATION & CONSTANTS ---
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

TIER_PRICING = {
    "Standard": 2.99,
    "Heirloom": 5.99,
    "Civic": 6.99,
    "Santa": 9.99,
    "Campaign": 2.99 # Base price
}

# --- 4. GLOBAL SIDEBAR (The Missing Piece) ---
def render_sidebar():
    """Persistent sidebar with User Info, Admin Link, and Legal."""
    with st.sidebar:
        st.header("VerbaPost 📮")
        st.markdown("---")
        
        # A. User Status Section
        user_email = st.session_state.get("user_email")
        if user_email:
            st.success(f"👤 **Logged in as:**\n{user_email}")
            
            # ADMIN CHECK
            admin_target = "tjkarat@gmail.com" # Fallback
            if secrets_manager:
                sec_admin = secrets_manager.get_secret("admin.email") or secrets_manager.get_secret("ADMIN_EMAIL")
                if sec_admin: admin_target = sec_admin
            
            # Show Admin Button if Email Matches
            if str(user_email).lower().strip() == str(admin_target).lower().strip():
                if st.button("🔐 Admin Console", type="primary", use_container_width=True):
                    st.session_state.app_mode = "admin"
                    st.rerun()

            if st.button("🚪 Log Out", type="secondary", use_container_width=True):
                # Clear session but keep navigation state safe
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.session_state.app_mode = "splash"
                st.rerun()
        else:
            st.info("👤 **Guest User**")
            if st.button("🔑 Log In / Sign Up", type="primary", use_container_width=True):
                st.session_state.app_mode = "login"
                st.rerun()

        st.markdown("---")
        
        # B. Navigation (Context Aware)
        mode = st.session_state.get("app_mode", "splash")
        if mode in ["workspace", "review"] and user_email:
             if st.button("🛒 Store (New Letter)", icon="🛍️", use_container_width=True):
                 st.session_state.app_mode = "store"
                 st.rerun()

        # C. Footer Links
        st.markdown("### Support")
        if st.button("⚖️ Legal & Privacy", use_container_width=True):
            st.session_state.app_mode = "legal"
            st.rerun()
            
        st.caption(f"v2.8 Production\nSession: {st.session_state.get('current_draft_id', 'New')}")

# --- 5. SESSION MANAGERS ---
def reset_app():
    recovered = st.query_params.get("draft_id")
    # Preserve user_email if it exists
    u_email = st.session_state.get("user_email")
    
    keys_to_clear = [
        "audio_path", "transcribed_text", "payment_complete", "sig_data", "to_addr", 
        "civic_targets", "bulk_targets", "bulk_paid_qty", "is_intl", "is_certified", 
        "letter_sent_success", "locked_tier", "w_to_name", "w_to_street", "w_to_street2", 
        "w_to_city", "w_to_state", "w_to_zip", "w_to_country", "addr_book_idx", 
        "last_tracking_num", "campaign_errors", "current_stripe_id", "current_draft_id"
    ]
    for k in keys_to_clear:
        if k in st.session_state: del st.session_state[k]
    
    st.session_state.to_addr = {}
    if u_email: st.session_state.user_email = u_email

    if "draft_id" in st.query_params and not recovered:
        st.query_params.clear()

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
        st.warning("⚠️ Session Expired. Please log in again.")
        st.session_state.app_mode = "login"
        st.rerun()
        return False
    return True

# --- 6. PAGE: STORE (Rich UI) ---
def render_store_page():
    # Handle Stripe Return
    sess_id = st.query_params.get("session_id")
    if sess_id and not st.session_state.get("payment_complete"):
        with st.spinner("Verifying Payment with Stripe..."):
            if payment_engine:
                success, details = payment_engine.verify_session(sess_id)
                if success:
                    st.session_state.payment_complete = True
                    # Auto-recover email from Stripe if missing
                    if not st.session_state.get("user_email"):
                        try:
                            rec = details.get("customer_details", {}).get("email")
                            if rec: st.session_state.user_email = rec
                        except: pass
                    
                    if audit_engine: 
                        audit_engine.log_event(st.session_state.get("user_email"), "PAYMENT_SUCCESS", sess_id, {"amount": details.get('amount_total')})
                    
                    st.toast("✅ Payment Confirmed!", icon="🎉")
                    time.sleep(1)
                    st.session_state.app_mode = "workspace"
                    st.rerun()
                else: 
                    st.error("❌ Payment Verification Failed. Please contact support.")

    if not check_session(): return
    
    # Hero Section
    st.markdown("""
    <div style="background: linear-gradient(135deg, #43cea2 0%, #185a9d 100%); padding: 30px; border-radius: 15px; color: white; text-align: center; margin-bottom: 20px;">
        <h1 style="color: white; margin:0;">Select Your Service</h1>
        <p style="opacity: 0.9;">Choose a package to begin drafting your letter.</p>
    </div>
    """, unsafe_allow_html=True)

    col_left, col_right = st.columns([1.8, 1])

    with col_left:
        st.subheader("📦 Packages")
        
        # Custom Radio Component using Columns
        tier = st.radio(
            "Select Tier:", 
            ["Standard", "Heirloom", "Civic", "Santa", "Campaign"],
            format_func=lambda x: f"{x} - ${TIER_PRICING[x]}",
            label_visibility="collapsed"
        )
        
        st.info(f"**Selected: {tier}**")
        
        # Dynamic Description
        if tier == "Standard":
            st.markdown("⚡ **Best for everyday mail.** Printed on standard 8.5x11 paper. Includes envelope and First Class postage.")
        elif tier == "Heirloom":
            st.markdown("🏺 **Best for personal notes.** Printed on archival ivory stock with a 'Handwritten' font style.")
        elif tier == "Civic":
            st.markdown("🏛️ **Best for activism.** We automatically find your representatives based on your address.")
        elif tier == "Santa":
            st.markdown("🎅 **For the Kids.** A magical letter from the North Pole, signed by Santa, on festive paper.")
        elif tier == "Campaign":
            st.markdown("📢 **Bulk Mail.** Upload a CSV of addresses. Ideal for newsletters or announcements.")

        # Options
        qty = 1
        price = TIER_PRICING[tier]
        is_intl = False
        is_certified = False

        if tier == "Campaign":
            qty = st.number_input("Recipient Count", min_value=10, max_value=5000, value=50, step=10)
            price = 2.99 + ((qty - 1) * 1.99) # Bulk pricing logic
            st.caption(f"Bulk Rate: $1.99/ea after first letter.")
        
        if tier in ["Standard", "Heirloom"]:
            c_opt1, c_opt2 = st.columns(2)
            if c_opt1.checkbox("🌍 International (+$2.00)"):
                price += 2.00
                is_intl = True
            if c_opt2.checkbox("📜 Certified Mail (+$12.00)"):
                price += 12.00
                is_certified = True

        st.session_state.locked_tier = tier
        st.session_state.is_intl = is_intl
        st.session_state.is_certified = is_certified
        st.session_state.bulk_paid_qty = qty

    with col_right:
        with st.container(border=True):
            st.subheader("💳 Checkout")
            st.divider()
            st.markdown(f"**Item:** {tier} Letter")
            if qty > 1: st.markdown(f"**Quantity:** {qty}")
            if is_intl: st.markdown(f"**Option:** International Mail")
            if is_certified: st.markdown(f"**Option:** Certified Mail")
            
            st.divider()
            
            # Promo Code
            code = st.text_input("Promo Code", placeholder="SAVE20")
            discounted = False
            if promo_engine and code:
                if promo_engine.validate_code(code):
                    discounted = True
                    st.success("✅ Code Applied!")
            
            final_price = 0.00 if discounted else price
            
            st.markdown(f"<h2 style='text-align:center;'>${final_price:.2f}</h2>", unsafe_allow_html=True)
            
            if discounted:
                if st.button("🚀 Start (Free)", type="primary", use_container_width=True):
                    # Free Logic
                    if promo_engine: promo_engine.log_usage(code, st.session_state.user_email)
                    _init_draft(tier, "0.00")
                    st.session_state.payment_complete = True
                    st.session_state.app_mode = "workspace"
                    st.rerun()
            else:
                if st.button(f"Pay & Start", type="primary", use_container_width=True):
                    _init_draft(tier, final_price)
                    _launch_stripe(tier, final_price, is_intl, is_certified, qty)

def _init_draft(tier, price):
    """Creates initial DB record."""
    if database:
        d_id = st.session_state.get("current_draft_id")
        if d_id:
            database.update_draft_data(d_id, status="Draft", tier=tier, price=price)
        else:
            d_id = database.save_draft(st.session_state.user_email, "", tier, price)
            st.session_state.current_draft_id = d_id
            st.query_params["draft_id"] = str(d_id)

def _launch_stripe(tier, price, is_intl, is_certified, qty):
    """Constructs Stripe session."""
    d_id = st.session_state.current_draft_id
    link = f"{YOUR_APP_URL}?tier={tier}&session_id={{CHECKOUT_SESSION_ID}}&draft_id={d_id}"
    if is_intl: link += "&intl=1"
    if is_certified: link += "&certified=1"
    if tier == "Campaign": link += f"&qty={qty}"
    
    if payment_engine:
        # Legacy Call (4 args)
        url, sess_id = payment_engine.create_checkout_session(f"VerbaPost {tier}", int(price*100), link, YOUR_APP_URL)
        if url: 
            st.markdown(f'<a href="{url}" target="_self"><button style="width:100%;padding:12px;background:#635bff;color:white;border:none;border-radius:8px;font-weight:bold;cursor:pointer;">👉 Proceed to Stripe</button></a>', unsafe_allow_html=True)
        else: 
            st.error("⚠️ Stripe Connection Failed. Check Secrets.")

# --- 7. PAGE: WORKSPACE (Composing) ---
def render_workspace_page():
    if not check_session(): return
    tier = st.session_state.get("locked_tier", "Standard")
    
    st.markdown(f"""
    <div style="background: #f8f9fa; padding: 20px; border-radius: 10px; border-left: 5px solid #2a5298; margin-bottom: 20px;">
        <h2 style="color: #2a5298; margin:0;">✍️ Compose: {tier}</h2>
        <p>Dictate your letter or upload audio. We'll handle the formatting.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 1. Addresses
    with st.expander("📍 Address Details", expanded=True):
        _render_address_form(tier)

    # 2. Content Creation
    st.markdown("### 🎙️ Letter Content")
    
    tab_mic, tab_upload, tab_text = st.tabs(["🎤 Dictate", "📂 Upload Audio", "⌨️ Type/Paste"])
    
    with tab_mic:
        if ai_engine:
            audio = st.audio_input("Record Voice Note")
            if audio:
                with st.spinner("🤖 Transcribing..."):
                    txt = ai_engine.transcribe_audio(audio)
                    st.session_state.transcribed_text = txt
                    st.session_state.app_mode = "review"
                    st.rerun()
        else: st.warning("AI Engine unavailable.")

    with tab_upload:
        up_file = st.file_uploader("Upload MP3/WAV", type=['mp3', 'wav'])
        if up_file and st.button("Transcribe File"):
            if ai_engine:
                with st.spinner("🤖 Processing File..."):
                    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{up_file.name.split('.')[-1]}") as tmp:
                        tmp.write(up_file.getvalue())
                        txt = ai_engine.transcribe_audio(tmp.name)
                        st.session_state.transcribed_text = txt
                        st.session_state.app_mode = "review"
                        st.rerun()
    
    with tab_text:
        val = st.text_area("Direct Input", height=200, placeholder="Type your letter here if you prefer not to use voice.")
        if st.button("Use Typed Text"):
            st.session_state.transcribed_text = val
            st.session_state.app_mode = "review"
            st.rerun()

    # 3. Signature
    if tier != "Santa":
        st.markdown("### ✍️ Signature")
        canvas = st_canvas(stroke_width=2, stroke_color="#000000", background_color="#ffffff", height=150, width=400, key="sig_canvas")
        if canvas.image_data is not None:
            st.session_state.sig_data = canvas.image_data

def _render_address_form(tier):
    u_email = st.session_state.get("user_email")
    
    # Load User Profile Defaults
    if database:
        p = database.get_user_profile(u_email)
        if p and "w_from_name" not in st.session_state:
            st.session_state.w_from_name = p.full_name
            st.session_state.w_from_street = p.address_line1
            st.session_state.w_from_city = p.address_city
            st.session_state.w_from_state = p.address_state
            st.session_state.w_from_zip = p.address_zip

    c_from, c_to = st.columns(2)
    
    # SENDER COLUMN
    with c_from:
        st.markdown("**From (Sender)**")
        if tier == "Santa":
            st.info("🎅 Sender: Santa Claus, North Pole")
        else:
            st.text_input("Name", key="w_from_name")
            st.text_input("Street", key="w_from_street")
            c1, c2 = st.columns(2)
            c1.text_input("City", key="w_from_city")
            c2.text_input("State", key="w_from_state")
            st.text_input("Zip", key="w_from_zip")
            st.session_state.w_from_country = "US"

    # RECIPIENT COLUMN
    with c_to:
        st.markdown("**To (Recipient)**")
        if tier == "Civic":
            st.info("🏛️ Recipient: Auto-Detected Reps")
            if civic_engine:
                 zip_look = st.session_state.get("w_from_zip")
                 if zip_look and st.button("Find Reps"):
                     st.session_state.civic_targets = civic_engine.get_reps(zip_look)
                     st.success("Reps Found!")
        elif tier == "Campaign":
            st.info("📢 Recipient: Bulk CSV Upload")
            if bulk_engine:
                f = st.file_uploader("Upload CSV", type="csv")
                if f:
                    data, err = bulk_engine.parse_csv(f)
                    if not err: st.session_state.bulk_targets = data; st.success(f"{len(data)} Loaded")
        else:
            # Address Book
            if database:
                cons = database.get_contacts(u_email)
                if cons:
                    opts = ["-- Quick Fill --"] + [c.name for c in cons]
                    sel = st.selectbox("Saved Contacts", opts)
                    if sel != "-- Quick Fill --":
                        c = next(x for x in cons if x.name == sel)
                        st.session_state.w_to_name = c.name
                        st.session_state.w_to_street = c.street
                        st.session_state.w_to_city = c.city
                        st.session_state.w_to_state = c.state
                        st.session_state.w_to_zip = c.zip_code

            st.text_input("Name", key="w_to_name")
            st.text_input("Street", key="w_to_street")
            c1, c2 = st.columns(2)
            c1.text_input("City", key="w_to_city")
            c2.text_input("State", key="w_to_state")
            st.text_input("Zip", key="w_to_zip")
            st.session_state.w_to_country = "US"

    # Save logic
    _scrape_addresses(tier)

def _scrape_addresses(tier):
    u_email = st.session_state.user_email
    # Logic to populate session_state.from_addr / to_addr
    # (Same as previous iterations but hidden in function for clean code)
    if tier == "Santa":
        st.session_state.from_addr = {"name": "Santa", "street": "North Pole", "city": "NP", "state": "NP", "zip": "88888", "country": "NP", "email": u_email}
    else:
        st.session_state.from_addr = {
            "name": st.session_state.get("w_from_name"), "street": st.session_state.get("w_from_street"),
            "city": st.session_state.get("w_from_city"), "state": st.session_state.get("w_from_state"),
            "zip": st.session_state.get("w_from_zip"), "country": "US", "email": u_email
        }
    
    if tier not in ["Civic", "Campaign"]:
        st.session_state.to_addr = {
            "name": st.session_state.get("w_to_name"), "street": st.session_state.get("w_to_street"),
            "city": st.session_state.get("w_to_city"), "state": st.session_state.get("w_to_state"),
            "zip": st.session_state.get("w_to_zip"), "country": "US"
        }

# --- 8. PAGE: REVIEW ---
def render_review_page():
    if not check_session(): return
    st.markdown("## 🔎 Review & Finalize")
    
    col_tools, col_preview = st.columns([1, 2])
    
    txt = st.session_state.get("transcribed_text", "")
    
    with col_tools:
        st.markdown("### AI Editor")
        if st.button("✨ Fix Grammar"): 
            st.session_state.transcribed_text = ai_engine.refine_text(txt, "Grammar") if ai_engine else txt
            st.rerun()
        if st.button("👔 Make Professional"):
            st.session_state.transcribed_text = ai_engine.refine_text(txt, "Professional") if ai_engine else txt
            st.rerun()
        if st.button("✂️ Make Concise"):
            st.session_state.transcribed_text = ai_engine.refine_text(txt, "Concise") if ai_engine else txt
            st.rerun()
        
        st.markdown("---")
        if st.button("⬅️ Edit Details"):
            st.session_state.app_mode = "workspace"
            st.rerun()

    with col_preview:
        edited_txt = st.text_area("Letter Body", value=txt, height=400)
        st.session_state.transcribed_text = edited_txt
        
        if st.button("👁️ Generate PDF Preview", type="secondary", use_container_width=True):
            _generate_preview()
            
        if st.button("🚀 Send Letter Now", type="primary", use_container_width=True):
            _send_letter()

def _generate_preview():
    tier = st.session_state.get("locked_tier")
    if letter_format:
        to_obj = StandardAddress.from_dict(st.session_state.get("to_addr", {}))
        from_obj = StandardAddress.from_dict(st.session_state.get("from_addr", {}))
        
        # Handle Signature
        sig_path = None
        if st.session_state.get("sig_data") is not None:
            img = Image.fromarray(st.session_state.sig_data.astype('uint8'), 'RGBA')
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp: 
                img.save(tmp.name); sig_path = tmp.name

        pdf = letter_format.create_pdf(
            st.session_state.transcribed_text, 
            to_obj.to_pdf_string(), 
            from_obj.to_pdf_string(), 
            is_heirloom=(tier=="Heirloom"), 
            is_santa=(tier=="Santa"), 
            signature_path=sig_path
        )
        
        if pdf:
            b64 = base64.b64encode(pdf).decode()
            st.markdown(f'<embed src="data:application/pdf;base64,{b64}" width="100%" height="600" type="application/pdf">', unsafe_allow_html=True)

def _send_letter():
    tier = st.session_state.get("locked_tier")
    
    # 1. Determine Targets
    targets = []
    if tier == "Campaign": targets = st.session_state.get("bulk_targets", [])
    elif tier == "Civic": 
        # Convert Rep dicts to Standard Address dicts
        for r in st.session_state.get("civic_targets", []): 
            targets.append(r['address_obj']) # Assuming civic_engine returns this structure
    else: targets.append(st.session_state.to_addr)
    
    if not targets or not targets[0]:
        st.error("❌ No Recipient Address Found!")
        return

    # 2. Loop & Send
    with st.status("📮 Processing Mail...", expanded=True) as status:
        success_count = 0
        for tgt in targets:
            status.write(f"Preparing letter for {tgt.get('name')}...")
            
            # Generate PDF
            to_obj = StandardAddress.from_dict(tgt)
            from_obj = StandardAddress.from_dict(st.session_state.from_addr)
            
            sig_path = None # (Signature logic same as preview)
            if st.session_state.get("sig_data") is not None:
                img = Image.fromarray(st.session_state.sig_data.astype('uint8'), 'RGBA')
                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp: img.save(tmp.name); sig_path = tmp.name

            pdf_bytes = letter_format.create_pdf(
                st.session_state.transcribed_text, 
                to_obj.to_pdf_string(), 
                from_obj.to_pdf_string(), 
                (tier=="Heirloom"), (tier=="Santa"), sig_path
            )
            
            # Send to PostGrid
            if mailer:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tpdf: 
                    tpdf.write(pdf_bytes); tpdf.close()
                    
                    ok, res = mailer.send_letter(tpdf.name, tgt, st.session_state.from_addr, st.session_state.get("is_certified", False))
                    if ok: success_count += 1
                    else: st.write(f"❌ Failed: {res}")
                    
                    os.remove(tpdf.name)
            
            # DB Log
            if database:
                database.save_draft(st.session_state.user_email, st.session_state.transcribed_text, tier, "PAID", tgt, st.session_state.from_addr, "Completed" if ok else "Failed")

        if success_count > 0:
            status.update(label="✅ Mail Sent!", state="complete", expanded=False)
            st.balloons()
            st.success(f"Successfully sent {success_count} letters!")
            st.session_state.letter_sent_success = True
            if st.button("Draft Another"): reset_app(); st.rerun()
        else:
            status.update(label="❌ Sending Failed", state="error")

# --- 9. MAIN ROUTER ---
def show_main_app():
    if "app_mode" not in st.session_state: reset_app()
    mode = st.session_state.app_mode
    
    # RENDER SIDEBAR (ON EVERY PAGE)
    render_sidebar()
    
    if mode == "splash":
        if ui_splash: ui_splash.show_splash()
        else: st.error("Splash Missing")
            
    elif mode == "login":
        if ui_login: ui_login.show_login(handle_login, handle_signup)
        else: st.error("Login Missing")
        
    elif mode == "store": render_store_page()
    elif mode == "workspace": render_workspace_page()
    elif mode == "review": render_review_page()
    
    elif mode == "admin":
        if ui_admin: ui_admin.show_admin()
        else: st.error("Admin Missing")
        
    elif mode == "legal": 
        if ui_legal: ui_legal.show_legal()
        else: st.info("Legal Page Under Maintenance")
        
    else: render_store_page()