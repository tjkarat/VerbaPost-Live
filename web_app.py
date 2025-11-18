import streamlit as st
from audio_recorder_streamlit import audio_recorder
from streamlit_drawable_canvas import st_canvas
import ai_engine
import database
import letter_format
import mailer
import os
from PIL import Image
import io

# --- ROBUST IMPORT ---
try:
    import recorder
    local_rec_available = True
except ImportError:
    local_rec_available = False

st.set_page_config(page_title="VerbaPost", page_icon="📮")

if "audio_path" not in st.session_state:
    st.session_state.audio_path = None

st.title("VerbaPost 📮")
st.markdown("**The Authenticity Engine.**")

# --- 1. SERVICE TIER ---
st.subheader("1. Choose Your Service")
service_tier = st.radio("Select Style:", 
    ["⚡ Standard ($2.50)", "🏺 Heirloom ($5.00)"], 
    captions=["API Fulfillment, Window Envelope", "Hand-stamped, Premium Paper, Handwritten Envelope"]
)

# --- 2. ADDRESS ---
st.divider()
st.subheader("2. Recipient")
col1, col2 = st.columns(2)
with col1:
    recipient_name = st.text_input("Name", placeholder="John Doe")
    street = st.text_input("Street", placeholder="123 Main St")
with col2:
    city = st.text_input("City", placeholder="Mt Juliet")
    state_zip = st.text_input("State/Zip", placeholder="TN 37122")

if not recipient_name or not street or not city or not state_zip:
    st.warning("Please fill out the address to proceed.")
    st.stop()

# --- 3. SIGNATURE (UPDATED) ---
st.divider()
st.subheader("3. Sign Your Letter")
st.markdown("Draw your signature below:")

# Updated Canvas with WHITE background
canvas_result = st_canvas(
    fill_color="rgba(255, 165, 0, 0.3)",
    stroke_width=2,
    stroke_color="#000000",
    background_color="#ffffff", # <--- CHANGED TO WHITE
    height=150,
    width=400,
    drawing_mode="freedraw",
    key="signature",
)

# --- 4. RECORDING ---
st.divider()
st.subheader("4. Dictate Message")

if local_rec_available:
    recording_mode = st.radio("Mic Source:", ["🖥️ Local Mac (Dev)", "🌐 Browser (Cloud)"])
else:
    recording_mode = "🌐 Browser (Cloud)"

if recording_mode == "🖥️ Local Mac (Dev)":
    if st.button("🔴 Record (5s)"):
        with st.spinner("Recording..."):
            path = "temp_letter.wav"
            recorder.record_audio(filename=path, duration=5)
            st.session_state.audio_path = path
        st.success("Done.")
else:
    audio_bytes = audio_recorder(text="", icon_size="50px")
    if audio_bytes:
        path = "temp_browser_recording.wav"
        with open(path, "wb") as f:
            f.write(audio_bytes)
        st.session_state.audio_path = path

# --- 5. GENERATE ---
if st.session_state.audio_path and os.path.exists(st.session_state.audio_path):
    st.audio(st.session_state.audio_path)
    
    if st.button("📮 Generate Letter", type="primary"):
        full_address = f"{recipient_name}\n{street}\n{city}, {state_zip}"
        
        with st.spinner("🧠 AI Transcribing & Rendering..."):
            try:
                text_content = ai_engine.transcribe_audio(st.session_state.audio_path)
            except Exception as e:
                st.error(f"AI Error: {e}")
                text_content = ""

            if text_content:
                sig_path = None
                if canvas_result.image_data is not None:
                    img = Image.fromarray(canvas_result.image_data.astype('uint8'), 'RGBA')
                    sig_path = "temp_signature.png"
                    img.save(sig_path)

                pdf_path = letter_format.create_pdf(text_content, full_address, "final_letter.pdf")
                
                st.balloons()
                if "Heirloom" in service_tier:
                    st.success("💌 Order Queued (Heirloom Tier)")
                else:
                    st.success("🚀 Sent to API (Standard Tier)")
                    mailer.send_letter(pdf_path)

                with open(pdf_path, "rb") as pdf_file:
                    st.download_button("📄 Download Preview", pdf_file, "letter.pdf")