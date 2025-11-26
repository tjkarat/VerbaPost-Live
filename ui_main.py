import streamlit as st
from streamlit_drawable_canvas import st_canvas
import os
import tempfile
from PIL import Image
import json
import base64
from io import BytesIO

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

# --- CONFIG ---
YOUR_APP_URL = "https://verbapost.streamlit.app/" 

# --- HELPER: SUPABASE ---
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
    st.session_state.to_addr = {}
    st.session_state.from_addr = {}
    st.session_state.civic_targets = []
    st.query_params.clear()

def render_hero(title, subtitle):
    st.markdown(f"""
    <style>
        #hero-container h1, #hero-container div {{ color: #FFFFFF !important; }}
    </style>
    <div id="hero-container" style="background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); 
                padding: 40px; border-radius: 15px; text-align: center; 
                margin-bottom: 30px; box-shadow: 0 8px 16px rgba(0,0,0,0.1);">
        <h1 style="margin: 0; font-size: 3rem; font-weight: 700;">{title}</h1>
        <div style="font-size: 1.2rem; opacity: 0.9; margin-top: 10px;">{subtitle}</div>
    </div>
    """, unsafe_allow_html=True)

# --- PAGE: LEGAL ---
def render_legal_page():
    render_hero("Legal Center", "Transparency & Trust")
    # ... (Content same as before) ...
    st.write("Terms and Privacy Policy content...")
    if st.button("← Return to Home", type="primary"):
        st.session_state.app_mode = "splash"
        st.rerun()

# --- PAGE: SPLASH ---
def render_splash_page():
    # ... (Logo & Marketing Content same as before) ...
    if os.path.exists("logo.png"):
        c1, c2, c3 = st.columns([3, 2, 3]) 
        with c2: st.image("logo.png", use_container_width=True)
    
    st.markdown("""<div style="text-align: center;"><h3>Turn your voice into a real letter.</h3></div>""", unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        if st.button("🔐 Log In / Sign Up to Start", type="primary", use_container_width=True):
            st.session_state.app_mode = "login"
            st.rerun()

    st.divider()
    # Features...
    st.subheader("Pricing")
    p1, p2, p3, p4 = st.columns(4)
    with p1: st.container(border=True).metric("⚡ Standard", "$2.99", "Machine Postage")
    with p2: st.container(border=True).metric("🏺 Heirloom", "$5.99", "Real Stamp")
    with p3: st.container(border=True).metric("🏛️ Civic", "$6.99", "3 Letters")
    with p4: st.container(border=True).metric("🎅 Santa", "$9.99", "North Pole")

    st.markdown("---")
    if st.button("Legal / Terms", type="secondary"):
        st.session_state.app_mode = "legal"
        st.rerun()

# --- PAGE: LOGIN ---
def render_login_page():
    st.markdown("<h2 style='text-align: center;'>Welcome Back</h2>", unsafe_allow_html=True)
    # ... (Login Logic same as before) ...
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        with st.container(border=True):
            tab_login, tab_signup = st.tabs(["Log In", "Sign Up"])
            with tab_login:
                l_email = st.text_input("Email", key="l_email")
                l_pass = st.text_input("Password", type="password", key="l_pass")
                if st.button("Log In", type="primary", use_container_width=True):
                     # ... auth logic ...
                     st.session_state.app_mode="store"; st.rerun()

            with tab_signup:
                # ... signup logic ...
                pass
            
            st.divider()
            if st.button("Forgot Password?", type="secondary"):
                st.session_state.app_mode = "forgot_password"
                st.rerun()

    if st.button("← Back"): st.session_state.app_mode = "splash"; st.rerun()

# --- PAGE: STORE ---
def render_store_page():
    # FIX 1: Hardcoded Title so it always appears
    render_hero("Select Service", "Choose your letter type")
    
    if st.session_state.get("user"):
        u_email = st.session_state.get("user_email", "")
        admin_target = st.secrets.get("admin", {}).get("email", "").strip().lower()
        if str(u_email).strip().lower() == admin_target:
             if st.button("🔐 Open Admin Console", type="secondary"):
                 import ui_admin
                 ui_admin.show_admin()
                 return

    c1, c2 = st.columns([2, 1])
    with c1:
        with st.container(border=True):
            st.subheader("Options")
            tier_display = {"Standard": "⚡ Standard ($2.99)", "Heirloom": "🏺 Heirloom ($5.99)", "Civic": "🏛️ Civic ($6.99)", "Santa": "🎅 Santa ($9.99)"}
            selected_option = st.radio("Select Tier", list(tier_display.keys()), format_func=lambda x: tier_display[x])
            
            # Helper to get short code
            if "Standard" in selected_option: tier_code="Standard"; st.info("Premium paper, #10 window envelope.")
            elif "Heirloom" in selected_option: tier_code="Heirloom"; st.info("Hand-addressed, real stamp.")
            elif "Civic" in selected_option: tier_code="Civic"; st.info("3 letters sent to reps.")
            elif "Santa" in selected_option: tier_code="Santa"; st.success("North Pole address.")
            else: tier_code="Standard"
            
            prices = {"Standard": 2.99, "Heirloom": 5.99, "Civic": 6.99, "Santa": 9.99}
            price = prices[tier_code]

    with c2:
        with st.container(border=True):
            st.subheader("Checkout")
            st.metric("Total", f"${price}")
            
            # ... (Promo Logic) ...
            
            if st.button(f"Pay ${price} & Start", type="primary"):
                u_email = st.session_state.get("user_email", "guest")
                if database: database.save_draft(u_email, "", tier_code, price)
                
                link = f"{YOUR_APP_URL}?tier={tier_code}&lang=English&session_id={{CHECKOUT_SESSION_ID}}"
                url, sess_id = payment_engine.create_checkout_session(tier_code, int(price*100), link, YOUR_APP_URL)
                if url: 
                    st.markdown(f"""<a href="{url}" target="_blank" class="pay-btn"><div><span style="color:white !important;">👉 Pay Now</span></div></a>""", unsafe_allow_html=True)

# --- PAGE: WORKSPACE ---
def render_workspace_page():
    tier = st.session_state.get("locked_tier", "Standard")
    # FIX 1: Ensure Title Renders
    render_hero("Compose Letter", f"{tier} Edition")
    
    u_email = st.session_state.get("user_email")
    # Load defaults...
    def_name=def_street=def_city=def_state=def_zip=""
    if database and u_email:
        profile = database.get_user_profile(u_email)
        if profile:
            def_name = profile.full_name or ""
            def_street = profile.address_line1 or ""
            # ...

    d = st.session_state.draft if "draft" in st.session_state else {}

    with st.container(border=True):
        st.subheader("📍 Addressing")
        
        # Santa Logic
        if tier == "Santa":
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
        
        # Civic Logic
        elif tier == "Civic":
            st.info("Civic Mode: We auto-find your reps.")
            c1, c2 = st.columns([1, 1])
            with c1:
                from_name = st.text_input("Name", value=def_name, key="w_from_name")
                from_street = st.text_input("Street", value=def_street, key="w_from_street")
                # ... (Rest of address inputs) ...
                # Dummy TO
                to_name="Civic"; to_street="Civic"; to_city="Civic"; to_state="TN"; to_zip="00000"

        # Standard / Heirloom Logic
        else:
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**To**")
                to_name = st.text_input("Name", key="w_to_name")
                to_street = st.text_input("Street", key="w_to_street")
                # ... (City/State/Zip inputs) ...
                c_x, c_y, c_z = st.columns(3)
                to_city = c_x.text_input("City", key="w_to_city")
                to_state = c_y.text_input("State", key="w_to_state")
                to_zip = c_z.text_input("Zip", key="w_to_zip")

            with c2:
                st.markdown("**From**")
                from_name = st.text_input("Name", value=def_name, key="w_from_name")
                # ... (Rest of inputs) ...
                from_street = st.text_input("Street", value=def_street, key="w_from_street")
                c_a, c_b, c_c = st.columns(3)
                from_city = c_a.text_input("City", value=def_city, key="w_from_city")
                from_state = c_b.text_input("State", value=def_state, key="w_from_state")
                from_zip = c_c.text_input("Zip", value=def_zip, key="w_from_zip")

        if st.button("Save Addresses"):
             # ... (Save logic) ...
             if tier == "Santa":
                 st.session_state.to_addr = {"name": to_name, "street": to_street, "city": to_city, "state": to_state, "zip": to_zip}
                 st.session_state.from_addr = {"name": "Santa Claus", "street": "123 Elf Road", "city": "North Pole", "state": "NP", "zip": "88888"}
             elif tier == "Civic":
                 st.session_state.from_addr = {"name": from_name, "street": from_street, "city": from_city, "state": from_state, "zip": from_zip}
                 # Call Civic Engine...
             else:
                 # Standard / Heirloom Save
                 st.session_state.to_addr = {"name": to_name, "street": to_street, "city": to_city, "state": to_state, "zip": to_zip}
                 st.session_state.from_addr = {"name": from_name, "street": from_street, "city": from_city, "state": from_state, "zip": from_zip}
             st.toast("Addresses Saved!")

    st.write("---")
    
    # FIX 2: Strict Validation before Recording
    is_ready = False
    if tier == "Civic" and st.session_state.get("from_addr"): is_ready = True
    elif st.session_state.get("to_addr") and st.session_state.get("to_addr").get("name"): is_ready = True
    
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
                # ... transcribe ...
                st.session_state.app_mode = "review"
                st.rerun()

def render_review_page():
    # FIX 1: Title
    render_hero("Review Letter", "Finalize and Send")
    txt = st.text_area("Body", st.session_state.get("transcribed_text", ""), height=300)
    
    if st.button("🚀 Send Letter", type="primary"):
        tier = st.session_state.get("locked_tier", "Standard")
        # ... Send Logic ...
        
        st.success("Letter Sent!")
        if st.button("Finish"): 
            reset_app()
            st.rerun()

# --- MAIN CONTROLLER ---
def show_main_app():
    if 'analytics' in globals(): analytics.inject_ga()
    
    # Routing logic...
    mode = st.session_state.get("app_mode", "splash")
    
    # Stripe Return Check
    if "session_id" in st.query_params:
        st.session_state.app_mode = "workspace"
        st.session_state.payment_complete = True
        if "tier" in st.query_params: st.session_state.locked_tier = st.query_params["tier"]
        st.query_params.clear()
        st.rerun()

    # Render Pages
    if mode == "splash": render_splash_page()
    elif mode == "login": render_login_page()
    elif mode == "store": render_store_page()
    elif mode == "workspace": render_workspace_page()
    elif mode == "review": render_review_page()
    elif mode == "legal": render_legal_page()
    
    # Sidebar
    with st.sidebar:
        if st.button("Home"): reset_app(); st.rerun()
        # ... User info ...