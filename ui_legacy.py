import streamlit as st
import time
import tempfile
import os
import json
import base64

# --- ROBUST IMPORTS ---
try:
    import database
except Exception:
    database = None

try:
    import payment_engine
except Exception:
    payment_engine = None

try:
    import secrets_manager
except Exception:
    secrets_manager = None

try:
    import letter_format
except Exception:
    letter_format = None

try:
    import ai_engine
except Exception:
    ai_engine = None

# --- ACCESSIBILITY CSS INJECTOR (Shared Logic) ---
def inject_legacy_accessibility_css():
    """
    Injects CSS to make tabs larger, high-contrast, and button-like.
    Same standard as ui_main for consistency.
    """
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

# --- HELPER: DRAFT SAVING ---
def _save_legacy_draft():
    """Saves the current state to the database so the user can return."""
    if not database:
        st.error("Database connection missing. Cannot save draft.")
        return

    user_email = st.session_state.get("user_email", "guest")
    text_content = st.session_state.get("legacy_text", "")
    
    try:
        d_id = st.session_state.get("current_legacy_draft_id")
        
        if d_id:
            database.update_draft_data(d_id, text=text_content, tier="Legacy", price=15.99)
            st.toast("Draft Saved! You can close this page safely.", icon="💾")
        else:
            d_id = database.save_draft(user_email, text_content, "Legacy", 15.99)
            st.session_state.current_legacy_draft_id = d_id
            st.toast("New Draft Created!", icon="✨")
            
    except Exception as e:
        st.error(f"Save failed: {e}")

# --- LEGACY PAGE LOGIC ---
def render_legacy_page():
    # Inject CSS
    inject_legacy_accessibility_css()

    # --- HEADER & CONTROLS ---
    c_head, c_save = st.columns([3, 1])
    with c_head:
        st.markdown("## 🕊️ Legacy Workspace")
    with c_save:
        if st.button("💾 Save Progress", use_container_width=True):
            _save_legacy_draft()

    with st.expander("ℹ️ Read First: How this process works", expanded=False):
        st.markdown("""
        **Take your time.** This is a space for important, lasting words.
        1.  **Identity:** Verify who this is from and exactly who must sign for it.
        2.  **Style:** Choose a handwriting style that fits your tone.
        3.  **Compose:** Dictate or type your message.
        4.  **Secure:** We generate a PDF proof sent via **Certified Mail**.
        """)

    st.info("💡 **Writer's Block?** The [Stanford Letter Project](https://med.stanford.edu/letter.html) offers excellent templates.")

    # --- STEP 1: ADDRESSING ---
    st.markdown("### 📍 Step 1: Delivery Details")
    
    # Address Book Loader
    if database and st.session_state.get("authenticated"):
        try:
            saved = database.get_saved_contacts(st.session_state.user_email)
            if saved:
                opts = {f"{x['name']} ({x.get('street','')})": x for x in saved}
                selected_key = st.selectbox("📂 Load Contact from Address Book", ["Select..."] + list(opts.keys()))
                if selected_key != "Select...":
                    data = opts[selected_key]
                    st.session_state.leg_r_name = data.get("name", "")
                    st.session_state.leg_r_street = data.get("street", "")
                    st.session_state.leg_r_city = data.get("city", "")
                    st.session_state.leg_r_state = data.get("state", "")
                    st.session_state.leg_r_zip = data.get("zip", "")
        except Exception: pass

    with st.form("legacy_address_form"):
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### 🏠 From (You)")
            s_name = st.text_input("Your Name", key="leg_s_name")
            s_str = st.text_input("Street Address", key="leg_s_street")
            sc1, sc2, sc3 = st.columns(3)
            s_city = sc1.text_input("City", key="leg_s_city")
            s_state = sc2.text_input("State", key="leg_s_state")
            s_zip = sc3.text_input("Zip", key="leg_s_zip")

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
                st.success("Addresses Confirmed.")
                st.session_state.legacy_sender = {"name": s_name, "street": s_str, "city": s_city, "state": s_state, "zip": s_zip}
                st.session_state.legacy_recipient = {"name": r_name, "street": r_str, "city": r_city, "state": r_state, "zip": r_zip}
            else:
                st.error("Please fill in all Name and Street fields.")

    if not st.session_state.get("legacy_sender") or not st.session_state.get("legacy_recipient"):
        st.warning("Please confirm addresses above to unlock the writing studio.")
        st.stop()

    # --- STEP 2: STYLE ---
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

    # --- STEP 3: COMPOSE (Improved Accessibility) ---
    st.markdown("---")
    st.markdown("### ✍️ Step 3: Compose")
    
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

    tab_write, tab_record = st.tabs(["⌨️ TYPE MANUALLY", "🎙️ RECORD VOICE"])
    
    with tab_write:
        st.markdown("### ⌨️ Typing Mode")
        letter_text = st.text_area(
            "Letter Body", 
            value=st.session_state.get("legacy_text", ""),
            height=600,
            label_visibility="collapsed",
            placeholder="My dearest...",
        )
        if letter_text:
            st.session_state.legacy_text = letter_text

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
        
        # Audio Input Widget
        audio_mic = st.audio_input("Record Voice", label_visibility="collapsed")
        
        if audio_mic and ai_engine:
            # FIX: Prevent infinite looping by checking if this EXACT audio has been processed
            # 1. Calculate a simple hash/id for the current audio bytes
            audio_bytes = audio_mic.getvalue()
            audio_hash = hash(audio_bytes)
            
            # 2. Compare with the last processed hash
            last_hash = st.session_state.get("last_legacy_audio_hash")
            
            if audio_hash != last_hash:
                st.info("⏳ Processing your voice... please wait.")
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as t:
                    t.write(audio_bytes)
                    tpath = t.name
                
                try:
                    text = ai_engine.transcribe_audio(tpath)
                    if text:
                        exist = st.session_state.get("legacy_text", "")
                        st.session_state.legacy_text = (exist + "\n\n" + text).strip()
                        
                        # 3. Mark as processed
                        st.session_state.last_legacy_audio_hash = audio_hash
                        
                        st.success("✅ Transcribed! Switch to 'Type Manually' to edit.")
                        st.rerun() # Refresh to update the text box in the other tab
                    else:
                        st.warning("⚠️ No speech detected.")
                except Exception as e:
                    st.error(f"Error: {e}")
                finally:
                    try: os.remove(tpath)
                    except: pass
            else:
                # If hash matches, we do nothing (the user hasn't recorded anything new)
                pass

    # --- STEP 4: REVIEW & PAY ---
    st.markdown("---")
    st.markdown("### 👁️ Step 4: Secure & Send")
    
    col_prev, col_pay = st.columns([1, 1])

    with col_prev:
        if st.button("📄 Generate PDF Proof"):
            if not letter_text:
                st.error("Please write your letter first.")
            elif letter_format:
                try:
                    # Explicitly convert to bytes to avoid 'bytearray' error
                    raw_pdf = letter_format.create_pdf(
                        letter_text, 
                        st.session_state.legacy_sender, 
                        st.session_state.legacy_recipient, 
                        tier="Standard", # Use Standard to ensure signature block is included
                        font_choice=st.session_state.legacy_font
                    )
                    pdf_bytes = bytes(raw_pdf) 
                    
                    b64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
                    pdf_display = f'<iframe src="data:application/pdf;base64,{b64_pdf}" width="100%" height="500" type="application/pdf"></iframe>'
                    st.markdown(pdf_display, unsafe_allow_html=True)
                    
                except Exception as e:
                    st.error(f"PDF Generation Error: {e}")

    with col_pay:
        st.markdown(f"""
        <div style="background-color: #f8f9fa; padding: 15px; border-radius: 10px;">
            <h4 style="margin:0;">Total: $15.99</h4>
            <ul style="font-size: 0.9rem; color: #555; padding-left: 20px;">
                <li>Archival Bond Paper</li>
                <li>USPS Certified Mail Tracking</li>
                <li>Digital & Physical Proof</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
        st.write("")
        if st.button("💳 Proceed to Secure Checkout", type="primary", use_container_width=True):
            if payment_engine:
                base = "https://verbapost.streamlit.app"
                if secrets_manager:
                    sec_url = secrets_manager.get_secret("BASE_URL")
                    if sec_url: base = sec_url
                
                success_url = f"{base.rstrip('/')}?session_id={{CHECKOUT_SESSION_ID}}&tier=Legacy&service=EndOfLife"
                _save_legacy_draft()
                
                url = payment_engine.create_checkout_session(
                    line_items=[{
                        "price_data": {
                            "currency": "usd",
                            "product_data": {"name": f"VerbaPost - Legacy Letter"},
                            "unit_amount": 1599,
                        },
                        "quantity": 1,
                    }],
                    user_email=st.session_state.get("user_email", "guest"),
                    draft_id=st.session_state.get("current_legacy_draft_id")
                )
                if url:
                    st.link_button("👉 Pay Now ($15.99)", url)
            else:
                st.error("Payment system offline.")

    st.markdown("---")
    if st.button("⬅️ Return to Dashboard"):
        st.query_params.clear()
        st.rerun()