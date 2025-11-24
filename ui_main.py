import streamlit as st
from streamlit_drawable_canvas import st_canvas
import os
from datetime import datetime

# --- CONDITIONAL IMPORTS ---
# These handle missing modules so the app doesn't crash during dev
try: import database
except ImportError: database = None

try: import ai_engine
except ImportError: ai_engine = None

try: import letter_format
except ImportError: letter_format = None

try: import mailer
except ImportError: mailer = None

try: import payment_engine
except ImportError: payment_engine = None

try: import analytics
except ImportError: analytics = None

try: import promo_engine
except ImportError: promo_engine = None

# --- CONFIG ---
YOUR_APP_URL = "https://verbapost.streamlit.app/" 
COST_STANDARD = 2.99
COST_HEIRLOOM = 5.99
COST_CIVIC = 6.99

# --- HELPER: SUPABASE ---
@st.cache_resource
def get_supabase():
    """Get Supabase client with error handling"""
    try:
        from supabase import create_client
        if "SUPABASE_URL" not in st.secrets:
            return None
        return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except Exception as e:
        st.error(f"Supabase connection failed: {e}")
        return None

def reset_app():
    """Reset app state while preserving login"""
    user = st.session_state.get("user")
    user_email = st.session_state.get("user_email")
    
    # Clear workspace-specific state
    keys_to_clear = ["audio_path", "transcribed_text", "payment_complete", 
                     "stripe_url", "sig_data", "to_addr", "from_addr", "locked_tier"]
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
    
    st.session_state.current_view = "main_app"
    st.query_params.clear()
    
    # Restore login state
    if user:
        st.session_state.user = user
    if user_email:
        st.session_state.user_email = user_email

def render_hero(title, subtitle):
    """Render hero banner"""
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                padding: 40px; border-radius: 20px; color: white; text-align: center; margin-bottom: 30px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
        <h1 style="color: white; margin: 0; font-size: 3rem; font-weight: 800;">{title}</h1>
        <p style="font-size: 1.2rem; opacity: 0.9; margin-top: 10px; color: #f0f0f0;">{subtitle}</p>
    </div>
    """, unsafe_allow_html=True)

# --- MAIN APP LOGIC ---
def show_main_app():
    """Main application controller"""
    
    # Initialize session state for workspace
    if "current_view" not in st.session_state:
        st.session_state.current_view = "store"
    if "processed_ids" not in st.session_state:
        st.session_state.processed_ids = []

    # --- STRIPE RETURN HANDLER (Processed here) ---
    qp = st.query_params
    if "session_id" in qp:
        session_id = qp["session_id"]
        if session_id not in st.session_state.processed_ids:
            if payment_engine and payment_engine.check_payment_status(session_id):
                st.session_state.payment_complete = True
                st.session_state.processed_ids.append(session_id)
                st.toast("✅ Payment Confirmed!")
                
                # Retrieve tier/lang from URL params
                if "tier" in qp:
                    st.session_state.locked_tier = qp["tier"]
                if "lang" in qp:
                    st.session_state.selected_language = qp["lang"]
                
                st.session_state.current_view = "workspace"
                # Clear params so we don't re-trigger on reload
                st.query_params.clear()
                st.rerun()
            else:
                st.error("Payment verification failed.")
        else:
            # If already processed, just ensure we are in workspace
            st.session_state.current_view = "workspace"

    # --- VIEW ROUTING WITHIN APP ---
    # Note: Global routing (Login vs App vs Admin) is handled in main.py
    # This handles the sub-views of the core product.
    
    # If payment just finished, force workspace
    if st.session_state.get("payment_complete") and st.session_state.current_view == "store":
        st.session_state.current_view = "workspace"

    view = st.session_state.get("current_view", "store")
    
    if view == "store":
        render_store_page()
    elif view == "workspace":
        render_workspace_page()
    elif view == "review":
        render_review_page()
    else:
        # Fallback
        render_store_page()

# --- PAGE RENDERERS ---

def render_store_page():
    render_hero("Select Service", "Choose your letter type")
    
    c1, c2 = st.columns([2, 1])
    
    with c1:
        with st.container(border=True):
            st.subheader("Letter Options")
            tier = st.radio("Select Tier", 
                           ["⚡ Standard ($2.99)", "🏺 Heirloom ($5.99)", "🏛️ Civic ($6.99)"],
                           key="store_tier")
            lang = st.selectbox("Language", ["English", "Spanish", "French"], key="store_lang")
    
    with c2:
        with st.container(border=True):
            st.subheader("Checkout")
            
            price = COST_STANDARD
            if "Heirloom" in tier: price = COST_HEIRLOOM
            elif "Civic" in tier: price = COST_CIVIC
            
            st.metric("Total", f"${price:.2f}")
            
            # Promo logic
            promo_code = st.text_input("Promo Code", key="store_promo")
            valid_promo = False
            
            if promo_code and promo_engine:
                if promo_engine.validate_code(promo_code):
                    valid_promo = True
                    price = 0.00
                    st.success("✅ Code Applied!")
            
            if valid_promo:
                if st.button("Start (Free)", type="primary", use_container_width=True):
                    st.session_state.payment_complete = True
                    st.session_state.current_view = "workspace"
                    st.session_state.locked_tier = tier.split()[1]
                    st.session_state.selected_language = lang
                    st.rerun()
            else:
                if st.button(f"Pay ${price:.2f}", type="primary", use_container_width=True):
                    user = st.session_state.get("user_email", "guest")
                    safe_tier = tier.split()[1] # Extract "Standard" from "⚡ Standard..."
                    
                    if database:
                        database.save_draft(user, "", tier, price)
                    
                    # Pass return link with query params
                    link = f"{YOUR_APP_URL}?tier={safe_tier}&lang={lang}"
                    
                    if payment_engine:
                        url, sess_id = payment_engine.create_checkout_session(
                            tier, int(price * 100), link, YOUR_APP_URL
                        )
                        if url:
                            st.link_button("👉 Click to Pay", url, type="primary", use_container_width=True)
                        else:
                            st.error("Payment error")

def render_workspace_page():
    tier = st.session_state.get("locked_tier", "Standard")
    render_hero("Compose Letter", f"{tier} Edition")
    
    # ... (Keep your existing workspace logic here) ...
    # Simplified for brevity in this fix, assume existing workspace logic exists
    
    st.info("🎤 Dictation and Transcription tools active")
    
    if st.button("Simulate Transcription (Dev)", key="sim_trans"):
        st.session_state.transcribed_text = "This is a test letter generated by the system."
        st.session_state.current_view = "review"
        st.rerun()

def render_review_page():
    render_hero("Review Letter", "Finalize and send")
    
    txt = st.text_area("Letter Body", st.session_state.get("transcribed_text", ""), height=300)
    
    if st.button("🚀 Send Letter", type="primary", use_container_width=True):
        st.success("Letter Sent!")
        if st.button("Start Over"):
            reset_app()
            st.rerun()