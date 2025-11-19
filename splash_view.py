import streamlit as st

def show_splash():
    # --- PRICING CONSTANTS ---
    P_STANDARD = ".99"
    P_HEIRLOOM = ".99"
    P_CIVIC = ".99"

    st.title("VerbaPost 📮")
    st.subheader("The Authenticity Engine.")
    st.markdown(
        """
        **Don't just send a text. Send a legacy.**
        
        VerbaPost turns your spoken voice into a physical, mailed letter. 
        """
    )
    
    st.divider()

    # --- Feature Breakdown (Columns) ---
    c1, c2, c3 = st.columns(3)
    
    with c1:
        st.markdown("### ⚡ Standard")
        st.caption(f"**{P_STANDARD} / letter**")
        st.write("API Fulfillment")
        st.write("Window Envelope")
        st.write("Mailed in 24hrs")

    with c2:
        st.markdown("### 🏺 Heirloom")
        st.caption(f"**{P_HEIRLOOM} / letter**")
        st.write("Hand-stamped")
        st.write("Premium Paper")
        st.write("Mailed from Nashville, TN")

    with c3:
        st.markdown("### 🏛️ Civic")
        st.caption(f"**{P_CIVIC} / blast**")
        st.write("Mail your Senators")
        st.write("Auto-lookup")
        st.write("(Coming Soon)")

    st.divider()

    # --- Call to Action ---
    # KEY ARGUMENT ADDED to prevent duplicate ID error
    if st.button("🚀 Start Writing Now", type="primary", use_container_width=True, key="splash_start"):
        st.session_state.current_view = "login"
        st.rerun()

    if st.button("Already a member? Log In", key="splash_login"):
        st.session_state.current_view = "login"
        st.rerun()
