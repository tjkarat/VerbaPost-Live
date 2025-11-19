import streamlit as st
from audio_recorder_streamlit import audio_recorder
from streamlit_drawable_canvas import st_canvas
import ai_engine
import database
import letter_format
import mailer
import os
from PIL import Image
from datetime import datetime
import zipcodes

# --- ROBUST IMPORT ---
try:
    import recorder
    local_rec_available = True
except (ImportError, OSError):
    local_rec_available = False

st.set_page_config(page_title="VerbaPost", page_icon="📮")
if "audio_path" not in st.session_state:
    st.session_state.audio_path = None

# --- ADDRESS VALIDATION ---
def validate_zip(zipcode, state):
    is_valid = zipcodes.is_real(zipcode)
    if not is_valid: return False, "Invalid Zip"
    details = zipcodes.matching(zipcode)
    if details and details[0]['state'] != state.upper():
         return False, f"Zip is in {details[0]['state']}"
    return True, "Valid"

st.title("VerbaPost 📮")
st.markdown("**The Authenticity Engine.**")

# --- 1. ADDRESS SECTION ---
st.subheader("1. Addressing")
col_to, col_from = st.tabs(["👉 To (Recipient)", "👈 From (Return Address)"])

with col_to:
    to_name = st.text_input("Recipient Name", placeholder="John Doe")
    to_street = st.text_input("Street Address", placeholder="123 Main St")
    c1, c2 = st.columns(2)
    to_city = c1.text_input("City", placeholder="Mt Juliet")
    to_state = c2.text_input("State (e.g. TN)", max_chars=2)
    to_zip = c2.text_input("Zip Code", max_chars=5)

with col_from:
    st.info("Required for the PDF.")
    from_name = st.text_input("Your Name")
    from_street = st.text_input("Your Street")
    c3, c4 = st.columns(2)
    from_city = c3.text_input("Your City")
    from_state = c4.text_input("Your State", max_chars=2)
    from_zip = c4.text_input("Your Zip", max_chars=5)

# Validation Check
if not (to_name and to_street and to_city and to_state and to_zip):
    st.info("👇 Fill out the **Recipient** tab to unlock the recorder.")
    st.stop()

# --- 2. SERVICE TIER ---
st.divider()
service_tier = st.radio("Service Level:", ["⚡ Standard ($2.50)", "🏺 Heirloom ($5.00)"], horizontal=True)
is_heirloom = "Heirloom" in service_tier

# --- 3. SIGNATURE ---
st.divider()
st.write("Sign Below:")
canvas_result = st_canvas(
    fill_color="rgba(255, 165, 0, 0.3)", 
    stroke_width=2, stroke_color="#000", background_color="#fff",
    height=120, width=300, drawing_mode="freedraw", key="sig"
)

# --- 4. RECORDER (Fixing the Silence Issue) ---
st.divider()
st.subheader("🎙️ Dictate")

c_rec, c_inst = st.columns([1, 2])
with c_inst:
    st.caption("1. Tap Mic. 2. Speak Clearly. 3. Tap Stop.")
    st.warning("⚠️ Only stop AFTER you finish speaking.")

with c_rec:
    if local_rec_available:
        mode = st.toggle("Dev Mode (Local)", value=False)
        if mode:
            if st.button("🔴 Record Local"):
                path = "temp_letter.wav"
                recorder.record_audio(filename=path, duration=5)
                st.session_state.audio_path = path
            audio_bytes = None
        else:
            # Increased thresholds to prevent "Ghost" recordings
            audio_bytes = audio_recorder(text="", icon_size="80px", pause_threshold=3.0, energy_threshold=400)
    else:
        audio_bytes = audio_recorder(text="", icon_size="80px", pause_threshold=3.0, energy_threshold=400)

if audio_bytes:
    # Stricter Check: Filter out files smaller than 2KB (usually empty headers)
    if len(audio_bytes) > 2000: 
        path = "temp_browser_recording.wav"
        with open(path, "wb") as f:
            f.write(audio_bytes)
        st.session_state.audio_path = path
        st.success(f"✅ Audio Captured! ({len(audio_bytes)} bytes)")
    else:
        st.error("❌ Audio too short/silent. Please try again closer to the mic.")

# --- 5. GENERATE ---
if st.session_state.audio_path and os.path.exists(st.session_state.audio_path):
    st.audio(st.session_state.audio_path)
    
    if st.button("📮 Generate Letter", type="primary", use_container_width=True):
        full_recipient = f"{to_name}\n{to_street}\n{to_city}, {to_state} {to_zip}"
        full_return = f"{from_name}\n{from_street}\n{from_city}, {from_state} {from_zip}" if from_name else ""
        
        with st.spinner("Processing..."):
            try:
                text_content = ai_engine.transcribe_audio(st.session_state.audio_path)
            except Exception as e:
                st.error(f"AI Error: {e}")
                text_content = ""

            if text_content:
                # Filter out the specific Whisper hallucination
                if "1 oz" in text_content or len(text_content.strip()) < 2:
                     st.error("⚠️ Audio was unclear. The AI heard only silence/static. Please re-record.")
                else:
                    sig_path = None
                    if canvas_result.image_data is not None:
                        img = Image.fromarray(canvas_result.image_data.astype('uint8'), 'RGBA')
                        sig_path = "temp_signature.png"
                        img.save(sig_path)

                    # Pass new arguments to PDF Engine
                    pdf_path = letter_format.create_pdf(
                        text_content, 
                        full_recipient, 
                        full_return, 
                        is_heirloom, 
                        "final_letter.pdf", 
                        sig_path
                    )
                    
                    st.balloons()
                    st.success("Letter Ready!")
                    
                    safe_name = "".join(x for x in to_name if x.isalnum())
                    unique_name = f"Letter_{safe_name}_{datetime.now().strftime('%H%M')}.pdf"

                    with open(pdf_path, "rb") as pdf_file:
                        st.download_button("📄 Download PDF", pdf_file, unique_name, "application/pdf", use_container_width=True)