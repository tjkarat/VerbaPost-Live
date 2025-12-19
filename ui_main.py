import streamlit as st
import time
import os
import base64
import re
import pandas as pd

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
try: import promo_engine
except ImportError: promo_engine = None

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
try: import ui_heirloom
except ImportError: ui_heirloom = None


# --- HELPER: SAFE PROFILE GETTER ---
def get_profile_field(profile, field, default=""):
    if not profile: return default
    if isinstance(profile, dict): return profile.get(field, default)
    return getattr(profile, field, default)

def _ensure_profile_loaded():
    """Syncs DB Profile to Session State if not done yet."""
    if st.session_state.get("authenticated") and not st.session_state.get("profile_synced"):
        try:
            email = st.session_state.get("user_email")
            profile = database.get_user_profile(email)
            if profile:
                st.session_state.user_profile = profile
                # Pre-fill FROM address in Session State
                st.session_state.from_name = get_profile_field(profile, "full_name")
                st.session_state.from_street = get_profile_field(profile, "address_line1")
                st.session_state.from_city = get_profile_field(profile, "address_city")
                st.session_state.from_state = get_profile_field(profile, "address_state")
                st.session_state.from_zip = get_profile_field(profile, "address_zip")
                st.session_state.profile_synced = True 
                st.rerun()
        except Exception as e:
            print(f"Profile Load Error: {e}")

# --- CSS INJECTOR (SAFE FONT LOADING) ---
def inject_custom_css(text_size=16):
    import base64
    font_face_css = ""
    try:
        # Try loading the custom font file
        with open("type_right.ttf", "rb") as f:
            b64_font = base64.b64encode(f.read()).decode()
        font_face_css = f"""
            @font-face {{
                font-family: 'TypeRight';
                src: url('data:font/ttf;base64,{b64_font}') format('truetype');
            }}
        """
    except FileNotFoundError:
        font_face_css = ""

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
        .stTextInput input {{ font-family: 'Helvetica Neue', sans-serif !important; }}
        p, li, .stMarkdown {{ font-family: 'Helvetica Neue', sans-serif; font-size: {text_size}px !important; line-height: 1.6 !important; }}
        .price-card {{ background-color: #ffffff; border-radius: 12px; padding: 20px 15px; text-align: center; border: 1px solid #e0e0e0; height: 220px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); display: flex; flex-direction: column; justify-content: flex-start; gap: 5px; }}
        .price-header {{ font-weight: 700; font-size: 1.4rem; color: #1f2937; margin-bottom: 2px; height: 35px; display: flex; align-items: center; justify-content: center; }}
        .price-sub {{ font-size: 0.75rem; font-weight: 600; color: #9ca3af; text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 5px; }}
        .price-tag {{ font-size: 2.4rem; font-weight: 800; color: #d93025; margin: 5px 0; }}
        .price-desc {{ font-size: 0.9rem; color: #4b5563; line-height: 1.3; margin-top: auto; padding-bottom: 5px; min-height: 50px; }}
        .instruction-box {{ background-color: #FEF3C7; border-left: 6px solid #F59E0B; padding: 15px; margin-bottom: 20px; border-radius: 4px; color: #000; }}
        #MainMenu {{visibility: hidden;}}
        footer {{visibility: hidden;}}
        </style>
    """, unsafe_allow_html=True)

# --- HELPER FUNCTIONS ---
def load_address_book():
    """Fetches user contacts for the dropdown."""
    if not st.session_state.get("authenticated"):
        return {}
    try:
        user_email = st.session_state.get("user_email")
        # Ensure database module has get_contacts
        contacts = database.get_contacts(user_email) if hasattr(database, 'get_contacts') else []
        result = {}
        for c in contacts:
            # Handle both dict and object access safely
            c_name = c.get('name') if isinstance(c, dict) else getattr(c, 'name', '')
            c_city = c.get('city') if isinstance(c, dict) else getattr(c, 'city', 'Unknown')
            label = f"{c_name} ({c_city})"
            result[label] = c
        return result
    except Exception as e:
        print(f"Address Book Error: {e}")
        return {}

def _handle_draft_creation(email, tier, price):
    d_id = st.session_state.get("current_draft_id")
    success = False
    if d_id:
        success = database.update_draft_data(d_id, status="Draft", tier=tier, price=price)
    if not success or not d_id:
        d_id = database.save_draft(email, "", tier, price)
        st.session_state.current_draft_id = d_id
    return d_id

# --- GLOBAL CALLBACKS ---
def cb_select_tier(tier, price, user_email):
    try:
        st.query_params.clear()
        st.session_state.locked_tier = tier
        st.session_state.locked_price = price
        st.session_state.app_mode = "workspace"
        if user_email:
            _handle_draft_creation(user_email, tier, price)
    except Exception as e:
        print(f"Draft creation warning: {e}")
        st.session_state.app_mode = "workspace"

# --- PAGE RENDERERS ---

def render_store_page():
    inject_custom_css(16)
    u_email = st.session_state.get("user_email", "")
    
    if not u_email:
        st.warning("⚠️ Session Expired. Please log in to continue.")
        if st.button("Go to Login"):
            st.session_state.app_mode = "login"
            st.rerun()
        return

    # --- RESTORED: HOW IT WORKS ---
    with st.expander("❓ How VerbaPost Works", expanded=True):
        st.markdown("""
        **1. Select Service:** Choose your letter style below (Standard, Heirloom, etc).
        **2. Write or Speak:** Use our AI voice tool to dictate, or type manually.
        **3. Address:** Load contacts from your address book or add new ones.
        **4. We Mail It:** We print, envelope, stamp, and mail it via USPS First Class.
        """)

    st.markdown("## 📮 Choose Your Letter Service")
    
    mode = st.radio("Mode", ["Single Letter", "Bulk Campaign"], horizontal=True, label_visibility="collapsed")
    
    if mode == "Bulk Campaign":
        st.info("📢 **Campaign Mode Active.**")
        render_campaign_uploader()
        return

    c1, c2, c3, c4 = st.columns(4)
    def html_card(title, qty_text, price, desc):
        return f"""<div class="price-card"><div class="price-header">{title}</div><div class="price-sub">{qty_text}</div><div class="price-tag">${price}</div><div class="price-desc">{desc}</div></div>"""

    with c1: st.markdown(html_card("Standard", "ONE LETTER", "2.99", "Premium paper. Times New Roman."), unsafe_allow_html=True)
    with c2: st.markdown(html_card("Heirloom", "ONE LETTER", "5.99", "Cream paper. Typewriter font."), unsafe_allow_html=True)
    with c3: st.markdown(html_card("Civic", "3 LETTERS", "6.99", "Find reps automatically."), unsafe_allow_html=True)
    with c4: st.markdown(html_card("Santa", "ONE LETTER", "9.99", "North Pole Postmark."), unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True) 
    b1, b2, b3, b4 = st.columns(4)
    with b1: st.button("Select Standard", use_container_width=True, on_click=cb_select_tier, args=("Standard", 2.99, u_email))
    with b2: st.button("Select Heirloom", key="btn_store_heirloom_product", use_container_width=True, on_click=cb_select_tier, args=("Heirloom", 5.99, u_email))
    with b3: st.button("Select Civic", use_container_width=True, on_click=cb_select_tier, args=("Civic", 6.99, u_email))
    with b4: st.button("Select Santa", use_container_width=True, on_click=cb_select_tier, args=("Santa", 9.99, u_email))

def render_campaign_uploader():
    st.markdown("### 📁 Upload Recipient List (CSV)")
    uploaded_file = st.file_uploader("Upload CSV", type=["csv"])
    if uploaded_file:
        contacts = bulk_engine.parse_csv(uploaded_file)
        if not contacts:
            st.error("❌ Could not parse CSV.")
            return
        st.success(f"✅ Loaded {len(contacts)} recipients.")
        st.dataframe(contacts[:5])
        total = pricing_engine.calculate_total("Campaign", qty=len(contacts))
        st.metric("Total", f"${total}")
        if st.button("Proceed"):
            st.session_state.locked_tier = "Campaign"
            st.session_state.bulk_targets = contacts
            st.session_state.app_mode = "workspace"; st.rerun()

def render_workspace_page():
    _ensure_profile_loaded()
    col_slide, col_gap = st.columns([1, 2])
    with col_slide: text_size = st.slider("Text Size", 12, 24, 16)
    inject_custom_css(text_size)
    
    current_tier = st.session_state.get('locked_tier', 'Draft')
    st.markdown(f"## 📝 Workspace: {current_tier}")

    # --- RESTORED: ROBUST ADDRESSING SECTION ---
    with st.expander("📍 Addressing (To & From)", expanded=True):
        
        # 1. ADDRESS BOOK LOADER
        addr_book = load_address_book()
        contact_options = ["-- Select from Address Book --"] + list(addr_book.keys())
        
        c_load, c_clear = st.columns([3, 1])
        with c_load:
            selected_contact_label = st.selectbox("📖 Quick Load Contact", contact_options, label_visibility="collapsed")
        
        # Auto-fill logic
        if selected_contact_label and selected_contact_label != "-- Select from Address Book --":
            data = addr_book[selected_contact_label]
            # Populate session state with selected data safely
            st.session_state.to_name = data.get('name', '')
            st.session_state.to_street = data.get('street') or data.get('address_line1', '')
            st.session_state.to_city = data.get('city') or data.get('address_city', '')
            st.session_state.to_state = data.get('state') or data.get('address_state', '')
            st.session_state.to_zip = data.get('zip') or data.get('address_zip', '')

        # 2. ADDRESS FORM TABS
        tab_to, tab_from = st.tabs(["📬 Recipient (To)", "🏠 Sender (From)"])
        
        with tab_to:
            if current_tier == "Campaign": 
                st.info("📬 Bulk Mode active. Recipients defined in CSV.")
            else:
                c1, c2 = st.columns(2)
                with c1: st.text_input("Recipient Name", key="to_name")
                with c2: st.text_input("Street Address", key="to_street")
                c3, c4, c5 = st.columns([2, 1, 1])
                with c3: st.text_input("City", key="to_city")
                with c4: st.text_input("State", key="to_state")
                with c5: st.text_input("Zip Code", key="to_zip")

        with tab_from:
            c1, c2 = st.columns(2)
            with c1: st.text_input("Your Name", key="from_name")
            with c2: st.text_input("Your Street", key="from_street")
            c3, c4, c5 = st.columns([2, 1, 1])
            with c3: st.text_input("City", key="from_city")
            with c4: st.text_input("State", key="from_state")
            with c5: st.text_input("Zip Code", key="from_zip")

        # Save Logic
        if st.button("💾 Save Addresses", use_container_width=True):
             # Save TO address to state
            st.session_state.addr_to = {
                "name": st.session_state.get("to_name"),
                "street": st.session_state.get("to_street"),
                "city": st.session_state.get("to_city"),
                "state": st.session_state.get("to_state"),
                "zip": st.session_state.get("to_zip")
            }
            # Save FROM address to state
            st.session_state.addr_from = {
                "name": st.session_state.get("from_name"),
                "street": st.session_state.get("from_street"),
                "city": st.session_state.get("from_city"),
                "state": st.session_state.get("from_state"),
                "zip": st.session_state.get("from_zip")
            }
            st.success("✅ Addresses Secured.")

    st.divider()

    # --- RESTORED: SPEAK & WRITE SECTION ---
    st.markdown("## ✍️ Write Letter")
    
    # Dictation Expander
    with st.expander("🎙️ Speak Your Letter (Dictation)", expanded=False):
        st.markdown("""
        <div class="instruction-box">
        <b>Instructions:</b>
        1. Click <b>Start Recording</b>.
        2. Speak your letter clearly including punctuation (e.g., "Period", "New Paragraph").
        3. Click <b>Stop</b> when finished. The text will appear below automatically.
        </div>
        """, unsafe_allow_html=True)
        
        # Audio Input Widget
        audio_val = st.audio_input("Record Audio")
        
        if audio_val:
            if st.button("✨ Transcribe Audio"):
                if ai_engine:
                    with st.spinner("🤖 AI is listening and typing..."):
                        transcription = ai_engine.transcribe_audio(audio_val)
                        if transcription and not str(transcription).startswith("Error"):
                            # Append or Replace logic? Usually replace for a fresh start or append
                            current_body = st.session_state.get("letter_body", "")
                            st.session_state.letter_body = current_body + "\n\n" + transcription
                            st.rerun()
                        else:
                            st.error(f"Transcription failed: {transcription}")
                else:
                    st.error("AI Engine not loaded.")

    # Main Text Area
    new_text = st.text_area("Body Content", value=st.session_state.get("letter_body", ""), height=400)
    st.session_state.letter_body = new_text

    st.markdown("---")
    if st.button("👀 Review & Pay (Next Step)", type="primary", use_container_width=True):
        # Basic validation
        if not st.session_state.get("letter_body"):
            st.error("⚠️ Please write or dictate your letter first.")
        else:
            st.session_state.app_mode = "review"
            st.rerun()

def render_review_page():
    """Persistent placeholders for real-time progress."""
    st.markdown("## 👁️ Step 4: Secure & Send")
    current_tier = st.session_state.get("locked_tier", "Standard")
    
    # LOCK: PAYMENT STATE PERSISTENCE
    if st.query_params.get("success") == "true":
        st.session_state.campaign_paid = True

    # --- RESTORED PROMO CODE LOGIC ---
    discount = 0.0
    promo_code = st.text_input("🎟️ Promo Code (Optional)")
    if promo_code and promo_engine:
        valid, val = promo_engine.validate_promo(promo_code)
        if valid:
            discount = val
            st.success(f"✅ Coupon applied: ${discount} off")
        else:
            st.error("❌ Invalid Code")

    if current_tier == "Campaign":
        targets = st.session_state.get("bulk_targets", [])
        st.info(f"📋 Campaign Mode: Mailing {len(targets)} personalized letters.")
        
        # 1. THE PAYMENT PHASE
        if not st.session_state.get("campaign_paid"):
            st.warning("⚠️ Secure payment required to start dispatch.")
            
            raw_total = pricing_engine.calculate_total(current_tier, qty=len(targets))
            final_total = max(0.0, raw_total - discount)
            st.markdown(f"### Total: ${final_total:.2f}")
            
            if st.button("💳 Proceed to Checkout", type="primary", use_container_width=True):
                url = payment_engine.create_checkout_session(
                    line_items=[{"price_data": {"currency": "usd", "product_data": {"name": "Campaign"}, "unit_amount": int(final_total * 100)}, "quantity": 1}], 
                    user_email=st.session_state.get("user_email")
                )
                if url: st.link_button("👉 Open Payment Gateway", url)
        
        # 2. THE DISPATCH PHASE (UNLOCKED)
        else:
            st.success("✅ Payment Verified. Engine Unlocked.")
            metrics_spot = st.empty()
            progress_spot = st.empty()
            
            if "campaign_metrics" not in st.session_state:
                st.session_state.campaign_metrics = {"sent": 0, "failed": 0, "total": len(targets)}
            
            with metrics_spot.container():
                c1, c2, c3 = st.columns(3)
                c1.metric("Target", len(targets))
                c2.metric("Success ✅", st.session_state.campaign_metrics["sent"])
                c3.metric("Failed ❌", st.session_state.campaign_metrics["failed"])

            if st.button("🚀 EXECUTE CAMPAIGN", type="primary", use_container_width=True):
                results_log = []
                for i, contact in enumerate(targets):
                    progress_spot.progress((i + 1) / len(targets), text=f"Mailing {contact['name']}...")
                    try:
                        p_body = re.sub(r"\[Organization Name\]", contact.get('name', ''), st.session_state.letter_body, flags=re.IGNORECASE)
                        std_to = address_standard.StandardAddress.from_dict(contact)
                        std_from = address_standard.StandardAddress.from_dict(st.session_state.get("addr_from", {}))
                        pdf = letter_format.create_pdf(p_body, std_to, std_from, current_tier, st.session_state.get("signature_text"))
                        
                        success, resp = mailer.send_letter(pdf, std_to, std_from, current_tier)
                        if success:
                            st.session_state.campaign_metrics["sent"] += 1
                            results_log.append({"Name": contact['name'], "Status": "Success", "ID": resp})
                        else:
                            st.session_state.campaign_metrics["failed"] += 1
                            results_log.append({"Name": contact['name'], "Status": "Failed", "Error": str(resp)})
                    except Exception as e:
                        st.session_state.campaign_metrics["failed"] += 1
                        results_log.append({"Name": contact['name'], "Status": "Error", "Error": str(e)})

                    with metrics_spot.container():
                        c1, c2, c3 = st.columns(3)
                        c1.metric("Target", len(targets))
                        c2.metric("Success ✅", st.session_state.campaign_metrics["sent"])
                        c3.metric("Failed ❌", st.session_state.campaign_metrics["failed"])

                progress_spot.empty(); st.balloons()
                st.download_button("📥 Result CSV", pd.DataFrame(results_log).to_csv(index=False), "results.csv", "text/csv")
                if mailer: mailer.send_email_notification(st.session_state.user_email, "Campaign Results", f"Success: {st.session_state.campaign_metrics['sent']}")
    else:
        # Standard Letter Logic
        if st.button("📄 Proof (Download/View)"):
            try:
                # Ensure address state is set before proofing
                if not st.session_state.get("addr_to") or not st.session_state.get("addr_from"):
                    st.warning("⚠️ Addresses not saved. Please check the 'Addressing' section.")
                
                std_to = address_standard.StandardAddress.from_dict(st.session_state.get("addr_to", {}))
                std_from = address_standard.StandardAddress.from_dict(st.session_state.get("addr_from", {}))
                
                pdf = letter_format.create_pdf(st.session_state.letter_body, std_to, std_from, current_tier, st.session_state.get("signature_text"))
                
                # Display PDF
                b64_pdf = base64.b64encode(pdf).decode('utf-8')
                pdf_display = f'<iframe src="data:application/pdf;base64,{b64_pdf}" width="100%" height="500" type="application/pdf"></iframe>'
                st.markdown(pdf_display, unsafe_allow_html=True)
            except Exception as e: 
                st.error(f"Proof failed: {e}")
        
        raw_total = pricing_engine.calculate_total(current_tier) if pricing_engine else 2.99
        final_total = max(0.0, raw_total - discount)
        st.markdown(f"### Total: ${final_total:.2f}")
        
        if st.button("💳 Pay & Send", type="primary"):
            line_items = [{
                "price_data": {
                    "currency": "usd",
                    "product_data": {"name": f"VerbaPost - {current_tier}"},
                    "unit_amount": int(final_total * 100)
                },
                "quantity": 1
            }]
            
            url = payment_engine.create_checkout_session(
                line_items=line_items, 
                user_email=st.session_state.get("user_email")
            )
            if url: st.link_button("👉 Click to Pay", url)

def render_application():
    if "app_mode" not in st.session_state: st.session_state.app_mode = "splash"
    mode = st.session_state.app_mode
    if mode == "splash": ui_splash.render_splash_page()
    elif mode == "login": ui_login.render_login_page()
    elif mode == "store": render_store_page()
    elif mode == "workspace": render_workspace_page()
    elif mode == "review": render_review_page()
    elif mode == "legal": ui_legal.render_legal_page()
    elif mode == "legacy": ui_legacy.render_legacy_page()
    else: st.session_state.app_mode = "splash"; st.rerun()

def render_main(): render_application()
if __name__ == "__main__": render_main()