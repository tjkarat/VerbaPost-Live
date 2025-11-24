import streamlit as st
from streamlit_drawable_canvas import st_canvas
import os
from PIL import Image
from datetime import datetime
import re
import io

# --- TOP LEVEL IMPORTS (Fixes KeyError) ---
try:
    import ai_engine 
    import database
    import letter_format
    import mailer
    import payment_engine
    # Optional modules (we will create stubs for these next)
    import zipcodes
    import civic_engine
    import promo_engine
    import analytics
except ImportError as e:
    print(f"⚠️ Warning: Missing module {e}")

# --- CONFIG ---
YOUR_APP_URL = "https://verbapost.streamlit.app" 
COST_STANDARD = 2.99
COST_HEIRLOOM = 5.99
COST_CIVIC = 6.99

# --- HELPER: INIT SUPABASE ---
@st.cache_resource
def get_supabase():
    from supabase import create_client
    try:
        if "SUPABASE_URL" not in st.secrets: return None
        return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except Exception: return None

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

# --- MAIN APP ---
def show_main_app():
    # Inject Analytics if module exists
    if 'analytics' in globals(): analytics.inject_ga()

    # Defaults
    if "app_mode" not in st.session_state: st.session_state.app_mode = "store"
    if "processed_ids" not in st.session_state: st.session_state.processed_ids = []

    # --- ROUTING: Legal ---
    if st.session_state.app_mode == "legal":
        render_hero("Legal", "Terms & Privacy")
        st.info("Privacy: We protect your data. Terms: Don't mail illegal stuff.")
        if st.button("← Back"): 
            st.session_state.app_mode = "splash"
            st.rerun()
        return

    # --- ROUTING: Login ---
    if st.session_state.app_mode == "login":
        st.markdown("<h1 style='text-align: center;'>Welcome Back</h1>", unsafe_allow_html=True)
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
                        reset_app()
                        st.session_state.app_mode = "store"
                        st.rerun()
                    except Exception as e: st.error(f"Login failed: {e}")
                if st.button("Sign Up", use_container_width=True):
                    sb = get_supabase()
                    try:
                        sb.auth.sign_up({"email": email, "password": password})
                        st.success("Check email for confirmation link.")
                    except Exception as e: st.error(f"Signup failed: {e}")
        if st.button("← Back"): 
            st.session_state.app_mode = "splash"
            st.rerun()
        return

    # --- STORE ---
    if st.session_state.app_mode == "store":
        render_hero("VerbaPost", "Voice to Letter.")
        c1, c2 = st.columns([2, 1])
        with c1:
            st.subheader("1. Customize")
            tier = st.radio("Tier", ["⚡ Standard ($2.99)", "🏺 Heirloom ($5.99)", "🏛️ Civic ($6.99)"])
            lang = st.selectbox("Language", ["English", "Spanish", "French"])
        with c2:
            st.subheader("2. Checkout")
            price = 2.99
            if "Heirloom" in tier: price = 5.99
            if "Civic" in tier: price = 6.99
            
            st.metric("Total", f"${price}")
            
            # Generate Link Logic
            if st.button("Pay & Start", type="primary", use_container_width=True):
                # Create Draft & Link
                user = st.session_state.get("user_email", "guest")
                draft_id = database.save_draft(user, "", tier, price)
                url, sess_id = payment_engine.create_checkout_session(tier, int(price*100), YOUR_APP_URL, YOUR_APP_URL)
                
                if url:
                    st.session_state.stripe_url = url
                    st.link_button("Click to Pay", url)
                else:
                    # FREE PASS for debugging if stripe fails
                    st.warning("Payment Offline (Dev Mode). Proceeding...")
                    st.session_state.payment_complete = True
                    st.session_state.app_mode = "workspace"
                    st.session_state.locked_tier = tier
                    st.rerun()

    # --- WORKSPACE ---
    elif st.session_state.app_mode == "workspace":
        render_hero("Compose", "Dictate & Send")
        
        # Address
        with st.expander("📍 Addresses", expanded=True):
            c1, c2 = st.columns(2)
            with c1: st.text_input("Recipient Name", key="to_name")
            with c2: st.text_input("Your Name", key="from_name")
            
        # Dictate
        st.divider()
        st.subheader("🎙️ Dictate Letter")
        audio = st.audio_input("Record")
        
        if audio:
            with st.status("Transcribing..."):
                path = "temp.wav"
                with open(path, "wb") as f: f.write(audio.getvalue())
                text = ai_engine.transcribe_audio(path)
                st.session_state.transcribed_text = text
                st.session_state.app_mode = "review"
                st.rerun()

    # --- REVIEW ---
    elif st.session_state.app_mode == "review":
        render_hero("Review", "Edit & Send")
        txt = st.text_area("Body", st.session_state.transcribed_text, height=300)
        
        if st.button("🚀 Send Letter", type="primary"):
            with st.status("Processing..."):
                # 1. Generate PDF
                pdf = letter_format.create_pdf(txt, "Recipient...", "Sender...")
                # 2. Mail
                mailer.send_letter(pdf, {}, {})
                st.success("Sent!")
                with open(pdf, "rb") as f:
                    st.download_button("Download PDF", f, "letter.pdf")
            
            if st.button("Start New"): reset_app()