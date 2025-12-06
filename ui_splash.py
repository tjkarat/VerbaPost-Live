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
        .hero-subtitle { font-size: 1.5rem; opacity: 0.9; margin-top: 10px; color: white !important; }
        
        /* CARDS (Features & Pricing) - DARK THEME WITH WHITE TEXT */
        /* We use specific class names to avoid breaking other pages */
        .price-card {
            background: linear-gradient(135deg, #2c3e50 0%, #4ca1af 100%);
            background: #1e3c72; /* Fallback */
            padding: 20px;
            border-radius: 10px;
            border: 1px solid #4a90e2;
            text-align: center;
            transition: transform 0.2s;
            height: 100%; /* Keeps boxes uniform height */
            display: flex;
            flex-direction: column;
            justify-content: flex-start;
            color: white !important; 
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .price-card:hover { transform: scale(1.03); border-color: #ffffff; }
        
        /* TEXT INSIDE CARDS */
        .price-title { color: #ffffff !important; font-weight: bold; font-size: 1.2rem; margin-bottom: 10px; }
        .price-tag { font-size: 2rem; font-weight: 800; color: #ffeb3b !important; margin: 10px 0; }
        .price-desc { color: #e0e0e0 !important; font-size: 0.9rem; line-height: 1.4; }
        
        /* List items inside cards */
        .price-card ul { list-style: none; padding: 0; }
        .price-card li { color: #e0e0e0 !important; font-size: 0.9rem; margin-bottom: 5px; }
    </style>
    """, unsafe_allow_html=True)

    # --- 2. SIDEBAR ---
    with st.sidebar:
        st.header("VerbaPost 📮")
        st.markdown("---")
        
        # Navigation
        if st.button("🔑 Member Login", use_container_width=True):
            st.session_state.app_mode = "login"
            st.session_state.auth_view = "login" # Explicitly set view
            st.rerun()
            
        if st.button("⚖️ Legal & Privacy", use_container_width=True):
            st.session_state.app_mode = "legal"
            st.rerun()
            
        st.markdown("---")
        st.markdown("**Useful Links**")
        st.markdown("📧 [Contact Support](mailto:support@verbapost.com)")
        st.markdown("🌐 [VerbaPost.com](https://verbapost.com)")
        st.caption("v2.5.4 Production")

    # --- 3. HERO SECTION ---
    st.markdown("""
    <div class="hero-container">
        <div class="hero-title">VerbaPost 📮</div>
        <div class="hero-subtitle">Real Physical Mail. Dictated by You. Sent by AI.</div>
        <div style="margin-top: 20px; font-size: 1.1rem; opacity: 0.9; color: white;">
            Texts are forgotten. Emails are ignored. <b>Real letters get read.</b>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # --- 4. CONSOLIDATED CTA (Targeting Sign Up) ---
    c_pad, c_btn, c_pad2 = st.columns([1, 2, 1])
    with c_btn:
        if st.button("🚀 Start Writing Your Letter", type="primary", use_container_width=True):
            st.session_state.app_mode = "login"
            st.session_state.auth_view = "signup" # <--- TARGETS NEW USER TAB
            st.rerun()
        st.markdown("<div style='text-align: center; color: #888; font-size: 0.8rem;'>Sign up to send.</div>", unsafe_allow_html=True)

    st.markdown("---")

    # --- 5. VISUAL FEATURE CARDS (Balanced Text Lengths) ---
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("""
        <div class="price-card" style="background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);">
            <div style="font-size: 3rem;">🗣️</div>
            <div class="price-title">Dictate</div>
            <p class="price-desc">Just speak naturally. Our AI transcribes and formats your words into a professional layout automatically.</p>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown("""
        <div class="price-card" style="background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);">
            <div style="font-size: 3rem;">✍️</div>
            <div class="price-title">Refine</div>
            <p class="price-desc">Optionally use AI to polish grammar. You maintain full control to manually edit your letter before sending.</p>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown("""
        <div class="price-card" style="background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);">
            <div style="font-size: 3rem;">📮</div>
            <div class="price-title">Mail</div>
            <p class="price-desc">We print and mail via USPS. Heirloom letters are hand-addressed and include a real physical stamp.</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # --- 6. PRICING TIERS ---
    st.subheader("📦 Simple Pricing")
    p1, p2, p3 = st.columns(3)
    
    with p1:
        st.markdown("""
        <div class="price-card" style="background: linear-gradient(135deg, #485563 0%, #29323c 100%);">
            <div class="price-title">Standard</div>
            <div class="price-tag">$2.99</div>
            <ul>
                <li>🇺🇸 Mailed via USPS</li>
                <li>📄 Standard Paper</li>
                <li>🤖 AI Transcription</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
    with p2:
        st.markdown("""
        <div class="price-card" style="background: linear-gradient(135deg, #D4AF37 0%, #8a7329 100%); border: 2px solid gold;">
            <div class="price-title">🏛️ Civic</div>
            <div class="price-tag">$6.99</div>
            <ul>
                <li>🏛️ Write to Congress</li>
                <li>📍 Auto-Rep Lookup</li>
                <li>📜 Formal Layout</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

    with p3:
        st.markdown("""
        <div class="price-card" style="background: linear-gradient(135deg, #cb2d3e 0%, #ef473a 100%); border: 2px solid #ff9999;">
            <div class="price-title">🎅 Santa</div>
            <div class="price-tag">$9.99</div>
            <ul>
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

    # --- 8. MISSION (Bottom) ---
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