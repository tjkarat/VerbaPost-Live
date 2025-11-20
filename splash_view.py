import streamlit as st

def show_splash():
    # --- CONFIG ---
    P_STANDARD = "$2.99"
    P_HEIRLOOM = "$5.99"
    P_CIVIC = "$6.99"

    # --- HERO ---
    st.title("VerbaPost 📮")
    st.subheader("The Authenticity Engine.")
    st.markdown("##### Texts are trivial. Emails are ignored. Real letters get read.")
    
    st.divider()

    # --- HOW IT WORKS ---
    st.subheader("How it Works")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("🎙️ **1. Dictate**")
        st.caption("Tap the mic. AI handles the typing. You edit as needed.")
    with c2:
        st.markdown("✍️ **2. Sign**")
        st.caption("Sign your name on screen.")
    with c3:
        st.markdown("📮 **3. We Mail**")
        st.caption("We print, stamp, and mail it.")

    st.divider()

    # --- PRICING TIERS (NATIVE COLUMNS) ---
    st.subheader("Simple Pricing")

    col1, col2, col3 = st.columns(3)

    # STANDARD CARD
    with col1:
        with st.container(border=True):
            st.markdown("### ⚡ Standard")
            st.metric(label="Cost", value=P_STANDARD, label_visibility="collapsed")
            st.caption("API Fulfillment • Window Envelope • Mailed in 24hrs")

    # HEIRLOOM CARD
    with col2:
        with st.container(border=True):
            st.markdown("### 🏺 Heirloom")
            st.metric(label="Cost", value=P_HEIRLOOM, label_visibility="collapsed")
            st.caption("Hand-Stamped • Premium Paper • Mailed from Nashville")

    # CIVIC CARD
    with col3:
        with st.container(border=True):
            st.markdown("### 🏛️ Civic")
            st.metric(label="Cost", value=P_CIVIC, label_visibility="collapsed")
            st.caption("Activism Mode • Auto-Find Reps • Mails Senate + House")

    st.divider()

    # --- CTA ---
    col_spacer, col_btn, col_spacer2 = st.columns([1, 2, 1])
    with col_btn:
        if st.button("🚀 Start Writing Now", type="primary", use_container_width=True):
            st.session_state.current_view = "main_app"
            st.rerun()
        
        st.write("")
        
        if st.button("Already a member? Log In", type="secondary", use_container_width=True):
            st.session_state.current_view = "login"
            st.rerun()