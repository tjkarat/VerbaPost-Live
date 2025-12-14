import streamlit as st
import time

# --- ROBUST IMPORTS ---
try:
    import database
except Exception:
    database = None

try:
    import payment_engine
except Exception:
    payment_engine = None

try:
    import secrets_manager
except Exception:
    secrets_manager = None

# --- LEGACY PAGE LOGIC ---
def render_legacy_page():
    # Updated Branding: End of Life Service
    st.markdown("## 🕊️ Legacy Service")
    st.info("Securely document and deliver your final wishes.")
    
    st.write("""
    The VerbaPost Legacy Service is designed for sensitive, high-importance correspondence 
    regarding end-of-life instructions, estate details, or final personal messages. 
    Includes certified tracking and archival-grade materials.
    """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Service Includes")
        st.markdown("""
        * **Format:** Heirloom Heavyweight Paper (Watermarked)
        * **Delivery:** USPS Certified Mail with Tracking
        * **Security:** Digital Encryption + Physical Proof of Delivery
        * **Price:** **$15.99** (All inclusive)
        """)
        
    with col2:
        st.markdown("### Secure Checkout")
        # Updated Price Button
        if st.button("Begin Legacy Process ($15.99)", type="primary"):
            if payment_engine:
                base = "https://verbapost.streamlit.app"
                if secrets_manager:
                    sec_url = secrets_manager.get_secret("BASE_URL")
                    if sec_url:
                        base = sec_url
                
                # Clean the base URL
                base = base.rstrip('/')
                # Pass a flag so main.py knows this is a high-value Legacy order
                success_url = f"{base}?session_id={{CHECKOUT_SESSION_ID}}&tier=Legacy&service=EndOfLife"
                
                with st.spinner("Initializing secure session..."):
                    # FIX: Correct Price (1599) and syntax
                    url, sid = payment_engine.create_checkout_session(
                        "VerbaPost Legacy Service (End of Life)",
                        1599,  # $15.99 in cents
                        success_url,
                        base
                    )
                    
                    if url:
                        st.success("Secure Link Ready")
                        st.link_button("👉 Proceed to Payment ($15.99)", url)
                    else:
                        st.error("Service temporarily unavailable.")
            else:
                st.error("Payment secure connection failed.")

    st.markdown("---")
    if st.button("⬅️ Return to Standard Services"):
        st.query_params.clear()
        st.rerun()