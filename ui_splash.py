import streamlit as st

def show_splash():
    # --- CSS STYLING ---
    # Custom CSS for ultra-compact vertical layout
    st.markdown("""
    <style>
        /* Reduce page top padding */
        div.block-container { padding-top: 1rem; padding-bottom: 5rem; }
        
        .hero-header {
            text-align: center; 
            padding-bottom: 5px;
            margin-bottom: 0px;
        }
        
        /* Ultra Compact Card Styling */
        .pricing-card {
            background: linear-gradient(180deg, #203A60 0%, #152845 100%);
            border-radius: 8px;
            padding: 8px 4px; /* Minimal padding */
            color: white;
            text-align: center;
            height: 100%;
            border: 1px solid #304b78;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            transition: transform 0.2s;
        }
        .pricing-card:hover {
            transform: translateY(-2px);
            border-color: #FF4B4B;
        }
        
        /* Tight Typography */
        .card-title {
            font-size: 1rem;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin: 0; 
            color: #ffffff;
            line-height: 1.1;
        }
        .card-sub {
            font-size: 0.7rem;
            color: #a0aab8;
            font-style: italic;
            margin: 0;
            line-height: 1.1;
        }
        .card-price {
            font-size: 1.4rem;
            font-weight: 900;
            margin: 2px 0 4px 0;
            color: #ffffff;
            line-height: 1;
        }
        
        /* Compact Feature List */
        .features-list {
            text-align: left;
            font-size: 0.75rem;
            margin: 0 auto;
            display: inline-block;
            line-height: 1.2;
            color: #d1d5db;
        }
        .feature-row {
            margin-bottom: 1px; /* Minimal spacing between items */
        }
        
        /* Button Adjustments */
        .stButton button {
            width: 100%;
            border-radius: 20px;
            font-weight: bold;
            height: auto;
            padding: 0.4rem 1rem;
        }

        /* FAQ Styling */
        .faq-box {
            background-color: #f8f9fa;
            border-radius: 8px;
            padding: 15px;
            margin-top: 20px;
            border: 1px solid #e9ecef;
        }
        .faq-q {
            font-weight: 700;
            font-size: 0.9rem;
            color: #203A60;
            margin-bottom: 2px;
        }
        .faq-a {
            font-size: 0.85rem;
            color: #4b5563;
            margin-bottom: 10px;
            line-height: 1.4;
        }
    </style>
    """, unsafe_allow_html=True)

    # --- HERO SECTION ---
    st.markdown('<div class="hero-header"><h1>VerbaPost</h1></div>', unsafe_allow_html=True)
    
    st.markdown(
        """
        <div style='text-align: center; margin-bottom: 20px;'>
            <h5 style='margin:0; padding:0;'>We handle transcription, printing, and USPS mailing.</h5>
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

    st.write("") # Small spacer

    # --- PRICING CARDS (Ultra Compact & Icon-Free) ---
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

    # --- HELP & FAQ SECTION ---
    # Positioned below pricing, above gamification
    st.write("")
    st.markdown("### ❓ Help & FAQ")
    
    faq1, faq2, faq3 = st.columns(3)
    
    with faq1:
        st.markdown("""
        <div class="faq-q">How does it work?</div>
        <div class="faq-a">Dictate or type your letter. We print it on real paper, envelope it, stamp it, and mail it via USPS.</div>
        """, unsafe_allow_html=True)
    
    with faq2:
        st.markdown("""
        <div class="faq-q">Is it real paper?</div>
        <div class="faq-a">Yes! Standard uses bright white bond. Heirloom uses heavy archival stock with wet-ink robotic pen technology.</div>
        """, unsafe_allow_html=True)
        
    with faq3:
        st.markdown("""
        <div class="faq-q">When will it arrive?</div>
        <div class="faq-a">We mail within 24 hours. USPS First Class typically delivers in 3-5 business days across the US.</div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # --- GAMIFICATION / LEADERBOARD ---
    # Made clearer by removing the expander and giving it a distinct section header
    st.subheader("🏆 Civic Impact Leaderboard")
    st.caption("See which states are making their voices heard with our Civic tier.")
    
    try:
        import database
        leaders = database.get_civic_leaderboard()
        if leaders:
            # Display metrics clearly in a row
            cols = st.columns(len(leaders))
            for idx, (state, count) in enumerate(leaders):
                cols[idx].metric(label=f"📍 {state}", value=f"{count} Sent")
        else:
            st.info("No civic activity recorded yet. Be the first!")
    except Exception:
        st.empty()