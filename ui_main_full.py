import streamlit as st
from streamlit_drawable_canvas import st_canvas
import os
import tempfile
from PIL import Image
import json
import base64
from io import BytesIO

# --- IMPORTS ---
try: import database
except: database = None
try: import ai_engine
except: ai_engine = None
try: import payment_engine
except: payment_engine = None
try: import promo_engine
except: promo_engine = None
try: import civic_engine
except: civic_engine = None
try: import letter_format
except: letter_format = None
try: import mailer
except: mailer = None

# --- CONFIG ---
YOUR_APP_URL = "https://verbapost.streamlit.app/" 

def render_hero(title, subtitle):
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); 
                padding: 40px; border-radius: 15px; text-align: center; 
                margin-bottom: 30px; box-shadow: 0 8px 16px rgba(0,0,0,0.1);">
        <h1 style="margin: 0; font-size: 3rem; font-weight: 700; color: white !important;">{title}</h1>
        <div style="font-size: 1.2rem; opacity: 0.9; margin-top: 10px; color: white !important;">{subtitle}</div>
    </div>
    """, unsafe_allow_html=True)

def render_store_page():
    render_hero("Select Service", "Choose your letter type")
    c1, c2 = st.columns([2, 1])
    with c1:
        with st.container(border=True):
            st.subheader("Letter Options")
            tier_options = {"⚡ Standard": 2.99, "🏺 Heirloom": 5.99, "🏛️ Civic": 6.99, "🎅 Santa": 9.99}
            selected_tier_name = st.radio("Select Tier", list(tier_options.keys()))
            lang = st.selectbox("Language", ["English", "Spanish", "French"])
            price = tier_options[selected_tier_name]
            tier_code = selected_tier_name.split(" ")[1] 
            
            # Extra info boxes
            if "Standard" in selected_tier_name: st.info("Machine printed, window envelope.")
            elif "Heirloom" in selected_tier_name: st.info("Hand-addressed, real stamp.")
            elif "Civic" in selected_tier_name: st.info("3 letters to your representatives.")
            elif "Santa" in selected_tier_name: st.success("Festive background, North Pole return address.")

    with c2:
        with st.container(border=True):
            st.subheader("Checkout")
            st.metric("Total", f"${price:.2f}")
            
            promo_code = st.text_input("Promo Code (Optional)")
            is_free = False
            if promo_code and promo_engine and promo_engine.validate_code(promo_code):
                is_free = True
                st.success("Code Applied!")

            if is_free:
                if st.button("🚀 Start (Free)", type="primary", use_container_width=True):
                    st.session_state.payment_complete = True
                    st.session_state.locked_tier = tier_code
                    st.session_state.selected_language = lang
                    st.session_state.app_mode = "workspace"
                    st.rerun()
            else:
                st.info("⚠️ **Note:** Payment opens in a new tab.")
                if st.button(f"Pay ${price} & Start", type="primary", use_container_width=True):
                    # Save Draft First
                    u_email = "guest"
                    if st.session_state.get("user_email"): u_email = st.session_state.user_email
                    
                    if database: database.save_draft(u_email, "", tier_code, price)
                    
                    # Generate Stripe Link
                    if payment_engine:
                        url, sess_id = payment_engine.create_checkout_session(
                            f"VerbaPost {tier_code}", 
                            int(price * 100), 
                            f"{YOUR_APP_URL}?session_id={{CHECKOUT_SESSION_ID}}&tier={tier_code}", 
                            YOUR_APP_URL
                        )
                        if url:
                            st.link_button("Click to Pay", url, type="primary", use_container_width=True)
                        else:
                            st.error("Payment Error")

def render_workspace_page():
    tier = st.session_state.get("locked_tier", "Standard")
    is_civic = "Civic" in tier
    is_santa = "Santa" in tier
    
    render_hero("Compose Letter", f"{tier} Edition")

    # --- ADDRESSING ---
    d = st.session_state.get("draft", {})
    
    with st.container(border=True):
        st.subheader("📍 Addressing")
        
        if is_santa:
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**To (Child/Recipient)**")
                to_name = st.text_input("Name", key="w_to_name")
                to_street = st.text_input("Street", key="w_to_street")
                c_x, c_y, c_z = st.columns(3)
                to_city = c_x.text_input("City", key="w_to_city")
                to_state = c_y.text_input("State", key="w_to_state")
                to_zip = c_z.text_input("Zip", key="w_to_zip")
            with c2:
                st.markdown("**From (North Pole)**")
                st.info("Sender locked to Santa Claus")
                # Hidden defaults for Santa
                from_name="Santa Claus"; from_street="123 Elf Road"; from_city="North Pole"; from_state="NP"; from_zip="88888"
                
        elif is_civic:
            st.info("Civic Mode: We will find your representatives automatically.")
            st.markdown("**Your Return Address**")
            from_name = st.text_input("Your Name", key="w_from_name")
            from_street = st.text_input("Street", key="w_from_street")
            c1, c2, c3 = st.columns(3)
            from_city = c1.text_input("City", key="w_from_city")
            from_state = c2.text_input("State", key="w_from_state")
            from_zip = c3.text_input("Zip", key="w_from_zip")
            to_name="Civic"; to_street="Civic"; to_city="Civic"; to_state="TN"; to_zip="00000"
            
        else:
            # Standard / Heirloom
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("To")
                to_name = st.text_input("To Name", key="w_to_name")
                to_street = st.text_input("To Street", key="w_to_street")
                c_x, c_y, c_z = st.columns(3)
                to_city = c_x.text_input("City", key="w_to_city")
                to_state = c_y.text_input("State", key="w_to_state")
                to_zip = c_z.text_input("Zip", key="w_to_zip")
            with c2:
                st.markdown("From")
                from_name = st.text_input("From Name", key="w_from_name")
                from_street = st.text_input("From Street", key="w_from_street")
                c_a, c_b, c_c = st.columns(3)
                from_city = c_a.text_input("City", key="w_from_city")
                from_state = c_b.text_input("State", key="w_from_state")
                from_zip = c_c.text_input("Zip", key="w_from_zip")

        if st.button("Save Addresses"):
             # Save to session logic here
             st.session_state.saved_to = {"name": to_name, "street": to_street, "city": to_city, "state": to_state, "zip": to_zip}
             st.session_state.saved_from = {"name": from_name, "street": from_street, "city": from_city, "state": from_state, "zip": from_zip}
             st.toast("Addresses Saved!")

    st.write("---")
    
    # --- SIGNATURE & DICTATION ---
    c_sig, c_mic = st.columns(2)
    with c_sig:
        st.write("✍️ **Signature**")
        canvas = st_canvas(stroke_width=2, stroke_color="#000", background_color="#fff", height=150, width=400, key="canvas")
        if canvas.image_data is not None: st.session_state.sig_data = canvas.image_data

    with c_mic:
        st.write("🎤 **Dictation**")
        audio = st.audio_input("Record")
        if audio:
            with st.status("Transcribing..."):
                if ai_engine:
                    text = ai_engine.transcribe_audio(audio)
                    st.session_state.transcribed_text = text
                    st.session_state.app_mode = "review"
                    st.rerun()

def render_review_page():
    render_hero("Review Letter", "Finalize and send")
    
    txt = st.text_area("Body", st.session_state.get("transcribed_text", ""), height=300)
    
    if st.button("🚀 Send Letter", type="primary", use_container_width=True):
        st.success("Letter Sent! (Simulation)")
        if st.button("Finish"):
             st.session_state.app_mode = "splash"
             st.rerun()
