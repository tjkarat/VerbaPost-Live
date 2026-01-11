import streamlit as st

def render_legal_page():
    """
    Renders the Terms of Service, Privacy Policy, and Acceptable Use Policy.
    Explicitly covers Automated PCM Fulfillment and Content Review.
    """
    st.title("⚖️ Legal & Privacy Center")
    st.markdown("Last Updated: **January 2026**")
    
    # --- NAVIGATION ---
    if st.button("⬅️ Return to App", type="primary"):
        # Smart Return Logic
        if st.session_state.get("authenticated"):
            # Return to active dashboard based on mode
            if st.session_state.get("is_partner"):
                st.session_state.app_mode = "partner"
            elif st.session_state.get("system_mode") == "utility":
                st.session_state.app_mode = "main"
            else:
                st.session_state.app_mode = "heirloom"
        else:
            # Return to Splash if logged out
            st.session_state.app_mode = "splash"
        st.rerun()

    st.divider()

    # --- TABS ---
    tab_terms, tab_privacy, tab_use = st.tabs(["📜 Terms of Service", "🔒 Privacy Policy", "🚫 Acceptable Use"])

    # --- TAB 1: TERMS OF SERVICE ---
    with tab_terms:
        st.markdown("""
        ### 1. Service Description
        VerbaPost ("The Service") is a hybrid digital-physical correspondence platform. We provide:
        * **The Letter Store:** A service to draft letters digitally which are printed and mailed physically.
        * **The Family Archive:** A service to capture voice recordings, transcribe them, and mail them as physical letters.
        
        ### 2. Fulfillment & Delivery
        By using VerbaPost, you acknowledge our fulfillment process:
        * **Automated Processing:** Your letters are processed and printed by our API partner, **PCM Integrations**.
        * **Carriers:** We utilize the United States Postal Service (USPS) for final delivery.
        * **Timelines:** We target a dispatch time of 1-2 business days. Delivery times are subject to USPS performance and are not guaranteed.
        * **Lost Mail:** VerbaPost is not liable for items lost, damaged, or delayed by the USPS. However, we will reprint and resend any undelivered items free of charge upon request.

        ### 3. Payment & Subscriptions
        * **One-Time Purchases:** Charged immediately via Stripe.
        * **Subscriptions:** The "Family Archive" subscription ($19/mo) renews automatically. You may cancel at any time via your account settings.
        * **Refunds:** Refunds are issued at our sole discretion. If a letter contains errors caused by our system, we will refund or reprint it. Errors in user-submitted addresses or content are the user's responsibility.

        ### 4. User Accounts
        You are responsible for maintaining the confidentiality of your login credentials. You agree to notify us immediately of any unauthorized use of your account.

        ### 5. Limitation of Liability
        To the maximum extent permitted by law, VerbaPost shall not be liable for any indirect, incidental, special, or consequential damages arising out of the use of the service.
        """)

    # --- TAB 2: PRIVACY POLICY ---
    with tab_privacy:
        st.markdown("""
        ### 1. Information We Collect
        * **Account Data:** Name, Email Address, and Password hash.
        * **Correspondence Data:** The text content of your letters and audio recordings of your stories.
        * **Mailing Data:** Names and Physical Addresses of your recipients.
        * **Usage Data:** Logs of when you access the service and payment transaction history (via Stripe).

        ### 2. How We Use Your Data
        * **Fulfillment:** We use your content and address data solely to generate PDF documents and physical envelopes via **PCM Integrations**.
        * **AI Processing:** We utilize **OpenAI** to transcribe audio and polish text. Data sent to OpenAI is processed ephemerally and is **not used to train their models**.
        * **Communication:** We send transactional emails (receipts, tracking) via **Resend**.

        ### 3. Data Privacy & Confidentiality
        **Important:** Our fulfillment partner, PCM Integrations, adheres to strict data privacy and security standards. 
        * We maintain strict confidentiality protocols.
        * We do not sell, rent, or share your personal content with advertisers.
        
        ### 4. Data Retention & Deletion
        * **Retention:** We retain drafts and sent letters to allow you to view your history.
        * **Deletion:** You have the "Right to be Forgotten." Contact `support@verbapost.com` to request the permanent deletion of your account and all associated data.

        ### 5. Third-Party Processors
        We trust the following partners with specific data segments:
        * **Stripe:** Payment Processing.
        * **Supabase:** Encrypted Database Storage.
        * **Twilio:** Telephony services for the Family Archive.
        * [cite_start]**PCM Integrations:** Physical printing and mailing. [cite: 1]
        * **Geocodio:** Civic data lookups (Representatives).
        """)

    # --- TAB 3: ACCEPTABLE USE ---
    with tab_use:
        st.error("⚠️ Violation of this policy will result in immediate account termination.")
        st.markdown("""
        ### 1. Prohibited Content
        VerbaPost is a family-oriented service. You may not use our platform to send:
        * **Hate Speech:** Content that promotes violence or hatred against individuals or groups based on race, religion, gender, or orientation.
        * **Harassment:** Threats, stalking, or bullying behavior.
        * **Illegal Material:** Content that facilitates illegal acts, including fraud or the sale of illicit goods.
        * **Sexually Explicit Material:** Pornographic or obscene content.

        ### 2. Content Screening
        * We reserve the right to refuse to print or mail any letter that we, in our sole discretion, deem to violate these policies.
        * If a letter is rejected for policy violations, your credit/payment may be forfeited to cover processing costs.

        ### 3. Civic Letters
        Letters sent to government officials must maintain a respectful tone. We will not process letters containing threats against public officials.
        """)

    st.divider()
    st.caption("VerbaPost Inc. | Nashville, TN | support@verbapost.com")