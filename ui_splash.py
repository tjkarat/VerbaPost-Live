import streamlit as st

def show_splash():
    # --- CSS STYLING ---
    st.markdown("""
    <style>
        /* Global Spacing */
        div.block-container { padding-top: 2rem; padding-bottom: 4rem; }
        
        /* Hero Typography */
        .hero-header {
            text-align: center; 
            padding-bottom: 5px;
            margin-bottom: 0px;
            font-family: 'Source Sans Pro', sans-serif;
        }
        .hero-sub {
            text-align: center; 
            margin-bottom: 30px; 
            color: #555;
            font-size: 1.1rem;
            line-height: 1.5;
        }
        
        /* PRICING CARDS (Dark Theme Accent) */
        .pricing-card {
            background: linear-gradient(180deg, #203A60 0%, #152845 100%);
            border-radius: 10px;
            padding: 12px 5px;
            color: white;
            text-align: center;
            height: 100%;
            border: 1px solid #304b78;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            transition: transform 0.2s;
        }
        .pricing-card:hover {
            transform: translateY(-3px);
            box-shadow: 0 6px 12px rgba(0,0,0,0.15);
        }
        .card-title {
            font-size: 0.9rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin: 0; 
            color: #e0e0e0;
        }
        .card-sub {
            font-size: 0.65rem;
            color: #a0aab8;
            font-style: italic;
            margin-bottom: 4px;
        }
        .card-price {
            font-size: 1.5rem;
            font-weight: 800;
            margin: 0px 0 8px 0;
            color: #ffffff;
        }
        .features-list {
            text-align: left;
            font-size: 0.7rem;
            margin: 0 auto;
            display: inline-block;
            color: #d1d5db;
            line-height: 1.4;
        }
        
        /* HOW IT WORKS CARDS (Light Theme) */
        .work-card {
            background-color: #ffffff;
            border: 1px solid #f0f2f6;
            border-radius: 10px;
            padding: 15px;
            text-align: center;
            height: 100%;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }
        .work-icon {
            font-size: 1.5rem;
            margin-bottom: 8px;
            display: block;
        }
        .work-title {
            font-weight: 700;
            font-size: 0.9rem;
            color: #31333F;
            margin-bottom: 5px;
        }
        .work-desc {
            font-size: 0.8rem;
            color: #666;
            line-height: 1.3;
        }

        /* LEADERBOARD (Compact) */
        .stat-box {
            background-color: #f8f9fa;
            border-radius: 6px;
            padding: 8px 12px;
            border: 1px solid #eee;
            text-align: center;
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 5px;
        }
        .stat-label {
            font-weight: 600;
            font-size: 0.85rem;
            color: #31333F;
        }
        .stat-val {
            font-weight: 700;
            font-size: 0.85rem;
            color: #FF4B4B;
            background: #fff0f0;
            padding: 2px 8px;
            border-radius: 10px;
        }
        
        /* Button Override */
        .stButton button {
            width: 100%;
            border-radius: 20px;
            font-weight: 600;
        }
    </style>
    """, unsafe_allow_html=True)

    # --- HERO SECTION ---
    st.markdown('<div class="hero-header"><h1>VerbaPost</h1></div>', unsafe_allow_html=True)
    st.markdown(
        """
        <div class="hero-sub">
            <div style="font-size: 1.2rem; font-weight: 600; color: #203A60; margin-bottom: 5px;">
                Record your voice, send a letter.
            </div>
            <div style="font-size: 0.95rem; color: #666;">
                Texts are trivial, emails ignored, <strong style="color: #333;">REAL MAIL GETS READ.</strong>
            </div>
        </div>
        """, 
        unsafe_allow_html=True
    )

    # --- MAIN CTA ---
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🚀 Start a Letter", type="primary", use_container_width=True):
            if st.session_state.get("authenticated"):
                st.session_state.app_mode = "store"
            else:
                st.session_state.auth_view = "signup"
                st.session_state.app_mode = "login"
            st.rerun()

    st.write("") 

    # --- PRICING SECTION ---
    c1, c2, c3, c4 = st.columns(4)

    # 1. STANDARD
    with c1:
        st.markdown("""
        <div class="pricing-card">
            <div class="card-title">Standard</div>
            <div class="card-sub">Single Letter</div>
            <div class="card-price">$2.99</div>
            <div class="features-list">
                <div>🇺🇸 USPS First Class</div>
                <div>📄 Standard Paper</div>
                <div>🤖 AI Transcription</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # 2. HEIRLOOM
    with c2:
        st.markdown("""
        <div class="pricing-card">
            <div class="card-title">Heirloom</div>
            <div class="card-sub">Single Letter</div>
            <div class="card-price">$5.99</div>
            <div class="features-list">
                <div>🖋️ Wet-Ink Style</div>
                <div>📜 Archival Stock</div>
                <div>✍️ Hand-Addressed</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # 3. CIVIC
    with c3:
        st.markdown("""
        <div class="pricing-card">
            <div class="card-title">Civic</div>
            <div class="card-sub">Three Letters</div>
            <div class="card-price">$6.99</div>
            <div class="features-list">
                <div>🏛️ Write Congress</div>
                <div>📍 Auto-Rep Lookup</div>
                <div>📦 Formal Layout</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # 4. SANTA
    with c4:
        st.markdown("""
        <div class="pricing-card">
            <div class="card-title">Santa</div>
            <div class="card-sub">Single Letter</div>
            <div class="card-price">$9.99</div>
            <div class="features-list">
                <div>❄️ North Pole Mark</div>
                <div>📜 Festive Paper</div>
                <div>🎅 Signed by Santa</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # --- HOW IT WORKS / FAQ SECTION (Moved from Sidebar) ---
    st.write("")
    st.write("")
    st.markdown("<h4 style='text-align: center; color: #333;'>🛠️ How It Works</h4>", unsafe_allow_html=True)
    
    hw1, hw2, hw3 = st.columns(3)
    
    with hw1:
        st.markdown("""
        <div class="work-card">
            <span class="work-icon">🎙️</span>
            <div class="work-title">1. Dictate or Type</div>
            <div class="work-desc">Use our AI tools to draft your letter quickly, or type it out manually.</div>
        </div>
        """, unsafe_allow_html=True)
    
    with hw2:
        st.markdown("""
        <div class="work-card">
            <span class="work-icon">🖨️</span>
            <div class="work-title">2. We Print & Prep</div>
            <div class="work-desc">We print on premium paper (Bond or Archival), fold, envelope, and stamp it.</div>
        </div>
        """, unsafe_allow_html=True)
        
    with hw3:
        st.markdown("""
        <div class="work-card">
            <span class="work-icon">📮</span>
            <div class="work-title">3. USPS Delivers</div>
            <div class="work-desc">Mailed within 24 hours via First Class. Arrives in 3-5 business days.</div>
        </div>
        """, unsafe_allow_html=True)

    st.write("")
    st.markdown("---")

    # --- GAMIFICATION / LEADERBOARD ---
    st.markdown("<h5 style='text-align: center; color: #555;'>🏆 Civic Impact Leaderboard</h5>", unsafe_allow_html=True)
    
    try:
        import database
        leaders = database.get_civic_leaderboard()
        if leaders:
            # Centered container for stats
            col_spacer, col_content, col_spacer2 = st.columns([1, 2, 1])
            with col_content:
                # Create a grid of small stats
                cols = st.columns(min(len(leaders), 3))
                for idx, (state, count) in enumerate(leaders[:3]):
                    with cols[idx]:
                        st.markdown(f"""
                        <div class="stat-box">
                            <span class="stat-label">📍 {state}</span>
                            <span class="stat-val">{count} Sent</span>
                        </div>
                        """, unsafe_allow_html=True)
        else:
            st.markdown("<p style='text-align:center; font-size: 0.8rem; color: #888;'>Be the first to make your voice heard!</p>", unsafe_allow_html=True)
    except Exception:
        st.empty()