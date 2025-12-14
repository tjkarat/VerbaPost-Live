import streamlit as st
import logging
import tempfile
import os
import json
import time
from io import BytesIO

# --- ROBUST IMPORTS ---
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

try:
    import promo_engine
except Exception:
    promo_engine = None

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
    """Loads user profile to autofill sender address."""
    if database and st.session_state.get("authenticated") and not st.session_state.get("profile_loaded"):
        try:
            if hasattr(database, "get_user_profile"):
                profile = database.get_user_profile(st.session_state.user_email)
                if profile:
                    # Save to a holding dict
                    st.session_state.sender_data = {
                        "name": profile.get("full_name", ""),
                        "street": profile.get("return_address_street", ""),
                        "city": profile.get("return_address_city", ""),
                        "state": profile.get("return_address_state", ""),
                        "zip": profile.get("return_address_zip", ""),
                        "country": profile.get("return_address_country", "US")
                    }
                    # FORCE HYDRATION: Push directly to widget keys
                    st.session_state.s_n = profile.get("full_name", "")
                    st.session_state.s_s = profile.get("return_address_street", "")
                    st.session_state.s_c = profile.get("return_address_city", "")
                    st.session_state.s_st = profile.get("return_address_state", "")
                    st.session_state.s_z = profile.get("return_address_zip", "")
            
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
            
            # PROMO CODE LOGIC
            promo_code = st.text_input("Promo Code", key="store_promo")
            if promo_code and promo_engine:
                valid, discount, p_type = promo_engine.validate_promo(promo_code)
                if valid:
                    st.success(f"Code Applied: {discount}% OFF")
                    price = price * (1 - discount/100)
                    st.metric("New Price", f"${price:.2f}")
                else:
                    st.error("Invalid Code")

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
    # Security Guard
    if not st.session_state.get("paid_order", False):
        st.warning("🔒 Please pay to access the Workspace.")
        st.session_state.app_mode = "store"
        time.sleep(1.5)
        st.rerun()

    # Load profile and hydrate keys if needed
    _load_user_profile()

    tier = st.session_state.get("locked_tier", "Standard")
    
    # --- HEADER & TUTORIAL ---
    st.markdown(f"## 📮 Workspace: {tier}")
    
    if "first_visit" not in st.session_state:
        st.info("👋 Welcome! Follow the steps below to dictate and send your letter.")
        st.session_state.first_visit = False

    t1, t2 = st.tabs(["📍 Step 1: Addressing", "✍️ Step 2: Composing"])
    
    # --- TAB 1: ADDRESSING ---
    with t1:
        st.caption("Tell us where this letter is going.")
        
        # --- ADDRESS BOOK LOGIC ---
        if database and st.session_state.get("authenticated"):
            try:
                saved = database.get_saved_contacts(st.session_state.user_email)
                if saved:
                    # Create a friendly label for the dropdown
                    opts = {f"{x['name']} ({x.get('street','')})": x for x in saved}
                    selected_key = st.selectbox("📂 Load from Address Book", ["Select..."] + list(opts.keys()))
                    
                    # If user selects someone, force-feed the form keys
                    if selected_key != "Select...":
                        data = opts[selected_key]
                        st.session_state.r_n = data.get("name", "")
                        st.session_state.r_s = data.get("street", "")
                        st.session_state.r_c = data.get("city", "")
                        st.session_state.r_st = data.get("state", "")
                        st.session_state.r_z = data.get("zip", "")
            except Exception: pass
        # --------------------------

        with st.form("addr_form"):
            c1, c2 = st.columns(2)
            
            # SENDER
            with c1:
                st.markdown("### 🏠 From (You)")
                # Keys allow auto-population from profile
                s_name = st.text_input("Name", key="s_n")
                s_str = st.text_input("Street", key="s_s")
                sa, sb, sc = st.columns(3)
                s_city = sa.text_input("City", key="s_c")
                s_state = sb.text_input("State", key="s_st")
                s_zip = sc.text_input("Zip", key="s_z")
                s_country = st.selectbox("Country", ["US", "CA", "UK"], index=0, key="s_co")

            # RECIPIENT
            with c2:
                if tier == "Civic":
                    st.markdown("### 🏛️ To (Congress)")
                    st.info("We automatically route your letter to your 2 Senators and 1 Representative based on your Return Address.")
                    
                    if st.form_submit_button("🔍 Verify My Representatives"):
                        if civic_engine and s_str and s_zip:
                            with st.spinner("Consulting Geocodio..."):
                                addr_str = f"{s_str}, {s_city}, {s_state} {s_zip}"
                                reps = civic_engine.get_representatives(addr_str)
                                if reps:
                                    st.success(f"Found: {', '.join(reps)}")
                                    st.session_state.civic_reps = reps
                                else:
                                    st.error("No representatives found.")
                        else:
                            st.error("Enter Return Address first.")
                
                elif tier == "Campaign":
                    st.markdown("### 📂 Bulk List")
                    st.info("Please upload your CSV file in the next step.")
                
                else:
                    st.markdown("### 📬 To (Recipient)")
                    # Keys allow auto-population from Address Book
                    r_name = st.text_input("Name", key="r_n")
                    r_str = st.text_input("Street", key="r_s")
                    ra, rb, rc = st.columns(3)
                    r_city = ra.text_input("City", key="r_c")
                    r_state = rb.text_input("State", key="r_st")
                    r_zip = rc.text_input("Zip", key="r_z")
                    r_country = st.selectbox("Country", ["US", "CA", "UK"], index=0, key="r_co")

            # Save Actions
            if tier not in ["Civic", "Campaign"]:
                save_b = st.checkbox("Save Recipient to Address Book")
                if st.form_submit_button("✅ Save Addresses"):
                    st.session_state.sender_data = {"name": s_name, "street": s_str, "city": s_city, "state": s_state, "zip": s_zip, "country": s_country}
                    st.session_state.recipient_data = {"name": r_name, "street": r_str, "city": r_city, "state": r_state, "zip": r_zip, "country": r_country}
                    
                    if save_b and st.session_state.authenticated:
                        _save_address_book(st.session_state.user_email, st.session_state.recipient_data, is_sender=False)
                    st.success("Addresses Saved!")

    # --- TAB 2: WRITING ---
    with t2:
        st.markdown("### 🎙️ Dictation Studio")
        
        with st.expander("📖 How to Record (Click to Open)", expanded=True):
            st.markdown("""
            1. **Hit Record:** Click the microphone icon below.
            2. **Speak Clearly:** Dictate your letter. Don't worry about mistakes!
            3. **Stop:** Click the icon again to stop recording.
            4. **Transcribe:** Click the 'Transcribe Audio' button.
            """)

        col_mic, col_file = st.columns(2)
        with col_mic:
            audio_mic = st.audio_input("🎤 Record Voice")
        with col_file:
            uploaded_file = st.file_uploader("📂 Or Upload Audio", type=["mp3", "wav", "m4a"])
        
        # Processing Logic
        active_audio = uploaded_file or audio_mic
        if active_audio and ai_engine:
            if st.button("✨ Transcribe Audio", type="primary"):
                with st.spinner("🧠 AI is listening..."):
                    suffix = ".wav" if not uploaded_file else os.path.splitext(uploaded_file.name)[1]
                    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as t:
                        t.write(active_audio.getvalue())
                        tpath = t.name
                    try:
                        text = ai_engine.transcribe_audio(tpath)
                        st.session_state.transcribed_text = text
                        st.success("Transcription Complete!")
                    except Exception as e:
                        st.error(f"Transcription Failed: {e}")
                    finally:
                        try: os.remove(tpath)
                        except: pass
                    st.rerun()

        # Editor
        st.markdown("#### 📝 Edit Your Letter")
        val = st.session_state.get("transcribed_text", "")
        txt = st.text_area("Letter Body", val, height=400, placeholder="Your transcribed text will appear here...")
        if txt: st.session_state.transcribed_text = txt
        
        # AI Buttons
        if ai_engine and txt:
            st.markdown("#### 🤖 AI Polish")
            c_ai1, c_ai2 = st.columns(2)
            if c_ai1.button("✨ Fix Grammar & Spelling", use_container_width=True):
                with st.spinner("Polishing..."):
                    st.session_state.transcribed_text = ai_engine.refine_text(txt, "Grammar")
                    st.rerun()
            if c_ai2.button("👔 Make Professional", use_container_width=True):
                with st.spinner("Refining..."):
                    st.session_state.transcribed_text = ai_engine.refine_text(txt, "Professional")
                    st.rerun()

    st.markdown("---")
    if st.button("Review & Send ➡️", type="primary", use_container_width=True):
        st.session_state.app_mode = "review"
        st.rerun()

# --- PAGE: REVIEW ---
def render_review_page():
    if not st.session_state.get("paid_order", False):
        st.session_state.app_mode = "store"
        st.rerun()

    if "locked_tier" not in st.session_state:
        st.session_state.locked_tier = "Standard"

    st.markdown("## 🔍 Final Review")
    
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Document Preview")
        if letter_format:
            try:
                s = st.session_state.get("sender_data", {})
                r = st.session_state.get("recipient_data", {})
                
                # Civic Override for PDF
                if st.session_state.locked_tier == "Civic":
                    r = {"name": "US Congress", "street": "Washington, DC"}

                pdf = letter_format.create_pdf(
                    st.session_state.get("transcribed_text", ""), 
                    s, 
                    r, 
                    st.session_state.locked_tier
                )
                if pdf:
                    st.success("✅ PDF Generated")
                    st.download_button("📄 Download Proof", pdf, "letter.pdf", "application/pdf")
            except Exception as e:
                st.error(f"Preview Error: {e}")
                
    with c2:
        st.subheader("Ready to Send?")
        st.info("Payment Confirmed. One click to mail.")
        if st.button("🚀 Send Letter Now", type="primary", use_container_width=True):
            st.balloons()
            st.success("Letter Sent! Check your email for tracking.")
            st.session_state.paid_order = False
            st.session_state.payment_url = None
            time.sleep(3)
            st.session_state.app_mode = "store"
            st.rerun()

# --- MAIN ENTRY ---
def render_main():
    render_sidebar()
    mode = st.session_state.get("app_mode", "store")
    if mode == "store": render_store_page()
    elif mode == "workspace": render_workspace_page()
    elif mode == "review": render_review_page()
    else: render_store_page()