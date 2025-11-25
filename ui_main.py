import streamlit as st
from streamlit_drawable_canvas import st_canvas

# --- IMPORTS ---
try: import database
except: database = None
try: import ai_engine
except: ai_engine = None
try: import payment_engine
except: payment_engine = None
try: import promo_engine
except: promo_engine = None

# --- CONFIG ---
YOUR_APP_URL = "https://verbapost.streamlit.app/" 

def render_hero(title, subtitle):
    st.markdown(f"""
    <style>
    #hero-container h1, #hero-container div {{ color: #FFFFFF !important; }}
    </style>
    <div id="hero-container" style="background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); 
                padding: 40px; border-radius: 15px; text-align: center; 
                margin-bottom: 30px; box-shadow: 0 8px 16px rgba(0,0,0,0.1);">
        <h1 style="margin: 0; font-size: 3rem; font-weight: 700;">{title}</h1>
        <div style="font-size: 1.2rem; opacity: 0.9; margin-top: 10px;">{subtitle}</div>
    </div>
    """, unsafe_allow_html=True)

def show_main_app():
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
            
            # Promo Logic
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
                # Paid Path
                if payment_engine:
                    if st.button("Proceed to Payment", type="primary", use_container_width=True):
                        with st.spinner("Connecting to Stripe..."):
                            checkout_url = payment_engine.create_checkout_session(
                                f"VerbaPost {tier_code}", int(price * 100),
                                f"{YOUR_APP_URL}?session_id={{CHECKOUT_SESSION_ID}}&tier={tier_code}",
                                YOUR_APP_URL
                            )
                            st.session_state.stripe_url = checkout_url
                            st.rerun()
                    
                    # Show the link button if generated
                    if st.session_state.get("stripe_url"):
                        st.info("⚠️ **Note:** Payment opens in a new tab. After paying, return here to continue.")
                        st.link_button("👉 Pay Now (Secure)", st.session_state.stripe_url, type="primary", use_container_width=True)
                else:
                    st.warning("Payment engine missing.")
                    if st.button("Bypass (Dev)"):
                        st.session_state.payment_complete = True
                        st.session_state.locked_tier = tier_code
                        st.rerun()

def render_workspace_page():
    tier = st.session_state.get("locked_tier", "Standard")
    render_hero("Compose Letter", f"{tier} Edition")
    
    user_email = ""
    if st.session_state.get("user"):
        u = st.session_state.user
        if isinstance(u, dict): user_email = u.get("email", "")
        elif hasattr(u, "email"): user_email = u.email
        elif hasattr(u, "user"): user_email = u.user.email

    profile = {}
    if database and user_email: profile = database.get_user_profile(user_email)
    
    def_name = profile.get("full_name", "")
    def_street = profile.get("address_line1", "")
    def_city = profile.get("address_city", "")
    def_state = profile.get("address_state", "")
    def_zip = profile.get("address_zip", "")

    with st.container(border=True):
        st.subheader("📍 Addressing")
        c_to, c_from = st.columns(2)
        with c_to:
            st.markdown("#### 👉 To (Recipient)")
            st.text_input("Full Name", key="to_name")
            st.text_input("Street Address", key="to_street")
            r1, r2, r3 = st.columns([2, 1, 1])
            r1.text_input("City", key="to_city")
            r2.text_input("State", key="to_state")
            r3.text_input("Zip", key="to_zip")
        with c_from:
            st.markdown("#### 👈 From (You)")
            name = st.text_input("Your Name", value=def_name, key="from_name")
            street = st.text_input("Street Address", value=def_street, key="from_street")
            s1, s2, s3 = st.columns([2, 1, 1])
            city = s1.text_input("City", value=def_city, key="from_city")
            state = s2.text_input("State", value=def_state, key="from_state")
            zip_code = s3.text_input("Zip", value=def_zip, key="from_zip")
            if st.button("💾 Save My Address"):
                if database and user_email:
                    database.update_user_profile(user_email, name, street, city, state, zip_code)
                    st.toast("✅ Saved!")

    st.write("---")
    
    c_sig, c_mic = st.columns(2)
    with c_sig:
        st.write("✍️ **Signature**")
        st_canvas(stroke_width=2, stroke_color="#000", background_color="#fff", height=150, width=400, key="canvas")
    
    with c_mic:
        st.write("🎤 **Dictation**")
        with st.expander("How to Record", expanded=True):
            st.write("1. Click Mic. 2. Speak. 3. Click Red Square.")
        audio = st.audio_input("Record Message")
        if audio:
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
    is_sent = st.session_state.get("letter_sent", False)
    st.text_area("Body", st.session_state.get("transcribed_text", ""), height=300, disabled=is_sent)
    
    if not is_sent:
        if st.button("🚀 Send Letter", type="primary", use_container_width=True):
            if database and st.session_state.get("user"):
                u = st.session_state.user
                email = ""
                if isinstance(u, dict): email = u.get("email")
                elif hasattr(u, "email"): email = u.email
                elif hasattr(u, "user"): email = u.user.email
                
                tier = st.session_state.get("locked_tier", "Standard")
                text = st.session_state.get("transcribed_text", "")
                price = st.session_state.get("temp_price", 2.99)
                database.save_draft(email, text, tier, price)
            
            st.session_state.letter_sent = True
            st.rerun()
    else:
        st.success("✅ Letter Sent to Mailroom successfully!")
        st.balloons()
        if st.button("🏁 Finish & Return Home", type="primary", use_container_width=True):
            for k in ["payment_complete", "locked_tier", "transcribed_text", "letter_sent", "app_mode", "stripe_url"]:
                if k in st.session_state: del st.session_state[k]
            st.session_state.current_view = "splash"
            st.rerun()