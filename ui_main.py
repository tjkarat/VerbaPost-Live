import streamlit as st
import time
import os
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
# We wrap these in try/except to prevent the app from crashing 
# if a single module is missing or has a syntax error.
try:
    import ui_splash
except ImportError:
    ui_splash = None

try:
    import ui_login
except ImportError:
    ui_login = None

try:
    import ui_admin
except ImportError:
    ui_admin = None

try:
    import ui_legal
except ImportError:
    ui_legal = None

try:
    import ui_legacy
except ImportError:
    ui_legacy = None

# --- ACCESSIBILITY CSS INJECTOR ---
def inject_accessibility_css():
    """
    Injects CSS to make tabs larger, high-contrast, and button-like.
    Designed for better accessibility (Fitts's Law + Vision).
    """
    st.markdown("""
        <style>
        /* 1. Make the Tab Text Huge and Bold */
        .stTabs [data-baseweb="tab"] p {
            font-size: 1.5rem !important;
            font-weight: 700 !important;
        }

        /* 2. Turn Tabs into Large Buttons with Outlines */
        .stTabs [data-baseweb="tab"] {
            height: 70px;
            white-space: pre-wrap;
            background-color: #F0F2F6;
            border-radius: 10px 10px 0px 0px;
            gap: 2px;
            padding-top: 10px;
            padding-bottom: 10px;
            border: 3px solid #9CA3AF; /* Thick Grey Outline */
            margin-right: 5px;
            color: #374151; /* Dark text for unselected */
        }

        /* 3. High Contrast for Selected Tab (Red Background, White Text) */
        .stTabs [aria-selected="true"] {
            background-color: #FF4B4B !important;
            border: 3px solid #FF4B4B !important;
            color: white !important;
        }
        
        /* 4. Force text color to white inside the active tab */
        .stTabs [aria-selected="true"] p {
            color: white !important;
        }

        /* 5. Improve Instruction Box Visibility */
        .instruction-box {
            background-color: #FEF3C7; /* Pale Yellow */
            border-left: 10px solid #F59E0B; /* Orange Accent */
            padding: 20px;
            margin-bottom: 25px;
            font-size: 20px;
            font-weight: 500;
            color: #000000;
        }
        </style>
    """, unsafe_allow_html=True)

# --- HELPER FUNCTIONS ---

def reset_app_state():
    """Clears session state for a fresh start."""
    keys_to_keep = ["authenticated", "user_email", "user_name", "user_role"]
    for key in list(st.session_state.keys()):
        if key not in keys_to_keep:
            del st.session_state[key]
    st.rerun()

def _handle_draft_creation(email, tier, price):
    """
    Ensures a draft exists in the DB before payment.
    Handles 'Ghost Drafts' where the DB row might be missing but session persists.
    """
    d_id = st.session_state.get("current_draft_id")
    success = False
    
    # Try to update existing
    if d_id and database:
        success = database.update_draft_data(d_id, status="Draft", tier=tier, price=price)
    
    # If update failed (row missing) or no draft ID, create new
    if not success and database:
        d_id = database.save_draft(email, "", tier, price)
        st.session_state.current_draft_id = d_id
    
    return d_id

# --- CORE PAGE RENDERERS ---

def render_store_page():
    """Step 1: The Store (Pricing & Tier Selection)"""
    # 1. Auth Guard
    u_email = st.session_state.get("user_email", "")
    if not u_email:
        st.warning("⚠️ Session Expired. Please log in to continue.")
        if st.button("Go to Login"):
            st.session_state.app_mode = "login"
            st.rerun()
        return

    st.markdown("## 📮 Choose Your Letter Service")
    
    # 2. Campaign Mode Toggle
    mode = st.radio("Mode", ["Single Letter", "Bulk Campaign"], horizontal=True, label_visibility="collapsed")
    
    if mode == "Bulk Campaign":
        st.info("📢 **Campaign Mode:** Upload a CSV to send letters to hundreds of people at once.")
        render_campaign_uploader()
        return

    # 3. Standard Pricing Cards
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
    """Handles CSV upload for Bulk Tier."""
    st.markdown("### 📁 Upload Recipient List (CSV)")
    
    uploaded_file = st.file_uploader("Upload CSV", type=["csv"])
    if uploaded_file:
        contacts = bulk_engine.parse_csv(uploaded_file)
        
        if not contacts:
            st.error("❌ Could not parse CSV. Please check format.")
            return

        st.success(f"✅ Loaded {len(contacts)} recipients.")
        
        # Calculate Bulk Price
        total = pricing_engine.calculate_total("Campaign", qty=len(contacts))
        st.metric("Estimated Total", f"${total}")
        
        if st.button("Proceed with Campaign"):
            st.session_state.locked_tier = "Campaign"
            st.session_state.bulk_targets = contacts
            st.session_state.app_mode = "workspace"
            st.rerun()

def render_workspace_page():
    """Step 2 & 3: Composition & Addressing (ACCESSIBLE VERSION)"""
    inject_accessibility_css()

    st.markdown(f"## 📝 Workspace: {st.session_state.get('locked_tier', 'Draft')}")

    # --- STEP 2: ADDRESSING ---
    with st.expander("📍 Step 2: Addressing", expanded=True):
        st.info("💡 **Tip:** Hit 'Save Addresses' to lock them in.")
        
        # We use a form to force browser autofill to sync
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
                # Pre-fill from user profile if available
                u_profile = st.session_state.get("user_profile", {})
                
                f_name = st.text_input("Your Name", value=u_profile.get("full_name",""), key="from_name")
                f_street = st.text_input("Your Street", value=u_profile.get("address_line1",""), key="from_street")
                f_city = st.text_input("Your City", value=u_profile.get("city",""), key="from_city")
                col_fs, col_fz = st.columns(2)
                f_state = col_fs.text_input("Your State", value=u_profile.get("state",""), key="from_state")
                f_zip = col_fz.text_input("Your Zip", value=u_profile.get("zip_code",""), key="from_zip")
            
            # Form Submit Button
            if st.form_submit_button("💾 Save Addresses"):
                # Save to session
                st.session_state.addr_to = {
                    "name": name, "street": street, "city": city, "state": state, "zip": zip_c
                }
                st.session_state.addr_from = {
                    "name": f_name, "street": f_street, "city": f_city, "state": f_state, "zip": f_zip
                }
                
                # Save to DB
                d_id = st.session_state.get("current_draft_id")
                if d_id and database:
                    database.update_draft_data(d_id, to_address=st.session_state.addr_to, from_address=st.session_state.addr_from)
                
                st.success("✅ Addresses Saved!")

    st.divider()

    # --- STEP 3: COMPOSE (ACCESSIBLE VERSION) ---
    st.markdown("## ✍️ Step 3: Write Your Letter")

    # High-Contrast Instruction Box
    st.markdown(
        """
        <div class="instruction-box">
        <b>HOW TO USE:</b><br>
        Click the <b>"RECORD VOICE"</b> tab below if you want to speak.<br>
        Click the <b>"TYPE MANUALLY"</b> tab below if you want to type.
        </div>
        """, 
        unsafe_allow_html=True
    )

    # TABS: Renamed and Styled via CSS
    tab_type, tab_record = st.tabs(["⌨️ TYPE MANUALLY", "🎙️ RECORD VOICE"])

    # -- TAB 1: TYPING --
    with tab_type:
        st.markdown("### ⌨️ Typing Mode")
        st.write("Click in the box below and start typing your letter.")
        
        current_text = st.session_state.get("letter_body", "")
        new_text = st.text_area("Letter Body", value=current_text, height=400, label_visibility="collapsed")
        
        if new_text != current_text:
            st.session_state.letter_body = new_text
            # Auto-save to DB
            d_id = st.session_state.get("current_draft_id")
            if d_id and database:
                database.update_draft_data(d_id, content=new_text)

    # -- TAB 2: RECORDING (Simplified & Enlarged) --
    with tab_record:
        st.markdown("### 🎙️ Voice Mode")
        
        # Explicit HTML Instructions
        st.markdown(
            """
            <div style="font-size: 22px; margin-bottom: 30px; line-height: 1.8; color: #111;">
            <ol>
                <li>Click the <b>Red Microphone</b> icon below.</li>
                <li>Speak your letter clearly.</li>
                <li>We will turn your voice into text automatically.</li>
            </ol>
            </div>
            """, 
            unsafe_allow_html=True
        )

        audio_val = st.audio_input("Record", label_visibility="collapsed")
        
        if audio_val:
            st.info("⏳ Processing your voice... please wait.")
            
            # Save temp file
            tmp_path = f"/tmp/temp_{int(time.time())}.wav"
            with open(tmp_path, "wb") as f:
                f.write(audio_val.getvalue())
            
            try:
                # Transcribe
                text = ai_engine.transcribe_audio(tmp_path)
                
                if text:
                    # Append or Replace? Let's Append to avoid deleting work
                    current = st.session_state.get("letter_body", "")
                    st.session_state.letter_body = (current + "\n\n" + text).strip()
                    
                    # Save to DB
                    d_id = st.session_state.get("current_draft_id")
                    if d_id and database:
                        database.update_draft_data(d_id, content=st.session_state.letter_body)
                    
                    st.success("✅ Audio Transcribed! Switch to 'Type Manually' to see the text.")
                    st.rerun()
                else:
                    st.warning("⚠️ No speech detected. Please try again.")
            
            except Exception as e:
                st.error(f"Error processing audio: {e}")
            
            finally:
                # Cleanup
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)

    st.divider()
    
    # Navigation
    col_l, col_r = st.columns([1, 4])
    with col_r:
        if st.button("👀 Review & Pay (Next Step)", type="primary", use_container_width=True):
            # Final Save check
            if not st.session_state.get("letter_body"):
                st.error("⚠️ Please write or record something before continuing!")
            else:
                st.session_state.app_mode = "review"
                st.rerun()

def render_review_page():
    """Step 4: Secure & Send"""
    st.markdown("## 👁️ Step 4: Secure & Send")
    
    if st.button("📄 Generate PDF Proof"):
        with st.spinner("Generating Proof..."):
            try:
                # Gather Data
                tier = st.session_state.get("locked_tier", "Standard")
                body = st.session_state.get("letter_body", "")
                addr_to = st.session_state.get("addr_to", {})
                addr_from = st.session_state.get("addr_from", {})
                
                # Normalize Addresses
                std_to = address_standard.StandardAddress.from_dict(addr_to)
                std_from = address_standard.StandardAddress.from_dict(addr_from)
                
                # Create PDF
                raw_pdf = letter_format.create_pdf(body, std_to, std_from, tier)
                
                # --- SAFETY CAST: Ensure it is bytes ---
                pdf_bytes = bytes(raw_pdf)
                
                # Display
                import base64
                b64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
                pdf_display = f'<iframe src="data:application/pdf;base64,{b64_pdf}" width="100%" height="500" type="application/pdf"></iframe>'
                st.markdown(pdf_display, unsafe_allow_html=True)
                
                st.session_state.final_pdf = pdf_bytes
            
            except Exception as e:
                st.error(f"PDF Generation Error: {e}")

    st.divider()
    
    # Recalculate Total
    tier = st.session_state.get("locked_tier", "Standard")
    is_cert = st.checkbox("Add Certified Mail Tracking (+$12.00)")
    total = pricing_engine.calculate_total(tier, is_certified=is_cert)
    
    col_pay, col_info = st.columns([2, 1])
    
    with col_info:
        st.markdown(f"### Total: ${total}")
        st.caption("• Archival Bond Paper")
        st.caption("• USPS First Class")
        if is_cert:
            st.caption("• Certified Tracking")
        st.caption("• Digital & Physical Proof")

    with col_pay:
        if st.button("💳 Proceed to Secure Checkout", type="primary", use_container_width=True):
            # Create Stripe Session
            u_email = st.session_state.get("user_email")
            d_id = st.session_state.get("current_draft_id")
            
            # Ensure draft is saved with final price
            if d_id and database:
                database.update_draft_data(d_id, price=total, status="Pending Payment")
            
            url = payment_engine.create_checkout_session(
                line_items=[{
                    "price_data": {
                        "currency": "usd",
                        "product_data": {"name": f"VerbaPost - {tier} Letter"},
                        "unit_amount": int(total * 100),
                    },
                    "quantity": 1,
                }],
                user_email=u_email,
                draft_id=d_id
            )
            
            if url:
                st.link_button("👉 Click to Pay", url)
                st.rerun()
            else:
                st.error("Payment Gateway Error. Please try again.")

# --- ROUTER CONTROLLER ---
def render_application():
    """
    Acts as the main router, switching views based on session state.
    """
    # Initialize app mode if missing
    if "app_mode" not in st.session_state:
        st.session_state.app_mode = "splash"

    mode = st.session_state.app_mode

    # 1. SPLASH / HERO
    if mode == "splash":
        if ui_splash:
            ui_splash.render_splash_page()
        else:
            st.error("UI Module 'splash' not found.")

    # 2. LOGIN / AUTH
    elif mode == "login":
        if ui_login:
            ui_login.render_login_page()
        else:
            st.error("UI Module 'login' not found.")

    # 3. STORE (Pricing)
    elif mode == "store":
        render_store_page()

    # 4. WORKSPACE (Compose)
    elif mode == "workspace":
        render_workspace_page()

    # 5. REVIEW (Pay)
    elif mode == "review":
        render_review_page()

    # 6. ADMIN
    elif mode == "admin":
        if ui_admin:
            ui_admin.render_admin_page()
        else:
            st.error("UI Module 'admin' not found.")

    # 7. LEGAL
    elif mode == "legal":
        if ui_legal:
            ui_legal.render_legal_page()
        else:
            st.error("UI Module 'legal' not found.")

    # 8. LEGACY (End of Life)
    elif mode == "legacy":
        if ui_legacy:
            ui_legacy.render_legacy_page()
        else:
            st.error("UI Module 'legacy' not found.")

    # Fallback
    else:
        st.warning(f"Unknown App Mode: {mode}")
        if st.button("Reset"):
            reset_app_state()

# --- ENTRY POINT ---
# This is the function called by main.py
# CRITICAL: This was missing in the previous version, causing the crash after payment
def render_main():
    render_application()

# If run directly (for testing), invoke the router
if __name__ == "__main__":
    render_main()