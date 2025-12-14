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

# --- CSS INJECTOR ---
def inject_legacy_accessibility_css():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Caveat&family=Great+Vibes&family=Indie+Flower&family=Schoolbell&display=swap');

        .stTabs [data-baseweb="tab"] p {
            font-size: 1.5rem !important;
            font-weight: 700 !important;
        }

        .stTabs [data-baseweb="tab"] {
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
        }

        .stTabs [aria-selected="true"] {
            background-color: #FF4B4B !important;
            border: 3px solid #FF4B4B !important;
            color: white !important;
        }
        
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

# --- STATE MANAGEMENT ---
def initialize_legacy_state():
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
    if not database or not st.session_state.get("authenticated"):
        return {}
    
    try:
        user_email = st.session_state.get("user_email")
        contacts = database.get_saved_contacts(user_email)
        return {f"{c['name']} ({c.get('city', 'Unknown')})": c for c in contacts}
    except Exception as e:
        print(f"Address Book Error: {e}")
        return {}

def _save_legacy_draft():
    if not database:
        st.error("Database connection missing.")
        return

    user_email = st.session_state.get("user_email", "guest")
    text_content = st.session_state.get("legacy_text", "")
    
    try:
        d_id = st.session_state.get("current_legacy_draft_id")
        
        if d_id:
            database.update_draft_data(
                d_id, 
                content=text_content, 
                tier="Legacy", 
                price=15.99
            )
            st.toast("Draft Saved!", icon="💾")
        else:
            d_id = database.save_draft(user_email, text_content, "Legacy", 15.99)
            st.session_state.current_legacy_draft_id = d_id
            st.toast("New Draft Created!", icon="✨")
            
    except Exception as e:
        st.error(f"Save failed: {e}")

# --- SUCCESS VIEW (Prevents Payment Loop) ---
def render_success_view():
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
    
    email = st.session_state.get("user_email", "your email")
    st.info(f"We will email the **USPS Tracking Number** to: **{email}**")
    
    if st.button("Start Another Letter"):
        st.session_state.paid_success = False
        st.session_state.current_legacy_draft_id = None
        st.session_state.legacy_text = ""
        st.session_state.last_legacy_hash = None
        st.rerun()

# --- MAIN RENDERER ---
def render_legacy_page():
    initialize_legacy_state()
    inject_legacy_accessibility_css()

    # CHECK FOR PAYMENT SUCCESS FIRST
    if st.session_state.get("paid_success"):
        render_success_view()
        return

    c_head, c_save = st.columns([3, 1])
    c_head.markdown("## 🕊️ Legacy Workspace")
    if c_save.button("💾 Save Progress", key="btn_save_legacy", use_container_width=True): 
        _save_legacy_draft()

    with st.expander("ℹ️ How this works", expanded=False):
        st.write("1. Confirm Identity  2. Choose Style  3. Speak or Type  4. Certified Delivery")

    # 1. ADDRESSING
    addr_opts = load_address_book()
    st.markdown("### 📍 Step 1: Delivery Details")
    if addr_opts:
        sel = st.selectbox("📂 Load from Address Book", ["Select..."] + list(addr_opts.keys()))
        if sel != "Select...":
            d = addr_opts[sel]
            st.session_state.leg_r_name = d.get('name', '')
            st.session_state.leg_r_street = d.get('street', '')
            st.session_state.leg_r_city = d.get('city', '')
            st.session_state.leg_r_state = d.get('state', '')
            st.session_state.leg_r_zip = d.get('zip_code', '') or d.get('zip', '')

    with st.form("leg_addr"):
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### 🏠 From (You)")
            prof = st.session_state.get("user_profile", {})
            sn = st.text_input("Name", value=prof.get("full_name", ""), key="leg_s_name")
            ss = st.text_input("Street", value=prof.get("address_line1", ""), key="leg_s_street")
            x1, x2, x3 = st.columns(3)
            sc = x1.text_input("City", value=prof.get("city", ""), key="leg_s_city")
            stt = x2.text_input("State", value=prof.get("state", ""), key="leg_s_state")
            sz = x3.text_input("Zip", value=prof.get("zip_code", ""), key="leg_s_zip")
        with c2:
            st.markdown("#### 📬 To (Recipient)")
            st.warning("⚠️ Certified Mail: Recipient must sign.")
            rn = st.text_input("Name", key="leg_r_name")
            rs = st.text_input("Street", key="leg_r_street")
            y1, y2, y3 = st.columns(3)
            rc = y1.text_input("City", key="leg_r_city")
            rt = y2.text_input("State", key="leg_r_state")
            rz = y3.text_input("Zip", key="leg_r_zip")
        
        if st.form_submit_button("✅ Confirm Addresses"):
            if sn and ss and rn and rs:
                st.session_state.legacy_sender = {"name": sn, "street": ss, "city": sc, "state": stt, "zip": sz}
                st.session_state.legacy_recipient = {"name": rn, "street": rs, "city": rc, "state": rt, "zip": rz}
                st.success("Addresses Confirmed.")
            else:
                st.error("Missing name or street.")

    if not st.session_state.get("legacy_sender"): st.stop()

    # 2. STYLE
    st.markdown("---")
    st.markdown("### 🖋️ Step 2: Handwriting Style")
    f_map = {"Caveat": "Caveat", "Great Vibes": "Great Vibes", "Indie Flower": "Indie Flower", "Schoolbell": "Schoolbell"}
    c_f1, c_f2 = st.columns([1, 2])
    with c_f1:
        f_sel = st.radio("Font", list(f_map.keys()))
        st.session_state.legacy_font = f_map[f_sel]
    with c_f2:
        fn = f_map[f_sel].replace(" ", "")
        st.markdown(f'<div class="font-preview-box"><p class="fp-{fn}">"To my dearest family..."</p></div>', unsafe_allow_html=True)

    # 3. COMPOSE
    st.markdown("---")
    st.markdown("### ✍️ Step 3: Write Your Legacy")
    
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
            "Message Body", 
            value=st.session_state.get("legacy_text", ""),
            height=600,
            label_visibility="collapsed",
            placeholder="My dearest..."
        )
        if letter_text:
            st.session_state.legacy_text = letter_text

    # RECORD TAB (RESTORED)
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
        
        # --- LOOP PREVENTION LOGIC ---
        if audio_mic and ai_engine:
            # 1. Calculate Hash of audio bytes
            audio_bytes = audio_mic.getvalue()
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

    # 4. REVIEW & PAY
    st.markdown("---")
    st.markdown("### 👁️ Step 4: Secure & Send")
    
    col_prev, col_pay = st.columns([1, 1])

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
                    # FIX: Safe Cast to Bytes
                    pdf_bytes = bytes(raw_pdf)
                    b64 = base64.b64encode(pdf_bytes).decode('utf-8')
                    st.markdown(f'<iframe src="data:application/pdf;base64,{b64}" width="100%" height="500"></iframe>', unsafe_allow_html=True)
                except Exception as e:
                    st.error(f"PDF Error: {e}")

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
            guest_email = st.text_input("📧 Email for Tracking Number (Required)", placeholder="you@example.com")
            if guest_email:
                st.session_state.user_email = guest_email
        
        if st.button("💳 Proceed to Secure Checkout", type="primary", use_container_width=True):
            current_email = st.session_state.get("user_email")
            # Strict check: Must have valid email or user must have entered one
            if not current_email or current_email == "guest" or "@" not in current_email:
                st.error("⚠️ Please enter a valid email address so we can send your tracking number.")
            elif payment_engine:
                _save_legacy_draft()
                
                url = payment_engine.create_checkout_session(
                    line_items=[{
                        "price_data": {
                            "currency": "usd",
                            "product_data": {"name": "Legacy Letter (Certified)"},
                            "unit_amount": 1599,
                        },
                        "quantity": 1,
                    }],
                    user_email=current_email,
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