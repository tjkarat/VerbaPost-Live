import streamlit as st

# Attempt to import database, fail gracefully
try: import database
except ImportError: database = None

def show_splash():
    # --- 1. RESTORED CSS & ANIMATIONS ---
    st.markdown("""
    <style>
        /* HERO GRADIENT */
        .hero-container {
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            padding: 60px 20px;
            border-radius: 15px;
            color: white;
            text-align: center;
            box-shadow: 0 10px 25px rgba(0,0,0,0.1);
            margin-bottom: 30px;
        }
        .hero-title { font-size: 3.5rem; font-weight: 700; margin: 0; }
        .hero-subtitle { font-size: 1.5rem; opacity: 0.9; margin-top: 10px; }
        
        /* PRICING CARDS */
        .price-card {
            background: white;
            padding: 20px;
            border-radius: 10px;
            border: 1px solid #e0e0e0;
            text-align: center;
            transition: transform 0.2s;
            height: 100%;
        }
        .price-card:hover { transform: scale(1.03); border-color: #2a5298; }
        .price-title { color: #2a5298; font-weight: bold; font-size: 1.2rem; }
        .price-tag { font-size: 2rem; font-weight: 800; color: #333; margin: 10px 0; }
        
        /* SANTA ANIMATION */
        @keyframes flyAcross {
            0% { transform: translateX(-100%); }
            100% { transform: translateX(120vw); }
        }
        .santa-sled {
            position: fixed; top: 15%; left: 0; font-size: 60px; z-index: 99;
            animation: flyAcross 20s linear infinite; pointer-events: none; opacity: 0.8;
        }
    </style>
    
    <div class="santa-sled">🎅🛷</div>
    """, unsafe_allow_html=True)

    # --- 2. NEW SIDEBAR (Requested) ---
    with st.sidebar:
        st.header("VerbaPost 📮")
        st.markdown("---")
        
        if st.button("🔑 Member Login", use_container_width=True):
            st.session_state.app_mode = "login"
            st.rerun()
            
        if st.button("⚖️ Legal & Privacy", use_container_width=True):
            st.session_state.app_mode = "legal"
            st.rerun()
            
        st.markdown("---")
        st.markdown("**Useful Links**")
        st.markdown("📧 [Contact Support](mailto:support@verbapost.com)")
        st.markdown("🌐 [VerbaPost.com](https://verbapost.com)")
        st.caption("v2.5.0 Production")

    # --- 3. RICH HERO SECTION ---
    st.markdown("""
    <div class="hero-container">
        <div class="hero-title">VerbaPost 📮</div>
        <div class="hero-subtitle">Real Physical Mail. Dictated by You. Sent by AI.</div>
        <div style="margin-top: 20px; font-size: 1.1rem; opacity: 0.8;">
            Texts are forgotten. Emails are ignored. <b>Real letters get read.</b>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # --- 4. CONSOLIDATED CTA ---
    c_pad, c_btn, c_pad2 = st.columns([1, 2, 1])
    with c_btn:
        # Using a primary button for the main action
        if st.button("🚀 Start Writing Your Letter", type="primary", use_container_width=True):
            st.session_state.app_mode = "login"
            st.rerun()
        st.markdown("<div style='text-align: center; color: #888; font-size: 0.8rem;'>No account required to browse. Sign up to send.</div>", unsafe_allow_html=True)

    st.markdown("---")

    # --- 5. VISUAL FEATURE CARDS ---
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("""
        <div class="price-card">
            <div style="font-size: 3rem;">🗣️</div>
            <div class="price-title">Dictate</div>
            <p style="color: #666; font-size: 0.9rem;">Just speak naturally. Our AI transcribes and formats your words into a professional layout.</p>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown("""
        <div class="price-card">
            <div style="font-size: 3rem;">✍️</div>
            <div class="price-title">Refine</div>
            <p style="color: #666; font-size: 0.9rem;">Choose a style: 'Professional', 'Friendly', or 'Witty'. We polish the grammar instantly.</p>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown("""
        <div class="price-card">
            <div style="font-size: 3rem;">📮</div>
            <div class="price-title">Mail</div>
            <p style="color: #666; font-size: 0.9rem;">We print, stamp, envelope, and mail it via USPS First Class or Certified Mail.</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # --- 6. PRICING TIERS (HTML) ---
    st.subheader("📦 Simple Pricing")
    p1, p2, p3 = st.columns(3)
    
    with p1:
        st.markdown("""
        <div class="price-card">
            <div class="price-title">Standard</div>
            <div class="price-tag">$2.99</div>
            <ul style="text-align: left; font-size: 0.85rem; color: #555;">
                <li>🇺🇸 Mailed via USPS</li>
                <li>📄 Standard Paper</li>
                <li>🤖 AI Transcription</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
    with p2:
        st.markdown("""
        <div class="price-card" style="border: 2px solid #d4af37;">
            <div class="price-title">🏛️ Civic</div>
            <div class="price-tag">$6.99</div>
            <ul style="text-align: left; font-size: 0.85rem; color: #555;">
                <li>🏛️ Write to Congress</li>
                <li>📍 Auto-Rep Lookup</li>
                <li>📜 Formal Layout</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

    with p3:
        st.markdown("""
        <div class="price-card" style="border: 2px solid #b41414;">
            <div class="price-title">🎅 Santa</div>
            <div class="price-tag">$9.99</div>
            <ul style="text-align: left; font-size: 0.85rem; color: #555;">
                <li>❄️ North Pole Postmark</li>
                <li>📜 Festive Paper</li>
                <li>✍️ Signed by Santa</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # --- 7. LEADERBOARD ---
    if database:
        stats = database.get_civic_leaderboard()
        if stats:
            with st.container(border=True):
                st.subheader("📢 Civic Leaderboard")
                st.caption("Top states making their voices heard this week")
                for state, count in stats:
                    st.progress(min(count * 5, 100), text=f"**{state}**: {count} letters sent")

    # --- 8. MISSION (Moved Bottom) ---
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #888; padding: 40px 20px;">
        <h4 style="color: #555;">Our Mission</h4>
        <p style="font-size: 0.95rem; max-width: 700px; margin: 0 auto; line-height: 1.6;">
            In a world drowning in digital noise, physical mail has become a superpower. 
            VerbaPost bridges the gap, allowing you to use modern voice technology to create 
            timeless physical correspondence. Whether it's a letter to Congress, a note to Grandma, 
            or a memory for your children, we make it real.
        </p>
    </div>
    """, unsafe_allow_html=True)