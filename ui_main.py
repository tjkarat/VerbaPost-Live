import streamlit as st
import logging
import tempfile
import os
import json
import time

# --- ROBUST IMPORTS ---
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

logger = logging.getLogger(__name__)

# --- CONFIG ---
YOUR_APP_URL = "https://verbapost.streamlit.app"
if secrets_manager:
    s_url = secrets_manager.get_secret("BASE_URL")
    if s_url: YOUR_APP_URL = s_url.rstrip("/")

# --- INTERNAL LOGIC ---
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

def _save_address_book(user_email, data, is_sender=False):
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
    except Exception: pass

# --- SIDEBAR (Logic Only) ---
def render_sidebar():
    with st.sidebar:
        st.markdown("<div style='text-align: center;'><h1>📮<br>VerbaPost</h1></div>", unsafe_allow_html=True)
        st.markdown("---")
        
        if st.session_state.get("authenticated"):
            st.success(f"👤 {st.session_state.get('user_email', 'User')}")
            
            st.markdown("---")
            if st.button("🏪 Store", key="nav_store", use_container_width=True): 
                st.session_state.app_mode = "store"
                st.rerun()
            
            # WORKSPACE BUTTON
            if st.button("✍️ Workspace", key="nav_work", use_container_width=True): 
                st.session_state.app_mode = "workspace" 
                st.rerun()
            
            st.markdown("---")
            if st.button("Log Out", key="sb_logout", use_container_width=True):
                st.session_state.clear()
                st.rerun()
        else:
            if st.button("🔑 Log In", key="sb_login", type="primary", use_container_width=True):
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
                if st.button("🛡️ Admin Console", key="sb_admin", use_container_width=True):
                    st.query_params["view"] = "admin"
                    st.rerun()
        except: pass

# --- PAGE: STORE ---
def render_store_page():
    st.markdown("## Select Service")
    
    # Campaign Toggle
    is_camp = st.toggle("📢 Bulk Campaign Mode", value=st.session_state.get("is_campaign", False))
    st.session_state.is_campaign = is_camp
    
    c1, c2 = st.columns([2, 1])
    
    with c1:
        if is_camp:
            st.info("Upload CSV in workspace. Base Price: $2.99/letter.")
            st.session_state.locked_tier = "Campaign"
            price = 2.99
        else:
            tier = st.radio("Tier", ["Standard", "Heirloom", "Civic", "Santa"],
                          captions=["$2.99 - Basic", "$5.99 - Archival", "$6.99 - Congress", "$9.99 - North Pole"])
            st.session_state.locked_tier = tier
            
            # Pricing logic
            price = 2.99
            if pricing_engine:
                price = pricing_engine.calculate_total(tier)
    
    with c2:
        with st.container(border=True):
            st.metric("Price / Unit", f"${price:.2f}")
            
            if st.button("Generate Checkout Link 💳", type="primary", use_container_width=True):
                st.session_state.locked_price = price
                u = st.session_state.get("user_email", "guest")
                d_id = _handle_draft_creation(u, st.session_state.locked_tier, price)
                
                if payment_engine:
                    with st.spinner("Creating link..."):
                        success_url = f"{YOUR_APP_URL}?session_id={{CHECKOUT_SESSION_ID}}"
                        url, sid = payment_engine.create_checkout_session(
                            f"VerbaPost {st.session_state.locked_tier}", 
                            int(price*100), 
                            success_url, 
                            YOUR_APP_URL, 
                            metadata={"draft": d_id}
                        )
                        if url:
                            st.session_state.payment_url = url
                        else:
                            st.error("Payment Gateway Error")
            
            if st.session_state.get("payment_url"):
                st.success("Link Ready!")
                st.link_button("👉 Click to Pay", st.session_state.payment_url, type="primary", use_container_width=True)

# --- PAGE: WORKSPACE ---
def render_workspace_page():
    # Security Guard
    if not st.session_state.get("paid_order", False):
        st.warning("🔒 Please pay to access the Workspace.")
        st.session_state.app_mode = "store"
        time.sleep(1.5)
        st.rerun()

    tier = st.session_state.get("locked_tier", "Standard")
    st.markdown(f"## Workspace: {tier}")
    
    t1, t2 = st.tabs(["Addressing", "Writing"])
    
    with t1:
        if database and st.session_state.get("authenticated"):
            try:
                saved = database.get_saved_contacts(st.session_state.user_email)
                if saved:
                    st.selectbox("📂 Load Contact", ["Select..."] + [x['name'] for x in saved])
            except: pass

        with st.form("addr_form"):
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**Return Address**")
                s_name = st.text_input("Name", key="s_n")
                s_str = st.text_input("Street", key="s_s")
                s_csz = st.text_input("City, State Zip", key="s_c")
            with c2:
                if tier == "Civic":
                    st.info("🏛️ Auto-routed to Representatives.")
                elif tier == "Campaign":
                    st.info("📂 Upload CSV in next step.")
                else:
                    st.markdown("**Recipient**")
                    r_name = st.text_input("Name", key="r_n")
                    r_str = st.text_input("Street", key="r_s")
                    r_csz = st.text_input("City, State Zip", key="r_c")
            
            save_b = st.checkbox("Save to Address Book")
            if st.form_submit_button("Save Addresses"):
                st.session_state.sender_data = {"name": s_name, "street": s_str, "csz": s_csz}
                if tier not in ["Civic", "Campaign"]:
                    st.session_state.recipient_data = {"name": r_name, "street": r_str, "csz": r_csz}
                
                if save_b and st.session_state.authenticated:
                    _save_address_book(st.session_state.user_email, st.session_state.sender_data, True)
                st.success("Saved!")

    with t2:
        st.markdown("### Compose")
        audio = st.audio_input("Dictate")
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
        
        val = st.session_state.get("transcribed_text", "")
        txt = st.text_area("Body", val, height=400)
        if txt: st.session_state.transcribed_text = txt
        
        if ai_engine and txt:
            if st.button("✨ Polish (AI)"):
                 st.session_state.transcribed_text = ai_engine.refine_text(txt, "Professional")
                 st.rerun()

    if st.button("Review & Send ➡️", type="primary"):
        st.session_state.app_mode = "review"
        st.rerun()

# --- PAGE: REVIEW ---
def render_review_page():
    if not st.session_state.get("paid_order", False):
        st.session_state.app_mode = "store"
        st.rerun()

    st.markdown("## Final Review")
    
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Preview")
        if letter_format:
            try:
                s = st.session_state.get("sender_data", {})
                r = st.session_state.get("recipient_data", {})
                pdf = letter_format.create_pdf(st.session_state.get("transcribed_text", ""), {**s, **r}, st.session_state.locked_tier)
                if pdf:
                    st.download_button("📄 Download PDF", pdf, "preview.pdf")
            except Exception as e:
                st.error(f"Preview Error: {e}")
                
    with c2:
        st.subheader("Action")
        st.success("Payment Confirmed ✅")
        if st.button("🚀 Send Letter Now", type="primary", use_container_width=True):
            st.balloons()
            st.success("Letter Sent!")
            st.session_state.paid_order = False
            st.session_state.payment_url = None
            time.sleep(3)
            st.session_state.app_mode = "store"
            st.rerun()

# --- MAIN CONTROLLER ENTRY ---
def render_main():
    # CRITICAL FIX: DO NOT CALL render_sidebar() HERE
    # It is already called by main.py
    
    mode = st.session_state.get("app_mode", "store")
    
    if mode == "store": render_store_page()
    elif mode == "workspace": render_workspace_page()
    elif mode == "review": render_review_page()
    else: render_store_page()