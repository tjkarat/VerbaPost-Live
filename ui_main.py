import streamlit as st
from streamlit_drawable_canvas import st_canvas
import os
# --- IMPORTS ---
try: import database; import ai_engine; import payment_engine; import promo_engine; import letter_format; import mailer
except: pass
import auth_ui 

YOUR_APP_URL = "https://verbapost.streamlit.app/" 

def reset_app():
    st.session_state.app_mode = "splash" 
    st.query_params.clear()

# --- SPLASH ---
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
    # ... Features & Pricing (Omitted for brevity but assumed present) ...
    st.write("Pricing: Standard $2.99 | Heirloom $5.99 | Civic $6.99 | Santa $9.99")

# --- MAIN ROUTER ---
def show_main_app():
    # 1. Routing
    mode = st.session_state.get("app_mode", "splash")
    
    if mode == "splash": render_splash_page()
    elif mode in ["login", "forgot_password", "verify_reset"]: auth_ui.route_auth_page(mode)
    elif mode == "store": 
        st.title("Store") # Placeholder
        # Call render_store_page() here if defined
    elif mode == "workspace": 
        st.title("Workspace") # Placeholder
        # Call render_workspace_page() here
    else:
        st.warning(f"Unknown Mode: {mode}")
        if st.button("Reset"): reset_app(); st.rerun()

    # Sidebar
    with st.sidebar:
        if st.button("Home"): reset_app(); st.rerun()