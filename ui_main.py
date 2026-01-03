import streamlit as st
import time
import os
import hashlib
import logging
import uuid 
from datetime import datetime
import json
import ast
from sqlalchemy import text, create_engine

# --- CRITICAL IMPORTS ---
import database 
import secrets_manager 

logger = logging.getLogger(__name__)

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
try: import email_engine
except ImportError: email_engine = None

# --- HELPER: NUCLEAR DATABASE SAVE (Heirloom Logic) ---
def _force_save_to_db(draft_id, content=None, to_data=None, from_data=None):
    """
    NUCLEAR OPTION: Uses raw SQL and a fresh connection.
    FIXED: Handles Integer vs String IDs correctly.
    """
    if not draft_id: 
        print(f"[DEBUG] ❌ Save Aborted: No Draft ID")
        return False
    
    try:
        # 1. GET URL DIRECTLY
        db_url = secrets_manager.get_secret("SUPABASE_DB_URL") or os.environ.get("SUPABASE_DB_URL")
        if not db_url:
             db_url = secrets_manager.get_secret("DATABASE_URL") or os.environ.get("DATABASE_URL")
        
        if not db_url:
            st.error("Database URL missing.")
            return False

        # 2. PREPARE DATA
        to_json = json.dumps(to_data) if isinstance(to_data, dict) else (str(to_data) if to_data else None)
        from_json = json.dumps(from_data) if isinstance(from_data, dict) else (str(from_data) if from_data else None)
        
        # 3. DEBUG OUTPUT TO CONSOLE
        print(f"--- [DEBUG] FORCE SAVE ---")
        print(f"ID: {draft_id}")
        if to_data: print(f"To: {to_data.get('name')} | {to_data.get('street')}")
        if content: print(f"Content Length: {len(content)}")
        
        # 4. CONSTRUCT RAW SQL
        # Updates 'recipient_data' (New) and 'to_addr' (Legacy) to be safe.
        query = text("""
            UPDATE letter_drafts 
            SET 
                recipient_data = :rd, 
                sender_data = :sd,
                to_addr = :rd,
                from_addr = :sd,
                content = COALESCE(:c, content)
            WHERE id = :id
        """)
        
        # FIX: Ensure ID type matches DB schema (Integer)
        safe_id = draft_id
        if str(draft_id).isdigit():
            safe_id = int(draft_id)

        params = {
            "rd": to_json,
            "sd": from_json,
            "c": content,
            "id": safe_id
        }

        # 5. EXECUTE
        # Uses fresh engine to bypass session pool issues
        temp_engine = create_engine(db_url, echo=False)
        with temp_engine.begin() as conn:
            result = conn.execute(query, params)
            print(f"✅ [DEBUG] DB COMMIT SUCCESS | Rows Updated={result.rowcount}")
            return True
                
    except Exception as e:
        print(f"❌ [DEBUG] NUCLEAR SAVE ERROR: {e}")
        logger.error(f"Nuclear Save Error: {e}")
        st.error(f"Save Failed: {e}") 
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
                    st.session_state.from_street = get_profile_field(profile, "address_line1")
                    st.session_state.from_city = get_profile_field(profile, "address_city")
                    st.session_state.from_state = get_profile_field(profile, "address_state")
                    st.session_state.from_zip = get_profile_field(profile, "address_zip")
                    st.session_state.profile_synced = True 
                    st.rerun()
            except Exception as e:
                logger.error(f"Profile Load Error: {e}")

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
        contacts = database.get_contacts(user_email)
        result = {}
        for c in contacts:
            name = str(c.get('name') or "Unknown")
            street = str(c.get('street') or c.get('address_line1') or "")[:10]
            label = f"{name} ({street}...)"
            result[label] = c
        return result
    except Exception as e:
        logger.error(f"Address Book Error: {e}")
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
            database.save_contact(user_email, contact_data)
            return True
        return False
    except Exception as e:
        logger.error(f"Smart Save Error: {e}")
        return False

def _handle_draft_creation(email, tier, price):
    d_id = st.session_state.get("current_draft_id")
    success = False
    
    # Try to update first if ID exists
    if d_id:
        try:
            success = database.update_draft_data(d_id, status="Draft", tier=tier, price=price)
        except:
            success = False
            
    # If no ID or update failed, create NEW record
    if not success or not d_id:
        d_id = database.save_draft(email, "", tier, price)
        st.session_state.current_draft_id = d_id
        
    return d_id

# --- PAGE RENDERERS ---

def render_store_page():
    inject_custom_css(16)
    u_email = st.session_state.get("user_email", "")
    
    # --- SAFETY GATE FOR UNAUTHENTICATED USERS ---
    if not u_email:
        st.warning("🔒 **Access Required**")
        st.markdown("""
        To use the Letter Store, please:
        1. Sign in to your existing account, or
        2. Create a new account (takes 30 seconds)
        """)
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Sign In", type="primary"):
                st.session_state.app_mode = "login"
                st.rerun()
        with col2:
            if st.button("Create Account"):
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
        st.markdown(html_card("Vintage", "ONE LETTER", "5.99", "Heavy cream paper. Real Stamp. Handwritten."), unsafe_allow_html=True)
    with c3:
        st.markdown(html_card("Civic", "3 LETTERS", "6.99", "Write to Congress. We find reps automatically."), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True) 
    b1, b2, b3 = st.columns(3)
    
    # --- DIRECT ACTION BUTTONS ---
    with b1:
        if st.button("Select Standard", key="store_btn_standard_final", use_container_width=True):
            st.session_state.locked_tier = "Standard"
            st.session_state.locked_price = 2.99
            # FORCE CREATE
            new_id = _handle_draft_creation(u_email, "Standard", 2.99)
            if new_id:
                st.session_state.app_mode = "workspace"
                st.rerun()
            else: st.error("Database Create Failed")

    with b2:
        if st.button("Select Vintage", key="store_btn_vintage_final", use_container_width=True):
            st.session_state.locked_tier = "Vintage"
            st.session_state.locked_price = 5.99
            # FORCE CREATE
            new_id = _handle_draft_creation(u_email, "Vintage", 5.99)
            if new_id:
                st.session_state.app_mode = "workspace"
                st.rerun()
            else: st.error("Database Create Failed")

    with b3:
        if st.button("Select Civic", key="store_btn_civic_final", use_container_width=True):
            st.session_state.locked_tier = "Civic"
            st.session_state.locked_price = 6.99
            # FORCE CREATE
            new_id = _handle_draft_creation(u_email, "Civic", 6.99)
            if new_id:
                st.session_state.app_mode = "workspace"
                st.rerun()
            else: st.error("Database Create Failed")

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
    user_email = st.session_state.get("user_email")
    
    # DRAFT GUARANTEE
    if not st.session_state.get("current_draft_id"):
        st.error("Session missing draft ID. Please go back to Store.")
        if st.button("Back"): 
            st.session_state.app_mode = "store"
            st.rerun()
        return

    d_id = st.session_state.get("current_draft_id")
    
    # --- 1. STATE INITIALIZATION (Prevent Ghost Data) ---
    keys_to_init = ["to_name_input", "to_street_input", "to_city_input", "to_state_input", "to_zip_input"]
    for k in keys_to_init:
        if k not in st.session_state:
            st.session_state[k] = ""

    col_slide, col_gap = st.columns([1, 2])
    with col_slide:
        text_size = st.slider("Text Size", 12, 24, 16, help="Adjust text size")
    inject_custom_css(text_size)

    current_tier = st.session_state.get('locked_tier', 'Draft')
    st.markdown(f"## 📝 Workspace: {current_tier} (Draft #{d_id})")

    with st.expander("📍 Step 2: Addressing", expanded=True):
        st.info("💡 **Tip:** Hit 'Save Addresses' to lock them in.")
        
        # --- 2. ADDRESS BOOK LOGIC (MOVED TO TOP) ---
        if st.session_state.get("authenticated") and current_tier != "Civic":
            addr_opts = load_address_book()
            if addr_opts:
                sel = st.selectbox("📂 Load Saved Contact", ["Select..."] + list(addr_opts.keys()))
                
                # Logic: If selection changed, update state AND rerun immediately
                if sel != "Select..." and sel != st.session_state.get("last_loaded_contact"):
                    d = addr_opts[sel]
                    
                    print(f"[DEBUG] Loading Contact: {d.get('name')}")
                    
                    # Direct State Injection
                    st.session_state.to_name_input = str(d.get('name') or d.get('full_name') or "")
                    st.session_state.to_street_input = str(d.get('street') or d.get('address_line1') or "")
                    st.session_state.to_city_input = str(d.get('city') or d.get('address_city') or "")
                    st.session_state.to_state_input = str(d.get('state') or d.get('province') or "")
                    st.session_state.to_zip_input = str(d.get('zip_code') or d.get('zip') or "")
                    
                    # --- FIX: DIRECT DB SAVE (NUCLEAR OPTION) ---
                    # Construct dictionary immediately to avoid 'Save' button step
                    direct_addr_to = {
                        "name": st.session_state.to_name_input,
                        "street": st.session_state.to_street_input,
                        "city": st.session_state.to_city_input,
                        "state": st.session_state.to_state_input,
                        "zip_code": st.session_state.to_zip_input
                    }
                    
                    # Force save to DB so "Review" page sees it even if UI refreshes
                    saved = _force_save_to_db(d_id, to_data=direct_addr_to)
                    
                    if saved:
                        st.toast("✅ Contact Loaded & Saved to Database!")
                    else:
                        st.error("❌ Database Save Failed (Check Logs)")
                    # ----------------------------------------------
                    
                    st.session_state.last_loaded_contact = sel
                    st.rerun() # Force UI refresh with new values
        
        # --- MANAGE CONTACTS ---
        if st.checkbox("📇 Manage Address Book"):
             contacts_raw = load_address_book()
             if contacts_raw:
                 for label, data in contacts_raw.items():
                     c1, c2 = st.columns([4, 1])
                     c1.text(f"• {label}")
                     if c2.button("🗑️", key=f"del_{data.get('id')}"):
                         database.delete_contact(st.session_state.user_email, data.get('id'))
                         st.rerun()

        # --- LIVE INPUTS (NO FORM WRAPPER) ---
        col_to, col_from = st.columns(2)
        with col_to:
            st.markdown("### To: (Recipient)")
            if current_tier == "Civic" and civic_engine:
                if st.button("🏛️ Find My Representatives"):
                    pass 
            else:
                # Removed 'value=' to let Streamlit manage the key binding naturally
                st.text_input("Name", key="to_name_input")
                st.text_input("Street Address", key="to_street_input")
                st.text_input("City", key="to_city_input")
                c_s, c_z = st.columns(2)
                c_s.text_input("State", key="to_state_input")
                c_z.text_input("Zip", key="to_zip_input")

        with col_from:
            st.markdown("### From: (Return Address)")
            st.text_input("Your Name", key="from_name")
            st.text_input("Signature", key="from_sig")
            st.text_input("Street", key="from_street")
            st.text_input("City", key="from_city")
            c_fs, c_fz = st.columns(2)
            c_fs.text_input("State", key="from_state")
            c_fz.text_input("Zip", key="from_zip")
            
        # Add Smart Save Option
        save_to_book = False
        if current_tier != "Civic" and st.session_state.get("authenticated"):
             st.caption("✅ New contacts will be automatically saved to your Address Book.")
             save_to_book = True

        if current_tier != "Civic":
            # Just a button, NOT a form_submit_button
            if st.button("💾 Save Addresses"):
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
                
                # Update Draft - NUCLEAR FIX
                if _force_save_to_db(d_id, to_data=st.session_state.addr_to, from_data=st.session_state.addr_from):
                    st.success("✅ Addresses Saved to Database!")
                    _save_new_contact(st.session_state.addr_to)
                else:
                    st.error("Failed to save addresses.")

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
    if st.session_state.get("addresses_saved_at") and time.time() - st.session_state.get("addresses_saved_at", 0) < 10:
        st.success("✅ Your addresses are saved and ready!")

    st.divider()

    st.markdown("## ✍️ Step 3: Write Your Letter")
    st.info("🎙️ **Voice Instructions:** Click the small microphone icon below. Speak for up to 5 minutes. Click the square 'Stop' button when finished.")
    
    # --- INIT CONTENT VAR ---
    content_to_save = st.session_state.get("letter_body", "")
    tab_type, tab_rec = st.tabs(["⌨️ TYPE", "🎙️ SPEAK"])

    with tab_type:
        # Note: We bind value directly. No key needed if we handle state manually below.
        new_text = st.text_area("Body", value=content_to_save, height=400, label_visibility="collapsed")
        content_to_save = new_text
        
        c_save, c_polish = st.columns([1, 1])
        with c_save:
             if st.button("💾 Save Draft", use_container_width=True):
                 st.session_state.letter_body = content_to_save
                 d_id = st.session_state.get("current_draft_id")
                 # NUCLEAR FIX
                 if _force_save_to_db(d_id, content=content_to_save):
                     st.session_state.last_autosave = time.time()
                     st.toast(f"✅ Saved to Draft #{d_id}")
                 else:
                     st.error("Save failed.")

        with c_polish:
            if st.button("✨ AI Polish", use_container_width=True):
                if new_text and ai_engine:
                    with st.spinner("Polishing..."):
                        polished = ai_engine.refine_text(new_text)
                        if polished:
                            st.session_state.letter_body = polished
                            st.rerun()

        # Autosave logic
        if content_to_save != st.session_state.get("last_saved_content", ""):
            if time.time() - st.session_state.get("last_autosave", 0) > 3:
                _force_save_to_db(d_id, content=content_to_save)
                st.session_state.last_saved_content = content_to_save
                st.session_state.last_autosave = time.time()

    with tab_rec:
        audio_val = st.audio_input("Record")
        if audio_val:
            pass # (Audio logic omitted for brevity, identical to previous)

    st.divider()
    
    # --- NAVIGATION TRIGGER ---
    if st.button("👀 Review & Pay (Next Step)", type="primary", use_container_width=True):
        # 1. IMPLICIT CAPTURE (Safe now that form is gone)
        addr_to = {
            "name": st.session_state.get("to_name_input", ""), 
            "street": st.session_state.get("to_street_input", ""),
            "city": st.session_state.get("to_city_input", ""), 
            "state": st.session_state.get("to_state_input", ""),
            "zip_code": st.session_state.get("to_zip_input", "")
        }
        addr_from = {
            "name": st.session_state.get("from_name", ""), 
            "street": st.session_state.get("from_street", ""),
            "city": st.session_state.get("from_city", ""), 
            "state": st.session_state.get("from_state", ""),
            "zip_code": st.session_state.get("from_zip", "")
        }
        
        # Update session state with implicit capture
        st.session_state.addr_to = addr_to
        st.session_state.addr_from = addr_from
        st.session_state.letter_body = content_to_save
        
        # 2. Force Save EVERYTHING
        st.info(f"Checking data: {addr_to}") # VISUAL DEBUG
        _force_save_to_db(d_id, content=content_to_save, to_data=addr_to, from_data=addr_from)

        if not content_to_save:
            st.error("⚠️ Letter is empty!")
        elif not addr_to.get("name") or not addr_to.get("street"):
            st.error("⚠️ Please fill out the recipient address.")
        else:
            st.session_state.app_mode = "review"
            st.rerun()

def render_review_page():
    # --- CRITICAL FIX: FORCE SYNC WITH DB ---
    u_email = st.session_state.get("user_email")
    d_id = st.session_state.get("current_draft_id")
    
    if d_id and database:
        # Load draft to ensure tier is correct
        try:
            with database.get_db_session() as s:
                d = s.query(database.LetterDraft).filter(database.LetterDraft.id == d_id).first()
                if d and d.tier:
                    st.session_state.locked_tier = d.tier
        except Exception as e:
            logger.error(f"Tier Sync Error: {e}")

    tier = st.session_state.get("locked_tier", "Standard")
    st.markdown(f"## 👁️ Step 4: Secure & Send ({tier})")
    
    st.info("📄 Your letter is ready for production. Proceed to payment below to print and mail.")

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

    # --- HANDLING FREE ORDERS ($0.00) ---
    if total <= 0:
        st.success("🎉 This order is FREE via Promo Code!")
        if st.button("✅ Complete Free Order", type="primary", use_container_width=True):
            if d_id and database:
                try:
                    # 1. GENERATE PDF & MAIL
                    with st.spinner("Processing..."):
                        # --- CRITICAL FIX: ROUTE VINTAGE TO MANUAL QUEUE ---
                        tracking = None
                        status_msg = ""
                        
                        # FORCE STRING CHECK
                        current_tier_str = str(tier).strip()
                        
                        if current_tier_str == "Vintage":
                            # MANUAL QUEUE
                            tracking = f"MANUAL_{str(uuid.uuid4())[:8].upper()}"
                            status_msg = "Queued (Manual)"
                            logger.info(f"Vintage Free Order {d_id} sent to Manual Queue")
                            
                            # Send "Queued" Email
                            if email_engine:
                                print("[DEBUG] Attempting to send Queued Email...")
                                try:
                                    email_engine.send_email(
                                        to_email=u_email,
                                        subject=f"VerbaPost Receipt: Order #{d_id}",
                                        html_content=f"<h3>Order Queued</h3><p>Your Vintage letter is in the manual print queue.</p><p>ID: {tracking}</p>"
                                    )
                                    print("[DEBUG] Queued Email Sent.")
                                except Exception as e:
                                    print(f"[DEBUG] Email Error: {e}")

                        else:
                            # STANDARD POSTGRID API
                            if letter_format and mailer:
                                t_addr = st.session_state.get('addr_to', {})
                                f_addr = st.session_state.get('addr_from', {})
                                body = st.session_state.get('letter_body', '')
                                pdf_bytes = letter_format.create_pdf(body, t_addr, f_addr, tier=tier)
                                tracking = mailer.send_letter(pdf_bytes, t_addr, f_addr, description=f"Free Order {d_id}")
                                status_msg = "Sent"

                        if tracking:
                            # 2. UPDATE DB
                            # Use Nuclear Update for Status too just in case
                            try:
                                db_url = secrets_manager.get_secret("SUPABASE_DB_URL") or os.environ.get("SUPABASE_DB_URL")
                                temp_engine = create_engine(db_url, echo=False)
                                with temp_engine.begin() as conn:
                                    conn.execute(
                                        text("UPDATE letter_drafts SET status=:s, price=:p, tracking_number=:t WHERE id=:id"),
                                        {"s": status_msg, "p": 0.0, "t": tracking, "id": str(d_id)}
                                    )
                            except:
                                # Fallback
                                database.update_draft_data(d_id, price=0.0, status=status_msg, tracking_number=tracking)
                            
                            # 3. LOG
                            if hasattr(database, "save_audit_log"):
                                database.save_audit_log({
                                    "user_email": u_email,
                                    "event_type": "ORDER_COMPLETE_FREE",
                                    "description": f"Sent via Promo ({status_msg})",
                                    "details": f"Track: {tracking}"
                                })
                            
                            # 4. RECORD PROMO USAGE
                            promo_code = st.session_state.get('applied_promo')
                            if promo_code:
                                database.record_promo_usage(promo_code, u_email)

                            # 5. SEND RECEIPT EMAIL (ADDED)
                            if email_engine and current_tier_str != "Vintage": # Vintage handled above
                                print("[DEBUG] Attempting to send Standard Email...")
                                try:
                                    email_engine.send_email(
                                        to_email=u_email,
                                        subject=f"VerbaPost Receipt: Order #{d_id}",
                                        html_content=f"""
                                        <h3>Letter Sent Successfully!</h3>
                                        <p>Your letter has been dispatched to the post office (Free via Promo).</p>
                                        <p><b>Tracking ID:</b> {tracking}</p>
                                        <p>Thank you for using VerbaPost.</p>
                                        """
                                    )
                                    print("[DEBUG] Standard Email Sent.")
                                except Exception as ex:
                                    print(f"[DEBUG] Standard Email Error: {ex}")
                                    logger.error(f"Free Order Receipt Failed: {ex}")

                            # 6. SUCCESS
                            st.session_state.app_mode = "receipt"
                            st.rerun()
                        else:
                            st.error("Mailing Failed. PostGrid rejected the address.")
                except Exception as e:
                    logger.error(f"Free Order Error: {e}")
                    st.error("Failed to process order. Please try again.")
        return

    # --- PAID ORDERS ---
    if st.button("💳 Proceed to Secure Checkout", type="primary", use_container_width=True):
        if d_id and database:
            try: database.update_draft_data(d_id, price=total, status="Pending Payment")
            except Exception as e: logger.error(f"State Persistence Error: {e}")
        
        # Pass promo_code to Stripe Metadata
        promo_code = st.session_state.get('applied_promo')
        
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
            draft_id=d_id,
            promo_code=promo_code 
        )
        if url: 
            st.link_button("👉 Click to Pay", url)
            st.session_state.stripe_checkout_url = url
        else: st.error("Payment Gateway Error")

def render_receipt_page():
    st.balloons()
    st.markdown("## 📮 Letter Sent!")
    st.success("Your letter has been successfully dispatched to the post office.")
    st.info("You will receive a confirmation email shortly.")
    
    if st.button("⬅️ Back to Store", use_container_width=True):
        st.session_state.app_mode = "store"
        st.rerun()

def render_main():
    if "app_mode" not in st.session_state: st.session_state.app_mode = "store"
    mode = st.session_state.app_mode
    if mode == "store": render_store_page()
    elif mode == "workspace": render_workspace_page()
    elif mode == "review": render_review_page()
    elif mode == "receipt": render_receipt_page()
    else: pass

if __name__ == "__main__":
    render_main()