import streamlit as st

def show_splash():
    # --- 1. MODERN HERO SECTION (The Purple Gradient) ---
    st.markdown("""
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                padding: 60px; border-radius: 20px; color: white; text-align: center; 
                margin-bottom: 40px; box-shadow: 0 10px 30px rgba(0,0,0,0.2);">
        <div style="font-size: 4rem; margin-bottom: 10px;">📮</div>
        <h1 style="font-size: 3.5rem; font-weight: 800; margin: 0; color: white; letter-spacing: -1px;">VerbaPost</h1>
        <p style="font-size: 1.5rem; font-weight: 400; opacity: 0.95; margin-top: 10px;">
            Turn your voice into a real, physical letter.
        </p>
        <p style="font-size: 1.1rem; opacity: 0.8; font-style: italic; margin-top: 5px;">
            "Texts are trivial. Emails are ignored. Real letters get read."
        </p>
    </div>
    """, unsafe_allow_html=True)

    # --- 2. CALL TO ACTION ---
    # Centered, large button
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        # NOTE: We use st.rerun() here to force the main.py router to pick up the change immediately
        if st.button("🚀 Log In / Create Account", type="primary", use_container_width=True):
            st.session_state.current_view = "login"
            st.rerun()
            
    st.markdown("<br><br>", unsafe_allow_html=True)

    # --- 3. FEATURE CARDS ---
    c1, c2, c3 = st.columns(3)
    
    with c1:
        with st.container(border=True):
            st.markdown("### 🎙️ **1. Dictate**")
            st.write("You speak. AI types. No typing required. We capture your tone perfectly.")

    with c2:
        with st.container(border=True):
            st.markdown("### ✍️ **2. Sign**")
            st.write("Sign directly on your screen. Your real signature goes on the paper.")

    with c3:
        with st.container(border=True):
            st.markdown("### 📮 **3. We Mail**")
            st.write("We print, fold, stamp, and mail it within 24 hours. Standard or Premium.")

    st.markdown("<br>", unsafe_allow_html=True)

    # --- 4. USE CASES ---
    st.subheader("Why VerbaPost?")
    uc1, uc2, uc3 = st.columns(3)
    
    with uc1:
        st.info("**🏘️ Realtors & Sales**\n\nHandwritten direct mail gets 99% open rates. Instant follow-up after meetings.")
    with uc2:
        st.info("**🏛️ Civic Activists**\n\nWrite to Congress. Physical petitions on desks get noticed; emails get deleted.")
    with uc3:
        st.info("**🧡 Families & Inmates**\n\nDirect prison delivery. Facility compliant. No stamps or envelopes needed.")

    # --- 5. PRICING SIMPLE ---
    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader("Simple Pricing")
    
    p1, p2, p3 = st.columns(3)
    p1.metric("⚡ Standard", "$2.99", "Includes Postage")
    p2.metric("🏺 Heirloom", "$5.99", "Premium Paper")
    p3.metric("🏛️ Civic Blast", "$6.99", "3 Reps (Senate/House)")