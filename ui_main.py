import streamlit as st
from streamlit_drawable_canvas import st_canvas
import os
import tempfile
from PIL import Image

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

YOUR_APP_URL = "https://verbapost.streamlit.app/" 

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

def show_main_app():
    if "draft" not in st.session_state: st.session_state.draft = {}

    if "session_id" in st.query_params:
        st.session_state.payment_complete = True
        if "tier" in st.query_params: st.session_state.locked_tier = st.query_params["tier"]
        st.session_state.app_mode = "workspace"
        st.query_params.clear(); st.rerun()

    if not st.session_state.get("payment_complete"): render_store_page()
    else:
        if st.session_state.get("app_mode") == "review": render_review_page()
        else: render_workspace_page()

def render_store_page():
    render_hero("Select Service", "Choose your letter type")
    c1, c2 = st.columns([2, 1])
    with c1:
        with st.container(border=True):
            st.subheader("Letter Options")
            tier_options = {"⚡ Standard": 2.99, "🏺 Heirloom": 5.99, "🏛️ Civic": 6.99}
            selected_tier_name = st.radio("Select Tier", list(tier_options.keys()))
            lang = st.selectbox("Language", ["English", "Spanish", "French"])
            price = tier_options[selected_tier_name]
            tier_code = selected_tier_name.split(" ")[1] 
            st.session_state.temp_tier = tier_code
            st.session_state.temp_price = price
    with c2:
        with st.container(border=True):
            st.subheader("Checkout")
            promo_code = st.text_input("Promo Code (Optional)")
            is_free = False
            if promo_code and promo_engine:
                if promo_engine.validate_code(promo_code):
                    is_free = True; st.success("✅ Code Applied!"); price = 0.00
                else: st.error("Invalid Code")
            st.metric("Total", f"${price:.2f}")
            st.divider()
            if is_free:
                if st.button("🚀 Start (Promo Applied)", type="primary", use_container_width=True):
                    st.session_state.payment_complete = True; st.session_state.locked_tier = tier_code
                    st.session_state.app_mode = "workspace"; st.rerun()
            else:
                if payment_engine:
                    st.info("⚠️ **Note:** Payment opens in a new tab. Return here after.")
                    if st.button("Proceed to Payment", type="primary", use_container_width=True):
                        with st.spinner("Connecting to Stripe..."):
                            url, sess_id = payment_engine.create_checkout_session(f"VerbaPost {tier_code}", int(price * 100), f"{YOUR_APP_URL}?session_id={{CHECKOUT_SESSION_ID}}&tier={tier_code}", YOUR_APP_URL)
                            st.session_state.stripe_url = url
                            st.rerun()
                    
                    if st.session_state.get("stripe_url"):
                        url = st.session_state.stripe_url
                        
                        # Debug: Show raw URL in case button fails
                        st.caption(f"Debug Link: {url}")
                        
                        # FIX: Force White Text on Link
                        st.markdown(f"""
                        <a href="{url}" target="_blank" style="text-decoration: none !important; color: white !important;">
                            <div style="
                                display: block; width: 100%; padding: 12px;
                                background-color: #2a5298; color: white !important;
                                text-align: center; border-radius: 8px;
                                font-weight: bold; margin-top: 10px;
                                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                            ">
                                👉 Pay Now (Secure)
                            </div>
                        </a>
                        """, unsafe_allow_html=True)
                else:
                    st.warning("No Payment Engine")

def render_workspace_page():
    # (Rest of workspace logic remains same - omitted for brevity)
    tier = st.session_state.get("locked_tier", "Standard")
    render_hero("Compose Letter", f"{tier} Edition")
    # ... rest of workspace code ...
    st.write("Workspace logic...") # Placeholder for now to keep paste short

def render_review_page():
    # ... rest of review code ...
    st.write("Review logic...")