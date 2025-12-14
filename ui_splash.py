import streamlit as st

def show_splash():
    # --- CSS STYLING ---
    st.markdown("""
    <style>
    .splash-container {
        text-align: center;
        width: 100%;
        padding: 1rem 0 2rem 0;
    }
    .splash-title {
        font-size: 2.8rem; /* Smaller to fit mobile */
        font-weight: 800;
        margin-bottom: 0;
        color: #212529;
        white-space: nowrap; /* Forces single line */
        line-height: 1.2;
    }
    .splash-subtitle {
        font-size: 1.25rem;
        font-weight: 700;
        color: #FF4B4B; /* Streamlit Red for emphasis */
        margin-top: 10px;
        margin-bottom: 5px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .splash-text {
        font-size: 1.1rem;
        color: #555;
        font-style: italic;
        margin-bottom: 30px;
        max-width: 600px;
        margin-left: auto;
        margin-right: auto;
    }
    </style>
    """, unsafe_allow_html=True)

    # --- HEADER SECTION ---
    st.markdown("""
    <div class="splash-container">
        <div class="splash-title">📮 VerbaPost</div>
        <div class="splash-subtitle">Texts are trivial, emails ignored, REAL MAIL GETS READ.</div>
        <div class="splash-text">Don't know how to start, what to write? Speak it first and we'll transcribe.</div>
    </div>
    """, unsafe_allow_html=True)

    # --- ACTION BUTTONS ---
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        # Main Call to Action
        if st.button("🚀 Start a Letter", type="primary", use_container_width=True):
            # Check auth state to determine routing
            if st.session_state.get("authenticated"):
                st.session_state.app_mode = "store"
            else:
                st.query_params["view"] = "login"  # Route to login/signup
            st.rerun()

        st.write("") # Spacer

        # Legacy / End of Life Service
        if st.button("🕊️ Legacy Service (End of Life)", use_container_width=True):
            st.query_params["view"] = "legacy"
            st.rerun()

    st.markdown("---")

    # --- VALUE PROPS (Keeping the icons) ---
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
    st.caption("VerbaPost v3.2.1 | Secure. Private. Real.")