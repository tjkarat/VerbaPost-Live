import streamlit as st

def render_splash_page():
    """
    The 'Glass Door' Entry Point.
    Transparency First: Shows Process & Pricing before Login.
    """
    # --- STYLING ---
    st.markdown("""
    <style>
        .hero-title { font-family: serif; color: #0f172a; font-size: 3rem; text-align: center; margin-bottom: 0; }
        .hero-sub { color: #64748b; font-size: 1.2rem; text-align: center; margin-top: 5px; margin-bottom: 30px; }
        .step-card { background: #f8fafc; padding: 20px; border-radius: 10px; border: 1px solid #e2e8f0; height: 100%; }
        .price-card { background: #ffffff; padding: 25px; border-radius: 12px; border: 2px solid #0f172a; text-align: center; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); }
        .cta-btn { margin-top: 15px; }
    </style>
    """, unsafe_allow_html=True)

    # --- 1. HERO SECTION ---
    st.markdown("<h1 class='hero-title'>VerbaPost</h1>", unsafe_allow_html=True)
    st.markdown("<p class='hero-sub'>The Family Legacy Archive</p>", unsafe_allow_html=True)
    
    st.markdown(
        "<div style='text-align: center; max-width: 700px; margin: 0 auto 40px auto;'>"
        "We interview your parents over the phone, transcribe their stories, and mail you "
        "a physical manuscript on archival linen paper for your family archive."
        "</div>", 
        unsafe_allow_html=True
    )

    # --- 2. HOW IT WORKS (3 COLUMNS) ---
    st.subheader("How it Works")
    c1, c2, c3 = st.columns(3)
    
    with c1:
        st.markdown("""
        <div class='step-card'>
            <h3>1. Setup</h3>
            <p><strong>The Family</strong> creates an account and enters the interviewee's phone number. You choose the specific question you want our Biographer to ask, send a prep email, and trigger the call when ready.</p>
        </div>
        """, unsafe_allow_html=True)
        
    with c2:
        st.markdown("""
        <div class='step-card'>
            <h3>2. The Call</h3>
            <p><strong>VerbaPost</strong> calls your loved one immediately. Our AI Biographer conducts a warm interview, asking the specific question you selected in Step 1.</p>
        </div>
        """, unsafe_allow_html=True)
        
    with c3:
        st.markdown("""
        <div class='step-card'>
            <h3>3. The Keepsake</h3>
            <p><strong>The Archive</strong> is created. You edit the transcript online, and we mail the final story on elegant linen paper, enclosed in a linen envelope with a vintage stamp.</p>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    # --- 3. PRICING & PORTALS ---
    st.subheader("Select Your Portal")
    
    col_family, col_advisor = st.columns(2)
    
    # === FAMILY PORTAL ===
    with col_family:
        st.info("🏠 **For Families**")
        st.markdown("""
        **Sponsored Access**
        * Access your private vault
        * Edit and approve transcripts
        * Order additional interviews
        """)
        if st.button("🔐 Family Login / Sign Up", key="btn_heir_login", use_container_width=True):
            st.query_params["nav"] = "login"
            st.rerun()

    # === ADVISOR PORTAL ===
    with col_advisor:
        st.warning("💼 **For Wealth Advisors**")
        st.markdown("""
        **Cost:** $99 per Client (Lifetime Access)
        * **Includes:** 1 Interview + Fulfillment
        * Physical Linen Letter & Postage
        * White-labeled branding
        """)
        if st.button("💼 Advisor Portal Access", key="btn_adv_login", use_container_width=True):
            st.query_params["nav"] = "advisor"
            st.rerun()

    st.markdown("---")
    
    # --- 4. FOOTER ---
    st.markdown("""
        <div style='text-align: center; color: #94a3b8; font-size: 0.8rem; margin-top: 20px;'>
            © 2026 VerbaPost
        </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    render_splash_page()