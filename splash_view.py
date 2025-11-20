import streamlit as st

# Version 3.0 - Force HTML Layout
def show_splash():
    # --- HERO ---
    st.title("VerbaPost 📮")
    st.subheader("The Authenticity Engine.")
    st.markdown("##### Texts are trivial. Emails are ignored. Real letters get read.")
    
    st.divider()

    # --- HOW IT WORKS ---
    st.subheader("How it Works")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("🎙️ **1. Dictate**")
        st.caption("Tap the mic. AI handles the typing.")
    with c2:
        st.markdown("✍️ **2. Sign**")
        st.caption("Sign your name on screen.")
    with c3:
        st.markdown("📮 **3. We Mail**")
        st.caption("We print, stamp, and mail it.")

    st.divider()

    # --- PRICING TIERS (HTML GRID) ---
    st.subheader("Simple Pricing")
    
    html_pricing = """
    <div style="display: flex; gap: 10px; flex-wrap: wrap; justify-content: center;">
        
        <div style="flex: 1; min-width: 200px; background: #f0f2f6; padding: 15px; border-radius: 10px; text-align: center;">
            <h3 style="margin:0;">⚡ Standard</h3>
            <h2 style="color: #E63946; font-size: 36px; margin: 0;">$2.99</h2>
            <p style="font-size: 14px; color: #555;">
                API Fulfillment<br>
                Window Envelope<br>
                Mailed in 24hrs
            </p>
        </div>

        <div style="flex: 1; min-width: 200px; background: #e8fdf5; padding: 15px; border-radius: 10px; text-align: center; border: 2px solid #4CAF50;">
            <h3 style="margin:0;">🏺 Heirloom</h3>
            <h2 style="color: #E63946; font-size: 36px; margin: 0;">$5.99</h2>
            <p style="font-size: 14px; color: #555;">
                Hand-Stamped<br>
                Premium Paper<br>
                Mailed from Nashville, TN
            </p>
        </div>

        <div style="flex: 1; min-width: 200px; background: #fff8e1; padding: 15px; border-radius: 10px; text-align: center;">
            <h3 style="margin:0;">🏛️ Civic</h3>
            <h2 style="color: #E63946; font-size: 36px; margin: 0;">$6.99</h2>
            <p style="font-size: 14px; color: #555;">
                Activism Mode<br>
                Auto-Find Reps<br>
                Mails Senate + House
            </p>
        </div>

    </div>
    """
    st.markdown(html_pricing, unsafe_allow_html=True)

    st.divider()

    # --- CTA ---
    col_spacer, col_btn, col_spacer2 = st.columns([1, 2, 1])
    with col_btn:
        if st.button("🚀 Start Writing Now", type="primary", use_container_width=True):
            st.session_state.current_view = "main_app"
            st.rerun()
            
        st.write("")
        
        if st.button("Already a member? Log In", type="secondary", use_container_width=True):
            st.session_state.current_view = "login"
            st.rerun()