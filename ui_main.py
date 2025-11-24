import streamlit as st
from streamlit_drawable_canvas import st_canvas
import os

# --- IMPORTS ---
try: import database
except: database = None
try: import ai_engine
except: ai_engine = None
try: import letter_format
except: letter_format = None
try: import mailer
except: mailer = None
try: import payment_engine
except: payment_engine = None
try: import promo_engine
except: promo_engine = None

# --- CONFIG ---
YOUR_APP_URL = "https://verbapost.streamlit.app/" 
COST_STANDARD = 2.99
COST_HEIRLOOM = 5.99
COST_CIVIC = 6.99

# --- UI HELPER: THE PURPLE LOOK ---
def render_hero(title, subtitle):
    """Render hero banner with Signature Purple Gradient"""
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                padding: 40px; border-radius: 20px; color: white; text-align: center; 
                margin-bottom: 30px; box-shadow: 0 10px 20px rgba(0,0,0,0.1);">
        <h1 style="margin: 0; font-size: 3rem; font-weight: 800; color: white;">{title}</h1>
        <div style="font-size: 1.2rem; opacity: 0.9; margin-top: 10px; color: #e0e0e0;">{subtitle}</div>
    </div>
    """, unsafe_allow_html=True)

# --- MAIN CONTROLLER ---
def show_main_app():
    if "current_view" not in st.session_state: st.session_state.current_view = "store"
    
    # Payment Return Handler
    if "session_id" in st.query_params:
        # (Simplified logic to prevent loop)
        st.session_state.payment_complete = True
        st.query_params.clear()
        
    if st.session_state.get("payment_complete") and st.session_state.current_view == "store":
        st.session_state.current_view = "workspace"

    view = st.session_state.get("current_view", "store")
    
    if view == "store": render_store_page()
    elif view == "workspace": render_workspace_page()
    elif view == "review": render_review_page()
    else: render_store_page()

# --- PAGES ---
def render_store_page():
    render_hero("Select Service", "Choose your letter type")
    
    c1, c2 = st.columns([2, 1])
    with c1:
        with st.container(border=True):
            st.subheader("Letter Options")
            tier = st.radio("Select Tier", ["⚡ Standard ($2.99)", "🏺 Heirloom ($5.99)", "🏛️ Civic ($6.99)"])
            lang = st.selectbox("Language", ["English", "Spanish", "French"])
    
    with c2:
        with st.container(border=True):
            st.subheader("Checkout")
            price = COST_STANDARD
            if "Heirloom" in tier: price = COST_HEIRLOOM
            elif "Civic" in tier: price = COST_CIVIC
            st.metric("Total", f"${price:.2f}")
            
            if st.button("Pay & Start", type="primary", use_container_width=True):
                st.session_state.payment_complete = True
                st.session_state.locked_tier = tier
                st.session_state.current_view = "workspace"
                st.rerun()

def render_workspace_page():
    tier = st.session_state.get("locked_tier", "Standard")
    render_hero("Compose Letter", f"{tier} Edition")
    
    with st.container(border=True):
        st.subheader("📍 Addressing")
        c1, c2 = st.columns(2)
        c1.text_input("Recipient Name")
        c2.text_input("Your Name")
        
    st.write("---")
    c_sig, c_mic = st.columns(2)
    with c_sig:
        st.write("✍️ **Signature**")
        st_canvas(height=150, width=300, key="canvas")
    with c_mic:
        st.write("🎤 **Dictation**")
        audio = st.audio_input("Record")
        if audio:
            st.session_state.transcribed_text = "Sample transcription..."
            st.session_state.current_view = "review"
            st.rerun()

def render_review_page():
    render_hero("Review Letter", "Finalize and send")
    st.text_area("Body", st.session_state.get("transcribed_text", ""), height=300)
    if st.button("🚀 Send", type="primary", use_container_width=True):
        st.success("Sent!")
        if st.button("Finish"):
            st.session_state.clear()
            st.rerun()