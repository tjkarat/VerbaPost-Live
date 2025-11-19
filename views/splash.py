import streamlit as st
from PIL import Image

def show_splash():
    """
    Renders the Landing/Splash page.
    
    Purpose:
    - Explain the value proposition.
    - Direct users to "Get Started" or "Login".
    - Showcase the tiers (Standard vs Heirloom).
    """
    
    # --- Hero Section ---
    st.title("VerbaPost 📮")
    st.subheader("The Authenticity Engine.")
    st.markdown(
        """
        **Don't just send a text. Send a legacy.**
        
        VerbaPost turns your spoken voice into a physical, mailed letter. 
        From a quick note to your Senator, to a handwritten heirloom for your grandchildren.
        """
    )
    
    st.divider()

    # --- Feature Breakdown (Columns) ---
    c1, c2, c3 = st.columns(3)
    
    with c1:
        st.markdown("### ⚡ Standard")
        st.caption("$2.50 / letter")
        st.write("Perfect for business, utility, and quick notes.")
        st.write("- API Fulfillment")
        st.write("- Window Envelope")
        st.write("- Mailed in 24hrs")

    with c2:
        st.markdown("### 🏺 Heirloom")
        st.caption("$5.00 / letter")
        st.write("For moments that matter.")
        st.write("- Hand-stamped")
        st.write("- Premium Paper")
        st.write("- Handwritten Envelope")

    with c3:
        st.markdown("### 🏛️ Civic")
        st.caption("$6.00 / blast")
        st.write("Make your voice heard.")
        st.write("- Auto-find Reps")
        st.write("- Mails 3 Letters (Senate + House)")
        st.write("- Maximum Impact")

    st.divider()

    # --- Call to Action ---
    # This button changes the session state to load the main app
    if st.button("🚀 Start Writing Now", type="primary", use_container_width=True):
        st.session_state.current_view = "main_app"
        st.rerun()

    st.markdown("Already a member? [Log In](#)")