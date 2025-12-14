import streamlit as st
import time
import tempfile
import os

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

# --- LEGACY PAGE LOGIC ---
def render_legacy_page():
    # --- CSS FOR FONT PREVIEWS ---
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
    
    /* Stanford Link Styling */
    .resource-link {
        font-size: 0.95rem;
        color: #555;
        background-color: #f0f2f6;
        padding: 10px 15px;
        border-radius: 8px;
        margin-bottom: 20px;
        border-left: 4px solid #667eea;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("## 🕊️ Legacy Service (End of Life)")
    
    # --- NEW: STANFORD LETTER PROJECT LINK ---
    st.markdown("""
    <div class="resource-link">
        <strong>💡 Need guidance on what to say?</strong><br>
        We highly recommend the <a href="https://med.stanford.edu/letter.html" target="_blank"><strong>Stanford Letter Project</strong></a>. 
        It provides excellent templates and advice for writing meaningful end-of-life letters.
    </div>
    """, unsafe_allow_html=True)

    st.info("Securely document and deliver your final wishes. \n\n**Privacy Guarantee:** This tool uses local transcription only. No AI analysis, editing, or data retention is performed.")

    # --- 1. SENDER INFO ---
    with st.expander("📍 Step 1: Your Information", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("Your Name", key="leg_name")
            street = st.text_input("Street Address", key="leg_street")
        with c2:
            city = st.text_input("City", key="leg_city")
            state = st.text_input("State", key="leg_state")
            zip_code = st.text_input("Zip", key="leg_zip")

    # --- 2. FONT SELECTION ---
    st.markdown("### 🖋️ Step 2: Choose Handwriting Style")
    
    font_map = {
        "Caveat (Casual)": "Caveat",
        "Great Vibes (Elegant)": "Great Vibes",
        "Indie Flower (Playful)": "Indie Flower", 
        "Schoolbell (Neat)": "Schoolbell"
    }
    
    f_col1, f_col2 = st.columns([1, 2])
    with f_col1:
        selected_label = st.radio(
            "Select Font:",
            list(font_map.keys()),
            index=0
        )
        font_choice = font_map[selected_label]
        st.session_state.legacy_font = font_choice

    with f_col2:
        css_class = f"fp-{font_choice.replace(' ', '')}"
        st.markdown(f"""
        <div class="font-preview-box">
            <p class="{css_class}">
                "To my dearest family,<br>
                This is how my final words will look on paper.<br>
                With love, {name or 'Me'}"
            </p>
        </div>
        """, unsafe_allow_html=True)

    # --- 3. DICTATION & COMPOSITION ---
    st.markdown("### 🎙️ Step 3: Record or Write")
    
    with st.container(border=True):
        st.markdown("#### 🗣️ Dictate Your Letter")
        st.markdown("""
        **Instructions:**
        1.  Click the microphone icon below.
        2.  Speak clearly and take your time. (Long pauses are okay).
        3.  Click 'Stop' when finished.
        4.  Press **Transcribe** to convert voice to text.
        """)
        
        col_mic, col_up = st.columns(2)
        with col_mic:
            audio_mic = st.audio_input("Record Voice")
        with col_up:
            uploaded_file = st.file_uploader("Or Upload Audio File (mp3/wav/m4a)", type=["mp3", "wav", "m4a"])

        active_audio = uploaded_file or audio_mic
        if active_audio:
            if ai_engine:
                if st.button("📝 Transcribe Audio", type="primary"):
                    with st.spinner("Transcribing..."):
                        suffix = ".wav" if not uploaded_file else os.path.splitext(uploaded_file.name)[1]
                        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as t:
                            t.write(active_audio.getvalue())
                            tpath = t.name
                        
                        try:
                            text = ai_engine.transcribe_audio(tpath)
                            current_text = st.session_state.get("legacy_text", "")
                            if current_text:
                                st.session_state.legacy_text = current_text + "\n\n" + text
                            else:
                                st.session_state.legacy_text = text
                            st.success("Transcription Complete!")
                        except Exception as e:
                            st.error(f"Transcription Failed: {e}")
                        finally:
                            if os.path.exists(tpath):
                                try: os.remove(tpath)
                                except: pass
            else:
                st.warning("AI Engine not loaded. Transcription unavailable.")

    st.markdown("#### ✍️ Edit & Review")
    letter_text = st.text_area(
        "Letter Content (Unlimited Length)", 
        value=st.session_state.get("legacy_text", ""),
        height=600, 
        key="legacy_text_area",
        placeholder="Type here or use the recorder above..."
    )
    if letter_text:
        st.session_state.legacy_text = letter_text

    # --- 4. PREVIEW & PAY ---
    st.markdown("### 👁️ Step 4: Finalize")
    
    col_prev, col_pay = st.columns([1, 1])

    with col_prev:
        if st.button("📄 Download PDF Proof"):
            if not name or not letter_text:
                st.error("Please fill in your name and letter text first.")
            elif letter_format:
                # Create dummy recipient for preview
                s_data = {"name": name, "street": street, "city": city, "state": state, "zip": zip_code}
                r_data = {"name": "Recipient Name", "street": "123 Example St", "city": "City", "state": "ST", "zip": "00000"}
                
                try:
                    pdf_bytes = letter_format.create_pdf(
                        letter_text, 
                        s_data, 
                        r_data, 
                        tier="Legacy",
                        font_choice=st.session_state.legacy_font
                    )
                    st.download_button(
                        label="⬇️ Download PDF",
                        data=pdf_bytes,
                        file_name="legacy_proof.pdf",
                        mime="application/pdf"
                    )
                except Exception as e:
                    st.error(f"Error generating PDF: {e}")
            else:
                st.error("PDF Engine not loaded.")

    with col_pay:
        st.markdown(f"""
        **Total: $15.99**
        * Archival Paper
        * Certified Mail Tracking
        * **{font_choice}** Style
        """)
        
        if st.button("💳 Proceed to Payment ($15.99)", type="primary"):
            if payment_engine:
                base = "https://verbapost.streamlit.app"
                if secrets_manager:
                    sec_url = secrets_manager.get_secret("BASE_URL")
                    if sec_url: base = sec_url
                
                success_url = f"{base.rstrip('/')}?session_id={{CHECKOUT_SESSION_ID}}&tier=Legacy&service=EndOfLife"
                
                url, sid = payment_engine.create_checkout_session(
                    f"Legacy Letter ({font_choice})",
                    1599,
                    success_url,
                    base
                )
                if url:
                    st.link_button("👉 Secure Checkout", url)
            else:
                st.error("Payment system offline.")

    st.markdown("---")
    if st.button("⬅️ Return to Main App"):
        st.query_params.clear()
        st.rerun()