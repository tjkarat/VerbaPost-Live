import streamlit as st
import os

def set_mode(mode):
    st.session_state.app_mode = mode
    st.rerun()

def show_splash():
    # --- SEO HIDDEN BLOCK ---
    st.markdown("""
    <div style="display:none;">
    <h1>VerbaPost: Send Physical Mail from Audio</h1>
    <p>Convert dictation to snail mail. Send Santa letters, write to Congress, 
    or mail heirloom letters with real stamps. The easiest way to send real letters online.</p>
    </div>
    """, unsafe_allow_html=True)

    # --- 1. HERO ---
    if os.path.exists("logo.png"):
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2: st.image("logo.png", use_container_width=True)
    
    st.markdown("""
    <div style="text-align: center; margin-bottom: 30px;">
        <h1 style="color: #1e3c72 !important; font-size: 2.5rem;">Turn voice into real mail.</h1>
        <p style="color: #555; font-size: 1.2rem;">Texts are trivial. Emails are ignored.<br><b>REAL LETTERS GET OPENED.</b></p>
    </div>
    """, unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        if st.button("🚀 Get Started", type="primary", use_container_width=True):
            set_mode("login")

    st.divider()

    # --- 2. HOW IT WORKS ---
    st.subheader("How it Works")
    c1, c2, c3 = st.columns(3)
    with c1: 
        st.markdown("### 🎙️ 1. Dictate")
        st.info("Speak naturally. Our AI cleans up 'ums' and 'uhs' and formats your letter perfectly.")
    with c2: 
        st.markdown("### ✍️ 2. Sign")
        st.info("Draw your signature on screen. We place it on the physical document.")
    with c3: 
        st.markdown("### 📮 3. We Mail")
        st.info("We print, envelope, stamp, and mail your letter via USPS First Class.")

    st.divider()
    
    # --- 3. USE CASES ---
    st.subheader("Choose Your Letter")
    u1, u2, u3 = st.columns(3)
    with u1:
        with st.container(border=True):
            st.write("🎅 **Santa Mail**")
            st.caption("Postmarked from North Pole. Includes nice background.")
    with u2:
        with st.container(border=True):
            st.write("🗳️ **Civic Action**")
            st.caption("We find your Reps based on your address and mail them all.")
    with u3:
        with st.container(border=True):
            st.write("🏺 **Heirloom**")
            st.caption("Thick paper, wet-ink style font, real physical stamp.")

    st.markdown("---")
    f1, f2 = st.columns([4, 1])
    with f2:
        if st.button("Legal / Terms", type="secondary"):
            set_mode("legal")