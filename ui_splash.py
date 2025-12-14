import streamlit as st

def show_splash():
    # --- CSS STYLING ---
    st.markdown("""
    <style>
    /* Force the container to be wider than standard Streamlit text */
    .splash-container {
        text-align: center;
        width: 100%;
        padding: 2rem 1rem;
        background-color: white;
        margin-top: -30px; /* Pull it up higher */
    }
    
    .splash-title {
        /* FLUID TYPOGRAPHY: shrinking font for mobile */
        font-size: clamp(2rem, 8vw, 4rem); 
        font-weight: 800;
        color: #212529;
        line-height: 1.1;
        white-space: nowrap; /* Keep on one line if possible */
        margin-bottom: 0.5rem;
    }
    
    .splash-subtitle {
        font-size: clamp(0.9rem, 3vw, 1.4rem); /* Responsive subtitle */
        font-weight: 700;
        color: #FF4B4B; 
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 1rem;
    }
    
    .splash-text {
        font-size: 1.1rem;
        color: #555;
        font-style: italic;
        margin-bottom: 2rem;
        max-width: 700px;
        margin-left: auto;
        margin-right: auto;
        line-height: 1.5;
    }
    
    /* Mobile-specific adjustments */
    @media (max-width: 640px) {
        .splash-title {
            white-space: normal; /* Allow wrap on TINY screens if needed */
        }
    }
    </style>
    """, unsafe_allow_html=True)

    # --- HEADER SECTION ---
    # The text is hardcoded here exactly as requested
    st.markdown("""
    <div class="splash-container">
        <div class="splash-title">📮 VerbaPost</div>
        <div class="splash-subtitle">Texts are trivial, emails ignored, REAL MAIL GETS READ.</div>
        <div class="splash-text">
            Don't know how to start, what to write? 
            Speak it first and we'll transcribe.
        </div>
    </div>
    """, unsafe_allow_html=True)

    # --- ACTION BUTTONS ---
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        # Main Call to Action
        if st.button("🚀 Start a Letter", type="primary", use_container_width=True):
            if st.session_state.get("authenticated"):
                st.session_state.app_mode = "store"
            else:
                st.query_params["view"] = "login"
            st.rerun()

        st.write("") # Spacer

        # Legacy Service Link
        if st.button("🕊️ Legacy Service (End of Life)", use_container_width=True):
            st.query_params["view"] = "legacy"
            st.rerun()

    st.markdown("---")

    # --- VALUE PROPS ---
    c_a, c_b, c_c = st.columns(3)
    with c_a:
        st.markdown("### 🎙️ Speak")
        st.caption("Dictate your letter. AI transcribes and polishes it to perfection.")
    with c_b:
        st.markdown("### 📄 Print")
        st.caption("We print on premium 24lb paper, fold, and envelope it for you.")
    with c_c:
        st.markdown("### 📬 Send")
        st.caption("Mailed via USPS First Class or Certified Mail. No stamps needed.")

    # --- FOOTER ---
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.caption("VerbaPost v3.2.2 | Secure. Private. Real.")