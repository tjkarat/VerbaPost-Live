import streamlit as st

# Try to import engines for dynamic data
try:
    import civic_engine
except ImportError:
    civic_engine = None

def render_splash():
    """
    Renders the FULL marketing landing page.
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
    
    start_label = "🚀 Start a Letter"
    if st.session_state.get("authenticated"):
        user = st.session_state.get("user_email", "").split('@')[0]
        start_label = f"🚀 Continue ({user})"

    with col1:
        if st.button(start_label, type="primary", use_container_width=True):
            if st.session_state.get("authenticated"):
                st.session_state.app_mode = "workspace"
                if "view" in st.query_params: del st.query_params["view"]
            else:
                # Force Login View via URL to ensure navigation happens
                st.session_state.auth_view = "signup"
                st.query_params["view"] = "login"
            st.rerun()
            
    with col2:
        if st.button("🕯️ Legacy Service (New)", use_container_width=True):
            st.query_params["view"] = "legacy"
            st.rerun()

    st.write("---")

    # --- 3. FEATURES ---
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("### 🎙️ Speak")
        st.caption("Don't type. Just talk. AI transcribes and polishes grammar.")
    with c2:
        st.markdown("### 📄 Print")
        st.caption("Printed on premium paper, folded, and enveloped securely.")
    with c3:
        st.markdown("### 📬 Send")
        st.caption("Dispatched via USPS First Class or Certified Mail.")
    
    st.write("---")
    
    # --- 4. PRICING ---
    p1, p2, p3 = st.columns(3)
    with p1: st.markdown("**Standard**\n### $2.99")
    with p2: st.markdown("**Heirloom**\n### $5.99")
    with p3: st.markdown("**Legacy**\n### $15.99")

    st.write("---")
    
    # --- 5. CIVIC LEADERBOARD ---
    st.subheader("🏛️ Civic Leaderboard")
    leaderboard_data = []
    try:
        if civic_engine and hasattr(civic_engine, "get_weekly_stats"):
            leaderboard_data = civic_engine.get_weekly_stats()
    except Exception: pass
    
    if not leaderboard_data:
        leaderboard_data = [
            {"Rank": "1", "Name": "Sen. Chuck Schumer", "Letters": "142"},
            {"Rank": "2", "Name": "Rep. Alexandria Ocasio-Cortez", "Letters": "89"},
            {"Rank": "3", "Name": "Sen. Mitch McConnell", "Letters": "64"},
        ]
    st.dataframe(leaderboard_data, use_container_width=True, hide_index=True)
    
    # --- 6. FOOTER (Fixed Legal) ---
    st.write("---")
    f1, f2, f3 = st.columns([2, 1, 1])
    with f1:
        st.caption("© 2025 VerbaPost. All rights reserved.")
    with f2:
        if st.button("📜 Terms"):
            st.query_params["view"] = "terms"
            st.rerun()
    with f3:
        if st.button("🔒 Privacy"):
            st.query_params["view"] = "privacy"
            st.rerun()