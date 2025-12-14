import streamlit as st
import time
import tempfile
import os
import json
import base64
import hashlib

# --- ROBUST IMPORTS ---
try:
    import database
except ImportError:
    database = None

try:
    import payment_engine
except ImportError:
    payment_engine = None

try:
    import secrets_manager
except ImportError:
    secrets_manager = None

try:
    import letter_format
except ImportError:
    letter_format = None

try:
    import ai_engine
except ImportError:
    ai_engine = None

# --- CSS INJECTOR (ACCESSIBILITY & STYLING) ---
def inject_legacy_accessibility_css():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Caveat&family=Great+Vibes&family=Indie+Flower&family=Schoolbell&display=swap');

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
            color: #374151;
        }

        /* 3. High Contrast for Selected Tab */
        .stTabs [aria-selected="true"] {
            background-color: #FF4B4B !important;
            border: 3px solid #FF4B4B !important;
            color: white !important;
        }
        
        /* 4. Force text color to white inside the active tab */
        .stTabs [aria-selected="true"] p {
            color: white !important;
        }

        /* 5. Font Preview Styling */
        .font-preview-box {
            padding: 20px;
            border: 1px solid #ddd;
            border-radius: 10px;
            background-color: #f9f9f9;
            margin-bottom: 20px;
            text-align: center;
        }
        .fp-Caveat { font-family: 'Caveat', cursive; font-size: 28px; color: #333; }
        .fp-GreatVibes { font-family: 'Great Vibes', cursive; font-size: 32px; color: #333; }
        .fp-IndieFlower { font-family: 'Indie Flower', cursive; font-size: 24px; color: #333; }
        .fp-Schoolbell { font-family: 'Schoolbell', cursive; font-size: 24px; color: #333; }
        
        /* 6. Instruction Box */
        .instruction-box {
            background-color: #FEF3C7;
            border-left: 10px solid #F59E0B;
            padding: 20px;
            margin-bottom: 25px;
            font-size: 20px;
            font-weight: 500;
            color: #000000;
        }
        </style>
    """, unsafe_allow_html=True)

# --- STATE MANAGEMENT ---
def initialize_legacy_state():
    """Ensures all necessary session state variables exist."""
    defaults = {
        "legacy_sender": {},
        "legacy_recipient": {},
        "legacy_text": "",
        "legacy_font": "Caveat",
        "current_legacy_draft_id": None,
        "last_legacy_hash": None,
        "paid_success": False
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

def load_address_book():
    """Fetches contacts from DB and returns a formatted dict for the dropdown."""
    if not database or not st.session_state.get("authenticated"):
        return {}
    
    try:
        user_email = st.session_state.get("user_email")
        contacts = database.get_saved_contacts(user_email)
        # Format: "Name (City)" -> Dict
        return {f"{c['name']} ({c.get('city', 'Unknown')})": c for c in contacts}
    except Exception as e:
        print(f"Address Book Error: {e}")
        return {}

# --- DRAFT SAVING ---
def _save_legacy_draft():
    """Saves the current state to the database."""
    if not database:
        st.error("Database connection missing. Cannot save.")
        return

    user_email = st.session_state.get("user_email", "guest")
    text_content = st.session_state.get("legacy_text", "")
    
    try:
        d_id = st.session_state.get("current_legacy_draft_id")
        
        if d_id:
            # Update existing draft
            # FIX: Changed argument from 'text' to 'content' to match database.py schema
            database.update_draft_data(
                d_id, 
                content=text_content, 
                tier="Legacy", 
                price=15.99
            )
            st.toast("Draft Saved!", icon="💾")
        else:
            # Create new draft
            d_id = database.save_draft(user_email, text_content, "Legacy", 15.99)
            st.session_state.current_legacy_draft_id = d_id
            st.toast("New Draft Created!", icon="✨")
            
    except Exception as e:
        st.error(f"Save failed: {e}")

# --- SUCCESS VIEW (NEW) ---
def render_success_view():
    """
    Displays the confirmation screen after payment.
    This BREAKS the loop where the user goes back to the form.
    """
    st.balloons()
    st.markdown("## ✅ Order Confirmed!")
    
    st.markdown(
        """
        <div style="background-color: #dcfce7; padding: 20px; border-radius: 10px; border: 1px solid #22c55e; margin-bottom: 20px;">
            <h3 style="color: #15803d; margin-top:0;">Secure Delivery Initiated</h3>
            <p>Your legacy letter has been securely generated and is being queued for <b>Certified Mail</b>.</p>
        </div>
        """, unsafe_allow_html=True
    )
    
    # Display the captured email
    email = st.session_state.get("user_email", "your email address")
    st.info(f"We will email the **USPS Tracking Number** to: **{email}**")
    
    st.markdown("---")
    
    if st.button("Start Another Letter"):
        # Reset specific legacy flags but keep auth
        st.session_state.paid_success = False
        st.session_state.current_legacy_draft_id = None
        st.session_state.legacy_text = ""
        st.session_state.last_legacy_hash = None
        st.rerun()

# --- MAIN RENDERER ---
def render_legacy_page():
    # 1. Setup
    initialize_legacy_state()
    inject_legacy_accessibility_css()

    # 2. CHECK: If payment succeeded, show success view immediately
    # This prevents the "Goofy Loop" where the user sees the form again
    if st.session_state.get("paid_success"):
        render_success_view()
        return

    # 3. Header & Controls
    col_head, col_save = st.columns([3, 1])
    with col_head:
        st.markdown("## 🕊️ Legacy Workspace")
    with col_save:
        if st.button("💾 Save Progress", key="btn_save_legacy", use_container_width=True): 
            _save_legacy_draft()

    with st.expander("ℹ️ How this works", expanded=False):
        st.markdown("""
        **Take your time.** This is a space for important, lasting words.
        1.  **Identity:** Verify who this is from and exactly who must sign for it.
        2.  **Style:** Choose a handwriting style that fits your tone.
        3.  **Compose:** Dictate or type your message.
        4.  **Secure:** We generate a PDF proof sent via **Certified Mail**.
        """)

    # RESTORED: Helpful Tip Link
    st.info("💡 **Writer's Block?** The [Stanford Letter Project](https://med.stanford.edu/letter.html) offers excellent templates.")

    # 4. Address Book & Loading
    address_options = load_address_book()
    
    st.markdown("### 📍 Step 1: Delivery Details")
    
    if address_options:
        selected_contact = st.selectbox("📂 Load from Address Book", ["Select..."] + list(address_options.keys()))
        if selected_contact != "Select...":
            data = address_options[selected_contact]
            # Autofill session state variables for the form
            st.session_state.leg_r_name = data.get('name', '')
            st.session_state.leg_r_street = data.get('street', '')
            st.session_state.leg_r_city = data.get('city', '')
            st.session_state.leg_r_state = data.get('state', '')
            st.session_state.leg_r_zip = data.get('zip_code', '') or data.get('zip', '')

    # 5. Address Form
    with st.form("legacy_address_form"):
        c1, c2 = st.columns(2)
        
        # FROM COLUMN
        with c1:
            st.markdown("#### 🏠 From (You)")
            # Try to pre-fill from user profile
            profile = st.session_state.get("user_profile", {})
            
            s_name = st.text_input("Your Name", value=profile.get("full_name", ""), key="leg_s_name")
            s_str = st.text_input("Street Address", value=profile.get("address_line1", ""), key="leg_s_street")
            
            sc1, sc2, sc3 = st.columns(3)
            s_city = sc1.text_input("City", value=profile.get("city", ""), key="leg_s_city")
            s_state = sc2.text_input("State", value=profile.get("state", ""), key="leg_s_state")
            s_zip = sc3.text_input("Zip", value=profile.get("zip_code", ""), key="leg_s_zip")

        # TO COLUMN
        with c2:
            st.markdown("#### 📬 To (Recipient)")
            st.warning("⚠️ Certified Mail: Recipient must sign for delivery.")
            
            r_name = st.text_input("Recipient Name", key="leg_r_name")
            r_str = st.text_input("Street Address", key="leg_r_street")
            
            rc1, rc2, rc3 = st.columns(3)
            r_city = rc1.text_input("City", key="leg_r_city")
            r_state = rc2.text_input("State", key="leg_r_state")
            r_zip = rc3.text_input("Zip", key="leg_r_zip")

        st.write("")
        if st.form_submit_button("✅ Confirm Addresses"):
            if s_name and s_str and r_name and r_str:
                st.session_state.legacy_sender = {"name": s_name, "street": s_str, "city": s_city, "state": s_state, "zip": s_zip}
                st.session_state.legacy_recipient = {"name": r_name, "street": r_str, "city": r_city, "state": r_state, "zip": r_zip}
                st.success("Addresses Confirmed.")
            else:
                st.error("Please fill in at least Name and Street for both parties.")

    if not st.session_state.get("legacy_sender") or not st.session_state.get("legacy_recipient"):
        st.warning("Please confirm addresses above to unlock the writing studio.")
        st.stop()

    # 6. Font Selection
    st.markdown("---")
    st.markdown("### 🖋️ Step 2: Handwriting Style")
    
    font_map = {
        "Caveat (Casual)": "Caveat",
        "Great Vibes (Elegant)": "Great Vibes",
        "Indie Flower (Playful)": "Indie Flower", 
        "Schoolbell (Neat)": "Schoolbell"
    }
    
    f_col1, f_col2 = st.columns([1, 2])
    with f_col1:
        selected_label = st.radio("Choose Font:", list(font_map.keys()), index=0)
        font_choice = font_map[selected_label]
        st.session_state.legacy_font = font_choice

    with f_col2:
        css_class = f"fp-{font_choice.replace(' ', '')}"
        display_name = st.session_state.legacy_sender.get("name", "Me")
        st.markdown(f"""
        <div class="font-preview-box">
            <p class="{css_class}">
                "To my dearest family,<br>
                This is how my final words will look on paper.<br>
                With love, {display_name}"
            </p>
        </div>
        """, unsafe_allow_html=True)

    # 7. Compose Section (With Accessibility Tabs & Loop Fix)
    st.markdown("---")
    st.markdown("### ✍️ Step 3: Compose")
    
    st.markdown(
        """
        <div class="instruction-box">
        <b>INSTRUCTIONS:</b> Click <b>RECORD VOICE</b> to speak, or <b>TYPE MANUALLY</b> to write.
        </div>
        """, 
        unsafe_allow_html=True
    )

    tab_write, tab_record = st.tabs(["⌨️ TYPE MANUALLY", "🎙️ RECORD VOICE"])
    
    # TYPE TAB
    with tab_write:
        st.markdown("### ⌨️ Typing Mode")
        letter_text = st.text_area(
            "Letter Body", 
            value=st.session_state.get("legacy_text", ""),
            height=600,
            label_visibility="collapsed",
            placeholder="Start writing here...",
        )
        if letter_text:
            st.session_state.legacy_text = letter_text

    # RECORD TAB (RESTORED WITH LOOP FIX)
    with tab_record:
        st.markdown("### 🎙️ Voice Mode")
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
        
        audio_mic = st.audio_input("Record Voice", label_visibility="collapsed")
        
        # --- FIX: LOOP PREVENTION LOGIC ---
        if audio_mic and ai_engine:
            # 1. Calculate Hash of audio bytes
            audio_bytes = audio_mic.getvalue()
            # Use md5 for reliable byte hashing
            audio_hash = hashlib.md5(audio_bytes).hexdigest()
            
            # 2. Check if this hash is different from the last one we processed
            last_hash = st.session_state.get("last_legacy_hash")
            
            if audio_hash != last_hash:
                st.info("⏳ Processing your voice... please wait.")
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as t:
                    t.write(audio_bytes)
                    tpath = t.name
                
                try:
                    text = ai_engine.transcribe_audio(tpath)
                    if text:
                        # Append text
                        exist = st.session_state.get("legacy_text", "")
                        st.session_state.legacy_text = (exist + "\n\n" + text).strip()
                        
                        # Update Hash so we don't process this again
                        st.session_state.last_legacy_hash = audio_hash
                        
                        st.success("✅ Transcribed! Switch to 'Type Manually' to edit.")
                        st.rerun() 
                    else:
                        st.warning("⚠️ No speech detected.")
                except Exception as e:
                    st.error(f"Transcription Error: {e}")
                finally:
                    try: os.remove(tpath)
                    except: pass
            else:
                pass # Do nothing if we've already processed this audio

    # 8. Review & Pay Section
    st.markdown("---")
    st.markdown("### 👁️ Step 4: Secure & Send")
    
    col_prev, col_pay = st.columns([1, 1])

    # PDF PREVIEW
    with col_prev:
        if st.button("📄 Generate PDF Proof"):
            if not st.session_state.get("legacy_text"):
                st.error("Please write your letter first.")
            elif letter_format:
                try:
                    # FIX: Force Standard tier for signature
                    raw_pdf = letter_format.create_pdf(
                        st.session_state.get("legacy_text", ""), 
                        st.session_state.legacy_sender, 
                        st.session_state.legacy_recipient, 
                        tier="Standard", 
                        font_choice=st.session_state.legacy_font
                    )
                    
                    # --- CRITICAL FIX: Explicit cast to bytes ---
                    # This solves the bytearray error
                    pdf_bytes = bytes(raw_pdf) 
                    
                    b64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
                    pdf_display = f'<iframe src="data:application/pdf;base64,{b64_pdf}" width="100%" height="500" type="application/pdf"></iframe>'
                    st.markdown(pdf_display, unsafe_allow_html=True)
                    
                except Exception as e:
                    st.error(f"PDF Generation Error: {e}")

    # CHECKOUT
    with col_pay:
        st.markdown(f"""
        <div style="background-color: #f8f9fa; padding: 15px; border-radius: 10px; margin-bottom: 15px;">
            <h4 style="margin:0;">Total: $15.99</h4>
            <ul style="font-size: 0.9rem; color: #555; padding-left: 20px;">
                <li>Archival Bond Paper</li>
                <li>USPS Certified Mail Tracking</li>
                <li>Digital & Physical Proof</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
        # --- FIX: COLLECT EMAIL MANUALLY IF GUEST ---
        guest_email = None
        if not st.session_state.get("authenticated"):
            guest_email = st.text_input("📧 Enter Email for Tracking Number", placeholder="you@example.com")
            # If user enters an email, save it to session
            if guest_email:
                st.session_state.user_email = guest_email
        
        st.write("")
        if st.button("💳 Proceed to Secure Checkout", type="primary", use_container_width=True):
            
            # CHECK: Do we have an email?
            final_email = st.session_state.get("user_email")
            
            # If still no email (and user isn't authenticated), block them.
            if not final_email and not st.session_state.get("authenticated"):
                st.error("⚠️ Please enter an email address so we can send your tracking number.")
            
            elif payment_engine:
                _save_legacy_draft()
                
                # --- FIX: Send correct structure to payment engine ---
                url = payment_engine.create_checkout_session(
                    line_items=[{
                        "price_data": {
                            "currency": "usd",
                            "product_data": {"name": f"VerbaPost - Legacy Letter"},
                            "unit_amount": 1599,
                        },
                        "quantity": 1,
                    }],
                    user_email=final_email,
                    draft_id=st.session_state.get("current_legacy_draft_id")
                )
                
                if url:
                    st.link_button("👉 Pay Now ($15.99)", url)
                else:
                    st.error("Could not generate payment link.")
            else:
                st.error("Payment system offline.")

    st.markdown("---")
    if st.button("⬅️ Return to Dashboard"):
        st.query_params.clear()
        st.rerun()