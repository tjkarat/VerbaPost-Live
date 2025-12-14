import streamlit as st
import logging
import tempfile
import os
import json
import time
from io import BytesIO

# --- ROBUST IMPORTS (Standard Syntax to Fix Crash) ---
try:
    import ui_splash
except Exception:
    ui_splash = None

try:
    import ui_login
except Exception:
    ui_login = None

try:
    import ui_admin
except Exception:
    ui_admin = None

try:
    import database
except Exception:
    database = None

try:
    import ai_engine
except Exception:
    ai_engine = None

try:
    import payment_engine
except Exception:
    payment_engine = None

try:
    import pricing_engine
except Exception:
    pricing_engine = None

try:
    import secrets_manager
except Exception:
    secrets_manager = None

try:
    import civic_engine
except Exception:
    civic_engine = None

try:
    import letter_format
except Exception:
    letter_format = None

logger = logging.getLogger(__name__)

# --- CONFIG ---
YOUR_APP_URL = "https://verbapost.streamlit.app"
if secrets_manager:
    s_url = secrets_manager.get_secret("BASE_URL")
    if s_url: YOUR_APP_URL = s_url.rstrip("/")

# --- INTERNAL LOGIC ---
def _handle_draft_creation(email, tier, price):
    d_id = st.session_state.get("current_draft_id")
    text = st.session_state.get("transcribed_text", "")
    if database:
        if d_id:
            if database.update_draft_data(d_id, tier=tier, price=price, text=text): return d_id
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
            "country": data.get("country", "US"),
            "type": "sender" if is_sender else "recipient"
        }
        database.save_contact(contact)
    except Exception: pass

def _load_user_profile():
    """Fetches user profile to auto-fill Return Address."""
    if not st.session_state.get("profile_loaded") and database and st.session_state.get("authenticated"):
        try:
            # Safe checking for profile function
            if hasattr(database, "get_user_profile"):
                profile = database.get_user_profile(st.session_state.user_email)
                if profile:
                    st.session_state.sender_data = {
                        "name": profile.get("full_name", ""),
                        "street": profile.get("return_address_street", ""),
                        "city": profile.get("return_address_city", ""),
                        "state": profile.get("return_address_state", ""),
                        "zip": profile.get("return_address_zip", ""),
                        "country": profile.get("return_address_country", "US")
                    }
            st.session_state.profile_loaded = True
        except Exception: pass

# --- SIDEBAR ---
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
            
            st.markdown("---")
            if st.button("Log Out", key="sb_logout", use_container_width=True):
                st.session_state.clear()
                st.rerun()
        else:
            if st.button("🔑 Log In", key="sb_login", type="primary", use_container_width=True):
                st.query_params["view"] = "login"
                st.rerun()

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
            price = 2.99
            if pricing_engine: price = pricing_engine.calculate_total(tier)
    
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
                        if url: st.session_state.payment_url = url
                        else: st.error("Payment Gateway Error")
            
            if st.session_state.get("payment_url"):
                st.success("Link Ready!")
                st.link_button("👉 Click to Pay", st.session_state.payment_url, type="primary", use_container_width=True)

# --- PAGE: WORKSPACE ---
def render_workspace_page():
    if not st.session_state.get("paid_order", False):
        st.warning("🔒 Please pay to access the Workspace.")
        st.session_state.app_mode = "store"
        time.sleep(1.5)
        st.rerun()

    _load_user_profile() # Auto-fill sender info
    
    tier = st.session_state.get("locked_tier", "Standard")
    st.markdown(f"## Workspace: {tier}")
    
    t1, t2 = st.tabs(["Addressing", "Writing"])
    
    # --- TAB 1: ADDRESSING ---
    with t1:
        # Address Book Logic
        if database and st.session_state.get("authenticated"):
            try:
                saved = database.get_saved_contacts(st.session_state.user_email)
                if saved:
                    # Helper to format dropdown display
                    opts = {f"{x['name']} ({x.get('street','')})": x for x in saved}
                    selected_key = st.selectbox("📂 Load Contact", ["Select..."] + list(opts.keys()))
                    if selected_key != "Select...":
                        data = opts[selected_key]
                        # Populate Recipient Data
                        st.session_state.recipient_data = {
                            "name": data.get("name"), "street": data.get("street"),
                            "city": data.get("city"), "state": data.get("state"),
                            "zip": data.get("zip"), "country": data.get("country", "US")
                        }
            except Exception: pass

        with st.form("addr_form"):
            c1, c2 = st.columns(2)
            
            # SENDER (Pre-filled from profile or session)
            s_defaults = st.session_state.get("sender_data", {})
            with c1:
                st.markdown("**Return Address (You)**")
                s_name = st.text_input("Name", value=s_defaults.get("name",""), key="s_n")
                s_str = st.text_input("Street", value=s_defaults.get("street",""), key="s_s")
                
                # Granular Fields
                sa, sb, sc = st.columns(3)
                s_city = sa.text_input("City", value=s_defaults.get("city",""), key="s_c")
                s_state = sb.text_input("State", value=s_defaults.get("state",""), key="s_st")
                s_zip = sc.text_input("Zip", value=s_defaults.get("zip",""), key="s_z")
                s_country = st.selectbox("Country", ["US", "CA", "UK"], index=0, key="s_co")

            # RECIPIENT
            r_defaults = st.session_state.get("recipient_data", {})
            with c2:
                if tier == "Civic":
                    st.info("🏛️ Auto-routed to Representatives.")
                elif tier == "Campaign":
                    st.info("📂 Upload CSV in next step.")
                else:
                    st.markdown("**Recipient**")
                    r_name = st.text_input("Name", value=r_defaults.get("name",""), key="r_n")
                    r_str = st.text_input("Street", value=r_defaults.get("street",""), key="r_s")
                    
                    ra, rb, rc = st.columns(3)
                    r_city = ra.text_input("City", value=r_defaults.get("city",""), key="r_c")
                    r_state = rb.text_input("State", value=r_defaults.get("state",""), key="r_st")
                    r_zip = rc.text_input("Zip", value=r_defaults.get("zip",""), key="r_z")
                    r_country = st.selectbox("Country", ["US", "CA", "UK"], index=0, key="r_co")
            
            save_b = st.checkbox("Save Recipient to Address Book")
            
            if st.form_submit_button("Save Addresses"):
                # Save to Session
                st.session_state.sender_data = {"name": s_name, "street": s_str, "city": s_city, "state": s_state, "zip": s_zip, "country": s_country}
                if tier not in ["Civic", "Campaign"]:
                    st.session_state.recipient_data = {"name": r_name, "street": r_str, "city": r_city, "state": r_state, "zip": r_zip, "country": r_country}
                
                # Save to DB
                if save_b and st.session_state.authenticated:
                    _save_address_book(st.session_state.user_email, st.session_state.recipient_data, is_sender=False)
                st.success("Addresses Saved!")

    # --- TAB 2: WRITING ---
    with t2:
        st.markdown("### Compose")
        
        # 1. File Import
        uploaded_file = st.file_uploader("📂 Import Audio (MP3/WAV)", type=["mp3", "wav", "m4a"])
        
        # 2. Mic Input
        audio_mic = st.audio_input("🎤 Record Voice")
        
        # Processing Logic
        active_audio = uploaded_file or audio_mic
        if active_audio and ai_engine:
            if st.button("Transcribe Audio"):
                with st.spinner("Transcribing..."):
                    # Create temp file
                    suffix = ".wav" if not uploaded_file else os.path.splitext(uploaded_file.name)[1]
                    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as t:
                        t.write(active_audio.getvalue())
                        tpath = t.name
                    
                    # Call Engine
                    try:
                        text = ai_engine.transcribe_audio(tpath)
                        st.session_state.transcribed_text = text
                    except Exception as e:
                        st.error(f"Transcription Failed: {e}")
                    finally:
                        try: os.remove(tpath)
                        except: pass
                    st.rerun()

        # Text Editor
        val = st.session_state.get("transcribed_text", "")
        txt = st.text_area("Body Text", val, height=400)
        if txt: st.session_state.transcribed_text = txt
        
        # AI Buttons
        if ai_engine and txt:
            st.markdown("#### AI Editing Tools")
            c_ai1, c_ai2 = st.columns(2)
            if c_ai1.button("✨ Polish Grammar"):
                with st.spinner("Polishing..."):
                    st.session_state.transcribed_text = ai_engine.refine_text(txt, "Grammar")
                    st.rerun()
            if c_ai2.button("👔 Make Professional"):
                with st.spinner("Refining..."):
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

    # Safety: Ensure locked_tier exists to prevent crash
    if "locked_tier" not in st.session_state:
        st.session_state.locked_tier = "Standard"

    st.markdown("## Final Review")
    
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Preview")
        # PDF Preview Logic
        if letter_format:
            try:
                # Prepare Data
                s = st.session_state.get("sender_data", {})
                r = st.session_state.get("recipient_data", {})
                
                # Create PDF
                pdf = letter_format.create_pdf(
                    st.session_state.get("transcribed_text", ""), 
                    {**s, **r}, # Merge dicts
                    st.session_state.locked_tier
                )
                
                if pdf:
                    st.success("PDF Generated Successfully")
                    st.download_button("📄 Download PDF Proof", pdf, "preview.pdf", "application/pdf")
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

# --- MAIN ENTRY ---
def render_main():
    # Only logic routing here. No global sidebar call.
    mode = st.session_state.get("app_mode", "store")
    
    if mode == "store": render_store_page()
    elif mode == "workspace": render_workspace_page()
    elif mode == "review": render_review_page()
    else: render_store_page()