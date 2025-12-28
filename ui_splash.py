import streamlit as st

def render_splash_page():
    """
    Renders the professional landing page for VerbaPost.
    Preserves all original minimalist CSS and hero sections.
    """
    # --- CSS ---
    st.markdown("""
    <style>
    .block-container { padding-top: 2rem !important; padding-bottom: 3rem; max-width: 900px; }
    .hero-container { background-color: #ffffff; width: 100%; padding: 4rem 1rem; text-align: center; border-bottom: 1px solid #eaeaea; margin-bottom: 2rem; }
    .hero-title { font-family: 'Merriweather', serif; font-weight: 700; color: #111; font-size: clamp(2.5rem, 6vw, 4.5rem); margin-bottom: 0.5rem; letter-spacing: -1px; line-height: 1.1; }
    .hero-subtitle { font-family: 'Helvetica Neue', sans-serif; font-size: clamp(1rem, 3vw, 1.4rem); font-weight: 300; color: #555; margin-bottom: 2rem; margin-top: 1rem; max-width: 700px; margin-left: auto; margin-right: auto; line-height: 1.5; }
    
    .trust-container { text-align: center; padding: 20px 0; opacity: 0.7; margin-top: 30px; display: flex; flex-wrap: wrap; justify-content: center; align-items: center; gap: 40px; }
    /* Greyscale filter for logos until hover */
    .trust-logo { height: 25px; filter: grayscale(100%); transition: filter 0.3s; opacity: 0.8; }
    .trust-logo:hover { filter: grayscale(0%); opacity: 1.0; }
    
    .secondary-link { text-align: center; margin-top: 40px; padding-top: 20px; border-top: 1px dashed #ddd; }
    .secondary-text { font-size: 0.9rem; color: #888; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

    # --- HERO SECTION (ARCHIVE FOCUSED) ---
    st.markdown("""
    <div class="hero-container">
        <div class="hero-title">The Family Archive</div>
        <div class="hero-subtitle">
            Don't let their stories fade.<br>
            We interview your parents over the phone, transcribe their memories, and mail you physical keepsake letters.
        </div>
    </div>
    """, unsafe_allow_html=True)

    # --- PRIMARY CTA (ARCHIVE) ---
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        if st.button("📚 Start Your Family Archive", type="primary", use_container_width=True):
            if st.session_state.get("authenticated"):
                st.session_state.app_mode = "heirloom"
            else:
                st.session_state.app_mode = "login"
                st.session_state.redirect_to = "heirloom"
            st.rerun()

    # --- TRUST BADGES (FIXED URLS) ---
    st.markdown("""
    <div style="text-align: center; margin-top: 40px; margin-bottom: 15px;">
        <small style="font-size: 0.7rem; letter-spacing: 1px; text-transform: uppercase; color: #888;">Secure Infrastructure</small>
    </div>
    <div class="trust-container">
        <img class="trust-logo" src="https://upload.wikimedia.org/wikipedia/commons/b/ba/Stripe_Logo%2C_revised_2016.svg" alt="Stripe">
        <img class="trust-logo" src="https://upload.wikimedia.org/wikipedia/commons/7/7e/Twilio_logo.svg" alt="Twilio" style="height: 28px;">
        <img class="trust-logo" src="https://upload.wikimedia.org/wikipedia/commons/4/4d/OpenAI_Logo.svg" alt="OpenAI">
        <img class="trust-logo" src="https://www.vectorlogo.zone/logos/supabase/supabase-ar21.svg" alt="Supabase" style="height: 32px;">
        <img class="trust-logo" src="https://www.vectorlogo.zone/logos/usps/usps-ar21.svg" alt="USPS" style="height: 35px;">
    </div>
    """, unsafe_allow_html=True)

    # --- SECONDARY OPTION (VENDING MACHINE) ---
    st.markdown("<div class='secondary-link'><div class='secondary-text'>Looking to send a single letter?</div></div>", unsafe_allow_html=True)
    
    col_sec1, col_sec2, col_sec3 = st.columns([1, 1, 1])
    with col_sec2:
        if st.button("📮 Go to Letter Store", use_container_width=True):
            if st.session_state.get("authenticated"):
                st.session_state.app_mode = "main" 
            else:
                st.session_state.app_mode = "login"
                st.session_state.redirect_to = "main" 
            st.rerun()

    # --- FOOTER ---
    st.markdown("<br><br>", unsafe_allow_html=True)
    
    # NAVIGATION (FIXED KEYS)
    c_blog, c_legal = st.columns(2)
    with c_blog:
         if st.button("📰 Read our Blog", use_container_width=True, key="splash_foot_blog"):
             st.session_state.app_mode = "blog"
             st.rerun()
    with c_legal:
         if st.button("⚖️ Legal / Terms", use_container_width=True, key="splash_foot_legal"):
            st.session_state.app_mode = "legal"
            st.rerun()

    st.markdown("<div style='text-align: center; color: #ccc; font-size: 0.75rem; border-top: 1px solid #f0f0f0; padding-top: 20px; margin-top: 20px;'>VerbaPost • Private • Secure • Forever</div>", unsafe_allow_html=True)
    
    return ""