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

# --- CONFIGURATION ---
MAX_BYTES_THRESHOLD = 35 * 1024 * 1024 
YOUR_APP_URL = "https://verbapost.streamlit.app" 

# --- PRICING ---
COST_STANDARD = 2.99
COST_HEIRLOOM = 5.99
COST_CIVIC = 6.99
COST_OVERAGE = 1.00

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
    st.query_params.clear()
    if "stripe_url" in st.session_state:
        del st.session_state.stripe_url
    if "last_config" in st.session_state:
        del st.session_state.last_config
    st.rerun()

def show_main_app():
    # --- 0. AUTO-DETECT RETURN FROM STRIPE (SMART CHECK) ---
    if "processed_ids" not in st.session_state:
        st.session_state.processed_ids = []

    if "session_id" in st.query_params:
        session_id = st.query_params["session_id"]
        
        # ONLY process if we haven't seen this ID before
        if session_id not in st.session_state.processed_ids:
            if payment_engine.check_payment_status(session_id):
                st.session_state.payment_complete = True
                st.session_state.processed_ids.append(session_id) # MARK AS USED
                st.toast("✅ Payment Confirmed! Recorder Unlocked.")
                st.query_params.clear() 
            else:
                st.error("Payment verification failed.")
        # If it IS in processed_ids, we do nothing (keep payment_complete as False for new letter)

    # --- INIT STATE ---
    if "app_mode" not in st.session_state:
        st.session_state.app_mode = "recording"
    if "audio_path" not in st.session_state:
        st.session_state.audio_path = None
    if "transcribed_text" not in st.session_state:
        st.session_state.transcribed_text = ""
    if "overage_agreed" not in st.session_state:
        st.session_state.overage_agreed = False
    if "payment_complete" not in st.session_state:
        st.session_state.payment_complete = False
    
    # --- SIDEBAR RESET ---
    with st.sidebar:
        st.subheader("Controls")
        if st.button("🔄 Start New Letter", type="primary", use_container_width=True):
            reset_app()
    
    # --- 1. ADDRESSING ---
    st.subheader("1. Addressing")
    col_to, col_from = st.tabs(["👉 Recipient", "👈 Sender"])

    def get_val(key): return st.session_state.get(key, st.query_params.get(key, ""))

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

    # Validation
    service_tier = st.radio("Service Level:", 
        [f"⚡ Standard (${COST_STANDARD})", f"🏺 Heirloom (${COST_HEIRLOOM})", f"🏛️ Civic (${COST_CIVIC})"],
        key="tier_select"
    )
    is_heirloom = "Heirloom" in service_tier
    is_civic = "Civic" in service_tier

    if is_civic:
        st.info("🏛️ **Civic Mode:** We will find your reps based on your Return Address.")
        if not (from_name and from_street and from_city and from_state and from_zip):
             st.warning("👇 Please fill out the **Sender** tab.")
             return
    else:
        if not (to_name and to_street and to_city and to_state and to_zip):
            st.info("👇 Fill out the **Recipient** tab to unlock the tools.")
            return
        if not (from_name and from_street and from_city and from_state and from_zip):
             st.warning("👇 Fill out the **Sender** tab.")
             return

    # --- 2. SIGNATURE ---
    st.divider()
    st.subheader("3. Sign")
    canvas_result = st_canvas(
        fill_color="rgba(255, 165, 0, 0.3)", stroke_width=2, stroke_color="#000", background_color="#fff",
        height=100, width=200, drawing_mode="freedraw", key="sig"
    )

    st.divider()
    
    # --- PRICE CALCULATION ---
    if is_heirloom: price = COST_HEIRLOOM
    elif is_civic: price = COST_CIVIC
    else: price = COST_STANDARD
    final_price = price + (COST_OVERAGE if st.session_state.overage_agreed else 0.00)

    # ==================================================
    #  PAYMENT GATE
    # ==================================================
    if not st.session_state.payment_complete:
        st.subheader("4. Payment")
        st.info(f"Total: **${final_price:.2f}**")
        
        params = {
            "to_name": to_name, "to_street": to_street, "to_city": to_city, "to_state": to_state, "to_zip": to_zip,
            "from_name": from_name, "from_street": from_street, "from_city": from_city, "from_state": from_state, "from_zip": from_zip
        }
        query_string = urllib.parse.urlencode(params)
        success_link = f"{YOUR_APP_URL}?{query_string}"

        current_config = f"{service_tier}_{final_price}"
        if "stripe_url" not in st.session_state or st.session_state.get("last_config") != current_config:
             url, session_id = payment_engine.create_checkout_session(
                product_name=f"VerbaPost {service_tier}",
                amount_in_cents=int(final_price * 100),
                success_url=success_link, 
                cancel_url=YOUR_APP_URL
            )
             st.session_state.stripe_url = url
             st.session_state.stripe_session_id = session_id
             st.session_state.last_config = current_config
        
        if st.session_state.stripe_url:
            st.link_button(f"💳 Pay ${final_price:.2f} & Unlock Recorder", st.session_state.stripe_url, type="primary")
            st.caption("Secure checkout via Stripe.")
            
            if st.button("🔄 I've Paid (Refresh Status)"):
                 if payment_engine.check_payment_status(st.session_state.stripe_session_id):
                     st.session_state.payment_complete = True
                     st.rerun()
                 else:
                     st.error("Payment not found. Please pay first.")
        else:
            st.error("Connection Error. Please refresh.")
        st.stop() 

    # ==================================================
    #  STATE 1: RECORDING
    # ==================================================
    if st.session_state.app_mode == "recording":
        st.subheader("🎙️ 5. Dictate")
        st.success("🔓 Payment Verified.")
        
        audio_value = st.audio_input("Record your letter")

        if audio_value:
            with st.status("⚙️ Processing Audio...", expanded=True) as status:
                path = "temp_browser_recording.wav"
                with open(path, "wb") as f:
                    f.write(audio_value.getvalue())
                st.session_state.audio_path = path
                
                file_size = audio_value.getbuffer().nbytes
                if file_size > MAX_BYTES_THRESHOLD:
                    status.update(label="⚠️ Recording too long!", state="error")
                    st.error("Recording exceeds 3 minutes.")
                    if st.button(f"💳 Agree to +${COST_OVERAGE} Charge"):
                        st.session_state.overage_agreed = True
                        st.session_state.app_mode = "transcribing"
                        st.rerun()
                    if st.button("🗑️ Delete & Retry"):
                        st.session_state.audio_path = None
                        st.rerun()
                    st.stop()
                else:
                    status.update(label="✅ Uploaded! Starting Transcription...", state="complete")
                    st.session_state.app_mode = "transcribing"
                    st.rerun()

    # ==================================================
    #  STATE 1.5: TRANSCRIBING
    # ==================================================
    elif st.session_state.app_mode == "transcribing":
        with st.spinner("🧠 AI is writing your letter..."):
            try:
                text = voice_processor.transcribe_audio(st.session_state.audio_path)
                st.session_state.transcribed_text = text
                st.session_state.app_mode = "editing"
                st.rerun()
            except Exception as e:
                st.error(f"Transcription Error: {e}")
                if st.button("Try Again"): reset_app()

    # ==================================================
    #  STATE 2: EDITING
    # ==================================================
    elif st.session_state.app_mode == "editing":
        st.divider()
        st.subheader("📝 Review")
        st.audio(st.session_state.audio_path)
        edited_text = st.text_area("Edit Text:", value=st.session_state.transcribed_text, height=300)
        c1, c2 = st.columns([1, 3])
        if c1.button("✨ AI Polish"):
             st.session_state.transcribed_text = voice_processor.polish_text(edited_text)
             st.rerun()
        if c2.button("🗑️ Re-Record (Free)"):
             st.session_state.app_mode = "recording"
             st.rerun()
        st.markdown("---")
        if st.button("🚀 Approve & Send Now", type="primary", use_container_width=True):
            st.session_state.transcribed_text = edited_text
            st.session_state.app_mode = "finalizing"
            st.rerun()

    # ==================================================
    #  STATE 3: FINALIZING
    # ==================================================
    elif st.session_state.app_mode == "finalizing":
        st.divider()
        with st.status("✉️ Sending...", expanded=True) as status:
            sig_path = None
            if canvas_result.image_data is not None:
                img = Image.fromarray(canvas_result.image_data.astype('uint8'), 'RGBA')
                sig_path = "temp_signature.png"
                img.save(sig_path)

            # --- CIVIC LOGIC ---
            if is_civic:
                st.write("🏛️ Finding your Representatives...")
                full_user_address = f"{from_street}, {from_city}, {from_state} {from_zip}"
                targets = civic_engine.get_reps(full_user_address)
                
                if not targets:
                    st.error("❌ Could not find representatives.")
                    st.caption("Try simplifying your address or checking the Zip Code.")
                    if st.button("Edit Address"):
                        st.session_state.app_mode = "recording"
                        st.rerun()
                    st.stop()
                
                final_files = []
                addr_from = {'name': from_name, 'street': from_street, 'city': from_city, 'state': from_state, 'zip': from_zip}
                
                for target in targets:
                    st.write(f"Processing for {target['name']}...")
                    fname = f"Letter_to_{target['name'].replace(' ', '')}.pdf"
                    t_addr = target['address_obj']
                    
                    pdf_path = letter_format.create_pdf(
                        st.session_state.transcribed_text, 
                        f"{target['name']}\n{t_addr['street']}\n{t_addr['city']}, {t_addr['state']} {t_addr['zip']}",
                        f"{from_name}\n{from_street}\n{from_city}, {from_state} {from_zip}",
                        False, 
                        st.session_state.get("language", "English"),
                        fname, 
                        sig_path
                    )
                    final_files.append(pdf_path)
                    t_addr_lob = {'name': target['name'], 'street': t_addr['street'], 'city': t_addr['city'], 'state': t_addr['state'], 'zip': t_addr['zip']}
                    mailer.send_letter(pdf_path, t_addr_lob, addr_from)

                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, "w") as zf:
                    for fp in final_files: zf.write(fp, os.path.basename(fp))
                
                st.success("All 3 Letters Sent!")
                st.download_button("📦 Download All", zip_buffer.getvalue(), "Civic_Blast.zip", "application/zip")

            # --- STANDARD LOGIC ---
            else:
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
                    st.write("🚀 Transmitting to Lob...")
                    mailer.send_letter(pdf_path, addr_to, addr_from)
                else:
                    st.info("🏺 Added to Heirloom Queue")
                
                st.write("✅ Done!")
                st.success("Letter Sent!")
                with open(pdf_path, "rb") as f:
                    st.download_button("📄 Download Receipt", f, "letter.pdf", use_container_width=True)
            
            # AUTO-SAVE
            if st.session_state.get("user"):
                try:
                    database.update_user_address(st.session_state.user.user.email, from_name, from_street, from_city, from_state, from_zip)
                except: pass

        if st.button("Start New"):
            reset_app()