import streamlit as st

# --- FUNCTION DEFINITION ---
def render_splash_page():
    # --- PROFESSIONAL MINIMALIST CSS ---
    st.markdown("""
    <style>
    .block-container { padding-top: 2rem !important; padding-bottom: 3rem; max-width: 900px; }
    .hero-container { background-color: #ffffff; width: 100%; padding: 3rem 1rem 2rem 1rem; text-align: center; border-bottom: 1px solid #eaeaea; margin-bottom: 2rem; }
    .hero-title { font-family: 'Merriweather', serif; font-weight: 700; color: #111; font-size: clamp(2.5rem, 6vw, 4rem); margin-bottom: 0.5rem; letter-spacing: -0.5px; line-height: 1.2; }
    .hero-subtitle { font-family: 'Helvetica Neue', sans-serif; font-size: clamp(0.9rem, 3vw, 1.1rem); font-weight: 600; text-transform: uppercase; letter-spacing: 2px; color: #d93025; margin-bottom: 1.5rem; margin-top: 1rem; }
    .hero-text { font-family: 'Helvetica Neue', sans-serif; font-size: 1.15rem; font-weight: 300; color: #555; max-width: 600px; margin: 0 auto; line-height: 1.6; }
    .feature-icon { font-size: 2rem; margin-bottom: 0.5rem; opacity: 0.8; }
    .feature-head { font-weight: 600; color: #111; margin-bottom: 0.25rem; font-family: 'Merriweather', serif; }
    .feature-body { color: #666; font-size: 0.9rem; line-height: 1.5; }
    @media (max-width: 600px) { .hero-container { padding: 1rem 0.5rem; border-bottom: none; } }
    </style>
    """, unsafe_allow_html=True)

    # --- HERO CONTENT ---
    st.markdown("""
    <div class="hero-container">
        <div class="hero-title">VerbaPost</div>
        <div class="hero-subtitle">Real Mail Gets Read</div>
        <div class="hero-text">
            Texts are trivial. Emails are ignored.<br>
            <span style="font-style: italic;">"Don't know how to start? Speak it first, and we'll transcribe."</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # --- ACTION BUTTONS ---
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        if st.button("Start a Letter", type="primary", use_container_width=True):
            if st.session_state.get("authenticated"):
                st.session_state.app_mode = "store"
            else:
                st.session_state.app_mode = "login"
            st.rerun()

        st.write("") 

        if st.button("Legacy Service (End of Life)", use_container_width=True):
            st.session_state.app_mode = "legacy"
            st.rerun()

    st.markdown("<br><br>", unsafe_allow_html=True)

    # --- FEATURES ---
    c_a, c_b, c_c = st.columns(3)
    with c_a:
        st.markdown("""<div style="text-align: center;"><div class="feature-icon">🎙️</div><div class="feature-head">Speak</div><div class="feature-body">Dictate your letter. AI transcribes and formats it instantly.</div></div>""", unsafe_allow_html=True)
    with c_b:
        st.markdown("""<div style="text-align: center;"><div class="feature-icon">📄</div><div class="feature-head">Print</div><div class="feature-body">Printed on archival bond paper, folded, and enveloped.</div></div>""", unsafe_allow_html=True)
    with c_c:
        st.markdown("""<div style="text-align: center;"><div class="feature-icon">📬</div><div class="feature-head">Send</div><div class="feature-body">USPS First Class or Certified Mail. Full tracking included.</div></div>""", unsafe_allow_html=True)

    # --- FOOTER ---
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    col_foot1, col_foot2, col_foot3 = st.columns([1, 2, 1])
    with col_foot2:
        st.markdown("<div style='text-align: center; color: #ccc; font-size: 0.75rem; border-top: 1px solid #f0f0f0; padding-top: 20px;'>VerbaPost • Secure • Private • Real</div>", unsafe_allow_html=True)
        # Legal Button
        if st.button("⚖️ Legal / Terms", use_container_width=True):
            st.session_state.app_mode = "legal"
            st.rerun()

    # Explicit return avoids "None" printing in main.py
    return