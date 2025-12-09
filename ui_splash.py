import streamlit as st

# Safe Import of Database
try:
    import database
except (ImportError, SyntaxError):
    database = None

def show_splash():
    # --- 1. SCOPED CSS ---
    st.markdown("""
    <style>
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
        .price-card {
            background: #1e3c72;
            padding: 15px; border-radius: 10px; border: 1px solid #4a90e2;
            text-align: center; height: 100%; display: flex;
            flex-direction: column; justify-content: flex-start;
            color: white !important;
        }
        .price-title { color: #ffffff !important; font-weight: bold; font-size: 1.1rem; }
        .price-tag { font-size: 1.8rem; font-weight: 800; color: #ffeb3b !important; margin: 5px 0; }
        .price-card ul { list-style: none; padding: 0; margin-top: 10px; }
        .price-card li { color: #e0e0e0 !important; font-size: 0.85rem; margin-bottom: 4px; }
    </style>
    """, unsafe_allow_html=True)

    # --- 2. HERO SECTION ---
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

    # Call to Action
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        if st.button("🚀 Start a Letter (Dictate or Upload)", type="primary", use_container_width=True):
            st.session_state.app_mode = "login"
            st.session_state.auth_view = "signup" 
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # --- 3. PRICING CARDS ---
    p1, p2, p3, p4 = st.columns(4)
    with p1:
        # UPDATED: Reduced to 3 items to match height of other cards
        st.markdown("""<div class="price-card"><div class="price-title">Standard</div><div class="price-tag">$2.99</div><ul><li>🇺🇸 USPS First Class</li><li>📄 Standard Paper</li><li>📮 Machine Stamped</li></ul></div>""", unsafe_allow_html=True)
    with p2:
        st.markdown("""<div class="price-card"><div class="price-title">Heirloom</div><div class="price-tag">$5.99</div><ul><li>🖋️ Wet-Ink Style</li><li>📜 Archival Stock</li><li>👋 Hand-Addressed</li></ul></div>""", unsafe_allow_html=True)
    with p3:
        st.markdown("""<div class="price-card"><div class="price-title">Civic</div><div class="price-tag">$6.99</div><ul><li>🏛️ Write Congress</li><li>📍 Auto-Rep Lookup</li><li>📜 Formal Layout</li></ul></div>""", unsafe_allow_html=True)
    with p4:
        st.markdown("""<div class="price-card"><div class="price-title">Santa</div><div class="price-tag">$9.99</div><ul><li>❄️ North Pole Mark</li><li>📜 Festive Paper</li><li>✍️ Signed by Santa</li></ul></div>""", unsafe_allow_html=True)

    # --- 4. LEADERBOARD (Safe Mode) ---
    st.markdown("<br>", unsafe_allow_html=True)
    
    if database is None:
        st.info("📢 Civic Leaderboard (Database Offline)")
        return

    # If database exists, try to fetch stats
    try:
        stats = database.get_civic_leaderboard()
        with st.container(border=True):
            st.subheader("📢 Civic Leaderboard")
            if not stats:
                st.info("No letters sent yet. Be the first!")
            else:
                for state, count in stats:
                    st.progress(min(count * 5, 100), text=f"**{state}**: {count} letters sent")
    except Exception as e:
        # Prevent splash crash if DB query fails
        st.warning(f"Leaderboard unavailable: {e}")