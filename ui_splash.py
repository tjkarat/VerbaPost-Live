import streamlit as st

# RENAMED from 'show_splash' to 'render_splash' to match your main.py
def render_splash():
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
        padding: 4rem 1rem 5rem 1rem;
        text-align: center;
        color: white;
        margin-top: -60px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }

    /* 3. Logo Title (Mobile Responsive) */
    .hero-title {
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        font-weight: 800;
        /* Clamp calculates size based on viewport width */
        font-size: clamp(2.8rem, 8vw, 5rem); 
        margin-bottom: 0.5rem;
        text-shadow: 0 2px 4px rgba(0,0,0,0.2);
        white-space: nowrap; /* Forces single line */
        line-height: 1.1;
    }

    .hero-subtitle {
        font-size: clamp(1rem, 4vw, 1.4rem);
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        color: #ffd700; /* Gold text */
        margin-bottom: 1.5rem;
    }

    .hero-text {
        font-size: 1.1rem;
        font-weight: 400;
        max-width: 600px;
        margin: 0 auto;
        opacity: 0.95;
        line-height: 1.6;
        font-style: italic;
    }

    /* 4. Feature Cards */
    .feature-card {
        background: white;
        padding: 2rem;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        text-align: center;
        height: 100%;
        border: 1px solid #f0f2f6;
        transition: transform 0.2s;
    }
    .feature-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 15px rgba(0,0,0,0.1);
    }
    .feature-icon { font-size: 2.5rem; margin-bottom: 1rem; }
    .feature-head { font-weight: 700; color: #333; margin-bottom: 0.5rem; }
    .feature-body { color: #666; font-size: 0.9rem; }

    /* Mobile Tweaks */
    @media (max-width: 600px) {
        .hero-container { padding-bottom: 3rem; }
    }
    </style>
    """, unsafe_allow_html=True)

    # --- HERO CONTENT ---
    st.markdown("""
    <div class="hero-container">
        <div class="hero-title">📮 VerbaPost</div>
        <div class="hero-subtitle">Texts are trivial, emails ignored<br>REAL MAIL GETS READ.</div>
        <div class="hero-text">
            "Don't know how to start, what to write?<br>
            Speak it first and we'll transcribe."
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # --- ACTION BUTTONS ---
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        # Primary "Start" Button
        if st.button("🚀 Start a Letter", type="primary", use_container_width=True):
            if st.session_state.get("authenticated"):
                st.session_state.app_mode = "store"
            else:
                st.query_params["view"] = "login"
            st.rerun()

        st.write("") 

        # Secondary "Legacy" Button
        if st.button("🕊️ Legacy Service (End of Life)", use_container_width=True):
            st.query_params["view"] = "legacy"
            st.rerun()

    st.markdown("<br><br>", unsafe_allow_html=True)

    # --- THREE COLUMN FEATURES ---
    c_a, c_b, c_c = st.columns(3)
    
    with c_a:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon">🎙️</div>
            <div class="feature-head">Speak</div>
            <div class="feature-body">Dictate your letter. AI transcribes and polishes it to perfection.</div>
        </div>
        """, unsafe_allow_html=True)
        
    with c_b:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon">📄</div>
            <div class="feature-head">Print</div>
            <div class="feature-body">We print on premium 24lb paper, fold, and envelope it for you.</div>
        </div>
        """, unsafe_allow_html=True)
        
    with c_c:
        st.markdown("""
        <div class="feature-card">
            <div class="feature-icon">📬</div>
            <div class="feature-head">Send</div>
            <div class="feature-body">Mailed via USPS First Class or Certified Mail. No stamps needed.</div>
        </div>
        """, unsafe_allow_html=True)

    # --- FOOTER ---
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    st.markdown("""
    <div style="text-align: center; color: #aaa; font-size: 0.8rem;">
        VerbaPost v3.2.4 • Secure • Private • Real
    </div>
    """, unsafe_allow_html=True)