import streamlit as st
import os

def set_mode(mode):
    st.session_state.app_mode = mode
    st.rerun()

def show_splash():
    # --- HERO SECTION ---
    if os.path.exists("logo.png"):
        c1, c2, c3 = st.columns([1, 1, 1])
        with c2: 
            st.image("logo.png", width=150)
    
    st.markdown("""
    <div style="text-align: center; padding-bottom: 20px;">
        <h1 style="color: #1e3c72; margin-bottom: 0;">VerbaPost</h1>
        <p style="font-size: 1.5rem; color: #555; margin-top: 5px;">
            The easiest way to send real mail.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # --- HOW IT WORKS ---
    st.markdown("### 📝 How it Works")
    step1, step2, step3 = st.columns(3)
    
    with step1:
        with st.container(border=True):
            st.markdown("#### 1. Sign Up")
            st.caption("Create a **free account**. We need this to save your drafts and store your return address.")
    
    with step2:
        with st.container(border=True):
            st.markdown("#### 2. Speak")
            st.caption("Dictate your letter using our AI, or type it out. Select a recipient or let us find your Congressperson.")
            
    with step3:
        with st.container(border=True):
            st.markdown("#### 3. We Mail")
            st.caption("We print, stamp, and mail the physical letter via USPS First Class mail.")

    st.markdown("---")

    # --- MID-PAGE CTA ---
    c_cta1, c_cta2, c_cta3 = st.columns([1, 2, 1])
    with c_cta2:
        st.info("💡 You must be logged in to create a letter.")
        if st.button("🚀 Create Free Account & Start", type="primary", use_container_width=True, key="top_signup_btn"):
            set_mode("login")
        if st.button("Already have an account? Log In", type="secondary", use_container_width=True, key="top_login_btn"):
            set_mode("login")

    st.markdown("---")

    # --- PRODUCT GRID ---
    st.subheader("What can you send?")
    
    col_a, col_b = st.columns(2)
    with col_a:
        with st.container(border=True):
            # --- THE UPDATE ---
            st.markdown("### 🎅 Letters FROM Santa")
            st.caption("Don't just write *to* him. Send a magical letter **FROM** the North Pole directly to your child.")
    with col_b:
        with st.container(border=True):
            st.markdown("### 🏛️ Civic Action")
            st.caption("Mail all your Representatives with one voice command.")

    col_c, col_d = st.columns(2)
    with col_c:
        with st.container(border=True):
            st.markdown("### 🏺 Heirloom")
            st.caption("Archival paper. Wet-ink style fonts. For memories.")
    with col_d:
        with st.container(border=True):
            st.markdown("### ⚡ Standard")
            st.caption("Quick, printed letters. Easier than a printer.")

    # --- BOTTOM CTA BUTTON ---
    st.markdown("<br>", unsafe_allow_html=True)
    c_bot1, c_bot2, c_bot3 = st.columns([1, 2, 1])
    with c_bot2:
        if st.button("✨ Create New Account", type="primary", use_container_width=True, key="bottom_signup_btn"):
            set_mode("login")

    # --- FOOTER ---
    st.markdown("<br><br>", unsafe_allow_html=True)
    f1, f2 = st.columns([4, 1])
    with f2:
        if st.button("Legal / Privacy"):
            set_mode("legal")