import streamlit as st
from streamlit_drawable_canvas import st_canvas
import os
import tempfile

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
    # Initialize Draft if not exists
    if "draft" not in st.session_state:
        st.session_state.draft = {}

    if "session_id" in st.query_params:
        st.session_state.payment_complete = True
        if "tier" in st.query_params: st.session_state.locked_tier = st.query_params["tier"]
        st.session_state.app_mode = "workspace"
        st.query_params.clear() 
        st.rerun()

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
            promo_code = st.text_input("Promo Code (Optional)")
            is_free = False
            if promo_code and promo_engine:
                if promo_engine.validate_code(promo_code):
                    is_free = True
                    st.success("✅ Code Applied!")
                    price = 0.00
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
                    st.session_state.payment_complete = True
                    st.session_state.locked_tier = tier_code
                    st.session_state.app_mode = "workspace"
                    st.rerun()
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
                    st.warning("Payment engine missing.")
                    if st.button("Bypass (Dev)"):
                        st.session_state.payment_complete = True
                        st.session_state.locked_tier = tier_code
                        st.rerun()

def render_workspace_page():
    tier = st.session_state.get("locked_tier", "Standard")
    is_civic = "Civic" in tier
    render_hero("Compose Letter", f"{tier} Edition")
    
    # --- AUTO-POPULATE LOGIC ---
    user_email = ""
    if st.session_state.get("user"):
        u = st.session_state.user
        if isinstance(u, dict): user_email = u.get("email", "")
        elif hasattr(u, "email"): user_email = u.email
        elif hasattr(u, "user"): user_email = u.user.email

    # Load Defaults from Profile if Draft is Empty
    if not st.session_state.draft.get("from_name") and database and user_email:
        profile = database.get_user_profile(user_email) or {}
        st.session_state.draft.update({
            "from_name": profile.get("full_name", ""),
            "from_street": profile.get("address_line1", ""),
            "from_city": profile.get("address_city", ""),
            "from_state": profile.get("address_state", ""),
            "from_zip": profile.get("address_zip", "")
        })

    # Helper to read from Draft
    d = st.session_state.draft

    with st.container(border=True):
        st.subheader("📍 Addressing")
        st.warning("⚠️ **Important:** Please fill out these fields carefully. They are required for mailing.")

        if is_civic:
            c1, c2 = st.columns([1, 1])
            with c1:
                st.markdown("#### 👈 Your Address (Required)")
                # BINDING DIRECTLY TO KEY allows Streamlit to track the value
                st.text_input("Your Name", value=d.get("from_name", ""), key="w_from_name")
                st.text_input("Street Address", value=d.get("from_street", ""), key="w_from_street")
                s1, s2, s3 = st.columns([2, 1, 1])
                s1.text_input("City", value=d.get("from_city", ""), key="w_from_city")
                s2.text_input("State", value=d.get("from_state", ""), key="w_from_state")
                s3.text_input("Zip", value=d.get("from_zip", ""), key="w_from_zip")
                
                if st.button("💾 Save & Find Reps"):
                    # CAPTURE VALUES TO DRAFT IMMEDIATELY
                    st.session_state.draft.update({
                        "from_name": st.session_state.w_from_name,
                        "from_street": st.session_state.w_from_street,
                        "from_city": st.session_state.w_from_city,
                        "from_state": st.session_state.w_from_state,
                        "from_zip": st.session_state.w_from_zip
                    })
                    
                    if database and user_email:
                        database.update_user_profile(user_email, st.session_state.w_from_name, 
                                                     st.session_state.w_from_street, st.session_state.w_from_city, 
                                                     st.session_state.w_from_state, st.session_state.w_from_zip)
                        
                    if civic_engine and st.session_state.w_from_street and st.session_state.w_from_zip:
                        full_addr = f"{st.session_state.w_from_street}, {st.session_state.w_from_city}, {st.session_state.w_from_state} {st.session_state.w_from_zip}"
                        with st.spinner("Locating..."):
                            targets = civic_engine.get_reps(full_addr)
                            st.session_state.civic_targets = targets
            
            with c2:
                st.markdown("#### 🏛️ Your Representatives")
                targets = st.session_state.get("civic_targets", [])
                if targets:
                    for t in targets:
                        st.info(f"**{t['name']}**\n{t['title']}")
                else:
                    st.info("Click 'Save & Find Reps' to load.")

        else:
            # STANDARD MODE
            c_to, c_from = st.columns(2)
            with c_to:
                st.markdown("#### 👉 To (Recipient)")
                st.text_input("Full Name", value=d.get("to_name", ""), key="w_to_name")
                st.text_input("Street Address", value=d.get("to_street", ""), key="w_to_street")
                r1, r2, r3 = st.columns([2, 1, 1])
                r1.text_input("City", value=d.get("to_city", ""), key="w_to_city")
                r2.text_input("State", value=d.get("to_state", ""), key="w_to_state")
                r3.text_input("Zip", value=d.get("to_zip", ""), key="w_to_zip")
            
            with c_from:
                st.markdown("#### 👈 From (You)")
                st.text_input("Your Name", value=d.get("from_name", ""), key="w_from_name")
                st.text_input("Street Address", value=d.get("from_street", ""), key="w_from_street")
                s1, s2, s3 = st.columns([2, 1, 1])
                s1.text_input("City", value=d.get("from_city", ""), key="w_from_city")
                s2.text_input("State", value=d.get("from_state", ""), key="w_from_state")
                s3.text_input("Zip", value=d.get("from_zip", ""), key="w_from_zip")
                
                if st.button("💾 Save My Address"):
                    # Capture
                    st.session_state.draft.update({
                        "from_name": st.session_state.w_from_name,
                        "from_street": st.session_state.w_from_street,
                        "from_city": st.session_state.w_from_city,
                        "from_state": st.session_state.w_from_state,
                        "from_zip": st.session_state.w_from_zip
                    })
                    if database and user_email:
                        database.update_user_profile(user_email, st.session_state.w_from_name, 
                                                     st.session_state.w_from_street, st.session_state.w_from_city, 
                                                     st.session_state.w_from_state, st.session_state.w_from_zip)
                        st.toast("✅ Saved!")

    st.write("---")
    
    c_sig, c_mic = st.columns(2)
    with c_sig:
        st.write("✍️ **Signature**")
        st_canvas(stroke_width=2, stroke_color="#000", background_color="#fff", height=150, width=400, key="canvas")
    
    with c_mic:
        st.write("🎤 **Dictation**")
        st.info("1. Click Mic 🎙️\n2. Speak your letter\n3. Click Red Square ⏹️ to Stop")
        audio = st.audio_input("Record Message")
        if audio:
            # --- CRITICAL FIX: CAPTURE DATA BEFORE LEAVING ---
            # Even if they didn't hit save, we grab the current values from the input widgets
            if is_civic:
                st.session_state.draft.update({
                    "from_name": st.session_state.w_from_name,
                    "from_street": st.session_state.w_from_street,
                    "from_city": st.session_state.w_from_city,
                    "from_state": st.session_state.w_from_state,
                    "from_zip": st.session_state.w_from_zip
                })
            else:
                st.session_state.draft.update({
                    "to_name": st.session_state.w_to_name,
                    "to_street": st.session_state.w_to_street,
                    "to_city": st.session_state.w_to_city,
                    "to_state": st.session_state.w_to_state,
                    "to_zip": st.session_state.w_to_zip,
                    "from_name": st.session_state.w_from_name,
                    "from_street": st.session_state.w_from_street,
                    "from_city": st.session_state.w_from_city,
                    "from_state": st.session_state.w_from_state,
                    "from_zip": st.session_state.w_from_zip
                })

            with st.status("🤖 Processing...", expanded=True) as status:
                st.write("Transcribing audio...")
                if ai_engine:
                    text = ai_engine.transcribe_audio(audio)
                    if "Error" in text:
                        status.update(label="❌ Failed", state="error")
                        st.error(text)
                    else:
                        status.update(label="✅ Done!", state="complete")
                        st.session_state.transcribed_text = text
                        st.session_state.app_mode = "review"
                        st.rerun()

def render_review_page():
    render_hero("Review Letter", "Finalize and send")
    
    if st.button("⬅️ Go Back to Edit"):
        st.session_state.app_mode = "workspace"
        st.rerun()

    # Pull from the SAVED DRAFT, not the raw widgets
    d = st.session_state.get("draft", {})
    tier = st.session_state.get("locked_tier", "Standard")
    civic_targets = st.session_state.get("civic_targets", [])
    is_civic = len(civic_targets) > 0
    is_heirloom = "Heirloom" in tier
    
    if is_civic: st.info(f"🏛️ **Civic Blast:** Mailing {len(civic_targets)} reps.")
    
    is_sent = st.session_state.get("letter_sent", False)
    st.text_area("Body", st.session_state.get("transcribed_text", ""), height=300, disabled=is_sent)
    
    if not is_sent:
        if st.button("🚀 Send Letter", type="primary", use_container_width=True):
            
            # VALIDATION (Now checks the draft dictionary)
            missing = []
            if not is_civic:
                if not d.get("to_name"): missing.append("Recipient Name")
                if not d.get("to_street"): missing.append("Recipient Street")
            if not d.get("from_street"): missing.append("Your Street")
            
            if missing:
                st.error(f"⚠️ Missing: {', '.join(missing)}")
                st.stop()

            # PREPARE DATA
            to_addr = {
                "name": d.get("to_name", ""), "address_line1": d.get("to_street", ""),
                "address_city": d.get("to_city", ""), "address_state": d.get("to_state", ""),
                "address_zip": d.get("to_zip", "")
            }
            from_addr = {
                "name": d.get("from_name", ""), "address_line1": d.get("from_street", ""),
                "address_city": d.get("from_city", ""), "address_state": d.get("from_state", ""),
                "address_zip": d.get("from_zip", "")
            }

            u_email = "guest"
            if st.session_state.get("user"):
                u = st.session_state.user
                if isinstance(u, dict): u_email = u.get("email")
                elif hasattr(u, "email"): u_email = u.email
                elif hasattr(u, "user"): u_email = u.user.email
            
            text = st.session_state.get("transcribed_text", "")
            price = st.session_state.get("temp_price", 2.99)

            # SENDING
            if is_heirloom:
                if database: database.save_draft(u_email, text, tier, price, to_addr, status="pending")
                if mailer: mailer.send_heirloom_notification(u_email, text)
            else:
                if mailer and letter_format:
                    pdf_bytes = letter_format.create_pdf(text, f"{to_addr['name']}\n{to_addr['address_line1']}", from_addr['name'], False)
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                        tmp.write(pdf_bytes)
                        tmp_path = tmp.name
                    
                    with st.spinner("Transmitting to PostGrid..."):
                        result = mailer.send_letter(tmp_path, to_addr, from_addr)
                        
                    os.remove(tmp_path)
                    status = "sent_api" if result else "failed"
                    if database: database.save_draft(u_email, text, tier, price, to_addr, status=status)
                    
                    if result: 
                        st.success("✅ Successfully transmitted to PostGrid!")
                        with st.expander("View PostGrid Response"): st.json(result)
                    else: st.error("❌ Automated sending failed. Admin notified.")

            st.session_state.letter_sent = True
            st.rerun()
    else:
        st.success("✅ Letter Processed Successfully!")
        if st.button("🏁 Finish & Return Home", type="primary", use_container_width=True):
            for k in ["payment_complete", "locked_tier", "transcribed_text", "letter_sent", "app_mode", "stripe_url", "civic_targets", "draft"]:
                if k in st.session_state: del st.session_state[k]
            st.session_state.current_view = "splash"
            st.rerun()