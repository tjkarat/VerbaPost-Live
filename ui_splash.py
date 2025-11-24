import streamlit as st

def set_mode(mode):
    st.session_state.app_mode = mode

def show_splash():
    import analytics
    analytics.inject_ga()

    # Hero
    st.markdown("""
    <div class="hero-banner">
        <div class="hero-title">VerbaPost 📮</div>
        <div class="hero-subtitle">Turn your voice into a real letter.</div>
        <p style="margin-top: 20px; color: white;">Texts are trivial. Real letters get read.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # CTA - Only Login/Signup now
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        st.info("Please Log In or Create an Account to begin.")
        if st.button("🔐 Log In / Sign Up", type="primary", use_container_width=True):
            set_mode("login")
            st.rerun()

    st.divider()
    
    # Features
    c1, c2, c3 = st.columns(3)
    with c1: st.markdown("### 🎙️ 1. Dictate"); st.caption("You speak. AI types.")
    with c2: st.markdown("### ✍️ 2. Sign"); st.caption("Sign on screen.")
    with c3: st.markdown("### 📮 3. We Mail"); st.caption("Printed & Stamped.")

    st.markdown("---")
    f1, f2 = st.columns([4, 1])
    with f2:
        if st.button("Legal", type="secondary"): set_mode("legal"); st.rerun()