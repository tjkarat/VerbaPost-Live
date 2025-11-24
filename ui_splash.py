import streamlit as st

def set_mode(mode):
    st.session_state.app_mode = mode

def show_splash():
    # --- LAZY IMPORT ---
    import analytics
    analytics.inject_ga()

    # --- HERO ---
    st.markdown("""
    <div class="hero-banner">
        <div class="hero-title">VerbaPost 📮</div>
        <div class="hero-subtitle">Turn your voice into a real letter.</div>
        <p style="margin-top: 20px; font-size: 1.1rem; opacity: 0.9;">
            Texts are trivial. Emails are ignored. <b>Real letters get read.</b>
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # --- HOW IT WORKS ---
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("### 🎙️ 1. Dictate")
        st.caption("You speak. AI types.")
    with c2:
        st.markdown("### ✍️ 2. Sign")
        st.caption("Sign on your screen.")
    with c3:
        st.markdown("### 📮 3. We Mail")
        st.caption("Printed, stamped, & sent.")

    st.divider()
    
    # --- USE CASES ---
    st.subheader("Why VerbaPost?")
    u1, u2, u3 = st.columns(3)
    with u1:
        with st.container(border=True):
            st.write("**🏡 Realtors & Sales**")
            st.caption("Handwritten direct mail. High open rates.")
    with u2:
        with st.container(border=True):
            st.write("**🗳️ Civic Activists**")
            st.caption("Write to Congress. Physical petitions.")
    with u3:
        with st.container(border=True):
            st.write("**🧡 Families & Inmates**")
            st.caption("Direct prison delivery. Facility compliant.")

    st.divider()

    # --- PRICING ---
    st.subheader("Pricing")
    p1, p2, p3 = st.columns(3)
    with p1:
        with st.container(border=True):
            st.metric(label="⚡ Standard", value="$2.99")
            st.caption("API Fulfillment • 24hr Speed")
    with p2:
        with st.container(border=True):
            st.metric(label="🏺 Heirloom", value="$5.99")
            st.caption("Hand-Stamped • Premium Paper")
    with p3:
        with st.container(border=True):
            st.metric(label="🏛️ Civic Blast", value="$6.99")
            st.caption("Mail Senate + House (3 Letters)")

    st.divider()

    # --- CTA (THE FIX) ---
    col_spacer, col_btn, col_spacer2 = st.columns([1, 2, 1])
    with col_btn:
        # Use on_click to force the state change immediately
        st.button(
            "🚀 Create Your First Letter", 
            type="primary", 
            use_container_width=True,
            on_click=set_mode,
            args=("store",) 
        )
        
        st.write("")
        
        st.button(
            "Log In / Account", 
            type="secondary", 
            use_container_width=True,
            on_click=set_mode,
            args=("store",)
        )

    st.markdown("---")
    f1, f2, f3 = st.columns([1, 2, 1])
    with f2:
        st.caption("© 2025 VerbaPost LLC")