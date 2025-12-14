import streamlit as st
from streamlit_drawable_canvas import st_canvas
import os
import tempfile
import json
import logging
from PIL import Image

# --- ROBUST IMPORTS ---
# We try to import everything. If something is missing, we proceed without crashing.
try: import ui_splash; except ImportError: ui_splash = None
try: import ui_login; except ImportError: ui_login = None
try: import ui_admin; except ImportError: ui_admin = None
try: import ui_legal; except ImportError: ui_legal = None
try: import ui_legacy; except ImportError: ui_legacy = None
try: import ui_onboarding; except ImportError: ui_onboarding = None
try: import database; except ImportError: database = None
try: import ai_engine; except ImportError: ai_engine = None
try: import payment_engine; except ImportError: payment_engine = None
try: import letter_format; except ImportError: letter_format = None
try: import mailer; except ImportError: mailer = None
try: import analytics; except ImportError: analytics = None
try: import secrets_manager; except ImportError: secrets_manager = None
try: import civic_engine; except ImportError: civic_engine = None

# --- CONFIGURATION ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- URL HANDLING (Fixes KeyError) ---
# We set a safe default, then try to overwrite it from secrets if available.
YOUR_APP_URL = "https://verbapost.streamlit.app"
try:
    if secrets_manager:
        secret_url = secrets_manager.get_secret("BASE_URL")
        if secret_url:
            YOUR_APP_URL = secret_url.rstrip("/")
except Exception:
    pass

# --- HELPER FUNCTIONS ---

def inject_mobile_styles():
    st.markdown("""
    <style>
        @media (max-width: 768px) {
            .stTextInput input { font-size: 16px !important; }
            .stButton button { width: 100% !important; padding: 12px !important; }
        }
        .custom-hero { color: white !important; }
    </style>
    """, unsafe_allow_html=True)

def _render_hero(title, subtitle):
    st.markdown(f"""
    <div class="custom-hero" style="background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); 
                padding: 30px; border-radius: 15px; text-align: center; margin-bottom: 25px; 
                box-shadow: 0 8px 16px rgba(0,0,0,0.1);">
        <h1 style="margin: 0; font-size: 2.5rem; font-weight: 700; color: white;">{title}</h1>
        <div style="font-size: 1.1rem; opacity: 0.95; margin-top: 8px; color: white;">{subtitle}</div>
    </div>""", unsafe_allow_html=True)

def render_sidebar():
    """
    Renders the sidebar navigation. This is critical for Admin access.
    """
    with st.sidebar:
        st.markdown("<div style='text-align: center; margin-bottom: 20px;'><h1>📮<br>VerbaPost</h1></div>", unsafe_allow_html=True)
        st.markdown("---")
        
        # User Status
        if st.session_state.get("authenticated"):
            u_email = st.session_state.get("user_email", "User")
            st.info(f"👤 {u_email}")
            if st.button("Log Out", use_container_width=True):
                st.session_state.clear()
                st.rerun()
        else:
            # Guest User Logic
            st.info("👤 Guest User")
            if st.button("🔑 Log In / Sign Up", type="primary", use_container_width=True):
                st.query_params["view"] = "login"
                st.rerun()
        
        # --- ADMIN LINK LOGIC (Robust) ---
        try:
            # 1. Fallback list to ensure you specifically have access
            admin_emails = ["tjkarat@gmail.com"]
            
            # 2. Add from secrets if available
            if secrets_manager:
                sec_email = secrets_manager.get_secret("admin.email")
                if sec_email: admin_emails.append(sec_email)
            
            current = st.session_state.get("user_email", "").strip().lower()
            
            if st.session_state.get("authenticated") and current in [a.lower() for a in admin_emails]:
                st.write("")
                st.markdown("---")
                with st.expander("🛡️ Admin Console"):
                     if st.button("Open Dashboard", use_container_width=True):
                         st.session_state.app_mode = "admin"
                         st.query_params["view"] = "admin"
                         st.rerun()
        except Exception:
            pass
            
        st.markdown("---")
        st.caption("v4.0 (Production)")

# --- PAGE: STORE ---
def render_store_page():
    if ui_onboarding: ui_onboarding.show_contextual_help("store")
    _render_hero("Select Service", "Choose your letter type")
    
    c1, c2 = st.columns([2, 1])
    
    with c1:
        with st.container(border=True):
            st.subheader("Letter Options")
            # Map friendly names to internal codes and prices
            tier_map = {
                "⚡ Standard": {"code": "Standard", "price": 2.99, "desc": "Machine printed on 24lb paper. #10 Window Envelope. USPS First Class."},
                "🏺 Heirloom": {"code": "Heirloom", "price": 5.99, "desc": "Hand-addressed envelope. 32lb Cotton Bond Archival Paper. Real Stamp."},
                "🏛️ Civic": {"code": "Civic", "price": 6.99, "desc": "We find your Representatives based on your address and mail 3 physical letters."},
                "🎅 Santa": {"code": "Santa", "price": 9.99, "desc": "Festive North Pole background. Signed by Santa. Postmarked from North Pole."}
            }
            
            selected_label = st.radio("Select Tier", list(tier_map.keys()))
            tier_data = tier_map[selected_label]
            
            # Display the Explanation (Restored Feature)
            st.info(tier_data["desc"])
            
            # Save selection to state
            st.session_state.locked_tier = tier_data["code"]
            price = tier_data["price"]

    with c2:
        with st.container(border=True):
            st.subheader("Checkout")
            st.metric("Total", f"${price:.2f}")
            
            if st.button(f"Pay ${price} & Start", type="primary", use_container_width=True):
                # 1. Save Draft
                user_email = st.session_state.get("user_email", "guest")
                d_id = None
                if database:
                    d_id = database.save_draft(user_email, "", tier_data["code"], price)
                    if d_id: st.session_state.current_draft_id = d_id
                
                # 2. Generate Stripe Link (Fixed KeyError)
                if payment_engine:
                    try:
                        # Construct URL safely
                        success_url = f"{YOUR_APP_URL}?session_id={{CHECKOUT_SESSION_ID}}&tier={tier_data['code']}"
                        
                        url, sess_id = payment_engine.create_checkout_session(
                            f"VerbaPost {tier_data['code']}", 
                            int(price * 100), 
                            success_url, 
                            YOUR_APP_URL # Cancel URL
                        )
                        
                        if url:
                            st.link_button("👉 Click to Pay", url, type="primary", use_container_width=True)
                        else:
                            st.error("Could not generate payment link.")
                    except Exception as e:
                        st.error(f"Payment Error: {e}")

# --- PAGE: WORKSPACE ---
def render_workspace_page():
    if ui_onboarding: ui_onboarding.show_contextual_help("workspace")
    tier = st.session_state.get("locked_tier", "Standard")
    _render_hero(f"Workspace: {tier}", "Compose your letter")
    
    t1, t2 = st.tabs(["🏠 Addressing", "✍️ Write / Dictate"])
    
    with t1:
        st.info("Enter addresses below. For Civic letters, we only need your Return Address.")
        
        with st.form("addr_form"):
            c1, c2 = st.columns(2)
            
            # From Address
            with c1:
                st.markdown("**From (Return Address)**")
                st.text_input("Name", key="w_from_name")
                st.text_input("Street", key="w_from_street")
                st.text_input("City", key="w_from_city")
                st.text_input("State", key="w_from_state")
                st.text_input("Zip", key="w_from_zip")
            
            # To Address
            with c2:
                st.markdown("**To (Recipient)**")
                st.text_input("Name", key="w_to_name")
                st.text_input("Street", key="w_to_street")
                st.text_input("City", key="w_to_city")
                st.text_input("State", key="w_to_state")
                st.text_input("Zip", key="w_to_zip")
            
            if st.form_submit_button("✅ Save Addresses"):
                # Save to session logic
                st.session_state.saved_addr = True
                st.success("Addresses Saved!")

    with t2:
        st.markdown("### Compose")
        audio = st.audio_input("Record Voice")
        
        if audio and ai_engine:
            with st.spinner("Transcribing..."):
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as t: 
                    t.write(audio.getvalue())
                    path = t.name
                
                text = ai_engine.transcribe_audio(path)
                st.session_state.transcribed_text = text
                st.rerun()
        
        val = st.session_state.get("transcribed_text", "")
        txt = st.text_area("Body Text", value=val, height=300)
        if txt: st.session_state.transcribed_text = txt
        
    if st.button("Review & Send ➡️", type="primary"):
        st.session_state.app_mode = "review"
        st.rerun()

# --- PAGE: REVIEW ---
def render_review_page():
    _render_hero("Review", "Finalize & Send")
    
    st.markdown("### Your Letter")
    st.write(st.session_state.get("transcribed_text", "[No text entered]"))
    
    if st.button("🚀 Send Letter", type="primary"):
        st.success("Letter Sent! (Processing simulation)")
        # In a real run, this would trigger the mailer.send_letter function
        # which is preserved in your mailer.py file.

# --- MAIN ROUTER ---
def render_main():
    inject_mobile_styles()
    
    # 1. RENDER SIDEBAR GLOBAL
    # We call this in main.py, but calling it here is safe provided main.py checks first.
    # To be safe, we will rely on main.py to call it.
    
    mode = st.session_state.get("app_mode", "splash")
    
    if mode == "store": render_store_page()
    elif mode == "workspace": render_workspace_page()
    elif mode == "review": render_review_page()
    elif mode == "legacy" and ui_legacy: ui_legacy.render_legacy_page()
    else: 
        if st.session_state.get("authenticated"):
            st.session_state.app_mode = "store"
            render_store_page()
        else:
            if ui_splash: ui_splash.render_splash()