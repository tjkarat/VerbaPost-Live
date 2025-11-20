import streamlit as st

# Version 7.0 - Native Metric + CSS Styling (The Stable Fix)
def show_splash():
    # --- CSS INJECTION TO STYLE METRICS AS CARDS ---
    st.markdown("""
        <style>
        /* 1. Make Metric Value Red and Sized Correctly */
        [data-testid="stMetricValue"] {
            color: #E63946 !important; 
            font-size: 2.0rem !important;
        }
        /* 2. Custom Card Styling (Achieve the background/border look) */
        .price-card-style {
            padding: 15px;
            border-radius: 10px;
            text-align: center;
            height: 100%;
        }
        .standard-bg { background-color: #f9f9f9; border: 1px solid #ddd;}
        .heirloom-bg { background-color: #f0fff4; border: 2px solid #4CAF50;}
        .civic-bg { background-color: #fff8e1; border: 1px solid #ddd;}
        /* 3. Ensure columns fill height */
        [data-testid="stColumn"] {
            display: flex;
            flex-direction: column;
        }
        </style>
        """, unsafe_allow_html=True)
    
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
        st.caption("Tap the mic. AI handles the typing.")
    with c2:
        st.markdown("✍️ **2. Sign**")
        st.caption("Review the text, sign your name on screen.")
    with c3:
        st.markdown("📮 **3. We Mail**")
        st.caption("We print, stamp, and mail it.")

    st.divider()

    # --- PRICING TIERS (NATIVE STREAMLIT + CSS STYLING) ---
    st.subheader("Simple Pricing")

    col1, col2, col3 = st.columns(3)

    # STANDARD CARD
    with col1:
        st.markdown('<div class="price-card-style standard-bg">', unsafe_allow_html=True)
        st.markdown('### ⚡ Standard')
        st.metric(label="Cost", value="$2.99", label_visibility="collapsed")
        st.caption("API Fulfillment • Window Envelope • Mailed in 24hrs")
        st.markdown('</div>', unsafe_allow_html=True)

    # HEIRLOOM CARD
    with col2:
        st.markdown('<div class="price-card-style heirloom-bg">', unsafe_allow_html=True)
        st.markdown('### 🏺 Heirloom')
        st.metric(label="Cost", value="$5.99", label_visibility="collapsed")
        st.caption("Hand-Stamped • Premium Paper • Mailed from Nashville, TN")
        st.markdown('</div>', unsafe_allow_html=True)

    # CIVIC CARD
    with col3:
        st.markdown('<div class="price-card-style civic-bg">', unsafe_allow_html=True)
        st.markdown('### 🏛️ Civic Blast')
        st.metric(label="Cost", value="$6.99", label_visibility="collapsed")
        st.caption("Activism Mode • Auto-Find Reps • Mails Senate + House")
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.divider()

    # --- CTA ---
    col_spacer, col_btn, col_spacer2 = st.columns([1, 2, 1])
    with col_btn:
        if st.button("🚀 Create My Account", type="primary", use_container_width=True):
            st.session_state.current_view = "login"
            st.session_state.initial_mode = "signup"
            st.rerun()
        
        st.write("")
        
        if st.button("Already a member? Log In", type="secondary", use_container_width=True):
            st.session_state.current_view = "login"
            st.session_state.initial_mode = "login"
            st.rerun()