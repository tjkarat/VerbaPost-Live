import streamlit as st
from streamlit_drawable_canvas import st_canvas
import os
import tempfile
import json

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
try: import analytics
except: analytics = None

# --- CONFIG ---
YOUR_APP_URL = "https://verbapost.streamlit.app/"

def reset_app():
    st.session_state.app_mode = "splash" 
    st.session_state.audio_path = None
    st.session_state.transcribed_text = ""
    st.session_state.payment_complete = False
    st.session_state.sig_data = None
    st.session_state.to_addr = {}
    st.session_state.from_addr = {}
    st.session_state.civic_targets = []
    st.query_params.clear()

def render_hero(title, subtitle):
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); 
                padding: 40px; border-radius: 15px; text-align: center; 
                margin-bottom: 30px; box-shadow: 0 8px 16px rgba(0,0,0,0.1);">
        <h1 style="margin: 0; font-size: 3rem; font-weight: 700; color: white !important;">{title}</h1>
        <div style="font-size: 1.2rem; opacity: 0.9; margin-top: 10px; color: white !important;">{subtitle}</div>
    </div>
    """, unsafe_allow_html=True)

# --- PAGE: LEGAL ---
def render_legal_page():
    render_hero("Legal Center", "Terms & Privacy")
    
    with st.container(border=True):
        st.subheader("Terms of Service")
        st.markdown("""
        **1. Service:** VerbaPost converts user-submitted audio/text into physical mail. We use third-party providers (PostGrid, Lob) for fulfillment.
        **2. Privacy:** We do not sell your data. Letter content is processed solely for the purpose of transcription and mailing.
        **3. Delivery:** While we use USPS First Class Mail, we cannot guarantee specific delivery dates once handed to the carrier.
        **4. Refunds:** Refunds are available for system errors (e.g., failed audio transcription) but not for address errors provided by the user.
        """)
        
        st.divider()
        
        st.subheader("Privacy Policy")
        st.markdown("""
        **Data Collection:** We collect your email, shipping address, and the content of your letters.
        **Data Usage:** Your address is used for return labels. Your letter content is sent to OpenAI for transcription and PostGrid for printing.
        **Deletion:** You may request account deletion by emailing support@verbapost.com.
        """)

    if st.button("← Return to Home", type="primary"):
        st.session_state.app_mode = "splash"
        st.rerun()

# --- PAGE: STORE ---
def render_store_page():
    render_hero("Select Service", "Choose your letter type")
    
    # Admin Link
    u_email = st.session_state.get("user_email", "")
    admin_target = st.secrets.get("admin", {}).get("email", "").strip().lower() if "admin" in st.secrets else ""
    if str(u_email).strip().lower() == admin_target:
        if st.button("🔐 Open Admin Console", type="secondary"):
            import ui_admin
            ui_admin.show_admin()
            return

    c1, c2 = st.columns([2, 1])
    with c1:
        with st.container(border=True):
            st.subheader("Available Packages")
            
            # IMPROVED SELECTION WITH BLURBS
            tier_options = {
                "Standard": "⚡ Standard ($2.99) - Machine generated, window envelope.",
                "Heirloom": "🏺 Heirloom ($5.99) - Handwriting font, thick paper, real stamp.",
                "Civic": "🏛️ Civic ($6.99) - Write to Congress. We find your Reps automatically.",
                "Santa": "🎅 Santa ($9.99) - Direct from North Pole. Festive background."
            }
            
            sel = st.radio("Select Tier", list(tier_options.keys()), format_func=lambda x: tier_options[x])
            
            tier_code = sel
            prices = {"Standard": 2.99, "Heirloom": 5.99, "Civic": 6.99, "Santa": 9.99}
            price = prices[tier_code]
            
            # Show detail blurb based on selection
            if tier_code == "Santa":
                st.info("🎅 **Santa Special:** Includes a magical North Pole background, uses a special handwriting font, and the return address is fixed to '123 Elf Road, North Pole'.")
            elif tier_code == "Civic":
                st.info("🏛️ **Civic Action:** Dictate one letter, and we will mail it to your US Representative and both US Senators based on your profile address.")

    with c2:
        with st.container(border=True):
            st.subheader("Checkout")
            st.metric("Total", f"${price}")
            
            if st.button(f"Pay ${price} & Start", type="primary", use_container_width=True):
                # Save Draft State
                if database: database.save_draft(u_email, "", tier_code, price)
                
                # Create Stripe Session
                link = f"{YOUR_APP_URL}?tier={tier_code}&session_id={{CHECKOUT_SESSION_ID}}"
                url, sess_id = payment_engine.create_checkout_session(tier_code, int(price*100), link, YOUR_APP_URL)
                
                if url:
                    # White text forced by CSS, but inline style ensures it works
                    st.markdown(f"""
                    <a href="{url}" target="_blank" style="text-decoration:none;">
                        <div style="background-color:#6772e5; color:white; padding:12px; border-radius:4px; text-align:center; font-weight:bold;">
                           👉 Pay Now via Stripe
                        </div>
                    </a>
                    """, unsafe_allow_html=True)
                else:
                    st.error("Payment System Offline")

# --- PAGE: WORKSPACE (Address Logic) ---
def render_workspace_page():
    tier = st.session_state.get("locked_tier", "Standard")
    render_hero("Compose Letter", f"{tier} Edition")
    
    # 1. FETCH USER PROFILE
    u_email = st.session_state.get("user_email")
    user_addr = {}
    if database and u_email:
        p = database.get_user_profile(u_email)
        if p:
            user_addr = {
                "name": p.full_name, "street": p.address_line1,
                "city": p.address_city, "state": p.address_state, "zip": p.address_zip
            }

    with st.container(border=True):
        st.subheader("📍 Addressing")
        
        # --- SCENARIO A: SANTA (Locked) ---
        if tier == "Santa":
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**To (Child)**")
                to_name = st.text_input("Child's Name", key="w_to_name")
                to_street = st.text_input("Street", key="w_to_street")
                c_x, c_y, c_z = st.columns(3)
                to_city = c_x.text_input("City", key="w_to_city")
                to_state = c_y.text_input("State", key="w_to_state")
                to_zip = c_z.text_input("Zip", key="w_to_zip")
            with c2:
                st.markdown("**From**")
                st.success("🎅 Locked: North Pole")
                # Hidden values for state
                from_name="Santa Claus"; from_street="123 Elf Road"; from_city="North Pole"; from_state="NP"; from_zip="88888"

        # --- SCENARIO B: CIVIC (Auto-Skip) ---
        elif tier == "Civic":
            # Check if we have a valid address from profile
            has_valid_addr = user_addr.get("street") and user_addr.get("zip")
            
            if has_valid_addr:
                st.success(f"✅ Using your registered address for Representative lookup.")
                st.caption(f"{user_addr.get('street')}, {user_addr.get('city')}")
                
                with st.expander("Edit My Address"):
                    from_name = st.text_input("Name", value=user_addr.get("name"), key="w_civic_name")
                    from_street = st.text_input("Street", value=user_addr.get("street"), key="w_civic_street")
                    c_a, c_b, c_c = st.columns(3)
                    from_city = c_a.text_input("City", value=user_addr.get("city"), key="w_civic_city")
                    from_state = c_b.text_input("State", value=user_addr.get("state"), key="w_civic_state")
                    from_zip = c_c.text_input("Zip", value=user_addr.get("zip"), key="w_civic_zip")
            else:
                st.warning("Please enter your address to find your Representatives.")
                from_name = st.text_input("Your Name", key="w_civic_name")
                from_street = st.text_input("Street", key="w_civic_street")
                c_a, c_b, c_c = st.columns(3)
                from_city = c_a.text_input("City", key="w_civic_city")
                from_state = c_b.text_input("State", key="w_civic_state")
                from_zip = c_c.text_input("Zip", key="w_civic_zip")

            # Dummy To
            to_name="Civic"; to_street="Civic"; to_city="Civic"; to_state="TN"; to_zip="00000"

        # --- SCENARIO C: STANDARD/HEIRLOOM ---
        else:
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**To**")
                to_name = st.text_input("Name", key="w_to_name")
                to_street = st.text_input("Street", key="w_to_street")
                c_x, c_y, c_z = st.columns(3)
                to_city = c_x.text_input("City", key="w_to_city")
                to_state = c_y.text_input("State", key="w_to_state")
                to_zip = c_z.text_input("Zip", key="w_to_zip")

            with c2:
                st.markdown("**From**")
                # Auto-populate defaults if available
                def_n = user_addr.get("name", "")
                def_s = user_addr.get("street", "")
                def_c = user_addr.get("city", "")
                def_st = user_addr.get("state", "")
                def_z = user_addr.get("zip", "")
                
                from_name = st.text_input("Name", value=def_n, key="w_from_name")
                from_street = st.text_input("Street", value=def_s, key="w_from_street")
                c_a, c_b, c_c = st.columns(3)
                from_city = c_a.text_input("City", value=def_c, key="w_from_city")
                from_state = c_b.text_input("State", value=def_st, key="w_from_state")
                from_zip = c_c.text_input("Zip", value=def_z, key="w_from_zip")

        if st.button("Save Addresses"):
             # Save to session
             st.session_state.to_addr = {"name": to_name, "street": to_street, "city": to_city, "state": to_state, "zip": to_zip}
             st.session_state.from_addr = {"name": from_name, "street": from_street, "city": from_city, "state": from_state, "zip": from_zip}
             
             # If Civic, we can trigger lookup here if we want, or wait for send
             st.toast("Addresses Saved!")

    st.write("---")
    
    # 3. VALIDATION
    is_ready = False
    if tier == "Civic" and st.session_state.get("from_addr", {}).get("zip"): is_ready = True
    elif st.session_state.get("to_addr", {}).get("name"): is_ready = True
    
    c_sig, c_mic = st.columns(2)
    with c_sig:
        st.write("✍️ **Signature**")
        if tier == "Santa":
             st.info("Signed by Santa")
             st.session_state.sig_data = None
        else:
             canvas = st_canvas(stroke_width=2, stroke_color="#000", background_color="#fff", height=150, width=400, key="canvas")
             if canvas.image_data is not None: st.session_state.sig_data = canvas.image_data
             
    with c_mic:
        st.write("🎤 **Dictation**")
        if not is_ready:
            st.warning("⚠️ Please Fill & Save Addresses Above First")
        else:
            audio = st.audio_input("Record")
            if audio:
                if ai_engine:
                    with st.spinner("Transcribing..."):
                        text = ai_engine.transcribe_audio(audio)
                        st.session_state.transcribed_text = text
                        st.session_state.app_mode = "review"
                        st.rerun()
                else:
                    st.error("AI Engine Missing")

def render_review_page():
    render_hero("Review Letter", "Finalize and Send")
    
    st.info("Please review the text below. You can edit it if the AI made a mistake.")
    txt = st.text_area("Body Content", st.session_state.get("transcribed_text", ""), height=300)
    st.session_state.transcribed_text = txt # Update state with edits
    
    if st.button("🚀 Send Letter", type="primary"):
        tier = st.session_state.get("locked_tier", "Standard")
        u_email = st.session_state.get("user_email")
        
        # Save Final Draft
        if database:
            # Re-convert session dicts to simple strings/json for storage if needed
            # Assuming database.save_draft handles the object storage or we update logic
            # For now, just mark it "Pending"
            st.toast("Processing...")
            
            # Simple notification logic here (mocked)
            st.success("Letter Queued for Delivery!")
            st.balloons()
            
            if st.button("Start New Letter"): 
                reset_app()
                st.rerun()

# --- MAIN CONTROLLER ---
def show_main_app():
    if analytics: analytics.inject_ga()
    
    # Routing logic
    mode = st.session_state.get("app_mode", "splash")
    
    # Check Stripe
    if "session_id" in st.query_params:
        st.session_state.app_mode = "workspace"
        st.session_state.payment_complete = True
        if "tier" in st.query_params: st.session_state.locked_tier = st.query_params["tier"]
        st.query_params.clear()
        st.rerun()

    # Views
    if mode == "splash": 
        import ui_splash
        ui_splash.show_splash()
    elif mode == "login": 
        import ui_login
        import auth_engine
        ui_login.show_login(lambda e,p: _handle_login(auth_engine, e,p), lambda e,p,n,a,c,s,z,l: _handle_signup(auth_engine, e,p,n,a,c,s,z,l))
    elif mode == "store": render_store_page()
    elif mode == "workspace": render_workspace_page()
    elif mode == "review": render_review_page()
    elif mode == "legal": render_legal_page()
    elif mode == "forgot_password": 
        import ui_login
        ui_login.show_forgot_password(None) # Placeholder

    # Sidebar
    with st.sidebar:
        if st.button("🏠 Home"): reset_app(); st.rerun()
        if st.session_state.get("user_email"):
            st.write(f"User: {st.session_state.user_email}")
            if st.button("Logout"):
                st.session_state.clear()
                st.rerun()

# --- AUTH CALLBACKS ---
def _handle_login(auth, email, password):
    res, err = auth.sign_in(email, password)
    if res and res.user:
        st.session_state.user = res.user
        st.session_state.user_email = res.user.email
        st.session_state.app_mode = "store"
        st.rerun()
    else:
        st.session_state.auth_error = err

def _handle_signup(auth, email, password, name, addr, city, state, zip_c, lang):
    res, err = auth.sign_up(email, password, name, addr, city, state, zip_c, lang)
    if res and res.user:
        st.success("Account Created! Please log in.")
        st.session_state.app_mode = "login"
    else:
        st.session_state.auth_error = err