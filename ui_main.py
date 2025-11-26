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
import auth_ui 

YOUR_APP_URL = "https://verbapost.streamlit.app/" 

def reset_app():
    st.session_state.app_mode = "splash" 
    st.query_params.clear()

# --- HELPER: SUPABASE ---
@st.cache_resource
def get_supabase():
    from supabase import create_client
    try:
        if "SUPABASE_URL" not in st.secrets: return None
        return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except: return None

# --- PAGES ---

def render_splash_page():
    if os.path.exists("logo.png"):
        c1, c2, c3 = st.columns([3, 2, 3]) 
        with c2: st.image("logo.png", use_container_width=True)
    
    st.markdown("""
    <div style="text-align: center; margin-bottom: 30px;">
        <h3 style="color: #2d3748;">Turn your voice into a real letter.</h3>
        <p style="color: #555;">Texts are trivial. Emails are ignored.<br><b>REAL LETTERS GET OPENED.</b></p>
    </div>
    """, unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        if st.button("🔐 Log In / Sign Up", type="primary", use_container_width=True):
            st.session_state.app_mode = "login"
            st.rerun()

    st.divider()
    # Features
    c1, c2, c3 = st.columns(3)
    with c1: st.markdown("### 🎙️ 1. Dictate"); st.caption("You speak. AI types.")
    with c2: st.markdown("### ✍️ 2. Sign"); st.caption("Sign on your screen.")
    with c3: st.markdown("### 📮 3. We Mail"); st.caption("Printed, stamped, & sent.")
    
    st.write("")
    st.caption("Pricing: Standard $2.99 | Heirloom $5.99 | Civic $6.99 | Santa $9.99")

# --- MAIN ROUTER ---
def show_main_app():
    # 1. ALWAYS RENDER SIDEBAR FIRST
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
            user_clean = str(u_email).strip().lower()
            
            if user_clean == admin_target:
                st.success("Admin Access")
                import ui_admin
                if st.button("Open Console"): ui_admin.show_admin()
            
            if st.button("Sign Out"): st.session_state.pop("user", None); reset_app(); st.rerun()
        else:
            st.divider()
            if st.button("🔐 Sidebar Login"): st.session_state.app_mode = "login"; st.rerun()

    # 2. Handle Routing
    mode = st.session_state.get("app_mode", "splash")

    # Stripe Return Check
    if "session_id" in st.query_params:
        st.session_state.app_mode = "workspace"
        st.session_state.payment_complete = True
        st.query_params.clear()
        st.rerun()

    # 3. Render Views
    if mode == "splash": render_splash_page()
    elif mode in ["login", "forgot_password", "verify_reset"]: auth_ui.route_auth_page(mode)
    elif mode == "legal": 
         import ui_main_full # Using placeholder for brevity
         # render_legal() logic
         st.write("Legal Page")
         if st.button("Back"): st.session_state.app_mode="splash"; st.rerun()
    elif mode == "store": 
        import ui_main_full
        ui_main_full.render_store_page()
    elif mode == "workspace": 
        import ui_main_full
        ui_main_full.render_workspace_page()
    elif mode == "review": 
        import ui_main_full
        ui_main_full.render_review_page()
    else:
        st.warning(f"Unknown Mode: {mode}")
        if st.button("Reset"): reset_app(); st.rerun()