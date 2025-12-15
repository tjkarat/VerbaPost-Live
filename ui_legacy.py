import streamlit as st
import time
import tempfile
import os
import json
import base64
import hashlib

# --- ROBUST IMPORTS ---
try: import database
except ImportError: database = None
try: import payment_engine
except ImportError: payment_engine = None
try: import secrets_manager
except ImportError: secrets_manager = None
try: import letter_format
except ImportError: letter_format = None
try: import ai_engine
except ImportError: ai_engine = None

# --- CSS INJECTOR ---
def inject_legacy_accessibility_css():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Caveat&family=Great+Vibes&family=Indie+Flower&family=Schoolbell&display=swap');
        .stTabs [data-baseweb="tab"] p { font-size: 1.5rem !important; font-weight: 700 !important; }
        .stTabs [data-baseweb="tab"] { height: 70px; white-space: pre-wrap; background-color: #F0F2F6; border: 3px solid #9CA3AF; color: #374151; }
        .stTabs [aria-selected="true"] { background-color: #FF4B4B !important; border: 3px solid #FF4B4B !important; color: white !important; }
        .stTabs [aria-selected="true"] p { color: white !important; }
        .fp-Caveat { font-family: 'Caveat', cursive; }
        .fp-GreatVibes { font-family: 'Great Vibes', cursive; }
        .fp-IndieFlower { font-family: 'Indie Flower', cursive; }
        .fp-Schoolbell { font-family: 'Schoolbell', cursive; }
        .instruction-box { background-color: #FEF3C7; border-left: 10px solid #F59E0B; padding: 20px; margin-bottom: 25px; font-size: 20px; font-weight: 500; color: #000000; }
        </style>
    """, unsafe_allow_html=True)

# --- STATE MANAGEMENT ---
def initialize_legacy_state():
    defaults = {"legacy_sender": {}, "legacy_recipient": {}, "legacy_text": "", "legacy_font": "Caveat", "legacy_signature": "", "current_legacy_draft_id": None, "last_legacy_hash": None, "paid_success": False, "tracking_number": None}
    for key, val in defaults.items():
        if key not in st.session_state: st.session_state[key] = val

def load_address_book():
    if not database or not st.session_state.get("authenticated"): return {}
    try:
        user_email = st.session_state.get("user_email")
        contacts = database.get_contacts(user_email)
        return {f"{c.name} ({c.city})": c for c in contacts}
    except: return {}

def _save_legacy_draft():
    if not database: st.error("Database connection missing."); return
    user_email = st.session_state.get("user_email", "guest")
    try:
        d_id = st.session_state.get("current_legacy_draft_id")
        if d_id:
            database.update_draft_data(d_id, content=st.session_state.legacy_text, tier="Legacy", price=15.99)
            st.toast("Draft Saved!", icon="💾")
        else:
            d_id = database.save_draft(user_email, st.session_state.legacy_text, "Legacy", 15.99)
            st.session_state.current_legacy_draft_id = d_id
            st.toast("New Draft Created!", icon="✨")
    except Exception as e: st.error(f"Save failed: {e}")

# --- SUCCESS VIEW ---
def render_success_view():
    st.balloons()
    st.markdown("## ✅ Order Confirmed!")
    track_num = st.session_state.get("tracking_number", "Processing...")
    email = st.session_state.get("user_email", "your email")
    st.markdown(f"""
        <div style="background-color: #dcfce7; padding: 25px; border-radius: 10px; border: 1px solid #22c55e; margin-bottom: 20px;">
            <h3 style="color: #15803d; margin-top:0;">Secure Delivery Initiated</h3>
            <p>Your legacy letter has been securely generated and sent to our certified mailing center.</p>
            <div style="background: white; padding: 15px; border-radius: 5px; margin-top: 15px;">
                <strong>Tracking Reference / ID:</strong><br><code style="font-size: 1.2em; color: #d93025;">{track_num}</code>
            </div>
            <p style="margin-top: 15px;">A confirmation email has been sent to <b>{email}</b>.</p>
        </div>
        """, unsafe_allow_html=True)
    if st.button("Start Another Letter"):
        st.session_state.paid_success = False
        st.session_state.current_legacy_draft_id = None
        st.session_state.legacy_text = ""
        st.session_state.tracking_number = None
        st.rerun()

# --- MAIN RENDERER ---
def render_legacy_page():
    initialize_legacy_state()
    inject_legacy_accessibility_css()
    if st.session_state.get("paid_success"): render_success_view(); return

    c_head, c_save = st.columns([3, 1])
    c_head.markdown("## 🕊️ Legacy Workspace")
    if c_save.button("💾 Save Progress", key="btn_save_legacy", use_container_width=True): _save_legacy_draft()

    # --- STANFORD PROJECT REFERENCE ---
    with st.expander("ℹ️ How this works & Writing Help", expanded=False): 
        st.write("1. Confirm Identity  2. Choose Style  3. Speak or Type  4. Certified Delivery")
        st.markdown("---")
        st.markdown("### 💡 Need help writing?")
        st.info("For guidance, templates, and inspiration on what to say, we highly recommend the **[Stanford Letter Project](https://med.stanford.edu/letter.html)**.")

    addr_opts = load_address_book()
    st.markdown("### 📍 Step 1: Delivery Details")
    if addr_opts:
        sel = st.selectbox("📂 Load from Address Book", ["Select..."] + list(addr_opts.keys()))
        if sel != "Select...":
            d = addr_opts[sel]
            st.session_state.leg_r_name = d.name if hasattr(d, 'name') else d.get('name', '')
            st.session_state.leg_r_street = d.street if hasattr(d, 'street') else d.get('street', '')
            st.session_state.leg_r_city = d.city if hasattr(d, 'city') else d.get('city', '')
            st.session_state.leg_r_state = d.state if hasattr(d, 'state') else d.get('state', '')
            st.session_state.leg_r_zip = d.zip_code if hasattr(d, 'zip_code') else d.get('zip_code', '')
    
    with st.form("leg_addr"):
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### 🏠 From (You)")
            prof = st.session_state.get("user_profile", {})
            p_name = prof.get("full_name", "") if isinstance(prof, dict) else getattr(prof, "full_name", "")
            p_addr = prof.get("address_line1", "") if isinstance(prof, dict) else getattr(prof, "address_line1", "")
            p_city = prof.get("address_city", "") if isinstance(prof, dict) else getattr(prof, "address_city", "")
            p_state = prof.get("address_state", "") if isinstance(prof, dict) else getattr(prof, "address_state", "")
            p_zip = prof.get("address_zip", "") if isinstance(prof, dict) else getattr(prof, "address_zip", "")
            
            sn = st.text_input("Name", value=p_name, key="leg_s_name")
            sig = st.text_input("Signature (Sign-off)", value=p_name, placeholder="e.g. Love, Grandma", key="leg_s_sig")
            ss = st.text_input("Street", value=p_addr, key="leg_s_street")
            x1, x2, x3 = st.columns(3)
            sc = x1.text_input("City", value=p_city, key="leg_s_city")
            stt = x2.text_input("State", value=p_state, key="leg_s_state")
            sz = x3.text_input("Zip", value=p_zip, key="leg_s_zip")
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
                st.session_state.legacy_signature = sig
                st.success("Addresses Confirmed.")
            else: st.error("Missing name or street.")

    if not st.session_state.get("legacy_sender"): st.stop()

    st.markdown("---")
    st.markdown("### 🖋️ Step 2: Handwriting Style")
    f_map = {"Caveat": "Caveat", "Great Vibes": "Great Vibes", "Indie Flower": "Indie Flower", "Schoolbell": "Schoolbell"}
    c_f1, c_f2 = st.columns([1, 2])
    with c_f1:
        f_sel = st.radio("Font", list(f_map.keys()))
        st.session_state.legacy_font = f_map[f_sel]
    with c_f2:
        fn = f_map[f_sel].replace(" ", "")
        # FIX 9: Larger, Senior-Friendly Font Preview
        preview_text = "My Dearest Family,<br>This is how my legacy letter will look.<br>With all my love,<br>Grandma"
        st.markdown(f'''<div style="background: #fff; padding: 25px; border: 2px solid #333; border-radius: 10px; margin-bottom: 20px;">
            <p class="fp-{fn}" style="font-size: 32px !important; line-height: 1.6; margin: 0; color: #000;">{preview_text}</p>
        </div>''', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### ✍️ Step 3: Compose")
    st.markdown('<div class="instruction-box"><b>INSTRUCTIONS:</b> Click <b>RECORD VOICE</b> to speak, or <b>TYPE MANUALLY</b> to write.</div>', unsafe_allow_html=True)
    t_type, t_rec = st.tabs(["⌨️ TYPE MANUALLY", "🎙️ RECORD VOICE"])
    with t_type:
        txt = st.text_area("Body", value=st.session_state.get("legacy_text", ""), height=600)
        if txt: st.session_state.legacy_text = txt
    with t_rec:
        st.markdown("1. Click Mic  2. Speak  3. Auto-transcribe")
        audio = st.audio_input("Record", label_visibility="collapsed")
        if audio and ai_engine:
            ahash = hashlib.md5(audio.getvalue()).hexdigest()
            if ahash != st.session_state.get("last_legacy_hash"):
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
                    tf.write(audio.getvalue())
                    tname = tf.name
                try:
                    res = ai_engine.transcribe_audio(tname)
                    if res:
                        if hasattr(ai_engine, 'enhance_transcription_for_seniors'):
                            res = ai_engine.enhance_transcription_for_seniors(res)
                        st.session_state.legacy_text = (st.session_state.get("legacy_text","") + "\n\n" + res).strip()
                        st.session_state.last_legacy_hash = ahash
                        st.rerun()
                finally: os.remove(tname)

    st.markdown("---")
    st.markdown("### 👁️ Step 4: Secure & Send")
    c_p, c_c = st.columns([1,1])
    with c_p:
        if st.button("📄 Generate PDF Proof"):
            if not st.session_state.get("legacy_text"): st.error("Please write your letter first.")
            elif letter_format:
                try:
                    raw = letter_format.create_pdf(
                        st.session_state.get("legacy_text", ""),
                        st.session_state.legacy_recipient, # Correct: To
                        st.session_state.legacy_sender,    # Correct: From
                        tier="Standard",
                        font_choice=st.session_state.legacy_font,
                        signature_text=st.session_state.get("legacy_signature")
                    )
                    pdf_bytes = bytes(raw)
                    b64 = base64.b64encode(pdf_bytes).decode('utf-8')
                    st.markdown(f'<embed src="data:application/pdf;base64,{b64}" width="100%" height="500" type="application/pdf">', unsafe_allow_html=True)
                    st.download_button("⬇️ Download PDF", pdf_bytes, "legacy_letter.pdf", "application/pdf")
                except Exception as e: st.error(f"PDF Error: {e}")

    with c_c:
        st.markdown(f"""<div style="background-color: #f8f9fa; padding: 15px; border-radius: 10px; margin-bottom: 15px;"><h4 style="margin:0;">Total: $15.99</h4><ul style="font-size: 0.9rem; color: #555; padding-left: 20px;"><li>Archival Bond Paper</li><li>USPS Certified Mail Tracking</li><li>Digital & Physical Proof</li></ul></div>""", unsafe_allow_html=True)
        guest_email = None
        if not st.session_state.get("authenticated"):
            guest_email = st.text_input("📧 Enter Email for Tracking Number", placeholder="you@example.com")
            if guest_email: st.session_state.user_email = guest_email
        if st.button("💳 Proceed to Secure Checkout", type="primary", use_container_width=True):
            if not st.session_state.get("user_email") and not guest_email: st.error("⚠️ Please enter an email address.")
            elif payment_engine:
                _save_legacy_draft()
                url = payment_engine.create_checkout_session(
                    line_items=[{"price_data": {"currency": "usd", "product_data": {"name": "Legacy Letter (Certified)"}, "unit_amount": 1599}, "quantity": 1}],
                    user_email=st.session_state.get("user_email"),
                    draft_id=st.session_state.get("current_legacy_draft_id")
                )
                if url: st.link_button("👉 Pay Now ($15.99)", url)
                else: st.error("Payment Link Error")
    st.markdown("---")
    if st.button("⬅️ Return to Dashboard"): st.query_params.clear(); st.rerun()