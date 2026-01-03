import streamlit as st
import time
import json
import logging

# --- LOGGING ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SPLASH")

# --- ASSETS ---
LOGO_STRIPE = "https://cdn.simpleicons.org/stripe/635BFF"
LOGO_TWILIO = "https://cdn.simpleicons.org/twilio/F22F46"
LOGO_OPENAI = "https://cdn.simpleicons.org/openai/000000"
LOGO_SUPABASE = "https://cdn.simpleicons.org/supabase/3ECF8E"
LOGO_USPS = "https://upload.wikimedia.org/wikipedia/commons/thumb/6/69/United_States_Postal_Service_Logo.svg/320px-United_States_Postal_Service_Logo.svg.png"

def render_splash_page():
    # --- CSS ---
    st.markdown("""
    <style>
    .block-container { padding-top: 2rem !important; padding-bottom: 3rem; max-width: 900px; }
    .hero-container { background-color: #ffffff; width: 100%; padding: 4rem 1rem; text-align: center; border-bottom: 1px solid #eaeaea; margin-bottom: 2rem; }
    .hero-title { font-family: 'Merriweather', serif; font-weight: 700; color: #111; font-size: clamp(2.5rem, 6vw, 4.5rem); margin-bottom: 0.5rem; letter-spacing: -1px; line-height: 1.1; }
    .hero-subtitle { font-family: 'Helvetica Neue', sans-serif; font-size: clamp(1rem, 3vw, 1.4rem); font-weight: 300; color: #555; margin-bottom: 2rem; margin-top: 1rem; max-width: 700px; margin-left: auto; margin-right: auto; line-height: 1.5; }
    .trust-container { text-align: center; padding: 20px 0; margin-top: 40px; display: flex; flex-wrap: wrap; justify-content: center; align-items: center; gap: 30px; opacity: 0.8; }
    .trust-logo { height: 24px; width: auto; object-fit: contain; filter: grayscale(100%); transition: filter 0.3s; }
    .trust-logo:hover { filter: grayscale(0%); }
    .logo-usps { height: 35px; filter: grayscale(0%); } 
    .secondary-link { text-align: center; margin-top: 50px; padding-top: 20px; border-top: 1px dashed #ddd; }
    .secondary-text { font-size: 0.9rem; color: #888; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

    # --- HERO SECTION ---
    st.markdown("""
    <div class="hero-container">
        <div class="hero-title">The Family Archive</div>
        <div class="hero-subtitle">
            Don't let their stories fade.<br>
            We interview your parents over the phone, transcribe their memories, and mail you physical keepsake letters.
        </div>
    </div>
    """, unsafe_allow_html=True)

    # --- PRIMARY CTA ---
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        if st.button("📚 Start Your Family Archive", type="primary", use_container_width=True):
            if st.session_state.get("authenticated"):
                st.session_state.app_mode = "heirloom"
            else:
                st.session_state.app_mode = "login"
                st.session_state.redirect_to = "heirloom"
            st.rerun()

    # --- TRUST BADGES ---
    st.markdown(f"""
    <div style="text-align: center; margin-top: 50px; margin-bottom: 15px;">
        <small style="font-size: 0.75rem; letter-spacing: 1.5px; text-transform: uppercase; color: #999; font-weight: 600;">Secure Infrastructure</small>
    </div>
    <div class="trust-container">
        <img class="trust-logo" src="{LOGO_STRIPE}" title="Stripe">
        <img class="trust-logo" src="{LOGO_TWILIO}" title="Twilio">
        <img class="trust-logo" src="{LOGO_OPENAI}" title="OpenAI">
        <img class="trust-logo" src="{LOGO_SUPABASE}" title="Supabase">
        <img class="trust-logo logo-usps" src="{LOGO_USPS}" title="USPS">
    </div>
    """, unsafe_allow_html=True)

    # --- SECONDARY OPTION ---
    st.markdown("<div class='secondary-link'><div class='secondary-text'>Looking to send a single letter?</div></div>", unsafe_allow_html=True)
    
    col_sec1, col_sec2, col_sec3 = st.columns([1, 1, 1])
    with col_sec2:
        if st.button("📮 Go to Letter Store", use_container_width=True):
            st.query_params["mode"] = "utility"
            if st.session_state.get("authenticated"):
                st.session_state.app_mode = "main" 
            else:
                st.session_state.app_mode = "login"
                st.session_state.redirect_to = "main" 
            st.rerun()

    # --- FOOTER ---
    st.markdown("<br><br>", unsafe_allow_html=True)
    c_blog, c_legal = st.columns(2)
    with c_blog:
         if st.button("📰 Read our Blog", use_container_width=True, key="splash_foot_blog"):
             st.session_state.app_mode = "blog"; st.rerun()
    with c_legal:
         if st.button("⚖️ Legal / Terms", use_container_width=True, key="splash_foot_legal"):
            st.session_state.app_mode = "legal"; st.rerun()

    return ""