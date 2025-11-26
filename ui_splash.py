import streamlit as st
import os

def set_mode(mode):
    st.session_state.app_mode = mode

def show_splash():
    # --- 1. LOGO (Bigger) ---
    if os.path.exists("logo.png"):
        c1, c2, c3 = st.columns([1, 2, 1])  # Wider middle column = Bigger logo
        with c2:
            st.image("logo.png", use_container_width=True)
    
    st.markdown("""
    <div style="text-align: center; margin-bottom: 30px;">
        <h3 style="color: #2d3748;">Turn your voice into a real letter.</h3>
        <p style="color: #555;">Texts are trivial. Emails are ignored.<br><b>REAL LETTERS GET OPENED.</b></p>
    </div>
    """, unsafe_allow_html=True)
    
    # ... (Rest of splash logic same as previous) ...
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        if st.button("🔐 Log In / Sign Up to Start", type="primary", use_container_width=True):
            st.session_state.app_mode = "login"
            st.rerun()

    st.divider()
    c1, c2, c3 = st.columns(3)
    with c1: st.markdown("### 🎙️ 1. Dictate"); st.caption("You speak. AI types.")
    with c2: st.markdown("### ✍️ 2. Sign"); st.caption("Sign on your screen.")
    with c3: st.markdown("### 📮 3. We Mail"); st.caption("Printed, stamped, & sent.")

    st.divider()
    
    # Use Cases (Including Santa)
    st.subheader("Why VerbaPost?")
    u1, u2, u3 = st.columns(3)
    with u1:
        with st.container(border=True):
            st.write("**🎅 Letter from Santa**")
            st.caption("Directly from the North Pole!")
    with u2:
        with st.container(border=True):
            st.write("**🗳️ Civic Activists**")
            st.caption("Write to Congress.")
    with u3:
        with st.container(border=True):
            st.write("**🏡 Realtors & Sales**")
            st.caption("Handwritten direct mail.")

    st.divider()
    st.subheader("Pricing")
    p1, p2, p3, p4 = st.columns(4)
    with p1: st.container(border=True).metric("⚡ Standard", "$2.99", "Machine")
    with p2: st.container(border=True).metric("🏺 Heirloom", "$5.99", "Real Stamp")
    with p3: st.container(border=True).metric("🏛️ Civic", "$6.99", "3 Letters")
    with p4: st.container(border=True).metric("🎅 Santa", "$9.99", "North Pole")

    st.markdown("---")
    f1, f2 = st.columns([4, 1])
    with f2:
        if st.button("Legal / Terms", type="secondary"):
            set_mode("legal")
            st.rerun()