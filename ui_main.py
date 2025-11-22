import streamlit as st
from streamlit_drawable_canvas import st_canvas
import os
from PIL import Image
from datetime import datetime
import urllib.parse

# Import core logic
import ai_engine 
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

def reset_app():
    # Clear everything to start fresh
    for key in list(st.session_state.keys()):
        if key not in ['user', 'user_email']: # Keep login info
            del st.session_state[key]
    st.query_params.clear()
    st.rerun()

def show_main_app():
    # --- 0. CHECK FOR PAYMENT RETURN ---
    # This runs on page load to catch the Stripe Redirect
    if "session_id" in st.query_params:
        session_id = st.query_params["session_id"]
        
        # Only verify if we haven't already
        if session_id not in st.session_state.get("processed_ids", []):
            if payment_engine.check_payment_status(session_id):
                st.session_state.payment_complete = True
                
                # Track used ID
                if "processed_ids" not in st.session_state: st.session_state.processed_ids = []
                st.session_state.processed_ids.append(session_id)
                
                # Set mode to 'paid_workspace'
                st.session_state.app_mode = "workspace"
                
                # Clear URL to prevent loops
                st.query_params.clear()
                st.toast("✅ Payment Successful! Workspace Unlocked.")
                st.rerun()

    # --- INIT STATE ---
    if "app_mode" not in st.session_state: st.session_state.app_mode = "store"
    if "payment_complete" not in st.session_state: st.session_state.payment_complete = False

    # --- SIDEBAR ---
    with st.sidebar:
        st.subheader("Controls")
        if st.button("🔄 Cancel & Restart", type="primary"):
            reset_app()

    # ==================================================
    #  PHASE 1: THE STORE (Select & Pay)
    # ==================================================
    if st.session_state.app_mode == "store":
        st.header("1. Select Service")
        
        # Tier Selection
        service_tier = st.radio("Choose your letter type:", 
            [f"⚡ Standard (${COST_STANDARD})", f"🏺 Heirloom (${COST_HEIRLOOM})", f"🏛️ Civic (${COST_CIVIC})"],
            index=0,
            key="tier_select"
        )
        
        # Determine Price
        if "Standard" in service_tier: price = COST_STANDARD
        elif "Heirloom" in service_tier: price = COST_HEIRLOOM
        elif "Civic" in service_tier: price = COST_CIVIC
        
        st.info(f"**Total: ${price}**")
        
        # PAYMENT BUTTON
        # We generate the link dynamically
        current_config = f"{service_tier}_{price}"
        if "stripe_url" not in st.session_state or st.session_state.get("last_config") != current_config:
             # We pass the APP URL as success, so it comes right back here
             url, session_id = payment_engine.create_checkout_session(
                product_name=f"VerbaPost {service_tier}",
                amount_in_cents=int(price * 100),
                success_url=YOUR_APP_URL, 
                cancel_url=YOUR_APP_URL
            )
             st.session_state.stripe_url = url
             st.session_state.stripe_session_id = session_id
             st.session_state.last_config = current_config
             
        if st.session_state.stripe_url:
            st.link_button(f"💳 Pay ${price} & Start Writing", st.session_state.stripe_url, type="primary")
            st.caption("You will be redirected to Stripe. Upon payment, you will return here to write your letter.")
        else:
            st.error("System Error: Payment link could not be generated.")

    # ==================================================
    #  PHASE 2: THE WORKSPACE (Address, Record, Send)
    # ==================================================
    elif st.session_state.app_mode == "workspace":
        st.success("🔓 Account Credited. Ready to write.")
        
        # Determine Tier from previous selection (or default/session)
        # Note: In a real app we'd store the 'purchased_tier' in DB. 
        # For MVP, we trust the session state persists or user re-selects valid logic.
        # To be safe, we let them toggle Logic here, but they already paid.
        
        # --- ADDRESSING ---
        st.subheader("2. Addressing")
        col_to, col_from = st.tabs(["👉 Recipient", "👈 Sender"])

        with col_to:
            to_name = st.text_input("Recipient Name", placeholder="John Doe")
            to_street = st.text_input("Street Address", placeholder="123 Main St")
            c1, c2 = st.columns(2)
            to_city = c1.text_input("City", placeholder="Mt Juliet")
            to_state = c2.text_input("State", max_chars=2, placeholder="TN")
            to_zip = c2.text_input("Zip", max_chars=5, placeholder="37122")

        with col_from:
            # Auto-fill if user is logged in
            u_name = st.session_state.get("from_name", "")
            u_street = st.session_state.get("from_street", "")
            u_city = st.session_state.get("from_city", "")
            u_state = st.session_state.get("from_state", "")
            u_zip = st.session_state.get("from_zip", "")

            from_name = st.text_input("Your Name", value=u_name)
            from_street = st.text_input("Your Street", value=u_street)
            from_city = st.text_input("Your City", value=u_city)
            c3, c4 = st.columns(2)
            from_state = c3.text_input("Your State", value=u_state, max_chars=2)
            from_zip = c4.text_input("Your Zip", value=u_zip, max_chars=5)

        # --- SIGNATURE ---
        st.divider()
        st.subheader("3. Sign")
        canvas_result = st_canvas(
            fill_color="rgba(255, 165, 0, 0.3)", stroke_width=2, stroke_color="#000", background_color="#fff",
            height=200, width=350, drawing_mode="freedraw", key="sig"
        )

        # --- RECORDER ---
        st.divider()
        st.subheader("4. Dictate")
        
        # Instruction Box
        st.info("Tap the microphone icon to start. Tap again to stop. (Max 3 Mins)")
        
        audio_value = st.audio_input("Record your letter")

        if audio_value:
            with st.status("⚙️ Processing...", expanded=True):
                path = "temp.wav"
                with open(path, "wb") as f: f.write(audio_value.getvalue())
                st.session_state.audio_path = path
                
                # Transcribe
                try:
                    text = ai_engine.transcribe_audio(path)
                    st.session_state.transcribed_text = text
                    st.session_state.app_mode = "review" # Move to next step
                    st.rerun()
                except Exception as e:
                    st.error(f"Transcription Error: {e}")

    # ==================================================
    #  PHASE 3: REVIEW & SEND
    # ==================================================
    elif st.session_state.app_mode == "review":
        st.header("5. Review")
        
        edited_text = st.text_area("Edit your letter:", value=st.session_state.transcribed_text, height=300)
        
        if st.button("🚀 Finalize & Send", type="primary", use_container_width=True):
            st.session_state.transcribed_text = edited_text
            
            with st.status("Sending...", expanded=True):
                # 1. Save Signature
                sig_path = None
                if canvas_result.image_data is not None:
                    img = Image.fromarray(canvas_result.image_data.astype('uint8'), 'RGBA')
                    sig_path = "temp_signature.png"
                    img.save(sig_path)
                
                # 2. Generate PDF
                # We need to reconstruct address strings
                full_to = f"{to_name}\n{to_street}\n{to_city}, {to_state} {to_zip}"
                full_from = f"{from_name}\n{from_street}\n{from_city}, {from_state} {from_zip}"
                
                # Check tier from session (need to persist it)
                # For MVP, we assume Standard if not Heirloom logic found, or check logic
                # Let's assume 'Standard' default or use what was selected
                # FIX: We need to persist the tier selection. 
                # For now, we default to False (Standard) unless user toggles.
                is_heirloom = False 
                
                pdf_path = letter_format.create_pdf(
                    st.session_state.transcribed_text, full_to, full_from, is_heirloom, "English", "final.pdf", sig_path
                )
                
                # 3. Send to Lob
                addr_to = {'name': to_name, 'street': to_street, 'city': to_city, 'state': to_state, 'zip': to_zip}
                addr_from = {'name': from_name, 'street': from_street, 'city': from_city, 'state': from_state, 'zip': from_zip}
                
                mailer.send_letter(pdf_path, addr_to, addr_from)
                st.write("✅ Sent to Network")
            
            st.success("Letter Mailed!")
            st.balloons()
            
            # Save Address for next time
            if st.session_state.get("user"):
                try:
                    database.update_user_address(st.session_state.user.user.email, from_name, from_street, from_city, from_state, from_zip)
                except: pass

            if st.button("Start Another"):
                reset_app()