import streamlit as st

# Attempt to import database, fail gracefully
try: import database
except ImportError: database = None

def show_splash():
    # --- 1. SCOPED CSS (Safe for Global App) ---
    st.markdown("""
    <style>
        /* HERO GRADIENT */
        .hero-container {
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            padding: 60px 20px;
            border-radius: 15px;
            color: white !important;
            text-align: center;
            box-shadow: 0 10px 25px rgba(0,0,0,0.1);
            margin-bottom: 30px;
        }
        .hero-title { font-size: 3.5rem; font-weight: 700; margin: 0; color: white !important; }
        .hero-subtitle { font-size: 1.8rem; font-weight: 600; margin-top: 10px; color: #a8c0ff !important; }
        .hero-subtext {
            margin-top: 20px; font-size: 1.15rem; line-height: 1.6;
            opacity: 0.95; color: #ffffff !important;
            max-width: 700px; margin-left: auto; margin-right: auto;
        }
        .hero-subtext b, .hero-subtext strong { color: #ffffff !important; font-weight: 800; }
        
        /* HOW IT WORKS SECTION */
        .steps-container {
            display: flex;
            justify-content: space-around;
            text-align: center;
            margin-bottom: 40px;
            gap: 20px;
        }
        .step-card {
            background: white;
            padding: 20px;
            border-radius: 10px;
            border: 1px solid #e2e8f0;
            flex: 1;
            box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        }
        .step-icon { font-size: 2.5rem; margin-bottom: 10px; display: block; }
        .step-title { font-weight: bold; color: #2a5298 !important; margin-bottom: 5px; font-size: 1.1rem; }
        .step-desc { font-size: 0.9rem; color: #666 !important; }

        /* PRICING CARDS */
        .price-card {
            background: linear-gradient(135deg, #2c3e50 0%, #4ca1af 100%);
            background: #1e3c72; /* Fallback */
            padding: 15px; border-radius: 10px; border: 1px solid #4a90e2;
            text-align: center; height: 100%; display: flex;
            flex-direction: column; justify-content: flex-start;
            color: white !important; box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .price-title { color: #ffffff !important; font-weight: bold; font-size: 1.1rem; margin-bottom: 5px; }
        .price-tag { font-size: 1.8rem; font-weight: 800; color: #ffeb3b !important; margin: 5px 0; }
        .price-desc { color: #e0e0e0 !important; font-size: 0.85rem; line-height: 1.4; }
        .price-card ul { list-style: none; padding: 0; margin-top: 10px; }
        .price-card li { color: #e0e0e0 !important; font-size: 0.85rem; margin-bottom: 4px; }
    </style>
    """, unsafe_allow_html=True)

    # --- 2. HERO ---
    st.markdown("""
    <div class="hero-container">
        <div class="hero-title">VerbaPost 📮</div>
        <div class="hero-subtitle">Making sending physical mail easier.</div>
        <div class="hero-subtext">
            Turn your voice into professional letters. Record live or <b>upload your audio files</b> (MP3/WAV). 
            <br>We handle the transcription, printing, and mailing via USPS.
        </div>
    </div>
    """, unsafe_allow_html=True)

    c_pad, c_btn, c_pad2 = st.columns([1, 2, 1])
    with c_btn:
        if st.button("🚀 Start a Letter (Dictate or Upload)", type="primary", use_container_width=True, key="splash_cta_main"):
            st.session_state.app_mode = "login"
            st.session_state.auth_view = "signup" 
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # --- 3. HOW IT WORKS ---
    st.markdown("""
    <h3 style="text-align: center; color: #2a5298; margin-bottom: 20px;">How It Works</h3>
    <div class="steps-container">
        <div class="step-card">
            <span class="step-icon">🎤</span>
            <div class="step-title">1. Speak or Type</div>
            <div class="step-desc">Dictate your letter, upload an audio file, or type it out directly.</div>
        </div>
        <div class="step-card">
            <span class="step-icon">🤖</span>
            <div class="step-title">2. AI Polish</div>
            <div class="step-desc">Our AI transcribes and formats your letter to look professional.</div>
        </div>
        <div class="step-card">
            <span class="step-icon">📮</span>
            <div class="step-title">3. We Mail It</div>
            <div class="step-desc">We print, envelope, stamp, and mail it via USPS First Class.</div>
        </div>
    </div>
    <br>
    """, unsafe_allow_html=True)

    # --- 4. PRICING CARDS ---
    p1, p2, p3, p4 = st.columns(4)
    with p1:
        st.markdown("""<div class="price-card"><div class="price-title">Standard</div><div class="price-tag">$2.99</div><ul><li>🇺🇸 USPS First Class</li><li>📄 Standard Paper</li><li>🤖 AI Transcription</li><li>&nbsp;</li></ul></div>""", unsafe_allow_html=True)
    with p2:
        st.markdown("""<div class="price-card"><div class="price-title">🏺 Heirloom</div><div class="price-tag">$5.99</div><ul><li>🖋️ Wet-Ink Style</li><li>📜 Archival Stock</li><li>👋 Hand-Addressed</li></ul></div>""", unsafe_allow_html=True)
    with p3:
        st.markdown("""<div class="price-card"><div class="price-title">🏛️ Civic</div><div class="price-tag">$6.99</div><ul><li>🏛️ Write Congress</li><li>📍 Auto-Rep Lookup</li><li>📜 Formal Layout</li></ul></div>""", unsafe_allow_html=True)
    with p4:
        st.markdown("""<div class="price-card"><div class="price-title">🎅 Santa</div><div class="price-tag">$9.99</div><ul><li>❄️ North Pole Mark</li><li>📜 Festive Paper</li><li>✍️ Signed by Santa</li></ul></div>""", unsafe_allow_html=True)

    # --- 5. LEADERBOARD ---
    if database:
        try:
            stats = database.get_civic_leaderboard()
            st.markdown("<br>", unsafe_allow_html=True)
            with st.container(border=True):
                st.subheader("📢 Civic Leaderboard")
                if stats:
                    for state, count in stats:
                        st.progress(min(count * 5, 100), text=f"**{state}**: {count} letters sent")
                else:
                    st.info("No letters sent yet. Be the first to start the movement!")
        except Exception:
            pass