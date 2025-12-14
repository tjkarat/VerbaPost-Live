import streamlit as st

def show_splash():
    # --- CSS STYLING (Mobile Optimized) ---
    st.markdown("""
    <style>
    /* 1. Force banner width to 100% and remove default padding constraints */
    .splash-container {
        width: 100vw !important;
        position: relative;
        left: 50%;
        right: 50%;
        margin-left: -50vw;
        margin-right: -50vw;
        background-color: #ffffff;
        padding: 2rem 1rem;
        text-align: center;
        margin-top: -60px; /* Pull to top of page */
    }
    
    /* 2. Responsive Logo Title */
    .splash-title {
        font-size: clamp(2.5rem, 6vw, 4.5rem) !important; /* Resizes with screen */
        font-weight: 900;
        color: #212529;
        line-height: 1.0;
        white-space: nowrap; /* CRITICAL: Forces one line */
        margin-bottom: 0.5rem;
    }
    
    /* 3. Punchy Subtitle */
    .splash-subtitle {
        font-size: clamp(0.9rem, 2.5vw, 1.3rem) !important;
        font-weight: 700;
        color: #FF4B4B; 
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 0.5rem;
    }
    
    /* 4. Descriptive Text */
    .splash-text {
        font-size: 1.1rem;
        color: #333;
        font-style: italic;
        margin-bottom: 2rem;
        max-width: 600px;
        margin-left: auto;
        margin-right: auto;
        padding: 0 10px;
    }
    </style>
    """, unsafe_allow_html=True)

    # --- CONTENT ---
    st.markdown("""
    <div class="splash-container">
        <div class="splash-title">📮 VerbaPost</div>
        <div class="splash-subtitle">Texts are trivial, emails ignored<br>REAL MAIL GETS READ.</div>
        <div class="splash-text">
            Don't know how to start, what to write?<br>
            Speak it first and we'll transcribe.
        </div>
    </div>
    """, unsafe_allow_html=True)

    # --- BUTTONS ---
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        if st.button("🚀 Start a Letter", type="primary", use_container_width=True):
            if st.session_state.get("authenticated"):
                st.session_state.app_mode = "store"
            else:
                st.query_params["view"] = "login"
            st.rerun()

        st.write("") 
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