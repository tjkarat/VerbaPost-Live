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
    # --- 1. SEO INJECTION (JSON-LD) ---
    st.markdown("""
    <script type="application/ld+json">
    {
      "@context": "https://schema.org",
      "@type": "SoftwareApplication",
      "name": "VerbaPost",
      "applicationCategory": "CommunicationApplication",
      "operatingSystem": "Web",
      "offers": {
        "@type": "Offer",
        "price": "2.99",
        "priceCurrency": "USD"
      },
      "description": "VerbaPost is the easiest way to send physical mail online. We convert voice dictation into USPS letters, printed and mailed automatically. Features include bulk campaign mailing, letters to Congress, and Santa letters.",
      "featureList": "Voice-to-Mail, USPS Delivery, Bulk Campaign Tools, Address Book"
    }
    </script>
    """, unsafe_allow_html=True)

    # --- 2. HERO SECTION (Text Only - Fast Load) ---
    st.markdown("""
    <div style="text-align: center; padding-top: 20px; padding-bottom: 20px;">
        <h1 style="color: #1e3c72; font-size: 3.5rem; margin-bottom: 10px;">VerbaPost</h1>
        <p style="font-size: 1.6rem; color: #444; font-weight: 500; margin-top: 0;">
            Texts are trivial. Emails are ignored.<br>
            <span style="color: #d93025; font-weight: 700;">REAL MAIL GETS READ.</span>
        </p>
        <p style="font-size: 1.1rem; color: #666; margin-top: 15px;">
            The first <b>Voice-to-Mail</b> platform. Speak your letter, and we print, stamp, and mail it for you.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # --- 3. CALL TO ACTION ---
    c_cta1, c_cta2, c_cta3 = st.columns([1, 2, 1])
    with c_cta2:
        if st.button("🚀 Start Sending Mail", type="primary", use_container_width=True, key="hero_signup_btn"):
            set_mode("login", view_preference="signup")
        
        st.markdown("""
        <div style="text-align: center; margin-top: 10px;">
            <small>No printer. No stamps. No post office lines.</small>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # --- 4. MISSION & ABOUT (New SEO Content) ---
    # This section specifically addresses Grok's feedback about "Insufficient Content"
    st.subheader("Why VerbaPost?")
    
    col_mission, col_features = st.columns([3, 2])
    
    with col_mission:
        st.markdown("""
        **Our Mission: Reconnecting the Physical World**
        
        In a world drowning in digital noise, physical mail has become a superpower. It implies effort, care, and importance. But the process of sending mail—finding paper, envelopes, stamps, and walking to a mailbox—is stuck in the past.
        
        **VerbaPost bridges the gap.** We use advanced AI (OpenAI Whisper) to capture your authentic voice and convert it into a professional physical document. Whether you are a constituent demanding action from Congress, a grandparent sharing a story, or a campaign manager reaching 500 voters, VerbaPost handles the logistics so you can focus on the message.
        """)
    
    with col_features:
        with st.container(border=True):
            st.markdown("""
            **Key Features:**
            * 🎙️ **Voice Dictation:** Just speak. We type.
            * ✨ **AI Editor:** Polish grammar instantly.
            * 📮 **USPS Fulfillment:** Printed & mailed in 24hrs.
            * 📂 **Bulk Campaigns:** CSV upload for mass mail.
            * 📜 **Certified Mail:** Tracking included.
            """)

    st.markdown("---")

    # --- 5. HOW IT WORKS ---
    st.subheader("How It Works")
    step1, step2, step3 = st.columns(3)
    
    with step1:
        with st.container(border=True):
            st.markdown("#### 1. Dictate")
            st.caption("Record your message directly in the browser. Our AI transcribes it with near-perfect accuracy.")
    
    with step2:
        with st.container(border=True):
            st.markdown("#### 2. Address")
            st.caption("Enter the recipient or choose from your Address Book. We verify the address automatically.")
            
    with step3:
        with st.container(border=True):
            st.markdown("#### 3. We Mail")
            st.caption("We print on premium paper, envelope, stamp, and hand it to the USPS.")

    # --- 6. SERVICES GRID ---
    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader("Services & Pricing")
    
    col_a, col_b = st.columns(2)
    with col_a:
        with st.container(border=True):
            st.markdown("### 🎅 Santa Letters ($9.99)")
            st.caption("The ultimate holiday magic. A letter FROM Santa, on festive stationery, with a **North Pole postmark**.")
    with col_b:
        with st.container(border=True):
            st.markdown("### 📢 Campaign / Bulk ($1.99)")
            st.caption("For activists and organizers. Upload a CSV and mail hundreds of constituents instantly.")

    col_c, col_d = st.columns(2)
    with col_c:
        with st.container(border=True):
            st.markdown("### 🏺 Heirloom ($5.99)")
            st.caption("For memories that last. Printed on archival heavyweight paper with handwriting-style fonts.")
    with col_d:
        with st.container(border=True):
            st.markdown("### ⚡ Standard ($2.99)")
            st.caption("For everyday correspondence. Fast, professional, and cheaper than your time.")

    # --- 7. CIVIC LEADERBOARD ---
    if database:
        stats = database.get_civic_leaderboard()
        if stats:
            st.markdown("---")
            st.subheader("🏛️ Civic Leaderboard")
            st.caption("Most active states writing to Congress via VerbaPost.")
            cols = st.columns(len(stats))
            for i, (state, count) in enumerate(stats):
                with cols[i]:
                    st.metric(label=state, value=str(count))

    # --- 8. FAQ ---
    st.markdown("---")
    st.subheader("Frequently Asked Questions")
    
    with st.expander("📮 How long does delivery take?"):
        st.write("We mail all letters via **USPS First Class Mail** within 24 hours. Domestic delivery typically takes 4-6 business days.")
        
    with st.expander("🔒 Is my data private?"):
        st.write("Yes. Standard and Civic letters are processed automatically via API. Humans do not read them. Heirloom/Santa letters are manually quality-checked.")
        
    with st.expander("🌍 Can I mail internationally?"):
        st.write("Yes! We support mailing to over 180 countries including the UK, Canada, and Australia.")

    # --- 9. FOOTER ---
    st.markdown("<br><br>", unsafe_allow_html=True)
    f1, f2 = st.columns([4, 1])
    with f2:
        if st.button("Legal / Terms", key="footer_legal"):
            set_mode("legal")