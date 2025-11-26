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
    <div style="background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); padding: 40px; border-radius: 15px; text-align: center; margin-bottom: 30px; box-shadow: 0 8px 16px rgba(0,0,0,0.1);">
        <h1 style="margin: 0; font-size: 3rem; font-weight: 700; color: white !important;">{title}</h1>
        <div style="font-size: 1.2rem; opacity: 0.9; margin-top: 10px; color: white !important;">{subtitle}</div>
    </div>
    """, unsafe_allow_html=True)

# --- SPLASH PAGE (Moved Here) ---
def render_splash_page():
    if os.path.exists("logo.png"):
        c1, c2, c3 = st.columns([3, 2, 3]) 
        with c2: st.image("logo.png", use_container_width=True)
    
    st.markdown("""
    <div style="text-align: center; margin-bottom: 30px;">
        <h3 style="font-weight: 600; margin-top: 0; color: #2d3748;">Turn your voice into a real letter.</h3>
        <p style="font-size: 1.2rem; color: #555; margin-top: 15px; line-height: 1.6;">
            Texts are trivial. Emails are ignored.<br><b style="color: #2d3748;">REAL LETTERS GET OPENED AND READ.</b>
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        if st.button("🔐 Log In / Sign Up to Start", type="primary", use_container_width=True):
            st.session_state.app_mode = "login"
            st.rerun()

    st.divider()
    c1, c2, c3 = st.columns(3)
    with c1: st.markdown("### 🎙️ 1. Dictate"); st.caption("You speak. AI types.")
    with c2: st.markdown("### ✍️ 2. Sign"); st.caption("Sign on your screen.")
    with c3: st.markdown("### 📮 3. We Mail"); st.caption("Printed, stamped, & sent.")
    
    st.divider()
    st.subheader("Pricing")
    p1, p2, p3, p4 = st.columns(4)
    with p1: st.container(border=True).metric("⚡ Standard", "$2.99", "Machine Postage")
    with p2: st.container(border=True).metric("🏺 Heirloom", "$5.99", "Real Stamp")
    with p3: st.container(border=True).metric("🏛️ Civic", "$6.99", "3 Letters to Congress")
    with p4: st.container(border=True).metric("🎅 Santa", "$9.99", "North Pole Address")
    
    st.markdown("---")
    f1, f2 = st.columns([4, 1])
    with f2:
        if st.button("Legal / Terms", type="secondary"):
            st.session_state.app_mode = "legal"
            st.rerun()

# --- LEGAL PAGE ---
def render_legal_page():
    render_hero("Legal Center", "Transparency & Trust")
    tab_tos, tab_privacy = st.tabs(["📜 Terms of Service", "🔒 Privacy Policy"])
    with tab_tos:
        st.write("You agree NOT to use VerbaPost to send threatening, abusive, or illegal content via US Mail.")
    with tab_privacy:
        st.write("We process your voice data solely for transcription. We do not sell your personal information.")
    if st.button("← Return to Home", type="primary"):
        st.session_state.app_mode = "splash"
        st.rerun()

# --- MAIN APP CONTROLLER ---
def show_main_app():
    # 1. Initialize Session
    if "app_mode" not in st.session_state: st.session_state.app_mode = "splash"
    if "processed_ids" not in st.session_state: st.session_state.processed_ids = []

    # 2. Stripe Return Logic (Must be first)
    qp = st.query_params
    if "session_id" in qp:
        session_id = qp["session_id"]
        if session_id not in st.session_state.processed_ids:
            if payment_engine and payment_engine.check_payment_status(session_id):
                st.session_state.payment_complete = True
                st.session_state.processed_ids.append(session_id)
                st.toast("✅ Payment Confirmed!")
                if "tier" in qp: st.session_state.locked_tier = qp["tier"]
                st.session_state.app_mode = "workspace"
            else:
                st.error("Payment verification failed.")
        else:
            if st.session_state.get("payment_complete"): st.session_state.app_mode = "workspace"
        st.query_params.clear()

    # 3. Render Sidebar (Available on ALL pages)
    with st.sidebar:
        if st.button("Home / Reset"): reset_app(); st.rerun()
        
        # User / Admin Section
        if st.session_state.get("user"):
            u_email = "Unknown"
            u = st.session_state.user
            if isinstance(u, dict): u_email = u.get("email", "")
            elif hasattr(u, "email"): u_email = u.email
            elif hasattr(u, "user"): u_email = u.user.email
            
            st.divider()
            st.caption(f"Logged in: {u_email}")
            
            # Admin Check
            admin_target = st.secrets.get("admin", {}).get("email", "").strip().lower()
            user_clean = u_email.strip().lower()
            
            if user_clean and admin_target and user_clean == admin_target:
                st.success("Admin Access")
                import ui_admin
                if st.button("Open Admin Console"):
                    ui_admin.show_admin()
            
            if st.button("Sign Out"): st.session_state.pop("user", None); reset_app(); st.rerun()
        else:
            st.divider()
            if st.button("🔐 Sidebar Login"): st.session_state.app_mode = "login"; st.rerun()

    # 4. Routing Switchboard
    mode = st.session_state.app_mode

    if mode == "splash": render_splash_page()
    elif mode == "legal": render_legal_page()
    
    elif mode == "login":
        st.markdown("<h1 style='text-align: center;'>Welcome Back</h1>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            with st.container(border=True):
                email = st.text_input("Email Address")
                password = st.text_input("Password", type="password")
                if st.button("Log In", type="primary", use_container_width=True):
                    sb = get_supabase()
                    if sb:
                        try:
                            res = sb.auth.sign_in_with_password({"email": email, "password": password})
                            st.session_state.user = res
                            st.session_state.app_mode = "store" # Direct to store
                            st.rerun()
                        except Exception as e: st.error(f"Login failed: {e}")
                if st.button("Sign Up", use_container_width=True):
                    sb = get_supabase()
                    if sb:
                        try:
                            sb.auth.sign_up({"email": email, "password": password})
                            st.success("Check email.")
                        except Exception as e: st.error(f"Signup failed: {e}")
                if st.button("Forgot Password?", type="secondary"):
                     st.info("Password reset feature disabled in this view.")
        if st.button("← Back"): st.session_state.app_mode = "splash"; st.rerun()

    elif mode == "store":
        render_store_page() # (Uses existing function from previous step)

    elif mode == "workspace":
        render_workspace_page() # (Uses existing function)

    elif mode == "review":
        render_review_page() # (Uses existing function)

# --- 5. THE STORE ---
    if st.session_state.app_mode == "store":
        render_hero("Select Service", "Choose your letter type.")
        c1, c2 = st.columns([2, 1])
        with c1:
            with st.container(border=True):
                st.subheader("Options")
                tier = st.radio("Tier", ["⚡ Standard ($2.99)", "🏺 Heirloom ($5.99)", "🏛️ Civic ($6.99)", "🎅 Santa ($9.99)"])
                lang = st.selectbox("Language", ["English", "Spanish", "French"])
        with c2:
            with st.container(border=True):
                st.subheader("Checkout")
                
                # Logic for pricing
                if "Standard" in tier: price = 2.99
                elif "Heirloom" in tier: price = 5.99
                elif "Civic" in tier: price = 6.99
                elif "Santa" in tier: price = 9.99
                
                st.metric("Total", f"${price}")
                
                promo_code = st.text_input("Promo Code (Optional)")
                is_free = False
                if promo_code and promo_engine.validate_code(promo_code):
                     is_free = True
                     st.success("Code Applied!")

                if is_free:
                     if st.button("Start (Free)", type="primary"):
                         st.session_state.payment_complete = True
                         st.session_state.app_mode = "workspace"
                         st.session_state.locked_tier = tier.split()[1] if "Santa" not in tier else "Santa"
                         st.session_state.selected_language = lang
                         st.rerun()
                else:
                    st.info("⚠️ **Note:** Payment opens in a new tab.")
                    if st.button(f"Pay ${price} & Start", type="primary"):
                        user = st.session_state.get("user_email", "guest")
                        database.save_draft(user, "", tier, price)
                        
                        if "Santa" in tier: safe_tier = "Santa"
                        else: safe_tier = tier.split()[1]
                        
                        link = f"{YOUR_APP_URL}?tier={safe_tier}&lang={lang}"
                        url, sess_id = payment_engine.create_checkout_session(tier, int(price*100), link, YOUR_APP_URL)
                        if url: st.link_button("Click here to Pay", url, type="primary")
                        else: st.error("Payment System Offline")

    # --- 6. WORKSPACE ---
    elif st.session_state.app_mode == "workspace":
        tier = st.session_state.get("locked_tier", "Standard")
        render_hero("Compose", f"{tier} Edition")
        
        # ... (Copy full Workspace logic from previous steps) ...
        # Placeholder to ensure file compiles - restore full logic here
        st.info("Dictation Workspace Active")
        st.button("Skip to Review (Debug)", on_click=lambda: st.session_state.update(app_mode="review"))

    # --- 7. REVIEW ---
    elif st.session_state.app_mode == "review":
        render_hero("Review", "Finalize Letter")
        # ... (Review Logic) ...
        st.button("Finish", on_click=reset_app)
