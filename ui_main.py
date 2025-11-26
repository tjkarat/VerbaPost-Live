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
    <style>#hero-container h1, #hero-container div {{ color: #FFFFFF !important; }}</style>
    <div id="hero-container" style="background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); 
                padding: 40px; border-radius: 15px; text-align: center; 
                margin-bottom: 30px; box-shadow: 0 8px 16px rgba(0,0,0,0.1);">
        <h1 style="margin: 0; font-size: 3rem; font-weight: 700;">{title}</h1>
        <div style="font-size: 1.2rem; opacity: 0.9; margin-top: 10px;">{subtitle}</div>
    </div>
    """, unsafe_allow_html=True)

def show_main_app():
    if "draft" not in st.session_state: st.session_state.draft = {}

    if "session_id" in st.query_params:
        st.session_state.payment_complete = True
        if "tier" in st.query_params: st.session_state.locked_tier = st.query_params["tier"]
        st.session_state.app_mode = "workspace"
        st.query_params.clear(); st.rerun()

    if not st.session_state.get("payment_complete"): render_store_page()
    else:
        if st.session_state.get("app_mode") == "review": render_review_page()
        else: render_workspace_page()

def render_store_page():
    render_hero("Select Service", "Choose your letter type")
    c1, c2 = st.columns([2, 1])
    
    with c1:
        with st.container(border=True):
            st.subheader("Letter Options")
            
            tier_display = {
                "Standard": "⚡ Standard ($2.99) - Machine postage.",
                "Heirloom": "🏺 Heirloom ($5.99) - Handwritten & Stamp.",
                "Civic": "🏛️ Civic ($6.99) - 3 Letters to Congress.",
                "Santa": "🎅 Santa ($9.99) - From North Pole!" 
            }
            
            selected_option = st.radio(
                "Select Tier", 
                options=list(tier_display.keys()),
                format_func=lambda x: tier_display[x]
            )
            
            if selected_option == "Standard":
                st.info("**Standard:** Premium paper, window envelope, First Class Mail.")
            elif selected_option == "Heirloom":
                st.info("**Heirloom:** Hand-addressed envelope with a physical stamp.")
            elif selected_option == "Civic":
                st.info("**Civic:** Auto-sends to your 2 Senators and 1 Rep.")
            elif selected_option == "Santa":
                st.success("**Santa Special:** Festive background, North Pole return address, mailed to your child (or adult!).")

            lang = st.selectbox("Language", ["English", "Spanish", "French"])
            
            prices = {"Standard": 2.99, "Heirloom": 5.99, "Civic": 6.99, "Santa": 9.99}
            price = prices[selected_option]
            tier_code = selected_option 
            
            st.session_state.temp_tier = tier_code
            st.session_state.temp_price = price
            st.session_state.temp_lang = lang

    with c2:
        with st.container(border=True):
            st.subheader("Checkout")
            promo_code = st.text_input("Promo Code (Optional)")
            is_free = False
            if promo_code and promo_engine:
                if promo_engine.validate_code(promo_code):
                    is_free = True; st.success("✅ Code Applied!"); price = 0.00
                else: st.error("Invalid Code")
            st.metric("Total", f"${price:.2f}")
            st.divider()
            if is_free:
                if st.button("🚀 Start (Promo Applied)", type="primary", use_container_width=True):
                    u_email = "guest"
                    if st.session_state.get("user"):
                        u = st.session_state.user
                        if isinstance(u, dict): u_email = u.get("email")
                        elif hasattr(u, "email"): u_email = u.email
                        elif hasattr(u, "user"): u_email = u.user.email
                    promo_engine.log_usage(promo_code, u_email)
                    st.session_state.payment_complete = True; st.session_state.locked_tier = tier_code
                    st.session_state.app_mode = "workspace"; st.rerun()
            else:
                if payment_engine:
                    st.info("⚠️ **Note:** Payment opens in a new tab.")
                    if st.button("Proceed to Payment", type="primary", use_container_width=True):
                        with st.spinner("Connecting to Stripe..."):
                            result = payment_engine.create_checkout_session(
                                f"VerbaPost {tier_code}", 
                                int(price * 100), 
                                f"{YOUR_APP_URL}?session_id={{CHECKOUT_SESSION_ID}}&tier={tier_code}", 
                                YOUR_APP_URL
                            )
                            if result and result[0]:
                                st.session_state.stripe_url = result[0]
                                st.rerun()
                            else:
                                st.error("Stripe Error: Check Logs/Secrets")
                    
                    if st.session_state.get("stripe_url"):
                        url = st.session_state.stripe_url
                        st.markdown(f"""
                        <style>
                            a.pay-btn-link, a.pay-btn-link:visited {{ color: #FFFFFF !important; text-decoration: none !important; }}
                        </style>
                        <a href="{url}" target="_blank" class="pay-btn-link">
                            <div style="display: block; width: 100%; padding: 14px; background-color: #2a5298; text-align: center; border-radius: 8px; margin-top: 10px; font-weight: bold;">
                                <span style="color: #FFFFFF !important;">👉 Pay Now (Secure)</span>
                            </div>
                        </a>
                        """, unsafe_allow_html=True)
                else:
                    st.warning("No Payment Engine")
                    if st.button("Bypass"): st.session_state.payment_complete = True; st.session_state.locked_tier = tier_code; st.rerun()

def render_workspace_page():
    tier = st.session_state.get("locked_tier", "Standard")
    is_civic = "Civic" in tier
    is_santa = "Santa" in tier
    
    render_hero("Compose Letter", f"{tier} Edition")
    
    user_email = ""
    if st.session_state.get("user"):
        u = st.session_state.user
        if isinstance(u, dict): user_email = u.get("email", "")
        elif hasattr(u, "email"): user_email = u.email
        elif hasattr(u, "user"): user_email = u.user.email

    if not st.session_state.draft.get("from_name") and database and user_email:
        profile = database.get_user_profile(user_email) or {}
        st.session_state.draft.update({
            "from_name": profile.get("full_name", ""), "from_street": profile.get("address_line1", ""),
            "from_city": profile.get("address_city", ""), "from_state": profile.get("address_state", ""),
            "from_zip": profile.get("address_zip", "")
        })
    d = st.session_state.draft

    with st.container(border=True):
        st.subheader("📍 Addressing")
        st.warning("⚠️ **Important:** Press **Enter** after typing in each field.")
        
        if is_civic:
            # ... (Civic Logic Omitted for brevity - same as before) ...
            st.info("Civic Mode Active")
        
        # --- SANTA LOGIC (New) ---
        elif is_santa:
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**To (Child/Recipient)**")
                st.text_input("Child's Name", value=d.get("to_name",""), key="w_to_name")
                st.text_input("Street", value=d.get("to_street",""), key="w_to_street")
                c_x, c_y, c_z = st.columns(3)
                c_x.text_input("City", value=d.get("to_city",""), key="w_to_city")
                c_y.text_input("State", value=d.get("to_state",""), key="w_to_state")
                c_z.text_input("Zip", value=d.get("to_zip",""), key="w_to_zip")
            
            with c2:
                st.markdown("**From (North Pole)**")
                # Locked inputs for Santa
                st.text_input("Sender", value="Santa Claus", disabled=True)
                st.text_input("Address", value="123 Elf Road", disabled=True)
                st.text_input("Location", value="North Pole, 88888", disabled=True)
                
                # Hidden values for state update
                st.session_state.w_from_name = "Santa Claus"
                st.session_state.w_from_street = "123 Elf Road"
                st.session_state.w_from_city = "North Pole"
                st.session_state.w_from_state = "NP"
                st.session_state.w_from_zip = "88888"
                
                if st.button("💾 Save Recipient"):
                    st.session_state.draft.update({
                        "to_name": st.session_state.w_to_name, "to_street": st.session_state.w_to_street, 
                        "to_city": st.session_state.w_to_city, "to_state": st.session_state.w_to_state, 
                        "to_zip": st.session_state.w_to_zip, 
                        "from_name": "Santa Claus", "from_street": "123 Elf Road", 
                        "from_city": "North Pole", "from_state": "NP", "from_zip": "88888"
                    })
                    st.toast("Saved!")

        else:
            # Standard Logic (Same as before)
            c1, c2 = st.columns(2)
            with c1:
                st.text_input("To Name", value=d.get("to_name",""), key="w_to_name")
                st.text_input("To Street", value=d.get("to_street",""), key="w_to_street")
                c_x, c_y, c_z = st.columns(3)
                c_x.text_input("City", value=d.get("to_city",""), key="w_to_city")
                c_y.text_input("State", value=d.get("to_state",""), key="w_to_state")
                c_z.text_input("Zip", value=d.get("to_zip",""), key="w_to_zip")
            with c2:
                st.text_input("From Name", value=d.get("from_name",""), key="w_from_name")
                st.text_input("From Street", value=d.get("from_street",""), key="w_from_street")
                c_a, c_b, c_c = st.columns(3)
                c_a.text_input("City", value=d.get("from_city",""), key="w_from_city")
                c_b.text_input("State", value=d.get("from_state",""), key="w_from_state")
                c_c.text_input("Zip", value=d.get("from_zip",""), key="w_from_zip")
                if st.button("💾 Save My Address"):
                    st.session_state.draft.update({"from_name": st.session_state.w_from_name, "from_street": st.session_state.w_from_street, "from_city": st.session_state.w_from_city, "from_state": st.session_state.w_from_state, "from_zip": st.session_state.w_from_zip})
                    if database and user_email: database.update_user_profile(user_email, st.session_state.w_from_name, st.session_state.w_from_street, st.session_state.w_from_city, st.session_state.w_from_state, st.session_state.w_from_zip)
                    st.toast("Saved!")

    st.write("---")
    c_sig, c_mic = st.columns(2)
    with c_sig:
        st.write("✍️ **Signature**")
        canvas = st_canvas(stroke_width=2, stroke_color="#000", background_color="#fff", height=150, width=400, key="canvas")
        if canvas.image_data is not None: st.session_state.sig_data = canvas.image_data

    with c_mic:
        st.write("🎤 **Dictation**")
        st.info("1. Click Mic 🎙️ 2. Speak 3. Stop")
        audio = st.audio_input("Record")
        if audio:
            # Auto-save state
            if not is_civic and not is_santa:
                 st.session_state.draft.update({"to_name": st.session_state.w_to_name, "to_street": st.session_state.w_to_street, "to_city": st.session_state.w_to_city, "to_state": st.session_state.w_to_state, "to_zip": st.session_state.w_to_zip, "from_name": st.session_state.w_from_name, "from_street": st.session_state.w_from_street, "from_city": st.session_state.w_from_city, "from_state": st.session_state.w_from_state, "from_zip": st.session_state.w_from_zip})
            
            with st.status("Processing...") as status:
                if ai_engine:
                    text = ai_engine.transcribe_audio(audio)
                    st.session_state.transcribed_text = text
                    st.session_state.app_mode = "review"
                    st.rerun()

def render_review_page():
    render_hero("Review Letter", "Finalize and send")
    if st.button("⬅️ Edit"): st.session_state.app_mode = "workspace"; st.rerun()
    
    d = st.session_state.get("draft", {})
    tier = st.session_state.get("locked_tier", "Standard")
    is_heirloom = "Heirloom" in tier
    is_santa = "Santa" in tier
    
    is_sent = st.session_state.get("letter_sent", False)
    
    if is_sent:
        st.success("✅ Letter Processed Successfully!")
        st.info("Your letter has been queued.")
        if st.button("🏁 Finish & Return Home", type="primary", use_container_width=True):
            for k in ["payment_complete", "locked_tier", "transcribed_text", "letter_sent", "app_mode", "stripe_url