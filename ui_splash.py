import streamlit as st

def show_splash():
    # --- CSS STYLING ---
    # We inject custom CSS to force the cards to be shorter and compact
    st.markdown("""
    <style>
        div.block-container { padding-top: 2rem; }
        
        .hero-header {
            text-align: center; 
            padding-bottom: 20px;
        }
        
        /* Compact Card Styling */
        .pricing-card {
            background: linear-gradient(180deg, #203A60 0%, #152845 100%);
            border-radius: 12px;
            padding: 15px 10px; /* Reduced vertical padding */
            color: white;
            text-align: center;
            height: 100%;
            border: 1px solid #304b78;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            transition: transform 0.2s;
        }
        .pricing-card:hover {
            transform: translateY(-3px);
            border-color: #FF4B4B;
        }
        
        /* Typography adjustments for height reduction */
        .card-title {
            font-size: 1.1rem;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin: 0 0 2px 0; /* Tight margin */
            color: #ffffff;
        }
        .card-sub {
            font-size: 0.8rem;
            color: #a0aab8;
            font-style: italic;
            margin-bottom: 5px;
        }
        .card-price {
            font-size: 1.8rem;
            font-weight: 900;
            margin: 5px 0 10px 0;
            color: #ffffff;
        }
        
        /* Feature list compaction */
        .features-list {
            text-align: left;
            font-size: 0.85rem;
            margin: 0 auto;
            display: inline-block;
            line-height: 1.4;
            color: #d1d5db;
        }
        .feature-row {
            margin-bottom: 4px; /* Tight spacing between items */
        }
        
        /* Button Styling */
        .stButton button {
            width: 100%;
            border-radius: 25px;
            font-weight: bold;
            padding: 0.5rem 1rem;
        }
    </style>
    """, unsafe_allow_html=True)

    # --- HERO SECTION ---
    st.markdown('<div class="hero-header"><h1>VerbaPost</h1></div>', unsafe_allow_html=True)
    
    st.markdown(
        """
        <div style='text-align: center; margin-bottom: 30px;'>
            <h4>We handle transcription, printing, and USPS mailing.</h4>
        </div>
        """, 
        unsafe_allow_html=True
    )

    # --- MAIN CTA ---
    # Centered Start Button
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🚀 Start a Letter (Dictate or Upload)", type="primary", use_container_width=True):
            # Intelligent Routing based on Auth Status
            if st.session_state.get("authenticated"):
                st.session_state.app_mode = "store"
            else:
                st.session_state.auth_view = "signup"
                st.session_state.app_mode = "login"
            st.rerun()

    st.write("") # Spacer

    # --- PRICING CARDS (COMPACT) ---
    # We use HTML inside columns to strictly control the height/padding
    
    c1, c2, c3, c4 = st.columns(4)

    # 1. STANDARD
    with c1:
        st.markdown("""
        <div class="pricing-card">
            <div class="card-title">STANDARD</div>
            <div class="card-sub">Single Letter</div>
            <div class="card-price">$2.99</div>
            <div class="features-list">
                <div class="feature-row">🇺🇸 USPS First Class</div>
                <div class="feature-row">📄 Standard Paper</div>
                <div class="feature-row">🤖 AI Transcription</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # 2. HEIRLOOM
    with c2:
        st.markdown("""
        <div class="pricing-card">
            <div class="card-title">HEIRLOOM</div>
            <div class="card-sub">Single Letter</div>
            <div class="card-price">$5.99</div>
            <div class="features-list">
                <div class="feature-row">🖋️ Wet-Ink Style</div>
                <div class="feature-row">📜 Archival Stock</div>
                <div class="feature-row">✍️ Hand-Addressed</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # 3. CIVIC
    with c3:
        st.markdown("""
        <div class="pricing-card">
            <div class="card-title">CIVIC</div>
            <div class="card-sub">Three Letters</div>
            <div class="card-price">$6.99</div>
            <div class="features-list">
                <div class="feature-row">🏛️ Write Congress</div>
                <div class="feature-row">📍 Auto-Rep Lookup</div>
                <div class="feature-row">📦 Formal Layout</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # 4. SANTA
    with c4:
        st.markdown("""
        <div class="pricing-card">
            <div class="card-title">SANTA</div>
            <div class="card-sub">Single Letter</div>
            <div class="card-price">$9.99</div>
            <div class="features-list">
                <div class="feature-row">❄️ North Pole Mark</div>
                <div class="feature-row">📜 Festive Paper</div>
                <div class="feature-row">🎅 Signed by Santa</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # --- LEADERBOARD (Optional, kept minimal) ---
    st.write("")
    st.write("")
    with st.expander("🏆 See where Civic letters are being sent"):
        try:
            import database
            leaders = database.get_civic_leaderboard()
            if leaders:
                cols = st.columns(len(leaders))
                for idx, (state, count) in enumerate(leaders):
                    cols[idx].metric(state, f"{count} sent")
            else:
                st.info("No civic data yet.")
        except Exception:
            st.empty()