cat <<EOF > splash_view.py
import streamlit as st

# Version 3.0 - Final HTML Grid
def show_splash():
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
    <style>
        .price-card {
            background-color: #f9f9f9;
            padding: 15px;
            border-radius: 10px;
            text-align: center;
            border: 1px solid #ddd;
            height: 100%;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }
        .price-tag {
            color: #E63946;
            font-size: 32px;
            font-weight: bold;
            margin: 10px 0;
        }
        .price-title {
            font-size: 18px;
            font-weight: 600;
            margin-bottom: 5px;
        }
        .price-desc {
            font-size: 14px;
            color: #555;
            line-height: 1.4;
        }
        .grid-container {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
        }
    </style>

    <div class="grid-container">
        <div class="price-card">
            <div>
                <div class="price-title">⚡ Standard</div>
                <div class="price-tag">&#36;2.99</div>
                <div class="price-desc">API Fulfillment<br>Window Envelope<br>Mailed in 24hrs</div>
            </div>
        </div>

        <div class="price-card" style="border: 2px solid #4CAF50; background-color: #f0fff4;">
            <div>
                <div class="price-title">🏺 Heirloom</div>
                <div class="price-tag">&#36;5.99</div>
                <div class="price-desc">Hand-Stamped<br>Premium Paper<br>Mailed from Nashville</div>
            </div>
        </div>

        <div class="price-card">
            <div>
                <div class="price-title">🏛️ Civic Blast</div>
                <div class="price-tag">&#36;6.99</div>
                <div class="price-desc">Activism Mode<br>Auto-Find Reps<br>Mails Senate + House</div>
            </div>
        </div>
    </div>
    """
    st.markdown(html_pricing, unsafe_allow_html=True)

    st.divider()

    # --- CTA ---
    col_spacer, col_btn, col_spacer2 = st.columns([1, 2, 1])
    with col_btn:
        if st.button("🚀 Create My Account", type="primary", use_container_width=True):
            st.session_state.current_view = "login"
            st.session_state.initial_mode = "signup"
            st.rerun()
        
        st.write("")
        
        if st.button("Already a member? Log In", type="secondary", use_container_width=True):
            st.session_state.current_view = "login"
            st.session_state.initial_mode = "login"
            st.rerun()