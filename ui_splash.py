import streamlit as st

def show_splash():
    # --- LAZY IMPORT (Fixes KeyError) ---
    import analytics
    import promo_engine # Only if you need promo logic here, otherwise remove
    # ------------------------------------

    # 1. INJECT ANALYTICS
    analytics.inject_ga()

    # --- HERO ---
    st.markdown("""
    <div style="text-align: center; padding-bottom: 20px;">
        <h1 style="margin-bottom:0;">VerbaPost 📮</h1>
        <h3 style="font-weight:normal; margin-top:0;">Turn your voice into a real letter.</h3>
        <p style="font-size:18px; color:#666;">
            Texts are trivial. Emails are ignored. <b>Real letters get read.</b>
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    st.divider()

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
    
    # --- USE CASES (REORDERED) ---
    st.subheader("Why VerbaPost?")
    
    u1, u2, u3 = st.columns(3)
    
    # LEFT: Realtors
    with u1:
        with st.container(border=True):
            st.write("**🏡 Realtors & Sales**")
            st.caption("Handwritten direct mail. High open rates. Instant follow-up.")

    # MIDDLE: Civic
    with u2:
        with st.container(border=True):
            st.write("**🗳️ Civic Activists**")
            st.caption("Write to Congress. Physical petitions get noticed.")

    # RIGHT: Families
    with u3:
        with st.container(border=True):
            st.write("**🧡 Families & Inmates**")
            st.caption("Direct prison delivery. Facility compliant. No stamps required.")

    st.divider()

    # --- PRICING ---
    st.subheader("Pricing")
    
    st.markdown("""
    <style>
        [data-testid="stMetricValue"] {
            font-size: 2.2rem !important;
            color: #E63946 !important;
        }
    </style>
    """, unsafe_allow_html=True)

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

    # --- CTA ---
    col_spacer, col_btn, col_spacer2 = st.columns([1, 2, 1])
    with col_btn:
        if st.button("🚀 Create My Account", type="primary", use_container_width=True):
            st.session_state.current_view = "login"
            st.session_state.initial_mode = "signup"
            st.rerun()
        
        st.write("")
        if st.button("Log In", type="secondary", use_container_width=True):
            st.session_state.current_view = "login"
            st.session_state.initial_mode = "login"
            st.rerun()

    # --- LEGAL FOOTER ---
    st.markdown("---")
    f1, f2, f3 = st.columns([1, 2, 1])
    with f2:
        st.caption("© 2025 VerbaPost LLC")
        if st.button("⚖️ Privacy Policy & Terms of Service", type="secondary", use_container_width=True):
            st.session_state.current_view = "legal"
            st.rerun()