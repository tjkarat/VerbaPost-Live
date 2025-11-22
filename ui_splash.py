import streamlit as st

# Version 15.0 - Pure Native Components (No HTML Strings)
def show_splash():
    # --- HERO ---
    st.title("VerbaPost 📮")
    st.subheader("The Authenticity Engine.")
    st.markdown("##### Texts are trivial. Emails are ignored. Real letters get read.")
    
    st.divider()

    # --- HOW IT WORKS ---
    c1, c2, c3 = st.columns(3)
    with c1:
        st.info("🎙️ **1. Dictate**")
        st.caption("Tap the mic. AI handles the typing.")
    with c2:
        st.warning("✍️ **2. Sign**")
        st.caption("Review the text, sign on screen.")
    with c3:
        st.success("📮 **3. We Mail**")
        st.caption("We print, stamp, and mail it.")

    st.divider()

    # --- PRICING TIERS (NATIVE) ---
    st.subheader("Simple Pricing")
    
    # Inject minimal CSS just for metric size/color
    st.markdown("""
    <style>
        [data-testid="stMetricValue"] {
            font-size: 2.5rem !important;
            color: #E63946 !important;
        }
    </style>
    """, unsafe_allow_html=True)

    p1, p2, p3 = st.columns(3)

    with p1:
        with st.container(border=True):
            st.markdown("### ⚡ Standard")
            st.metric(label="Price", value="$2.99", label_visibility="collapsed")
            st.caption("API Fulfillment • Window Envelope • Mailed in 24hrs")

    with p2:
        with st.container(border=True):
            st.markdown("### 🏺 Heirloom")
            st.metric(label="Price", value="$5.99", label_visibility="collapsed")
            st.caption("Hand-Stamped • Premium Paper • Mailed from Nashville")

    with p3:
        with st.container(border=True):
            st.markdown("### 🏛️ Civic Blast")
            st.metric(label="Price", value="$6.99", label_visibility="collapsed")
            st.caption("Activism Mode • Auto-Find Reps • Mails Senate + House")

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