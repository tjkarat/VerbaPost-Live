import streamlit as st
import os
import logging
import tempfile

# --- ROBUST IMPORTS ---
try: import ui_splash; except ImportError: ui_splash = None
try: import ui_login; except ImportError: ui_login = None
try: import database; except ImportError: database = None
try: import ai_engine; except ImportError: ai_engine = None
try: import payment_engine; except ImportError: payment_engine = None
try: import secrets_manager; except ImportError: secrets_manager = None
try: import ui_onboarding; except ImportError: ui_onboarding = None

# --- CONFIGURATION ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- URL HANDLING ---
YOUR_APP_URL = "https://verbapost.streamlit.app"
try:
    if secrets_manager:
        # Safe get to prevent KeyError
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

# --- CRITICAL: SIDEBAR LOGIC ---
def render_sidebar():
    """
    Renders the sidebar navigation and Admin Console link.
    """
    with st.sidebar:
        st.markdown("<div style='text-align: center; margin-bottom: 20px;'><h1>📮<br>VerbaPost</h1></div>", unsafe_allow_html=True)
        st.markdown("---")
        
        # User Status
        if st.session_state.get("authenticated"):
            u_email = st.session_state.get("user_email", "User")
            st.info(f"👤 {u_email}")
            if st.button("Log Out", key="sb_logout", use_container_width=True):
                st.session_state.clear()
                st.rerun()
        else:
            st.info("👤 Guest User")
            if st.button("🔑 Log In / Sign Up", key="sb_login", type="primary", use_container_width=True):
                st.query_params["view"] = "login"
                st.rerun()
        
        # --- ADMIN LINK LOGIC ---
        try:
            admin_emails = ["tjkarat@gmail.com"]
            
            # Fetch secret admins safely
            if secrets_manager:
                sec_email = secrets_manager.get_secret("admin.email")
                if sec_email: admin_emails.append(sec_email)
            
            current = st.session_state.get("user_email", "").strip().lower()
            
            # Check if current user is an admin
            if st.session_state.get("authenticated") and current in [a.lower() for a in admin_emails]:
                st.write("")
                st.markdown("---")
                with st.expander("🛡️ Admin Console"):
                     if st.button("Open Dashboard", key="sb_admin_btn", use_container_width=True):
                         st.session_state.app_mode = "admin"
                         st.query_params["view"] = "admin"
                         st.rerun()
        except Exception as e:
            # Silently fail admin check to not disturb users
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
            tier_map = {
                "⚡ Standard": {"code": "Standard", "price": 2.99, "desc": "Machine printed. USPS First Class."},
                "🏺 Heirloom": {"code": "Heirloom", "price": 5.99, "desc": "Cotton Bond Archival Paper. Real Stamp."},
                "🏛️ Civic": {"code": "Civic", "price": 6.99, "desc": "Mails to your 3 Representatives."},
                "🎅 Santa": {"code": "Santa", "price": 9.99, "desc": "Postmarked from North Pole."}
            }
            
            selected_label = st.radio("Select Tier", list(tier_map.keys()))
            tier_data = tier_map[selected_label]
            st.info(tier_data["desc"])
            
            st.session_state.locked_tier = tier_data["code"]
            price = tier_data["price"]

    with c2:
        with st.container(border=True):
            st.subheader("Checkout")
            st.metric("Total", f"${price:.2f}")
            
            if st.button(f"Pay ${price}", type="primary", use_container_width=True):
                user_email = st.session_state.get("user_email", "guest")
                d_id = None
                
                # Create Draft
                if database:
                    d_id = database.save_draft(user_email, "", tier_data["code"], price)
                    if d_id: st.session_state.current_draft_id = d_id
                
                # Stripe
                if payment_engine:
                    try:
                        success_url = f"{YOUR_APP_URL}?session_id={{CHECKOUT_SESSION_ID}}"
                        url, sess_id = payment_engine.create_checkout_session(
                            f"VerbaPost {tier_data['code']}", 
                            int(price * 100), 
                            success_url, 
                            YOUR_APP_URL 
                        )
                        if url: st.link_button("👉 Click to Pay", url, type="primary", use_container_width=True)
                        else: st.error("Payment Link Error")
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
            with c1:
                st.markdown("**From (Return Address)**")
                st.text_input("Name", key="w_from_name")
                st.text_input("Street", key="w_from_street")
                st.text_input("City", key="w_from_city")
                st.text_input("State", key="w_from_state")
                st.text_input("Zip", key="w_from_zip")
            with c2:
                st.markdown("**To (Recipient)**")
                st.text_input("Name", key="w_to_name")
                st.text_input("Street", key="w_to_street")
                st.text_input("City", key="w_to_city")
                st.text_input("State", key="w_to_state")
                st.text_input("Zip", key="w_to_zip")
            
            if st.form_submit_button("✅ Save Addresses"):
                st.session_state.saved_addr = True
                st.success("Addresses Saved!")

    with t2:
        st.markdown("### Compose")
        # Audio Input
        audio = st.audio_input("Record Voice")
        if audio and ai_engine:
            with st.spinner("Transcribing..."):
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as t: 
                    t.write(audio.getvalue())
                    path = t.name
                text = ai_engine.transcribe_audio(path)
                st.session_state.transcribed_text = text
                st.rerun()
        
        # Text Input
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

# --- MAIN CONTROLLER ENTRY ---
def render_main():
    inject_mobile_styles()
    
    # Note: render_sidebar() is handled by main.py
    
    mode = st.session_state.get("app_mode", "splash")
    
    if mode == "store": render_store_page()
    elif mode == "workspace": render_workspace_page()
    elif mode == "review": render_review_page()
    else: 
        if st.session_state.get("authenticated"):
            render_store_page()
        else:
            if ui_splash: ui_splash.render_splash()