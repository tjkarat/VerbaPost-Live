import streamlit as st
from streamlit_drawable_canvas import st_canvas
import os
import tempfile
from PIL import Image
import numpy as np

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
            tier_options = {"⚡ Standard": 2.99, "🏺 Heirloom": 5.99, "🏛️ Civic": 6.99}
            selected_tier_name = st.radio("Select Tier", list(tier_options.keys()))
            lang = st.selectbox("Language", ["English", "Spanish", "French"])
            price = tier_options[selected_tier_name]
            tier_code = selected_tier_name.split(" ")[1] 
            st.session_state.temp_tier = tier_code
            st.session_state.temp_price = price
    with c2:
        with st.container(border=True):
            st.subheader("Checkout")
            promo_code = st.text_input("Promo Code")
            is_free = False
            if promo_code and promo_engine:
                if promo_engine.validate_code(promo_code):
                    is_free = True; st.success("Code Applied!"); price = 0.00
                else: st.error("Invalid")
            st.metric("Total", f"${price:.2f}")
            st.divider()
            if is_free:
                if st.button("🚀 Start", type="primary", use_container_width=True):
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
                    st.info("⚠️ **Note:** Payment opens in a new tab. Return here after.")
                    if st.button("Proceed to Payment", type="primary", use_container_width=True):
                        with st.spinner("Connecting to Stripe..."):
                            url = payment_engine.create_checkout_session(
                                f"VerbaPost {tier_code}", int(price * 100),
                                f"{YOUR_APP_URL}?session_id={{CHECKOUT_SESSION_ID}}&tier={tier_code}",
                                YOUR_APP_URL
                            )
                            st.session_state.stripe_url = url
                            st.rerun()
                    if st.session_state.get("stripe_url"):
                        st.link_button("👉 Pay Now (Secure)", st.session_state.stripe_url, type="primary", use_container_width=True)
                else:
                    st.warning("No Payment Engine")
                    if st.button("Bypass"): st.session_state.payment_complete = True; st.session_state.locked_tier = tier_code; st.rerun()

def render_workspace_page():
    tier = st.session_state.get("locked_tier", "Standard")
    is_civic = "Civic" in tier
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
            c1, c2 = st.columns(2)
            with c1:
                st.text_input("Name", value=d.get("from_name",""), key="w_from_name")
                st.text_input("Street", value=d.get("from_street",""), key="w_from_street")
                c_a, c_b, c_c = st.columns(3)
                c_a.text_input("City", value=d.get("from_city",""), key="w_from_city")
                c_b.text_input("State", value=d.get("from_state",""), key="w_from_state")
                c_c.text_input("Zip", value=d.get("from_zip",""), key="w_from_zip")
                if st.button("💾 Save & Find Reps"):
                    st.session_state.draft.update({"from_name": st.session_state.w_from_name, "from_street": st.session_state.w_from_street, "from_city": st.session_state.w_from_city, "from_state": st.session_state.w_from_state, "from_zip": st.session_state.w_from_zip})
                    if database and user_email: database.update_user_profile(user_email, st.session_state.w_from_name, st.session_state.w_from_street, st.session_state.w_from_city, st.session_state.w_from_state, st.session_state.w_from_zip)
                    if civic_engine:
                        full = f"{st.session_state.w_from_street}, {st.session_state.w_from_city}, {st.session_state.w_from_state} {st.session_state.w_from_zip}"
                        with st.spinner("Locating..."):
                            st.session_state.civic_targets = civic_engine.get_reps(full)
            with c2:
                st.write("Representatives:")
                for t in st.session_state.get("civic_targets", []): st.info(f"**{t['name']}**\n{t['title']}")
        else:
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
        # Capture canvas data
        canvas_result = st_canvas(stroke_width=2, stroke_color="#000", background_color="#fff", height=150, width=400, key="canvas")
        
        # Store the image data in session state for the next step
        if canvas_result.image_data is not None:
            st.session_state.sig_data = canvas_result.image_data

    with c_mic:
        st.write("🎤 **Dictation**")
        st.info("1. Click Mic. 2. Speak. 3. Stop.")
        audio = st.audio_input("Record")
        if audio:
            # CAPTURE FIELDS BEFORE MOVING
            if is_civic:
                st.session_state.draft.update({"from_name": st.session_state.w_from_name, "from_street": st.session_state.w_from_street, "from_city": st.session_state.w_from_city, "from_state": st.session_state.w_from_state, "from_zip": st.session_state.w_from_zip})
            else:
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
    civic_targets = st.session_state.get("civic_targets", [])
    is_civic = len(civic_targets) > 0
    
    st.text_area("Body", st.session_state.get("transcribed_text", ""), height=300)
    
    if st.button("🚀 Send Letter", type="primary", use_container_width=True):
        to_addr = {"name": d.get("to_name"), "address_line1": d.get("to_street"), "address_city": d.get("to_city"), "address_state": d.get("to_state"), "address_zip": d.get("to_zip")}
        from_addr = {"name": d.get("from_name"), "address_line1": d.get("from_street"), "address_city": d.get("from_city"), "address_state": d.get("from_state"), "address_zip": d.get("from_zip")}
        text = st.session_state.get("transcribed_text", "")
        
        # --- PROCESS SIGNATURE ---
        sig_path = None
        if "sig_data" in st.session_state and st.session_state.sig_data is not None:
            # Convert numpy array to Image and save temp
            try:
                img_data = st.session_state.sig_data
                # Convert RGBA to RGB (white background)
                img = Image.fromarray(img_data.astype('uint8'), 'RGBA')
                
                # Create white background image
                background = Image.new("RGB", img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[3]) # 3 is the alpha channel
                
                # Save to temp
                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_sig:
                    background.save(tmp_sig, format="PNG")
                    sig_path = tmp_sig.name
            except Exception as e:
                print(f"Signature Error: {e}")

        # --- GENERATE PDF ---
        if mailer and letter_format:
            pdf_bytes = letter_format.create_pdf(
                body_text=text,
                recipient_info=f"{to_addr['name']}\n{to_addr['address_line1']}\n{to_addr['address_city']}, {to_addr['address_state']} {to_addr['address_zip']}",
                sender_info=f"{from_addr['name']}\n{from_addr['address_line1']}\n{from_addr['address_city']}, {from_addr['address_state']} {from_addr['address_zip']}",
                is_heirloom=is_heirloom,
                signature_path=sig_path # PASS SIGNATURE HERE
            )
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(pdf_bytes)
                pdf_path = tmp.name
            
            if is_heirloom:
                # Just Notify
                mailer.send_heirloom_notification("User", text) # Simplified for brevity
                st.success("Sent to Mailroom!")
            else:
                # Send to PostGrid
                res = mailer.send_letter(pdf_path, to_addr, from_addr)
                if res: st.success("Sent to PostGrid!")
                else: st.error("PostGrid Failed")
            
            # Cleanup
            os.remove(pdf_path)
            if sig_path: os.remove(sig_path)
            
            st.session_state.letter_sent = True
            st.rerun()