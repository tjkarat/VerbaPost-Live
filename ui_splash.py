import streamlit as st

def show_splash():
    # --- BLUE HERO SECTION ---
    st.markdown("""
    <div style="background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); 
                padding: 60px; border-radius: 15px; color: white; text-align: center; 
                margin-bottom: 40px; box-shadow: 0 10px 30px rgba(0,0,0,0.15);">
        <div style="font-size: 4rem; margin-bottom: 10px;">📮</div>
        <h1 style="font-size: 3.5rem; font-weight: 700; margin: 0; color: white; letter-spacing: -1px;">VerbaPost</h1>
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
        with st.container(border=True):
            st.markdown("### 🎙️ **1. Dictate**")
            st.write("You speak. AI types. We capture your tone perfectly.")
    with c2:
        with st.container(border=True):
            st.markdown("### ✍️ **2. Sign**")
            st.write("Sign directly on your screen. Your real signature.")
    with c3:
        with st.container(border=True):
            st.markdown("### 📮 **3. We Mail**")
            st.write("We print, fold, stamp, and mail it within 24 hours.")

    st.markdown("<br>", unsafe_allow_html=True)

    # --- USE CASES (The Missing Section) ---
    st.subheader("Why VerbaPost?")
    uc1, uc2, uc3 = st.columns(3)
    
    with uc1:
        st.info("**🏘️ Realtors & Sales**\n\nHandwritten direct mail gets 99% open rates.")
    with uc2:
        st.info("**🏛️ Civic Activists**\n\nPhysical petitions on desks get noticed.")
    with uc3:
        st.info("**🧡 Families & Inmates**\n\nDirect prison delivery. Facility compliant.")

    # --- PRICING ---
    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader("Simple Pricing")
    
    p1, p2, p3 = st.columns(3)
    p1.metric("⚡ Standard", "$2.99", "Includes Postage")
    p2.metric("🏺 Heirloom", "$5.99", "Premium Paper")
    p3.metric("🏛️ Civic Blast", "$6.99", "3 Reps (Senate/House)")