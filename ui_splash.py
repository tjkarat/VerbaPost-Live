import streamlit as st

def render_splash():
    # --- HERO SECTION ---
    st.markdown("""
    <div style="text-align: center; padding: 40px 0 20px 0;">
        <h1 style="font-size: 3rem; margin-bottom: 10px;">📮 VerbaPost</h1>
        <p style="font-size: 1.3em; color: #555;">
            Real letters, sent from your screen.<br>
            <b>We print, envelope, and mail it for you.</b>
        </p>
    </div>
    """, unsafe_allow_html=True)

    # --- MAIN ACTIONS ---
    col1, col2 = st.columns(2)
    
    with col1:
        # Standard Flow
        if st.button("🚀 Start a Letter", type="primary", use_container_width=True):
            st.session_state.auth_view = "signup" 
            st.session_state.app_mode = "login" # Redirects to login/signup
            st.rerun()
            
    with col2:
        # 🆕 LEGACY PIVOT BUTTON
        if st.button("🕯️ Legacy Service", use_container_width=True):
            st.query_params["view"] = "legacy"
            st.rerun()

    st.write("---")

    # --- VALUE PROPS ---
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
    
    # --- PRICING GRID (Restored) ---
    st.subheader("Pricing")
    
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

    # --- CIVIC LEADERBOARD (Restored Placeholder) ---
    # In v3.0, this likely pulled data from civic_engine.py
    st.subheader("🏛️ Civic Leaderboard")
    st.caption("Most popular representatives messaged this week:")
    
    # Static placeholder - connect to real data if civic_engine has a 'get_stats()' method
    st.dataframe(
        [
            {"Name": "Sen. Chuck Schumer", "Letters": 142},
            {"Name": "Rep. AOC", "Letters": 89},
            {"Name": "Sen. Mitch McConnell", "Letters": 64},
        ],
        use_container_width=True,
        hide_index=True
    )
    
    st.markdown("<div style='text-align: center; color: #888; margin-top: 50px;'>v4.0 - Production Ready</div>", unsafe_allow_html=True)