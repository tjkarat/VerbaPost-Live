import streamlit as st
import ai_engine
import database
import letter_format
import mailer
import os
from PIL import Image
from datetime import datetime
import zipcodes

# --- PAGE CONFIG ---
st.set_page_config(page_title="VerbaPost", page_icon="📮")

# --- TITLE ---
st.title("VerbaPost 📮")
st.caption("The Authenticity Engine - Stable Build")

# --- 1. ADDRESSING ---
st.subheader("1. Addressing")

col_to, col_from = st.tabs(["👉 Recipient", "👈 Sender"])

with col_to:
    to_name = st.text_input("Recipient Name", placeholder="John Doe")
    to_street = st.text_input("Street Address", placeholder="123 Main St")
    c1, c2 = st.columns(2)
    to_city = c1.text_input("City", placeholder="Mt Juliet")
    to_state = c2.text_input("State", max_chars=2, placeholder="TN")
    to_zip = c2.text_input("Zip", max_chars=5, placeholder="37122")

with col_from:
    from_name = st.text_input("Your Name")
    from_street = st.text_input("Your Street")
    from_city = st.text_input("Your City")
    from_state = st.text_input("Your State", max_chars=2)
    from_zip = st.text_input("Your Zip", max_chars=5)

# --- 2. SETTINGS & SIGNATURE ---
st.divider()
c_set, c_sig = st.columns(2)
with c_set:
    st.subheader("2. Settings")
    service_tier = st.radio("Tier:", ["⚡ Standard ($2.50)", "🏺 Heirloom ($5.00)"])
    is_heirloom = "Heirloom" in service_tier

with c_sig:
    st.subheader("3. Sign")
    from streamlit_drawable_canvas import st_canvas
    canvas_result = st_canvas(
        fill_color="rgba(255, 165, 0, 0.3)",
        stroke_width=2, stroke_color="#000", background_color="#fff",
        height=100, width=200, drawing_mode="freedraw", key="sig"
    )

# --- 4. NATIVE RECORDING (The Stability Fix) ---
st.divider()
st.subheader("4. Dictate")

# This is the NATIVE widget. It works on iPhone perfectly.
audio_value = st.audio_input("Record your letter")

if audio_value:
    # DEBUG: Verify file size immediately
    file_size = audio_value.getbuffer().nbytes
    
    if file_size < 2000:
        st.error(f"⚠️ Recording too short ({file_size} bytes). Please try again.")
    else:
        st.success(f"✅ Audio Locked ({file_size} bytes). Ready to Generate.")
        
        # --- 5. GENERATE BUTTON ---
        if st.button("🚀 Generate & Mail Letter", type="primary"):
            
            if not (to_name and to_street and to_city and to_state and to_zip):
                st.error("Please fill out the Recipient Address first!")
                st.stop()

            # Format Addresses
            full_recipient = f"{to_name}\n{to_street}\n{to_city}, {to_state} {to_zip}"
            full_return = f"{from_name}\n{from_street}\n{from_city}, {from_state} {from_zip}" if from_name else ""

            with st.spinner("Processing..."):
                # Save Temp File
                path = "temp_native.wav"
                with open(path, "wb") as f:
                    f.write(audio_value.getvalue())

                # Transcribe
                try:
                    text_content = ai_engine.transcribe_audio(path)
                except Exception as e:
                    st.error(f"Transcription Failed: {e}")
                    st.stop()

                # Check for hallucinations
                if not text_content or "1 oz" in text_content or len(text_content) < 5:
                    st.error("⚠️ The AI heard silence. Please re-record closer to the mic.")
                    st.stop()

                # Signature
                sig_path = None
                if canvas_result.image_data is not None:
                    img = Image.fromarray(canvas_result.image_data.astype('uint8'), 'RGBA')
                    sig_path = "temp_signature.png"
                    img.save(sig_path)

                # PDF
                pdf_path = letter_format.create_pdf(
                    text_content, full_recipient, full_return, is_heirloom, "final_letter.pdf", sig_path
                )
                
                # Success State
                st.balloons()
                st.success("Generated Successfully!")
                st.text_area("Final Text:", value=text_content)
                
                # Unique Name
                safe_name = "".join(x for x in to_name if x.isalnum())
                unique_name = f"Letter_{safe_name}_{datetime.now().strftime('%H%M')}.pdf"

                with open(pdf_path, "rb") as pdf_file:
                    st.download_button("Download PDF", pdf_file, unique_name, "application/pdf", use_container_width=True)
                
                if not is_heirloom:
                    mailer.send_letter(pdf_path)