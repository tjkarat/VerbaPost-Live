import streamlit as st
import logging

# Robust Import
try: import database
except ImportError: database = None

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def show_splash():
    # CSS
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
        .hero-subtext b, .hero-subtext strong { color: #ffffff !important; font-weight: 800; }
        .price-card {
            background: linear-gradient(135deg, #2c3e50 0%, #4ca1af 100%);
            padding: 15px; border-radius: 10px; border: 1px solid #4a90e2;
            text-align: center; height: 100%; display: flex;
            flex-direction: column; justify-content: flex-start;
            color: white !important; box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .price-title { color: #ffffff !important; font-weight: bold; font-size: 1.1rem; margin-bottom: 5px; }
        .price-tag { font-size: 1.8rem; font-weight: 800; color: #ffeb3b !important; margin: 5px 0; }
        .price-card ul { list-style: none; padding: 0; margin-top: 10px; }
        .price-card li { color: #e0e0e0 !important; font-size: 0.85rem; margin-bottom: 4px; }
    </style>
    """, unsafe_allow_html=True)

    # HERO
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
        if st.button("🚀 Start a Letter (Dictate or Upload)", type="primary", use_container_width=True):
            st.session_state.app_mode = "store"
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # PRICING
    p1, p2, p3, p4 = st.columns(4)
    with p1:
        st.markdown("""<div class="price-card"><div class="price-title">Standard</div><div class="price-tag">$2.99</div><ul><li>🇺🇸 USPS First Class</li><li>📄 Standard Paper</li><li>🤖 AI Transcription</li></ul></div>""", unsafe_allow_html=True)
    with p2:
        st.markdown("""<div class="price-card"><div class="price-title">🏺 Heirloom</div><div class="price-tag">$5.99</div><ul><li>🖋️ Wet-Ink Style</li><li>📜 Archival Stock</li><li>👋 Hand-Addressed</li></ul></div>""", unsafe_allow_html=True)
    with p3:
        st.markdown("""<div class="price-card"><div class="price-title">🏛️ Civic</div><div class="price-tag">$6.99</div><ul><li>🏛️ Write Congress</li><li>📍 Auto-Rep Lookup</li><li>📜 Formal Layout</li></ul></div>""", unsafe_allow_html=True)
    with p4:
        st.markdown("""<div class="price-card"><div class="price-title">🎅 Santa</div><div class="price-tag">$9.99</div><ul><li>❄️ North Pole Mark</li><li>📜 Festive Paper</li><li>✍️ Signed by Santa</li></ul></div>""", unsafe_allow_html=True)

    # LEADERBOARD
    if database:
        try:
            stats = database.get_civic_leaderboard()
            if stats:
                st.markdown("<br>", unsafe_allow_html=True)
                with st.container(border=True):
                    st.subheader("📢 Civic Leaderboard")
                    for state, count in stats:
                        st.progress(min(count * 5, 100), text=f"**{state}**: {count} letters sent")
            else:
                # Database connected but empty - show nothing or placeholder
                pass
        except Exception as e:
            # Log error but don't break UI
            logger.error(f"Leaderboard Error: {e}")
            pass
    else:
        st.info("Leaderboard temporarily unavailable.")