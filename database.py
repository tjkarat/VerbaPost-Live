import streamlit as st
import time
import os
import hashlib
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

# --- HELPER: SAFE PROFILE GETTER ---
def get_profile_field(profile, field, default=""):
    if not profile: return default
    if isinstance(profile, dict): return profile.get(field, default)
    return getattr(profile, field, default)

def _ensure_profile_loaded():
    """
    Robust profile loader. Checks if the 'From' address is missing 
    and re-fetches it from the database if needed.
    """
    if st.session_state.get("authenticated"):
        # Load if synced flag is missing OR if the actual data is empty
        needs_load = not st.session_state.get("profile_synced") or not st.session_state.get("from_name")
        
        if needs_load:
            try:
                email = st.session_state.get("user_email")
                profile = database.get_user_profile(email)
                if profile:
                    st.session_state.user_profile = profile
                    # Auto-Populate Session State for Text Inputs
                    st.session_state.from_name = get_profile_field(profile, "full_name")
                    st.session_state.from_street = get_profile_field(profile, "address_line1")
                    st.session_state.from_city = get_profile_field(profile, "address_city")
                    st.session_state.from_state = get_profile_field(profile, "address_state")
                    st.session_state.from_zip = get_profile_field(profile, "address_zip")
                    
                    st.session_state.profile_synced = True 
                    st.rerun() # Refresh to show data
            except Exception as e:
                print(f"Profile Load Error: {e}")

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
        .stTabs [data-baseweb="tab"] p {{ font-size: 1.2rem !important; font-weight: 600 !important; }}
        .stTabs [data-baseweb="tab"] {{ height: 60px; white-space: pre-wrap; background-color: #F0F2F6; border-radius: 8px 8px 0px 0px; gap: 2px; padding: 10px; border: 1px solid #ccc; border-bottom: none; color: #333; }}
        .stTabs [aria-selected="true"] {{ background-color: #FF4B4B !important; border: 1px solid #FF4B4B !important; color: white !important; }}
        .stTabs [aria-selected="true"] p {{ color: white !important; }}
        .instruction-box {{ background-color: #FEF3C7; border-left: 6px solid #F59E0B; padding: 15px; margin-bottom: 20px; border-radius: 4px; color: #000; }}
        
        #MainMenu {{visibility: hidden;}}
        footer {{visibility: hidden;}}
        </style>
    """, unsafe_allow_html=True)

# --- HELPER FUNCTIONS ---
def load_address_book():
    """Fetches contacts from DB safely."""
    if not st.session_state.get("authenticated"):
        return {}
    try:
        user_email = st.session_state.get("user_email")
        # Explicit strip to handle potential whitespace in session
        if user_email: user_email = user_email.strip()
        
        # Database call using safe model
        contacts = database.get_contacts(user_email)
        
        result = {}
        for c in contacts:
            name = c.get('name', 'Unknown')
            street = c.get('street', '')[:10]
            label = f"{name} ({street}...)"
            result[label] = c
        return result
    except Exception as e:
        # VISIBLE ERROR FOR DEBUGGING
        st.error(f"Address Book Load Error: {e}")
        return {}

def _save_new_contact(contact_data):
    """Smartly saves a contact only if it doesn't exist."""
    try:
        if not st.session_state.get("authenticated"): return
        
        user_email = st.session_state.get("user_email")
        current_book = load_address_book()
        
        is_new = True
        for label, existing in current_book.items():
            if (existing.get('name') == contact_data.get('name') and 
                existing.get('street') == contact_data.get('street')):
                is_new = False
                break
        
        if is_new:
            if hasattr(database, "save_contact"):
                database.save_contact(user_email, contact_data)
            return True
        return False
    except Exception as e:
        st.error(f"Save Contact Error: {e}")
        return False

def _handle_draft_creation(email, tier, price):
    d_id = st.session_state.get("current_draft_id")
    success = False
    if d_id:
        success = database.update_draft_data(d_id, status="Draft", tier=tier, price=price)
    if not success or not d_id:
        d_id = database.save_draft(email, "", tier, price)
        st.session_state.current_draft_id = d_id
    return d_id

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

    with st.expander("❓ How VerbaPost Works", expanded=False):
        st.markdown("""
        1. **Select Service:** Choose your letter tier below.
        2. **Write:** Type or dictate your content.
        3. **Address:** Load or enter recipient.
        4. **Send:** We print and mail it via USPS.
        """)

    st.markdown("## 📮 Choose Your Letter Service")
    
    mode = st.radio("Mode", ["Single Letter", "Bulk Campaign"], horizontal=True, label_visibility="collapsed")
    
    if mode == "Bulk Campaign":
        render_campaign_uploader()
        return

    # --- 3 COLUMN LAYOUT ---
    c1, c2, c3 = st.columns(3)
    
    def html_card(title, qty_text, price, desc):
        return f"""
        <div class="price-card">
            <div class="price-header">{title}</div>
            <div class="price-sub">{qty_text}</div>
            <div class="price-tag">${price}</div>
            <div class="price-desc">{desc}</div>
        </div>
        """

    with c1:
        st.markdown(html_card("Standard", "ONE LETTER", "2.99", "Premium paper. Standard #10 Envelope."), unsafe_allow_html=True)
    with c2:
        st.markdown(html_card("Vintage", "ONE LETTER", "5.99", "Heavy cream paper. Wax seal effect."), unsafe_allow_html=True)
    with c3:
        st.markdown(html_card("Civic", "3 LETTERS", "6.99", "Write to Congress. We find reps automatically."), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True) 
    b1, b2, b3 = st.columns(3)
    
    with b1:
        if st.button("Select Standard", key="store_btn_standard_final", use_container_width=True):
            st.session_state.locked_tier = "Standard"
            st.session_state.locked_price = 2.99
            st.session_state.app_mode = "workspace"
            _handle_draft_creation(u_email, "Standard", 2.99)
            st.rerun()

    with b2:
        if st.button("Select Vintage", key="store_btn_vintage_final", use_container_width=True):
            st.session_state.locked_tier = "Vintage"
            st.session_state.locked_price = 5.99
            st.session_state.app_mode = "workspace"
            _handle_draft_creation(u_email, "Vintage", 5.99)
            st.rerun()

    with b3:
        if st.button("Select Civic", key="store_btn_civic_final", use_container_width=True):
            st.session_state.locked_tier = "Civic"
            st.session_state.locked_price = 6.99
            st.session_state.app_mode = "workspace"
            _handle_draft_creation(u_email, "Civic", 6.99)
            st.rerun()

def render_campaign_uploader():
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
    # 1. AUTO-POPULATE TRIGGER
    _ensure_profile_loaded()
    
    col_slide, col_gap = st.columns([1, 2])
    with col_slide:
        text_size = st.slider("Text Size", 12, 24, 16, help="Adjust text size")
    inject_custom_css(text_size)

    current_tier = st.session_state.get('locked_tier', 'Draft')
    st.markdown(f"## 📝 Workspace: {current_tier}")

    with st.expander("📍 Step 2: Addressing", expanded=True):
        st.info("💡 **Tip:** Hit 'Save Addresses' to lock them in.")
        
        # 2. ADDRESS BOOK LOGIC
        if st.session_state.get("authenticated") and current_tier != "Civic":
            addr_opts = load_address_book()
            
            if addr_opts:
                col_load, col_empty = st.columns([2, 1])
                with col_load:
                    selected_contact_label = st.selectbox("📂 Load Saved Contact", ["Select..."] + list(addr_opts.keys()))
                    if selected_contact_label != "Select..." and selected_contact_label != st.session_state.get("last_loaded_contact"):
                        data = addr_opts[selected_contact_label]
                        st.session_state.to_name_input = data.get('name', '')
                        st.session_state.to_street_input = data.get('street', '')
                        st.session_state.to_city_input = data.get('city', '')
                        st.session_state.to_state_input = data.get('state', '')
                        st.session_state.to_zip_input = data.get('zip_code', '') 
                        st.session_state.last_loaded_contact = selected_contact_label
                        st.rerun()
            else:
                st.caption("ℹ️ No saved contacts found. Add friends in your Profile to see them here.")

        with st.form("addressing_form"):
            col_to, col_from = st.columns(2)
            with col_to:
                st.markdown("### To: (Recipient)")
                if current_tier == "Civic" and civic_engine:
                    st.info("ℹ️ We will send 3 letters: One to your Rep, and two to your Senators.")
                    if st.form_submit_button("🏛️ Find My Representatives"):
                        temp_addr = {
                            "street": st.session_state.get("from_street"),
                            "city": st.session_state.get("from_city"),
                            "state": st.session_state.get("from_state"),
                            "zip": st.session_state.get("from_zip")
                        }
                        if temp_addr["zip"]:
                            with st.spinner(f"Looking up officials for {temp_addr['zip']}..."):
                                reps = civic_engine.find_representatives(temp_addr)
                                if reps:
                                    st.session_state.civic_reps_found = reps
                                    st.success(f"✅ Found {len(reps)} officials! We will mail all of them.")
                                else:
                                    st.error("❌ No officials found. Please check your 'From' address.")
                        else:
                            st.error("⚠️ Please fill out your 'From' address first.")
                    if st.session_state.get("civic_reps_found"):
                        st.write("---")
                        st.markdown("**Recipients Found:**")
                        for r in st.session_state.civic_reps_found:
                            st.caption(f"• {r['name']} ({r['office']})")
                else:
                    st.text_input("Name", key="to_name_input")
                    st.text_input("Street Address", key="to_street_input")
                    st.text_input("City", key="to_city_input")
                    c_s, c_z = st.columns(2)
                    c_s.text_input("State", key="to_state_input")
                    c_z.text_input("Zip", key="to_zip_input")

            with col_from:
                st.markdown("### From: (Return Address)")
                st.text_input("Your Name", key="from_name")
                st.text_input("Signature (Sign-off)", key="from_sig")
                st.text_input("Your Street", key="from_street")
                st.text_input("Your City", key="from_city")
                c_fs, c_fz = st.columns(2)
                c_fs.text_input("Your State", key="from_state")
                c_fz.text_input("Your Zip", key="from_zip")
            
            # Add Smart Save Option
            save_to_book = False
            if current_tier != "Civic" and st.session_state.get("authenticated"):
                 st.caption("✅ New contacts will be automatically saved to your Address Book.")
                 save_to_book = True

            if current_tier != "Civic":
                if st.form_submit_button("💾 Save Addresses"):
                    st.session_state.addr_to = {
                        "name": st.session_state.to_name_input, 
                        "street": st.session_state.to_street_input, 
                        "city": st.session_state.to_city_input, 
                        "state": st.session_state.to_state_input, 
                        "zip_code": st.session_state.to_zip_input
                    }
                    st.session_state.addr_from = {
                        "name": st.session_state.from_name, 
                        "street": st.session_state.from_street, 
                        "city": st.session_state.from_city, 
                        "state": st.session_state.from_state, 
                        "zip_code": st.session_state.from_zip
                    }
                    st.session_state.signature_text = st.session_state.from_sig
                    
                    # Update Draft
                    d_id = st.session_state.get("current_draft_id")
                    if d_id and database:
                        to_str = str(st.session_state.addr_to)
                        from_str = str(st.session_state.addr_from)
                        database.update_draft_data(d_id, to_addr=to_str, from_addr=from_str)

                    # Smart Address Book Save
                    if save_to_book:
                        _save_new_contact(st.session_state.addr_to)

                    if mailer:
                        with st.spinner("Validating with USPS/PostGrid..."):
                            t_valid, t_data = mailer.validate_address(st.session_state.addr_to)
                            f_valid, f_data = mailer.validate_address(st.session_state.addr_from)
                            if not t_valid:
                                err = t_data.get('error', 'Invalid Recipient Address')
                                st.error(f"❌ Recipient Address Error: {err}")
                            if not f_valid:
                                err = f_data.get('error', 'Invalid Sender Address')
                                st.error(f"❌ Sender Address Error: {err}")
                            if t_valid and f_valid:
                                st.session_state.addr_to = t_data
                                st.session_state.addr_from = f_data
                                st.session_state.addresses_saved_at = time.time()
                                st.success(f"✅ Addresses Verified & Saved!")
                    else:
                        st.session_state.addresses_saved_at = time.time()
                        st.success(f"✅ Addresses Saved (Verification Offline)")
        
        # --- SAFE SUCCESS MESSAGE (Prevents "None") ---
        if st.session_state.get("addresses_saved_at") and time.time() - st.session_state.addresses_saved_at < 10:
            st.success("✅ Your addresses are saved and ready!")

    st.divider()

    st.markdown("## ✍️ Step 3: Write Your Letter")
    st.info("🎙️ **Voice Instructions:** Click the small microphone icon below. Speak for up to 5 minutes. Click the square 'Stop' button when finished.")
    tab_type, tab_rec = st.tabs(["⌨️ TYPE", "🎙️ SPEAK"])

    with tab_type:
        st.markdown("### ⌨️ Typing Mode")
        current_text = st.session_state.get("letter_body", "")
        new_text = st.text_area("Letter Body", value=current_text, height=400, label_visibility="collapsed", placeholder="Dear...")
        
        # --- NEW BUTTON LAYOUT ---
        col_save, col_polish, col_undo = st.columns([1, 1, 1])
        
        with col_save:
             if st.button("💾 Save Draft", use_container_width=True):
                 st.session_state.letter_body = new_text
                 d_id = st.session_state.get("current_draft_id")
                 if d_id and database:
                     database.update_draft_data(d_id, content=new_text)
                     st.session_state.last_autosave = time.time()
                     st.toast("✅ Draft Saved Successfully")

        with col_polish:
            if st.button("✨ AI Polish (Professional)", use_container_width=True):
                if new_text and ai_engine:
                    with st.spinner("Polishing..."):
                        try:
                            if "letter_body_history" not in st.session_state: st.session_state.letter_body_history = []
                            st.session_state.letter_body_history.append(new_text)
                            polished = ai_engine.refine_text(new_text, style="Professional")
                            if polished:
                                st.session_state.letter_body = polished
                                st.rerun()
                        except Exception as e: st.error(f"AI Error: {e}")
        with col_undo:
            if "letter_body_history" in st.session_state and len(st.session_state.letter_body_history) > 0:
                if st.button("↩️ Undo Last Change", use_container_width=True):
                    st.session_state.letter_body = st.session_state.letter_body_history.pop()
                    st.rerun()

        # Auto-save Logic (Background)
        if new_text != current_text:
            st.session_state.letter_body = new_text
            if time.time() - st.session_state.get("last_autosave", 0) > 3:
                d_id = st.session_state.get("current_draft_id")
                if d_id:
                    database.update_draft_data(d_id, content=new_text)
                    st.session_state.last_autosave = time.time()
                    st.caption("💾 Auto-saved")

    with tab_rec:
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
                    if os.path.exists(tmp_path):
                        try: os.remove(tmp_path)
                        except: pass 

    st.divider()
    
    if st.button("👀 Review & Pay (Next Step)", type="primary", use_container_width=True):
        if not st.session_state.get("letter_body"):
            st.error("⚠️ Letter is empty!")
        elif not st.session_state.get("addr_to") and current_tier != "Civic":
            st.error("⚠️ Please save addresses first.")
        else:
            st.session_state.app_mode = "review"
            st.rerun()

    # --- DEBUGGER (New: Helps you see if data exists) ---
    with st.expander("🕵️ Database Inspector (Debug)", expanded=False):
        if st.button("Check Connectivity"):
            try:
                # RAW SQL Test
                with database.get_db_session() as s:
                    st.write(f"Connected to DB. Checking 'saved_contacts'...")
                    from sqlalchemy import text
                    result = s.execute(text("SELECT count(*) FROM saved_contacts"))
                    count = result.scalar()
                    st.write(f"Total Rows: {count}")
                    
                    # Fetch first 3
                    res_rows = s.execute(text("SELECT * FROM saved_contacts LIMIT 3"))
                    for row in res_rows:
                        st.write(row)
            except Exception as e:
                st.error(f"Inspector Error: {e}")

def render_review_page():
    tier = st.session_state.get("locked_tier", "Standard")
    st.markdown(f"## 👁️ Step 4: Secure & Send ({tier})")
    
    if st.button("📄 Generate PDF Proof"):
        with st.spinner("Generating Proof..."):
            try:
                body = st.session_state.get("letter_body", "")
                if tier == "Civic":
                    std_to = address_standard.StandardAddress(name="Representative", street="Washington DC", city="Washington", state="DC", zip_code="20515")
                else:
                    std_to = address_standard.StandardAddress.from_dict(st.session_state.get("addr_to", {}))
                std_from = address_standard.StandardAddress.from_dict(st.session_state.get("addr_from", {}))
                
                pdf_bytes = letter_format.create_pdf(body, std_to, std_from, tier, signature_text=st.session_state.get("signature_text"))
                
                import base64
                b64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
                st.markdown(f'<embed src="data:application/pdf;base64,{b64_pdf}" width="100%" height="500" type="application/pdf">', unsafe_allow_html=True)
                st.download_button("⬇️ Download PDF", pdf_bytes, "letter_proof.pdf", "application/pdf")
            except Exception as e: st.error(f"PDF Error: {e}")

    st.divider()
    
    # --- PRICING LOGIC ---
    is_cert = st.checkbox("Add Certified Mail Tracking (+$12.00)")
    
    # Calculate Base Total
    total = pricing_engine.calculate_total(tier, is_certified=is_cert)
    
    # Ensure tier wasn't reset to standard if price mismatches
    if tier == "Vintage" and total < 5.00:
        total = 5.99 + (12.00 if is_cert else 0.0)
    elif tier == "Santa" and total < 9.00:
        total = 9.99 + (12.00 if is_cert else 0.0)

    discount = 0.0
    
    # --- PROMO CODE LOGIC ---
    if promo_engine:
        with st.expander("🎟️ Have a Promo Code?"):
            raw_code = st.text_input("Enter Code", key="promo_input_field")
            code = raw_code.upper().strip() if raw_code else ""
            
            if st.button("Apply Code"):
                if not code:
                    st.error("Please enter a code.")
                else:
                    result = promo_engine.validate_code(code)
                    if isinstance(result, tuple) and len(result) == 2:
                        valid, val = result
                    else:
                        valid, val = False, "Engine Error"

                    if valid:
                        if val > 0:
                            st.session_state.applied_promo = code
                            st.session_state.promo_val = val
                            st.success(f"Applied! ${val} off")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.warning("Code is valid but has $0.00 value. Please check with support.")
                    else: st.error(f"Invalid Code: {val}")
                    
    if st.session_state.get("applied_promo"):
        discount = st.session_state.get("promo_val", 0)
        st.markdown(f"**Item Price:** ${total:.2f}")
        total = max(0, total - discount)
        st.info(f"Discount Applied: -${discount:.2f}")
    
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
def render_main():
    if "app_mode" not in st.session_state: st.session_state.app_mode = "store"
    mode = st.session_state.app_mode

    # STRICT ROUTING - Prevents "heirloom" ghost routing
    if mode == "store":
        render_store_page()
    elif mode == "workspace":
        render_workspace_page()
    elif mode == "review":
        render_review_page()
    else:
        # Fallback: if mode is anything else (e.g. heirloom), do nothing here.
        # This lets main.py handle the other modules.
        pass

if __name__ == "__main__":
    render_main()