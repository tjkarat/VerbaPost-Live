import streamlit as st
import time
import os
import hashlib
from datetime import datetime

# --- CRITICAL IMPORTS ---
# We import database explicitly. If this fails, the app should show the error.
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
# --- NEW: SECRETS MANAGER FOR ADMIN CHECK ---
try: import secrets_manager
except ImportError: secrets_manager = None

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


# --- HELPER: SAFE PROFILE GETTER ---
def get_profile_field(profile, field, default=""):
    """Safely retrieves fields from profile whether it's a dict or None."""
    if not profile: return default
    if isinstance(profile, dict): return profile.get(field, default)
    # Fallback if somehow it's still an object
    return getattr(profile, field, default)

def _ensure_profile_loaded():
    """
    Forces profile load AND syncs it to session state inputs.
    This fixes the 'Autopopulate not working' issue.
    """
    if st.session_state.get("authenticated") and not st.session_state.get("profile_synced"):
        try:
            email = st.session_state.get("user_email")
            # Now returns a DICT, which is safe from 'DetachedInstanceError'
            profile = database.get_user_profile(email)
            if profile:
                st.session_state.user_profile = profile
                
                # FORCE UPDATE SESSION STATE KEYS
                # This overrides whatever Streamlit has cached in the input widgets
                st.session_state.from_name = get_profile_field(profile, "full_name")
                st.session_state.from_street = get_profile_field(profile, "address_line1")
                st.session_state.from_city = get_profile_field(profile, "address_city")
                st.session_state.from_state = get_profile_field(profile, "address_state")
                st.session_state.from_zip = get_profile_field(profile, "address_zip")
                
                st.session_state.profile_synced = True # Mark as done so we don't overwrite user edits later
                st.rerun()
        except Exception as e:
            st.error(f"Database Error: {e}")

# --- CSS INJECTOR ---
def inject_custom_css(text_size=16):
    """Injects CSS. Fixed the visibility bug by escaping curly braces."""
    st.markdown(f"""
        <style>
        /* Base Text Sizing */
        .stTextArea textarea, .stTextInput input, p, li, .stMarkdown {{
            font-size: {text_size}px !important;
            line-height: 1.6 !important;
        }}
        
        /* Card-like Styling for Pricing */
        .price-card {{
            background-color: #ffffff;
            border-radius: 12px;
            padding: 20px;
            text-align: center;
            border: 1px solid #e0e0e0;
            height: 180px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            display: flex;
            flex-direction: column;
            justify-content: center;
        }}
        .price-header {{
            font-family: 'Helvetica Neue', sans-serif;
            font-weight: 700;
            font-size: 1.3rem;
            color: #333;
            margin-bottom: 5px;
        }}
        .price-tag {{
            font-size: 2.2rem;
            font-weight: 800;
            color: #d93025;
            margin: 5px 0;
        }}
        .price-sub {{
            font-size: 0.85rem;
            font-weight: 600;
            color: #888;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 8px;
        }}
        .price-desc {{
            font-size: 0.9rem;
            color: #666;
            line-height: 1.4;
        }}

        /* Tab Styling */
        .stTabs [data-baseweb="tab"] p {{
            font-size: 1.2rem !important;
            font-weight: 600 !important;
        }}
        .stTabs [data-baseweb="tab"] {{
            height: 60px;
            white-space: pre-wrap;
            background-color: #F0F2F6;
            border-radius: 8px 8px 0px 0px;
            gap: 2px;
            padding: 10px;
            border: 1px solid #ccc;
            border-bottom: none;
            color: #333;
        }}
        .stTabs [aria-selected="true"] {{
            background-color: #FF4B4B !important;
            border: 1px solid #FF4B4B !important;
            color: white !important;
        }}
        .stTabs [aria-selected="true"] p {{
            color: white !important;
        }}
        
        /* Instruction Box */
        .instruction-box {{
            background-color: #FEF3C7;
            border-left: 6px solid #F59E0B;
            padding: 15px;
            margin-bottom: 20px;
            border-radius: 4px;
            color: #000;
        }}
        
        /* FIX: Double Curly Braces to escape f-string */
        #MainMenu {{visibility: hidden;}}
        footer {{visibility: hidden;}}
        </style>
    """, unsafe_allow_html=True)


# --- HELPER FUNCTIONS ---
def reset_app_state():
    """Clears session state for a fresh start, keeping auth."""
    keys_to_keep = ["authenticated", "user_email", "user_name", "user_role", "user_profile", "profile_synced"]
    for key in list(st.session_state.keys()):
        if key not in keys_to_keep:
            del st.session_state[key]
    st.rerun()

def load_address_book():
    """Fetches contacts from DB if logged in."""
    if not st.session_state.get("authenticated"):
        return {}
    try:
        user_email = st.session_state.get("user_email")
        # contacts is now a list of dicts from the updated database.py
        contacts = database.get_contacts(user_email)
        result = {}
        for c in contacts:
            # Safely access dict keys
            name = c.get('name', '')
            city = c.get('city', 'Unknown')
            # Create a label for the dropdown
            label = f"{name} ({city})"
            result[label] = c
        return result
    except Exception as e:
        print(f"Address Book Error: {e}")
        return {}

def _handle_draft_creation(email, tier, price):
    """Ensures a draft exists in the DB before payment."""
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
    """Step 1: The Store (Pricing & Tier Selection)."""
    inject_custom_css(16)
    
    u_email = st.session_state.get("user_email", "")
    
    # Auth Guard
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
        st.info("📢 **Campaign Mode:** Upload a CSV to send letters to hundreds of people.")
        render_campaign_uploader()
        return

    # --- PRICING GRID LAYOUT ---
    
    c1, c2, c3, c4 = st.columns(4)
    
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
        st.markdown(html_card("Standard", "One Letter", "2.99", "Premium paper. Standard #10 Envelope."), unsafe_allow_html=True)
    with c2:
        st.markdown(html_card("Heirloom", "One Letter", "5.99", "Heavy cream paper. Wax seal effect."), unsafe_allow_html=True)
    with c3:
        st.markdown(html_card("Civic", "3 Letters", "6.99", "Write to Congress. We find your 3 reps automatically."), unsafe_allow_html=True)
    with c4:
        st.markdown(html_card("Santa", "One Letter", "9.99", "North Pole Postmark. Golden Ticket. Magical."), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True) 
    b1, b2, b3, b4 = st.columns(4)
    
    def select_tier(tier, price):
        st.session_state.locked_tier = tier
        st.session_state.locked_price = price
        _handle_draft_creation(u_email, tier, price)
        st.session_state.app_mode = "workspace"
        st.rerun()

    with b1:
        st.button("Select Standard", use_container_width=True, on_click=select_tier, args=("Standard", 2.99))
    with b2:
        st.button("Select Heirloom", use_container_width=True, on_click=select_tier, args=("Heirloom", 5.99))
    with b3:
        st.button("Select Civic", use_container_width=True, on_click=select_tier, args=("Civic", 6.99))
    with b4:
        st.button("Select Santa", use_container_width=True, on_click=select_tier, args=("Santa", 9.99))


def render_campaign_uploader():
    """Handles CSV upload for Bulk Tier."""
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
        
        # Calculate Bulk Price
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
    _ensure_profile_loaded()

    col_slide, col_gap = st.columns([1, 2])
    with col_slide:
        text_size = st.slider("Text Size", 12, 24, 16, help="Adjust text size")
    inject_custom_css(text_size)

    current_tier = st.session_state.get('locked_tier', 'Draft')
    st.markdown(f"## 📝 Workspace: {current_tier}")

    # --- STEP 2: ADDRESSING ---
    with st.expander("📍 Step 2: Addressing", expanded=True):
        st.info("💡 **Tip:** Hit 'Save Addresses' to lock them in.")
        
        # 1. Address Book Visibility (Hidden for Civic/Santa)
        if st.session_state.get("authenticated") and current_tier not in ["Civic", "Santa"]:
            addr_opts = load_address_book()
            if addr_opts:
                col_load, col_empty = st.columns([2, 1])
                with col_load:
                    selected_contact = st.selectbox("📂 Load Saved Contact", ["Select..."] + list(addr_opts.keys()))
                    
                    if selected_contact != "Select..." and selected_contact != st.session_state.get("last_loaded_contact"):
                        data = addr_opts[selected_contact]
                        st.session_state.to_name_input = data.get('name', '')
                        st.session_state.to_street_input = data.get('street', '')
                        st.session_state.to_city_input = data.get('city', '')
                        st.session_state.to_state_input = data.get('state', '')
                        st.session_state.to_zip_input = data.get('zip_code', '') # Fixed key
                        st.session_state.last_loaded_contact = selected_contact
                        st.rerun()

        # 2. Main Form
        with st.form("addressing_form"):
            col_to, col_from = st.columns(2)
            
            # --- "To" Logic ---
            with col_to:
                st.markdown("### To: (Recipient)")
                
                # CIVIC TIER SPECIAL
                if current_tier == "Civic" and civic_engine:
                    st.info("ℹ️ We will send 3 letters: One to your Rep, and two to your Senators.")
                    
                    if st.form_submit_button("🏛️ Find My Representatives"):
                        # Use the FROM address to look up
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

                # STANDARD/HEIRLOOM Logic
                else:
                    st.text_input("Name", key="to_name_input")
                    st.text_input("Street Address", key="to_street_input")
                    st.text_input("City", key="to_city_input")
                    c_s, c_z = st.columns(2)
                    c_s.text_input("State", key="to_state_input")
                    c_z.text_input("Zip", key="to_zip_input")

            # --- "From" Logic ---
            with col_from:
                st.markdown("### From: (Return Address)")
                
                # These keys are auto-populated by _ensure_profile_loaded
                st.text_input("Your Name", key="from_name")
                st.text_input("Signature (Sign-off)", key="from_sig")
                st.text_input("Your Street", key="from_street")
                st.text_input("Your City", key="from_city")
                c_fs, c_fz = st.columns(2)
                c_fs.text_input("Your State", key="from_state")
                c_fz.text_input("Your Zip", key="from_zip")
            
            # --- Save Button ---
            # FIX: Only show save button for non-Civic tiers to avoid form confusion
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
                    
                    d_id = st.session_state.get("current_draft_id")
                    if d_id:
                        database.update_draft_data(d_id, to_addr=st.session_state.addr_to, from_addr=st.session_state.addr_from)
                    
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
                                st.success("✅ Addresses Verified & Saved!")
                    else:
                        st.session_state.addresses_saved_at = time.time()
                        st.success("✅ Addresses Saved (Verification Offline)")
        
        if st.session_state.get("addresses_saved_at") and time.time() - st.session_state.addresses_saved_at < 10:
            st.success("✅ Your addresses are saved and ready!")

    st.divider()

    # --- STEP 3: COMPOSE ---
    st.markdown("## ✍️ Step 3: Write Your Letter")
    
    # NEW INSTRUCTIONS (As Requested)
    st.info("🎙️ **Voice Instructions:** Click the small microphone icon below. Speak for up to 5 minutes. Click the square 'Stop' button when finished.")

    tab_type, tab_rec = st.tabs(["⌨️ TYPE", "🎙️ SPEAK"])

    with tab_type:
        st.markdown("### ⌨️ Typing Mode")
        current_text = st.session_state.get("letter_body", "")
        # Using placeholder to detect changes
        new_text = st.text_area("Letter Body", value=current_text, height=400, label_visibility="collapsed", placeholder="Dear...")
        
        col_polish, col_undo = st.columns([1, 1])
        with col_polish:
            if st.button("✨ AI Polish (Professional)"):
                if new_text and ai_engine:
                    with st.spinner("Polishing..."):
                        try:
                            # Save history
                            if "letter_body_history" not in st.session_state: st.session_state.letter_body_history = []
                            st.session_state.letter_body_history.append(new_text)
                            
                            polished = ai_engine.refine_text(new_text, style="Professional")
                            if polished:
                                st.session_state.letter_body = polished
                                st.rerun()
                        except Exception as e: st.error(f"AI Error: {e}")
        
        with col_undo:
            if "letter_body_history" in st.session_state and len(st.session_state.letter_body_history) > 0:
                if st.button("↩️ Undo Last Change"):
                    st.session_state.letter_body = st.session_state.letter_body_history.pop()
                    st.rerun()

        # Autosave Logic
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
                st.info("⏳