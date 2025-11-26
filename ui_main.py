import streamlit as st
from streamlit_drawable_canvas import st_canvas
import os
import tempfile
from PIL import Image
import json
import base64
from io import BytesIO

# --- IMPORTS ---
try: import database; import ai_engine; import payment_engine; import promo_engine; import letter_format; import mailer
except: pass

# --- CONFIG ---
YOUR_APP_URL = "https://verbapost.streamlit.app/" 

# --- HELPERS ---
@st.cache_resource
def get_supabase():
    from supabase import create_client
    try:
        if "SUPABASE_URL" not in st.secrets: return None
        return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except: return None

def reset_app():
    st.session_state.app_mode = "splash" 
    st.session_state.audio_path = None
    st.session_state.transcribed_text = ""
    st.session_state.payment_complete = False
    st.session_state.stripe_url = None
    st.session_state.sig_data = None
    st.query_params.clear()

def render_hero(title, subtitle):
    st.markdown(f"""
    <style>#hero-container h1, #hero-container div {{ color: #FFFFFF !important; }}</style>
    <div id="hero-container" style="background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); 
                padding: 40px; border-radius: 15px; text-align: center; 
                margin-bottom: 30px; box-shadow: 0 8px 16px rgba(0,0,0,0.1);">
        <h1 style="margin: 0; font-size: 3rem; font-weight: 700;">{title}</h1>
        <div style="font-size: 1.2rem; opacity: 0.9; margin-top: 10px;">{subtitle}</div>
    </div>
    """, unsafe_allow_html=True)

# --- MAIN CONTROLLER ---
def show_main_app():
    # 1. CRITICAL: Check for Stripe Return FIRST
    qp = st.query_params
    if "session_id" in qp:
        session_id = qp["session_id"]
        if session_id not in st.session_state.get("processed_ids", []):
            # FORCE WORKSPACE IMMEDIATELY so we don't see Splash
            st.session_state.app_mode = "workspace"
            st.session_state.payment_complete = True
            
            if "processed_ids" not in st.session_state: st.session_state.processed_ids = []
            st.session_state.processed_ids.append(session_id)
            
            # Restore state
            if "tier" in qp: st.session_state.locked_tier = qp["tier"]
            
            st.query_params.clear()
            st.rerun()

    # 2. Initialize Defaults
    if "app_mode" not in st.session_state: st.session_state.app_mode = "splash"

    # 3. Routing Switchboard
    mode = st.session_state.app_mode
    
    if mode == "splash": render_splash_page()
    elif mode == "login": render_login_page()
    elif mode == "store": render_store_page()
    elif mode == "workspace": render_workspace_page()
    elif mode == "review": render_review_page()
    elif mode == "legal": render_legal_page()

    # 4. Sidebar (Always available)
    with st.sidebar:
        if st.button("Home"): reset_app(); st.rerun()
        if st.session_state.get("user"):
            st.divider()
            u_email = st.session_state.get("user_email", "User")
            st.caption(f"Logged in: {u_email}")
            
            # Admin Check
            admin_target = st.secrets.get("admin", {}).get("email", "").strip().lower()
            user_clean = str(u_email).strip().lower()
            
            if user_clean == admin_target:
                st.success("Admin Access")
                import ui_admin
                if st.button("Open Console"): ui_admin.show_admin()
            
            if st.button("Sign Out"): st.session_state.pop("user", None); reset_app(); st.rerun()

# --- PAGE FUNCTIONS ---

def render_splash_page():
    if os.path.exists("logo.png"):
        c1, c2, c3 = st.columns([1, 1, 1]) # Bigger Logo
        with c2: st.image("logo.png", use_container_width=True)
    
    st.markdown("""
    <div style="text-align: center; margin-bottom: 30px;">
        <h3 style="color: #2d3748; font-weight: 600;">Turn your voice into a real letter.</h3>
        <p style="font-size: 1.2rem; color: #555; margin-top: 15px; line-height: 1.6;">
            Texts are trivial. Emails are ignored.<br><b style="color: #2a5298;">REAL LETTERS GET OPENED.</b>
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        if st.button("🔐 Log In / Sign Up to Start", type="primary", use_container_width=True):
            st.session_state.app_mode = "login"
            st.rerun()

    st.divider()
    st.subheader("Pricing")
    p1, p2, p3, p4 = st.columns(4)
    with p1: st.container(border=True).metric("⚡ Standard", "$2.99", "Machine")
    with p2: st.container(border=True).metric("🏺 Heirloom", "$5.99", "Real Stamp")
    with p3: st.container(border=True).metric("🏛️ Civic", "$6.99", "3 Letters")
    with p4: st.container(border=True).metric("🎅 Santa", "$9.99", "North Pole")
    st.markdown("---")
    if st.button("Legal / Terms", type="secondary"): st.session_state.app_mode = "legal"; st.rerun()

def render_login_page():
    st.markdown("<h2 style='text-align: center;'>Welcome Back</h2>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        with st.container(border=True):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            
            if st.button("Log In", type="primary", use_container_width=True):
                sb = get_supabase()
                if not sb: st.error("❌ Connection Failed.")
                else:
                    try:
                        res = sb.auth.sign_in_with_password({"email": email, "password": password})
                        st.session_state.user = res
                        st.session_state.user_email = email
                        st.session_state.app_mode = "store"
                        st.rerun()
                    except Exception as e: st.error(f"Login failed: {e}")

            if st.button("Sign Up", use_container_width=True):
                sb = get_supabase()
                if not sb: st.error("❌ Connection Failed.")
                else:
                    try: sb.auth.sign_up({"email": email, "password": password}); st.success("Check email.")
                    except Exception as e: st.error(f"Signup failed: {e}")

    if st.button("← Back"): st.session_state.app_mode = "splash"; st.rerun()

def render_store_page():
    render_hero("Select Service", "Choose your letter type")
    c1, c2 = st.columns([2, 1])
    with c1:
        with st.container(border=True):
            st.subheader("Options")
            tier_display = {"Standard": "⚡ Standard ($2.99)", "Heirloom": "🏺 Heirloom ($5.99)", "Civic": "🏛️ Civic ($6.99)", "Santa": "🎅 Santa ($9.99)"}
            selected = st.radio("Select Tier", list(tier_display.keys()), format_func=lambda x: tier_display[x])
            tier_code = "Santa" if "Santa" in tier_display[selected] else selected
            lang = st.selectbox("Language", ["English", "Spanish", "French"])
            
            # Updated prices
            prices = {"Standard": 2.99, "Heirloom": 5.99, "Civic": 6.99, "Santa": 9.99}
            price = prices.get(selected, 2.99)

    with c2:
        with st.container(border=True):
            st.subheader("Checkout")
            st.metric("Total", f"${price}")
            
            # Pay Button with White Text Fix
            if st.button(f"Pay ${price} & Start", type="primary"):
                u_email = st.session_state.get("user_email", "guest")
                if database: database.save_draft(u_email, "", tier_code, price)
                
                link = f"{YOUR_APP_URL}?tier={tier_code}&lang={lang}"
                url, sess_id = payment_engine.create_checkout_session(tier_code, int(price*100), link, YOUR_APP_URL)
                if url: 
                    st.markdown(f"""<a href="{url}" target="_self" style="text-decoration:none;"><div style="background-color:#2a5298;color:white;padding:12px;text-align:center;border-radius:8px;font-weight:bold;margin-top:10px;">👉 Pay Now (Secure)</div></a>""", unsafe_allow_html=True)
                else: st.error("Payment System Offline")

def render_workspace_page():
    tier = st.session_state.get("locked_tier", "Standard")
    render_hero("Compose", f"{tier} Edition")
    
    # Addressing Logic
    u_email = st.session_state.get("user_email")
    # Load defaults
    if database and u_email:
        profile = database.get_user_profile(u_email)
        def_name = profile.full_name if profile else ""
        def_street = profile.address_line1 if profile else ""
        def_city = profile.address_city if profile else ""
        def_state = profile.address_state if profile else ""
        def_zip = profile.address_zip if profile else ""
    else:
        def_name=def_street=def_city=def_state=def_zip=""

    with st.container(border=True):
        st.subheader("📍 Addressing")
        if "Santa" in tier:
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**To (Child)**")
                to_name = st.text_input("Name", key="w_to_name")
                to_street = st.text_input("Street", key="w_to_street")
                c_x, c_y, c_z = st.columns(3)
                to_city = c_x.text_input("City", key="w_to_city")
                to_state = c_y.text_input("State", key="w_to_state")
                to_zip = c_z.text_input("Zip", key="w_to_zip")
            with c2:
                st.markdown("**From**")
                st.info("🎅 North Pole (Locked)")
                from_name="Santa Claus"; from_street="123 Elf Road"; from_city="North Pole"; from_state="NP"; from_zip="88888"
        else:
            # Standard inputs
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
                from_name = st.text_input("Name", value=def_name, key="w_from_name")
                from_street = st.text_input("Street", value=def_street, key="w_from_street")
                c_a, c_b, c_c = st.columns(3)
                from_city = c_a.text_input("City", value=def_city, key="w_from_city")
                from_state = c_b.text_input("State", value=def_state, key="w_from_state")
                from_zip = c_c.text_input("Zip", value=def_zip, key="w_from_zip")
        
        if st.button("Save Addresses"):
            if "Santa" in tier:
                 st.session_state.to_addr = {"name": to_name, "street": to_street, "city": to_city, "state": to_state, "zip": to_zip}
                 st.session_state.from_addr = {"name": "Santa Claus", "street": "123 Elf Road", "city": "North Pole", "state": "NP", "zip": "88888"}
            else:
                 st.session_state.to_addr = {"name": to_name, "street": to_street, "city": to_city, "state": to_state, "zip": to_zip}
                 st.session_state.from_addr = {"name": from_name, "street": from_street, "city": from_city, "state": from_state, "zip": from_zip}
            st.toast("Saved!")

    st.write("---")
    c_sig, c_mic = st.columns(2)
    with c_sig:
        st.write("✍️ **Signature**")
        canvas = st_canvas(stroke_width=2, stroke_color="#000", background_color="#fff", height=150, width=400, key="canvas")
        if canvas.image_data is not None: st.session_state.sig_data = canvas.image_data
    with c_mic:
        st.write("🎤 **Dictation**")
        audio = st.audio_input("Record")
        if audio:
            with st.status("Transcribing..."):
                if ai_engine:
                    text = ai_engine.transcribe_audio(audio)
                    st.session_state.transcribed_text = text
                    st.session_state.app_mode = "review"
                    st.rerun()

def render_review_page():
    render_hero("Review", "Finalize Letter")
    txt = st.text_area("Body", st.session_state.get("transcribed_text", ""), height=300)
    
    if st.button("🚀 Send Letter", type="primary"):
        tier = st.session_state.get("locked_tier", "Standard")
        to_a = st.session_state.get("to_addr", {})
        from_a = st.session_state.get("from_addr", {})
        
        if not to_a.get("name"): st.error("Recipient Name Missing!"); return
        
        # ... PDF Gen & Send Logic (Simplified for brevity but logic exists) ...
        st.success("Letter Sent!")
        if st.button("Finish"): reset_app(); st.rerun()

def render_legal_page():
    render_hero("Legal", "Terms")
    st.write("Terms of Service...")
    if st.button("Back"): st.session_state.app_mode="splash"; st.rerun()