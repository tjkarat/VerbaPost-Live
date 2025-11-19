import streamlit as st

def show_splash():
    st.title("VerbaPost 📮")
    st.subheader("The Authenticity Engine.")
    st.markdown(
        """
        **Don't just send a text. Send a legacy.**
        VerbaPost turns your spoken voice into a physical, mailed letter.
        """
    )
    st.divider()
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("### ⚡ Standard")
        st.caption(".50")
        st.write("API Fulfillment. Window Envelope.")
    with c2:
        st.markdown("### 🏺 Heirloom")
        st.caption(".00")
        st.write("Hand-stamped. Premium Paper.")
    with c3:
        st.markdown("### 🏛️ Civic")
        st.caption(".00")
        st.write("Mail your Senators.")
    st.divider()
    
    if st.button("🚀 Start Writing Now", type="primary", use_container_width=True):
        st.session_state.current_view = "main_app"
        st.rerun()
