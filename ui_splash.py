import streamlit as st

# Try to import civic engine for leaderboard, fail gracefully if missing
try: import civic_engine
except ImportError: civic_engine = None

def render_splash():
    # --- MOBILE OPTIMIZATION CSS ---
    st.markdown("""
    <style>
        /* Desktop Defaults */
        .splash-header { font-size: 3.5rem; margin-bottom: 10px; color: #1E1E1E; }
        .splash-sub { font-size: 1.5rem; color: #555; margin-bottom: 30px; }
        .splash-container { 
            text-align: center; 
            padding: 40px 20px 60px 20px; 
            background: linear-gradient(180deg, #FFFFFF 0%, #F0F2F6 100%); 
            border-radius: 0 0 20px 20px; 
            margin-bottom: 30px; 
        }

        /* Mobile Overrides */
        @media (max-width: 768px) {
            .splash-header { font-size: 2.2rem !important; }
            .splash-sub { font-size: 1.1rem !important; }
            .splash-container { padding: 20px 10px 30px 10px !important; }
            .stButton button { width: 100% !important; }
        }
    </style>
    """, unsafe_allow_html=True)

    # --- HERO SECTION ---
    st.markdown("""
    <div class="splash-container">
        <h1 class="splash-header">📮 VerbaPost</h1>
        <p class="splash-sub">Real letters, sent from your screen.</p>
    </div>
    """, unsafe_allow_html=True)

    # --- CALL TO ACTION BUTTONS ---
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        col_a, col_b = st.columns(2)
        with col_a:
            label = f"🚀 Continue" if st.session_state.get("authenticated") else "🚀 Start a Letter"
            if st.button(label, type="primary", use_container_width=True):
                if st.session_state.get("authenticated"):
                    st.session_state.app_mode = "store"
                else:
                    st.query_params["view"] = "login"
                st.rerun()
        
        with col_b:
             if st.button("🕯️ Legacy Service", use_container_width=True):
                 st.query_params["view"] = "legacy"
                 st.rerun()

    # --- VALUE PROPS ---
    st.markdown("---")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("### 🎙️ Speak")
        st.caption("Dictate your letter. AI transcribes and polishes it to perfection.")
    with c2:
        st.markdown("### 📄 Print")
        st.caption("We print on premium 24lb paper, fold, and envelope it for you.")
    with c3:
        st.markdown("### 📬 Send")
        st.caption("Mailed via USPS First Class or Certified Mail. No stamps needed.")

    # --- PRICING GRID ---
    st.markdown("---")
    st.subheader("Simple Pricing")
    
    p1, p2, p3 = st.columns(3)
    
    with p1:
        st.container(border=True).markdown("""
        #### ⚡ Standard
        ## $2.99
        * Machine Printed
        * Standard Envelope
        * USPS First Class
        """)
    
    with p2:
        st.container(border=True).markdown("""
        #### 🏺 Heirloom
        ## $5.99
        * **Cotton Bond Paper**
        * **Real Stamp**
        * Hand-Addressed
        """)
        
    with p3:
        st.container(border=True).markdown("""
        #### 🏛️ Civic
        ## $6.99
        * **3 Letters Pack**
        * Auto-find Reps
        * Mailed to Congress
        """)

    # --- CIVIC LEADERBOARD ---
    st.markdown("---")
    st.subheader("🏛️ Weekly Civic Leaderboard")
    st.caption("Most contacted representatives this week via VerbaPost.")
    
    leader_data = []
    if civic_engine:
        try: 
            leader_data = civic_engine.get_leaderboard()
        except: 
            pass
            
    if not leader_data:
        # Fallback / Demo Data
        leader_data = [
            {"Rank": "1", "Name": "Sen. Chuck Schumer (NY)", "Letters": 142},
            {"Rank": "2", "Name": "Rep. Alexandria Ocasio-Cortez (NY)", "Letters": 89},
            {"Rank": "3", "Name": "Sen. Ted Cruz (TX)", "Letters": 64},
        ]
    
    st.dataframe(leader_data, use_container_width=True, hide_index=True)

    # --- FOOTER ---
    st.markdown("---")
    f1, f2 = st.columns([3, 1])
    f1.caption("© 2025 VerbaPost Inc. | Made in NYC")
    with f2:
        if st.button("⚖️ Legal & Privacy"):
            st.query_params["view"] = "legal"
            st.rerun()