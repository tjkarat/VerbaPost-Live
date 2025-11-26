import streamlit as st
import os

def set_mode(mode):
    st.session_state.app_mode = mode

def show_splash():
    # --- 1. LOGO HANDLING ---
    # If you upload a file named 'logo.png', it will appear here.
    c_logo = st.container()
    if os.path.exists("logo.png"):
        with c_logo:
            c1, c2, c3 = st.columns([1, 1, 1])
            with c2:
                st.image("logo.png", use_container_width=True)
    
    # --- 2. HERO BANNER ---
    # This acts as the text logo if no image is found
    st.markdown("""
    <div class="hero-banner">
        <div class="hero-title">VerbaPost 📮</div>
        <div class="hero-subtitle">Turn your voice into a real letter.</div>
        <p style="margin-top: 20px; font-size: 1.1rem; opacity: 0.9;">
            Texts are trivial. Emails are ignored. <b>Real letters get read.</b>
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # --- 3. MAIN CTA ---
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        if st.button("🔐 Log In / Sign Up to Start", type="primary", use_container_width=True):
            set_mode("login")
            st.rerun()

    st.divider()
    
    # --- 4. FEATURES ---
    c1, c2, c3 = st.columns(3)
    with c1: st.markdown("### 🎙️ 1. Dictate"); st.caption("You speak. AI types.")
    with c2: st.markdown("### ✍️ 2. Sign"); st.caption("Sign on your screen.")
    with c3: st.markdown("### 📮 3. We Mail"); st.caption("Printed, stamped, & sent.")

    st.divider()
    
    # --- 5. USE CASES (Including Santa) ---
    st.subheader("Why VerbaPost?")
    u1, u2, u3 = st.columns(3)
    
    with u1:
        with st.container(border=True):
            st.write("**🎅 Letter from Santa**")
            st.caption("Surprise a child with a letter mailed directly from the North Pole!")

    with u2:
        with st.container(border=True):
            st.write("**🗳️ Civic Activists**")
            st.caption("Write to Congress. Physical petitions get noticed.")

    with u3:
        with st.container(border=True):
            st.write("**🏡 Realtors & Sales**")
            st.caption("Handwritten direct mail. High open rates. Instant follow-up.")

    st.divider()

    # --- 6. PRICING ---
    st.subheader("Pricing")
    p1, p2, p3, p4 = st.columns(4)

    with p1:
        with st.container(border=True):
            st.metric(label="⚡ Standard", value="$2.99")
            st.caption("Machine Postage")

    with p2:
        with st.container(border=True):
            st.metric(label="🏺 Heirloom", value="$5.99")
            st.caption("Real Stamp")

    with p3:
        with st.container(border=True):
            st.metric(label="🏛️ Civic", value="$6.99")
            st.caption("3 Letters to Congress")

    with p4:
        with st.container(border=True):
            st.metric(label="🎅 Santa", value="$9.99")
            st.caption("North Pole Address")

    st.markdown("---")
    
    # --- 7. FOOTER ---
    f1, f2 = st.columns([4, 1])
    with f2:
        if st.button("Legal / Terms", type="secondary"):
            set_mode("legal")
            st.rerun()