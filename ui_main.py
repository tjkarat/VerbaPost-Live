import streamlit as st
from streamlit_drawable_canvas import st_canvas
import os
from datetime import datetime
import re

# --- IMPORTS ---
try:
    import ai_engine 
    import database
    import letter_format
    import mailer
    import payment_engine
    import analytics
    import promo_engine
except ImportError: pass

# --- CONFIG ---
YOUR_APP_URL = "https://verbapost.streamlit.app/" # Ensure trailing slash
COST_STANDARD = 2.99
COST_HEIRLOOM = 5.99
COST_CIVIC = 6.99

# --- HELPER: SUPABASE ---
@st.cache_resource
def get_supabase():
    from supabase import create_client
    try:
        if "SUPABASE_URL" not in st.secrets: return None
        return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except: return None

def reset_app():
    st.session_state.app_mode = "store"
    st.session_state.audio_path = None
    st.session_state.transcribed_text = ""
    st.session_state.payment_complete = False
    st.session_state.stripe_url = None
    st.session_state.sig_data = None
    st.query_params.clear()

def render_hero(title, subtitle):
    st.markdown(f"""<div class="hero-banner"><div class="hero-title">{title}</div><div class="hero-subtitle">{subtitle}</div></div>""", unsafe_allow_html=True)

# --- MAIN LOGIC ---
def show_main_app():
    if 'analytics' in globals(): analytics.inject_ga()

    # Defaults
    if "app_mode" not in st.session_state: st.session_state.app_mode = "store"
    if "processed_ids" not in st.session_state: st.session_state.processed_ids = []

    # --- 1. STRIPE RETURN HANDLER (Fixed) ---
    qp = st.query_params
    if "session_id" in qp:
        session_id = qp["session_id"]
        if session_id not in st.session_state.processed_ids:
            if payment_engine.check_payment_status(session_id):
                st.session_state.payment_complete = True
                st.session_state.processed_ids.append(session_id)
                st.toast("✅ Payment Confirmed!")
                
                # Restore State
                if "tier" in qp: st.session_state.locked_tier = qp["tier"]
                if "lang" in qp: st.session_state.selected_language = qp["lang"]
                
                # FORCE WORKSPACE
                st.session_state.app_mode = "workspace"
            else:
                st.error("Payment verification failed.")
        # Clear params to prevent loop
        st.query_params.clear()

    # --- 2. LOGIN / SIGNUP ---
    if st.session_state.app_mode == "login":
        st.markdown("<h1 style='text-align: center;'>Welcome</h1>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns([1,2,1])
        with c2:
            with st.container(border=True):
                email = st.text_input("Email")
                password = st.text_input("Password", type="password")
                
                if st.button("Log In", type="primary", use_container_width=True):
                    sb = get_supabase()
                    try:
                        res = sb.auth.sign_in_with_password({"email": email, "password": password})
                        st.session_state.user = res
                        st.session_state.user_email = email # Save for easier access
                        reset_app()
                        st.session_state.app_mode = "store"
                        st.rerun()
                    except Exception as e: st.error(f"Login failed: {e}")
                
                if st.button("Sign Up", use_container_width=True):
                    sb = get_supabase()
                    try:
                        sb.auth.sign_up({"email": email, "password": password})
                        st.success("Check email for confirmation.")
                    except Exception as e: st.error(f"Signup failed: {e}")
        
        if st.button("← Back"): st.session_state.app_mode = "splash"; st.rerun()
        return

    # --- 3. SIDEBAR & ADMIN (Fixed) ---
    with st.sidebar:
        if st.button("Reset App"): reset_app(); st.rerun()
        
        # ADMIN CHECK
        user_obj = st.session_state.get("user")
        if user_obj:
            # Normalize emails to lowercase and strip whitespace
            u_email = st.session_state.get("user_email", "").lower().strip()
            if not u_email: # Fallback to object if session string missing
                try: u_email = user_obj.user.email.lower().strip()
                except: pass
            
            st.caption(f"User: {u_email}")
            
            # Get secret and normalize
            admin_email = st.secrets.get("admin", {}).get("email", "").lower().strip()
            
            # Compare
            if u_email and admin_email and u_email == admin_email:
                st.divider()
                st.write("🔐 **Admin Console**")
                if st.button("Generate Promo"):
                    code = promo_engine.generate_code()
                    st.info(f"Code: `{code}`")
            
            if st.button("Sign Out"):
                st.session_state.pop("user", None)
                st.session_state.app_mode = "splash"
                st.rerun()

    # --- 4. THE STORE ---
    if st.session_state.app_mode == "store":
        render_hero("Select Service", "Choose your letter type.")
        c1, c2 = st.columns([2, 1])
        with c1:
            with st.container(border=True):
                st.subheader("Options")
                tier = st.radio("Tier", ["⚡ Standard ($2.99)", "🏺 Heirloom ($5.99)", "🏛️ Civic ($6.99)"])
                lang = st.selectbox("Language", ["English", "Spanish", "French"])
        with c2:
            with st.container(border=True):
                st.subheader("Checkout")
                price = 2.99
                if "Heirloom" in tier: price = 5.99
                if "Civic" in tier: price = 6.99
                
                st.metric("Total", f"${price}")
                
                if st.button("Pay & Start", type="primary", use_container_width=True):
                    user = st.session_state.get("user_email", "guest")
                    draft_id = database.save_draft(user, "", tier, price)
                    
                    safe_tier = tier.split()[1]
                    success_link = f"{YOUR_APP_URL}?tier={safe_tier}&lang={lang}"
                    
                    url, sess_id = payment_engine.create_checkout_session(tier, int(price*100), success_link, YOUR_APP_URL)
                    
                    if url: st.link_button("Proceed to Payment", url, type="primary")
                    else: st.error("Payment System Offline")

    # --- 5. THE WORKSPACE (Logic Updated) ---
    elif st.session_state.app_mode == "workspace":
        tier = st.session_state.get("locked_tier", "Standard")
        render_hero("Compose", f"{tier} Edition")
        
        # Fetch saved address for Sender
        user_email = st.session_state.get("user_email")
        saved_profile = database.get_user_profile(user_email) if user_email else None
        
        # Defaults from DB if available
        def_name = saved_profile.full_name if saved_profile else ""
        def_street = saved_profile.address_line1 if saved_profile else ""
        def_city = saved_profile.address_city if saved_profile else ""
        def_state = saved_profile.address_state if saved_profile else ""
        def_zip = saved_profile.address_zip if saved_profile else ""

        with st.container(border=True):
            st.subheader("Addressing")
            
            # LOGIC FOR CIVIC vs STANDARD
            if "Civic" in tier:
                st.info("🏛️ **Civic Mode:** We will auto-detect your representatives based on your Return Address.")
                # Only show Sender
                with st.expander("📍 Your Return Address (Required for Lookup)", expanded=True):
                    from_name = st.text_input("Your Name", value=def_name)
                    from_street = st.text_input("Street", value=def_street)
                    c1, c2, c3 = st.columns(3)
                    from_city = c1.text_input("City", value=def_city)
                    from_state = c2.text_input("State", value=def_state)
                    from_zip = c3.text_input("Zip", value=def_zip)
                    
                    # Dummy recipient for logic continuity
                    to_name, to_street, to_city, to_state, to_zip = "Civic", "Civic", "Civic", "TN", "00000"
            
            else:
                # Standard / Heirloom: Show Tabs
                t1, t2 = st.tabs(["👉 Recipient", "👈 Sender"])
                with t1:
                    to_name = st.text_input("Recipient Name")
                    to_street = st.text_input("Street Address")
                    c1, c2, c3 = st.columns(3)
                    to_city = c1.text_input("City")
                    to_state = c2.text_input("State")
                    to_zip = c3.text_input("Zip")
                
                with t2:
                    st.caption("Pre-filled from your profile")
                    from_name = st.text_input("Your Name", value=def_name)
                    from_street = st.text_input("Street", value=def_street)
                    c1, c2, c3 = st.columns(3)
                    from_city = c1.text_input("Your City", value=def_city)
                    from_state = c2.text_input("Your State", value=def_state)
                    from_zip = c3.text_input("Your Zip", value=def_zip)

            if st.button("Save Addresses"):
                # Save sender back to DB for future
                if user_email:
                    database.update_user_profile(user_email, from_name, from_street, from_city, from_state, from_zip)
                
                # Save to session
                st.session_state.to_addr = {'name': to_name, 'street': to_street, 'city': to_city, 'state': to_state, 'zip': to_zip}
                st.session_state.from_addr = {'name': from_name, 'street': from_street, 'city': from_city, 'state': from_state, 'zip': from_zip}
                st.toast("Addresses Saved!")

        # Dictation & Signing
        st.markdown("<br>", unsafe_allow_html=True)
        c_sig, c_mic = st.columns(2)
        
        with c_sig:
            st.write("Signature")
            canvas = st_canvas(fill_color="rgba(255, 165, 0, 0.3)", stroke_width=2, stroke_color="#000", background_color="#fff", height=150, width=300, key="sig")
            if canvas.image_data is not None: st.session_state.sig_data = canvas.image_data

        with c_mic:
            st.write("Dictate Body")
            audio = st.audio_input("Record")
            if audio:
                with st.status("Transcribing..."):
                    path = "temp.wav"
                    with open(path, "wb") as f: f.write(audio.getvalue())
                    text = ai_engine.transcribe_audio(path)
                    st.session_state.transcribed_text = text
                    st.session_state.app_mode = "review"
                    st.rerun()

    # --- 6. REVIEW & SEND ---
    elif st.session_state.app_mode == "review":
        render_hero("Review", "Finalize Letter")
        
        txt = st.text_area("Body", st.session_state.transcribed_text, height=300)
        
        if st.button("🚀 Send Letter", type="primary"):
            to_a = st.session_state.get("to_addr", {})
            from_a = st.session_state.get("from_addr", {})
            
            # Generate PDF
            pdf = letter_format.create_pdf(txt, str(to_a), str(from_a)) # Pass dicts as strings for now or unpack in letter_format
            
            # Send
            mailer.send_letter(pdf, to_a, from_a)
            st.success("Letter Sent!")
            if st.button("Finish"): reset_app()