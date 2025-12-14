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
    st.markdown("## 🏛️ Legacy Service")
    st.info("You are viewing the classic VerbaPost interface (v1.0).")
    
    st.write("""
    This service allows you to send a standard letter without the advanced AI features 
    of the new Workspace. It is maintained for compatibility.
    """)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Service Details")
        st.markdown("""
        * **Format:** Standard Business Letter
        * **Price:** $2.99 flat rate
        * **Features:** Basic text input, PDF generation, USPS First Class Mail
        """)
        
    with col2:
        st.markdown("### Checkout")
        if st.button("Generate Legacy Payment Link", type="primary"):
            if payment_engine:
                base = "https://verbapost.streamlit.app"
                if secrets_manager:
                    sec_url = secrets_manager.get_secret("BASE_URL")
                    if sec_url:
                        base = sec_url
                
                # Clean the base URL
                base = base.rstrip('/')
                success_url = f"{base}?session_id={{CHECKOUT_SESSION_ID}}&tier=Legacy"
                
                with st.spinner("Creating session..."):
                    # FIX: Arguments are now correctly inside the parentheses
                    url, sid = payment_engine.create_checkout_session(
                        "VerbaPost Legacy Service",
                        299,  # Price in cents ($2.99)
                        success_url,
                        base
                    )
                    
                    if url:
                        st.success("Link Created!")
                        st.link_button("👉 Pay Now ($2.99)", url)
                    else:
                        st.error("Could not create payment session.")
            else:
                st.error("Payment engine is not loaded.")

    st.markdown("---")
    if st.button("⬅️ Return to Main App"):
        st.query_params.clear()
        st.rerun()