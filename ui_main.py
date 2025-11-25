# ... (Keep Imports & Config) ...
import streamlit as st
from streamlit_drawable_canvas import st_canvas

# ... (Keep imports) ...
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
try: import mailer
except: mailer = None

YOUR_APP_URL = "https://verbapost.streamlit.app/"

# ... (Keep render_hero, show_main_app, render_store_page unchanged) ...
# ... (Paste previous versions or keep existing if unmodified) ...

# I will provide the CRITICAL update for render_review_page below.
# The rest of ui_main.py (store, workspace) is fine as previously provided.

def render_hero(title, subtitle):
    st.markdown(f"""
    <style>#hero-container h1, #hero-container div {{ color: #FFFFFF !important; }}</style>
    <div id="hero-container" style="background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); 
                padding: 40px; border-radius: 15px; text-align: center; margin-bottom: 30px;">
        <h1 style="margin: 0; font-size: 3rem; font-weight: 700;">{title}</h1>
        <div style="font-size: 1.2rem; opacity: 0.9; margin-top: 10px;">{subtitle}</div>
    </div>
    """, unsafe_allow_html=True)

def show_main_app():
    if "session_id" in st.query_params:
        st.session_state.payment_complete = True
        if "tier" in st.query_params: st.session_state.locked_tier = st.query_params["tier"]
        st.session_state.app_mode = "workspace"
        st.query_params.clear(); st.rerun()
    
    if not st.session_state.get("payment_complete"): render_store_page()
    else:
        if st.session_state.get("app_mode") == "review": render_review_page()
        else: render_workspace_page()

# ... (Assuming render_store_page and render_workspace_page are unchanged from previous working version) ...
# To be safe, here is render_workspace_page to ensure session state captures inputs

def render_store_page():
    # ... (Same as before) ...
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
            if is_free:
                if st.button("🚀 Start", type="primary", use_container_width=True):
                    # Log usage logic...
                    st.session_state.payment_complete = True; st.session_state.locked_tier = tier_code
                    st.session_state.app_mode = "workspace"; st.rerun()
            else:
                if payment_engine:
                    if st.button("Proceed to Payment", type="primary"):
                        url = payment_engine.create_checkout_session(f"VerbaPost {tier_code}", int(price*100), f"{YOUR_APP_URL}?session_id={{CHECKOUT_SESSION_ID}}&tier={tier_code}", YOUR_APP_URL)
                        st.session_state.stripe_url = url; st.rerun()
                    if st.session_state.get("stripe_url"):
                        st.link_button("👉 Pay Now", st.session_state.stripe_url, type="primary")

def render_workspace_page():
    tier = st.session_state.get("locked_tier", "Standard")
    is_civic = "Civic" in tier
    render_hero("Compose Letter", f"{tier} Edition")
    
    # Setup Profile...
    user_email = ""
    if st.session_state.get("user"):
        u = st.session_state.user
        if isinstance(u, dict): user_email = u.get("email", "")
        elif hasattr(u, "email"): user_email = u.email
        elif hasattr(u, "user"): user_email = u.user.email
    
    profile = {}
    if database and user_email: profile = database.get_user_profile(user_email) or {}
    
    with st.container(border=True):
        st.subheader("📍 Addressing")
        if is_civic:
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("#### Your Address")
                name = st.text_input("Name", value=profile.get("full_name", ""), key="from_name")
                street = st.text_input("Street", value=profile.get("address_line1", ""), key="from_street")
                c_a, c_b, c_c = st.columns(3)
                city = c_a.text_input("City", value=profile.get("address_city", ""), key="from_city")
                state = c_b.text_input("State", value=profile.get("address_state", ""), key="from_state")
                zip_code = c_c.text_input("Zip", value=profile.get("address_zip", ""), key="from_zip")
                if st.button("Find Reps"):
                    if civic_engine: 
                        st.session_state.civic_targets = civic_engine.get_reps(f"{street}, {city}, {state} {zip_code}")
            with c2:
                st.write("Representatives:")
                for t in st.session_state.get("civic_targets", []): st.success(f"{t['name']} ({t['title']})")
        else:
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("#### To (Recipient)")
                # THESE KEYS ARE CRITICAL FOR CAPTURE
                st.text_input("Full Name", key="to_name")
                st.text_input("Street Address", key="to_street")
                r1, r2, r3 = st.columns(3)
                r1.text_input("City", key="to_city")
                r2.text_input("State", key="to_state")
                r3.text_input("Zip", key="to_zip")
            with c2:
                st.markdown("#### From (You)")
                st.text_input("Your Name", value=profile.get("full_name", ""), key="from_name")
                st.text_input("Street", value=profile.get("address_line1", ""), key="from_street")
                # ... other inputs ...

    st.write("---")
    # Signature & Audio Logic...
    c_sig, c_mic = st.columns(2)
    with c_sig: st_canvas(stroke_width=2, stroke_color="#000", background_color="#fff", height=150, width=400, key="canvas")
    with c_mic: 
        audio = st.audio_input("Record")
        if audio and ai_engine:
            text = ai_engine.transcribe_audio(audio)
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
                
                # --- CAPTURE DATA ---
                recipient_data = {
                    "name": st.session_state.get("to_name", ""),
                    "street": st.session_state.get("to_street", ""),
                    "city": st.session_state.get("to_city", ""),
                    "state": st.session_state.get("to_state", ""),
                    "zip": st.session_state.get("to_zip", "")
                }
                
                # Handle Civic Special Case
                if "Civic" in tier:
                    targets = st.session_state.get("civic_targets", [])
                    names = ", ".join([t['name'] for t in targets])
                    text = f"[CIVIC TARGETS: {names}]\n\n{text}"
                    recipient_data["name"] = "Civic Blast (Multiple)"

                # SAVE
                database.save_draft(email, text, tier, price, recipient_data)
                
                # NOTIFY ADMIN IF HEIRLOOM
                if "Heirloom" in tier and mailer:
                    mailer.send_heirloom_notification(email, text)
            
            st.session_state.letter_sent = True
            st.rerun()
    else:
        st.success("✅ Letter Sent!")
        st.balloons()
        if st.button("Finish"):
            for k in list(st.session_state.keys()): 
                if k not in ["user", "user_email"]: del st.session_state[k]
            st.session_state.current_view = "splash"
            st.rerun()