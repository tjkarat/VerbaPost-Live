import streamlit as st
import time
import json
import logging

# --- LOGGING ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SPLASH")

def render_splash_page():
    # --- CSS ---
    st.markdown("""
    <style>
    .block-container { padding-top: 2rem !important; padding-bottom: 3rem; max-width: 900px; }
    .hero-container { background-color: #ffffff; width: 100%; padding: 4rem 1rem; text-align: center; border-bottom: 1px solid #eaeaea; margin-bottom: 2rem; }
    .badge { display: inline-block; background: #ecfdf5; color: #047857; font-size: 0.75rem; font-weight: 600; padding: 6px 12px; border-radius: 20px; border: 1px solid #d1fae5; margin-bottom: 15px; text-transform: uppercase; }
    .hero-title { font-family: 'Merriweather', serif; font-weight: 700; color: #0f172a; font-size: clamp(2.5rem, 6vw, 4.0rem); margin-bottom: 0.5rem; letter-spacing: -0.5px; line-height: 1.1; }
    .hero-subtitle { font-family: 'Helvetica Neue', sans-serif; font-size: clamp(1rem, 3vw, 1.3rem); font-weight: 300; color: #475569; margin-bottom: 2rem; margin-top: 1rem; max-width: 700px; margin-left: auto; margin-right: auto; line-height: 1.6; }
    .secondary-link { text-align: center; margin-top: 60px; padding-top: 20px; border-top: 1px dashed #ddd; }
    .secondary-text { font-size: 0.85rem; color: #94a3b8; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

    # --- HERO SECTION (B2B) ---
    st.markdown("""
    <div class="hero-container">
        <div class="badge">For Estate Planners & Attorneys</div>
        <div class="hero-title">Preserve the Legacy.<br>Keep the Heirs.</div>
        <div class="hero-subtitle">
            The ultimate client retention tool. We interview your clients, capture their life stories, and mail physical letters to their beneficiaries—branding <b>you</b> as the architect of their family legacy.
        </div>
    </div>
    """, unsafe_allow_html=True)

    # --- PRIMARY CTA (PARTNER PORTAL) ---
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        if st.button("💼 Partner Portal Access", type="primary", use_container_width=True):
            if st.session_state.get("authenticated"):
                st.session_state.app_mode = "partner"
            else:
                st.session_state.app_mode = "login"
                st.session_state.redirect_to = "partner"
            st.rerun()
            
        st.markdown("<div style='text-align: center; font-size: 0.8rem; color: #64748b; margin-top: 10px;'>FINRA Rule 3220 Compliant ($99 Limit)</div>", unsafe_allow_html=True)

    # --- SECONDARY OPTION (UTILITY STORE) ---
    st.markdown("<div class='secondary-link'><div class='secondary-text'>Looking for the standard store?</div></div>", unsafe_allow_html=True)
    
    col_sec1, col_sec2, col_sec3 = st.columns([1, 1, 1])
    with col_sec2:
        if st.button("✉️ Go to Letter Store", use_container_width=True):
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
         if st.button("📰 Advisor Blog", use_container_width=True, key="splash_foot_blog"):
             st.session_state.app_mode = "blog"; st.rerun()
    with c_legal:
         if st.button("⚖️ Terms & Privacy", use_container_width=True, key="splash_foot_legal"):
            st.session_state.app_mode = "legal"; st.rerun()

    return ""