import streamlit as st
import time
import tempfile
import os
import json

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

# --- HELPER: DRAFT SAVING ---
def _save_legacy_draft():
    """Saves the current state to the database so the user can return."""
    if not database:
        st.error("Database connection missing. Cannot save draft.")
        return

    # 1. Gather Data
    user_email = st.session_state.get("user_email", "guest")
    text_content = st.session_state.get("legacy_text", "")
    
    # Bundle addresses into a JSON-friendly structure or separate fields
    # For this implementation, we'll save the text and tier. 
    # Ideally, your DB 'save_draft' handles extra metadata, or we save to 'text' for now.
    
    try:
        # Check if we already have a draft ID for this session
        d_id = st.session_state.get("current_legacy_draft_id")
        
        if d_id:
            # Update existing
            database.update_draft_data(d_id, text=text_content, tier="Legacy", price=15.99)
            st.toast("Draft Saved! You can close this page safely.", icon="💾")
        else:
            # Create new
            d_id = database.save_draft(user_email, text_content, "Legacy", 15.99)
            st.session_state.current_legacy_draft_id = d_id
            st.toast("New Draft Created!", icon="✨")
            
    except Exception as e:
        st.error(f"Save failed: {e}")

# --- LEGACY PAGE LOGIC ---
def render_legacy_page():
    # --- CSS STYLING ---
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Caveat&family=Great+Vibes&family=Indie+Flower&family=Schoolbell&display=swap');
    
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
    
    .process-step {
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 10px;
        border-left: 4px solid #667eea;
    }
    
    .certified-warning {
        background-color: #fff3cd;
        color: #856404;
        padding: 10px;
        border-radius: 5px;
        font-size: 0.9rem;
        margin-bottom: 10px;
        border: 1px solid #ffeeba;
    }
    </style>
    """, unsafe_allow_html=True)

    # --- HEADER & CONTROLS ---
    c_head, c_save = st.columns([3, 1])
    with c_head:
        st.markdown("## 🕊️ Legacy Workspace")
    with c_save:
        if st.button("💾 Save Progress", use_container_width=True):
            _save_legacy_draft()

    # --- PROCESS EXPLANATION (PATIENCE) ---
    with st.expander("ℹ️ Read First: How this process works", expanded=False):
        st.markdown("""
        **Take your time.** This is a space for important, lasting words. You can stop, save, and return to this page anytime.
        
        1.  **Identity:** Verify who this is from and exactly who must sign for it.
        2.  **Style:** Choose a handwriting style that fits your tone.
        3.  **Compose:** Dictate or type your message. There is no length limit.
        4.  **Secure:** We generate a PDF proof. Once you pay ($15.99), it is printed on archival paper and sent via **Certified Mail**.
        """)

    # --- STANFORD RESOURCE ---
    st.info("💡 **Writer's Block?** The [Stanford Letter Project](https://med.stanford.edu/letter.html) offers excellent templates for end-of-life letters.")

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
                    # Pre-fill session state for the form
                    st.session_state.leg_r_name = data.get("name", "")
                    st.session_state.leg_r_street = data.get("street", "")
                    st.session_state.leg_r_city = data.get("city", "")
                    st.session_state.leg_r_state = data.get("state", "")
                    st.session_state.leg_r_zip = data.get("zip", "")
        except Exception: pass

    with st.form("legacy_address_form"):
        c1, c2 = st.columns(2)
        
        # SENDER
        with c1:
            st.markdown("#### 🏠 From (You)")
            s_name = st.text_input("Your Name", key="leg_s_name")
            s_str = st.text_input("Street Address", key="leg_s_street")
            sc1, sc2, sc3 = st.columns(3)
            s_city = sc1.text_input("City", key="leg_s_city")
            s_state = sc2.text_input("State", key="leg_s_state")
            s_zip = sc3.text_input("Zip", key="leg_s_zip")

        # RECIPIENT
        with c2:
            st.markdown("#### 📬 To (Recipient)")
            st.markdown("""<div class="certified-warning">⚠️ <strong>Certified Mail:</strong> The person listed below will need to sign for this letter. Ensure the name matches their ID.</div>""", unsafe_allow_html=True)
            
            r_name = st.text_input("Recipient Name", key="leg_r_name")
            r_str = st.text_input("Street Address", key="leg_r_street")
            rc1, rc2, rc3 = st.columns(3)
            r_city = rc1.text_input("City", key="leg_r_city")
            r_state = rc2.text_input("State", key="leg_r_state")
            r_zip = rc3.text_input("Zip", key="leg_r_zip")

        # Submit Action
        st.write("")
        col_submit, _ = st.columns([1, 2])
        with col_submit:
            saved = st.form_submit_button("✅ Confirm Addresses")
        
        if saved:
            if s_name and s_str and r_name and r_str:
                st.success("Addresses Confirmed.")
                # Save to session state manually to be safe
                st.session_state.legacy_sender = {"name": s_name, "street": s_str, "city": s_city, "state": s_state, "zip": s_zip}
                st.session_state.legacy_recipient = {"name": r_name, "street": r_str, "city": r_city, "state": r_state, "zip": r_zip}
            else:
                st.error("Please fill in all Name and Street fields.")

    # Validation Gate
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

    # --- STEP 3: COMPOSE ---
    st.markdown("---")
    st.markdown("### ✍️ Step 3: Compose")
    st.caption("You can record your voice, type manually, or paste from another document.")

    tab_write, tab_record = st.tabs(["📝 Type", "🎙️ Record"])
    
    with tab_record:
        st.info("Record your thoughts. We will transcribe them into text below.")
        audio_mic = st.audio_input("Record Voice")
        if audio_mic and ai_engine:
            if st.button("Transcribe Recording", type="primary"):
                with st.spinner("Processing..."):
                    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as t:
                        t.write(audio_mic.getvalue())
                        tpath = t.name
                    try:
                        text = ai_engine.transcribe_audio(tpath)
                        # Append to existing text
                        exist = st.session_state.get("legacy_text", "")
                        st.session_state.legacy_text = (exist + "\n\n" + text).strip()
                        st.success("Transcribed! Check the 'Type' tab to edit.")
                    except Exception as e:
                        st.error(f"Error: {e}")
                    finally:
                        try: os.remove(tpath)
                        except: pass

    with tab_write:
        letter_text = st.text_area(
            "Letter Body", 
            value=st.session_state.get("legacy_text", ""),
            height=600,
            placeholder="My dearest...",
            help="This content is private. No AI editing is applied."
        )
        if letter_text:
            st.session_state.legacy_text = letter_text

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
                    pdf_bytes = letter_format.create_pdf(
                        letter_text, 
                        st.session_state.legacy_sender, 
                        st.session_state.legacy_recipient, 
                        tier="Legacy",
                        font_choice=st.session_state.legacy_font
                    )
                    st.download_button(
                        label="⬇️ Download Official Proof",
                        data=pdf_bytes,
                        file_name="legacy_proof.pdf",
                        mime="application/pdf"
                    )
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
                
                # Save draft one last time before redirecting
                _save_legacy_draft()
                
                url, sid = payment_engine.create_checkout_session(
                    f"Legacy Letter ({font_choice})",
                    1599,
                    success_url,
                    base
                )
                if url:
                    st.link_button("👉 Pay Now ($15.99)", url)
            else:
                st.error("Payment system offline.")

    st.markdown("---")
    if st.button("⬅️ Return to Dashboard"):
        st.query_params.clear()
        st.rerun()