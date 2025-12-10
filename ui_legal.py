import streamlit as st

def show_legal():
    st.markdown("# ⚖️ Legal & Privacy")
    st.markdown("---")
    
    # --- FIX: Button now forces immediate rerun ---
    if st.button("⬅️ Return to Home", key="legal_back_btn"):
        st.session_state.app_mode = "splash"
        st.rerun()

    # --- LEGAL CONTENT (From Screenshot) ---
    st.markdown("""
    We respect your privacy. We do not sell your data. We only use your data to print and mail your letters.

    **1. Data Collection:** We collect your email, name, and address to facilitate account creation and letter delivery. We also collect the content of your letters for printing purposes.

    **2. Data Usage:** We use your data to:
    * Create and manage your account.
    * Process your payments securely via Stripe.
    * Print and mail your letters via our third-party print partner, PostGrid.
    * Improve our services and communicate with you about your account.

    **3. Data Sharing:** We do not sell your personal data to third parties. We share data only with trusted partners (Stripe, PostGrid, OpenAI) as necessary to provide our services.

    **4. Security:** We employ industry-standard security measures to protect your data. However, no method of transmission over the internet is 100% secure.
    """)