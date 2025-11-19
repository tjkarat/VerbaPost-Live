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

# --- CONFIG ---
st.set_page_config(page_title="VerbaPost", page_icon="📮")

# --- SESSION STATE INITIALIZATION ---
# We use this to track exactly where the user is in the flow
if "app_mode" not in st.session_state:
    st.session_state.app_mode = "recording" # Options: recording, reviewing, success
if "audio_path" not in st.session_state:
    st.session_state.audio_path = None
if "final_text" not in st.session_state:
    st.session_state.final_text = ""

# --- ROBUST IMPORT ---
try:
    import recorder
    local_rec_available = True
except (ImportError, OSError):
    local_rec_available = False

# --- ADDRESS VALIDATION ---
def validate_zip(zipcode, state):
    if not zipcodes.is_real(zipcode): return False, "Invalid Zip"
    details = zipcodes.matching(zipcode)
    if details and details[0]['state'] != state.upper():
         return False, f"Zip is in {details[0]['state']}"
    return True, "Valid"

# --- RESET FUNCTION ---
def reset_app():
    st.session_state.app_mode = "recording"
    st.session_state.audio_path = None
    st.session_state.final_text = ""
    # We perform a rerun to instantly clear the screen
    st.rerun()

st.title("VerbaPost 📮")

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
    from_name = st.text_input("Your Name")
    from_street = st.text_input("Your Street")
    c3, c4 = st.columns(2)
    from_city = c3.text_input("Your City")
    from_state = c4.text_input("Your State", max_chars=2)
    from_zip = c4.text_input("Your Zip", max_chars=5)

# Lock app until address is valid
if not (to_name and to_street and to_city and to_state and to_zip):
    st.info("👇 Fill out the **Recipient** tab to unlock the recorder.")
    st.stop()

# --- 2. SETTINGS ---
st.divider()
c_tier, c_sig = st.columns(2)
with c_tier:
    service_tier = st.radio("Service Level:", ["⚡ Standard ($2.50)", "🏺 Heirloom ($5.00)"])
    is_heirloom = "Heirloom" in service_tier

with c_sig:
    st.write("Sign Below:")
    canvas_result = st_canvas(
        fill_color="rgba(255, 165, 0, 0.3)", 
        stroke_width=2, stroke_color="#000", background_color="#fff",
        height=100, width=200, drawing_mode="freedraw", key="sig"
    )

# ==================================================
#  THE STATE MACHINE (Recording -> Review -> Send)
# ==================================================
st.divider()
st.subheader("🎙️ Dictate Message")

# === STATE: RECORDING ===
if st.session_state.app_mode == "recording":
    st.info("Tap the mic to START. Tap again to STOP.")
    
    # FIX FOR SHORT RECORDING:
    # pause_threshold=60.0 means "Don't auto-stop until 60 seconds of silence".
    # This forces the user to manually click stop, preventing premature cuts.
    audio_bytes = audio_recorder(
        text="",
        recording_color="#e8b62c",
        neutral_color="#6aa36f",
        icon_size="100px",
        pause_threshold=60.0,  # <--- FIX FOR "2 SECONDS" BUG
        sample_rate=44100
    )
    
    if audio_bytes and len(audio_bytes) > 2000:
        path = "temp_browser_recording.wav"
        with open(path, "wb") as f:
            f.write(audio_bytes)
        st.session_state.audio_path = path
        st.session_state.app_mode = "reviewing"
        st.rerun() # Force instant refresh to hide recorder and show review

# === STATE: REVIEWING ===
elif st.session_state.app_mode == "reviewing":
    st.success("✅ Recording Captured")
    
    # Listen back
    st.audio(st.session_state.audio_path)
    
    col_retry, col_send = st.columns(2)
    
    with col_retry:
        if st.button("🔄 Trash & Retry", use_container_width=True):
            reset_app()
            
    with col_send:
        # This is the "Confirm Done" button you asked for
        if st.button("🚀 Confirm & Send", type="primary", use_container_width=True):
            st.session_state.app_mode = "processing"
            st.rerun()

# === STATE: PROCESSING (Automatic) ===
elif st.session_state.app_mode == "processing":
    with st.status("✉️ Processing Letter...", expanded=True):
        
        # 1. Transcribe
        st.write("🧠 AI is listening...")
        try:
            text_content = ai_engine.transcribe_audio(st.session_state.audio_path)
        except Exception as e:
            st.error(f"AI Error: {e}")
            st.stop()

        if not text_content or "1 oz" in text_content or len(text_content.strip()) < 2:
             st.error("⚠️ Audio was unclear. Please Retry.")
             if st.button("Back"): reset_app()
             st.stop()
        
        st.write("📝 Formatting PDF...")
        full_recipient = f"{to_name}\n{to_street}\n{to_city}, {to_state} {to_zip}"
        full_return = f"{from_name}\n{from_street}\n{from_city}, {from_state} {from_zip}" if from_name else ""

        sig_path = None
        if canvas_result.image_data is not None:
            img = Image.fromarray(canvas_result.image_data.astype('uint8'), 'RGBA')
            sig_path = "temp_signature.png"
            img.save(sig_path)

        pdf_path = letter_format.create_pdf(
            text_content, full_recipient, full_return, is_heirloom, "final_letter.pdf", sig_path
        )
        
        # 2. Mail
        if not is_heirloom:
            st.write("🚀 Sending to API...")
            mailer.send_letter(pdf_path)
        
        st.write("✅ Done!")

    # FINAL SUCCESS UI
    st.balloons()
    st.success("Letter Sent Successfully!")
    st.text_area("Final Message:", value=text_content)
    
    safe_name = "".join(x for x in to_name if x.isalnum())
    unique_name = f"Letter_{safe_name}_{datetime.now().strftime('%H%M')}.pdf"

    with open(pdf_path, "rb") as pdf_file:
        st.download_button("📄 Download Copy", pdf_file, unique_name, "application/pdf", use_container_width=True)
    
    if st.button("📮 Write Another Letter"):
        reset_app()