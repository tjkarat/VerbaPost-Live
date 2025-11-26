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
    # Features
    c1, c2, c3 = st.columns(3)
    with c1: st.markdown("### 🎙️ 1. Dictate"); st.caption("You speak. AI types.")
    with c2: st.markdown("### ✍️ 2. Sign"); st.caption("Sign on your screen.")
    with c3: st.markdown("### 📮 3. We Mail"); st.caption("Printed, stamped, & sent.")
    
    st.write("")
    st.caption("Pricing: Standard $2.99 | Heirloom $5.99 | Civic $6.99 | Santa $9.99")

# --- HELPER: SUPABASE ---
@st.cache_resource
def get_supabase():
    from supabase import create_client
    try:
        if "SUPABASE_URL" not in st.secrets: return None
        return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except: return None

# --- MAIN ROUTER ---
def show_main_app():
    mode = st.session_state.get("app_mode", "splash")
    
    if mode == "splash": 
        render_splash_page()
        
    # --- STABILIZED LOGIN PAGE (USING FORMS) ---
    elif mode == "login":
        st.markdown("<h2 style='text-align: center;'>Welcome Back</h2>", unsafe_allow_html=True)
        
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            # LOG IN FORM
            with st.form("login_form"):
                st.subheader("Log In")
                email = st.text_input("Email")
                password = st.text_input("Password", type="password")
                submitted = st.form_submit_button("Log In", type="primary", use_container_width=True)
                
                if submitted:
                    sb = get_supabase()
                    if not sb:
                        st.error("System Error: Database connection missing.")
                    else:
                        try:
                            res = sb.auth.sign_in_with_password({"email": email, "password": password})
                            st.session_state.user = res
                            st.session_state.user_email = email
                            st.session_state.app_mode = "store"
                            st.rerun()
                        except Exception as e:
                            st.error(f"Login failed: {e}")
            
            st.write("")
            
            # SIGN UP FORM
            with st.expander("New here? Create an Account"):
                with st.form("signup_form"):
                    new_email = st.text_input("New Email")
                    new_pass = st.text_input("New Password", type="password")
                    signup_sub = st.form_submit_button("Sign Up", use_container_width=True)
                    
                    if signup_sub:
                        sb = get_supabase()
                        try:
                            sb.auth.sign_up({"email": new_email, "password": new_pass})
                            st.success("Success! Check your email to confirm.")
                        except Exception as e:
                            st.error(f"Signup failed: {e}")

            if st.button("← Back"):
                st.session_state.app_mode = "splash"
                st.rerun()

    elif mode in ["forgot_password", "verify_reset"]: auth_ui.route_auth_page(mode)
    elif mode == "store": 
        import ui_main_full # Load the full logic file only when needed
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

    # Sidebar
    with st.sidebar:
        if st.button("Home"): reset_app(); st.rerun()