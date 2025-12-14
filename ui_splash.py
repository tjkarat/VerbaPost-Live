import streamlit as st
try: import civic_engine
except: civic_engine = None

def render_splash():
    st.markdown("""
    <div style="text-align: center; padding: 60px 0 30px 0;">
        <h1 style="font-size: 3.5rem; margin-bottom: 10px; color: #333;">📮 VerbaPost</h1>
        <p style="font-size: 1.4em; color: #555;">Real letters, sent from your screen.</p>
    </div>
    """, unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    label = f"🚀 Continue ({st.session_state.user_email.split('@')[0]})" if st.session_state.get("authenticated") else "🚀 Start a Letter"

    with c1:
        if st.button(label, type="primary", use_container_width=True):
            if st.session_state.get("authenticated"):
                st.session_state.app_mode = "workspace"
                if "view" in st.query_params: del st.query_params["view"]
            else:
                # FORCE ROUTER TO SWITCH
                st.query_params["view"] = "login" 
            st.rerun()
            
    with c2:
        if st.button("🕯️ Legacy Service", use_container_width=True):
            st.query_params["view"] = "legacy"
            st.rerun()

    st.write("---")
    
    # FEATURES
    c1, c2, c3 = st.columns(3)
    c1.markdown("### 🎙️ Speak\nJust talk. AI transcribes/polishes.")
    c2.markdown("### 📄 Print\nPremium paper, folded & enveloped.")
    c3.markdown("### 📬 Send\nUSPS First Class or Certified.")
    
    st.write("---")
    
    # PRICING
    p1, p2, p3 = st.columns(3)
    p1.markdown("**Standard**\n### $2.99"); p2.markdown("**Heirloom**\n### $5.99"); p3.markdown("**Legacy**\n### $15.99")

    # LEADERBOARD
    st.write("---"); st.subheader("🏛️ Civic Leaderboard")
    data = []
    if civic_engine: 
        try: data = civic_engine.get_weekly_stats()
        except: pass
    if not data:
        data = [{"Rank": 1, "Name": "Sen. Schumer", "Letters": 142}, {"Rank": 2, "Name": "Rep. AOC", "Letters": 89}]
    st.dataframe(data, use_container_width=True, hide_index=True)
    
    # FOOTER
    st.write("---")
    f1, f2 = st.columns([3, 1])
    f1.caption("© 2025 VerbaPost | v4.0")
    with f2:
        if st.button("⚖️ Legal"): 
            st.query_params["view"] = "legal"
            st.rerun()