import streamlit as st
from streamlit_drawable_canvas import st_canvas
import os
from PIL import Image
from datetime import datetime
import time

# Import core logic
import ai_engine
import database
import letter_format
import mailer
import zipcodes
import payment_engine

# --- CONFIGURATION ---
MAX_BYTES_THRESHOLD = 35 * 1024 * 1024 

# --- PRICING ---
COST_STANDARD = 2.99
COST_HEIRLOOM = 5.99
COST_CIVIC = 6.99

def validate_zip(zipcode, state):
    if not zipcodes.is_real(zipcode): return False, "Invalid Zip Code"
    details = zipcodes.matching(zipcode)
    if details and details[0]['state'] != state.upper():
         return False, f"Zip is in {details[0]['state']}, not {state}"
    return True, "Valid"

def reset_app():
    st.session_state.audio_path = None
    st.session_state.transcribed_text = ""
    st.session_state.app_mode = "recording"
    st.session_state.overage_agreed = False
    st.session_state.payment_complete = False
    if "stripe_session_id" in st.session_state:
        del st.session_state.stripe_session_id
    st.rerun()

def show_main_app():
    # --- INIT STATE ---
    if "app_mode" not in st.session_state:
        st.session_state.app_mode = "recording"
    if "audio_path" not in st.session_state:
        st.session_state.audio_path = None
    if "transcribed_text" not in st.session_state:
        st.session_state.transcribed_text = ""
    if "payment_complete" not in st.session_state:
        st.session_state.payment_complete = False
    
    # --- SIDEBAR ---
    with st.sidebar:
        st.subheader("Controls")
        if st.button("🔄 Start New Letter", type="primary", use_container_width=True):
            reset_app()
    
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
        c3, c4 = st.columns(2)
        from_state = c3.text_input("Your State", max_chars=2)
        from_zip = c4.text_input("Your Zip", max_chars=5)

    if not (to_name and to_street and to_city and to_state and to_zip):
        st.info("👇 Fill out the **Recipient** tab to unlock the tools.")
        return

    # --- 2. SETTINGS & SIGNATURE ---
    st.divider()
    c_set, c_sig = st.columns(2)
    with c_set:
        st.subheader("2. Settings")
        service_tier = st.radio("Service Level:", 
            [
                f"⚡ Standard (${COST_STANDARD})", 
                f"🏺 Heirloom (${COST_HEIRLOOM})", 
                f"🏛️ Civic (${COST_CIVIC})"
            ]
        )
        is_heirloom = "Heirloom" in service_tier
        is_civic = "Civic" in service_tier

    with c_sig:
        st.subheader("3. Sign")
        canvas_result = st_canvas(
            fill_color="rgba(255, 165, 0, 0.3)",
            stroke_width=2, stroke_color="#000", background_color="#fff",
            height=100, width=200, drawing_mode="freedraw", key="sig"
        )

    st.divider()
    
    # --- PRICE CALCULATION ---
    if is_heirloom: price = COST_HEIRLOOM
    elif is_civic: price = COST_CIVIC
    else: price = COST_STANDARD

    # --- PAYMENT GATE ---
    if not st.session_state.payment_complete:
        st.subheader("4. Payment")
        st.info(f"Please pay **${price}** to unlock the recorder.")
        
        if "stripe_session_id" not in st.session_state:
            url, session_id = payment_engine.create_checkout_session(
                product_name=f"VerbaPost {service_tier}",
                amount_in_cents=int(price * 100),
                success_url="https://google.com", 
                cancel_url="https://google.com"
            )
            if url:
                st.session_state.stripe_url = url
                st.session_state.stripe_session_id = session_id
            else:
                st.error("⚠️ Payment Error. Check Secrets.")
                st.stop()

        st.link_button(f"💳 Pay ${price} in New Tab", st.session_state.stripe_url)
        
        with st.status("Waiting for payment...", expanded=True) as status:
            st.write("Complete payment in the new tab, then click check.")
            if st.button("🔄 Check Payment Status"):
                 is_paid = payment_engine.check_payment_status(st.session_state.stripe_session_id)
                 if is_paid:
                     status.update(label="✅ Payment Received!", state="complete")
                     st.session_state.payment_complete = True
                     st.rerun()
                 else:
                     st.warning("Not paid yet.")
        st.stop()

    # --- RECORDING ---
    if st.session_state.app_mode == "recording":
        st.subheader("🎙️ 5. Dictate")
        st.success("🔓 Recorder Unlocked!")
        
        audio_value = st.audio_input("Record your letter")

        if audio_value:
            with st.status("⚙️ Processing...", expanded=True) as status:
                path = "temp_browser_recording.wav"
                with open(path, "wb") as f:
                    f.write(audio_value.getvalue())
                st.session_state.audio_path = path
                
                file_size = audio_value.getbuffer().nbytes
                if file_size > MAX_BYTES_THRESHOLD:
                    st.error("Recording too long.")
                    if st.button("🗑️ Retry"): reset_app()
                    st.stop()
                else:
                    st.session_state.app_mode = "transcribing"
                    st.rerun()

    # --- TRANSCRIBING ---
    elif st.session_state.app_mode == "transcribing":
        with st.spinner("🧠 AI Transcribing..."):
            try:
                text = ai_engine.transcribe_audio(st.session_state.audio_path)
                st.session_state.transcribed_text = text
                st.session_state.app_mode = "editing"
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")
                if st.button("Retry"): reset_app()

    # --- EDITING ---
    elif st.session_state.app_mode == "editing":
        st.divider()
        st.subheader("📝 Review")
        st.audio(st.session_state.audio_path)
        edited_text = st.text_area("Edit Text:", value=st.session_state.transcribed_text, height=300)
        
        c1, c2 = st.columns([1, 3])
        if c1.button("✨ AI Polish"):
             st.session_state.transcribed_text = ai_engine.polish_text(edited_text)
             st.rerun()
        if c2.button("🗑️ Re-Record"):
             st.session_state.app_mode = "recording"
             st.rerun()

        st.markdown("---")
        if st.button("🚀 Approve & Send Now", type="primary", use_container_width=True):
            st.session_state.transcribed_text = edited_text
            st.session_state.app_mode = "finalizing"
            st.rerun()

    # --- FINALIZING ---
    elif st.session_state.app_mode == "finalizing":
        st.divider()
        with st.status("✉️ Sending...", expanded=True):
            sig_path = None
            if canvas_result.image_data is not None:
                img = Image.fromarray(canvas_result.image_data.astype('uint8'), 'RGBA')
                sig_path = "temp_signature.png"
                img.save(sig_path)

            pdf_path = letter_format.create_pdf(
                st.session_state.transcribed_text, 
                f"{to_name}\n{to_street}\n{to_city}, {to_state} {to_zip}", 
                f"{from_name}\n{from_street}\n{from_city}, {from_state} {from_zip}" if from_name else "", 
                is_heirloom, 
                st.session_state.get("language", "English"),
                "final_letter.pdf", 
                sig_path
            )
            
            if not is_heirloom:
                addr_to = {'name': to_name, 'street': to_street, 'city': to_city, 'state': to_state, 'zip': to_zip}
                addr_from = {'name': from_name, 'street': from_street, 'city': from_city, 'state': from_state, 'zip': from_zip}
                mailer.send_letter(pdf_path, addr_to, addr_from)
            
            st.write("✅ Done!")

        st.balloons()
        st.success("Letter Sent!")
        
        # Download logic...
        with open(pdf_path, "rb") as f:
            st.download_button("Download Copy", f, "letter.pdf")
            
        if st.button("Start New"): reset_app()