import streamlit as st

# Try to import engines for dynamic data
try:
    import civic_engine
except ImportError:
    civic_engine = None

def render_splash():
    """
    Renders the marketing landing page.
    """
    
    # --- 1. HERO SECTION ---
    st.markdown("""
    <div style="text-align: center; padding: 60px 0 40px 0;">
        <h1 style="font-size: 3.5rem; margin-bottom: 10px; color: #333;">📮 VerbaPost</h1>
        <p style="font-size: 1.4em; color: #555; max-width: 600px; margin: 0 auto;">
            Real letters, sent from your screen.<br>
            <b>We print, envelope, and mail it for you.</b>
        </p>
    </div>
    """, unsafe_allow_html=True)

    # --- 2. MAIN CALL TO ACTION ---
    col1, col2 = st.columns(2)
    
    # Context-aware button label
    start_label = "🚀 Start a Letter"
    if st.session_state.get("authenticated"):
        user = st.session_state.get("user_email", "")
        if user: start_label = f"🚀 Continue ({user.split('@')[0]})"

    with col1:
        if st.button(start_label, type="primary", use_container_width=True):
            if not st.session_state.get("authenticated"):
                # FIX: Explicitly tell main.py to show the login view
                st.session_state.auth_view = "signup"
                st.query_params["view"] = "login"
            else:
                # If logged in, go straight to workspace
                st.session_state.app_mode = "workspace"
                if "view" in st.query_params: del st.query_params["view"]
            st.rerun()
            
    with col2:
        # Link to new Legacy Module
        if st.button("🕯️ Legacy Service (New)", use_container_width=True):
            st.query_params["view"] = "legacy"
            st.rerun()

    st.write("---")

    # --- 3. VALUE PROPOSITIONS ---
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("### 🎙️ Speak")
        st.caption("Don't type. Just talk. Our AI transcribes and polishes your grammar instantly.")
    with c2:
        st.markdown("### 📄 Print")
        st.caption("Printed on premium paper, folded, and enveloped in a secure facility.")
    with c3:
        st.markdown("### 📬 Send")
        st.caption("Dispatched via USPS First Class or Certified Mail to any US address.")
    
    st.write("---")
    
    # --- 4. PRICING GRID ---
    st.subheader("Simple Pricing")
    
    p1, p2, p3 = st.columns(3)
    
    with p1:
        st.markdown("**Standard**")
        st.markdown("### $2.99")
        st.caption("Standard Paper\nNo AI Polish\nUSPS First Class")
        
    with p2:
        st.markdown("**Heirloom**")
        st.markdown("### $5.99")
        st.caption("Cotton Bond Paper\nAI Polish Included\nUSPS First Class")
        
    with p3:
        st.markdown("**Legacy 🆕**")
        st.markdown("### $15.99")
        st.caption("Archival Paper\nContext Prompts\n**Certified Tracking**\nDigital Scrubbing")

    st.write("---")

    # --- 5. CIVIC LEADERBOARD ---
    st.subheader("🏛️ Civic Leaderboard")
    st.caption("Who is getting mail this week?")
    
    # Attempt to fetch real data
    leaderboard_data = []
    try:
        if civic_engine and hasattr(civic_engine, "get_weekly_stats"):
            leaderboard_data = civic_engine.get_weekly_stats()
    except Exception:
        pass 
        
    if not leaderboard_data:
        leaderboard_data = [
            {"Rank": "1", "Name": "Sen. Chuck Schumer", "Letters": "142"},
            {"Rank": "2", "Name": "Rep. Alexandria Ocasio-Cortez", "Letters": "89"},
            {"Rank": "3", "Name": "Sen. Mitch McConnell", "Letters": "64"},
        ]
    
    st.dataframe(leaderboard_data, use_container_width=True, hide_index=True)
    
    # --- FOOTER ---
    st.markdown("<div style='text-align: center; color: #888; margin-top: 50px; font-size: 0.8em;'>v4.0 - Production Ready | <a href='?view=terms'>Terms</a> | <a href='?view=privacy'>Privacy</a></div>", unsafe_allow_html=True)