import streamlit as st
from streamlit_drawable_canvas import st_canvas
import os
from PIL import Image
from datetime import datetime
import urllib.parse
import io
import zipfile

# Import core logic
import voice_processor 
import database
import letter_format
import mailer
import zipcodes
import payment_engine
import civic_engine

# --- CONFIG ---
MAX_BYTES_THRESHOLD = 35 * 1024 * 1024 
YOUR_APP_URL = "https://verbapost.streamlit.app" 
COST_STANDARD = 2.99
COST_HEIRLOOM = 5.99
COST_CIVIC = 6.99
COST_OVERAGE = 1.00

def reset_app():
    st.session_state.audio_path = None
    st.session_state.transcribed_text = ""
    st.session_state.app_mode = "recording"
    st.session_state.overage_agreed = False
    st.session_state.payment_complete = False
    st.query_params.clear()
    st.rerun()

def show_main_app():
    # --- 1. AUTO-DETECT PAYMENT (THE FIX) ---
    # This runs immediately when the page loads
    if "session_id" in st.query_params:
        session_id = st.query_params["session_id"]
        if payment_engine.check_payment_status(session_id):
            st.session_state.payment_complete = True
            st.toast("✅ Payment Confirmed! Recorder Unlocked.")
            st.query_params.clear() # Remove code from URL so it looks clean
        else:
            st.error("Payment verification failed. Please try again.")

    # --- INIT STATE ---
    if "app_mode" not in st.session_state: st.session_state.app_mode = "recording"
    if "audio_path" not in st.session_state: st.session_state.audio_path = None
    if "payment_complete" not in st.session_state: st.session_state.payment_complete = False

    # --- SIDEBAR ---
    with st.sidebar:
        if st.button("🔄 Start New Letter"): reset_app()

    # --- 2. ADDRESSING ---
    st.subheader("1. Addressing")
    col_to, col_from = st.tabs(["👉 Recipient", "👈 Sender"])
    
    def get_val(k): return st.session_state.get(k, "")

    with col_to:
        to_name = st.text_input("Recipient Name", value=get_val("to_name"), key="to_name")
        to_street = st.text_input("Street Address", value=get_val("to_street"), key="to_street")
        c1, c2 = st.columns(2)
        to_city = c1.text_input("City", value=get_val("to_city"), key="to_city")
        to_state = c2.text_input("State", value=get_val("to_state"), max_chars=2, key="to_state")
        to_zip = c2.text_input("Zip", value=get_val("to_zip"), max_chars=5, key="to_zip")

    with col_from:
        from_name = st.text_input("Your Name", value=get_val("from_name"), key="from_name")
        from_street = st.text_input("Your Street", value=get_val("from_street"), key="from_street")
        from_city = st.text_input("Your City", value=get_val("from_city"), key="from_city")
        c3, c4 = st.columns(2)
        from_state = c3.text_input("Your State", value=get_val("from_state"), max_chars=2, key="from_state")
        from_zip = c4.text_input("Your Zip", value=get_val("from_zip"), max_chars=5, key="from_zip")

    # Service Selection
    st.divider()
    st.subheader("2. Settings")
    service_tier = st.radio("Service Level:", [f"⚡ Standard (${COST_STANDARD})", f"🏺 Heirloom (${COST_HEIRLOOM})", f"🏛️ Civic (${COST_CIVIC})"], key="tier_select")
    is_heirloom = "Heirloom" in service_tier
    is_civic = "Civic" in service_tier

    # Logic: If Civic, we only need Sender. If not, we need Both.
    valid_to = to_name and to_street and to_city and to_state and to_zip
    valid_from = from_name and from_street and from_city and from_state and from_zip

    if is_civic:
        if not valid_from:
            st.warning("👇 Fill out **Sender** tab to find Representatives.")
            return
    else:
        if not valid_to:
            st.info("👇 Fill out **Recipient** tab.")
            return
        if not valid_from:
            st.warning("👇 Fill out **Sender** tab.")
            return

    # --- 3. SIGNATURE ---
    st.subheader("3. Sign")
    canvas_result = st_canvas(fill_color="rgba(255, 165, 0, 0.3)", stroke_width=2, stroke_color="#000", background_color="#fff", height=100, width=200, drawing_mode="freedraw", key="sig")

    # --- 4. PAYMENT GATE ---
    if is_heirloom: price = COST_HEIRLOOM
    elif is_civic: price = COST_CIVIC
    else: price = COST_STANDARD

    st.divider()
    if not st.session_state.payment_complete:
        st.subheader("4. Payment")
        st.info(f"Total: **${price}**")
        
        # Build Return URL with state
        params = {"to_name": to_name, "to_street": to_street, "from_name": from_name} # Minimal params to keep URL short
        q_str = urllib.parse.urlencode(params)
        success_link = f"{YOUR_APP_URL}?{q_str}"
        
        # Get Link
        url, session_id = payment_engine.create_checkout_session(f"VerbaPost {service_tier}", int(price * 100), success_link, YOUR_APP_URL)
        
        if url:
            st.link_button(f"💳 Pay ${price}", url, type="primary")
        else:
            st.error("Payment Error.")
        st.stop()

    # --- 5. RECORD & SEND ---
    if st.session_state.app_mode == "recording":
        st.subheader("🎙️ 5. Dictate")
        st.success("🔓 Payment Verified")
        
        audio_value = st.audio_input("Record Letter")
        if audio_value:
            path = "temp.wav"
            with open(path, "wb") as f: f.write(audio_value.getvalue())
            st.session_state.audio_path = path
            st.session_state.app_mode = "transcribing"
            st.rerun()

    elif st.session_state.app_mode == "transcribing":
        with st.spinner("Transcribing..."):
            text = voice_processor.transcribe_audio(st.session_state.audio_path)
            st.session_state.transcribed_text = text
            st.session_state.app_mode = "editing"
            st.rerun()

    elif st.session_state.app_mode == "editing":
        st.divider()
        st.subheader("📝 Review")
        edited_text = st.text_area("Edit:", value=st.session_state.transcribed_text, height=300)
        if st.button("✨ AI Polish"):
            st.session_state.transcribed_text = voice_processor.polish_text(edited_text)
            st.rerun()
        if st.button("🚀 Send Now", type="primary", use_container_width=True):
            st.session_state.transcribed_text = edited_text
            st.session_state.app_mode = "finalizing"
            st.rerun()

    elif st.session_state.app_mode == "finalizing":
        with st.status("Sending...", expanded=True):
            # Save Sig
            sig_path = None
            if canvas_result.image_data is not None:
                img = Image.fromarray(canvas_result.image_data.astype('uint8'), 'RGBA')
                sig_path = "sig.png"
                img.save(sig_path)
            
            lang = "English" # Default for now
            
            if is_civic:
                # CIVIC BLAST LOGIC
                full_addr = f"{from_street}, {from_city}, {from_state} {from_zip}"
                targets = civic_engine.get_reps(full_addr)
                
                if not targets:
                    st.error("No Reps Found. Check address.")
                    st.stop()
                    
                files = []
                addr_from = {'name': from_name, 'street': from_street, 'city': from_city, 'state': from_state, 'zip': from_zip}

                for t in targets:
                    t_addr = t['address_obj']
                    pdf = letter_format.create_pdf(
                        st.session_state.transcribed_text,
                        f"{t['name']}\n{t_addr['street']}\n{t_addr['city']}, {t_addr['state']}",
                        f"{from_name}\n{from_street}...",
                        False, lang, f"{t['name']}.pdf", sig_path
                    )
                    files.append(pdf)
                    
                    t_lob = {'name': t['name'], 'street': t_addr['street'], 'city': t_addr['city'], 'state': t_addr['state'], 'zip': t_addr['zip']}
                    mailer.send_letter(pdf, t_lob, addr_from)
                
                # Zip Download
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, "w") as zf:
                    for f in files: zf.write(f, os.path.basename(f))
                st.download_button("📦 Download All (ZIP)", zip_buffer.getvalue(), "letters.zip")
                
            else:
                # STANDARD LOGIC
                full_to = f"{to_name}\n{to_street}\n{to_city}, {to_state} {to_zip}"
                full_from = f"{from_name}\n{from_street}\n{from_city}, {from_state} {from_zip}"
                pdf = letter_format.create_pdf(st.session_state.transcribed_text, full_to, full_from, is_heirloom, lang, "letter.pdf", sig_path)
                
                if not is_heirloom:
                    addr_to = {'name': to_name, 'street': to_street, 'city': to_city, 'state': to_state, 'zip': to_zip}
                    addr_from = {'name': from_name, 'street': from_street, 'city': from_city, 'state': from_state, 'zip': from_zip}
                    mailer.send_letter(pdf, addr_to, addr_from)
                
                with open(pdf, "rb") as f:
                    st.download_button("Download PDF", f, "letter.pdf")
            
            st.success("Sent!")
        
        if st.button("Start New"): reset_app()