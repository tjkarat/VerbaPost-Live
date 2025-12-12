import streamlit as st
import logging

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Robust Import for Leaderboard
try: import database
except ImportError: database = None

def show_splash():
    # --- CSS CONFIGURATION (Fixed for Dark Mode) ---
    st.markdown("""
    <style>
        /* HERO STYLING */
        .hero-container {
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            padding: 40px 20px;
            border-radius: 15px;
            color: #FFFFFF !important;
            text-align: center;
            box-shadow: 0 10px 25px rgba(0,0,0,0.15);
            margin-bottom: 25px;
        }
        .hero-title { 
            font-size: clamp(2.2rem, 5vw, 3.5rem); 
            font-weight: 800; 
            margin: 0; 
            color: #FFFFFF !important; 
            text-shadow: 0 2px 4px rgba(0,0,0,0.3);
            line-height: 1.1;
        }
        .hero-subtitle { 
            font-size: clamp(1.1rem, 3vw, 1.8rem); 
            font-weight: 600; 
            margin-top: 10px; 
            color: #E0E0E0 !important; 
        }
        .hero-subtext {
            margin-top: 15px; 
            font-size: 1.1rem; 
            line-height: 1.6;
            color: #F0F0F0 !important;
            max-width: 800px; 
            margin-left: auto; 
            margin-right: auto;
        }
        .hero-subtext b { color: #FFFFFF !important; font-weight: 800; }
        
        /* PRICE CARD STYLING */
        .price-card {
            background: linear-gradient(135deg, #2c3e50 0%, #4ca1af 100%);
            padding: 15px;
            border-radius: 12px; 
            border: 1px solid #4a90e2;
            text-align: center; 
            height: 100%; 
            display: flex;
            flex-direction: column; 
            justify-content: flex-start;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            color: #FFFFFF !important;
            min-height: 240px;
        }
        .price-title { 
            color: #FFFFFF !important; 
            font-weight: 800; 
            font-size: 1.2rem; 
            margin-bottom: 2px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        .price-subtitle { 
            color: #a8c0ff !important; 
            font-size: 0.85rem; 
            font-style: italic; 
            margin-bottom: 10px; 
            font-weight: 500;
        }
        .price-tag { 
            font-size: 1.8rem; 
            font-weight: 800; 
            color: #FFEB3B !important; 
            margin: 5px 0;
            text-shadow: 0 1px 2px rgba(0,0,0,0.5);
        }
        /* Force list items to be white even in dark mode */
        .price-card ul { 
            list-style: none; 
            padding: 0; 
            margin-top: 10px; 
            text-align: center;
        }
        .price-card li { 
            color: #F0F0F0 !important; 
            font-size: 0.9rem; 
            margin-bottom: 4px; 
            line-height: 1.3;
        }
    </style>
    """, unsafe_allow_html=True)

    # --- HERO SECTION ---
    st.markdown("""
    <div class="hero-container">
        <div class="hero-title">VerbaPost 📮</div>
        <div class="hero-subtitle">Making sending physical mail easier.</div>
        <div class="hero-subtext">
            Turn your voice into professional letters. Record live or <b>upload your audio files</b> (MP3/WAV). 
            <br>We handle transcription, printing, and USPS mailing.
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Call to Action
    c_pad, c_btn, c_pad2 = st.columns([1, 2, 1])
    with c_btn:
        if st.button("🚀 Start a Letter (Dictate or Upload)", type="primary", use_container_width=True):
            if st.session_state.get("user_email"):
                st.session_state.app_mode = "store"
            else:
                st.session_state.app_mode = "login"
                st.session_state.auth_view = "signup"
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # --- PRICING CARDS ---
    p1, p2, p3, p4 = st.columns(4)
    with p1:
        st.markdown("""<div class="price-card"><div class="price-title">Standard</div><div class="price-subtitle">Single Letter</div><div class="price-tag">$2.99</div><ul><li>🇺🇸 USPS First Class</li><li>📄 Standard Paper</li><li>🤖 AI Transcription</li></ul></div>""", unsafe_allow_html=True)
    with p2:
        st.markdown("""<div class="price-card"><div class="price-title">🏺 Heirloom</div><div class="price-subtitle">Single Letter</div><div class="price-tag">$5.99</div><ul><li>🖋️ Wet-Ink Style</li><li>📜 Archival Stock</li><li>👋 Hand-Addressed</li></ul></div>""", unsafe_allow_html=True)
    with p3:
        st.markdown("""<div class="price-card"><div class="price-title">🏛️ Civic</div><div class="price-subtitle">Three Letters</div><div class="price-tag">$6.99</div><ul><li>🏛️ Write Congress</li><li>📍 Auto-Rep Lookup</li><li>📜 Formal Layout</li></ul></div>""", unsafe_allow_html=True)
    with p4:
        st.markdown("""<div class="price-card"><div class="price-title">🎅 Santa</div><div class="price-subtitle">Single Letter</div><div class="price-tag">$9.99</div><ul><li>❄️ North Pole Mark</li><li>📜 Festive Paper</li><li>✍️ Signed by Santa</li></ul></div>""", unsafe_allow_html=True)

    # --- LEADERBOARD (Safe Mode) ---
    st.markdown("<br><hr>", unsafe_allow_html=True)
    if database:
        try:
            # Safely check if function exists to prevent crash if database.py is outdated
            func = getattr(database, 'get_civic_leaderboard', None)
            stats = func() if func else []
            
            with st.container(border=True):
                st.subheader("📢 Civic Leaderboard")
                if stats:
                    for state, count in stats:
                        st.progress(min(count * 5, 100), text=f"**{state}**: {count} letters sent")
                else:
                    st.info("No letters sent yet this month. Be the first!")
        except Exception as e:
            logger.error(f"Leaderboard Error: {e}")
            st.warning("Leaderboard temporarily unavailable.")
    else:
        # Graceful degradation if DB is down
        pass

    # --- LEGAL FOOTER ---
    st.markdown("<br><br>", unsafe_allow_html=True)
    c_foot1, c_foot2, c_foot3 = st.columns([1, 1, 1])
    with c_foot2:
        if st.button("⚖️ View Legal & Privacy", type="secondary", use_container_width=True):
            st.session_state.app_mode = "legal"
            st.rerun()