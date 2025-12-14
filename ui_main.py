import streamlit as st
import logging
import tempfile
import os
import json
import time
import pandas as pd
from io import BytesIO

# --- ROBUST IMPORTS ---
# We try to import everything to ensure full functionality
try: import ui_splash; except ImportError: ui_splash = None
try: import ui_login; except ImportError: ui_login = None
try: import ui_admin; except ImportError: ui_admin = None
try: import database; except ImportError: database = None
try: import ai_engine; except ImportError: ai_engine = None
try: import payment_engine; except ImportError: payment_engine = None
try: import pricing_engine; except ImportError: pricing_engine = None
try: import secrets_manager; except ImportError: secrets_manager = None
try: import civic_engine; except ImportError: civic_engine = None
try: import letter_format; except ImportError: letter_format = None
try: import mailer; except ImportError: mailer = None
try: import bulk_engine; except ImportError: bulk_engine = None

logger = logging.getLogger(__name__)

# --- CONFIG & STATE ---
YOUR_APP_URL = "https://verbapost.streamlit.app"
if secrets_manager:
    s_url = secrets_manager.get_secret("BASE_URL")
    if s_url: YOUR_APP_URL = s_url.rstrip("/")

def init_state():
    defaults = {
        "app_mode": "splash", "authenticated": False, "user_email": "",
        "locked_tier": "Standard", "locked_price": 2.99,
        "transcribed_text": "", "current_draft_id": None,
        "sender_data": {}, "recipient_data": {},
        "campaign_data": None, "is_campaign": False
    }
    for k, v in defaults.items():
        if k not in st.session_state: st.session_state[k] = v

init_state()

# --- HELPER: MOBILE & STYLES ---
def inject_styles():
    st.markdown("""
    <style>
        .tier-card { border: 1px solid #ddd; padding: 20px; border-radius: 10px; margin-bottom: 10px; }
        .tier-card:hover { border-color: #FF4B4B; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
        .big-price { font-size: 1.8em; font-weight: bold; color: #333; }
        .stButton button { width: 100%; border-radius: 6px; font-weight: 600; }
        @media (max-width: 768px) { .stTextInput input { font-size: 16px; } }
    </style>
    """, unsafe_allow_html=True)

# --- HELPER: LOGIC ---
def _save_address_book(user_email, data, is_sender=False):
    """Saves contact to Supabase Address Book"""
    if not database or not user_email: return
    try:
        contact = {
            "user_email": user_email,
            "name": data.get("name"),
            "street": data.get("street"),
            "city": data.get("city"),
            "state": data.get("state"),
            "zip": data.get("zip"),
            "type": "sender" if is_sender else "recipient"
        }
        database.save_contact(contact)
    except Exception as e:
        logger.error(f"Address Book Save Error: {e}")

def _handle_draft_creation(email, tier, price):
    """Creates or updates draft to ensure data persistence"""
    d_id = st.session_state.get("current_draft_id")
    text = st.session_state.get("transcribed_text", "")
    
    if database:
        # Update existing
        if d_id:
            if database.update_draft_data(d_id, tier=tier, price=price, text=text): 
                return d_id
        
        # Create new
        d_id = database.save_draft(email, text, tier, price)
        st.session_state.current_draft_id = d_id
        return d_id
    return "temp_draft"

# --- SIDEBAR ---
def render_sidebar():
    with st.sidebar:
        st.markdown("## 📮 VerbaPost")
        
        if st.session_state.get("authenticated"):
            st.success(f"👤 {st.session_state.get('user_email')}")
            
            # Navigation
            st.markdown("---")
            if st.button("🏪 Store", key="nav_store"): st.session_state.app_mode = "store"; st.rerun()
            if st.button("✍️ Workspace", key="nav_work"): st.session_state.app_mode = "workspace"; st.rerun()
            
            st.markdown("---")
            if st.button("Log Out", key="sb_logout"):
                st.session_state.clear()
                st.rerun()
        else:
            if st.button("🔑 Log In", key="sb_login", type="primary"):
                st.query_params["view"] = "login"
                st.rerun()

        # Admin Link
        try:
            admins = ["tjkarat@gmail.com"]
            if secrets_manager:
                sec = secrets_manager.get_secret("admin.email")
                if sec: admins.append(sec)
            
            curr = st.session_state.get("user_email", "").strip().lower()
            if st.session_state.get("authenticated") and curr in [a.lower() for a in admins]:
                st.markdown("---")
                if st.button("🛡️ Admin", key="sb_admin"):
                    st.query_params["view"] = "admin"
                    st.rerun()
        except: pass

# --- PAGE: STORE (TIER SELECTION) ---
def render_store_page():
    inject_styles()
    st.title("Select Service Level")
    
    # 1. Campaign Mode Toggle
    is_campaign = st.toggle("📢 Bulk Campaign Mode (Upload CSV)", value=st.session_state.get("is_campaign", False))
    st.session_state.is_campaign = is_campaign

    if is_campaign:
        st.info("Campaign Mode: Upload a CSV with 'Name', 'Street', 'City', 'State', 'Zip'. Base price $2.99/letter.")
        # Campaign logic handles in Pricing/Checkout
        st.session_state.locked_tier = "Campaign"
        
    c1, c2 = st.columns([2, 1])
    
    with c1:
        # Tier Grid
        tiers = [
            {"name": "Standard", "price": 2.99, "desc": "USPS First Class. #10 Envelope. 24lb Paper.", "icon": "⚡"},
            {"name": "Heirloom", "price": 5.99, "desc": "Real Stamp. Cotton Bond Paper. Hand-addressed.", "icon": "🏺"},
            {"name": "Civic", "price": 6.99, "desc": "Mail to your 3 Reps (House + Senate).", "icon": "🏛️"},
            {"name": "Santa", "price": 9.99, "desc": "North Pole Postmark. Festive Stationery.", "icon": "🎅"}
        ]
        
        if not is_campaign:
            selected = st.radio("Choose Tier", [t["name"] for t in tiers], 
                              format_func=lambda x: next(f"{t['icon']} {t['name']} - ${t['price']}" for t in tiers if t["name"] == x))
            st.session_state.locked_tier = selected
            
            # Description Box
            desc = next(t["desc"] for t in tiers if t["name"] == selected)
            st.info(desc)

    with c2:
        # Checkout Box
        with st.container(border=True):
            st.subheader("Order Summary")
            tier = st.session_state.locked_tier
            
            # Pricing Calculation
            price = 2.99
            if pricing_engine:
                price = pricing_engine.calculate_total(tier)
            
            st.metric("Price per Letter", f"${price:.2f}")
            
            if is_campaign:
                st.warning("Final total calculated after CSV upload.")
            
            if st.button("Start Drafting ➡️", type="primary", use_container_width=True):
                # Save State & Move
                st.session_state.locked_price = price
                
                # Create Ghost Draft
                user = st.session_state.get("user_email", "guest")
                _handle_draft_creation(user, tier, price)
                
                st.session_state.app_mode = "workspace"
                st.rerun()

# --- PAGE: WORKSPACE (ADDRESSING & WRITING) ---
def render_workspace_page():
    tier = st.session_state.get("locked_tier", "Standard")
    st.title(f"Workspace: {tier}")
    
    t1, t2 = st.tabs(["1. Addressing", "2. Writing"])
    
    # --- TAB 1: ADDRESSING ---
    with t1:
        # Address Book Loader
        if database and st.session_state.get("authenticated"):
            saved = database.get_saved_contacts(st.session_state.user_email)
            if saved:
                selected_contact = st.selectbox("📂 Load from Address Book", ["Select..."] + [f"{c['name']}" for c in saved])
                # Logic to populate fields based on selection would go here
        
        with st.form("address_form"):
            c1, c2 = st.columns(2)
            
            # Sender
            with c1:
                st.subheader("Return Address")
                s_name = st.text_input("Name", key="s_name")
                s_street = st.text_input("Street", key="s_street")
                c_a, c_b, c_c = st.columns(3)
                s_city = c_a.text_input("City", key="s_city")
                s_state = c_b.text_input("State", key="s_state")
                s_zip = c_c.text_input("Zip", key="s_zip")
                
            # Recipient
            with c2:
                if tier == "Civic":
                    st.info("🏛️ We automatically find your representatives based on your Return Address.")
                elif tier == "Campaign":
                    st.info("📂 Upload your CSV in the Review step.")
                else:
                    st.subheader("Recipient")
                    r_name = st.text_input("Name", key="r_name")
                    r_street = st.text_input("Street", key="r_street")
                    c_x, c_y, c_z = st.columns(3)
                    r_city = c_x.text_input("City", key="r_city")
                    r_state = c_y.text_input("State", key="r_state")
                    r_zip = c_z.text_input("Zip", key="r_zip")
            
            save_book = st.checkbox("Save to Address Book")
            
            if st.form_submit_button("Save Addresses"):
                # Save to Session
                st.session_state.sender_data = {"name": s_name, "street": s_street, "city": s_city, "state": s_state, "zip": s_zip}
                if tier == "Standard" or tier == "Heirloom":
                    st.session_state.recipient_data = {"name": r_name, "street": r_street, "city": r_city, "state": r_state, "zip": r_zip}
                
                # Save to DB
                if save_book and st.session_state.authenticated:
                    _save_address_book(st.session_state.user_email, st.session_state.sender_data, is_sender=True)
                
                st.success("Addresses Saved!")

    # --- TAB 2: WRITING ---
    with t2:
        st.subheader("Compose Letter")
        
        # Audio
        audio = st.audio_input("Dictate (Whisper AI)")
        if audio and ai_engine:
            with st.spinner("Transcribing..."):
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as t:
                    t.write(audio.getvalue())
                    tpath = t.name
                
                text = ai_engine.transcribe_audio(tpath)
                st.session_state.transcribed_text = text
                try: os.remove(tpath)
                except: pass
                st.rerun()
        
        # Editor
        val = st.session_state.get("transcribed_text", "")
        txt = st.text_area("Body Text", val, height=400)
        if txt: st.session_state.transcribed_text = txt
        
        # AI Tools
        if ai_engine and txt:
            c_ai1, c_ai2 = st.columns(2)
            if c_ai1.button("✨ Polish Grammar"):
                st.session_state.transcribed_text = ai_engine.refine_text(txt, "Grammar")
                st.rerun()
            if c_ai2.button("👔 Make Professional"):
                st.session_state.transcribed_text = ai_engine.refine_text(txt, "Professional")
                st.rerun()

    st.markdown("---")
    if st.button("Review & Pay ➡️", type="primary"):
        st.session_state.app_mode = "review"
        st.rerun()

# --- PAGE: REVIEW (PDF PREVIEW & PAY) ---
def render_review_page():
    st.title("Final Review")
    
    c1, c2 = st.columns([1, 1])
    
    with c1:
        st.subheader("Preview")
        # PDF Generation Logic
        if letter_format:
            try:
                # Mock data if address missing
                s_data = st.session_state.get("sender_data", {})
                r_data = st.session_state.get("recipient_data", {})
                
                pdf_bytes = letter_format.create_pdf(
                    st.session_state.get("transcribed_text", ""),
                    {**s_data, **r_data}, # Flatten dicts
                    tier=st.session_state.locked_tier
                )
                
                # Display PDF
                if pdf_bytes:
                    # Convert bytes to displayable format if needed, or just download btn
                    st.download_button("📄 Download PDF Proof", pdf_bytes, "letter_proof.pdf", "application/pdf")
            except Exception as e:
                st.error(f"Preview Error: {e}")
        else:
            st.warning("PDF Engine missing.")

    with c2:
        st.subheader("Checkout")
        tier = st.session_state.locked_tier
        price = st.session_state.get("locked_price", 2.99)
        
        st.metric("Total", f"${price:.2f}")
        
        if st.button("Pay & Send 🚀", type="primary", use_container_width=True):
            user = st.session_state.get("user_email", "guest")
            
            # 1. Final Save
            d_id = _handle_draft_creation(user, tier, price)
            
            # 2. Payment
            if payment_engine:
                success_url = f"{YOUR_APP_URL}?session_id={{CHECKOUT_SESSION_ID}}"
                try:
                    url, sid = payment_engine.create_checkout_session(
                        f"VerbaPost {tier}", 
                        int(price*100), 
                        success_url, 
                        YOUR_APP_URL,
                        metadata={"draft_id": d_id}
                    )
                    if url: st.link_button("👉 Proceed to Stripe", url, type="primary")
                except Exception as e:
                    st.error(f"Payment Error: {e}")

# --- MAIN ROUTER ---
def render_main():
    render_sidebar()
    mode = st.session_state.get("app_mode", "store")
    
    if mode == "store": render_store_page()
    elif mode == "workspace": render_workspace_page()
    elif mode == "review": render_review_page()
    else: render_store_page()