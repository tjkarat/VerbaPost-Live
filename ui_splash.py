import streamlit as st

def show_splash():
    # --- MODERN CSS STYLING ---
    st.markdown("""
    <style>
    /* 1. Global Reset & Container Logic */
    .block-container {
        padding-top: 0rem !important; /* Remove default top padding */
        padding-bottom: 2rem;
        max-width: 100%;
    }
    
    /* 2. The Modern Hero Section */
    .hero-container {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        width: 100vw;
        position: relative;
        left: 50%;
        right: 50%;
        margin-left: -50vw;
        margin-right: -50vw;
        padding: 4rem 1rem 6rem 1rem; /* Extra bottom padding for overlap effect */
        text-align: center;
        color: white;
        box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        margin-top: -60px; /* Pull to absolute top */
        margin-bottom: 2rem;
    }

    /* 3. Typography & Branding */
    .hero-title {
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        font-weight: 800;
        /* Responsive font size: starts big, shrinks on mobile */
        font-size: clamp(2.5rem, 8vw, 5rem); 
        letter-spacing: -1px;
        margin-bottom: 0.5rem;
        text-shadow: 0 2px 4px rgba(0,0,0,0.2);
        white-space: nowrap; /* Forces logo to stay on one line */
    }

    .hero-subtitle {
        font-size: clamp(1rem, 4vw, 1.5rem);
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 1px;
        color: #ffd700; /* Gold/Yellow for pop against purple */
        margin-bottom: 1.5rem;
    }

    .hero-text {
        font-size: 1.2rem;
        font-weight: 400;
        max-width: 700px;
        margin: 0 auto;
        opacity: 0.9;
        line-height: 1.6;
        font-style: italic;
    }

    /* 4. Feature Cards */
    .feature-card {
        background: white;
        padding: 1.5rem;
        border-radius: 16px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        text-align: center;
        transition: transform 0.3s ease;
        height: 100%;
        border: 1px solid #f0f2f6;
    }
    .feature-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 15px rgba(0,0,0,0.1);
    }
    .feature-icon {
        font-size: 2.5rem;
        margin-bottom: 1rem;
    }
    .feature-title {
        font-weight: 700;
        color: #333;
        margin-bottom: 0.5rem;
    }
    .feature-desc {
        color: #666;
        font-size: 0.9rem;
    }

    /* Mobile Tweaks */
    @media (max-width: 600px) {
        .hero-container { padding: 3rem 1rem 4rem 1rem; }
        .hero-text { font-size: 1rem; padding: 0 10px; }
    }
    </style>
    """, unsafe_allow_html=True)

    # --- HERO SECTION ---
    st.markdown("""
    <div class="hero-container">
        <div class="hero-title">📮 VerbaPost</div>
        <div class="hero-subtitle">Texts are trivial, emails ignored.<br>REAL MAIL GETS READ.</div>
        <div class="hero-text">
            "Don't know how to start or what to write?<br>
            Speak it first and we'll transcribe."
        </div>
    </div>
    """, unsafe_allow_html=True)

    # --- ACTION BUTTONS (Floating Effect) ---
    # We use a container to visually separate this from the hero
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        # Main Call to Action
        if st.button("🚀 Start a Letter", type="primary", use_container_width=True):
            if st.session_state.get("authenticated"):
                st.session_state.app_mode = "store"
            else:
                st.query_params["view"] = "login"
            st.rerun()

        st.write("") # Spacer

        # Legacy Service Link
        if st.button("🕊️ Legacy Service (End of Life)", use_container_width=True):
            st.query_params["view"] = "legacy"
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # --- MODERN FEATURE GRID ---
    c_a, c_b, c_c = st.columns(3)
    
    with c_a:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon">🎙️</div>
            <div class="feature-title">Speak</div>
            <div class="feature-desc">Dictate your letter effortlessly. Our AI transcribes and polishes your words to perfection.</div>
        </div>
        """, unsafe_allow_html=True)
        
    with c_b:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon">📄</div>
            <div class="feature-title">Print</div>
            <div class="feature-desc">We print on premium 24lb archival paper, fold, and envelope it for you.</div>
        </div>
        """, unsafe_allow_html=True)
        
    with c_c:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon">📬</div>
            <div class="feature-title">Send</div>
            <div class="feature-desc">Mailed via USPS First Class or Certified Mail with full tracking. No stamps needed.</div>
        </div>
        """, unsafe_allow_html=True)

    # --- FOOTER ---
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    st.markdown("""
    <div style="text-align: center; color: #888; font-size: 0.8rem;">
        VerbaPost v3.2.3 • Secure • Private • Real<br>
        <span style="opacity: 0.6;">Trusted by 10,000+ senders</span>
    </div>
    """, unsafe_allow_html=True)