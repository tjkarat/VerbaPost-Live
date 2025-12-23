import streamlit as st

def render_splash_page():
    """
    Renders the professional landing page for VerbaPost.
    Preserves all original minimalist CSS and hero sections.
    Fixed: 'Start a Letter' button now sets app_mode to 'store' correctly.
    """
    # --- PROFESSIONAL MINIMALIST CSS ---
    st.markdown("""
    <style>
    .block-container { padding-top: 2rem !important; padding-bottom: 3rem; max-width: 900px; }
    .hero-container { background-color: #ffffff; width: 100%; padding: 3rem 1rem 2rem 1rem; text-align: center; border-bottom: 1px solid #eaeaea; margin-bottom: 2rem; }
    .hero-title { font-family: 'Merriweather', serif; font-weight: 700; color: #111; font-size: clamp(2.5rem, 6vw, 4rem); margin-bottom: 0.5rem; letter-spacing: -0.5px; line-height: 1.2; }
    .hero-subtitle { font-family: 'Helvetica Neue', sans-serif; font-size: clamp(0.9rem, 3vw, 1.1rem); font-weight: 600; text-transform: uppercase; letter-spacing: 2px; color: #d93025; margin-bottom: 1.5rem; margin-top: 1rem; }
    .hero-text { font-family: 'Helvetica Neue', sans-serif; font-size: 1.15rem; font-weight: 300; color: #555; max-width: 600px; margin: 0 auto; line-height: 1.6; }
    
    /* TRUST LOGO STYLING */
    .trust-container { text-align: center; padding: 20px 0; opacity: 0.8; margin-top: 10px; }
    .trust-logo { display: inline-block; margin: 0 15px; height: 24px; vertical-align: middle; }
    
    .feature-icon { font-size: 2rem; margin-bottom: 0.5rem; opacity: 0.8; }
    .feature-head { font-weight: 600; color: #111; margin-bottom: 0.25rem; font-family: 'Merriweather', serif; }
    .feature-body { color: #666; font-size: 0.9rem; line-height: 1.5; }
    </style>
    """, unsafe_allow_html=True)

    # --- HERO CONTENT ---
    st.markdown("""
    <div class="hero-container">
        <div class="hero-title">VerbaPost</div>
        <div class="hero-subtitle">REAL MAIL GETS READ</div>
        <div class="hero-text">
            Texts are trivial. Emails are ignored.<br>
            <span style="font-style: italic;">"Don't know how to start? Speak it first, and we'll transcribe."</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # --- ACTION BUTTONS ---
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        # BUTTON 1: START A LETTER (Fixed trigger to 'store')
        if st.button("Start a Letter", use_container_width=True, key="splash_btn_start_letter"):
            if st.session_state.get("authenticated"):
                st.session_state.app_mode = "store"
            else:
                st.session_state.app_mode = "login"
                st.session_state.redirect_to = "store" # Ensure redirection target is set
            st.rerun()

        st.write("") 
        
        # BUTTON 2: THE FAMILY ARCHIVE (Direct trigger to 'heirloom')
        if st.button("The Family Archive", type="primary", use_container_width=True, key="splash_btn_heirloom"):
            if st.session_state.get("authenticated"):
                st.session_state.app_mode = "heirloom"
            else:
                st.session_state.app_mode = "login"
                # REDIRECTION TARGET: ui_login knows where to go next
                st.session_state.redirect_to = "heirloom"
            st.rerun()

    # --- INFRASTRUCTURE LOGOS ---
    st.markdown("""
    <div class="trust-container">
        <small style="display:block; margin-bottom:12px; color:#666; font-weight: 600; letter-spacing:1px; text-transform: uppercase; font-size: 0.7rem;">Powered by Secure & Reliable Infrastructure</small>
        <img class="trust-logo" src="https://www.vectorlogo.zone/logos/stripe/stripe-ar21.svg" alt="Stripe">
        <img class="trust-logo" src="https://www.vectorlogo.zone/logos/twilio/twilio-ar21.svg" alt="Twilio">
        <img class="trust-logo" src="https://www.vectorlogo.zone/logos/supabase/supabase-ar21.svg" alt="Supabase">
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # --- FEATURES ---
    c_a, c_b, c_c = st.columns(3)
    with c_a:
        st.markdown("""<div style="text-align: center;"><div class="feature-icon">🎙️</div><div class="feature-head">Speak</div><div class="feature-body">Dictate your letter. AI transcribes and formats it instantly.</div></div>""", unsafe_allow_html=True)
    with c_b:
        st.markdown("""<div style="text-align: center;"><div class="feature-icon">📄</div><div class="feature-head">Print</div><div class="feature-body">Printed on archival bond paper, folded, and enveloped.</div></div>""", unsafe_allow_html=True)
    with c_c:
        st.markdown("""<div style="text-align: center;"><div class="feature-icon">📬</div><div class="feature-head">Send</div><div class="feature-body">USPS First Class or Certified Mail. Full tracking included.</div></div>""", unsafe_allow_html=True)

    # --- FOOTER ---
    st.markdown("<br><br>", unsafe_allow_html=True)
    col_foot1, col_foot2, col_foot3 = st.columns([1, 2, 1])
    with col_foot2:
        st.markdown("<div style='text-align: center; color: #ccc; font-size: 0.75rem; border-top: 1px solid #f0f0f0; padding-top: 20px;'>VerbaPost • Secure • Private • Real</div>", unsafe_allow_html=True)
        # NAVIGATION FIX: Assigning the mode correctly
        if st.button("⚖️ Legal / Terms", use_container_width=True, key="splash_btn_legal"):
            st.session_state.app_mode = "legal"
            st.rerun()
    
    return ""