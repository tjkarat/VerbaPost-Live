import streamlit as st

def show_splash():
    # --- CSS FORCE WHITE TEXT FOR HERO ---
    st.markdown("""
    <style>
    #splash-hero h1, #splash-hero div, #splash-hero p {
        color: #FFFFFF !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # --- HERO SECTION ---
    st.markdown("""
    <div id="splash-hero" style="background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); 
                padding: 60px; border-radius: 15px; text-align: center; 
                margin-bottom: 40px; box-shadow: 0 10px 30px rgba(0,0,0,0.15);">
        <div style="font-size: 4rem; margin-bottom: 10px;">📮</div>
        <h1 style="font-size: 3.5rem; font-weight: 700; margin: 0; letter-spacing: -1px;">VerbaPost</h1>
        <p style="font-size: 1.5rem; font-weight: 400; opacity: 0.95; margin-top: 10px;">
            Turn your voice into a real, physical letter.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # --- CALL TO ACTION ---
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        if st.button("🚀 Log In / Create Account", type="primary", use_container_width=True):
            st.session_state.current_view = "login"
            st.rerun()
            
    st.markdown("<br><br>", unsafe_allow_html=True)

    # --- FEATURES ---
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("### 🎙️ **1. Dictate**")
        st.write("You speak. AI types. We capture your tone perfectly.")
    with c2:
        st.markdown("### ✍️ **2. Sign**")
        st.write("Sign directly on your screen. Your real signature.")
    with c3:
        st.markdown("### 📮 **3. We Mail**")
        st.write("We print, fold, stamp, and mail it within 24 hours.")

    st.markdown("<br><br>", unsafe_allow_html=True)

    # --- USE CASES (Was Missing) ---
    st.subheader("Who is this for?")
    uc1, uc2, uc3 = st.columns(3)
    
    with uc1:
        st.info("**🏘️ Realtors & Sales**\n\nHandwritten direct mail gets 99% open rates. Instant follow-up.")
    with uc2:
        st.info("**🏛️ Civic Activists**\n\nPhysical petitions on desks get noticed. Emails get deleted.")
    with uc3:
        st.info("**🧡 Families & Inmates**\n\nDirect prison delivery. Facility compliant. No stamps needed.")

    st.markdown("<br><hr>", unsafe_allow_html=True)

    # --- FOOTER / TERMS OF SERVICE ---
    fc1, fc2, fc3 = st.columns([1, 2, 1])
    with fc2:
        if st.button("📜 Read Terms of Service & Privacy Policy", type="secondary", use_container_width=True):
            st.session_state.current_view = "legal"
            st.rerun()
        st.markdown("<div style='text-align: center; color: #888;'>© 2024 VerbaPost</div>", unsafe_allow_html=True)