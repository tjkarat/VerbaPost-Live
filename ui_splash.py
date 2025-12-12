import streamlit as st
import logging

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Robust Import for Leaderboard
try: import database
except ImportError: database = None

def show_splash():
    # --- CSS CONFIGURATION ---
    st.markdown("""
    <style>
        /* MOBILE OPTIMIZATIONS */
        @media (max-width: 768px) {
            .hero-container { padding: 20px 10px !important; }
            .hero-title { font-size: 2rem !important; }
            .stButton button { width: 100% !important; }
        }

        /* HERO CONTAINER */
        .hero-container {
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            padding: 40px 20px;
            border-radius: 15px;
            text-align: center;
            box-shadow: 0 10px 25px rgba(0,0,0,0.15);
            margin-bottom: 25px;
        }
        
        /* FORCE WHITE TEXT HERO */
        .hero-container, .hero-container h1, .hero-container p, 
        .hero-container div, .hero-container span, .hero-container strong {
            color: #FFFFFF !important;
            --text-color: #FFFFFF !important;
        }

        .hero-title { 
            font-size: clamp(2.2rem, 5vw, 3.5rem); 
            font-weight: 800; 
            margin: 0; 
            line-height: 1.1;
            text-shadow: 0 2px 4px rgba(0,0,0,0.3);
        }
        .hero-subtitle { 
            font-size: clamp(1.1rem, 3vw, 1.8rem); 
            font-weight: 600; 
            margin-top: 10px; 
            opacity: 0.95;
        }
        .hero-subtext {
            margin-top: 15px; 
            font-size: 1.1rem; 
            line-height: 1.6;
            max-width: 800px; 
            margin-left: auto; 
            margin-right: auto;
            opacity: 0.9;
        }
        
        /* PRICE CARDS - FIXED HEIGHT & WHITE TEXT */
        .price-card {
            background: linear-gradient(135deg, #2c3e50 0%, #4ca1af 100%);
            padding: 20px;
            border-radius: 12px; 
            border: 1px solid #4a90e2;
            text-align: center; 
            
            /* ALIGNMENT FIX */
            height: 100%;           
            min-height: 380px;      /* Forces equal height for all cards */
            display: flex;
            flex-direction: column; 
            justify-content: flex-start;
            
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }

        /* FORCE WHITE TEXT CARDS */
        .price-card, .price-card div, .price-card h3, .price-card p, 
        .price-card li, .price-card span, .price-card strong, .price-card b {
            color: #FFFFFF !important;
            --text-color: #FFFFFF !important;
        }
        
        .price-title { 
            font-weight: 800; 
            font-size: 1.2rem; 
            margin-bottom: 5px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        .price-subtitle { 
            opacity: 0.9;
            font-size: 0.85rem; 
            font-style: italic; 
            margin-bottom: 15px; 
            font-weight: 500;
        }
        .price-tag { 
            font-size: 2rem; 
            font-weight: 800; 
            color: #FFEB3B !important; 
            margin: 10px 0;
            text-shadow: 0 1px 2px rgba(0,0,0,0.5);
        }
        .price-card ul { 
            list-style: none; 
            padding: 0; 
            margin-top: 10px; 
            text-align: center;
        }
        .price-card li { 
            font-size: 0.95rem; 
            margin-bottom: 6px; 
            line-height: 1.3;
            opacity: 0.95;
        }
    </style>
    """, unsafe_allow_html=True)

    # --- HERO ---
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

    # --- PRICING ---
    p1, p2, p3, p4 = st.columns(4)
    with p1:
        st.markdown("""<div class="price-card"><div class="price-title">Standard</div><div class="price-subtitle">Single Letter</div><div class="price-tag">$2.99</div><ul><li>🇺🇸 USPS First Class</li><li>📄 Standard Paper</li><li>🤖 AI Transcription</li></ul></div>""", unsafe_allow_html=True)
    with p2:
        st.markdown("""<div class="price-card"><div class="price-title">🏺 Heirloom</div><div class="price-subtitle">Single Letter</div><div class="price-tag">$5.99</div><ul><li>🖋️ Wet-Ink Style</li><li>📜 Archival Stock</li><li>👋 Hand-Addressed</li></ul></div>""", unsafe_allow_html=True)
    with p3:
        st.markdown("""<div class="price-card"><div class="price-title">🏛️ Civic</div><div class="price-subtitle">Three Letters</div><div class="price-tag">$6.99</div><ul><li>🏛️ Write Congress</li><li>📍 Auto-Rep Lookup</li><li>📜 Formal Layout</li></ul></div>""", unsafe_allow_html=True)
    with p4:
        st.markdown("""<div class="price-card"><div class="price-title">🎅 Santa</div><div class="price-subtitle">Single Letter</div><div class="price-tag">$9.99</div><ul><li>❄️ North Pole Mark</li><li>📜 Festive Paper</li><li>✍️ Signed by Santa</li></ul></div>""", unsafe_allow_html=True)

    # --- LEADERBOARD ---
    st.markdown("<br><hr>", unsafe_allow_html=True)
    if database:
        try:
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
            pass

    # --- FOOTER ---
    st.markdown("<br><br>", unsafe_allow_html=True)
    c_foot1, c_foot2, c_foot3 = st.columns([1, 1, 1])
    with c_foot2:
        if st.button("⚖️ View Legal & Privacy", type="secondary", use_container_width=True):
            st.session_state.app_mode = "legal"
            st.rerun()