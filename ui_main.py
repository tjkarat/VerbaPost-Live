import streamlit as st
from streamlit_drawable_canvas import st_canvas
import os
from PIL import Image
from datetime import datetime
import urllib.parse
import io
import zipfile

# Import core logic
import ai_engine 
import database
import letter_format
import mailer
import zipcodes
import payment_engine
import civic_engine

# --- CONFIG ---
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
    # Wipe session
    keys = ["audio_path", "transcribed_text", "overage_agreed", "payment_complete", "stripe_url", "last_config", "processed_ids", "locked_tier"]
    for k in keys:
        if k in st.session_state: del st.session_state[k]
    st.query_params.clear()
    st.rerun()

def show_main_app():
    # --- 0. AUTO-DETECT PAYMENT RETURN ---
    qp = st.query_params
    if "session_id" in qp:
        session_id = qp["session_id"]
        if session_id not in st.session_state.get("processed_ids", []):
            if payment_engine.check_payment_status(session_id):
                st.session_state.payment_complete = True
                if "processed_ids" not in st.session_state: st.session_state.processed_ids = []
                st.session_state.processed_ids.append(session_id)
                
                st.session_state.app_mode = "workspace"
                st.toast("✅ Payment Confirmed! Workspace Unlocked.")
                
                # Restore Locked Tier
                if "tier" in qp: st.session_state.locked_tier = qp["tier"]
                
                st.query_params.clear() 
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
    #  PHASE 1: THE STORE
    # ==================================================
    if st.session_state.app_mode == "store":
        st.header("1. Select Service")
        
        service_tier = st.radio("Choose your letter type:", 
            [f"⚡ Standard (${COST_STANDARD})", f"🏺 Heirloom (${COST_HEIRLOOM})", f"🏛️ Civic (${COST_CIVIC})"],
            index=0,
            key="tier_select"
        )
        
        if "Standard" in service_tier: 
            price = COST_STANDARD
            tier_name = "Standard"
        elif "Heirloom" in service_tier: 
            price = COST_HEIRLOOM
            tier_name = "Heirloom"
        elif "Civic" in service_tier: 
            price = COST_CIVIC
            tier_name = "Civic"
        
        st.info(f"**Total: ${price}**")
        
        # PAYMENT GENERATION
        current_config = f"{service_tier}_{price}"
        if "stripe_url" not in st.session_state or st.session_state.get("last_config") != current_config:
             success_link = f"{YOUR_APP_URL}?tier={tier_name}"
             url, session_id = payment_engine.create_checkout_session(
                product_name=f"VerbaPost {service_tier}",
                amount_in_cents=int(price * 100),
                success_url=success_link, 
                cancel_url=YOUR_APP_URL
            )
             st.session_state.stripe_url = url
             st.session_state.stripe_session_id = session_id
             st.session_state.last_config = current_config
             
        if st.session_state.stripe_url:
            # NATIVE BUTTON (RELIABLE)
            st.link_button(f"💳 Pay ${price} & Start Writing", st.session_state.stripe_url, type="primary")
            st.caption("A new secure tab will open for payment. You will be returned here automatically.")
        else:
            st.error("System Error: Payment link could not be generated.")

    # ==================================================
    #  PHASE 2: THE WORKSPACE
    # ==================================================
    elif st.session_state.app_mode == "workspace":
        locked_tier = st.session_state.get("locked_tier", "Standard")
        is_heirloom = "Heirloom" in locked_tier
        is_civic = "Civic" in locked_tier

        st.success(f"🔓 **{locked_tier}** Unlocked. Ready to write.")

        # --- ADDRESSING ---
        st.subheader("2. Addressing")
        col_to, col_from = st.tabs(["👉 Recipient", "👈 Sender"])

        with col_to:
            if is_civic:
                st.info("🏛️ Auto-Detecting Representatives...")
                to_name, to_street, to_city, to_state, to_zip = "Civic", "Civic", "Civic", "TN", "00000"
            else:
                to_name = st.text_input("Recipient Name")
                to_street = st.text_input("Street Address")
                c1, c2 = st.columns(2)
                to_city = c1.text_input("City")
                to_state = c2.text_input("State")
                to_zip = c2.text_input("Zip")

        with col_from:
            # Auto-fill
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
        
        st.markdown("""
        <div style="background-color:#e8fdf5; padding:15px; border-radius:10px; border:1px solid #c3e6cb; margin-bottom:10px;">
            <h4 style="margin-top:0; color:#155724;">👇 How to Record</h4>
            <ol style="color:#155724; margin-bottom:0;">
                <li>Tap the <b>Microphone Icon</b> below.</li>
                <li>Speak your letter clearly.</li>
                <li>Tap the <b>Red Square</b> to stop.</li>
            </ol>
        </div>
        """, unsafe_allow_html=True)
        
        audio_value = st.audio_input("Record your letter")

        if audio_value:
            with st.status("⚙️ Processing...", expanded=True):
                path = "temp.wav"
                with open(path, "wb") as f: f.write(audio_value.getvalue())
                st.session_state.audio_path = path
                try:
                    text = ai_engine.transcribe_audio(path)
                    st.session_state.transcribed_text = text
                    st.session_state.app_mode = "review"
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
                sig_path = None
                if canvas_result.image_data is not None:
                    img = Image.fromarray(canvas_result.image_data.astype('uint8'), 'RGBA')
                    sig_path = "temp_signature.png"
                    img.save(sig_path)

                # PDF GEN
                full_to = f"{to_name}\n{to_street}\n{to_city}, {to_state} {to_zip}"
                full_from = f"{from_name}\n{from_street}\n{from_city}, {from_state} {from_zip}"
                
                pdf_path = letter_format.create_pdf(
                    st.session_state.transcribed_text, full_to, full_from, is_heirloom, "English", "final.pdf", sig_path
                )
                
                if not is_heirloom:
                    addr_to = {'name': to_name, 'street': to_street, 'city': to_city, 'state': to_state, 'zip': to_zip}
                    addr_from = {'name': from_name, 'street': from_street, 'city': from_city, 'state': from_state, 'zip': from_zip}
                    mailer.send_letter(pdf_path, addr_to, addr_from)
                
                with open(pdf, "rb") as f:
                    st.download_button("Download PDF", f, "letter.pdf")
            
            st.success("Letter Mailed!")
            
            # Update User Profile
            if st.session_state.get("user"):
                try:
                    database.update_user_address(st.session_state.user.user.email, from_name, from_street, from_city, from_state, from_zip)
                except: pass

            if st.button("Start Another"): reset_app()
EOF