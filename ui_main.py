import streamlit as st
import time
import os
import hashlib
from datetime import datetime

# --- ENGINE IMPORTS ---
import ai_engine
import payment_engine
import mailer
import database
import letter_format
import address_standard
import pricing_engine
import bulk_engine
import audit_engine

# --- UI MODULE IMPORTS ---
try: import ui_splash
except ImportError: ui_splash = None
try: import ui_login
except ImportError: ui_login = None
try: import ui_admin
except ImportError: ui_admin = None
try: import ui_legal
except ImportError: ui_legal = None
try: import ui_legacy
except ImportError: ui_legacy = None
try: import promo_engine
except ImportError: promo_engine = None
try: import civic_engine
except ImportError: civic_engine = None

# --- HELPER: SAFE PROFILE GETTER ---
def get_profile_field(profile, field, default=""):
    """Safely retrieves fields from profile whether it's a dict, object, or None."""
    if not profile: return default
    if isinstance(profile, dict): return profile.get(field, default)
    return getattr(profile, field, default)

# --- ACCESSIBILITY CSS INJECTOR ---
def inject_accessibility_css(text_size=16):
    """Injects CSS to make tabs larger, high-contrast, and button-like."""
    st.markdown(f"""
        <style>
        .stTextArea textarea, .stTextInput input, p, li, .stMarkdown {{
            font-size: {text_size}px !important;
            line-height: 1.6 !important;
        }}
        .stTabs [data-baseweb="tab"] p {{
            font-size: 1.5rem !important;
            font-weight: 700 !important;
        }}
        .stTabs [data-baseweb="tab"] {{
            height: 70px;
            white-space: pre-wrap;
            background-color: #F0F2F6;
            border-radius: 10px 10px 0px 0px;
            gap: 2px;
            padding-top: 10px;
            padding-bottom: 10px;
            border: 3px solid #9CA3AF;
            margin-right: 5px;
            color: #374151;
        }}
        .stTabs [aria-selected="true"] {{
            background-color: #FF4B4B !important;
            border: 3px solid #FF4B4B !important;
            color: white !important;
        }}
        .stTabs [aria-selected="true"] p {{
            color: white !important;
        }}
        .instruction-box {{
            background-color: #FEF3C7;
            border-left: 10px solid #F59E0B;
            padding: 20px;
            margin-bottom: 25px;
            font-size: 20px;
            font-weight: 500;
            color: #000000;
        }}
        </style>
    """, unsafe_allow_html=True)

# --- HELPER FUNCTIONS ---
def reset_app_state():
    """Clears session state for a fresh start."""
    keys_to_keep = ["authenticated", "user_email", "user_name", "user_role", "user_profile"]
    for key in list(st.session_state.keys()):
        if key not in keys_to_keep:
            del st.session_state[key]
    st.rerun()

def load_address_book():
    """Fetches contacts from DB if logged in."""
    if not database or not st.session_state.get("authenticated"):
        return {}
    try:
        user_email = st.session_state.get("user_email")
        contacts = database.get_contacts(user_email)
        result = {}
        for c in contacts:
            # Handle dicts vs objects safely
            name = c.get('name') if isinstance(c, dict) else getattr(c, 'name', '')
            city = c.get('city') if isinstance(c, dict) else getattr(c, 'city', 'Unknown')
            contact_data = {
                'name': name,
                'street': c.get('street') if isinstance(c, dict) else getattr(c, 'street', ''),
                'city': city,
                'state': c.get('state') if isinstance(c, dict) else getattr(c, 'state', ''),
                'zip': c.get('zip_code') if isinstance(c, dict) else getattr(c, 'zip_code', '')
            }
            result[f"{name} ({city})"] = contact_data
        return result
    except Exception as e:
        print(f"Address Book Error: {e}")
        return {}

def _handle_draft_creation(email, tier, price):
    """Ensures a draft exists in the DB before payment."""
    d_id = st.session_state.get("current_draft_id")
    success = False
    if d_id and database:
        success = database.update_draft_data(d_id, status="Draft", tier=tier, price=price)
    if (not success or not d_id) and database:
        d_id = database.save_draft(email, "", tier, price)
        st.session_state.current_draft_id = d_id
    return d_id

# --- PAGE RENDERERS ---

def render_store_page():
    """Step 1: The Store (Pricing & Tier Selection)."""
    u_email = st.session_state.get("user_email", "")
    if not u_email:
        st.warning("⚠️ Session Expired. Please log in to continue.")
        if st.button("Go to Login"):
            st.session_state.app_mode = "login"
            st.rerun()
        return

    with st.expander("❓ How VerbaPost Works (Help)", expanded=False):
        st.markdown("""
        **Simple 4-Step Process:**
        1. **Select Service:** Choose your letter tier.
        2. **Write:** Type or dictate your content.
        3. **Address:** Load or enter recipient.
        4. **Send:** We print and mail it via USPS.
        """)

    st.markdown("## 📮 Choose Your Letter Service")
    mode = st.radio("Mode", ["Single Letter", "Bulk Campaign"], horizontal=True, label_visibility="collapsed")
    
    if mode == "Bulk Campaign":
        st.info("📢 **Campaign Mode:** Upload a CSV to send letters to hundreds of people.")
        render_campaign_uploader()
        return

    col1, col2, col3, col4 = st.columns(4)
    
    def price_card(col, title, price, desc, tier_code, btn_key):
        with col:
            st.markdown(f"### {title}")
            st.markdown(f"## ${price}")
            st.caption(desc)
            if st.button(f"Select {title}", key=btn_key, use_container_width=True):
                st.session_state.locked_tier = tier_code
                st.session_state.locked_price = price
                _handle_draft_creation(u_email, tier_code, price)
                st.session_state.app_mode = "workspace"
                st.rerun()

    price_card(col1, "Standard", 2.99, "Standard #10 Envelope\nPremium Paper", "Standard", "btn_std")
    price_card(col2, "Heirloom", 5.99, "Heavy Cream Paper\nWax Seal Effect", "Heirloom", "btn_heir")
    price_card(col3, "Civic", 6.99, "Write to Congress\nAuto-lookup Officials", "Civic", "btn_civ")
    price_card(col4, "Santa", 9.99, "North Pole Postmark\nGolden Ticket", "Santa", "btn_santa")

def render_campaign_uploader():
    """Handles CSV upload for Bulk Tier (RESTORED)."""
    st.markdown("### 📁 Upload Recipient List (CSV)")
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
            with st.spinner(f"Preparing {len(contacts)} letters..."):
                time.sleep(1)
                st.session_state.locked_tier = "Campaign"
                st.session_state.bulk_targets = contacts
                st.success(f"✅ Ready!")
                time.sleep(1)
                st.session_state.app_mode = "workspace"
                st.rerun()

def render_workspace_page():
    """Step 2 & 3: Composition & Addressing."""
    col_slide, col_gap = st.columns([1, 2])
    with col_slide:
        text_size = st.slider("Text Size", 12, 24, 16, help="Adjust text size")
    inject_accessibility_css(text_size)

    current_tier = st.session_state.get('locked_tier', 'Draft')
    st.markdown(f"## 📝 Workspace: {current_tier}")

    # --- STEP 2: ADDRESSING ---
    with st.expander("📍 Step 2: Addressing", expanded=True):
        st.info("💡 **Tip:** Hit 'Save Addresses' to lock them in.")
        
        # Address Book
        if st.session_state.get("authenticated"):
            addr_opts = load_address_book()
            if addr_opts:
                col_load, col_empty = st.columns([2, 1])
                with col_load:
                    selected_contact = st.selectbox("📂 Load Saved Contact", ["Select..."] + list(addr_opts.keys()))
                    
                    # FIX: Prevent infinite rerun loop
                    if selected_contact != "Select..." and selected_contact != st.session_state.get("last_loaded_contact"):
                        data = addr_opts[selected_contact]
                        st.session_state.to_name_input = data.get('name', '')
                        st.session_state.to_street_input = data.get('street', '')
                        st.session_state.to_city_input = data.get('city', '')
                        st.session_state.to_state_input = data.get('state', '')
                        st.session_state.to_zip_input = data.get('zip', '')
                        st.session_state.last_loaded_contact = selected_contact
                        st.rerun()

        # Addressing Form
        with st.form("addressing_form"):
            col_to, col_from = st.columns(2)
            
            with col_to:
                st.markdown("### To: (Recipient)")
                name = st.text_input("Name", key="to_name_input")
                street = st.text_input("Street Address", key="to_street_input")
                city = st.text_input("City", key="to_city_input")
                col_s, col_z = st.columns(2)
                state = col_s.text_input("State", key="to_state_input")
                zip_c = col_z.text_input("Zip", key="to_zip_input")

            with col_from:
                st.markdown("### From: (Return Address)")
                profile = st.session_state.get("user_profile", {})
                
                # Logic for Tier-Specific Defaults
                d_name, d_str, d_city, d_state, d_zip = "", "", "", "", ""
                if current_tier == "Santa":
                    d_name, d_str, d_city, d_state, d_zip = "Santa Claus", "123 Elf Lane", "North Pole", "AK", "99705"
                else:
                    d_name = get_profile_field(profile, "full_name")
                    d_str = get_profile_field(profile, "address_line1")
                    d_city = get_profile_field(profile, "address_city")
                    d_state = get_profile_field(profile, "address_state")
                    d_zip = get_profile_field(profile, "address_zip")

                f_name = st.text_input("Your Name", value=d_name, key="from_name")
                f_sig = st.text_input("Signature (Sign-off)", value=d_name, placeholder="e.g. Love, Mom", key="from_sig")
                f_street = st.text_input("Your Street", value=d_str, key="from_street")
                f_city = st.text_input("Your City", value=d_city, key="from_city")
                col_fs, col_fz = st.columns(2)
                f_state = col_fs.text_input("Your State", value=d_state, key="from_state")
                f_zip = col_fz.text_input("Your Zip", value=d_zip, key="from_zip")
            
            if st.form_submit_button("💾 Save Addresses"):
                st.session_state.addr_to = {"name": name, "street": street, "city": city, "state": state, "zip": zip_c}
                st.session_state.addr_from = {"name": f_name, "street": f_street, "city": f_city, "state": f_state, "zip": f_zip}
                st.session_state.signature_text = f_sig
                
                d_id = st.session_state.get("current_draft_id")
                if d_id and database:
                    database.update_draft_data(d_id, to_addr=st.session_state.addr_to, from_addr=st.session_state.addr_from)
                
                st.session_state.addresses_saved_at = time.time()
                st.success("✅ Addresses Saved!")
        
        if st.session_state.get("addresses_saved_at") and time.time() - st.session_state.addresses_saved_at < 10:
            st.success("✅ Your addresses are saved and ready!")

    st.divider()

    # --- STEP 3: COMPOSE ---
    st.markdown("## ✍️ Step 3: Write Your Letter")

    st.markdown(
        """
        <div class="instruction-box">
            <p style="margin: 0 0 10px 0; font-weight: bold;">📱 INSTRUCTIONS</p>
            <p style="margin: 5px 0;">1️⃣ Click <b>RECORD VOICE</b> to speak<br>2️⃣ Click <b>TYPE MANUALLY</b> to type</p>
        </div>
        """, 
        unsafe_allow_html=True
    )

    tab_type, tab_record = st.tabs(["⌨️ TYPE MANUALLY", "🎙️ RECORD VOICE"])

    with tab_type:
        st.markdown("### ⌨️ Typing Mode")
        current_text = st.session_state.get("letter_body", "")
        new_text = st.text_area("Letter Body", value=current_text, height=400, label_visibility="collapsed", placeholder="Dear...")
        
        if "letter_body_history" not in st.session_state:
            st.session_state.letter_body_history = []
        
        col_polish, col_undo = st.columns([1, 1])
        with col_polish:
            if st.button("✨ AI Polish (Professional)"):
                if new_text and ai_engine:
                    with st.spinner("Polishing..."):
                        try:
                            st.session_state.letter_body_history.append(new_text)
                            polished = ai_engine.refine_text(new_text, style="Professional")
                            if polished:
                                st.session_state.letter_body = polished
                                st.rerun()
                        except Exception as e: st.error(f"AI Error: {e}")
                else: st.warning("Please write something first.")
        
        with col_undo:
            if len(st.session_state.get("letter_body_history", [])) > 0:
                if st.button("↩️ Undo Last Change"):
                    st.session_state.letter_body = st.session_state.letter_body_history.pop()
                    st.rerun()

        if new_text != current_text:
            st.session_state.letter_body = new_text
            if time.time() - st.session_state.get("last_autosave", 0) > 3:
                d_id = st.session_state.get("current_draft_id")
                if d_id and database:
                    database.update_draft_data(d_id, content=new_text)
                    st.session_state.last_autosave = time.time()
                    st.caption("💾 Auto-saved")

    with tab_record:
        st.markdown("### 🎙️ Voice Mode")
        audio_val = st.audio_input("Record", label_visibility="collapsed")
        
        if audio_val:
            audio_bytes = audio_val.getvalue()
            audio_hash = hashlib.md5(audio_bytes).hexdigest()
            
            if audio_hash != st.session_state.get("last_processed_audio_hash"):
                st.info("⏳ Processing...")
                tmp_path = f"/tmp/temp_{int(time.time())}.wav"
                with open(tmp_path, "wb") as f: f.write(audio_bytes)
                try:
                    text = ai_engine.transcribe_audio(tmp_path)
                    if text:
                        if hasattr(ai_engine, 'enhance_transcription_for_seniors'):
                            text = ai_engine.enhance_transcription_for_seniors(text)
                        current = st.session_state.get("letter_body", "")
                        st.session_state.letter_body = (current + "\n\n" + text).strip()
                        st.session_state.last_processed_audio_hash = audio_hash
                        st.success("✅ Transcribed! Switch to 'Type Manually' to see the text.")
                        st.rerun()
                    else: st.warning("⚠️ No speech detected.")
                except Exception as e: st.error(f"Error: {e}")
                finally:
                    if os.path.exists(tmp_path): os.remove(tmp_path)

    st.divider()
    
    if st.button("👀 Review & Pay (Next Step)", type="primary", use_container_width=True):
        if not st.session_state.get("letter_body"):
            st.error("⚠️ Letter is empty!")
        elif not st.session_state.get("addr_to"):
            st.error("⚠️ Please save addresses first.")
        else:
            st.session_state.app_mode = "review"
            st.rerun()

def render_review_page():
    """Step 4: Secure & Send."""
    st.markdown("## 👁️ Step 4: Secure & Send")
    
    if st.button("📄 Generate PDF Proof"):
        with st.spinner("Generating Proof..."):
            try:
                tier = st.session_state.get("locked_tier", "Standard")
                body = st.session_state.get("letter_body", "")
                std_to = address_standard.StandardAddress.from_dict(st.session_state.get("addr_to", {}))
                std_from = address_standard.StandardAddress.from_dict(st.session_state.get("addr_from", {}))
                
                raw_pdf = letter_format.create_pdf(body, std_to, std_from, tier, signature_text=st.session_state.get("signature_text"))
                pdf_bytes = bytes(raw_pdf)
                
                import base64
                b64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
                st.markdown(f'<embed src="data:application/pdf;base64,{b64_pdf}" width="100%" height="500" type="application/pdf">', unsafe_allow_html=True)
                st.download_button("⬇️ Download PDF", pdf_bytes, "letter_proof.pdf", "application/pdf")
            except Exception as e: st.error(f"PDF Error: {e}")

    st.divider()
    
    tier = st.session_state.get("locked_tier", "Standard")
    is_cert = st.checkbox("Add Certified Mail Tracking (+$12.00)")
    total = pricing_engine.calculate_total(tier, is_certified=is_cert)
    
    # Promo Code
    discount = 0.0
    if promo_engine:
        with st.expander("🎟️ Have a Promo Code?"):
            code = st.text_input("Enter Code").upper()
            if st.button("Apply Code"):
                valid, val = promo_engine.validate_code(code)
                if valid:
                    st.session_state.applied_promo = code
                    st.session_state.promo_val = val
                    st.success(f"Applied! ${val} off")
                    st.rerun()
                else: st.error("Invalid Code")
    
    if st.session_state.get("applied_promo"):
        discount = st.session_state.get("promo_val", 0)
        total = max(0, total - discount)
        st.info(f"Discount Applied: -${discount}")

    st.markdown(f"### Total: ${total:.2f}")

    if st.button("💳 Proceed to Secure Checkout", type="primary", use_container_width=True):
        u_email = st.session_state.get("user_email")
        d_id = st.session_state.get("current_draft_id")
        
        if d_id and database:
            database.update_draft_data(d_id, price=total, status="Pending Payment")
        
        url = payment_engine.create_checkout_session(
            line_items=[{
                "price_data": {
                    "currency": "usd",
                    "product_data": {"name": f"VerbaPost - {tier}"},
                    "unit_amount": int(total * 100),
                },
                "quantity": 1,
            }],
            user_email=u_email,
            draft_id=d_id
        )
        if url: st.link_button("👉 Click to Pay", url)
        else: st.error("Payment Gateway Error")

# --- ROUTER CONTROLLER ---
def render_application():
    if "app_mode" not in st.session_state: st.session_state.app_mode = "splash"
    mode = st.session_state.app_mode

    if mode == "splash":
        if ui_splash: ui_splash.render_splash_page()
        else: st.error("Splash missing")
    elif mode == "login":
        if ui_login: ui_login.render_login_page()
        else: st.error("Login missing")
    elif mode == "store":
        render_store_page()
    elif mode == "workspace":
        render_workspace_page()
    elif mode == "review":
        render_review_page()
    elif mode == "admin":
        if ui_admin: ui_admin.render_admin_page()
        else: st.error("Admin missing")
    elif mode == "legal":
        if ui_legal: ui_legal.render_legal_page()
        else: st.error("Legal missing")
    elif mode == "legacy":
        if ui_legacy: ui_legacy.render_legacy_page()
        else: st.error("Legacy missing")
    else:
        st.warning(f"Unknown Mode: {mode}")
        if st.button("Reset"): reset_app_state()

def render_main():
    render_application()

if __name__ == "__main__":
    render_main()