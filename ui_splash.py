import streamlit as st
import os

# --- OPTIONAL IMPORT FOR LEADERBOARD ---
try: import database
except: database = None

def set_mode(mode, view_preference="login"):
    st.session_state.app_mode = mode
    st.session_state.auth_view = view_preference
    st.rerun()

def show_splash():
    # --- 1. SEO INJECTION (JSON-LD ENHANCED) ---
    # Added specific keywords like "Online Post Office" and "Snail Mail App"
    st.markdown("""
    <script type="application/ld+json">
    {
      "@context": "https://schema.org",
      "@type": "SoftwareApplication",
      "name": "VerbaPost",
      "operatingSystem": "Web",
      "applicationCategory": "CommunicationApplication",
      "offers": {
        "@type": "Offer",
        "price": "2.99",
        "priceCurrency": "USD"
      },
      "description": "The easiest way to send real physical mail online. Turn voice dictation or text into USPS First Class letters. Features include Santa Letters, writing to Congress, bulk campaign mailing, and archival heirloom letters. No printer or stamps required.",
      "featureList": "Voice-to-Text Dictation, USPS Mail Delivery, Santa Letters, Civic Engagement Tools, Bulk Mailing, Address Book"
    }
    </script>
    """, unsafe_allow_html=True)

    # --- 2. HERO SECTION (Logo Removed for Speed) ---
    # The Title and Tagline now appear instantly at the very top
    st.markdown("""
    <div style="text-align: center; padding-bottom: 20px; padding-top: 10px;">
        <h1 style="color: #1e3c72; margin-bottom: 0; font-size: 3.5rem;">VerbaPost</h1>
        <p style="font-size: 1.5rem; color: #555; margin-top: 5px; font-weight: 500;">
            Texts are trivial, emails ignored, <b>REAL MAIL gets READ.</b>
        </p>
    </div>
    """, unsafe_allow_html=True)

    # --- 3. HOW IT WORKS ---
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

    # --- 4. MID-PAGE CTA ---
    c_cta1, c_cta2, c_cta3 = st.columns([1, 2, 1])
    with c_cta2:
        st.info("💡 You must be logged in to create a letter.")
        
        if st.button("🚀 Create Free Account & Start", type="primary", use_container_width=True, key="top_signup_btn"):
            set_mode("login", view_preference="signup")
            
        if st.button("Already have an account? Log In", type="secondary", use_container_width=True, key="top_login_btn"):
            set_mode("login", view_preference="login")

    st.markdown("---")

    # --- 5. PRODUCT GRID ---
    st.subheader("What can you send?")
    
    col_a, col_b = st.columns(2)
    with col_a:
        with st.container(border=True):
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

    # --- 6. FAQ (SEO CONTENT) ---
    st.markdown("---")
    st.subheader("Frequently Asked Questions")
    
    with st.expander("📮 How long does delivery take?"):
        st.write("We mail all letters via **USPS First Class Mail** within 24 hours. Domestic delivery typically takes 4-6 business days. International mail takes 5-21 days depending on the destination.")
        
    with st.expander("🔒 Is my audio private?"):
        st.write("Yes. For Standard and Civic letters, the process is automated. Your audio is transcribed by AI and sent directly to our printing API (PostGrid). No humans listen to your dictation.")
        
    with st.expander("🌍 Can I send letters internationally?"):
        st.write("Yes! We support mailing to over 180 countries including the UK, Canada, Australia, and most of Europe for a small surcharge.")
        
    with st.expander("🎅 How does the Santa letter work?"):
        st.write("You dictate a message to your child. We print it on festive North Pole stationery and mail it with a specialized **North Pole postmark** so it looks like it came directly from Santa's desk.")

    # --- 7. CIVIC LEADERBOARD (Bottom) ---
    if database:
        stats = database.get_civic_leaderboard()
        if stats:
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("### 🏛️ Civic Leaderboard: Most Active States")
            st.caption("Real-time count of letters sent to Congress by state.")
            
            cols = st.columns(len(stats))
            for i, (state, count) in enumerate(stats):
                with cols[i]:
                    with st.container(border=True):
                        st.metric(label=state, value=f"{count}")

    # --- 8. BOTTOM CTA ---
    st.markdown("<br>", unsafe_allow_html=True)
    c_bot1, c_bot2, c_bot3 = st.columns([1, 2, 1])
    with c_bot2:
        if st.button("✨ Create New Account", type="primary", use_container_width=True, key="bottom_signup_btn"):
            set_mode("login", view_preference="signup")

    # --- 9. FOOTER ---
    st.markdown("<br><br>", unsafe_allow_html=True)
    f1, f2 = st.columns([4, 1])
    with f2:
        if st.button("Legal / Privacy"):
            st.session_state.app_mode = "legal"
            st.rerun()