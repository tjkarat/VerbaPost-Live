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
      "operatingSystem": "Web",
      "applicationCategory": "CommunicationApplication",
      "offers": {
        "@type": "Offer",
        "price": "2.99",
        "priceCurrency": "USD"
      },
      "description": "The easiest way to send real physical mail online. Turn voice dictation or text into USPS First Class letters. Features include Santa Letters, writing to Congress, bulk campaign mailing, and archival heirloom letters.",
      "featureList": "Voice-to-Text Dictation, USPS Mail Delivery, Santa Letters, Civic Engagement Tools, Bulk Mailing, Address Book"
    }
    </script>
    """, unsafe_allow_html=True)

    # --- 2. SEMANTIC HEADER (Replaces Logo) ---
    st.markdown("""
    <header style="text-align: center; padding-top: 20px; padding-bottom: 30px;">
        <h1 style="font-size: 3.5rem; font-weight: 700; color: #1e3c72; margin-bottom: 0.5rem;">
            VerbaPost
        </h1>
        <h2 style="font-size: 1.5rem; font-weight: 500; color: #555; margin-top: 0;">
            Texts are trivial. Emails are ignored.<br>
            <span style="color: #d93025; font-weight: 700;">REAL MAIL GETS READ.</span>
        </h2>
    </header>
    """, unsafe_allow_html=True)

    # --- 3. CALL TO ACTION ---
    c_cta1, c_cta2, c_cta3 = st.columns([1, 2, 1])
    with c_cta2:
        if st.button("🚀 Start Sending Mail", type="primary", use_container_width=True, key="hero_signup_btn"):
            set_mode("login", view_preference="signup")
        
        st.markdown("""
        <div style="text-align: center; margin-top: 10px; color: #666;">
            <small>No printer. No stamps. No post office lines.</small>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # --- 4. MISSION & ABOUT (SEO Content) ---
    st.subheader("Why VerbaPost?")
    
    col_mission, col_features = st.columns([3, 2])
    
    with col_mission:
        st.markdown("""
        <div style="font-size: 1.1rem; line-height: 1.6;">
        <p><strong>Our Mission: Reconnecting the Physical World</strong></p>
        <p>In a world drowning in digital noise, physical mail has become a superpower. It implies effort, care, and importance. But the process of sending mail—finding paper, envelopes, stamps, and walking to a mailbox—is stuck in the past.</p>
        <p><strong>VerbaPost bridges the gap.</strong> We use advanced AI to capture your authentic voice and convert it into a professional physical document. Whether you are a constituent demanding action from Congress, a grandparent sharing a story, or a campaign manager reaching 500 voters, VerbaPost handles the logistics so you can focus on the message.</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col_features:
        with st.container(border=True):
            st.markdown("""
            **Key Features:**
            * 🎙️ **Voice Dictation:** Just speak. We type.
            * ✨ **AI Editor:** Polish grammar instantly.
            * 📮 **USPS Fulfillment:** Mailed in 24hrs.
            * 📂 **Bulk Campaigns:** CSV upload supported.
            * 📜 **Certified Mail:** Tracking available.
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
                    with st.container(border=True):
                        st.metric(label=state, value=str(count))

    # --- 8. FAQ ---
    st.markdown("---")
    st.subheader("Frequently Asked Questions")
    
    with st.expander("📮 How long does delivery take?"):
        st.write("We mail all letters via **USPS First Class Mail** within 24 hours. Domestic delivery typically takes 4-6 business days.")
        
    with st.expander("🔒 Is my data private?"):
        st.write("Yes. Standard and Civic letters are processed automatically via API. Humans do not read them. Heirloom/Santa letters are manually quality-checked.")
        
    with st.expander("🌍 Can I mail internationally?"):